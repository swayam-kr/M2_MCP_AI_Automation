"""
Phase 7: MCP Dispatcher
=======================
Handles gated dispatch of generated content to designated MCP servers.
Communicates using MCP's JSON-RPC protocol over stdio.
"""

import sys
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from backend.config import get_setting
from backend.utils import format_pulse_for_dispatch, format_explainer_for_dispatch

logger = logging.getLogger("mcp_dispatcher")

class MCPDispatcherError(Exception):
    pass

class MCPDispatcher:
    def __init__(self):
        doc_cmd = get_setting("mcp.google_docs.server_command", "npx @anthropic/google-docs-mcp").split()
        if doc_cmd[0] in ("python", "python3"):
            doc_cmd[0] = sys.executable
        self.doc_cmd = doc_cmd
        
        gmail_cmd = get_setting("mcp.gmail.server_command", "npx @anthropic/gmail-mcp").split()
        if gmail_cmd[0] in ("python", "python3"):
            gmail_cmd[0] = sys.executable
        self.gmail_cmd = gmail_cmd

    def dispatch(self, content: Dict[str, Any], content_type: str, approvals: Dict[str, bool], recipients: List[str]) -> Dict[str, Any]:
        """
        Main entry point for dispatch pipeline.
        Formats the content, checks the gates, and executes MCP calls.
        """
        logger.info(f"Dispatching {content_type} content. Gates: {approvals}")
        
        # 1. Format content
        if content_type == "pulse":
            doc_text = format_pulse_for_dispatch(content)
            email_text = doc_text
            subject = f"Weekly Review Pulse - {content.get('generated_at', 'Now')}"
        elif content_type == "explainer":
            doc_text = format_explainer_for_dispatch(content)
            email_text = doc_text
            subject = f"Fee Explainer - {content.get('asset_class', 'Unknown')}"
        elif content_type == "combined":
            pulse_data = content.get("pulse", {})
            explainer_data = content.get("explainer", {})
            
            # Robust data extraction (handles both raw and wrapped structures)
            if "data" in pulse_data: pulse_data = pulse_data["data"]
            if "data" in explainer_data: explainer_data = explainer_data["data"]
            
            # 1. Structured Google Doc Text
            period = pulse_data.get("period", "Current Week")
            date_str = pulse_data.get("generated_at", "N/A")
            analysis_context = pulse_data.get("analysis_explanation", "N/A")
            
            # Full Report for Doc
            pulse_formatted = format_pulse_for_dispatch(pulse_data)
            explainer_formatted = format_explainer_for_dispatch(explainer_data)
            
            doc_text = (
                f"Groww Weekly Pulse - Summaries\n"
                f"Period: {period}\n"
                f"Generated on: {date_str}\n\n"
                f"Analysis Context:\n{analysis_context}\n\n"
                f"{pulse_formatted}\n\n"
                f"{explainer_formatted}"
            )

            # 2. Enhanced Email Subject (with date range)
            subject = f"Weekly Pulse + Fee Explainer - {period}"
            
            # 3. Smartly Structured Email Body
            pulse_formatted = format_pulse_for_dispatch(pulse_data)
            explainer_formatted = format_explainer_for_dispatch(explainer_data)
            
            email_text = (
                "Dear Operations Team,\n\n"
                f"Please find below the consolidated **Weekly Product Pulse** for the period: {period}.\n\n"
                f"{pulse_formatted}\n\n"
                "--- \n"
                f"{explainer_formatted}\n\n"
                "Best regards,\n"
                "Groww Intelligence Hub"
            )
        else:
            raise ValueError(f"Unknown content type for dispatch: {content_type}")

        results = {
            "doc": {"status": "skipped", "error": None},
            "draft": {"status": "skipped", "error": None},
            "formatted_text": email_text  # Show email text in UI by default
        }

        # Gate 1: Append to Doc
        if approvals.get("append_to_doc"):
            doc_id = get_setting("mcp.google_docs.document_id", "fallback_id")
            try:
                res = self._append_to_doc(doc_text, doc_id)
                results["doc"] = res
            except Exception as e:
                logger.error(f"Doc append failed: {e}")
                results["doc"] = {"status": "error", "error": str(e)}

        # Gate 2: Create Draft
        if approvals.get("create_draft"):
            try:
                res = self._create_draft(recipients, subject, email_text)
                results["draft"] = res
            except Exception as e:
                logger.error(f"Draft creation failed: {e}")
                results["draft"] = {"status": "error", "error": str(e)}

        return results

    def _call_mcp_tool(self, server_cmd: List[str], tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Subprocess wrapper to communicate with an MCP server via JSON-RPC stdio.
        """
        try:
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "ai-ops-automator", "version": "3.0"}
                }
            }
            call_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                }
            }
            payload = json.dumps(init_req) + "\n" + json.dumps(call_req) + "\n"
            
            logger.debug(f"Calling MCP tool: {tool_name} with command: {' '.join(server_cmd)}")
            proc = subprocess.run(
                server_cmd,
                input=payload.encode("utf-8"),
                capture_output=True,
                timeout=15,
                shell=False
            )

            stdout_str = proc.stdout.decode("utf-8", errors="replace")
            stderr_str = proc.stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                raise MCPDispatcherError(f"Command failed (exit {proc.returncode}): {stderr_str.strip()[:200]}")
            
            # Since MCP can return multiple JSON-RPC responses line by line, parse the last valid one 
            # associated with id=2
            responses = []
            for line in stdout_str.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            
            for resp in reversed(responses):
                if resp.get("id") == 2:
                    if "error" in resp:
                        err_msg = resp["error"].get("message", "Unknown tool error")
                        raise MCPDispatcherError(f"MCP returned error: {err_msg}")
                    content_list = resp.get("result", {}).get("content", [])
                    if content_list and content_list[0].get("type") == "text":
                        return {"result": content_list[0].get("text")}
                    return resp.get("result", {})
            
            if stderr_str.strip():
                raise MCPDispatcherError(f"No valid JSON-RPC response. Stderr: {stderr_str.strip()[:150]}")
            
            logger.warning(f"No valid JSON-RPC tool response found. stdout: {stdout_str}")
            return {"status": "mock_success_or_unparsable"}

        except subprocess.TimeoutExpired:
            raise MCPDispatcherError("Subprocess timed out after 15s. May be waiting for interactive OAuth prompt.")
        except Exception as e:
            logger.error(f"MCP tool call {tool_name} failed: {e}")
            raise MCPDispatcherError(str(e))

    def _append_to_doc(self, formatted_text: str, doc_id: str) -> Dict[str, Any]:
        """Call Google Docs MCP: appendText"""
        if not doc_id:
            raise ValueError("No Google Docs ID configured.")
        
        res = self._call_mcp_tool(
            self.doc_cmd, 
            "documents.appendText", 
            {"document_id": doc_id, "text": formatted_text}
        )
        # Mock actual return formatting for testing
        return {"status": "appended", "revision_id": res.get("result", "mock_rev_id")}

    def _create_draft(self, to_list: List[str], subject: str, body: str) -> Dict[str, Any]:
        """Call Gmail MCP: createDraft"""
        if not to_list:
            raise ValueError("No recipients provided for email draft.")
            
        res = self._call_mcp_tool(
            self.gmail_cmd, 
            "gmail.createDraft", 
            {"to": ", ".join(to_list), "subject": subject, "body": body}
        )
        return {"status": "created", "draft_id": res.get("result", "mock_draft_123")}

    def _send_draft(self, draft_id: str) -> Dict[str, Any]:
        """Call Gmail MCP: sendDraft"""
        if not draft_id:
            raise ValueError("Draft ID is required to send email.")
            
        res = self._call_mcp_tool(
            self.gmail_cmd, 
            "gmail.sendDraft", 
            {"draft_id": draft_id}
        )
        return {"status": "sent", "message_id": res.get("result", "mock_msg_456")}

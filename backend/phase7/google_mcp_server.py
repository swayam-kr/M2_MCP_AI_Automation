import sys
import os
import json
import logging
import traceback
import base64
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

def get_credentials():
    try:
        # 1. Stateless Serverless Fast-Path (Vercel)
        token_env = os.environ.get("GOOGLE_TOKEN_JSON")
        if token_env:
            logging.error("Found GOOGLE_TOKEN_JSON in environment. Loading stateless credentials...")
            token_dict = json.loads(token_env)
            return Credentials.from_authorized_user_info(token_dict)
            
        # 2. Stateful Local Fallback
        if not os.path.exists("token.json"):
            logging.error("token.json not found and GOOGLE_TOKEN_JSON env var missing.")
            return None
            
        logging.error("Loading credentials from local token.json file...")
        return Credentials.from_authorized_user_file("token.json")
    except Exception as e:
        logging.error(f"Error loading credentials: {e}")
        return None

def handle_append_text(creds, params):
    doc_id = params.get("document_id")
    text = params.get("text")
    
    if not doc_id or not text:
        return "Error: document_id and text strictly required."
        
    try:
        service = build('docs', 'v1', credentials=creds)
        
        # 1. Get document metadata to find the terminal index
        doc = service.documents().get(documentId=doc_id).execute()
        # End index is the last element's end property minus 1 for safety
        end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
        
        requests = [
            {
                'insertPageBreak': {
                    'location': {
                        'index': end_index
                    }
                }
            },
            {
                'insertText': {
                    'location': {
                        'index': end_index + 1,
                    },
                    'text': text + "\n\n"
                }
            }
        ]
        
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        return "success"
    except Exception as e:
        logging.error(f"Docs API Error: {e}")
        return f"Error: {e}"

def handle_create_draft(creds, params):
    to_addr = params.get("to")
    subject = params.get("subject")
    body = params.get("body")
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_addr
        message['From'] = 'me'
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'message': {'raw': encoded_message}}
        
        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        return draft['id']
    except Exception as e:
        logging.error(f"Gmail API Draft Error: {e}")
        return f"Error: {e}"

def handle_send_draft(creds, params):
    draft_id = params.get("draft_id")
    if not draft_id:
        return "Error: draft_id required."
        
    try:
        service = build('gmail', 'v1', credentials=creds)
        sent = service.users().drafts().send(userId="me", body={'id': draft_id}).execute()
        return sent.get('id', "success")
    except Exception as e:
        logging.error(f"Gmail API Send Error: {e}")
        return f"Error: {e}"

def main():
    creds = get_credentials()
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
            
        jsonrpc = msg.get("jsonrpc", "2.0")
        msg_id = msg.get("id")
        method = msg.get("method")
        
        if method == "initialize":
            res = {
                "jsonrpc": jsonrpc,
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05", # standard
                    "capabilities": {},
                    "serverInfo": {"name": "google-workspace-mcp", "version": "1.0.0"}
                }
            }
            print(json.dumps(res), flush=True)
            
        elif method == "tools/call":
            tool_name = msg.get("params", {}).get("name")
            params = msg.get("params", {}).get("arguments", {})
            
            res_text = "unsupported_tool"
            if not creds:
                res_text = "Error: Unauthenticated. Please run auth.py to generate token.json."
            elif tool_name == "documents.appendText":
                res_text = handle_append_text(creds, params)
            elif tool_name == "gmail.createDraft":
                res_text = handle_create_draft(creds, params)
            elif tool_name == "gmail.sendDraft":
                res_text = handle_send_draft(creds, params)
                
            if str(res_text).startswith("Error:"):
                # proper MCP error response handling (we can just return text result error)
                response = {
                    "jsonrpc": jsonrpc,
                    "id": msg_id,
                    "error": {
                        "code": -32000,
                        "message": res_text
                    }
                }
            else:
                response = {
                    "jsonrpc": jsonrpc,
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": str(res_text)}
                        ]
                    }
                }
            print(json.dumps(response), flush=True)

if __name__ == "__main__":
    main()

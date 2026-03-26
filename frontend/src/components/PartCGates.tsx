"use client";

import { useState } from "react";
import { APIResponse, DispatchResult, DispatchApprovals } from "@/types";

export default function PartCGates({ activeContent, contentType, setIsLoading, isLoading, setDispatchStatus }: { 
  activeContent: APIResponse | null, 
  contentType: string, 
  setIsLoading: (loading: boolean) => void, 
  isLoading: boolean, 
  setDispatchStatus: (status: DispatchResult | null) => void 
}) {
  const [recipients, setRecipients] = useState("");
  const [showRawText, setShowRawText] = useState(false);
  const [lastRawText, setLastRawText] = useState("");

  const handleDispatch = async (approvals: DispatchApprovals) => {
    setIsLoading(true);
    setDispatchStatus(null);
    try {
      const recips = recipients.split("\n").filter(e => e.trim());
      const res = await fetch(`/api/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content_type: contentType,
          content: activeContent,    // Send the combined object format
          approvals: approvals,
          recipients: recips
        }),
      });
      const data = await res.json();
      setDispatchStatus(data);
      if (data.results && data.results.formatted_text) {
          setLastRawText(data.results.formatted_text);
      }
    } catch (err) {
      console.error(err);
      setDispatchStatus({ status: "error", error: "Dispatch failed" });
    } finally {
      setIsLoading(false);
    }
  };

  const isDispatchDisabled = isLoading || !activeContent;

  return (
    <div>
      <h3 style={{ fontSize: "1rem", marginBottom: "16px", color: "var(--text-main)", fontWeight: 600 }}>Part C: MCP Dispatch</h3>
      
      <div className="control-group" style={{ marginBottom: "16px" }}>
        <label>Recipients (One per line)</label>
        <textarea rows={2} value={recipients} onChange={e => setRecipients(e.target.value)} placeholder="ceo@groww.in" disabled={isLoading} style={{ resize: "none" }} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "24px" }}>
        <button 
          className="btn-primary" 
          onClick={() => handleDispatch({append_to_doc: true, create_draft: false})} 
          disabled={isDispatchDisabled} 
          style={{ backgroundColor: "var(--accent-secondary)", fontSize: "0.95rem" }}
        >
          1. Append to Google Doc
        </button>
        <button 
          className="btn-primary" 
          onClick={() => handleDispatch({append_to_doc: false, create_draft: true})} 
          disabled={isDispatchDisabled} 
          style={{ backgroundColor: "#00d09c", fontSize: "0.95rem" }}
        >
          2. Generate Email Draft
        </button>
      </div>

      {lastRawText && (
        <div style={{ marginTop: "16px" }}>
          <label className="toggle-row" style={{ padding: "8px 12px", marginBottom: "12px", background: "rgba(0,0,0,0.03)", border: "1px solid var(--border-color)" }}>
            <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "var(--text-main)" }}>View Raw Draft Text</span>
            <label className="switch">
              <input type="checkbox" checked={showRawText} onChange={e => setShowRawText(e.target.checked)} />
              <span className="slider"></span>
            </label>
          </label>
          {showRawText && (
            <textarea 
              readOnly 
              value={lastRawText} 
              style={{ width: "100%", height: "200px", fontFamily: "monospace", fontSize: "0.85rem", padding: "12px", background: "#f8f9fa", color: "#333", border: "1px solid var(--border-color)", borderRadius: "var(--radius-sm)" }}
            />
          )}
        </div>
      )}
    </div>
  );
}

import { APIResponse, PulseTheme, PulseQuote, DispatchResult } from "@/types";

export default function OutputPreview({ data, isLoading, dispatchStatus }: { data: APIResponse | null, isLoading: boolean, dispatchStatus: DispatchResult | null }) {
  if (isLoading) {
    return (
      <div className="preview-pane">
        <div className="loader-overlay">
          <div className="empty-state">
            <div className="spinner"></div>
            <p style={{ marginTop: "24px", color: "var(--text-main)" }}>Processing via AI Engine...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="preview-pane">
        <div className="empty-state">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style={{ width: 64, height: 64, marginBottom: 16, color: "var(--accent)" }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          <p style={{ color: "var(--text-main)" }}>Ready. Configure settings and click Generate Report.</p>
        </div>
      </div>
    );
  }

  if (data.status === "error" || data.error) {
    return (
      <div className="preview-pane">
        <div style={{ color: "var(--danger)", padding: "24px", border: "1px solid var(--danger)", borderRadius: "var(--radius-sm)", background: "rgba(248, 81, 73, 0.1)" }}>
          <h3 style={{ margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: 8 }}>
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            Generation Failed
          </h3>
          <p style={{ margin: 0, fontFamily: "monospace", fontSize: "14px" }}>{data.error || "Unknown error occurred."}</p>
        </div>
      </div>
    );
  }

  const pulseResult = data.pulse;
  const explainerResult = data.explainer;

  return (
    <div className="preview-pane">
      {/* Top Bar Badges */}
      <div style={{ display: "flex", alignItems: "center", marginBottom: "32px", borderBottom: "1px solid var(--border-color)", paddingBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
        
        {dispatchStatus && dispatchStatus.status === "success" && (
          <>
            <div className={`badge ${dispatchStatus.results?.doc.status === 'error' ? 'provider' : ''}`} style={{ borderColor: dispatchStatus.results?.doc.status === 'error' ? 'var(--danger)' : '' }}>
              {dispatchStatus.results?.doc.status === 'skipped' ? '⏭️' : dispatchStatus.results?.doc.status === 'appended' ? '✅' : '❌'} Doc
            </div>
            <div className={`badge ${dispatchStatus.results?.draft.status === 'error' ? 'provider' : ''}`} style={{ borderColor: dispatchStatus.results?.draft.status === 'error' ? 'var(--danger)' : '' }}>
              {dispatchStatus.results?.draft.status === 'skipped' ? '⏭️' : dispatchStatus.results?.draft.status === 'created' ? '✅' : '❌'} Draft
            </div>
          </>
        )}
      </div>

      <div className="markdown-body">
        {pulseResult && (
          <>
            <h2 style={{ fontSize: "2rem", marginBottom: "8px", color: "var(--accent-secondary)" }}>Weekly Internal Pulse</h2>
            <p style={{ color: "var(--text-muted)", marginBottom: "32px", fontSize: "0.9rem" }}>
              Generated at {pulseResult.generated_at ? new Date(pulseResult.generated_at).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : "N/A"}
            </p>

            <p style={{ fontStyle: "italic", marginBottom: "24px", color: "var(--accent)" }}>{pulseResult.analysis_explanation}</p>
            <ul>
              {pulseResult.themes?.map((t: any, i: number) => (
                <li key={i}>
                  <strong>{t.name}</strong> — {t.review_count} reviews 
                  {t.percentage !== undefined && <span style={{ color: "var(--accent)", marginLeft: 8 }}>({t.percentage}%)</span>}
                  {t.average_rating !== undefined && <span style={{ color: "#fbbf24", marginLeft: 8 }}>★{t.average_rating}</span>}
                </li>
              ))}
            </ul>

            <div style={{ padding: "24px", background: "rgba(0, 208, 156, 0.03)", borderRadius: "12px", border: "1px solid rgba(0, 208, 156, 0.1)", marginBottom: "32px" }}>
              <h3 className="section-title" style={{ marginTop: 0 }}>Executive Intel Summary</h3>
              <div style={{ display: "flex", gap: "12px", marginBottom: "20px" }}>
                {pulseResult.top_3_themes?.map((t: string, i: number) => (
                  <div key={i} style={{ padding: "6px 14px", background: "var(--accent)", borderRadius: "20px", color: "white", fontSize: "0.85rem", fontWeight: "600" }}>
                    {t}
                  </div>
                ))}
              </div>
              <p style={{ fontSize: "1.1rem", lineHeight: "1.7", color: "var(--text-main)", margin: 0 }}>{pulseResult.summary}</p>
            </div>

            <h3 className="section-title">Raw Verbatim Quotes</h3>
            {pulseResult.quotes?.map((q: PulseQuote, i: number) => (
              <div key={i} className="quote-card">
                <span className="stars" style={{ color: "#fbbf24", marginRight: 8, fontWeight: "bold" }}>{"★".repeat(q.star_rating)}{"☆".repeat(5-q.star_rating)}</span>
                &quot;{q.text}&quot;
                <span style={{ display: "block", marginTop: "8px", fontSize: "0.8rem", color: "var(--text-muted)" }}>— {new Date(q.date).toLocaleDateString()}</span>
              </div>
            ))}

            <div style={{ padding: "24px", background: "rgba(139, 148, 158, 0.05)", borderRadius: "12px", marginBottom: "32px" }}>
              <h3 className="section-title" style={{ marginTop: 0 }}>Suggested Action Trackings</h3>
              <ul style={{ margin: 0, paddingLeft: "20px" }}>
                {pulseResult.action_ideas?.map((a: string, i: number) => (
                  <li key={i} style={{ marginBottom: "8px", color: "var(--text-main)" }}>{a}</li>
                ))}
              </ul>
            </div>
          </>
        )}

        {pulseResult && explainerResult && <hr style={{ margin: "40px 0", borderColor: "var(--border-color)" }} />}

        {explainerResult && (
          <>
            <h2 style={{ fontSize: "2rem", marginBottom: "8px", color: "var(--accent-secondary)" }}>Fee Explainer: {explainerResult.asset_class}</h2>
            <p style={{ color: "var(--text-muted)", marginBottom: "32px" }}>Zero-Hallucination Pipeline • Checked {explainerResult.last_checked ? new Date(explainerResult.last_checked).toLocaleDateString() : "N/A"}</p>

            <div style={{ background: "rgba(0, 208, 156, 0.05)", padding: "24px", borderRadius: "12px", border: "1px solid rgba(0, 208, 156, 0.2)", 
                          boxShadow: explainerResult.tone === "flagged_promotional" ? "0 0 0 2px var(--danger)" : "none" }}>
              
              {explainerResult.tone === "flagged_promotional" && (
                <div style={{ padding: "12px", background: "rgba(248,81,73,0.1)", color: "var(--danger)", borderRadius: "6px", marginBottom: "20px", fontWeight: "bold" }}>
                  ⚠️ Warning: Pipeline flagged promotional tone in LLM output.
                </div>
              )}

              <ul style={{ margin: 0 }}>
                {explainerResult.explanation_bullets?.map((bull: string, i: number) => (
                  <li key={i} style={{ paddingBottom: "12px", fontSize: "1.1rem" }}>{bull}</li>
                ))}
              </ul>
            </div>

            <h3 className="section-title">Official Sources Disclosed</h3>
            <ul>
              {explainerResult.official_links?.map((link: string, i: number) => (
                <li key={i}><a href={link} target="_blank" rel="noreferrer" style={{ textDecoration: "underline", color: "var(--accent-secondary)" }}>{link}</a></li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

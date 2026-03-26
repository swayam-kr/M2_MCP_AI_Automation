"use client";

import { useState } from "react";
import PartCGates from "@/components/PartCGates";
import OutputPreview from "@/components/OutputPreview";
import { APIResponse, DispatchResult } from "@/types";

export default function Home() {
  const [weeks, setWeeks] = useState(4);
  const [maxReviews, setMaxReviews] = useState(100);
  const [starMin, setStarMin] = useState(1);
  const [starMax, setStarMax] = useState(5);
  const [assetClass, setAssetClass] = useState("Stocks");

  const [combinedData, setCombinedData] = useState<APIResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState<DispatchResult | null>(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    setDispatchStatus(null);
    setCombinedData(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
      
      const [pulseRes, explainerRes] = await Promise.all([
        fetch(`${baseUrl}/api/pulse`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ weeks, max_reviews: maxReviews, star_range_min: starMin, star_range_max: starMax })
        }),
        fetch(`${baseUrl}/api/explainer`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ asset_class: assetClass })
        })
      ]);

      const pulseJson = await pulseRes.json();
      const explainerJson = await explainerRes.json();

      if (pulseJson.status === "error" || explainerJson.status === "error") {
        setCombinedData({
          status: "error",
          error: pulseJson.error || explainerJson.error
        });
      } else {
        setCombinedData({
          status: "success",
          pulse: pulseJson.data,
          explainer: explainerJson.data
        });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error occurred";
      setCombinedData({ status: "error", error: message });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="app-container">
      {/* Sidebar Controls */}
      <aside className="sidebar">
        <div style={{ padding: "24px", borderBottom: "1px solid var(--border-color)", display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ width: 40, height: 40, background: "var(--accent)", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 800, fontSize: "1.2rem" }}>G</div>
          <div>
            <h1 style={{ fontSize: "1.2rem", margin: 0, color: "var(--text-main)", fontWeight: 700 }}>Groww Weekly Digest</h1>
            <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--accent-secondary)", fontWeight: 500, letterSpacing: "0.02em" }}>Syncing User Sentiment with Operational Clarity</p>
          </div>
        </div>

        <div style={{ padding: "24px" }}>
          
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--accent-secondary)", fontWeight: 600 }}>1. Review Pulse Settings</h3>
            <div className="control-group">
              <label>Timeframe (Weeks): {weeks}</label>
              <input type="range" min="1" max="8" value={weeks} onChange={e => setWeeks(Number(e.target.value))} />
            </div>
            <div className="control-group">
              <label>Max Reviews: {maxReviews}</label>
              <input type="range" min="10" max="200" step="10" value={maxReviews} onChange={e => setMaxReviews(Number(e.target.value))} />
            </div>
            <div className="control-group">
              <label>Star Rating Range</label>
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <select value={starMin} onChange={e => setStarMin(Number(e.target.value))} style={{ flex: 1 }} className="form-select">
                  {[1,2,3,4,5].map(v => <option key={`min-${v}`} value={v}>{v} Star</option>)}
                </select>
                <span>to</span>
                <select value={starMax} onChange={e => setStarMax(Number(e.target.value))} style={{ flex: 1 }} className="form-select">
                  {[1,2,3,4,5].map(v => <option key={`max-${v}`} value={v}>{v} Star</option>)}
                </select>
              </div>
            </div>
          </div>

          <hr style={{ borderColor: "var(--border-color)", margin: "24px 0" }} />

          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--accent-secondary)", fontWeight: 600 }}>2. Fee Explainer Settings</h3>
            <div className="control-group">
              <label>Target Asset Class</label>
              <select 
                value={assetClass} 
                onChange={e => setAssetClass(e.target.value)}
                className="form-select"
                style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid var(--border-color)" }}
              >
                <option value="Stocks">Stocks / Equity</option>
                <option value="F&O">F&O (Futures & Options)</option>
                <option value="Mutual Funds">Mutual Funds</option>
              </select>
            </div>
          </div>

          <button 
            className="btn-primary w-full"
            onClick={handleGenerate} 
            disabled={isLoading}
            style={{ padding: "12px", fontSize: "1.05rem", fontWeight: "bold" }}
          >
            {isLoading ? "Generating..." : "Generate Full Report"}
          </button>

          <hr style={{ borderColor: "var(--border-color)", margin: "32px 0 24px 0" }} />

          <h3 style={{ fontSize: "1rem", marginBottom: 16, color: "var(--text-main)", fontWeight: 600 }}>3. Dispatch Report</h3>
          <PartCGates 
            activeContent={combinedData && combinedData.status !== "error" 
              ? { 
                  status: "success", 
                  pulse: combinedData.pulse, 
                  explainer: combinedData.explainer, 
                  generated_at: new Date().toISOString() 
                } 
              : null}
            contentType="combined"
            setIsLoading={setIsLoading}
            isLoading={isLoading}
            setDispatchStatus={setDispatchStatus}
          />
        </div>
      </aside>

      {/* Main Preview Panel */}
      <section className="main-content">
        <OutputPreview 
          data={combinedData}
          isLoading={isLoading}
          dispatchStatus={dispatchStatus}
        />
      </section>
    </main>
  );
}

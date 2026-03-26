"use client";

import { useState } from "react";
import { APIResponse, DispatchResult } from "@/types";

export default function PartAControls({ setResult, setIsLoading, isLoading, setDispatchStatus }: { 
  setResult: (res: APIResponse) => void, 
  setIsLoading: (loading: boolean) => void, 
  isLoading: boolean, 
  setDispatchStatus: (status: DispatchResult | null) => void 
}) {
  const [weeks, setWeeks] = useState(4);
  const [maxReviews, setMaxReviews] = useState(100);
  const [starMin, setStarMin] = useState(1);
  const [starMax, setStarMax] = useState(5);

  const handleGenerate = async () => {
    setIsLoading(true);
    setDispatchStatus(null);
    try {
      const res = await fetch("/api/pulse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ weeks, max_reviews: maxReviews, star_range_min: starMin, star_range_max: starMax }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
      setResult({ status: "error", error: "Failed to connect to backend" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h3 style={{ fontSize: "1rem", marginBottom: "16px" }}>Part A: Review Pulse</h3>
      
      <div className="control-group">
        <label>Time Window: {weeks} weeks</label>
        <input type="range" min="1" max="8" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} disabled={isLoading} />
      </div>

      <div className="control-group">
        <label>Max Reviews to Process</label>
        <input type="number" min="10" max="200" value={maxReviews} onChange={(e) => setMaxReviews(Number(e.target.value))} disabled={isLoading} />
      </div>

      <div className="control-group">
        <label>Star Range: {starMin} - {starMax}</label>
        <div style={{ display: "flex", gap: "10px" }}>
          <input type="number" min="1" max="5" value={starMin} onChange={(e) => setStarMin(Number(e.target.value))} disabled={isLoading} />
          <input type="number" min="1" max="5" value={starMax} onChange={(e) => setStarMax(Number(e.target.value))} disabled={isLoading} />
        </div>
      </div>

      <button className="btn-primary" onClick={handleGenerate} disabled={isLoading}>
        Generate Pulse
      </button>
    </div>
  );
}

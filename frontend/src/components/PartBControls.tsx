"use client";

import { useState } from "react";
import { APIResponse, DispatchResult } from "@/types";

export default function PartBControls({ setResult, setIsLoading, isLoading, setDispatchStatus }: { 
  setResult: (res: APIResponse) => void, 
  setIsLoading: (loading: boolean) => void, 
  isLoading: boolean, 
  setDispatchStatus: (status: DispatchResult | null) => void 
}) {
  const [assetClass, setAssetClass] = useState("Mutual Funds");

  const handleGenerate = async () => {
    setIsLoading(true);
    setDispatchStatus(null);
    try {
      const res = await fetch("/api/explainer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_class: assetClass }),
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
      <h3 style={{ fontSize: "1rem", marginBottom: "16px" }}>Part B: Fee Explainer</h3>
      
      <div className="control-group">
        <label>Asset Class Domain</label>
        <select value={assetClass} onChange={(e) => setAssetClass(e.target.value)} disabled={isLoading}>
          <option value="Stocks">Stocks</option>
          <option value="F&O">Futures & Options</option>
          <option value="Mutual Funds">Mutual Funds</option>
        </select>
      </div>

      <button className="btn-primary" onClick={handleGenerate} disabled={isLoading}>
        Extract Fees
      </button>
    </div>
  );
}

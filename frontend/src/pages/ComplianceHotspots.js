import React, { useState, useEffect } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function ComplianceHotspots() {
  const [hotspots, setHotspots] = useState([]);
  const [selectedState, setSelectedState] = useState("Maharashtra");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHotspots();
  }, []);

  const fetchHotspots = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/analytics/hotspots`, { withCredentials: true });
      setHotspots(res.data || []);
    } catch (e) {
      console.error("Hotspots error:", e);
    } finally {
      setLoading(false);
    }
  };

  const currentStateData = hotspots.find((h) => h.state === selectedState) || hotspots[0];

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header */}
      <div className="border-b border-gray-200 pb-5">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
            Geographic Surveillance
          </span>
          <span className="text-xs text-gray-500">• National Enforcement Hotspots</span>
        </div>
        <h1 className="text-2xl font-black text-[#001255] tracking-tight">Compliance Hotspots & Regional Analytics</h1>
        <p className="text-xs text-gray-600 mt-1">
          Cross-jurisdictional non-compliance risk indicators, high-frequency violation types, and zonal enforcement coverage.
        </p>
      </div>

      {/* Hotspot Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {hotspots.map((h, i) => (
          <div
            key={i}
            onClick={() => setSelectedState(h.state)}
            data-testid={`hotspot-card-${h.state.toLowerCase().replace(/\s+/g, "-")}`}
            className={`p-5 rounded-2xl border transition-all cursor-pointer shadow-sm relative overflow-hidden ${
              selectedState === h.state
                ? "bg-white border-[#E88A1E] ring-2 ring-amber-400"
                : "bg-white border-gray-100 hover:border-blue-300"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-sm text-[#001255]">{h.state}</span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                  h.risk_level === "High"
                    ? "bg-red-100 text-red-800"
                    : h.risk_level === "Medium"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-emerald-100 text-emerald-800"
                }`}
              >
                {h.risk_level} Risk
              </span>
            </div>

            <p className="text-xs text-gray-500 mb-3">{h.district}</p>

            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Compliance Rate:</span>
                <span className="font-bold text-emerald-600">{h.compliant_rate}%</span>
              </div>
              <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full"
                  style={{ width: `${h.compliant_rate}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-[11px] text-gray-500 pt-2 border-t border-gray-100 mt-2">
                <span>Top Issue:</span>
                <span className="font-medium text-red-600 truncate max-w-[150px]">{h.top_violation}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* State Detail Insight Panel */}
      {currentStateData && (
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <div>
              <h2 className="text-base font-bold text-[#001255]">
                Jurisdictional Breakdown: {currentStateData.state} ({currentStateData.district})
              </h2>
              <p className="text-xs text-gray-500">
                Surveillance coverage by {currentStateData.enforcement_officers} designated field inspectors
              </p>
            </div>
            <span
              className={`text-xs font-bold px-3 py-1 rounded-full ${
                currentStateData.risk_level === "High"
                  ? "bg-red-100 text-red-800"
                  : "bg-amber-100 text-amber-800"
              }`}
            >
              Priority Zone: {currentStateData.risk_level} Attention
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-1">
              <span className="text-gray-500 uppercase font-bold text-[10px]">Total Scans Conducted</span>
              <p className="text-2xl font-black text-[#001255]">{currentStateData.total_inspections.toLocaleString()}</p>
              <span className="text-gray-400">Retail & Supermarket checkpoints</span>
            </div>

            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-1">
              <span className="text-gray-500 uppercase font-bold text-[10px]">Non-Compliance Percentage</span>
              <p className="text-2xl font-black text-red-600">{currentStateData.violations_rate}%</p>
              <span className="text-gray-400">Flagged for Section 36 proceedings</span>
            </div>

            <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-1">
              <span className="text-gray-500 uppercase font-bold text-[10px]">Primary Violation Pattern</span>
              <p className="text-sm font-bold text-gray-900 mt-1">{currentStateData.top_violation}</p>
              <span className="text-gray-400">Statutory penalty under Rule 6 / 7</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
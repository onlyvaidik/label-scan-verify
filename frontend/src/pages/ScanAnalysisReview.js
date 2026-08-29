import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function ScanAnalysisReview() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [scanData, setScanData] = useState(null);
  const [declarations, setDeclarations] = useState({});
  const [showBoundingBoxes, setShowBoundingBoxes] = useState(true);
  const [activeRegion, setActiveRegion] = useState(null);
  const [inspectorNotes, setInspectorNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [savedCaseId, setSavedCaseId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const raw = sessionStorage.getItem("current_scan_data");
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        setScanData(parsed);
        setDeclarations(parsed.declarations || {});
      } catch (e) {
        console.error("Parse error:", e);
      }
    }
  }, []);

  if (!scanData) {
    return (
      <div className="p-8 text-center min-h-[calc(100vh-64px)] flex flex-col items-center justify-center bg-[#f5f7fb]">
        <div className="w-16 h-16 rounded-2xl bg-amber-100 text-[#E88A1E] flex items-center justify-center mb-4">
          <span className="material-symbols-outlined text-4xl">inventory_2</span>
        </div>
        <h2 className="text-xl font-bold text-[#001255]">No Active Scan Found</h2>
        <p className="text-xs text-gray-500 mt-1 mb-4">Please upload or select a packaged commodity first.</p>
        <button
          onClick={() => navigate("/new-scan")}
          data-testid="no-scan-goto-scan-btn"
          className="bg-[#E88A1E] text-white text-xs font-bold px-4 py-2 rounded-xl"
        >
          Start Product Scan
        </button>
      </div>
    );
  }

  const handleDeclarationChange = (field, value) => {
    setDeclarations((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleRecalculateAndSave = async () => {
    setSaving(true);
    setError("");
    setSaveSuccess(false);

    try {
      const payload = {
        id: scanData.id,
        brand_name: scanData.brand_name || declarations.commodity_name || "Scanned Product",
        commodity_name: declarations.commodity_name || scanData.commodity_name || "Commodity",
        category: scanData.category || "FMCG Packaged Food",
        barcode_gtin: scanData.barcode_gtin,
        image_url: scanData.image_url,
        panel_area_sq_cm: scanData.panel_area_sq_cm,
        numeral_height_mm: scanData.numeral_height_mm,
        letter_height_mm: scanData.letter_height_mm,
        declarations: declarations,
        ocr_raw_text: scanData.ocr_raw_text,
        label_regions: scanData.label_regions,
        inspector_notes: inspectorNotes
      };

      const res = await axios.post(`${BACKEND_URL}/api/scan/save`, payload, { withCredentials: true });
      setScanData(res.data);
      setSavedCaseId(res.data.id);
      setSaveSuccess(true);
      sessionStorage.setItem("current_scan_data", JSON.stringify(res.data));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save verification record.");
    } finally {
      setSaving(false);
    }
  };

  const isCompliant = scanData.compliance_status === "Compliant";

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              Interactive Verification
            </span>
            <span className="text-xs text-gray-500 font-mono">Engine: {scanData.engine_used || "Google Gemini 3 Flash Vision"}</span>
          </div>
          <h1 className="text-2xl font-black text-[#001255] tracking-tight flex items-center gap-3">
            <span>{scanData.brand_name || "Product Scan Analysis"}</span>
            <span
              className={`text-xs font-bold px-3 py-1 rounded-full ${
                isCompliant
                  ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                  : "bg-red-100 text-red-800 border border-red-300"
              }`}
            >
              {scanData.compliance_status} ({scanData.compliance_score}/100)
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-2">
          {savedCaseId && (
            <a
              href={`${BACKEND_URL}/api/reports/${savedCaseId}/pdf`}
              target="_blank"
              rel="noreferrer"
              data-testid="review-download-pdf-btn"
              className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow"
            >
              <span className="material-symbols-outlined text-base">picture_as_pdf</span>
              <span>Download Official PDF Report</span>
            </a>
          )}

          <button
            onClick={handleRecalculateAndSave}
            disabled={saving}
            data-testid="save-verification-btn"
            className="bg-[#001255] hover:bg-[#1a2f70] text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-base">
              {saving ? "progress_activity" : "verified"}
            </span>
            <span>{saving ? "Evaluating..." : "Certify & Save Record"}</span>
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div
          data-testid="save-success-alert"
          className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center justify-between"
        >
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-lg text-emerald-600">check_circle</span>
            <span>
              <b>Case Certified Successfully!</b> Case ID: <span className="font-mono">{savedCaseId}</span> recorded into national audit repository.
            </span>
          </div>
          <a
            href={`${BACKEND_URL}/api/reports/${savedCaseId}/pdf`}
            target="_blank"
            rel="noreferrer"
            className="font-bold underline text-emerald-900"
          >
            View Generated PDF
          </a>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs flex items-center gap-2">
          <span className="material-symbols-outlined text-base">error</span>
          <span>{error}</span>
        </div>
      )}

      {/* Split-View: Left Visual Inspector vs Right Declarations Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Image with Bounding Boxes (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                <span className="material-symbols-outlined text-base text-blue-600">crop_free</span>
                <span>Packaging Label Inspector</span>
              </span>
              <button
                onClick={() => setShowBoundingBoxes(!showBoundingBoxes)}
                data-testid="toggle-bounding-boxes-btn"
                className="text-xs font-semibold text-[#001255] bg-gray-100 px-2.5 py-1 rounded-lg hover:bg-gray-200 flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-xs">
                  {showBoundingBoxes ? "visibility" : "visibility_off"}
                </span>
                <span>{showBoundingBoxes ? "Hide Bounding Boxes" : "Show Bounding Boxes"}</span>
              </button>
            </div>

            {/* Visual Canvas Area */}
            <div className="relative w-full h-96 rounded-xl overflow-hidden bg-gray-900 flex items-center justify-center border border-gray-200">
              <img
                src={scanData.image_url || "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&auto=format&fit=crop&q=80"}
                alt="Product Label"
                className="max-h-full max-w-full object-contain"
              />

              {/* Bounding Boxes Layer */}
              {showBoundingBoxes &&
                scanData.label_regions?.map((r, i) => (
                  <div
                    key={i}
                    onClick={() => setActiveRegion(r)}
                    data-testid={`region-box-${i}`}
                    style={{
                      left: `${r.x}%`,
                      top: `${r.y}%`,
                      width: `${r.width}%`,
                      height: `${r.height}%`
                    }}
                    className={`absolute border-2 cursor-pointer transition-all rounded ${
                      activeRegion?.label === r.label
                        ? "border-amber-400 bg-amber-400/20 z-20 ring-2 ring-amber-300"
                        : "border-emerald-400/80 bg-emerald-400/10 hover:border-amber-400 hover:bg-amber-400/20"
                    }`}
                    title={`${r.label}: ${r.text}`}
                  >
                    <span className="absolute -top-4 left-0 text-[9px] font-bold bg-[#001255] text-white px-1 rounded shadow truncate max-w-[120px]">
                      {r.label}
                    </span>
                  </div>
                ))}
            </div>

            {/* Active Region Preview */}
            {activeRegion && (
              <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-xs">
                <span className="font-bold text-amber-900 block">{activeRegion.label}</span>
                <span className="text-gray-700 font-mono text-[11px]">{activeRegion.text}</span>
              </div>
            )}
          </div>

          {/* Table-II Font Size & PDP Analysis Card */}
          <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-[#001255] uppercase tracking-wider flex items-center gap-1.5">
              <span className="material-symbols-outlined text-base text-purple-600">format_size</span>
              <span>Table-II Font Size & PDP Verification</span>
            </h3>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-500 block text-[11px]">PDP Area</span>
                <span className="font-bold text-gray-900">{scanData.panel_area_sq_cm} sq. cm</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-500 block text-[11px]">OCR Confidence</span>
                <span className="font-bold text-emerald-600">{scanData.ocr_confidence || 94}%</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-500 block text-[11px]">Measured Numeral</span>
                <span className="font-bold text-[#001255]">{scanData.table_ii_font_check?.measured_numeral_height_mm || scanData.numeral_height_mm} mm</span>
                <span className="text-[10px] text-gray-500 block">(Req: {scanData.table_ii_font_check?.required_numeral_height_mm} mm)</span>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                <span className="text-gray-500 block text-[11px]">Measured Letter</span>
                <span className="font-bold text-[#001255]">{scanData.table_ii_font_check?.measured_letter_height_mm || scanData.letter_height_mm} mm</span>
                <span className="text-[10px] text-gray-500 block">(Req: {scanData.table_ii_font_check?.required_letter_height_mm} mm)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Rule 6 Mandatory Declarations Verification Form (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Violations List */}
          {scanData.violations && scanData.violations.length > 0 && (
            <div className="bg-red-50 rounded-2xl p-5 border border-red-200 space-y-2.5">
              <h3 className="text-xs font-bold text-red-900 uppercase tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-base text-red-600">gavel</span>
                <span>Statutory Violations Identified ({scanData.violations.length})</span>
              </h3>
              <div className="space-y-2">
                {scanData.violations.map((v, i) => (
                  <div key={i} className="p-3 bg-white rounded-xl border border-red-200 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-red-800">{v.section}: {v.title}</span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-100 text-red-800 uppercase">
                        {v.severity}
                      </span>
                    </div>
                    <p className="text-gray-600">{v.description}</p>
                    <p className="text-amber-800 font-medium text-[11px]">Remedy: {v.recommendation}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Declarations Form */}
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-sm font-bold text-[#001255] flex items-center gap-2">
                <span className="material-symbols-outlined text-emerald-600">fact_check</span>
                <span>Rule 6 Mandatory Declarations (Editable for Inspector Override)</span>
              </h3>
            </div>

            <div className="space-y-4 text-xs">
              {/* Manufacturer Name & Address */}
              <div className="space-y-2 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <label className="font-bold text-gray-800 uppercase tracking-wider block">
                  Rule 6(1)(a) Manufacturer Name & Address
                </label>
                <input
                  type="text"
                  data-testid="decl-mfg-name"
                  value={declarations.manufacturer_name || ""}
                  onChange={(e) => handleDeclarationChange("manufacturer_name", e.target.value)}
                  placeholder="Manufacturer Company Name"
                  className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                />
                <textarea
                  rows={2}
                  data-testid="decl-mfg-address"
                  value={declarations.manufacturer_address || ""}
                  onChange={(e) => handleDeclarationChange("manufacturer_address", e.target.value)}
                  placeholder="Complete Address with Street, City, State, and 6-digit PIN code"
                  className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                />
              </div>

              {/* Generic Name */}
              <div className="space-y-1 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <label className="font-bold text-gray-800 uppercase tracking-wider block">
                  Rule 6(1)(b) Generic / Common Commodity Name
                </label>
                <input
                  type="text"
                  data-testid="decl-commodity-name"
                  value={declarations.commodity_name || ""}
                  onChange={(e) => handleDeclarationChange("commodity_name", e.target.value)}
                  placeholder="e.g. Butter Cookies / Skin Cream"
                  className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                />
              </div>

              {/* Net Quantity & SI Unit */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <div>
                  <label className="font-bold text-gray-800 uppercase tracking-wider block mb-1">
                    Rule 6(1)(c) Net Quantity (Verbatim)
                  </label>
                  <input
                    type="text"
                    data-testid="decl-net-qty"
                    value={declarations.net_quantity_raw || declarations.net_quantity_value || ""}
                    onChange={(e) => handleDeclarationChange("net_quantity_raw", e.target.value)}
                    placeholder="e.g. Net Qty: 200 g"
                    className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="font-bold text-gray-800 uppercase tracking-wider block mb-1">
                    Rule 6(1)(da) Unit Sale Price (USP)
                  </label>
                  <input
                    type="text"
                    data-testid="decl-usp"
                    value={declarations.unit_sale_price || ""}
                    onChange={(e) => handleDeclarationChange("unit_sale_price", e.target.value)}
                    placeholder="e.g. ₹ 0.25 per g"
                    className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              {/* MRP & Tax Phrase */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <div>
                  <label className="font-bold text-gray-800 uppercase tracking-wider block mb-1">
                    Rule 6(1)(e) Maximum Retail Price (MRP)
                  </label>
                  <input
                    type="text"
                    data-testid="decl-mrp"
                    value={declarations.mrp_raw || declarations.mrp_value || ""}
                    onChange={(e) => handleDeclarationChange("mrp_raw", e.target.value)}
                    placeholder="MRP Rs. 150.00 (incl. of all taxes)"
                    className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="font-bold text-gray-800 uppercase tracking-wider block mb-1">
                    Rule 6(1)(d) Month & Year of Mfg / Pkd
                  </label>
                  <input
                    type="text"
                    data-testid="decl-mfg-date"
                    value={declarations.manufacturing_date || ""}
                    onChange={(e) => handleDeclarationChange("manufacturing_date", e.target.value)}
                    placeholder="MM/YYYY (e.g. 03/2026)"
                    className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              {/* Consumer Care & Origin */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-gray-50 p-3 rounded-xl border border-gray-100">
                <div>
                  <label className="font-bold text-gray-800 uppercase tracking-wider block mb-1">
                    Rule 6(1)(f) Consumer Helpline
                  </label>
                  <input
                    type="text"
                    data-testid="decl-consumer-phone"
                    value={declarations.consumer_care_phone || declarations.consumer_care_email || ""}
                    onChange={(e) => handleDeclarationChange("consumer_care_phone", e.target.value)}
                    placeholder="1800-425-4449 or care@company.in"
                    className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                  />
                </div>
                <div>
                  <label className="font-bold text-gray-800 uppercase tracking-wider block mb-1">
                    Rule 6(1)(g) Country of Origin
                  </label>
                  <input
                    type="text"
                    data-testid="decl-country-origin"
                    value={declarations.country_of_origin || ""}
                    onChange={(e) => handleDeclarationChange("country_of_origin", e.target.value)}
                    placeholder="Made in India"
                    className="w-full bg-white border border-gray-200 rounded-lg p-2 font-medium"
                  />
                </div>
              </div>

              {/* Inspector Remarks */}
              <div className="space-y-1">
                <label className="font-bold text-gray-800 uppercase tracking-wider block">
                  Field Inspector Endorsement / Observations
                </label>
                <textarea
                  rows={2}
                  data-testid="inspector-notes-input"
                  value={inspectorNotes}
                  onChange={(e) => setInspectorNotes(e.target.value)}
                  placeholder="Add notes, statutory directions, or physical sample seal number..."
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 text-xs"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
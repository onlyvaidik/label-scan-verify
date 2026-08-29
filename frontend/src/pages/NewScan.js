import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function NewScan() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [samples, setSamples] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [productHint, setProductHint] = useState("");
  const [category, setCategory] = useState("FMCG Packaged Food");
  const [panelArea, setPanelArea] = useState(140.0);
  const [loading, setLoading] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSamples();
  }, []);

  const fetchSamples = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/scan/samples`, { withCredentials: true });
      setSamples(res.data || []);
    } catch (e) {
      console.error("Samples load error:", e);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setSelectedImage(reader.result);
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSampleSelect = (sample) => {
    setImagePreview(sample.image_url);
    setSelectedImage(sample.image_url);
    setProductHint(sample.brand_name + " - " + sample.commodity_name);
    setCategory(sample.category);
    setPanelArea(sample.panel_area_sq_cm || 140.0);
    setError("");
  };

  const handleStartAnalysis = async () => {
    if (!selectedImage && !imagePreview) {
      setError("Please select an image or choose one of the pre-loaded sample packages.");
      return;
    }

    setError("");
    setLoading(true);
    setProgressStep(1); // Preprocessing

    // Convert URL to base64 if it's external or use directly
    let base64Payload = selectedImage;
    if (imagePreview && !imagePreview.startsWith("data:")) {
      try {
        const imgRes = await fetch(imagePreview);
        const blob = await imgRes.blob();
        base64Payload = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result);
          reader.readAsDataURL(blob);
        });
      } catch (e) {
        base64Payload = "data:image/jpeg;base64,mocksample";
      }
    }

    setTimeout(() => setProgressStep(2), 600); // OCR Detection
    setTimeout(() => setProgressStep(3), 1200); // Rule 6 Entity Extraction
    setTimeout(() => setProgressStep(4), 1800); // Table-II Font Size Calculation

    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/scan/analyze`,
        {
          image_base64: base64Payload,
          product_hint: productHint,
          category: category,
          panel_area_sq_cm: parseFloat(panelArea) || 140.0
        },
        { withCredentials: true }
      );

      // Save analysis state in session storage for immediate review
      sessionStorage.setItem("current_scan_data", JSON.stringify({
        ...res.data,
        image_url: imagePreview || "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&auto=format&fit=crop&q=80"
      }));

      navigate("/scan-review");
    } catch (err) {
      setError(err.response?.data?.detail || "AI Scanning pipeline encountered an issue. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              AI Vision & OCR Scanner
            </span>
            <span className="text-xs text-gray-500">• Rule 6 & Table-II Extraction</span>
          </div>
          <h1 className="text-3xl font-extrabold text-[#001255] tracking-tight">New Product Scan</h1>
          <p className="text-sm text-gray-600 mt-1">
            Upload packaging labels to automatically detect mandatory declarations, measure font height, and assess legal compliance.
          </p>
        </div>
      </div>

      {error && (
        <div
          data-testid="scan-error-alert"
          className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-3"
        >
          <span className="material-symbols-outlined text-xl text-red-500">error</span>
          <span>{error}</span>
        </div>
      )}

      {/* Sample Pre-loaded Products (For Instant One-Click Testing) */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-[#001255] flex items-center gap-2">
              <span className="material-symbols-outlined text-amber-500">flash_on</span>
              <span>Quick Test Samples (Instant Selection)</span>
            </h2>
            <p className="text-xs text-gray-500">Click any realistic test commodity to evaluate compliance rules immediately</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {samples.map((s, idx) => (
            <button
              key={idx}
              type="button"
              data-testid={`select-sample-${s.id}`}
              onClick={() => handleSampleSelect(s)}
              className={`text-left p-3.5 rounded-xl border transition-all flex flex-col justify-between ${
                imagePreview === s.image_url
                  ? "border-[#E88A1E] bg-amber-50/50 ring-2 ring-amber-400"
                  : "border-gray-200 hover:border-blue-400 bg-gray-50/50 hover:bg-white"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <img src={s.image_url} alt={s.brand_name} className="w-12 h-12 rounded-lg object-cover border border-gray-200" />
                <div className="overflow-hidden">
                  <span className="font-bold text-xs text-gray-900 block truncate">{s.brand_name}</span>
                  <span className="text-[11px] text-gray-500 block truncate">{s.category}</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-[11px] pt-2 border-t border-gray-200/50">
                <span className="font-mono text-gray-500">{s.id}</span>
                <span
                  className={`font-bold px-2 py-0.5 rounded ${
                    s.compliance_status === "Compliant"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-red-100 text-red-800"
                  }`}
                >
                  {s.compliance_status}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Upload & Parameters Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Image Upload & Viewport (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex flex-col items-center">
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              data-testid="file-upload-input"
              onChange={handleFileSelect}
              className="hidden"
            />

            {imagePreview ? (
              <div className="w-full relative group">
                <div className="w-full h-80 rounded-xl overflow-hidden border border-gray-200 bg-gray-900 flex items-center justify-center relative">
                  <img src={imagePreview} alt="Package Preview" className="max-h-full max-w-full object-contain" />
                  
                  {loading && (
                    <div className="absolute inset-0 bg-black/60 backdrop-blur-sm flex flex-col items-center justify-center text-white p-6 text-center">
                      <div className="w-12 h-12 border-4 border-amber-400 border-t-transparent rounded-full animate-spin mb-3"></div>
                      <h4 className="text-base font-bold">Scanning Package Label...</h4>
                      <p className="text-xs text-amber-300 mt-1">
                        {progressStep === 1 && "Step 1/4: Preprocessing & Noise Reduction..."}
                        {progressStep === 2 && "Step 2/4: Optical Character Recognition..."}
                        {progressStep === 3 && "Step 3/4: Rule 6 Mandatory Entity Extraction..."}
                        {progressStep === 4 && "Step 4/4: Table-II Font Height & Score Calculation..."}
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex justify-between items-center mt-3">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    data-testid="change-image-btn"
                    className="text-xs font-semibold text-[#001255] hover:underline flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">photo_camera</span>
                    <span>Change Package Photo</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setImagePreview("");
                      setSelectedImage(null);
                    }}
                    data-testid="remove-image-btn"
                    className="text-xs font-semibold text-red-600 hover:underline"
                  >
                    Clear Image
                  </button>
                </div>
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                data-testid="upload-dropzone"
                className="w-full h-80 border-2 border-dashed border-gray-300 hover:border-[#E88A1E] rounded-2xl flex flex-col items-center justify-center p-8 text-center cursor-pointer bg-gray-50/50 hover:bg-amber-50/20 transition-all group"
              >
                <div className="w-16 h-16 rounded-2xl bg-blue-50 group-hover:bg-amber-100 text-[#001255] group-hover:text-[#E88A1E] flex items-center justify-center mb-4 transition-colors">
                  <span className="material-symbols-outlined text-4xl">cloud_upload</span>
                </div>
                <h3 className="text-base font-bold text-gray-900">Upload Product Packaging Image</h3>
                <p className="text-xs text-gray-500 mt-1 max-w-sm">
                  Drag and drop JPEG, PNG, or WEBP photo of packaging label or click to browse.
                </p>
                <span className="mt-4 text-xs font-bold text-[#001255] bg-white px-4 py-2 rounded-xl border border-gray-200 shadow-sm">
                  Select Image File
                </span>
              </div>
            )}
          </div>

          {/* Capture Guidelines */}
          <div className="bg-blue-50/60 rounded-2xl p-5 border border-blue-100">
            <h4 className="text-xs font-bold text-[#001255] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <span className="material-symbols-outlined text-base text-blue-600">verified</span>
              <span>Optimal Scanning Guidelines</span>
            </h4>
            <ul className="text-xs text-gray-700 space-y-1.5 list-disc list-inside">
              <li>Ensure MRP, Net Weight, and Manufacturing Date are unobstructed in the frame.</li>
              <li>Avoid strong specular glare or camera flash over glossy packaging panels.</li>
              <li>Include full perimeter of the Principal Display Panel (PDP) for Table-II font measurement.</li>
            </ul>
          </div>
        </div>

        {/* Right Column: Scan Parameters & Trigger (5 Cols) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-[#001255] border-b border-gray-100 pb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-amber-500">tune</span>
              <span>Inspection Parameters</span>
            </h3>

            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                Product Commodity Hint (Optional)
              </label>
              <input
                type="text"
                data-testid="product-hint-input"
                value={productHint}
                onChange={(e) => setProductHint(e.target.value)}
                placeholder="e.g., Britannia Good Day Butter Biscuits"
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:border-[#001255]"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                Regulatory Commodity Category
              </label>
              <select
                data-testid="category-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:border-[#001255]"
              >
                <option value="FMCG Packaged Food">FMCG Packaged Food</option>
                <option value="Cosmetics & Personal Care">Cosmetics & Personal Care</option>
                <option value="Electronics & Appliances">Electronics & Appliances</option>
                <option value="Household Goods">Household Goods</option>
                <option value="Pharmaceuticals & Wellness">Pharmaceuticals & Wellness</option>
                <option value="Industrial & Institutional">Industrial & Institutional</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                Principal Display Panel (PDP) Area (sq. cm)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min="10"
                  max="5000"
                  data-testid="panel-area-input"
                  value={panelArea}
                  onChange={(e) => setPanelArea(e.target.value)}
                  className="w-32 bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:border-[#001255]"
                />
                <span className="text-xs text-gray-500">
                  {panelArea <= 50
                    ? "Bracket: ≤ 50 cm² (Min font 1.0mm)"
                    : panelArea <= 200
                    ? "Bracket: 50-200 cm² (Min font 2.0mm)"
                    : "Bracket: >200 cm² (Min font 4.0mm)"}
                </span>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-100">
              <button
                type="button"
                disabled={loading}
                data-testid="run-analysis-btn"
                onClick={handleStartAnalysis}
                className="w-full bg-[#E88A1E] hover:bg-[#d47b15] active:scale-[0.99] text-white font-bold py-3.5 rounded-xl shadow-lg shadow-amber-600/30 transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-xl">progress_activity</span>
                    <span>Running AI Vision Pipeline...</span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-xl">qr_code_scanner</span>
                    <span>Analyze Label & Check Compliance</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
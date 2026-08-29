import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function InspectionReports() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { id } = useParams();

  const [scans, setScans] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [jurisdiction, setJurisdiction] = useState("All");
  const [loading, setLoading] = useState(true);

  // Modal / Selected Report Detail
  const [selectedScan, setSelectedScan] = useState(null);
  const [actionNotes, setActionNotes] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  
  // Send Notice Modal
  const [showNoticeModal, setShowNoticeModal] = useState(false);
  const [noticeChannel, setNoticeChannel] = useState("email");
  const [noticeEmail, setNoticeEmail] = useState("");
  const [noticePhone, setNoticePhone] = useState("");
  const [noticeDeadlineDays, setNoticeDeadlineDays] = useState(15);
  const [noticeSending, setNoticeSending] = useState(false);
  const [noticeResult, setNoticeResult] = useState(null);
  const [noticeError, setNoticeError] = useState("");

  useEffect(() => {
    fetchScans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, category, statusFilter, jurisdiction]);

  useEffect(() => {
    if (id) {
      fetchSingleScan(id);
    }
  }, [id]);

  const fetchScans = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (category !== "All") params.category = category;
      if (statusFilter !== "All") params.status = statusFilter;
      if (jurisdiction !== "All") params.jurisdiction = jurisdiction;

      const res = await axios.get(`${BACKEND_URL}/api/scans`, {
        params,
        withCredentials: true
      });
      setScans(res.data.scans || []);
      setTotal(res.data.total || 0);
    } catch (e) {
      console.error("Fetch scans error:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchSingleScan = async (scanId) => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/scans/${scanId}`, { withCredentials: true });
      setSelectedScan(res.data);
    } catch (e) {
      console.error("Single scan error:", e);
    }
  };

  const handlePerformAction = async (actionType) => {
    if (!selectedScan) return;
    setActionLoading(true);
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/scans/${selectedScan.id}/action`,
        { action: actionType, notes: actionNotes },
        { withCredentials: true }
      );
      setSelectedScan(res.data);
      setActionNotes("");
      fetchScans();
    } catch (e) {
      console.error("Action error:", e);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExportCSV = () => {
    window.open(`${BACKEND_URL}/api/reports/export/csv`, "_blank");
  };

  const openNoticeModal = () => {
    if (!selectedScan) return;
    setNoticeEmail(selectedScan.declarations?.consumer_care_email || "");
    setNoticePhone(selectedScan.declarations?.consumer_care_phone || "");
    setNoticeChannel("email");
    setNoticeResult(null);
    setNoticeError("");
    setShowNoticeModal(true);
  };

  const handleSendNotice = async () => {
    if (!selectedScan) return;
    setNoticeSending(true);
    setNoticeError("");
    setNoticeResult(null);
    try {
      const payload = {
        channel: noticeChannel,
        reply_deadline_days: parseInt(noticeDeadlineDays) || 15
      };
      if (noticeChannel === "email" || noticeChannel === "both") payload.recipient_email = noticeEmail;
      if (noticeChannel === "sms" || noticeChannel === "both") payload.recipient_phone = noticePhone;
      const res = await axios.post(
        `${BACKEND_URL}/api/scans/${selectedScan.id}/send-notice`,
        payload,
        { withCredentials: true }
      );
      setNoticeResult(res.data);
      fetchSingleScan(selectedScan.id);
      fetchScans();
    } catch (e) {
      const d = e.response?.data?.detail;
      setNoticeError(typeof d === "string" ? d : (d?.message || "Failed to send notice."));
    } finally {
      setNoticeSending(false);
    }
  };

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              Inspection Repository
            </span>
            <span className="text-xs text-gray-500">• {total} Recorded Cases</span>
          </div>
          <h1 className="text-2xl font-black text-[#001255] tracking-tight">Inspection Reports & Case Registry</h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            data-testid="reports-export-csv-btn"
            className="bg-white border border-gray-300 hover:bg-gray-50 text-[#001255] font-semibold text-xs px-3.5 py-2 rounded-xl shadow-sm flex items-center gap-1.5"
          >
            <span className="material-symbols-outlined text-base">download</span>
            <span>Export CSV</span>
          </button>
          <button
            onClick={() => navigate("/new-scan")}
            data-testid="reports-new-scan-btn"
            className="bg-[#E88A1E] hover:bg-[#d47b15] text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow"
          >
            <span className="material-symbols-outlined text-base">qr_code_scanner</span>
            <span>New Scan</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">Search Cases</label>
          <div className="relative">
            <span className="absolute left-2.5 top-2 material-symbols-outlined text-sm text-gray-400">search</span>
            <input
              type="text"
              data-testid="reports-search-input"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search Brand, Barcode, Case ID..."
              className="w-full bg-gray-50 border border-gray-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-gray-800"
            />
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">Category</label>
          <select
            data-testid="reports-category-filter"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 text-xs text-gray-800"
          >
            <option value="All">All Categories</option>
            <option value="FMCG Packaged Food">FMCG Packaged Food</option>
            <option value="Cosmetics & Personal Care">Cosmetics & Personal Care</option>
            <option value="Electronics & Appliances">Electronics & Appliances</option>
            <option value="Household Goods">Household Goods</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">Compliance Status</label>
          <select
            data-testid="reports-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 text-xs text-gray-800"
          >
            <option value="All">All Statuses</option>
            <option value="Compliant">Compliant</option>
            <option value="Non-Compliant">Non-Compliant</option>
            <option value="Partially Compliant">Partially Compliant</option>
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">Jurisdiction / Zone</label>
          <select
            data-testid="reports-jurisdiction-filter"
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 text-xs text-gray-800"
          >
            <option value="All">All Jurisdictions</option>
            <option value="New Delhi Central">New Delhi Central</option>
            <option value="Maharashtra Zone 1">Maharashtra Zone 1</option>
            <option value="Delhi NCR">Delhi NCR</option>
            <option value="National">National Central</option>
          </select>
        </div>
      </div>

      {/* Table of Scans */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-gray-500 text-xs flex items-center justify-center gap-2">
            <span className="material-symbols-outlined animate-spin text-lg">progress_activity</span>
            <span>Loading inspection repository...</span>
          </div>
        ) : scans.length === 0 ? (
          <div className="p-12 text-center text-gray-500 text-xs">
            No inspection cases found matching filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse" data-testid="inspection-reports-table">
              <thead>
                <tr className="border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500 bg-gray-50/50">
                  <th className="py-3 px-4 font-bold">Case ID</th>
                  <th className="py-3 px-4 font-bold">Product / Brand</th>
                  <th className="py-3 px-4 font-bold">Category</th>
                  <th className="py-3 px-4 font-bold">Status</th>
                  <th className="py-3 px-4 font-bold">Score</th>
                  <th className="py-3 px-4 font-bold">Violations</th>
                  <th className="py-3 px-4 font-bold">Inspector</th>
                  <th className="py-3 px-4 font-bold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 text-xs">
                {scans.map((s) => {
                  const isComp = s.compliance_status === "Compliant";
                  return (
                    <tr key={s.id} className="hover:bg-blue-50/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-[#001255]">{s.id}</td>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        <div className="font-bold">{s.brand_name}</div>
                        <div className="text-[11px] text-gray-400">{s.commodity_name}</div>
                      </td>
                      <td className="py-3 px-4 text-gray-600">{s.category}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 font-bold px-2 py-0.5 rounded-full ${
                            isComp
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-red-50 text-red-700 border border-red-200"
                          }`}
                        >
                          {s.compliance_status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold">
                        <span className={isComp ? "text-emerald-700" : "text-red-600"}>
                          {s.compliance_score} / 100
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {s.violations_count > 0 ? (
                          <span className="font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded">
                            {s.violations_count} violations
                          </span>
                        ) : (
                          <span className="text-emerald-600 font-semibold">None</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-600">{s.inspector_name}</td>
                      <td className="py-3 px-4 text-right space-x-1.5">
                        <button
                          onClick={() => setSelectedScan(s)}
                          data-testid={`view-detail-${s.id}`}
                          className="px-2.5 py-1 rounded bg-[#001255] hover:bg-[#1a2f70] text-white font-semibold"
                        >
                          View Case
                        </button>
                        <a
                          href={`${BACKEND_URL}/api/reports/${s.id}/pdf`}
                          target="_blank"
                          rel="noreferrer"
                          data-testid={`download-pdf-${s.id}`}
                          className="px-2 py-1 rounded bg-red-50 text-red-700 font-semibold border border-red-200 inline-flex items-center gap-1"
                        >
                          <span className="material-symbols-outlined text-xs">picture_as_pdf</span>
                          PDF
                        </a>
                        <a
                          href={`${BACKEND_URL}/api/reports/${s.id}/docx`}
                          target="_blank"
                          rel="noreferrer"
                          data-testid={`download-docx-${s.id}`}
                          className="px-2 py-1 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200 inline-flex items-center gap-1"
                        >
                          <span className="material-symbols-outlined text-xs">description</span>
                          DOCX
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Selected Report Case Detail Modal */}
      {selectedScan && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-100 p-6 space-y-6">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-gray-200 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-[#001255] bg-blue-50 px-2 py-0.5 rounded">
                    {selectedScan.id}
                  </span>
                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                      selectedScan.compliance_status === "Compliant"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {selectedScan.compliance_status} ({selectedScan.compliance_score}/100)
                  </span>
                </div>
                <h2 className="text-xl font-black text-[#001255] mt-1">{selectedScan.brand_name}</h2>
                <p className="text-xs text-gray-500">{selectedScan.commodity_name} • GTIN: {selectedScan.barcode_gtin}</p>
              </div>
              <button
                onClick={() => setSelectedScan(null)}
                data-testid="close-case-modal-btn"
                className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>

            {/* Content Columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              {/* Left Column: Declarations & Product info */}
              <div className="space-y-4">
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-100 space-y-2">
                  <h4 className="font-bold text-[#001255] uppercase tracking-wider">Product Identification</h4>
                  <p><b>Brand:</b> {selectedScan.brand_name}</p>
                  <p><b>Category:</b> {selectedScan.category}</p>
                  <p><b>Inspector:</b> {selectedScan.inspector_name} ({selectedScan.inspector_id})</p>
                  <p><b>Jurisdiction:</b> {selectedScan.jurisdiction}</p>
                  <p><b>Inspection Date:</b> {selectedScan.created_at?.slice(0, 19)}</p>
                </div>

                <div className="bg-gray-50 p-4 rounded-xl border border-gray-100 space-y-2">
                  <h4 className="font-bold text-[#001255] uppercase tracking-wider">Rule 6 Declarations</h4>
                  <p><b>Manufacturer:</b> {selectedScan.declarations?.manufacturer_name || "N/A"}</p>
                  <p><b>Address:</b> {selectedScan.declarations?.manufacturer_address || "N/A"}</p>
                  <p><b>Net Quantity:</b> {selectedScan.declarations?.net_quantity_raw || selectedScan.declarations?.net_quantity_value || "N/A"}</p>
                  <p><b>Unit Sale Price:</b> {selectedScan.declarations?.unit_sale_price || "Not Declared"}</p>
                  <p><b>MRP:</b> {selectedScan.declarations?.mrp_raw || selectedScan.declarations?.mrp_value || "N/A"}</p>
                  <p><b>Mfg Date:</b> {selectedScan.declarations?.manufacturing_date || "N/A"}</p>
                  <p><b>Consumer Care:</b> {selectedScan.declarations?.consumer_care_phone || selectedScan.declarations?.consumer_care_email || "N/A"}</p>
                  <p><b>Country of Origin:</b> {selectedScan.declarations?.country_of_origin || "N/A"}</p>
                </div>
              </div>

              {/* Right Column: Violations, Table-II, and Actions */}
              <div className="space-y-4">
                {selectedScan.violations?.length > 0 ? (
                  <div className="bg-red-50 p-4 rounded-xl border border-red-200 space-y-2">
                    <h4 className="font-bold text-red-900 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">gavel</span>
                      <span>Violations Identified ({selectedScan.violations.length})</span>
                    </h4>
                    {selectedScan.violations.map((v, idx) => (
                      <div key={idx} className="p-2.5 bg-white rounded-lg border border-red-200 space-y-1">
                        <span className="font-bold text-red-800">{v.section}: {v.title}</span>
                        <p className="text-gray-600">{v.description}</p>
                        <p className="text-amber-800 font-medium">Penalty: {v.penalty_clause}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-emerald-50 p-4 rounded-xl border border-emerald-200 text-emerald-800 font-bold">
                    ✓ Fully Compliant under Legal Metrology Rules, 2011.
                  </div>
                )}

                {/* Enforcement Officer Actions */}
                <div className="bg-blue-50/60 p-4 rounded-xl border border-blue-100 space-y-3">
                  <h4 className="font-bold text-[#001255] uppercase tracking-wider">Enforcement Actions</h4>
                  <textarea
                    rows={2}
                    data-testid="case-action-notes"
                    value={actionNotes}
                    onChange={(e) => setActionNotes(e.target.value)}
                    placeholder="Enter statutory notice directions or testing instructions..."
                    className="w-full bg-white border border-blue-200 rounded-lg p-2 text-xs"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={openNoticeModal}
                      disabled={actionLoading}
                      data-testid="action-send-notice-btn"
                      className="bg-red-700 hover:bg-red-800 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-xs">forward_to_inbox</span>
                      Send Notice (Email/SMS)
                    </button>
                    <button
                      onClick={() => handlePerformAction("issue_notice")}
                      disabled={actionLoading}
                      data-testid="action-issue-notice-btn"
                      className="bg-red-600 hover:bg-red-700 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-xs">gavel</span>
                      Issue Sec 36 Notice
                    </button>
                    <button
                      onClick={() => handlePerformAction("flag_lab_test")}
                      disabled={actionLoading}
                      data-testid="action-flag-lab-btn"
                      className="bg-[#E88A1E] hover:bg-[#d47b15] text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-xs">biotech</span>
                      Flag for Lab Test
                    </button>
                    <button
                      onClick={() => handlePerformAction("mark_verified")}
                      disabled={actionLoading}
                      data-testid="action-mark-verified-btn"
                      className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-xs">check</span>
                      Mark Verified
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="border-t border-gray-200 pt-4 flex justify-between items-center">
              <div className="space-x-2">
                <a
                  href={`${BACKEND_URL}/api/reports/${selectedScan.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="modal-download-pdf-btn"
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-xs rounded-xl inline-flex items-center gap-1.5 shadow"
                >
                  <span className="material-symbols-outlined text-sm">picture_as_pdf</span>
                  Download PDF Report
                </a>
                <a
                  href={`${BACKEND_URL}/api/reports/${selectedScan.id}/docx`}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="modal-download-docx-btn"
                  className="px-4 py-2 bg-[#001255] hover:bg-[#1a2f70] text-white font-bold text-xs rounded-xl inline-flex items-center gap-1.5 shadow"
                >
                  <span className="material-symbols-outlined text-sm">description</span>
                  Download DOCX
                </a>
              </div>
              <button
                onClick={() => setSelectedScan(null)}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Send Notice Modal */}
      {showNoticeModal && selectedScan && (
        <div
          data-testid="notice-modal"
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
        >
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-gray-200 pb-3">
              <div>
                <h3 className="text-base font-bold text-[#001255] flex items-center gap-2">
                  <span className="material-symbols-outlined text-red-600">forward_to_inbox</span>
                  <span>Serve Section 36 Notice</span>
                </h3>
                <p className="text-[11px] text-gray-500">Case: {selectedScan.id} • {selectedScan.brand_name}</p>
              </div>
              <button
                onClick={() => setShowNoticeModal(false)}
                data-testid="close-notice-modal-btn"
                className="p-1 text-gray-400 hover:text-gray-700"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {noticeResult ? (
              <div className="space-y-3">
                <div
                  data-testid="notice-success-alert"
                  className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs"
                >
                  <div className="flex items-center gap-2 font-bold mb-1">
                    <span className="material-symbols-outlined text-base">check_circle</span>
                    <span>Notice {noticeResult.notice_number} dispatched</span>
                  </div>
                  <p className="text-emerald-800 text-[11px]">Reply deadline: {noticeResult.reply_deadline}</p>
                </div>

                {noticeResult.deliveries?.map((d, i) => (
                  <div key={i} className="p-2.5 bg-blue-50 border border-blue-100 rounded-lg text-[11px]">
                    <b className="text-blue-900">{d.channel.toUpperCase()} via {d.provider}</b> — status:{" "}
                    <span className="font-mono text-emerald-700">{d.status}</span> to <code>{d.recipient}</code>
                    <div className="text-gray-500 text-[10px]">Msg ID: {d.provider_message_id}</div>
                  </div>
                ))}

                {noticeResult.errors?.length > 0 && noticeResult.errors.map((err, i) => (
                  <div key={i} className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900">
                    <b>{err.channel.toUpperCase()}</b> failed: {err.error}
                  </div>
                ))}

                <button
                  onClick={() => setShowNoticeModal(false)}
                  data-testid="close-notice-success-btn"
                  className="w-full bg-[#001255] hover:bg-[#1a2f70] text-white font-bold py-2.5 rounded-xl text-sm"
                >
                  Done
                </button>
              </div>
            ) : (
              <>
                {noticeError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs">
                    {noticeError}
                  </div>
                )}

                <div>
                  <label className="block text-[11px] font-bold text-gray-600 uppercase mb-1.5">Channel</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { v: "email", l: "Email", i: "mail" },
                      { v: "sms", l: "SMS", i: "sms" },
                      { v: "both", l: "Both", i: "campaign" }
                    ].map((c) => (
                      <button
                        key={c.v}
                        type="button"
                        data-testid={`notice-channel-${c.v}`}
                        onClick={() => setNoticeChannel(c.v)}
                        className={`px-3 py-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 border transition-all ${
                          noticeChannel === c.v
                            ? "bg-[#001255] text-white border-[#001255]"
                            : "bg-white border-gray-200 text-gray-700 hover:border-blue-400"
                        }`}
                      >
                        <span className="material-symbols-outlined text-sm">{c.i}</span>
                        {c.l}
                      </button>
                    ))}
                  </div>
                </div>

                {(noticeChannel === "email" || noticeChannel === "both") && (
                  <div>
                    <label className="block text-[11px] font-bold text-gray-600 uppercase mb-1.5">Recipient Email</label>
                    <input
                      type="email"
                      data-testid="notice-email-input"
                      value={noticeEmail}
                      onChange={(e) => setNoticeEmail(e.target.value)}
                      placeholder="seller@company.com"
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm"
                    />
                  </div>
                )}

                {(noticeChannel === "sms" || noticeChannel === "both") && (
                  <div>
                    <label className="block text-[11px] font-bold text-gray-600 uppercase mb-1.5">Recipient Phone (E.164)</label>
                    <input
                      type="tel"
                      data-testid="notice-phone-input"
                      value={noticePhone}
                      onChange={(e) => setNoticePhone(e.target.value)}
                      placeholder="+919812345678"
                      className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm"
                    />
                    <p className="text-[10px] text-gray-400 mt-1">Include country code. India: +91xxxxxxxxxx</p>
                  </div>
                )}

                <div>
                  <label className="block text-[11px] font-bold text-gray-600 uppercase mb-1.5">Reply Deadline (days)</label>
                  <input
                    type="number"
                    min="1"
                    max="90"
                    data-testid="notice-deadline-input"
                    value={noticeDeadlineDays}
                    onChange={(e) => setNoticeDeadlineDays(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-sm"
                  />
                </div>

                <div className="p-2.5 bg-amber-50/60 border border-amber-200 rounded-lg text-[11px] text-amber-900">
                  <b>The notice will include:</b> case ID, all detected violations, remedy directions,
                  Section 36 penalty clauses, official signature block, and a strict {noticeDeadlineDays}-day reply window.
                </div>

                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => setShowNoticeModal(false)}
                    className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold py-2.5 rounded-xl text-sm"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSendNotice}
                    disabled={noticeSending}
                    data-testid="send-notice-submit-btn"
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    {noticeSending ? (
                      <>
                        <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
                        <span>Dispatching...</span>
                      </>
                    ) : (
                      <>
                        <span className="material-symbols-outlined text-base">send</span>
                        <span>Serve Notice Now</span>
                      </>
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
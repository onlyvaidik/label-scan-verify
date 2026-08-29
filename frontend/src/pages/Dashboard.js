import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/dashboard/stats`, { withCredentials: true });
      setStats(res.data);
    } catch (e) {
      console.error("Dashboard stats error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    window.open(`${BACKEND_URL}/api/reports/export/csv`, "_blank");
  };

  return (
    <div className="p-8 space-y-8 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              National Enforcement Grid
            </span>
            <span className="text-xs text-gray-500">• Rule 6 & Table-II Surveillance</span>
          </div>
          <h1 className="text-3xl font-extrabold text-[#001255] tracking-tight">Compliance Dashboard</h1>
          <p className="text-sm text-gray-600 mt-1">
            Real-time monitoring of packaged commodity declarations, OCR accuracy, and statutory violations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            data-testid="dashboard-export-csv-btn"
            className="bg-white border border-gray-300 hover:bg-gray-50 text-[#001255] font-semibold text-sm px-4 py-2.5 rounded-xl shadow-sm flex items-center gap-2 transition-all"
          >
            <span className="material-symbols-outlined text-lg">download</span>
            <span>Export Inspection CSV</span>
          </button>

          <button
            onClick={() => navigate("/new-scan")}
            data-testid="dashboard-start-scan-btn"
            className="bg-[#E88A1E] hover:bg-[#d47b15] text-white font-bold text-sm px-5 py-2.5 rounded-xl shadow-lg shadow-amber-500/20 flex items-center gap-2 transition-all transform hover:-translate-y-0.5"
          >
            <span className="material-symbols-outlined text-xl">qr_code_scanner</span>
            <span>Start New Product Scan</span>
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Card 1: Total Scans */}
        <div
          data-testid="metric-total-scans"
          className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm relative overflow-hidden group hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Total Inspections</span>
            <span className="p-2 bg-blue-50 text-[#001255] rounded-xl material-symbols-outlined text-xl">
              assignment
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-[#001255]">{stats?.total_scans || 0}</span>
            <span className="text-xs font-semibold text-emerald-600 flex items-center bg-emerald-50 px-1.5 py-0.5 rounded">
              <span className="material-symbols-outlined text-xs">trending_up</span> +12.4%
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-2">Active cases in repository</p>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-[#001255]"></div>
        </div>

        {/* Card 2: Compliant Rate */}
        <div
          data-testid="metric-compliant-rate"
          className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm relative overflow-hidden group hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Compliant Packages</span>
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-xl material-symbols-outlined text-xl">
              check_circle
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-emerald-600">{stats?.compliant_count || 0}</span>
            <span className="text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
              {stats?.compliance_rate || 0}%
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-2">Fully meet LMPC Rules, 2011</p>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-emerald-500"></div>
        </div>

        {/* Card 3: Non-Compliant */}
        <div
          data-testid="metric-violations-count"
          className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm relative overflow-hidden group hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Violations Detected</span>
            <span className="p-2 bg-red-50 text-red-600 rounded-xl material-symbols-outlined text-xl">
              warning
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-red-600">{stats?.non_compliant_count || 0}</span>
            <span className="text-xs font-semibold text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
              Requires Legal Notice
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-2">Missing declarations or defective units</p>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-red-500"></div>
        </div>

        {/* Card 4: Notices Issued */}
        <div
          data-testid="metric-notices-issued"
          className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm relative overflow-hidden group hover:shadow-md transition-all"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Sec 36 Notices</span>
            <span className="p-2 bg-amber-50 text-[#E88A1E] rounded-xl material-symbols-outlined text-xl">
              gavel
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-[#E88A1E]">{stats?.notices_issued || 0}</span>
            <span className="text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded">
              Active Proceedings
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-2">Section 36 penalty actions</p>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-[#E88A1E]"></div>
        </div>
      </div>

      {/* Two-Column Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Breakdown */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-base font-bold text-[#001255] mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-blue-600 text-lg">category</span>
            <span>Category Compliance Rate</span>
          </h3>
          <div className="space-y-4">
            {stats?.category_stats?.map((cat, idx) => (
              <div key={idx} className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span className="text-gray-700">{cat._id}</span>
                  <span className="text-gray-500">
                    {cat.count} scans ({cat.count - cat.non_compliant} compliant)
                  </span>
                </div>
                <div className="w-full bg-gray-100 h-2.5 rounded-full overflow-hidden">
                  <div
                    className="bg-[#001255] h-full rounded-full transition-all"
                    style={{ width: `${Math.max(15, ((cat.count - cat.non_compliant) / cat.count) * 100)}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Violation Distribution */}
        <div className="lg:col-span-2 bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-base font-bold text-[#001255] mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-red-500 text-lg">error_outline</span>
            <span>Common Statutory Violations (LMPC Rules, 2011)</span>
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {stats?.violation_chart_data && stats.violation_chart_data.length > 0 ? (
              stats.violation_chart_data.map((v, i) => (
                <div key={i} className="p-3.5 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-gray-800 block">{v.name}</span>
                    <span className="text-[11px] text-gray-500">Rule 6 / Table-II</span>
                  </div>
                  <span className="text-sm font-black text-red-600 bg-red-50 px-2.5 py-1 rounded-lg border border-red-100">
                    {v.count} cases
                  </span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-400 col-span-2">No statutory violations recorded yet.</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Inspection Records Table */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold text-[#001255]">Recent Product Inspections</h2>
            <p className="text-xs text-gray-500">Latest scans verified by Field Officers</p>
          </div>
          <button
            onClick={() => navigate("/reports")}
            data-testid="dashboard-view-all-reports-btn"
            className="text-xs font-bold text-[#E88A1E] hover:underline flex items-center gap-1"
          >
            <span>View All Repository Cases</span>
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse" data-testid="recent-scans-table">
            <thead>
              <tr className="border-b border-gray-200 text-xs uppercase tracking-wider text-gray-500 bg-gray-50/50">
                <th className="py-3 px-4 font-bold">Case ID</th>
                <th className="py-3 px-4 font-bold">Product / Brand</th>
                <th className="py-3 px-4 font-bold">Category</th>
                <th className="py-3 px-4 font-bold">Compliance Status</th>
                <th className="py-3 px-4 font-bold">Score</th>
                <th className="py-3 px-4 font-bold">Inspector</th>
                <th className="py-3 px-4 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              {stats?.recent_scans?.map((scan) => {
                const isCompliant = scan.compliance_status === "Compliant";
                return (
                  <tr key={scan.id} className="hover:bg-blue-50/30 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-xs text-[#001255]">
                      {scan.id}
                    </td>
                    <td className="py-3 px-4 font-medium text-gray-900">
                      <div>{scan.brand_name}</div>
                      <div className="text-xs text-gray-400">{scan.commodity_name}</div>
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-600">{scan.category}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full ${
                          isCompliant
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : "bg-red-50 text-red-700 border border-red-200"
                        }`}
                      >
                        <span className="material-symbols-outlined text-sm">
                          {isCompliant ? "check_circle" : "cancel"}
                        </span>
                        {scan.compliance_status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-xs">
                      <span className={isCompliant ? "text-emerald-700" : "text-red-600"}>
                        {scan.compliance_score} / 100
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-600">{scan.inspector_name}</td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        onClick={() => navigate(`/reports/${scan.id}`)}
                        data-testid={`view-scan-${scan.id}`}
                        className="px-2.5 py-1 rounded bg-[#001255] hover:bg-[#1a2f70] text-white text-xs font-semibold"
                      >
                        Inspect
                      </button>
                      <a
                        href={`${BACKEND_URL}/api/reports/${scan.id}/pdf`}
                        target="_blank"
                        rel="noreferrer"
                        data-testid={`download-pdf-${scan.id}`}
                        className="px-2.5 py-1 rounded bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold border border-red-200 inline-flex items-center gap-1"
                      >
                        <span className="material-symbols-outlined text-xs">picture_as_pdf</span>
                        PDF
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
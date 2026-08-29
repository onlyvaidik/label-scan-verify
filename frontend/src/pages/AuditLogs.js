import React, { useState, useEffect } from "react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const fetchAuditLogs = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/audit-logs`, { withCredentials: true });
      setLogs(res.data || []);
    } catch (e) {
      console.error("Audit logs error:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header */}
      <div className="border-b border-gray-200 pb-5">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
            Statutory Integrity
          </span>
          <span className="text-xs text-gray-500">• Immutable Security & Enforcement Trails</span>
        </div>
        <h1 className="text-2xl font-black text-[#001255] tracking-tight">Inspection History & Audit Log</h1>
        <p className="text-xs text-gray-600 mt-1">
          Cryptographic and timestamped trail of all packaging scans, officer overrides, legal notices, and logins.
        </p>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-gray-500 text-xs">Loading audit records...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs" data-testid="audit-logs-table">
              <thead>
                <tr className="border-b border-gray-200 text-gray-500 uppercase bg-gray-50/50">
                  <th className="py-3 px-4 font-bold">Timestamp (UTC)</th>
                  <th className="py-3 px-4 font-bold">Officer / User</th>
                  <th className="py-3 px-4 font-bold">Action Event</th>
                  <th className="py-3 px-4 font-bold">Entity Type</th>
                  <th className="py-3 px-4 font-bold">Entity ID</th>
                  <th className="py-3 px-4 font-bold">Details</th>
                  <th className="py-3 px-4 font-bold">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-mono">
                {logs.map((l, i) => (
                  <tr key={i} className="hover:bg-blue-50/20 transition-colors">
                    <td className="py-3 px-4 text-gray-500">{l.timestamp?.slice(0, 19)}</td>
                    <td className="py-3 px-4 font-sans font-bold text-[#001255]">{l.user_email}</td>
                    <td className="py-3 px-4">
                      <span className="font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-900 border border-blue-200">
                        {l.action}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600">{l.entity_type}</td>
                    <td className="py-3 px-4 text-gray-900 font-bold">{l.entity_id}</td>
                    <td className="py-3 px-4 text-gray-600 font-sans max-w-xs truncate">
                      {JSON.stringify(l.details)}
                    </td>
                    <td className="py-3 px-4 text-gray-400">{l.ip_address || "127.0.0.1"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
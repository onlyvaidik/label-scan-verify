import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function SettingsProfile() {
  const { user, toggle2FA } = useAuth();
  const [twoFAEnabled, setTwoFAEnabled] = useState(user?.two_factor_enabled || false);
  const [backupCodes, setBackupCodes] = useState(user?.backup_codes || []);
  const [sessions, setSessions] = useState([]);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setTwoFAEnabled(user.two_factor_enabled || false);
      setBackupCodes(user.backup_codes || []);
    }
    fetchSessions();
  }, [user]);

  const fetchSessions = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/auth/sessions`, { withCredentials: true });
      setSessions(res.data || []);
    } catch (e) {
      console.error("Sessions error:", e);
    }
  };

  const handleToggle2FA = async () => {
    setLoading(true);
    try {
      const target = !twoFAEnabled;
      const res = await toggle2FA(target);
      setTwoFAEnabled(target);
      setBackupCodes(res.backup_codes || []);
      setMsg(target ? "Two-Factor Authentication enabled! Save your backup codes below." : "2FA disabled.");
      setTimeout(() => setMsg(""), 4000);
    } catch (e) {
      console.error("2FA toggle error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId) => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/auth/sessions/revoke`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      fetchSessions();
    } catch (e) {
      console.error("Revoke error:", e);
    }
  };

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header */}
      <div className="border-b border-gray-200 pb-5">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
            Inspector Credentials
          </span>
          <span className="text-xs text-gray-500">• Profile & Security</span>
        </div>
        <h1 className="text-2xl font-black text-[#001255] tracking-tight">Officer Profile & Security Settings</h1>
      </div>

      {msg && (
        <div
          data-testid="settings-alert-msg"
          className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold"
        >
          {msg}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Officer Information Card */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-[#001255] flex items-center gap-2 border-b border-gray-100 pb-3">
            <span className="material-symbols-outlined text-blue-600">badge</span>
            <span>Enforcement Credential Details</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-1.5 border-b border-gray-50">
              <span className="text-gray-500">Officer Name:</span>
              <span className="font-bold text-gray-900">{user?.name}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-50">
              <span className="text-gray-500">Official Email:</span>
              <span className="font-mono text-gray-900">{user?.email}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-50">
              <span className="text-gray-500">Officer Badge ID:</span>
              <span className="font-mono font-bold text-[#001255]">{user?.officer_id || "INS-782"}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-50">
              <span className="text-gray-500">Statutory Role:</span>
              <span className="font-bold text-[#E88A1E] uppercase">{user?.role?.replace("_", " ")}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-gray-50">
              <span className="text-gray-500">Designation:</span>
              <span className="font-medium text-gray-800">{user?.designation || "Metrology Inspector"}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-gray-500">Jurisdiction:</span>
              <span className="font-medium text-gray-800">{user?.jurisdiction || "National Central"}</span>
            </div>
          </div>
        </div>

        {/* Two-Factor Authentication (2FA) */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-[#001255] flex items-center gap-2 border-b border-gray-100 pb-3">
            <span className="material-symbols-outlined text-amber-500">security</span>
            <span>Two-Factor Authentication (2FA)</span>
          </h3>

          <p className="text-xs text-gray-600">
            Two-factor verification adds an extra security layer for enforcement officers issuing legal notices.
          </p>

          <div className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl border border-gray-100">
            <div>
              <span className="font-bold text-xs text-gray-900 block">
                2FA Status: {twoFAEnabled ? "Enabled" : "Disabled"}
              </span>
              <span className="text-[11px] text-gray-500">Requires 6-digit code upon login</span>
            </div>
            <button
              onClick={handleToggle2FA}
              disabled={loading}
              data-testid="toggle-2fa-btn"
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                twoFAEnabled
                  ? "bg-red-50 text-red-700 border border-red-200 hover:bg-red-100"
                  : "bg-emerald-600 text-white hover:bg-emerald-700 shadow"
              }`}
            >
              {loading ? "Updating..." : twoFAEnabled ? "Disable 2FA" : "Enable 2FA"}
            </button>
          </div>

          {backupCodes.length > 0 && (
            <div className="p-4 bg-amber-50 rounded-xl border border-amber-200 space-y-2 text-xs">
              <span className="font-bold text-amber-900 block">Emergency One-Time Backup Codes:</span>
              <div className="grid grid-cols-2 gap-2 font-mono text-[11px] text-gray-800">
                {backupCodes.map((c, i) => (
                  <div key={i} className="p-1 bg-white rounded border border-amber-200 text-center">
                    {c}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Active Login Sessions */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-[#001255] flex items-center gap-2">
          <span className="material-symbols-outlined text-purple-600">devices</span>
          <span>Active Login Sessions</span>
        </h3>

        <div className="space-y-2 text-xs">
          {sessions.map((s, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-gray-400">computer</span>
                <div>
                  <span className="font-bold text-gray-800 block">{s.user_agent || "Web Browser"}</span>
                  <span className="text-[11px] text-gray-500 font-mono">
                    IP: {s.ip_address} • Logged in: {s.login_time?.slice(0, 19)}
                  </span>
                </div>
              </div>
              {s.active && (
                <button
                  onClick={() => handleRevokeSession(s.id)}
                  data-testid={`revoke-session-${s.id}`}
                  className="text-xs text-red-600 hover:underline font-semibold"
                >
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
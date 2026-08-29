import React, { useState, useEffect } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { user, login, verify2FA } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("admin@metrology.gov.in");
  const [password, setPassword] = useState("AdminMetrology@2026");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // 2FA state
  const [requires2FA, setRequires2FA] = useState(false);
  const [twoFACode, setTwoFACode] = useState("");
  const [twoFAMessage, setTwoFAMessage] = useState("");

  if (user) {
    return <Navigate to="/" replace />;
  }

  const handleLogin = async (e) => {
    e?.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await login(email, password);
      if (res.requires_2fa) {
        setRequires2FA(true);
        setTwoFAMessage(res.message || "Enter 6-digit verification code");
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Authentication failed. Please verify credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e) => {
    e?.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verify2FA(email, twoFACode);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid 2FA verification code.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (roleEmail, rolePass) => {
    setEmail(roleEmail);
    setPassword(rolePass);
    setError("");
  };

  return (
    <div className="min-h-screen bg-[#07112e] flex flex-col justify-center items-center p-4 relative overflow-hidden font-sans">
      {/* Background Decorative Elements */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-md z-10">
        {/* Header Emblem & Title */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#001255] to-[#1a2f70] border-2 border-amber-400/40 shadow-xl mb-3 text-amber-400">
            <span className="material-symbols-outlined text-4xl">balance</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Legal Metrology Portal</h1>
          <p className="text-xs text-amber-300 font-medium uppercase tracking-wider mt-1">
            Packaged Commodities (LMPC Rules, 2011) Compliance System
          </p>
          <p className="text-xs text-blue-200/70 mt-1">Ministry of Consumer Affairs, Government of India</p>
        </div>

        {/* Login Card */}
        <div className="bg-[#0e2052]/90 backdrop-blur-md rounded-2xl p-6 shadow-2xl border border-blue-700/30 text-white">
          {error && (
            <div
              data-testid="login-error-alert"
              className="mb-4 p-3 bg-red-950/80 border border-red-500/50 rounded-xl text-red-200 text-xs flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-base text-red-400">error</span>
              <span>{error}</span>
            </div>
          )}

          {!requires2FA ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-blue-200 uppercase tracking-wider mb-1.5">
                  Official Email Address
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-blue-400 material-symbols-outlined text-lg">badge</span>
                  <input
                    type="email"
                    required
                    data-testid="login-email-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="inspector@metrology.gov.in"
                    className="w-full bg-[#071333] border border-blue-800 rounded-xl pl-10 pr-3 py-2.5 text-sm text-white focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all placeholder:text-blue-300/40"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-blue-200 uppercase tracking-wider mb-1.5">
                  Security Password
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-blue-400 material-symbols-outlined text-lg">lock</span>
                  <input
                    type="password"
                    required
                    data-testid="login-password-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#071333] border border-blue-800 rounded-xl pl-10 pr-3 py-2.5 text-sm text-white focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400 transition-all placeholder:text-blue-300/40"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                data-testid="login-submit-button"
                className="w-full bg-[#E88A1E] hover:bg-[#d47b15] active:scale-[0.99] text-white font-bold py-3 rounded-xl shadow-lg shadow-amber-600/30 transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {loading ? (
                  <span className="material-symbols-outlined animate-spin text-lg">progress_activity</span>
                ) : (
                  <span className="material-symbols-outlined text-lg">login</span>
                )}
                <span>{loading ? "Authenticating..." : "Access Official Portal"}</span>
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerify2FA} className="space-y-4">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-amber-500/20 text-amber-400 mx-auto flex items-center justify-center mb-2">
                  <span className="material-symbols-outlined text-2xl">security</span>
                </div>
                <h3 className="text-base font-bold text-white">Two-Factor Authentication</h3>
                <p className="text-xs text-blue-200 mt-1">{twoFAMessage}</p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-blue-200 uppercase tracking-wider mb-1.5 text-center">
                  Enter 6-Digit Code
                </label>
                <input
                  type="text"
                  maxLength={8}
                  required
                  data-testid="login-2fa-input"
                  value={twoFACode}
                  onChange={(e) => setTwoFACode(e.target.value)}
                  placeholder="123456"
                  className="w-full text-center tracking-[0.3em] font-mono text-xl bg-[#071333] border border-blue-800 rounded-xl py-2.5 text-amber-300 focus:outline-none focus:border-amber-400"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                data-testid="login-2fa-submit-button"
                className="w-full bg-[#E88A1E] hover:bg-[#d47b15] text-white font-bold py-3 rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 text-sm"
              >
                {loading ? "Verifying..." : "Verify & Enter Portal"}
              </button>

              <button
                type="button"
                onClick={() => setRequires2FA(false)}
                className="w-full text-xs text-blue-300 hover:text-white underline text-center"
              >
                Back to password login
              </button>
            </form>
          )}

          {/* Role Demo Quick Switcher */}
          <div className="mt-6 pt-4 border-t border-blue-800/60">
            <p className="text-[11px] font-semibold text-amber-300 uppercase tracking-wider mb-2 text-center">
              Quick Test Login (Demo Roles)
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                data-testid="quick-login-admin"
                onClick={() => handleQuickLogin("admin@metrology.gov.in", "AdminMetrology@2026")}
                className="p-2 rounded-lg bg-[#14285e] hover:bg-[#1e3985] text-left border border-blue-700/50 transition-colors"
              >
                <span className="font-bold text-amber-300 block">Super Admin</span>
                <span className="text-[10px] text-blue-200">Full Statutory Access</span>
              </button>

              <button
                type="button"
                data-testid="quick-login-officer"
                onClick={() => handleQuickLogin("officer.mumbai@metrology.gov.in", "Officer@2026")}
                className="p-2 rounded-lg bg-[#14285e] hover:bg-[#1e3985] text-left border border-blue-700/50 transition-colors"
              >
                <span className="font-bold text-emerald-300 block">Enforcement Officer</span>
                <span className="text-[10px] text-blue-200">Zonal Review & Notices</span>
              </button>

              <button
                type="button"
                data-testid="quick-login-inspector"
                onClick={() => handleQuickLogin("inspector.delhi@metrology.gov.in", "Inspector@2026")}
                className="p-2 rounded-lg bg-[#14285e] hover:bg-[#1e3985] text-left border border-blue-700/50 transition-colors"
              >
                <span className="font-bold text-sky-300 block">Field Inspector</span>
                <span className="text-[10px] text-blue-200">Scan & Label Analysis</span>
              </button>

              <button
                type="button"
                data-testid="quick-login-viewer"
                onClick={() => handleQuickLogin("viewer@metrology.gov.in", "Viewer@2026")}
                className="p-2 rounded-lg bg-[#14285e] hover:bg-[#1e3985] text-left border border-blue-700/50 transition-colors"
              >
                <span className="font-bold text-purple-300 block">Public / Auditor</span>
                <span className="text-[10px] text-blue-200">Read-Only Reports</span>
              </button>
            </div>
          </div>
        </div>

        {/* Statutory Compliance Footer Notice */}
        <div className="mt-4 text-center text-[11px] text-blue-300/60">
          Authorized access only under Section 15 of Legal Metrology Act, 2009.
        </div>
      </div>
    </div>
  );
}
import React from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header
      data-testid="header-container"
      className="fixed top-0 left-64 right-0 h-16 bg-[#001255] text-white z-40 flex items-center justify-between px-8 shadow-md border-b border-[#1a2f70]"
    >
      {/* Left: Emblem & National Title */}
      <div className="flex items-center gap-4">
        <span className="text-sm font-semibold tracking-wider uppercase text-white flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
          Official Enforcement System
        </span>
        <div className="h-5 w-[1px] bg-blue-400/30"></div>
        <span className="text-xs text-amber-300 font-medium px-2.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
          LMPC RULES, 2011 STATUTORY ENGINE
        </span>
      </div>

      {/* Right: Actions, Search, Badge, User */}
      <div className="flex items-center gap-4">
        <div
          data-testid="header-jurisdiction-badge"
          className="hidden md:flex items-center gap-1.5 text-xs text-blue-200 bg-[#0a1945] px-3 py-1.5 rounded-full border border-blue-800"
        >
          <span className="material-symbols-outlined text-sm text-amber-400">location_on</span>
          <span>{user?.jurisdiction || "National Central"}</span>
        </div>

        <button
          data-testid="header-new-scan-btn"
          onClick={() => navigate("/new-scan")}
          className="bg-[#E88A1E] hover:bg-[#d47b15] text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow transition-all"
        >
          <span className="material-symbols-outlined text-sm">qr_code_scanner</span>
          <span>Scan Product</span>
        </button>

        <div className="h-6 w-[1px] bg-blue-800"></div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/settings")}
            data-testid="header-settings-btn"
            className="p-1.5 text-blue-200 hover:text-white rounded-lg hover:bg-[#1a2f70] transition-colors"
            title="Settings & 2FA"
          >
            <span className="material-symbols-outlined text-xl">settings</span>
          </button>
          <button
            onClick={logout}
            data-testid="header-logout-btn"
            className="p-1.5 text-red-300 hover:text-red-100 rounded-lg hover:bg-red-900/30 transition-colors"
            title="Logout"
          >
            <span className="material-symbols-outlined text-xl">power_settings_new</span>
          </button>
        </div>
      </div>
    </header>
  );
}
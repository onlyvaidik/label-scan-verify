import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Sidebar() {
  const { user, logout, isSuperAdmin, isOfficer } = useAuth();
  const navigate = useNavigate();

  const navItems = [
    { name: "Dashboard", path: "/", icon: "dashboard", testId: "nav-dashboard" },
    { name: "New Product Scan", path: "/new-scan", icon: "document_scanner", testId: "nav-new-scan" },
    { name: "Inspection Reports", path: "/reports", icon: "history", testId: "nav-reports" },
    { name: "Statutory Rule Library", path: "/rules", icon: "gavel", testId: "nav-rules" },
    { name: "Hotspots & Analytics", path: "/hotspots", icon: "analytics", testId: "nav-hotspots" },
    ...(isSuperAdmin || isOfficer
      ? [{ name: "User Management", path: "/users", icon: "group", testId: "nav-users" }]
      : []),
    { name: "Audit Trail", path: "/audit-logs", icon: "receipt_long", testId: "nav-audit-logs" },
    { name: "Profile & Security", path: "/settings", icon: "settings", testId: "nav-settings" },
  ];

  return (
    <aside
      data-testid="sidebar-container"
      className="fixed left-0 top-0 h-full w-64 bg-[#0a1945] text-white z-50 flex flex-col border-r border-[#1a2f70] shadow-xl"
    >
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3 border-b border-[#1a2f70] bg-[#001255]">
        <div className="w-10 h-10 rounded-lg bg-[#E88A1E] flex items-center justify-center text-white shadow-md">
          <span className="material-symbols-outlined text-2xl">balance</span>
        </div>
        <div className="overflow-hidden">
          <h1 className="text-base font-bold tracking-tight text-white leading-tight">Legal Metrology</h1>
          <p className="text-[11px] text-amber-300 font-medium uppercase tracking-wider">Compliance Portal</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            data-testid={item.testId}
            className={({ isActive }) =>
              `flex items-center px-4 py-2.5 rounded-lg text-sm font-medium transition-all group ${
                isActive
                  ? "bg-[#E88A1E] text-white shadow-md font-semibold"
                  : "text-blue-100/80 hover:bg-[#1a2f70] hover:text-white"
              }`
            }
          >
            <span className="material-symbols-outlined mr-3 text-xl">{item.icon}</span>
            <span>{item.name}</span>
          </NavLink>
        ))}
      </nav>

      {/* User Profile Card */}
      <div className="p-3 m-3 bg-[#001255]/80 rounded-xl border border-[#1a2f70]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white font-bold border-2 border-amber-400">
            {user?.name ? user.name.charAt(0) : "U"}
          </div>
          <div className="overflow-hidden flex-1">
            <p className="text-xs font-bold text-white truncate" data-testid="sidebar-user-name">
              {user?.name || "Metrology Officer"}
            </p>
            <p className="text-[10px] text-amber-300 font-medium uppercase truncate" data-testid="sidebar-user-role">
              {user?.role ? user.role.replace("_", " ") : "Inspector"}
            </p>
          </div>
          <button
            onClick={logout}
            data-testid="sidebar-logout-button"
            title="Logout"
            className="text-blue-300 hover:text-amber-400 p-1 transition-colors"
          >
            <span className="material-symbols-outlined text-lg">logout</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
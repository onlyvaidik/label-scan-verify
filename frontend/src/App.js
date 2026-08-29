import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import NewScan from "./pages/NewScan";
import ScanAnalysisReview from "./pages/ScanAnalysisReview";
import InspectionReports from "./pages/InspectionReports";
import StatutoryRuleLibrary from "./pages/StatutoryRuleLibrary";
import ComplianceHotspots from "./pages/ComplianceHotspots";
import UserManagement from "./pages/UserManagement";
import AuditLogs from "./pages/AuditLogs";
import SettingsProfile from "./pages/SettingsProfile";

function ProtectedLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#001255] flex flex-col items-center justify-center text-white font-sans">
        <div className="w-12 h-12 border-4 border-amber-400 border-t-transparent rounded-full animate-spin mb-4"></div>
        <h2 className="text-base font-bold">Connecting to Legal Metrology Portal...</h2>
        <p className="text-xs text-amber-300 mt-1">Verifying officer security credentials</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-[#f5f7fb] flex">
      <Sidebar />
      <div className="pl-64 flex-1 flex flex-col min-w-0">
        <Header />
        <main className="pt-16 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new-scan" element={<NewScan />} />
            <Route path="/scan-review" element={<ScanAnalysisReview />} />
            <Route path="/reports" element={<InspectionReports />} />
            <Route path="/reports/:id" element={<InspectionReports />} />
            <Route path="/rules" element={<StatutoryRuleLibrary />} />
            <Route path="/hotspots" element={<ComplianceHotspots />} />
            <Route path="/users" element={<UserManagement />} />
            <Route path="/audit-logs" element={<AuditLogs />} />
            <Route path="/settings" element={<SettingsProfile />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

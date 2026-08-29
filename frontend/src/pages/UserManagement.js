import React, { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export default function UserManagement() {
  const { user, isSuperAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  // New User Form State
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("Password@2026");
  const [newRole, setNewRole] = useState("inspector");
  const [newJurisdiction, setNewJurisdiction] = useState("New Delhi Central");
  const [newDesignation, setNewDesignation] = useState("Field Metrology Inspector");
  const [formMsg, setFormMsg] = useState("");

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/users`, { withCredentials: true });
      setUsers(res.data || []);
    } catch (e) {
      console.error("Fetch users error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setFormMsg("");
    try {
      await axios.post(
        `${BACKEND_URL}/api/users`,
        {
          email: newEmail,
          name: newName,
          password: newPassword,
          role: newRole,
          jurisdiction: newJurisdiction,
          designation: newDesignation
        },
        { withCredentials: true }
      );
      setShowAddModal(false);
      setNewEmail("");
      setNewName("");
      fetchUsers();
    } catch (err) {
      setFormMsg(err.response?.data?.detail || "Failed to create user.");
    }
  };

  const handleRoleChange = async (targetEmail, updatedRole) => {
    try {
      await axios.put(
        `${BACKEND_URL}/api/users/${targetEmail}`,
        { role: updatedRole },
        { withCredentials: true }
      );
      fetchUsers();
    } catch (e) {
      console.error("Role update failed:", e);
    }
  };

  return (
    <div className="p-8 space-y-6 bg-[#f5f7fb] min-h-[calc(100vh-64px)] font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-[#E88A1E] uppercase tracking-wider bg-amber-50 px-2.5 py-0.5 rounded border border-amber-200">
              Access Control & RBAC
            </span>
            <span className="text-xs text-gray-500">• Enforcement Squad Directory</span>
          </div>
          <h1 className="text-2xl font-black text-[#001255] tracking-tight">User & Team Management</h1>
        </div>

        {isSuperAdmin && (
          <button
            onClick={() => setShowAddModal(true)}
            data-testid="add-user-btn"
            className="bg-[#001255] hover:bg-[#1a2f70] text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-base">person_add</span>
            <span>Add Officer / Inspector</span>
          </button>
        )}
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs" data-testid="user-management-table">
            <thead>
              <tr className="border-b border-gray-200 text-gray-500 uppercase bg-gray-50/50">
                <th className="py-3 px-4 font-bold">Officer Name / ID</th>
                <th className="py-3 px-4 font-bold">Email</th>
                <th className="py-3 px-4 font-bold">Designation</th>
                <th className="py-3 px-4 font-bold">Role</th>
                <th className="py-3 px-4 font-bold">Jurisdiction</th>
                <th className="py-3 px-4 font-bold">2FA Status</th>
                {isSuperAdmin && <th className="py-3 px-4 font-bold text-right">Role Assignment</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u, i) => (
                <tr key={i} className="hover:bg-blue-50/20 transition-colors">
                  <td className="py-3 px-4 font-medium text-gray-900">
                    <div className="font-bold text-[#001255]">{u.name}</div>
                    <div className="text-[11px] font-mono text-gray-400">{u.officer_id || "N/A"}</div>
                  </td>
                  <td className="py-3 px-4 font-mono text-gray-600">{u.email}</td>
                  <td className="py-3 px-4 text-gray-700">{u.designation || "Inspector"}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`font-bold px-2.5 py-0.5 rounded-full uppercase text-[10px] ${
                        u.role === "super_admin"
                          ? "bg-purple-100 text-purple-800"
                          : u.role === "enforcement_officer"
                          ? "bg-amber-100 text-amber-800"
                          : u.role === "inspector"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {u.role?.replace("_", " ")}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-gray-600">{u.jurisdiction || "National"}</td>
                  <td className="py-3 px-4">
                    <span
                      className={`font-bold text-[10px] px-2 py-0.5 rounded ${
                        u.two_factor_enabled
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {u.two_factor_enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  {isSuperAdmin && (
                    <td className="py-3 px-4 text-right">
                      <select
                        value={u.role}
                        data-testid={`role-select-${u.email}`}
                        onChange={(e) => handleRoleChange(u.email, e.target.value)}
                        className="bg-gray-50 border border-gray-200 rounded-lg px-2 py-1 text-xs"
                      >
                        <option value="super_admin">Super Admin</option>
                        <option value="enforcement_officer">Enforcement Officer</option>
                        <option value="inspector">Inspector</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-gray-100 space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-gray-200 pb-3">
              <h3 className="text-sm font-bold text-[#001255]">Create Officer Account</h3>
              <button onClick={() => setShowAddModal(false)} className="text-gray-400 hover:text-gray-600">
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>

            {formMsg && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs">
                {formMsg}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3">
              <div>
                <label className="font-bold text-gray-700 block mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  data-testid="add-user-name-input"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Inspector Name"
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
                />
              </div>

              <div>
                <label className="font-bold text-gray-700 block mb-1">Official Email Address</label>
                <input
                  type="email"
                  required
                  data-testid="add-user-email-input"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="officer@metrology.gov.in"
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
                />
              </div>

              <div>
                <label className="font-bold text-gray-700 block mb-1">Initial Temporary Password</label>
                <input
                  type="text"
                  required
                  data-testid="add-user-password-input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 font-mono"
                />
              </div>

              <div>
                <label className="font-bold text-gray-700 block mb-1">Role</label>
                <select
                  data-testid="add-user-role-select"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
                >
                  <option value="inspector">Inspector (Field Scans)</option>
                  <option value="enforcement_officer">Enforcement Officer (Zonal Notices)</option>
                  <option value="super_admin">Super Admin (Central Controller)</option>
                  <option value="viewer">Viewer (Read-Only Audit)</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-gray-700 block mb-1">Jurisdiction / District</label>
                <input
                  type="text"
                  value={newJurisdiction}
                  onChange={(e) => setNewJurisdiction(e.target.value)}
                  placeholder="e.g. Maharashtra Zone 1"
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 rounded-lg text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  data-testid="submit-create-user-btn"
                  className="px-4 py-1.5 bg-[#001255] text-white font-bold rounded-lg"
                >
                  Create Officer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
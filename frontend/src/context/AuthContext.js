import React, { createContext, useContext, useState, useEffect } from "react";
import axios from "axios";

const AuthContext = createContext(null);
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const stored = localStorage.getItem("lmpc_user");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed?.token) {
          axios.defaults.headers.common["Authorization"] = `Bearer ${parsed.token}`;
        }
      }
      const res = await axios.get(`${BACKEND_URL}/api/auth/me`, { withCredentials: true });
      setUser(res.data);
    } catch (err) {
      // If cookie fails, check localStorage token fallback
      const stored = localStorage.getItem("lmpc_user");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed?.token) {
            axios.defaults.headers.common["Authorization"] = `Bearer ${parsed.token}`;
          }
          setUser(parsed);
        } catch (e) {
          setUser(false);
        }
      } else {
        setUser(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const res = await axios.post(
      `${BACKEND_URL}/api/auth/login`,
      { email, password },
      { withCredentials: true }
    );
    if (res.data.requires_2fa) {
      return res.data;
    }
    if (res.data.token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${res.data.token}`;
    }
    setUser(res.data);
    localStorage.setItem("lmpc_user", JSON.stringify(res.data));
    return res.data;
  };

  const verify2FA = async (email, code) => {
    const res = await axios.post(
      `${BACKEND_URL}/api/auth/verify-2fa`,
      { email, code },
      { withCredentials: true }
    );
    if (res.data.token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${res.data.token}`;
    }
    setUser(res.data);
    localStorage.setItem("lmpc_user", JSON.stringify(res.data));
    return res.data;
  };

  const logout = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/auth/logout`, {}, { withCredentials: true });
    } catch (e) {
      // ignore
    }
    delete axios.defaults.headers.common["Authorization"];
    setUser(false);
    localStorage.removeItem("lmpc_user");
  };

  const toggle2FA = async (enabled) => {
    const res = await axios.post(
      `${BACKEND_URL}/api/auth/toggle-2fa`,
      { enabled },
      { withCredentials: true }
    );
    setUser((prev) => ({ ...prev, two_factor_enabled: enabled, backup_codes: res.data.backup_codes }));
    return res.data;
  };

  const isSuperAdmin = user?.role === "super_admin";
  const isOfficer = user?.role === "enforcement_officer" || isSuperAdmin;
  const isInspector = user?.role === "inspector" || isOfficer;
  const isViewer = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        verify2FA,
        logout,
        toggle2FA,
        checkAuth,
        isSuperAdmin,
        isOfficer,
        isInspector,
        isViewer
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
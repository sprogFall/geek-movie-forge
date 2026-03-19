"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  clearAuth,
  fetchMe,
  getStoredToken,
  getStoredUser,
  login as apiLogin,
  register as apiRegister,
  setOnUnauthorized,
  storeAuth,
} from "@/lib/api";
import type { UserResponse } from "@/types/api";

type AuthState = {
  user: UserResponse | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);
const PUBLIC_PATHS = ["/login", "/register"];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.includes(pathname);
}

function AuthScreen({ message }: { message: string }) {
  return (
    <div className="loading-screen">
      <div className="loading-panel">
        <span className="loading-dot" />
        <span>{message}</span>
      </div>
    </div>
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    navigate("/login", { replace: true });
  }, [navigate]);

  useEffect(() => {
    setOnUnauthorized(logout);
  }, [logout]);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
      setLoading(false);
    }

    fetchMe()
      .then((nextUser) => {
        setUser(nextUser);
        storeAuth(token, nextUser);
      })
      .catch(() => {
        if (!stored) logout();
      })
      .finally(() => {
        setLoading(false);
      });
  }, [logout]);

  useEffect(() => {
    if (loading) return;

    const isPublic = isPublicPath(pathname);
    if (!user && !isPublic) {
      navigate("/login", { replace: true });
      return;
    }

    if (user && isPublic) {
      navigate("/", { replace: true });
    }
  }, [loading, navigate, pathname, user]);

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      const res = await apiLogin(username, password);
      storeAuth(res.access_token, res.user);
      setUser(res.user);
      navigate("/", { replace: true });
    },
    [navigate],
  );

  const handleRegister = useCallback(
    async (username: string, password: string) => {
      const res = await apiRegister(username, password);
      storeAuth(res.access_token, res.user);
      setUser(res.user);
      navigate("/", { replace: true });
    },
    [navigate],
  );

  const value = useMemo<AuthState>(
    () => ({ user, loading, login: handleLogin, register: handleRegister, logout }),
    [user, loading, handleLogin, handleRegister, logout],
  );

  if (loading) {
    return <AuthScreen message="正在加载登录状态..." />;
  }

  if (!user && !isPublicPath(pathname)) {
    return <AuthScreen message="登录状态无效，正在跳转到登录页..." />;
  }

  if (user && isPublicPath(pathname)) {
    return <AuthScreen message="正在进入控制台..." />;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

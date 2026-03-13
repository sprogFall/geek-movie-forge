"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

import {
  login as apiLogin,
  register as apiRegister,
  getStoredToken,
  getStoredUser,
  storeAuth,
  clearAuth,
  setOnUnauthorized,
  fetchMe,
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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    router.push("/login");
  }, [router]);

  useEffect(() => {
    setOnUnauthorized(logout);
  }, [logout]);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      if (!PUBLIC_PATHS.includes(pathname)) {
        router.replace("/login");
      }
      return;
    }

    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
      setLoading(false);
    }

    fetchMe()
      .then((u) => {
        setUser(u);
        storeAuth(token, u);
      })
      .catch(() => {
        logout();
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading && !user && !PUBLIC_PATHS.includes(pathname)) {
      router.replace("/login");
    }
  }, [loading, user, pathname, router]);

  useEffect(() => {
    if (!loading && user && PUBLIC_PATHS.includes(pathname)) {
      router.replace("/");
    }
  }, [loading, user, pathname, router]);

  async function handleLogin(username: string, password: string) {
    const res = await apiLogin(username, password);
    storeAuth(res.access_token, res.user);
    setUser(res.user);
    router.push("/");
  }

  async function handleRegister(username: string, password: string) {
    const res = await apiRegister(username, password);
    storeAuth(res.access_token, res.user);
    setUser(res.user);
    router.push("/");
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-panel">
          <span className="loading-dot" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  if (!user && !PUBLIC_PATHS.includes(pathname)) {
    return null;
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, login: handleLogin, register: handleRegister, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

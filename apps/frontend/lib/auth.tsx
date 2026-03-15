"use client";

import { createContext, useContext, useEffect, useState, useCallback, useMemo, ReactNode } from "react";
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

  // 初始化认证状态——仅在挂载时执行一次
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    // 优先从 localStorage 恢复用户态，立即解除 loading
    const stored = getStoredUser();
    if (stored) {
      setUser(stored);
      setLoading(false);
    }

    // 后台校验 token 有效性（不阻塞页面渲染）
    fetchMe()
      .then((u) => {
        setUser(u);
        storeAuth(token, u);
      })
      .catch(() => {
        // 仅在后台校验失败时登出，不影响已恢复的状态
        if (!stored) logout();
      })
      .finally(() => {
        // 兜底：确保即使无 stored user 也能结束 loading
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 统一路由守卫：合并为单个 effect，减少重渲染次数
  useEffect(() => {
    if (loading) return;
    const isPublic = PUBLIC_PATHS.includes(pathname);
    if (!user && !isPublic) {
      router.replace("/login");
    } else if (user && isPublic) {
      router.replace("/");
    }
  }, [loading, user, pathname, router]);

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      const res = await apiLogin(username, password);
      storeAuth(res.access_token, res.user);
      setUser(res.user);
      router.push("/");
    },
    [router],
  );

  const handleRegister = useCallback(
    async (username: string, password: string) => {
      const res = await apiRegister(username, password);
      storeAuth(res.access_token, res.user);
      setUser(res.user);
      router.push("/");
    },
    [router],
  );

  // 稳定的 context value——仅在 user/loading/函数引用变化时生成新对象
  const value = useMemo<AuthState>(
    () => ({ user, loading, login: handleLogin, register: handleRegister, logout }),
    [user, loading, handleLogin, handleRegister, logout],
  );

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-panel">
          <span className="loading-dot" />
          <span>加载中...</span>
        </div>
      </div>
    );
  }

  if (!user && !PUBLIC_PATHS.includes(pathname)) {
    return null;
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";

const REMEMBER_KEY = "gmf_remember";

const ERROR_MAP: Record<string, string> = {
  "Invalid username or password": "用户名或密码错误",
  "Username already exists": "该用户名已被注册",
};

function friendlyError(msg: string): string {
  return ERROR_MAP[msg] ?? msg;
}

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(REMEMBER_KEY);
      if (saved) {
        const data = JSON.parse(saved);
        setUsername(data.username ?? "");
        setPassword(data.password ?? "");
        setRemember(true);
      }
    } catch {
      // ignore corrupt data
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    // 在登录前保存/清除记住的凭证（登录成功后会导航离开）
    if (remember) {
      localStorage.setItem(REMEMBER_KEY, JSON.stringify({ username, password }));
    } else {
      localStorage.removeItem(REMEMBER_KEY);
    }

    try {
      await login(username, password);
    } catch (err) {
      setError(friendlyError(err instanceof Error ? err.message : "登录失败"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="auth-header">
          <div className="brand-mark">
            <span className="brand-orb" />
            <div className="brand-copy">
              <strong>Geek Movie Forge</strong>
              <span>制作控制台</span>
            </div>
          </div>
          <h1>登录</h1>
          <p>请输入账号密码以进入控制台。</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="form-stack">
          <div className="form-group">
            <label className="form-label" htmlFor="username">
              用户名
            </label>
            <input
              id="username"
              className="form-input"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              密码
            </label>
            <input
              id="password"
              className="form-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoComplete="current-password"
              required
            />
          </div>

          <div className="form-check">
            <input
              id="remember"
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            <label htmlFor="remember">记住密码</label>
          </div>

          <button className="btn btn-primary auth-btn" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "正在登录..." : "登录"}
          </button>
        </div>

        <p className="auth-footer">
          还没有账号？{" "}
          <Link href="/register" className="auth-link">
            去注册
          </Link>
        </p>
      </form>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await register(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
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
          <h1>注册</h1>
          <p>创建账号后即可使用制作控制台。</p>
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
              placeholder="至少 2 个字符"
              autoComplete="username"
              required
              minLength={2}
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
              placeholder="至少 6 个字符"
              autoComplete="new-password"
              required
              minLength={6}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirm-password">
              确认密码
            </label>
            <input
              id="confirm-password"
              className="form-input"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="请再次输入密码"
              autoComplete="new-password"
              required
              minLength={6}
            />
          </div>

          <button className="btn btn-primary auth-btn" type="submit" disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "正在创建账号..." : "创建账号"}
          </button>
        </div>

        <p className="auth-footer">
          已有账号？{" "}
          <Link href="/login" className="auth-link">
            去登录
          </Link>
        </p>
      </form>
    </div>
  );
}

"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { navigationSections } from "@/lib/navigation";

type AppShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
};

const SIDEBAR_COLLAPSED_KEY = "gmf_sidebar:collapsed";

export function AppShell({ eyebrow, title, description, children }: AppShellProps) {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
      setSidebarCollapsed(raw === "1");
    } catch {
      setSidebarCollapsed(false);
    }
  }, []);

  function toggleSidebar() {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? "1" : "0");
      } catch {
        // ignore localStorage failures
      }
      return next;
    });
  }

  return (
    <div className={`shell${sidebarCollapsed ? " is-sidebar-collapsed" : ""}`}>
      <aside className={`sidebar${sidebarCollapsed ? " is-collapsed" : ""}`}>
        <button
          className="sidebar-toggle"
          type="button"
          onClick={toggleSidebar}
          aria-label={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
          title={sidebarCollapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            {sidebarCollapsed ? (
              <>
                <path d="M9 6l6 6-6 6" />
                <path d="M4 4h2v16H4z" />
              </>
            ) : (
              <>
                <path d="M15 6l-6 6 6 6" />
                <path d="M18 4h2v16h-2z" />
              </>
            )}
          </svg>
          <span className="sidebar-toggle-label">{sidebarCollapsed ? "展开" : "收起"}</span>
        </button>

        <div className="brand-mark">
          <span className="brand-orb" />
          <div className="brand-copy">
            <strong>Geek Movie Forge</strong>
            <span>制作控制台</span>
          </div>
        </div>

        <nav className="nav" aria-label="主导航">
          {navigationSections.map((section, index) => (
            <div key={index} className="nav-section">
              {section.title ? <span className="nav-section-title">{section.title}</span> : null}
              {section.items.map((item) => {
                const isActive = pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={`nav-link${isActive ? " is-active" : ""}`}
                    data-short={item.label.slice(0, 1)}
                    title={item.label}
                  >
                    <strong>{item.label}</strong>
                    <span>{item.description}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <section className="sidebar-user">
          <div className="sidebar-user-info">
            <div className="user-avatar">{user?.username.charAt(0).toUpperCase()}</div>
            <div>
              <strong>{user?.username}</strong>
              <span>已登录</span>
            </div>
          </div>
          <button className="btn btn-sm btn-secondary" onClick={logout} type="button">
            退出登录
          </button>
        </section>
      </aside>

      <main className="content">
        <header className="topbar">
          <div className="title-block">
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>

          <div className="topbar-status">
            <span className="status-dot" />
            <div>
              <strong>流水线状态</strong>
              <div>API 正常，队列链路就绪</div>
            </div>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}

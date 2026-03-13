"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

import { navigationItems } from "@/lib/navigation";

type AppShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
};

export function AppShell({ eyebrow, title, description, children }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-mark">
          <span className="brand-orb" />
          <div className="brand-copy">
            <strong>Geek Movie Forge</strong>
            <span>same-repo production console</span>
          </div>
        </div>

        <nav className="nav" aria-label="Primary navigation">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link${isActive ? " is-active" : ""}`}
              >
                <strong>{item.label}</strong>
                <span>{item.description}</span>
              </Link>
            );
          })}
        </nav>

        <section className="sidebar-footer">
          <strong>Workspace mode</strong>
          <p>Frontend, API, orchestration and workers now live in one repository.</p>
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
              <strong>Pipeline heartbeat</strong>
              <div>API green, queue wiring ready</div>
            </div>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}

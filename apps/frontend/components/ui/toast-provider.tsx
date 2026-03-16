"use client";

import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";

type ToastKind = "success" | "error" | "info";

export type Toast = {
  id: string;
  kind: ToastKind;
  title: string;
  message?: string;
  createdAt: number;
};

type ToastInput = Omit<Toast, "id" | "createdAt"> & { durationMs?: number };

type ToastApi = {
  push: (toast: ToastInput) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
};

const ToastContext = createContext<ToastApi | null>(null);

function uid() {
  return `toast_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (input: ToastInput) => {
      const id = uid();
      const durationMs = input.durationMs ?? 2400;
      const toast: Toast = {
        id,
        kind: input.kind,
        title: input.title,
        message: input.message,
        createdAt: Date.now(),
      };
      setToasts((prev) => [toast, ...prev].slice(0, 4));
      window.setTimeout(() => remove(id), durationMs);
    },
    [remove],
  );

  const api = useMemo<ToastApi>(
    () => ({
      push,
      success: (title, message) => push({ kind: "success", title, message }),
      error: (title, message) => push({ kind: "error", title, message, durationMs: 3600 }),
      info: (title, message) => push({ kind: "info", title, message }),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-viewport" aria-live="polite" aria-relevant="additions">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.kind}`} role="status">
            <div className="toast-head">
              <strong>{t.title}</strong>
              <button className="toast-close" type="button" onClick={() => remove(t.id)} aria-label="关闭提示">
                ×
              </button>
            </div>
            {t.message ? <div className="toast-msg">{t.message}</div> : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}


// Small reusable UI pieces used by many pages.

import { useEffect, useRef, useState, type ReactNode } from "react";

// ------------------------------------------------------- status badge ---

const STATUS_STYLES: Record<string, string> = {
  Successful: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  Healthy: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  running: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  Building: "bg-blue-500/10 text-blue-300 border-blue-500/30",
  Deploying: "bg-blue-500/10 text-blue-300 border-blue-500/30",
  Pending: "bg-slate-500/10 text-slate-300 border-slate-500/30",
  restarting: "bg-amber-500/10 text-amber-300 border-amber-500/30",
  Failed: "bg-red-500/10 text-red-300 border-red-500/30",
  Unhealthy: "bg-red-500/10 text-red-300 border-red-500/30",
  "Rolled Back": "bg-amber-500/10 text-amber-300 border-amber-500/30",
  Replaced: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  exited: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  Stopped: "bg-slate-500/10 text-slate-400 border-slate-500/30",
};

const DOT_STYLES: Record<string, string> = {
  Successful: "bg-emerald-400",
  Healthy: "bg-emerald-400",
  running: "bg-emerald-400",
  Building: "bg-blue-400 animate-pulse",
  Deploying: "bg-blue-400 animate-pulse",
  Pending: "bg-slate-400 animate-pulse",
  Failed: "bg-red-400",
  Unhealthy: "bg-red-400",
  "Rolled Back": "bg-amber-400",
  restarting: "bg-amber-400",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-slate-500/10 text-slate-400 border-slate-500/30";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${style}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${DOT_STYLES[status] ?? "bg-slate-500"}`} />
      {status || "-"}
    </span>
  );
}

export function TypeBadge({ type }: { type: string }) {
  const styles: Record<string, string> = {
    python: "text-sky-300 bg-sky-500/10 border-sky-500/30",
    node: "text-lime-300 bg-lime-500/10 border-lime-500/30",
    java: "text-orange-300 bg-orange-500/10 border-orange-500/30",
  };
  const labels: Record<string, string> = { python: "Python", node: "Node.js", java: "Java" };
  return (
    <span className={`rounded-md border px-1.5 py-0.5 text-xs font-medium ${styles[type] ?? "text-muted border-line"}`}>
      {labels[type] ?? "Unknown"}
    </span>
  );
}

// ------------------------------------------------------- page layout ---

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{message}</div>
  );
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center justify-center px-6 py-14 text-center">
      <p className="font-medium text-white">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-muted">{text}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return <span className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`} />;
}

export function ProgressBar({ value, color = "from-brand-blue to-brand-violet" }: { value: number; color?: string }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
      <div className={`h-full rounded-full bg-gradient-to-r ${color}`} style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} />
    </div>
  );
}

// -------------------------------------------------------------- hooks ---

/**
 * Load data from the API and reload it every `intervalMs` milliseconds
 * (0 = load once). Returns the data, an error message and a reload function.
 */
export function usePolling<T>(loader: () => Promise<T>, intervalMs = 0, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = async () => {
    try {
      setData(await loaderRef.current());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  useEffect(() => {
    setData(null);
    reload();
    if (!intervalMs) return;
    const timer = window.setInterval(reload, intervalMs);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);

  return { data, error, reload };
}

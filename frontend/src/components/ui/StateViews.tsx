/**
 * 通用 UI 组件 · Loading / Error / Empty
 */
import { ReactNode } from "react";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-12 text-slate-500 text-sm">
      <div className="animate-pulse">{label}</div>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="border border-red-200 bg-red-50 rounded-md p-4 text-sm text-red-700">
      <div className="font-medium">API request failed</div>
      <div className="mt-1 text-red-600">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-3 py-1 text-xs border border-red-300 rounded hover:bg-red-100"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
}: {
  title: string;
  hint?: string;
}) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 rounded-md py-10 text-center text-sm text-slate-500">
      <div className="font-medium text-slate-700">{title}</div>
      {hint && <div className="mt-1 text-xs">{hint}</div>}
    </div>
  );
}

export function Card({
  title,
  subtitle,
  right,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`bg-white border border-slate-200 rounded-md shadow-sm ${className}`}
    >
      {(title || right) && (
        <header className="flex items-start justify-between px-4 py-3 border-b border-slate-100">
          <div>
            {title && (
              <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
            )}
            {subtitle && (
              <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
            )}
          </div>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function KPITile({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "neutral" | "warning" | "danger" | "ok";
}) {
  const toneClass: Record<string, string> = {
    neutral: "text-slate-800",
    ok: "text-emerald-600",
    warning: "text-amber-600",
    danger: "text-red-600",
  };
  return (
    <div className="bg-white border border-slate-200 rounded-md p-4 shadow-sm">
      <div className="text-xs text-slate-500 uppercase tracking-wide">
        {label}
      </div>
      <div className={`text-2xl font-semibold mt-2 ${toneClass[tone]}`}>
        {value}
      </div>
      {hint && <div className="text-xs text-slate-400 mt-1">{hint}</div>}
    </div>
  );
}

export function Badge({
  children,
  color = "slate",
}: {
  children: ReactNode;
  color?: "slate" | "green" | "amber" | "orange" | "red" | "blue";
}) {
  const palette: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700 border-slate-200",
    green: "bg-emerald-50 text-emerald-700 border-emerald-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    orange: "bg-orange-50 text-orange-700 border-orange-200",
    red: "bg-red-50 text-red-700 border-red-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded ${palette[color]}`}
    >
      {children}
    </span>
  );
}

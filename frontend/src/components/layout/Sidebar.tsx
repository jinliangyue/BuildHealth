/**
 * Sidebar · 桌面端常驻 / 移动端抽屉
 */
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/buildings", label: "Buildings", end: false },
  { to: "/monitoring", label: "Monitoring", end: false },
  { to: "/risk-health", label: "Risk & Health", end: false },
  { to: "/retrofit", label: "Retrofit Decision", end: false },
  { to: "/data", label: "Data / Settings", end: false },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  // 路由切换后自动关闭移动 drawer
  useEffect(() => {
    const handler = () => setOpen(false);
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);

  return (
    <>
      {/* 移动端 hamburger */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="md:hidden fixed top-3 left-3 z-40 w-10 h-10 bg-white border border-slate-300 rounded shadow-sm flex items-center justify-center text-slate-700"
        aria-label="Open navigation"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>

      {/* 移动端 overlay */}
      {open && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-40"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`
          fixed md:static top-0 left-0 h-full z-50 w-60 bg-white border-r border-slate-200 flex flex-col
          transition-transform duration-200
          ${open ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <div className="text-base font-bold text-slate-900">BuildHealth</div>
            <div className="text-[11px] text-slate-500 mt-0.5 leading-snug">
              Existing Building Health Monitoring
              <br />& Intelligent Retrofit Decision Platform
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="md:hidden text-slate-500 hover:text-slate-700 px-2"
            aria-label="Close navigation"
          >
            ✕
          </button>
        </div>
        <nav className="flex-1 py-3">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `block px-5 py-2 text-sm border-l-2 ${
                  isActive
                    ? "bg-blue-50 text-blue-700 border-blue-600 font-medium"
                    : "text-slate-600 border-transparent hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-3 border-t border-slate-200 text-[11px] text-slate-500 leading-relaxed">
          <div className="font-medium text-slate-700">Phase 4 · v0.4.0</div>
          <div className="mt-1 px-1.5 py-0.5 bg-amber-50 border border-amber-200 rounded inline-block text-amber-700">
            Simulated Data
          </div>
        </div>
      </aside>
    </>
  );
}

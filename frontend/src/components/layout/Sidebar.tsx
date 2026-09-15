import { NavLink } from "react-router-dom";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/buildings", label: "Buildings", end: false },
  { to: "/monitoring", label: "Monitoring", end: false },
  { to: "/risk-health", label: "Risk & Health", end: false },
  { to: "/data", label: "Data / Settings", end: false },
];

export default function Sidebar() {
  return (
    <aside className="w-60 bg-white border-r border-slate-200 flex flex-col h-full">
      <div className="px-5 py-4 border-b border-slate-200">
        <div className="text-base font-bold text-slate-900">BuildHealth</div>
        <div className="text-[11px] text-slate-500 mt-0.5 leading-snug">
          Existing Building Health Monitoring
          <br />& Intelligent Retrofit Decision Platform
        </div>
      </div>
      <nav className="flex-1 py-3">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
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
        <div className="font-medium text-slate-700">Phase 2 · v0.2.0</div>
        <div className="mt-1 px-1.5 py-0.5 bg-amber-50 border border-amber-200 rounded inline-block text-amber-700">
          Simulated Data
        </div>
      </div>
    </aside>
  );
}

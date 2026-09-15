import { NavLink } from "react-router-dom";

/**
 * 侧边栏导航 · Phase 0 占位
 */
export default function Sidebar() {
  const navItems = [
    { to: "/", label: "Dashboard", icon: "▦" },
    { to: "/buildings", label: "Buildings", icon: "▤" },
    { to: "/monitoring", label: "Monitoring", icon: "▣" },
    { to: "/risk-health", label: "Risk & Health", icon: "◆" },
    { to: "/settings", label: "Settings", icon: "◇" },
  ];

  return (
    <aside className="w-56 bg-engineering-surface border-r border-engineering-border flex flex-col">
      <div className="px-4 py-5 border-b border-engineering-border">
        <h1 className="text-lg font-bold">BuildHealth</h1>
        <p className="text-xs text-engineering-muted mt-1">
          既有建筑健康监测
        </p>
      </div>
      <nav className="flex-1 py-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2 text-sm ${
                isActive
                  ? "bg-engineering-bg text-white border-l-2 border-risk-normal"
                  : "text-engineering-muted hover:text-engineering-text hover:bg-engineering-bg"
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-engineering-border text-xs text-engineering-muted">
        <p>Phase 0 · v0.0.1</p>
        <p className="mt-1 text-amber-500">Simulated Data</p>
      </div>
    </aside>
  );
}

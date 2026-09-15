/**
 * Dashboard 页面占位
 * Phase 1 实现：KPI 卡片 + Top 风险 + 总览图
 */
export default function Dashboard() {
  return (
    <div>
      <header className="mb-6">
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-engineering-muted mt-1">
          平台总览 · 当前 Phase 0 骨架
        </p>
      </header>

      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "Buildings", value: "—" },
          { label: "Active Sensors", value: "—" },
          { label: "Avg BHI", value: "—" },
          { label: "High Risk Alerts", value: "—" },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="bg-engineering-surface border border-engineering-border rounded p-4"
          >
            <div className="text-xs text-engineering-muted">{kpi.label}</div>
            <div className="text-2xl font-semibold mt-2">{kpi.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-engineering-surface border border-engineering-border rounded p-6 text-center text-engineering-muted">
        <p>图表占位 · Phase 1 实现（ECharts TrendChart / BhiRadar）</p>
      </div>
    </div>
  );
}

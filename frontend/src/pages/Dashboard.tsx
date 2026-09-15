/**
 * Dashboard · 全平台总览
 * 全部数据来自 GET /api/dashboard/summary
 */
import { Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import { Card, KPITile, LoadingState, ErrorState, Badge } from "../components/ui/StateViews";
import DistributionPie from "../components/charts/DistributionPie";
import { dashboardApi } from "../api/dashboard";
import { useApi } from "../hooks/useApi";
import { formatTimestamp, formatNumber } from "../hooks/format";
import {
  RISK_LEVEL_COLORS,
  RISK_LEVEL_LABELS,
  SEVERITY_COLORS,
} from "../types/api";

export default function Dashboard() {
  const { data, loading, error, refetch } = useApi(() => dashboardApi.summary());

  return (
    <div className="max-w-7xl mx-auto">
      <TopBar
        title="Platform Overview"
        subtitle="Real-time aggregate metrics across all monitored buildings"
        right={
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      />

      {loading && <LoadingState label="Loading dashboard data..." />}
      {error && <ErrorState message={error} onRetry={refetch} />}
      {data && (
        <div className="space-y-5">
          {/* KPI 行 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <KPITile
              label="Total Buildings"
              value={data.total_buildings}
              hint="Monitored buildings"
            />
            <KPITile
              label="Monitoring Points"
              value={data.monitoring_points}
              hint="Active sensors"
            />
            <KPITile
              label="Active Alerts"
              value={data.active_alerts}
              tone={data.active_alerts > 0 ? "danger" : "ok"}
              hint="Unresolved prototype anomalies"
            />
            <KPITile
              label="Average BHI"
              value={formatNumber(data.average_health_score)}
              tone={
                data.average_health_score >= 75
                  ? "ok"
                  : data.average_health_score >= 60
                    ? "warning"
                    : "danger"
              }
              hint="Across all buildings (0-100)"
            />
          </div>

          {/* 风险分布 + Building Ranking */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card title="Risk Distribution" subtitle="Prototype Risk Classification">
              <DistributionPie distribution={data.risk_distribution} />
            </Card>

            <Card
              title="Building Ranking"
              subtitle="Sorted by BHI ascending"
              className="lg:col-span-2"
            >
              {data.building_ranking.length === 0 ? (
                <div className="text-sm text-slate-500 py-6 text-center">
                  No buildings available
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Building</th>
                      <th className="text-right">BHI</th>
                      <th>Risk Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.building_ranking.map((r) => (
                      <tr key={r.building_id}>
                        <td>
                          <Link
                            to={`/buildings/${r.building_id}`}
                            className="text-blue-700 hover:underline"
                          >
                            {r.name}
                          </Link>
                        </td>
                        <td className="text-right font-mono">
                          {formatNumber(r.bhi)}
                        </td>
                        <td>
                          <Badge
                            color={
                              r.risk_level === "Normal"
                                ? "green"
                                : r.risk_level === "Attention"
                                  ? "amber"
                                  : r.risk_level === "Abnormal"
                                    ? "orange"
                                    : "red"
                            }
                          >
                            <span
                              className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
                              style={{ background: RISK_LEVEL_COLORS[r.risk_level] }}
                            />
                            {RISK_LEVEL_LABELS[r.risk_level]}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>

          {/* Recent Alerts */}
          <Card
            title="Recent Alerts"
            subtitle="Latest 10 active prototype anomalies"
          >
            {data.recent_alerts.length === 0 ? (
              <div className="text-sm text-slate-500 py-6 text-center">
                No active alerts
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Building</th>
                    <th>Metric</th>
                    <th className="text-right">Current</th>
                    <th className="text-right">Change</th>
                    <th>Method</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_alerts.map((a) => (
                    <tr key={a.id}>
                      <td className="font-mono text-xs">
                        {formatTimestamp(a.timestamp)}
                      </td>
                      <td>
                        <Link
                          to={`/buildings/${a.building_id}`}
                          className="text-blue-700 hover:underline"
                        >
                          #{a.building_id}
                        </Link>
                      </td>
                      <td className="font-mono text-xs">{a.metric}</td>
                      <td className="text-right font-mono">
                        {formatNumber(a.current_value)}
                      </td>
                      <td className="text-right font-mono">
                        {a.change !== null ? formatNumber(a.change) : "—"}
                      </td>
                      <td className="text-xs">{a.detection_method}</td>
                      <td>
                        <span
                          className="px-2 py-0.5 text-xs rounded border"
                          style={{
                            background: `${SEVERITY_COLORS[a.severity]}20`,
                            color: SEVERITY_COLORS[a.severity],
                            borderColor: SEVERITY_COLORS[a.severity],
                          }}
                        >
                          {a.severity}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}

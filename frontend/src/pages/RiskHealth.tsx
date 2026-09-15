/**
 * Risk & Health · 风险列表 + BHI 雷达 + 异常全表
 */
import { Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
  Badge,
} from "../components/ui/StateViews";
import BhiRadar from "../components/charts/BhiRadar";
import DistributionPie from "../components/charts/DistributionPie";
import { buildingsApi } from "../api/buildings";
import { healthApi } from "../api/health";
import { riskApi } from "../api/risk";
import { useApi } from "../hooks/useApi";
import { formatTimestamp, formatNumber } from "../hooks/format";
import {
  BHI_WEIGHTS,
  DIMENSION_LABELS,
  METRIC_LABELS,
  RISK_LEVEL_COLORS,
  RISK_LEVEL_LABELS,
  SEVERITY_COLORS,
  type Building,
  type HealthAssessment,
  type RiskAlert,
  type RiskClassification,
  type RiskDistribution,
  type DimensionInfo,
} from "../types/api";

interface BuildingBlock {
  building: Building;
  health: HealthAssessment;
  risk: RiskClassification;
}

export default function RiskHealth() {
  const { data, loading, error, refetch } = useApi(async () => {
    const buildings = await buildingsApi.list();
    const blocks = await Promise.all(
      buildings.map(async (b): Promise<BuildingBlock | null> => {
        try {
          const health = await healthApi.get(b.id);
          const risk = await riskApi.classify(b.id);
          return { building: b, health, risk };
        } catch {
          return null;
        }
      }),
    );
    const validBlocks = blocks.filter((x): x is BuildingBlock => x !== null);
    // 收集全部 alerts
    const allAlerts: (RiskAlert & { building_name: string })[] = (
      await Promise.all(
        buildings.map(async (b) => {
          try {
            const alerts = await riskApi.alerts(b.id, true);
            return alerts.map((a) => ({ ...a, building_name: b.name }));
          } catch {
            return [];
          }
        }),
      )
    ).flat();
    // 分布
    const distribution: RiskDistribution = {
      Normal: 0,
      Attention: 0,
      Abnormal: 0,
      HighRisk: 0,
    };
    validBlocks.forEach((b) => {
      distribution[b.risk.risk_level] += 1;
    });
    // 排序 alerts by severity desc, time desc
    const severityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
    allAlerts.sort((a, b) => {
      const sev = severityOrder[a.severity] - severityOrder[b.severity];
      if (sev !== 0) return sev;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
    return { blocks: validBlocks, alerts: allAlerts, distribution };
  });

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <TopBar
        title="Risk & Health"
        subtitle="Cross-building risk classification and prototype anomaly summary"
        right={
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      />

      {loading && <LoadingState label="Loading risk data..." />}
      {error && <ErrorState message={error} onRetry={refetch} />}
      {data && (
        <>
          {/* Distribution */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card title="Risk Distribution">
              <DistributionPie distribution={data.distribution} />
            </Card>
            <Card
              title="Average BHI"
              subtitle="Across all monitored buildings"
              className="md:col-span-2"
            >
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="col-span-2 md:col-span-1 flex flex-col items-center justify-center border-r border-slate-100 pr-4">
                  <div className="text-xs text-slate-500 uppercase">
                    Platform Average
                  </div>
                  <div className="text-4xl font-bold font-mono mt-2 text-slate-900">
                    {data.blocks.length === 0
                      ? "—"
                      : formatNumber(
                          data.blocks.reduce((s, b) => s + b.health.score, 0) /
                            data.blocks.length,
                        )}
                  </div>
                </div>
                {data.blocks.map((b) => (
                  <div
                    key={b.building.id}
                    className="border border-slate-200 rounded p-3 bg-slate-50"
                  >
                    <div className="text-xs text-slate-500 truncate">
                      {b.building.name}
                    </div>
                    <div className="text-2xl font-semibold font-mono mt-1 text-slate-900">
                      {formatNumber(b.health.score)}
                    </div>
                    <div className="mt-1">
                      <Badge
                        color={
                          b.risk.risk_level === "Normal"
                            ? "green"
                            : b.risk.risk_level === "Attention"
                              ? "amber"
                              : b.risk.risk_level === "Abnormal"
                                ? "orange"
                                : "red"
                        }
                      >
                        {RISK_LEVEL_LABELS[b.risk.risk_level]}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Per-Building BHI + Radar */}
          {data.blocks.map((b) => {
            const dimScores: Record<DimensionInfo["key"], number> = {
              structural_safety: b.health.structural_safety,
              facility_condition: b.health.facility_condition,
              environmental_quality: b.health.environmental_quality,
              energy_performance: b.health.energy_performance,
              fire_safety: b.health.fire_safety,
            };
            return (
              <Card
                key={b.building.id}
                title={`${b.building.name} · BHI Profile`}
                subtitle={`${b.health.calculation_version} · Prototype · Weights sum to ${(
                  Object.values(BHI_WEIGHTS).reduce((s, w) => s + w, 0) * 100
                ).toFixed(0)}%`}
              >
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-1">
                    <BhiRadar scores={dimScores} height={220} />
                  </div>
                  <div className="lg:col-span-2">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Dimension</th>
                          <th className="text-right">Score</th>
                          <th className="text-right">Weight</th>
                          <th>Explanation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(Object.keys(BHI_WEIGHTS) as DimensionInfo["key"][]).map(
                          (k) => (
                            <tr key={k}>
                              <td>{DIMENSION_LABELS[k]}</td>
                              <td className="text-right font-mono">
                                {formatNumber(b.health[k])}
                              </td>
                              <td className="text-right font-mono text-slate-500">
                                {(BHI_WEIGHTS[k] * 100).toFixed(0)}%
                              </td>
                              <td className="text-xs text-slate-500">
                                {b.health.explanation
                                  .replace(/^Prototype assessment.*yields BHI=[\d.]+\.\s*/, "")
                                  .split(". ")[0] +
                                  "."}
                              </td>
                            </tr>
                          ),
                        )}
                      </tbody>
                    </table>
                    <div className="mt-3 px-3 py-2 bg-blue-50 border border-blue-100 rounded text-xs text-blue-800 leading-relaxed">
                      <span className="font-medium">Why: </span>
                      {b.risk.explanation}
                      <br />
                      <span className="font-medium">Recommended Action: </span>
                      Further professional inspection is recommended. This is an
                      auxiliary recommendation only, not an automated structural
                      reinforcement plan.
                    </div>
                    <div className="mt-2 text-right">
                      <Link
                        to={`/buildings/${b.building.id}`}
                        className="text-xs text-blue-700 hover:underline"
                      >
                        View full detail →
                      </Link>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}

          {/* Risk Alerts 全表 */}
          <Card
            title="All Active Risk Alerts"
            subtitle={`${data.alerts.length} active prototype anomalies (sorted by severity then time)`}
          >
            {data.alerts.length === 0 ? (
              <EmptyState
                title="No active alerts"
                hint="All monitored metrics are within prototype thresholds"
              />
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Building</th>
                    <th>Metric</th>
                    <th className="text-right">Current</th>
                    <th className="text-right">Baseline</th>
                    <th className="text-right">Change</th>
                    <th>Method</th>
                    <th>Severity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.alerts.slice(0, 50).map((a) => (
                    <tr key={a.id}>
                      <td className="font-mono text-xs">
                        {formatTimestamp(a.timestamp)}
                      </td>
                      <td>
                        <Link
                          to={`/buildings/${a.building_id}`}
                          className="text-blue-700 hover:underline"
                        >
                          {a.building_name}
                        </Link>
                      </td>
                      <td className="font-mono text-xs">
                        {METRIC_LABELS[a.metric as keyof typeof METRIC_LABELS] ??
                          a.metric}
                      </td>
                      <td className="text-right font-mono">
                        {formatNumber(a.current_value)}
                      </td>
                      <td className="text-right font-mono">
                        {a.baseline_value !== null
                          ? formatNumber(a.baseline_value)
                          : "—"}
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
                      <td className="text-xs">
                        <Badge
                          color={
                            a.status === "active"
                              ? "amber"
                              : a.status === "resolved"
                                ? "green"
                                : "slate"
                          }
                        >
                          {a.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Legend */}
          <Card title="Risk Level Reference" subtitle="Prototype Risk Classification v1.0">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              {(
                ["Normal", "Attention", "Abnormal", "HighRisk"] as Array<
                  keyof RiskDistribution
                >
              ).map((k) => (
                <div key={k} className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-sm"
                    style={{ background: RISK_LEVEL_COLORS[k] }}
                  />
                  <span className="font-medium">{RISK_LEVEL_LABELS[k]}</span>
                  <span className="text-xs text-slate-500">
                    ({k === "Normal"
                      ? "90-100"
                      : k === "Attention"
                        ? "75-89"
                        : k === "Abnormal"
                          ? "60-74"
                          : "0-59"})
                  </span>
                </div>
              ))}
            </div>
            <p className="text-xs text-amber-700 mt-3">
              Prototype Risk Classification only. Not a legally binding building safety grade.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}

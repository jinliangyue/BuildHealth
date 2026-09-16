/**
 * Building Detail · 单建筑档案 + BHI + 监测趋势 + 异常
 */
import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import { Card, LoadingState, ErrorState, EmptyState, Badge } from "../components/ui/StateViews";
import BhiRadar from "../components/charts/BhiRadar";
import TrendChart from "../components/charts/TrendChart";
import { buildingsApi } from "../api/buildings";
import { healthApi } from "../api/health";
import { riskApi } from "../api/risk";
import { monitoringApi } from "../api/monitoring";
import { retrofitApi } from "../api/retrofit";
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
  type Sensor,
  type HealthAssessment,
  type RiskClassification,
  type RiskAlert,
  type DimensionInfo,
  type RetrofitDecision,
} from "../types/api";
import PriorityScoreCard from "../components/retrofit/PriorityScoreCard";
import PriorityRankingList from "../components/retrofit/PriorityRankingList";
import RecommendationDetail from "../components/retrofit/RecommendationDetail";

interface DetailPayload {
  building: Building;
  sensors: Sensor[];
  health: HealthAssessment;
  risk: RiskClassification;
  alerts: RiskAlert[];
  crackSeries: { ts: string; value: number }[];
  crackAnomalies: { ts: string; value: number; severity: "low" | "medium" | "high"; method: string }[];
  crackUnit: string;
}

export default function BuildingDetail() {
  const { id } = useParams<{ id: string }>();
  const buildingId = Number(id);
  const [selectedRecId, setSelectedRecId] = useState<number | undefined>(undefined);

  const { data, loading, error, refetch } = useApi(async (): Promise<DetailPayload | null> => {
    if (!Number.isFinite(buildingId)) return null;
    const building = await buildingsApi.get(buildingId);
    const sensors = await buildingsApi.sensors(buildingId);
    const health = await healthApi.get(buildingId);
    const risk = await riskApi.classify(buildingId);
    const alerts = await riskApi.alerts(buildingId, true);

    // 拉取 crack_width 趋势
    const crackSensor = sensors.find((s) => s.sensor_type === "crack_width");
    let crackSeries: { ts: string; value: number }[] = [];
    let crackAnomalies: DetailPayload["crackAnomalies"] = [];
    let crackUnit = "mm";
    if (crackSensor) {
      crackUnit = crackSensor.unit;
      const records = await monitoringApi.query({
        sensor_id: crackSensor.id,
        limit: 500,
      });
      crackSeries = records.map((r) => ({ ts: r.timestamp, value: r.value }));
      crackAnomalies = alerts
        .filter((a) => a.sensor_id === crackSensor.id)
        .map((a) => ({
          ts: a.timestamp,
          value: a.current_value,
          severity: a.severity,
          method: a.detection_method,
        }));
    }

    return {
      building,
      sensors,
      health,
      risk,
      alerts,
      crackSeries,
      crackAnomalies,
      crackUnit,
    };
  }, [buildingId]);

  // Retrofit decision (独立 useApi 以便 tab 切换不影响 overview)
  const { data: retrofitData, loading: retrofitLoading, error: retrofitError, refetch: refetchRetrofit } = useApi(
    async (): Promise<RetrofitDecision | null> => {
      if (!Number.isFinite(buildingId)) return null;
      try {
        return await retrofitApi.decision(buildingId);
      } catch {
        return null;
      }
    },
    [buildingId],
  );

  const dimensionRows = useMemo<DimensionInfo[]>(() => {
    if (!data) return [];
    const dims: DimensionInfo["key"][] = [
      "structural_safety",
      "facility_condition",
      "environmental_quality",
      "energy_performance",
      "fire_safety",
    ];
    return dims.map((k) => ({
      key: k,
      label: DIMENSION_LABELS[k],
      weight: BHI_WEIGHTS[k],
      score: data.health[k],
    }));
  }, [data]);

  if (loading) return <LoadingState label="Loading building detail..." />;
  if (error) return <ErrorState message={error} onRetry={refetch} />;
  if (!data)
    return (
      <EmptyState
        title="Building not found"
        hint="Check the building ID in the URL"
      />
    );

  const { building, sensors, health, risk, alerts, crackSeries, crackAnomalies, crackUnit } = data;
  const dimScores: Record<DimensionInfo["key"], number> = {
    structural_safety: health.structural_safety,
    facility_condition: health.facility_condition,
    environmental_quality: health.environmental_quality,
    energy_performance: health.energy_performance,
    fire_safety: health.fire_safety,
  };

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <TopBar
        title={building.name}
        subtitle={`Building #${building.id} · ${building.address}`}
        right={
          <Link
            to="/buildings"
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            ← Back to Buildings
          </Link>
        }
      />

      {/* Building Summary */}
      <Card title="Building Summary">
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-3 text-sm">
          <Field label="Address" value={building.address} />
          <Field label="Built Year" value={String(building.year_built)} mono />
          <Field label="Building Type" value={building.building_type} />
          <Field label="Structure Type" value={building.structure_type} />
          <Field label="Floors" value={String(building.floors)} mono />
          <Field label="Area" value={`${formatNumber(building.area, 0)} ㎡`} mono />
          <Field
            label="Design Life"
            value={`${building.design_life} years`}
            mono
          />
          <Field
            label="Current Age"
            value={`${building.current_age} years`}
            mono
          />
        </dl>
      </Card>

      {/* Health Overview */}
      <Card title="Health Overview">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-1 flex flex-col items-center justify-center border-r border-slate-100 pr-4">
            <div className="text-xs text-slate-500 uppercase tracking-wide">
              Building Health Index
            </div>
            <div className="text-5xl font-bold text-slate-900 mt-2 font-mono">
              {formatNumber(health.score)}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {health.calculation_version} · Prototype
            </div>
          </div>
          <div className="md:col-span-1 flex flex-col items-center justify-center">
            <div className="text-xs text-slate-500 uppercase tracking-wide">
              Risk Level
            </div>
            <div className="mt-3">
              <Badge
                color={
                  risk.risk_level === "Normal"
                    ? "green"
                    : risk.risk_level === "Attention"
                      ? "amber"
                      : risk.risk_level === "Abnormal"
                        ? "orange"
                        : "red"
                }
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
                  style={{ background: RISK_LEVEL_COLORS[risk.risk_level] }}
                />
                {RISK_LEVEL_LABELS[risk.risk_level]}
              </Badge>
            </div>
            <div className="text-xs text-slate-400 mt-2 text-center px-2 leading-snug">
              {risk.n_high} high · {risk.n_medium} medium alerts
            </div>
          </div>
          <div className="md:col-span-2">
            <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">
              Risk Explanation
            </div>
            <p className="text-sm text-slate-700 leading-relaxed">
              {risk.explanation}
            </p>
            <p className="text-xs text-amber-700 mt-2">
              Prototype assessment only. Further professional inspection is recommended.
            </p>
          </div>
        </div>
      </Card>

      {/* 5 Dimensions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Five Dimensions (Radar)">
          <BhiRadar scores={dimScores} />
        </Card>
        <Card title="Dimension Scores & Weights">
          <table className="data-table">
            <thead>
              <tr>
                <th>Dimension</th>
                <th className="text-right">Score</th>
                <th className="text-right">Weight</th>
                <th className="text-right">Contribution</th>
              </tr>
            </thead>
            <tbody>
              {dimensionRows.map((d) => (
                <tr key={d.key}>
                  <td>{d.label}</td>
                  <td className="text-right font-mono">
                    {formatNumber(d.score)}
                  </td>
                  <td className="text-right font-mono text-slate-500">
                    {(d.weight * 100).toFixed(0)}%
                  </td>
                  <td className="text-right font-mono">
                    {formatNumber(d.score * d.weight)}
                  </td>
                </tr>
              ))}
              <tr className="font-semibold bg-slate-50">
                <td>BHI (Weighted Sum)</td>
                <td></td>
                <td className="text-right font-mono">100%</td>
                <td className="text-right font-mono">
                  {formatNumber(health.score)}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="text-xs text-slate-500 mt-3 leading-relaxed">
            {health.explanation}
          </p>
        </Card>
      </div>

      {/* Monitoring Overview */}
      <Card
        title={`Monitoring Overview · ${METRIC_LABELS.crack_width}`}
        subtitle="Most recent 500 records · anomaly points overlaid from active alerts"
      >
        {crackSeries.length === 0 ? (
          <EmptyState
            title="No monitoring records"
            hint="Try recomputing health to refresh data"
          />
        ) : (
          <TrendChart
            series={crackSeries}
            anomalies={crackAnomalies}
            unit={crackUnit}
            metricLabel={METRIC_LABELS.crack_width}
          />
        )}
      </Card>

      {/* Active Alerts */}
      <Card
        title="Active Alerts"
        subtitle={`${alerts.length} active prototype anomalies`}
      >
        {alerts.length === 0 ? (
          <EmptyState
            title="No active alerts"
            hint="All monitored metrics are within prototype thresholds"
          />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Metric</th>
                <th className="text-right">Current</th>
                <th className="text-right">Baseline</th>
                <th className="text-right">Change</th>
                <th>Method</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {alerts.slice(0, 20).map((a) => (
                <tr key={a.id}>
                  <td className="font-mono text-xs">
                    {formatTimestamp(a.timestamp)}
                  </td>
                  <td className="font-mono text-xs">{a.metric}</td>
                  <td className="text-right font-mono">
                    {formatNumber(a.current_value)}
                  </td>
                  <td className="text-right font-mono">
                    {a.baseline_value !== null ? formatNumber(a.baseline_value) : "—"}
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

      {/* Sensors 摘要 */}
      <Card title="Sensors">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {sensors.map((s) => (
            <div
              key={s.id}
              className="border border-slate-200 rounded p-3 bg-slate-50"
            >
              <div className="text-xs text-slate-500 uppercase">
                {METRIC_LABELS[s.sensor_type] ?? s.sensor_type}
              </div>
              <div className="text-sm font-medium text-slate-800 mt-1">
                {s.name}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Unit: {s.unit} · {s.status}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Phase 4 V2 · Retrofit Decision Tab */}
      <Card
        title="Retrofit Decision"
        subtitle="Prototype priority + recommendations + engineering notes"
        right={
          <button
            onClick={refetchRetrofit}
            className="text-xs px-2.5 py-1 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      >
        {retrofitLoading && <LoadingState label="Loading retrofit decision..." />}
        {retrofitError && <ErrorState message={retrofitError} onRetry={refetchRetrofit} />}
        {retrofitData && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <PriorityScoreCard
                score={retrofitData.overall_priority}
                level={retrofitData.overall_priority_level}
                calculationVersion={retrofitData.calculation_version}
                subtitle={`${retrofitData.recommendations.length} recommendations`}
              />
              <div>
                <h4 className="text-sm font-semibold text-slate-800 mb-2">
                  Priority Ranking
                </h4>
                <PriorityRankingList
                  items={retrofitData.recommendations}
                  selectedId={selectedRecId}
                  onSelect={(rec) => setSelectedRecId(rec.id)}
                  showHeader={false}
                />
              </div>
            </div>

            {selectedRecId && (
              (() => {
                const rec = retrofitData.recommendations.find(
                  (r) => r.id === selectedRecId,
                );
                if (!rec) return null;
                return <RecommendationDetail rec={rec} />;
              })()
            )}

            {/* Engineering Notes */}
            {retrofitData.engineering_notes.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-slate-800 mb-2">
                  Engineering Notes
                </h4>
                <ul className="space-y-2">
                  {retrofitData.engineering_notes.map((n) => (
                    <li
                      key={n.id}
                      className="border border-slate-200 rounded p-2 bg-slate-50"
                    >
                      <div className="text-xs text-slate-500 mb-0.5">
                        {n.source} · {formatTimestamp(n.created_at)}
                      </div>
                      <div className="text-sm text-slate-700">{n.text}</div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Disclaimer */}
            <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800 leading-relaxed">
              {retrofitData.disclaimer}
            </div>
          </div>
        )}
      </Card>

      {/* Phase 5 V3 · AI Engineering Assistant 入口 */}
      <Card
        title="AI Engineering Assistant"
        subtitle="Explanation layer (Mock provider) over existing BHI / Risk / Retrofit data"
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <Link
            to={`/ai-assistant?building_id=${buildingId}&q=${encodeURIComponent(
              "Summarize the current building health status",
            )}`}
            className="text-xs px-3 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 text-center"
          >
            Explain Health
          </Link>
          <Link
            to={`/ai-assistant?building_id=${buildingId}&q=${encodeURIComponent(
              "Explain the current risk level and why",
            )}`}
            className="text-xs px-3 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 text-center"
          >
            Explain Risk
          </Link>
          <Link
            to={`/ai-assistant?building_id=${buildingId}&q=${encodeURIComponent(
              "Explain the retrofit priorities",
            )}`}
            className="text-xs px-3 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 text-center"
          >
            Explain Retrofit Priority
          </Link>
        </div>
        <div className="mt-2 text-[11px] text-slate-500">
          AI response is grounded in the V1 BHI / Risk and V2 Retrofit Priority
          values shown above. Mock provider by default; no real LLM is invoked.
        </div>
      </Card>
    </div>
  );
}

function Field({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-slate-500 uppercase tracking-wide">{label}</dt>
      <dd className={`mt-0.5 text-slate-800 ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

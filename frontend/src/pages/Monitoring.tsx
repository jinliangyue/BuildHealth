/**
 * Monitoring · 监测数据查询 + 时序图 + 统计
 */
import { useEffect, useMemo, useState } from "react";
import TopBar from "../components/layout/TopBar";
import { Card, LoadingState, ErrorState, EmptyState } from "../components/ui/StateViews";
import TrendChart from "../components/charts/TrendChart";
import { buildingsApi } from "../api/buildings";
import { monitoringApi } from "../api/monitoring";
import { riskApi } from "../api/risk";
import { useApi } from "../hooks/useApi";
import { formatNumber } from "../hooks/format";
import {
  METRIC_LABELS,
  type Building,
  type Sensor,
  type RiskAlert,
  type Metric,
} from "../types/api";

export default function Monitoring() {
  const { data: buildings } = useApi(() => buildingsApi.list());

  const [buildingId, setBuildingId] = useState<number | null>(null);
  const [sensorId, setSensorId] = useState<number | null>(null);
  const [days, setDays] = useState<number>(30);

  // 初始化默认选第一个建筑
  useEffect(() => {
    if (buildings && buildings.length > 0 && buildingId === null) {
      setBuildingId(buildings[0].id);
    }
  }, [buildings, buildingId]);

  // 拉取选中建筑的 sensors
  const { data: sensors } = useApi<Sensor[]>(
    async () => (buildingId ? buildingsApi.sensors(buildingId) : []),
    [buildingId],
  );

  // 默认选第一个 sensor
  useEffect(() => {
    if (sensors && sensors.length > 0 && sensorId === null) {
      setSensorId(sensors[0].id);
    }
  }, [sensors, sensorId]);

  // 切换建筑时清空 sensor
  useEffect(() => {
    setSensorId(null);
  }, [buildingId]);

  const currentSensor = useMemo(
    () => sensors?.find((s) => s.id === sensorId) ?? null,
    [sensors, sensorId],
  );

  // 计算时间窗口
  const end = useMemo(() => new Date(), []);
  const start = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d;
  }, [days]);

  // 拉取监测数据 + 对应建筑的 alerts
  const { data, loading, error, refetch } = useApi(
    async () => {
      if (!sensorId || !currentSensor || !buildingId) {
        return { records: [], alerts: [] };
      }
      const records = await monitoringApi.query({
        sensor_id: sensorId,
        start: start.toISOString(),
        end: end.toISOString(),
        limit: 2000,
      });
      const alerts = await riskApi.alerts(buildingId, true);
      return { records, alerts };
    },
    [sensorId, currentSensor, buildingId, start, end],
  );

  const series = useMemo(
    () =>
      data?.records.map((r) => ({ ts: r.timestamp, value: r.value })) ?? [],
    [data],
  );

  const anomalyPoints = useMemo(() => {
    if (!data || !currentSensor) return [];
    return data.alerts
      .filter((a) => a.sensor_id === currentSensor.id)
      .map((a: RiskAlert) => ({
        ts: a.timestamp,
        value: a.current_value,
        severity: a.severity,
        method: a.detection_method,
      }));
  }, [data, currentSensor]);

  const stats = useMemo(() => {
    if (!data || data.records.length === 0) {
      return { min: null, max: null, avg: null, latest: null, anomalyCount: 0 };
    }
    const values = data.records.map((r) => r.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const latest = data.records[data.records.length - 1].value;
    const anomalyCount = anomalyPoints.length;
    return { min, max, avg, latest, anomalyCount };
  }, [data, anomalyPoints]);

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <TopBar
        title="Monitoring"
        subtitle="Query sensor records · trend chart · anomaly overlay"
        right={
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      />

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-3 items-end">
          <SelectField label="Building">
            <select
              value={buildingId ?? ""}
              onChange={(e) => setBuildingId(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border border-slate-300 rounded w-56"
            >
              <option value="" disabled>
                Select building
              </option>
              {(buildings ?? []).map((b: Building) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </SelectField>
          <SelectField label="Sensor">
            <select
              value={sensorId ?? ""}
              onChange={(e) => setSensorId(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border border-slate-300 rounded w-56"
              disabled={!sensors || sensors.length === 0}
            >
              <option value="" disabled>
                Select sensor
              </option>
              {(sensors ?? []).map((s: Sensor) => (
                <option key={s.id} value={s.id}>
                  {METRIC_LABELS[s.sensor_type as Metric] ?? s.sensor_type} · {s.name}
                </option>
              ))}
            </select>
          </SelectField>
          <SelectField label="Range">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border border-slate-300 rounded w-32"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={60}>Last 60 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </SelectField>
        </div>
      </Card>

      {/* Chart */}
      <Card
        title={
          currentSensor
            ? `${METRIC_LABELS[currentSensor.sensor_type as Metric] ?? currentSensor.sensor_type} · ${currentSensor.name}`
            : "Trend Chart"
        }
        subtitle={
          currentSensor
            ? `Unit: ${currentSensor.unit} · status: ${currentSensor.status}`
            : "Select a sensor to view trend"
        }
      >
        {loading && <LoadingState label="Loading records..." />}
        {error && <ErrorState message={error} onRetry={refetch} />}
        {!loading && !error && series.length === 0 && (
          <EmptyState
            title="No monitoring records found"
            hint="Try a different sensor or expand the date range"
          />
        )}
        {!loading && !error && series.length > 0 && currentSensor && (
          <TrendChart
            series={series}
            anomalies={anomalyPoints}
            unit={currentSensor.unit}
            metricLabel={METRIC_LABELS[currentSensor.sensor_type as Metric] ?? currentSensor.sensor_type}
            height={360}
          />
        )}
      </Card>

      {/* Stats */}
      {data && data.records.length > 0 && currentSensor && (
        <Card title="Statistics" subtitle="Computed from current query window">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <StatTile label="Records" value={String(data.records.length)} />
            <StatTile
              label={`Min (${currentSensor.unit})`}
              value={stats.min !== null ? formatNumber(stats.min) : "—"}
            />
            <StatTile
              label={`Max (${currentSensor.unit})`}
              value={stats.max !== null ? formatNumber(stats.max) : "—"}
            />
            <StatTile
              label={`Avg (${currentSensor.unit})`}
              value={stats.avg !== null ? formatNumber(stats.avg) : "—"}
            />
            <StatTile
              label="Anomaly Count"
              value={String(stats.anomalyCount)}
              tone={stats.anomalyCount > 0 ? "danger" : "ok"}
            />
          </div>
        </Card>
      )}
    </div>
  );
}

function SelectField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">
        {label}
      </div>
      {children}
    </label>
  );
}

function StatTile({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "neutral" | "ok" | "danger";
}) {
  const cls =
    tone === "danger"
      ? "text-red-600"
      : tone === "ok"
        ? "text-emerald-600"
        : "text-slate-800";
  return (
    <div className="border border-slate-200 rounded p-3 bg-slate-50">
      <div className="text-xs text-slate-500 uppercase tracking-wide">
        {label}
      </div>
      <div className={`text-xl font-semibold mt-1 font-mono ${cls}`}>{value}</div>
    </div>
  );
}

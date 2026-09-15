/**
 * Buildings · 建筑列表
 * 数据源：GET /api/buildings + /buildings/{id}/health + /buildings/{id}/risk
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import { Card, LoadingState, ErrorState, Badge } from "../components/ui/StateViews";
import { buildingsApi } from "../api/buildings";
import { healthApi } from "../api/health";
import { riskApi } from "../api/risk";
import { useApi } from "../hooks/useApi";
import { formatNumber } from "../hooks/format";
import {
  RISK_LEVEL_COLORS,
  RISK_LEVEL_LABELS,
  type Building,
  type HealthAssessment,
  type RiskClassification,
  type RiskLevel,
} from "../types/api";

interface BuildingRow extends Building {
  bhi: number | null;
  risk_level: RiskLevel | null;
  n_high: number;
  n_medium: number;
}

export default function Buildings() {
  const { data, loading, error, refetch } = useApi(async () => {
    const buildings = await buildingsApi.list();
    const rows = await Promise.all(
      buildings.map(async (b): Promise<BuildingRow> => {
        let bhi: number | null = null;
        let risk: RiskClassification | null = null;
        let health: HealthAssessment | null = null;
        try {
          health = await healthApi.get(b.id);
          bhi = health.score;
        } catch {
          // 没有评估时跳过
        }
        try {
          if (health) risk = await riskApi.classify(b.id);
        } catch {
          // 没有评估时跳过
        }
        return {
          ...b,
          bhi,
          risk_level: risk?.risk_level ?? null,
          n_high: risk?.n_high ?? 0,
          n_medium: risk?.n_medium ?? 0,
        };
      }),
    );
    return rows;
  });

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [sortKey, setSortKey] = useState<"bhi" | "year_built" | "floors">("bhi");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filtered = useMemo(() => {
    if (!data) return [];
    let rows = [...data];
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          r.address.toLowerCase().includes(q) ||
          r.building_type.toLowerCase().includes(q),
      );
    }
    if (riskFilter !== "all") {
      rows = rows.filter((r) => r.risk_level === riskFilter);
    }
    rows.sort((a, b) => {
      let av: number | null;
      let bv: number | null;
      if (sortKey === "bhi") {
        av = a.bhi;
        bv = b.bhi;
      } else if (sortKey === "year_built") {
        av = a.year_built;
        bv = b.year_built;
      } else {
        av = a.floors;
        bv = b.floors;
      }
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return rows;
  }, [data, search, riskFilter, sortKey, sortDir]);

  const toggleSort = (k: typeof sortKey) => {
    if (k === sortKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(k);
      setSortDir("asc");
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <TopBar
        title="Buildings"
        subtitle={`${data?.length ?? 0} monitored buildings`}
        right={
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      />

      {loading && <LoadingState label="Loading buildings..." />}
      {error && <ErrorState message={error} onRetry={refetch} />}
      {data && (
        <Card>
          {/* Filters */}
          <div className="flex flex-wrap gap-3 mb-4">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name / address / type"
              className="px-3 py-1.5 text-sm border border-slate-300 rounded w-72"
            />
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value as RiskLevel | "all")}
              className="px-3 py-1.5 text-sm border border-slate-300 rounded"
            >
              <option value="all">All Risk Levels</option>
              <option value="Normal">Normal</option>
              <option value="Attention">Attention</option>
              <option value="Abnormal">Abnormal</option>
              <option value="HighRisk">High Risk</option>
            </select>
            <span className="ml-auto text-xs text-slate-500 self-center">
              Showing {filtered.length} / {data.length}
            </span>
          </div>

          {/* Table */}
          {filtered.length === 0 ? (
            <div className="text-sm text-slate-500 py-8 text-center">
              No buildings match current filters
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Structure</th>
                  <th
                    className="cursor-pointer select-none"
                    onClick={() => toggleSort("year_built")}
                  >
                    Built {sortKey === "year_built" && (sortDir === "asc" ? "↑" : "↓")}
                  </th>
                  <th
                    className="cursor-pointer select-none"
                    onClick={() => toggleSort("floors")}
                  >
                    Floors {sortKey === "floors" && (sortDir === "asc" ? "↑" : "↓")}
                  </th>
                  <th className="text-right">Area (㎡)</th>
                  <th
                    className="text-right cursor-pointer select-none"
                    onClick={() => toggleSort("bhi")}
                  >
                    BHI {sortKey === "bhi" && (sortDir === "asc" ? "↑" : "↓")}
                  </th>
                  <th>Risk Level</th>
                  <th className="text-right">High Alerts</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((b) => (
                  <tr key={b.id}>
                    <td>
                      <Link
                        to={`/buildings/${b.id}`}
                        className="text-blue-700 hover:underline font-medium"
                      >
                        {b.name}
                      </Link>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {b.address}
                      </div>
                    </td>
                    <td className="text-xs">{b.building_type}</td>
                    <td className="text-xs">{b.structure_type}</td>
                    <td className="font-mono">{b.year_built}</td>
                    <td className="font-mono">{b.floors}</td>
                    <td className="text-right font-mono">
                      {formatNumber(b.area, 0)}
                    </td>
                    <td className="text-right font-mono">
                      {b.bhi !== null ? formatNumber(b.bhi) : "—"}
                    </td>
                    <td>
                      {b.risk_level ? (
                        <Badge
                          color={
                            b.risk_level === "Normal"
                              ? "green"
                              : b.risk_level === "Attention"
                                ? "amber"
                                : b.risk_level === "Abnormal"
                                  ? "orange"
                                  : "red"
                          }
                        >
                          <span
                            className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
                            style={{ background: RISK_LEVEL_COLORS[b.risk_level] }}
                          />
                          {RISK_LEVEL_LABELS[b.risk_level]}
                        </Badge>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="text-right">
                      {b.n_high > 0 ? (
                        <span className="text-red-600 font-mono text-sm">
                          {b.n_high}
                        </span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}

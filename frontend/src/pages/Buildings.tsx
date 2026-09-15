/**
 * Buildings · 建筑列表
 * 使用 /api/buildings/overview 批量接口（1 次请求 · 替代 N+1）
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import { Card, LoadingState, ErrorState, Badge } from "../components/ui/StateViews";
import { buildingsApi, type BuildingOverview } from "../api/buildings";
import { useApi } from "../hooks/useApi";
import { formatNumber } from "../hooks/format";
import {
  RISK_LEVEL_COLORS,
  RISK_LEVEL_LABELS,
  type RiskLevel,
} from "../types/api";

export default function Buildings() {
  const { data, loading, error, refetch } = useApi(() => buildingsApi.overview());

  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [sortKey, setSortKey] = useState<"bhi" | "year_built" | "floors">("bhi");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filtered = useMemo<BuildingOverview[]>(() => {
    if (!data) return [];
    let rows = [...data.items];
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(
        (r) =>
          r.building.name.toLowerCase().includes(q) ||
          r.building.address.toLowerCase().includes(q) ||
          r.building.building_type.toLowerCase().includes(q),
      );
    }
    if (riskFilter !== "all") {
      rows = rows.filter((r) => r.risk?.risk_level === riskFilter);
    }
    rows.sort((a, b) => {
      const av = sortKey === "bhi" ? a.health?.score ?? null : sortKey === "year_built" ? a.building.year_built : a.building.floors;
      const bv = sortKey === "bhi" ? b.health?.score ?? null : sortKey === "year_built" ? b.building.year_built : b.building.floors;
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
        subtitle={`${data?.total ?? 0} monitored buildings · single batch request`}
        right={
          <button
            onClick={() => void refetch()}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      />

      {loading && <LoadingState label="Loading buildings..." />}
      {error && <ErrorState message={error} onRetry={() => void refetch()} />}
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
              Showing {filtered.length} / {data.total}
            </span>
          </div>

          {/* Table */}
          {filtered.length === 0 ? (
            <div className="text-sm text-slate-500 py-8 text-center">
              No buildings match current filters
            </div>
          ) : (
            <div className="overflow-x-auto">
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
                {filtered.map((row) => {
                  const b = row.building;
                  const bhi = row.health?.score ?? null;
                  const riskLevel = row.risk?.risk_level ?? null;
                  return (
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
                        {bhi !== null ? formatNumber(bhi) : "—"}
                      </td>
                      <td>
                        {riskLevel ? (
                          <Badge
                            color={
                              riskLevel === "Normal"
                                ? "green"
                                : riskLevel === "Attention"
                                  ? "amber"
                                  : riskLevel === "Abnormal"
                                    ? "orange"
                                    : "red"
                            }
                          >
                            <span
                              className="inline-block w-1.5 h-1.5 rounded-full mr-1.5"
                              style={{ background: RISK_LEVEL_COLORS[riskLevel] }}
                            />
                            {RISK_LEVEL_LABELS[riskLevel]}
                          </Badge>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                      <td className="text-right">
                        {row.active_alert_count > 0 ? (
                          <span className="text-red-600 font-mono text-sm">
                            {row.active_alert_count}
                          </span>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

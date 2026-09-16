/**
 * Retrofit Decision · Phase 4 V2
 * 跨建筑 retrofit overview 页面.
 * 显示 KPI, 优先级排序, 工程笔记摘要, 强制 disclaimer.
 */
import { Link } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import {
  Card,
  LoadingState,
  ErrorState,
  KPITile,
} from "../components/ui/StateViews";
import { retrofitApi } from "../api/retrofit";
import { useApi } from "../hooks/useApi";
import { formatNumber } from "../hooks/format";
import {
  CATEGORY_LABELS,
  PRIORITY_LEVEL_COLORS,
  PRIORITY_LEVEL_LABELS,
  type RetrofitCategory,
  type RetrofitOverviewResponse,
} from "../types/api";

export default function RetrofitDecision() {
  const { data, loading, error, refetch } = useApi(
    async (): Promise<RetrofitOverviewResponse> => {
      return await retrofitApi.overview();
    },
  );

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <TopBar
        title="Retrofit Decision"
        subtitle="Cross-building retrofit priority overview (Prototype Decision Support)"
        right={
          <button
            onClick={refetch}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
        }
      />

      {loading && <LoadingState label="Loading retrofit decisions..." />}
      {error && <ErrorState message={error} onRetry={refetch} />}

      {data && (
        <>
          {/* Top KPI Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPITile
              label="Buildings Requiring Attention"
              value={data.items.filter((i) => i.recommendation_count > 0).length}
              hint={`of ${data.total} buildings`}
              tone={data.items.some((i) => i.high_priority_count > 0) ? "warning" : "ok"}
            />
            <KPITile
              label="Average Retrofit Priority"
              value={formatNumber(data.average_priority, 1)}
              hint={`calculation ${data.calculation_version}`}
              tone="neutral"
            />
            <KPITile
              label="High Priority Items"
              value={data.items.reduce((s, i) => s + i.high_priority_count, 0)}
              hint="priority ≥ 75"
              tone={
                data.items.reduce((s, i) => s + i.high_priority_count, 0) > 0
                  ? "danger"
                  : "neutral"
              }
            />
            <KPITile
              label="Total Recommendations"
              value={data.items.reduce((s, i) => s + i.recommendation_count, 0)}
              hint="across all buildings"
              tone="neutral"
            />
          </div>

          {/* Cross-Building Ranking */}
          <Card
            title="Retrofit Priority Ranking"
            subtitle="Sorted by overall priority · click to view building"
          >
            {data.items.length === 0 ? (
              <LoadingState label="No buildings to rank" />
            ) : (
              <div className="space-y-2">
                {data.items.map((item, idx) => {
                  const color =
                    PRIORITY_LEVEL_COLORS[item.overall_priority_level];
                  return (
                    <Link
                      key={item.building.id}
                      to={`/buildings/${item.building.id}`}
                      className="block border border-slate-200 rounded-md p-3 hover:bg-slate-50 transition"
                    >
                      <div className="flex items-center gap-4">
                        <div className="text-2xl font-bold font-mono text-slate-400 w-10 shrink-0">
                          {String(idx + 1).padStart(2, "0")}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-slate-800">
                            {item.building.name}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5">
                            {item.building.address} · {item.building.building_type}{" "}
                            · {item.building.floors}F · age {item.building.current_age}y
                          </div>
                          <div className="mt-1.5 flex items-center gap-2 flex-wrap text-xs">
                            {item.recommendation_count > 0 ? (
                              <>
                                <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded">
                                  {item.recommendation_count} recommendations
                                </span>
                                {item.high_priority_count > 0 && (
                                  <span className="px-1.5 py-0.5 bg-red-50 text-red-700 border border-red-200 rounded">
                                    {item.high_priority_count} high-priority
                                  </span>
                                )}
                                {item.top_category && item.top_category !== "—" && (
                                  <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded">
                                    top: {CATEGORY_LABELS[item.top_category as RetrofitCategory] ?? item.top_category}
                                  </span>
                                )}
                              </>
                            ) : (
                              <span className="text-slate-400 italic">
                                No active recommendations
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div
                            className="text-2xl font-bold font-mono"
                            style={{ color }}
                          >
                            {formatNumber(item.overall_priority, 1)}
                          </div>
                          <div
                            className="text-[10px] uppercase font-medium"
                            style={{ color }}
                          >
                            {PRIORITY_LEVEL_LABELS[item.overall_priority_level]}
                          </div>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Aggregate Insights */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card title="Top Categories" subtitle="Across all active recommendations">
              <CategoryDistribution items={data.items} />
            </Card>
            <Card title="Priority Distribution" subtitle="How buildings distribute across priority levels">
              <PriorityDistribution items={data.items} />
            </Card>
            <Card title="Calculation" subtitle="Prototype Retrofit Priority">
              <div className="text-xs text-slate-600 space-y-1.5">
                <div>
                  <span className="font-mono text-slate-500">v</span>{" "}
                  {data.calculation_version}
                </div>
                <div className="text-slate-500 mt-2">
                  5 weighted dimensions:
                </div>
                <ul className="text-[11px] text-slate-600 space-y-0.5">
                  <li>· Risk Severity 35%</li>
                  <li>· Trend / Deterioration 25%</li>
                  <li>· Component Importance 20%</li>
                  <li>· Intervention Urgency 10%</li>
                  <li>· Cost Efficiency 10%</li>
                </ul>
                <div className="mt-2 text-[11px] text-amber-700">
                  Prototype parameters. Not a national or industry standard.
                </div>
              </div>
            </Card>
          </div>

          {/* Disclaimer */}
          <div className="bg-amber-50 border border-amber-200 rounded-md p-4 text-xs text-amber-800 leading-relaxed">
            <div className="font-semibold mb-1">Engineering Disclaimer</div>
            {data.disclaimer}
          </div>
        </>
      )}
    </div>
  );
}

function CategoryDistribution({
  items,
}: {
  items: RetrofitOverviewResponse["items"];
}) {
  const counts: Record<string, number> = {};
  items.forEach((it) => {
    if (it.top_category && it.top_category !== "—") {
      counts[it.top_category] = (counts[it.top_category] ?? 0) + 1;
    }
  });
  const sorted = Object.entries(counts).sort(([, a], [, b]) => b - a);
  if (sorted.length === 0) {
    return (
      <div className="text-xs text-slate-400 italic">No active categories</div>
    );
  }
  return (
    <ul className="space-y-1.5 text-sm">
      {sorted.slice(0, 6).map(([cat, count]) => (
        <li key={cat} className="flex items-center justify-between">
          <span className="text-slate-700">
            {CATEGORY_LABELS[cat as RetrofitCategory] ?? cat}
          </span>
          <span className="font-mono text-slate-500">{count}</span>
        </li>
      ))}
    </ul>
  );
}

function PriorityDistribution({
  items,
}: {
  items: RetrofitOverviewResponse["items"];
}) {
  const counts: Record<string, number> = {
    Low: 0,
    Medium: 0,
    High: 0,
    "Very High": 0,
  };
  items.forEach((it) => {
    const label = PRIORITY_LEVEL_LABELS[it.overall_priority_level];
    if (label in counts) counts[label]++;
  });
  return (
    <ul className="space-y-1.5 text-sm">
      {Object.entries(counts).map(([level, count]) => (
        <li key={level} className="flex items-center justify-between">
          <span
            className="px-2 py-0.5 rounded text-xs font-medium"
            style={{
              background: `${PRIORITY_LEVEL_COLORS[level as keyof typeof PRIORITY_LEVEL_COLORS]}20`,
              color: PRIORITY_LEVEL_COLORS[level as keyof typeof PRIORITY_LEVEL_COLORS],
            }}
          >
            {level}
          </span>
          <span className="font-mono text-slate-500">{count}</span>
        </li>
      ))}
    </ul>
  );
}

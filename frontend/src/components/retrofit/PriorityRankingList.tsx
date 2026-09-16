/**
 * PriorityRankingList · Phase 4 V2
 * 排序列表 (01/02/03) + priority_score + category badge.
 */
import {
  CATEGORY_LABELS,
  URGENCY_COLORS,
  type RetrofitRecommendation,
} from "../../types/api";
import { EmptyState } from "../ui/StateViews";
import { formatNumber } from "../../hooks/format";

interface Props {
  items: RetrofitRecommendation[];
  selectedId?: number;
  onSelect?: (rec: RetrofitRecommendation) => void;
  showHeader?: boolean;
}

export default function PriorityRankingList({
  items,
  selectedId,
  onSelect,
  showHeader = true,
}: Props) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No retrofit recommendations"
        hint="All monitored metrics are within prototype thresholds. Continue routine monitoring."
      />
    );
  }

  return (
    <ol className="space-y-2">
      {showHeader && (
        <li className="text-xs text-slate-500 uppercase tracking-wide pb-1">
          Priority Ranking
        </li>
      )}
      {items.map((rec, idx) => {
        const isSelected = selectedId === rec.id;
        return (
          <li
            key={rec.id}
            onClick={() => onSelect?.(rec)}
            className={`border rounded-md p-3 transition cursor-pointer ${
              isSelected
                ? "border-blue-400 bg-blue-50"
                : "border-slate-200 bg-white hover:bg-slate-50"
            }`}
          >
            <div className="flex items-start gap-3">
              <div className="text-2xl font-bold font-mono text-slate-400 w-10 shrink-0">
                {String(idx + 1).padStart(2, "0")}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-800 truncate">
                    {rec.title}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-2 flex-wrap text-xs">
                  <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded">
                    {CATEGORY_LABELS[rec.category]}
                  </span>
                  <span
                    className="px-1.5 py-0.5 rounded border font-medium uppercase"
                    style={{
                      background: `${URGENCY_COLORS[rec.urgency]}20`,
                      color: URGENCY_COLORS[rec.urgency],
                      borderColor: URGENCY_COLORS[rec.urgency],
                    }}
                  >
                    {rec.urgency}
                  </span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xl font-bold font-mono text-slate-900">
                  {formatNumber(rec.priority_score, 1)}
                </div>
                <div className="text-[10px] text-slate-400 uppercase">
                  priority
                </div>
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

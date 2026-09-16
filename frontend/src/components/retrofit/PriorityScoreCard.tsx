/**
 * PriorityScoreCard · Phase 4 V2
 * 显示 single priority score + level + RP version + Prototype disclaimer.
 */
import {
  PRIORITY_LEVEL_COLORS,
  PRIORITY_LEVEL_LABELS,
  type RetrofitPriorityLevel,
} from "../../types/api";
import { formatNumber } from "../../hooks/format";

interface Props {
  score: number;
  level: RetrofitPriorityLevel;
  calculationVersion: string;
  subtitle?: string;
}

export default function PriorityScoreCard({
  score,
  level,
  calculationVersion,
  subtitle,
}: Props) {
  const color = PRIORITY_LEVEL_COLORS[level];
  return (
    <div className="bg-white border border-slate-200 rounded-md p-5 shadow-sm">
      <div className="text-xs text-slate-500 uppercase tracking-wide">
        Overall Retrofit Priority
      </div>
      <div className="flex items-baseline gap-3 mt-2">
        <div
          className="text-5xl font-bold font-mono"
          style={{ color }}
        >
          {formatNumber(score, 1)}
        </div>
        <div className="text-sm text-slate-500 font-mono">/ 100</div>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <span
          className="inline-block w-2 h-2 rounded-full"
          style={{ background: color }}
        />
        <span
          className="text-sm font-semibold"
          style={{ color }}
        >
          {PRIORITY_LEVEL_LABELS[level]} Priority
        </span>
      </div>
      {subtitle && (
        <div className="text-xs text-slate-500 mt-2">{subtitle}</div>
      )}
      <div className="mt-3 pt-3 border-t border-slate-100 text-[11px] text-slate-500 leading-relaxed">
        <span className="font-medium text-slate-600">{calculationVersion}</span>{" "}
        · Prototype Retrofit Priority · engineering decision support only.
        All recommendations require qualified professional review.
      </div>
    </div>
  );
}

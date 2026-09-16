/**
 * RecommendationDetail · Phase 4 V2
 * 完整 detail panel: problem / evidence / trend / risk / priority / breakdown / action / benefit / cost.
 */
import {
  CATEGORY_LABELS,
  URGENCY_COLORS,
  COST_LEVEL_COLORS,
  ISSUE_TYPE_LABELS,
  type RetrofitRecommendation,
} from "../../types/api";
import { Card } from "../ui/StateViews";
import EvidenceChain from "./EvidenceChain";
import { formatNumber } from "../../hooks/format";

interface Props {
  rec: RetrofitRecommendation;
}

export default function RecommendationDetail({ rec }: Props) {
  const breakdown = rec.priority_breakdown;
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-md p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500 uppercase tracking-wide">
              {CATEGORY_LABELS[rec.category]} ·{" "}
              {ISSUE_TYPE_LABELS[rec.issue_type] ?? rec.issue_type}
            </div>
            <h3 className="text-base font-semibold text-slate-900 mt-1">
              {rec.title}
            </h3>
            <p className="text-sm text-slate-600 mt-2 leading-relaxed">
              {rec.recommendation}
            </p>
          </div>
          <div className="text-right shrink-0">
            <div className="text-3xl font-bold font-mono text-slate-900">
              {formatNumber(rec.priority_score, 1)}
            </div>
            <div className="text-[10px] text-slate-400 uppercase">
              priority / 100
            </div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-2 text-xs">
          <Badge
            color={URGENCY_COLORS[rec.urgency]}
            label={`Urgency: ${rec.urgency}`}
          />
          <Badge
            color={COST_LEVEL_COLORS[rec.estimated_cost_level]}
            label={`Cost: ${rec.estimated_cost_level}`}
          />
          <Badge color="#3B82F6" label={`Benefit: ${rec.expected_benefit}`} />
          <span className="text-slate-400 font-mono">
            {rec.source} · {rec.calculation_version}
          </span>
        </div>
      </div>

      {/* Priority Breakdown */}
      <Card title="Priority Score Breakdown" subtitle={breakdown.calculation_version}>
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
            <tr>
              <td>Risk Severity</td>
              <td className="text-right font-mono">{formatNumber(breakdown.risk_severity)}</td>
              <td className="text-right font-mono text-slate-500">35%</td>
              <td className="text-right font-mono">
                +{formatNumber(breakdown.risk_severity_contribution)}
              </td>
            </tr>
            <tr>
              <td>Trend / Deterioration</td>
              <td className="text-right font-mono">{formatNumber(breakdown.trend)}</td>
              <td className="text-right font-mono text-slate-500">25%</td>
              <td className="text-right font-mono">
                +{formatNumber(breakdown.trend_contribution)}
              </td>
            </tr>
            <tr>
              <td>Component Importance</td>
              <td className="text-right font-mono">
                {formatNumber(breakdown.component_importance)}
              </td>
              <td className="text-right font-mono text-slate-500">20%</td>
              <td className="text-right font-mono">
                +{formatNumber(breakdown.component_importance_contribution)}
              </td>
            </tr>
            <tr>
              <td>Intervention Urgency</td>
              <td className="text-right font-mono">{formatNumber(breakdown.urgency)}</td>
              <td className="text-right font-mono text-slate-500">10%</td>
              <td className="text-right font-mono">
                +{formatNumber(breakdown.urgency_contribution)}
              </td>
            </tr>
            <tr>
              <td>Cost Efficiency</td>
              <td className="text-right font-mono">
                {formatNumber(breakdown.cost_efficiency)}
              </td>
              <td className="text-right font-mono text-slate-500">10%</td>
              <td className="text-right font-mono">
                +{formatNumber(breakdown.cost_efficiency_contribution)}
              </td>
            </tr>
            <tr className="font-semibold bg-slate-50">
              <td>Total</td>
              <td></td>
              <td className="text-right font-mono">100%</td>
              <td className="text-right font-mono">
                {formatNumber(breakdown.total)}
              </td>
            </tr>
          </tbody>
        </table>
      </Card>

      {/* Rationale + Next Action */}
      <Card title="Engineering Rationale">
        <p className="text-sm text-slate-700 leading-relaxed">{rec.rationale}</p>
      </Card>

      <Card title="Recommended Next Action">
        <p className="text-sm text-slate-700 leading-relaxed">
          {rec.next_action}
        </p>
        <p className="text-xs text-amber-700 mt-2">
          This is a Prototype Retrofit Recommendation. Not an automated
          structural reinforcement plan. Qualified professional review
          required.
        </p>
      </Card>

      {/* Evidence Chain */}
      <Card title="Evidence Chain" subtitle="Trace from monitoring to recommendation">
        <EvidenceChain evidence={rec.evidence} />
      </Card>
    </div>
  );
}

function Badge({ color, label }: { color: string; label: string }) {
  return (
    <span
      className="px-2 py-0.5 rounded border font-medium"
      style={{
        background: `${color}20`,
        color,
        borderColor: color,
      }}
    >
      {label}
    </span>
  );
}

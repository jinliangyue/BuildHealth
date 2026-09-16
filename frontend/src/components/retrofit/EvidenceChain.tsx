/**
 * EvidenceChain · Phase 4 V2
 * 证据链可视化: Sensors → Recent Values → Anomalies → BHI → Risk → Recommendation
 */
import {
  METRIC_LABELS,
  type RetrofitEvidence,
} from "../../types/api";
import { formatNumber } from "../../hooks/format";

interface Props {
  evidence: RetrofitEvidence;
}

export default function EvidenceChain({ evidence }: Props) {
  return (
    <div className="space-y-3">
      {/* Sensors Block */}
      {evidence.sensors.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-700 mb-2">
            Sensors
          </div>
          <div className="space-y-2">
            {evidence.sensors.map((s) => (
              <div
                key={s.sensor_id}
                className="border border-slate-200 rounded p-2 bg-slate-50"
              >
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <span className="text-sm font-medium text-slate-800">
                    {s.name} (sensor #{s.sensor_id})
                  </span>
                  <span className="text-xs text-slate-500">
                    {METRIC_LABELS[s.metric]} · {s.unit} · {s.location}
                  </span>
                </div>
                {/* Anomaly counts */}
                <div className="mt-1 flex items-center gap-2 text-xs">
                  {s.anomaly_count_by_severity.high > 0 && (
                    <span className="px-1.5 py-0.5 bg-red-50 text-red-700 border border-red-200 rounded">
                      H: {s.anomaly_count_by_severity.high}
                    </span>
                  )}
                  {s.anomaly_count_by_severity.medium > 0 && (
                    <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded">
                      M: {s.anomaly_count_by_severity.medium}
                    </span>
                  )}
                  {s.anomaly_count_by_severity.low > 0 && (
                    <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 border border-slate-200 rounded">
                      L: {s.anomaly_count_by_severity.low}
                    </span>
                  )}
                </div>
                {/* Recent values */}
                {s.recent_values.length > 0 && (
                  <div className="mt-2">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wide">
                      Recent Values
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1.5 font-mono text-[11px] text-slate-700">
                      {s.recent_values.slice(-10).map((rv, idx) => (
                        <span
                          key={idx}
                          className="px-1.5 py-0.5 bg-white border border-slate-200 rounded"
                          title={rv.timestamp}
                        >
                          {formatNumber(rv.value, 3)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Anomalies Block */}
      {evidence.anomalies.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-slate-700 mb-2">
            Anomalies ({evidence.anomalies.length})
          </div>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {evidence.anomalies.slice(0, 5).map((a, idx) => (
              <div
                key={idx}
                className="text-xs border-l-2 border-slate-200 pl-2 py-0.5"
              >
                <span className="font-mono text-slate-500">
                  {String(a.timestamp).slice(0, 16)}
                </span>{" "}
                · {a.metric} ·{" "}
                <span
                  className={
                    a.severity === "high"
                      ? "text-red-700 font-medium"
                      : a.severity === "medium"
                        ? "text-amber-700 font-medium"
                        : "text-slate-600"
                  }
                >
                  {a.severity}
                </span>{" "}
                · {a.detection_method}
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {a.explanation}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Context Block */}
      {(evidence.bhi_context || evidence.risk_context) && (
        <div>
          <div className="text-xs font-semibold text-slate-700 mb-2">
            Context
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {evidence.bhi_context && (
              <div className="border border-slate-200 rounded p-2 bg-slate-50">
                <div className="text-[10px] text-slate-500 uppercase">
                  BHI
                </div>
                <div className="text-base font-mono font-semibold text-slate-800">
                  {formatNumber(evidence.bhi_context.score)}
                </div>
                {evidence.bhi_context.weakest_dimension && (
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    weakest: {evidence.bhi_context.weakest_dimension}
                  </div>
                )}
              </div>
            )}
            {evidence.risk_context && (
              <div className="border border-slate-200 rounded p-2 bg-slate-50">
                <div className="text-[10px] text-slate-500 uppercase">
                  Risk
                </div>
                <div className="text-base font-mono font-semibold text-slate-800">
                  {evidence.risk_context.risk_level}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">
                  {evidence.risk_context.explanation}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {evidence.anomaly_summary && (
        <div className="text-xs text-slate-600 px-2 py-1 bg-slate-50 border border-slate-200 rounded">
          Total anomalies: {evidence.anomaly_summary.total} (H:{" "}
          {evidence.anomaly_summary.high} · M: {evidence.anomaly_summary.medium})
        </div>
      )}
    </div>
  );
}

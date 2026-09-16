/**
 * AIResponsePanel · Phase 5 V3 + Phase 6B
 * 渲染 AIResponse: answer + key_findings + evidence + knowledge_evidence
 * + recommended_actions + disclaimer.
 *
 * Phase 6B: engineering Evidence 与 Knowledge Sources 分区渲染,
 * 不混合, 以免把通用知识误读为本建筑证据.
 */
import {
  AI_SEVERITY_COLORS,
  AI_URGENCY_COLORS,
  type AIResponse,
} from "../../types/api";
import EvidenceList from "./EvidenceList";
import KnowledgeEvidenceList from "./KnowledgeEvidenceList";

interface Props {
  response: AIResponse;
}

export default function AIResponsePanel({ response }: Props) {
  // 防御: 旧版后端响应可能没有该字段
  const knowledgeItems = response.knowledge_evidence ?? [];

  return (
    <div className="space-y-4">
      {/* Provider tag */}
      <div className="flex items-center gap-2 text-[11px] text-slate-500 uppercase tracking-wide">
        <span className="px-1.5 py-0.5 bg-slate-100 border border-slate-200 rounded font-mono">
          {response.provider}
        </span>
        <span className="font-mono">{response.model}</span>
        <span className="font-mono">{response.calculation_version}</span>
      </div>

      {/* Answer */}
      <div>
        <h4 className="text-xs text-slate-500 uppercase tracking-wide mb-1">
          Answer
        </h4>
        <div className="text-sm text-slate-800 leading-relaxed whitespace-pre-wrap">
          {response.answer}
        </div>
      </div>

      {/* Key Findings */}
      {response.key_findings.length > 0 && (
        <div>
          <h4 className="text-xs text-slate-500 uppercase tracking-wide mb-2">
            Key Findings
          </h4>
          <ul className="space-y-2">
            {response.key_findings.map((kf, idx) => {
              const color = AI_SEVERITY_COLORS[kf.severity];
              return (
                <li
                  key={idx}
                  className="border-l-2 pl-2 py-1"
                  style={{ borderColor: color }}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-slate-800">
                      {kf.title}
                    </span>
                    <span
                      className="px-1.5 py-0.5 text-[10px] rounded border font-medium uppercase"
                      style={{
                        background: `${color}20`,
                        color,
                        borderColor: color,
                      }}
                    >
                      {kf.severity}
                    </span>
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5">
                    {kf.description}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Evidence (engineering data · 本建筑实测与派生指标) */}
      {response.evidence.length > 0 && (
        <div>
          <h4 className="text-xs text-slate-500 uppercase tracking-wide mb-2">
            Evidence
          </h4>
          <EvidenceList items={response.evidence} />
        </div>
      )}

      {/* Knowledge Sources (Phase 6B · 通用工程知识, 非本建筑证据) */}
      {knowledgeItems.length > 0 && (
        <div>
          <h4 className="text-xs text-violet-600 uppercase tracking-wide mb-2">
            Knowledge Sources
          </h4>
          <KnowledgeEvidenceList items={knowledgeItems} />
        </div>
      )}

      {/* Recommended Actions */}
      {response.recommended_actions.length > 0 && (
        <div>
          <h4 className="text-xs text-slate-500 uppercase tracking-wide mb-2">
            Recommended Actions
          </h4>
          <ul className="space-y-2">
            {response.recommended_actions.map((a, idx) => {
              const color = AI_URGENCY_COLORS[a.urgency];
              return (
                <li
                  key={idx}
                  className="border border-slate-200 rounded p-2 bg-slate-50"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className="px-1.5 py-0.5 text-[10px] rounded border font-medium uppercase"
                      style={{
                        background: `${color}20`,
                        color,
                        borderColor: color,
                      }}
                    >
                      urgency: {a.urgency}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-slate-800 mt-1">
                    {a.action}
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5">{a.reason}</div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-800 leading-relaxed">
        {response.disclaimer}
      </div>
    </div>
  );
}

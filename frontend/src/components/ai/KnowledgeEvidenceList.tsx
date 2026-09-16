/**
 * KnowledgeEvidenceList · Phase 6B
 *
 * 渲染 RAG 检索到的工程知识片段 (knowledge_evidence).
 *
 * 与 EvidenceList 的关键区别:
 * - EvidenceList = engineering data evidence (本建筑实测数据 / 派生指标)
 * - 本组件 = 通用工程知识背景, 不描述本建筑的实际情况
 *
 * 因此这里用独立配色 (violet) 与显式提示语, 避免用户把知识文档
 * 误读为本建筑的证据.
 */
import type { KnowledgeEvidence } from "../../types/api";

interface Props {
  items: KnowledgeEvidence[];
}

/** 0-1 相关度 → 百分比标签 */
function formatRelevance(score: number): string {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  return `${pct}%`;
}

export default function KnowledgeEvidenceList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="text-xs text-slate-400 italic">
        No knowledge sources retrieved.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-violet-700 bg-violet-50 border border-violet-200 rounded px-2 py-1 leading-relaxed">
        General background from BuildHealth Internal Engineering Notes. These are
        not measurements of this building and are not an official standard.
      </p>
      <ul className="space-y-2">
        {items.map((it, idx) => (
          <li
            key={it.chunk_id || idx}
            className="border border-violet-200 rounded p-2 bg-violet-50/40"
          >
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-1.5 py-0.5 bg-violet-100 text-violet-800 border border-violet-200 rounded font-mono text-[10px] shrink-0">
                {it.document}
              </span>
              <span className="text-xs font-medium text-slate-700 flex-1">
                {it.section}
              </span>
              <span
                className="px-1.5 py-0.5 text-[10px] rounded border border-violet-300 text-violet-700 font-mono shrink-0"
                title="Lexical relevance score (TF-IDF cosine)"
              >
                {formatRelevance(it.relevance_score)}
              </span>
            </div>
            <div className="text-xs text-slate-600 mt-1.5 leading-relaxed">
              {it.content}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              {it.source}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * EvidenceList · Phase 5 V3
 * 渲染 evidence 列表, 每项可点击跳转 (如 reference_path 以 /api 开头则视为 API 链接).
 */
import { Link } from "react-router-dom";
import type { AIEvidenceRef } from "../../types/api";

interface Props {
  items: AIEvidenceRef[];
}

const SOURCE_LABELS: Record<string, string> = {
  sensor: "Sensor",
  anomaly: "Anomaly",
  health: "Health",
  risk: "Risk",
  retrofit_recommendation: "Retrofit",
  engineering_note: "Note",
  building: "Building",
};

export default function EvidenceList({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="text-xs text-slate-400 italic">No evidence items.</div>
    );
  }
  return (
    <ul className="space-y-1.5">
      {items.map((it, idx) => {
        // 转换为 frontend 内部路由 (e.g. /api/buildings/1/health → /buildings/1)
        const linkPath = toInternalPath(it.reference_path);
        const content = (
          <div className="flex items-start gap-2 text-xs">
            <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded font-mono text-[10px] uppercase shrink-0">
              {SOURCE_LABELS[it.source_type] ?? it.source_type}
            </span>
            <span className="text-slate-700 flex-1">{it.description}</span>
            {linkPath && (
              <span className="text-blue-600 text-[10px] shrink-0">→</span>
            )}
          </div>
        );
        return (
          <li
            key={idx}
            className="border border-slate-200 rounded p-1.5 bg-white hover:bg-slate-50"
          >
            {linkPath ? (
              <Link to={linkPath} className="block">
                {content}
              </Link>
            ) : (
              content
            )}
          </li>
        );
      })}
    </ul>
  );
}

function toInternalPath(apiPath: string | null): string | null {
  if (!apiPath) return null;
  // 简单映射: /api/buildings/{id}/... → /buildings/{id}
  const m = apiPath.match(/^\/api\/buildings\/(\d+)(\/.*)?$/);
  if (m) {
    return `/buildings/${m[1]}${m[2] ?? ""}`;
  }
  // 其它 /api/... 路径不显示为内部链接
  if (apiPath.startsWith("/api/")) return null;
  return apiPath;
}

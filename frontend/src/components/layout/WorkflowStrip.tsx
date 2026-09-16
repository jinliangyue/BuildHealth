/**
 * WorkflowStrip · engineering workflow orientation
 *
 * The platform implements one analysis chain:
 *   Building → Monitoring → Anomaly → Health → Risk → Retrofit → AI Explanation
 *
 * Every step below is a real page. The strip exists so a first-time viewer can
 * see how the layers connect without clicking through the whole app.
 *
 * This is orientation only — it renders no engineering data.
 */
import { Link } from "react-router-dom";

interface Step {
  to: string;
  label: string;
  hint: string;
}

const STEPS: Step[] = [
  { to: "/buildings", label: "Building", hint: "Asset register" },
  { to: "/monitoring", label: "Monitoring", hint: "Sensor time series" },
  { to: "/risk-health", label: "Anomaly", hint: "Prototype detection" },
  { to: "/risk-health", label: "Health & Risk", hint: "BHI · risk tier" },
  { to: "/retrofit", label: "Retrofit", hint: "Priority · recommendations" },
  { to: "/ai-assistant", label: "AI Explanation", hint: "Grounded in the data" },
];

export default function WorkflowStrip() {
  return (
    <div className="mb-5 border border-slate-200 bg-white rounded-md px-4 py-3">
      <div className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">
        Engineering workflow
      </div>
      <ol className="flex flex-wrap items-stretch gap-y-2">
        {STEPS.map((s, idx) => (
          <li key={`${s.to}-${s.label}`} className="flex items-center">
            <Link
              to={s.to}
              className="px-2.5 py-1 rounded border border-slate-200 hover:border-blue-300 hover:bg-blue-50 group"
            >
              <div className="text-xs font-medium text-slate-700 group-hover:text-blue-800">
                {s.label}
              </div>
              <div className="text-[10px] text-slate-500">{s.hint}</div>
            </Link>
            {idx < STEPS.length - 1 && (
              <span
                aria-hidden="true"
                className="px-1.5 text-slate-300 text-sm select-none"
              >
                →
              </span>
            )}
          </li>
        ))}
      </ol>
      <p className="text-[10px] text-slate-400 mt-2">
        Evidence chain is shown per building; Knowledge Sources appear inside AI
        responses. All parameters are prototype decision-support values.
      </p>
    </div>
  );
}

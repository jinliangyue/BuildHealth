/**
 * Data / Settings · 数据源 + Prototype Parameters + 免责声明
 */
import TopBar from "../components/layout/TopBar";
import { Card } from "../components/ui/StateViews";
import { BHI_WEIGHTS, DIMENSION_LABELS } from "../types/api";

const RISK_THRESHOLDS = [
  { level: "Normal", range: "90-100", color: "#10B981" },
  { level: "Attention", range: "75-89", color: "#F59E0B" },
  { level: "Abnormal", range: "60-74", color: "#F97316" },
  { level: "HighRisk", range: "0-59", color: "#DC2626" },
];

const DETECTION_THRESHOLDS = [
  { metric: "crack_width", medium: "0.20 mm", high: "0.30 mm" },
  { metric: "tilt", medium: "3.0 ‰", high: "4.0 ‰" },
  { metric: "temperature", medium: "40 ℃", high: "—" },
  { metric: "humidity", medium: "85 %", high: "—" },
];

export default function DataSettings() {
  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <TopBar
        title="Data & Settings"
        subtitle="Data source disclosure · prototype parameters · engineering disclaimer"
      />

      {/* 数据源 */}
      <Card title="Data Source" subtitle="Phase 2 · Read-only display">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-sm font-medium bg-amber-50 border border-amber-300 text-amber-800 rounded">
            SIMULATED DATA
          </span>
          <span className="text-sm text-slate-600">
            All monitoring records in this platform are <b>simulated</b> using a
            deterministic engineering-time-series generator with baseline, trend,
            periodic fluctuation, noise, and event components.
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-3 leading-relaxed">
          No real buildings or real communities are monitored. No real
          IoT/MQTT/ESP32 devices are connected. The platform does not claim to
          be deployed at any real location.
        </p>
      </Card>

      {/* BHI 计算参数 */}
      <Card
        title="BHI Calculation Parameters"
        subtitle="Prototype Design Parameters · calculation_version = BHI-v1.0"
      >
        <p className="text-sm text-slate-700 leading-relaxed mb-4">
          BHI = Σ (dimension × weight). Range [0, 100]. Each dimension input
          must be in [0, 100]; out-of-range inputs raise an error and are not
          silently accepted.
        </p>
        <table className="data-table">
          <thead>
            <tr>
              <th>Dimension</th>
              <th className="text-right">Weight</th>
              <th>Source (V1)</th>
            </tr>
          </thead>
          <tbody>
            {(Object.keys(BHI_WEIGHTS) as Array<keyof typeof BHI_WEIGHTS>).map(
              (k) => (
                <tr key={k}>
                  <td>{DIMENSION_LABELS[k]}</td>
                  <td className="text-right font-mono">
                    {(BHI_WEIGHTS[k] * 100).toFixed(0)}%
                  </td>
                  <td className="text-xs text-slate-500">
                    {k === "structural_safety"
                      ? "Anomaly-based log-decay scoring"
                      : k === "facility_condition"
                        ? "current_age / design_life ratio"
                        : k === "environmental_quality"
                          ? "temperature & humidity stability"
                          : k === "energy_performance"
                            ? "electricity coefficient of variation"
                            : "placeholder: floors + age"}
                  </td>
                </tr>
              ),
            )}
            <tr className="font-semibold bg-slate-50">
              <td>Sum</td>
              <td className="text-right font-mono">100%</td>
              <td className="text-xs text-slate-500">
                Defensive assertion enforced at runtime
              </td>
            </tr>
          </tbody>
        </table>
      </Card>

      {/* 风险阈值 */}
      <Card
        title="Risk Classification Thresholds"
        subtitle="Prototype Risk Classification v1.0"
      >
        <table className="data-table">
          <thead>
            <tr>
              <th>Risk Level</th>
              <th>BHI Range</th>
              <th>Color</th>
            </tr>
          </thead>
          <tbody>
            {RISK_THRESHOLDS.map((r) => (
              <tr key={r.level}>
                <td className="font-medium">{r.level}</td>
                <td className="font-mono">{r.range}</td>
                <td>
                  <div className="flex items-center gap-2">
                    <span
                      className="w-4 h-4 rounded"
                      style={{ background: r.color }}
                    />
                    <span className="font-mono text-xs text-slate-500">
                      {r.color}
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-amber-700 mt-3">
          Additional rule: HIGH-severity prototype anomaly presence forces a
          minimum upgrade to Attention.
        </p>
      </Card>

      {/* 异常检测参数 */}
      <Card
        title="Anomaly Detection Parameters"
        subtitle="Three methods · Prototype Detection Parameters"
      >
        <table className="data-table">
          <thead>
            <tr>
              <th>Method</th>
              <th>Description</th>
              <th>Default Threshold</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="font-medium">Threshold Detection</td>
              <td className="text-xs">Absolute value comparison</td>
              <td className="font-mono text-xs">
                {DETECTION_THRESHOLDS.map((t) => `${t.metric} (M:${t.medium} H:${t.high})`).join(" · ")}
              </td>
            </tr>
            <tr>
              <td className="font-medium">Rate of Change</td>
              <td className="text-xs">Adjacent point relative change</td>
              <td className="font-mono text-xs">
                |Δ| ≥ abs_threshold AND |Δ%| ≥ rel_pct (varies by metric)
              </td>
            </tr>
            <tr>
              <td className="font-medium">Z-score (Statistical)</td>
              <td className="text-xs">7-day rolling window deviation</td>
              <td className="font-mono text-xs">
                {"|z| > 4.0 → anomaly · |z| > 6.0 → HIGH · disabled for electricity & humidity"}
              </td>
            </tr>
          </tbody>
        </table>
      </Card>

      {/* 免责声明 */}
      <Card
        title="Engineering Disclaimer"
        subtitle="Mandatory disclosure"
      >
        <div className="border-l-4 border-amber-400 bg-amber-50 px-4 py-3 text-sm text-amber-900 leading-relaxed">
          This platform is a <b>prototype engineering decision-support system
          based on simulated data</b>. It does <b>not</b> replace professional
          inspection, structural appraisal, or engineering judgment.
          <br />
          <br />
          The BHI (Building Health Index) is computed from{" "}
          <b>Prototype Design Parameters (v1.0)</b>, not a national standard,
          industry standard, or legally binding building safety grade.
          <br />
          <br />
          Risk classification is <b>Prototype Risk Classification</b>, not a
          statutory safety rating. The system does <b>not</b> predict building
          collapse, does <b>not</b> substitute for professional structural
          inspection, and does <b>not</b> generate automated structural
          reinforcement plans.
          <br />
          <br />
          Any risk results shown should be treated as auxiliary assessment /
          digital prototype demonstration only. Always consult qualified
          engineering personnel before any retrofit or maintenance decision.
        </div>
      </Card>
    </div>
  );
}

/**
 * 全局 Simulated Data 标识 · 工程真实性原则
 * 满足 docs/02_Engineering_Requirements.md ER-02 红线
 */
export default function SimulatedBanner() {
  return (
    <div className="fixed bottom-3 right-3 z-50 px-2.5 py-1 bg-amber-50 border border-amber-300 text-amber-800 text-[11px] rounded shadow-sm">
      <span className="font-semibold">Simulated Data</span>
      <span className="mx-1">·</span>
      <span>Prototype Parameters</span>
    </div>
  );
}

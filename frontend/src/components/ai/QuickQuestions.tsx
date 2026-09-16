/**
 * QuickQuestions · Phase 5 V3
 * 5 个固定 quick question 按钮.
 */
interface Props {
  onSelect: (question: string) => void;
  disabled?: boolean;
}

const QUESTIONS = [
  { label: "Summarize Health", text: "Summarize the current building health status" },
  { label: "Explain Risk", text: "Explain the current risk level and why" },
  { label: "Explain Anomalies", text: "What are the active prototype anomalies?" },
  { label: "Explain Retrofit Priority", text: "Explain the retrofit priorities" },
  { label: "What Should Engineers Review Next?", text: "What should qualified engineers review next?" },
];

export default function QuickQuestions({ onSelect, disabled }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {QUESTIONS.map((q) => (
        <button
          key={q.text}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(q.text)}
          className="text-xs px-2.5 py-1.5 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {q.label}
        </button>
      ))}
    </div>
  );
}

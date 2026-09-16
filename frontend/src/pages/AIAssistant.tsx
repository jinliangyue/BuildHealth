/**
 * AI Engineering Assistant · Phase 5 V3
 * 工程仪表盘风格 AI 助手页面 (NOT ChatGPT-style chat).
 */
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import TopBar from "../components/layout/TopBar";
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
} from "../components/ui/StateViews";
import AIResponsePanel from "../components/ai/AIResponsePanel";
import QuickQuestions from "../components/ai/QuickQuestions";
import { aiApi } from "../api/ai";
import { buildingsApi } from "../api/buildings";
import { useApi } from "../hooks/useApi";
import type { AIResponse, Building } from "../types/api";

export default function AIAssistant() {
  const [searchParams] = useSearchParams();
  const initialBuildingId = Number(searchParams.get("building_id")) || null;
  const initialQuestion = searchParams.get("q");

  const [selectedBuildingId, setSelectedBuildingId] = useState<number | null>(
    initialBuildingId,
  );
  const [question, setQuestion] = useState<string>(initialQuestion ?? "");
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Buildings list
  const { data: buildingsData, loading: buildingsLoading } = useApi(
    async (): Promise<Building[]> => buildingsApi.list(),
  );

  // AI provider health
  const { data: healthData } = useApi(
    async () => aiApi.health(),
  );

  // Auto-pick first building if none selected
  useEffect(() => {
    if (selectedBuildingId === null && buildingsData && buildingsData.length > 0) {
      setSelectedBuildingId(buildingsData[0].id);
    }
  }, [buildingsData, selectedBuildingId]);

  // Auto-submit if initial question provided
  useEffect(() => {
    if (
      initialQuestion &&
      selectedBuildingId !== null &&
      !response &&
      !submitting
    ) {
      void handleAsk(initialQuestion);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion, selectedBuildingId]);

  async function handleAsk(q: string) {
    if (selectedBuildingId === null) return;
    if (!q.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const r = await aiApi.ask(selectedBuildingId, q);
      setResponse(r);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSummarize() {
    if (selectedBuildingId === null) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const r = await aiApi.summarize(selectedBuildingId);
      setResponse(r);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <TopBar
        title="AI Engineering Assistant"
        subtitle="Explanation layer over V1 BHI / Risk / V2 Retrofit Decision (Mock provider by default)"
        right={
          <Link
            to="/ai-assistant"
            className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
          >
            Reset
          </Link>
        }
      />

      {/* Provider status banner */}
      {healthData && (
        <div
          className={`text-xs px-3 py-2 rounded border ${
            healthData.status === "ok"
              ? "bg-blue-50 border-blue-200 text-blue-800"
              : "bg-amber-50 border-amber-200 text-amber-800"
          }`}
        >
          <span className="font-medium">Provider:</span> {healthData.provider}{" "}
          ({healthData.model}) · <span className="font-medium">Status:</span>{" "}
          {healthData.status} · {healthData.message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left column: Building selector */}
        <Card title="Building" subtitle="Select a building to query">
          {buildingsLoading && <LoadingState label="Loading buildings..." />}
          {buildingsData && (
            <ul className="space-y-1">
              {buildingsData.map((b) => (
                <li key={b.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedBuildingId(b.id)}
                    className={`w-full text-left px-2 py-1.5 rounded text-sm border ${
                      selectedBuildingId === b.id
                        ? "bg-blue-50 border-blue-300 text-blue-800"
                        : "border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="font-medium">{b.name}</div>
                    <div className="text-[11px] text-slate-500">
                      #{b.id} · {b.building_type} · {b.floors}F · age{" "}
                      {b.current_age}y
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Right column: Quick questions + Free-form + Response */}
        <div className="lg:col-span-2 space-y-4">
          <Card title="Quick Questions" subtitle="Click to ask the AI assistant">
            <QuickQuestions
              onSelect={(q) => {
                setQuestion(q);
                void handleAsk(q);
              }}
              disabled={selectedBuildingId === null || submitting}
            />
            <div className="mt-3 flex items-center gap-2">
              <button
                type="button"
                onClick={() => void handleSummarize()}
                disabled={selectedBuildingId === null || submitting}
                className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Quick Summary
              </button>
              <span className="text-[11px] text-slate-500">
                Generates a one-shot building summary
              </span>
            </div>
          </Card>

          <Card title="Free-form Question" subtitle="Ask anything about the building">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
              placeholder="Type a question about the selected building…"
              className="w-full text-sm border border-slate-300 rounded p-2 resize-y focus:outline-none focus:border-blue-500"
            />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-[11px] text-slate-500">
                Max 2000 chars · grounded in V1/V2 deterministic engineering data
              </span>
              <button
                type="button"
                onClick={() => void handleAsk(question)}
                disabled={
                  selectedBuildingId === null ||
                  !question.trim() ||
                  submitting
                }
                className="text-xs px-4 py-1.5 bg-slate-800 text-white rounded hover:bg-slate-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Ask
              </button>
            </div>
          </Card>

          <Card title="AI Response" subtitle="Grounded answer + evidence + actions">
            {submitting && <LoadingState label="AI is processing..." />}
            {submitError && <ErrorState message={submitError} />}
            {!submitting && !submitError && !response && (
              <EmptyState
                title="No response yet"
                hint="Click a quick question, Quick Summary, or type a question and press Ask."
              />
            )}
            {response && <AIResponsePanel response={response} />}
          </Card>
        </div>
      </div>
    </div>
  );
}

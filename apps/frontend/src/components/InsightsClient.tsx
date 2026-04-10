import { useState } from "react";
import { api, wsUrlForRun, type InsightResponse, type OrchestratorStreamEvent } from "@/lib/api";
import { $orchestrator, $session } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID, AUTH_REQUIRED } from "@/lib/featureFlags";
import { ErrorBoundary } from "@/components/ErrorBoundary";

type StreamStep = {
  name: string;
  status: "pending" | "running" | "completed" | "error";
  message?: string;
};

const STEP_ORDER = ["github_analyst", "psychometric_profiler", "compatibility_engine", "synthesis"];

function stepLabel(name: string) {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function InsightsInner() {
  const session = $session.get();
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;

  if (AUTH_REQUIRED && !session) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-20 pb-12 w-full max-w-3xl mx-auto">
        <section className="glass-panel p-8 rounded-none w-full text-center">
          <h3 className="text-xl font-bold font-display text-white">Authentication Required</h3>
          <p className="text-gray-400 mt-2 mb-6">Sign in on the auth page to view synthesis insights.</p>
          <a href="/auth" className="btn btn-primary justify-center">Go to Sign In</a>
        </section>
      </main>
    );
  }

  const [streaming, setStreaming] = useState(false);
  const [streamDone, setStreamDone] = useState(false);
  const [streamError, setStreamError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<StreamStep[]>([]);
  const [data, setData] = useState<InsightResponse | null>(null);

  const startStream = async () => {
    setStreaming(true);
    setStreamDone(false);
    setStreamError(false);
    setProgress(0);
    setData(null);
    setSteps(
      STEP_ORDER.map((name) => ({ name, status: "pending" }))
    );

    try {
      const run = await api.orchestratorRun("team_alpha", userId);

      $orchestrator.set({
        runId: run.run_id,
        currentStep: run.steps[0] ?? "",
        progressPct: 0,
        status: "queued",
        events: [],
      });

      const ws = new WebSocket(wsUrlForRun(run.run_id));

      ws.onmessage = (evt) => {
        const event = JSON.parse(evt.data as string) as OrchestratorStreamEvent;

        setProgress(event.progress_pct);

        $orchestrator.set({
          runId: run.run_id,
          currentStep: event.step,
          progressPct: event.progress_pct,
          status: event.status,
          events: [],
        });

        setSteps((prev) =>
          prev.map((s) => {
            if (s.name !== event.step) return s;
            return {
              ...s,
              status: event.status === "completed" ? "completed" : event.status === "error" ? "error" : "running",
              message: event.message,
            };
          })
        );

        // Extract synthesis data from synthesis step completion
        if (event.status === "completed" && event.step === "synthesis" && event.data?.synthesis) {
          const synth = event.data.synthesis as unknown as InsightResponse;
          setData(synth);
        }

        if (event.progress_pct >= 100) {
          setStreamDone(true);
          setStreaming(false);
        }
      };

      ws.onerror = () => {
        setStreamError(true);
        setStreaming(false);
        setSteps((prev) =>
          prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s))
        );
      };

      ws.onclose = () => {
        setStreaming(false);
        if (!streamDone) setStreamDone(true);
      };
    } catch {
      setStreamError(true);
      setStreaming(false);
    }
  };

  return (
    <main className="relative z-10 w-full max-w-[1200px] mx-auto px-4 md:px-8 pt-40 pb-20 flex flex-col min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6">
        <div>
          <span className="text-accent-info font-mono text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
            AI Synthesis
          </span>
          <h1 className="text-4xl md:text-5xl font-bold font-display text-white mb-2">
            Executive Summary
          </h1>
          <p className="text-gray-400 max-w-xl">
            Holistic insights combining GitHub metrics, chronotype alignment, and psychometric assessments.
          </p>
        </div>
        <button
          onClick={startStream}
          disabled={streaming}
          className="btn btn-primary shadow-neon flex items-center gap-2 px-5 py-2.5"
        >
          <span className="material-symbols-outlined text-[20px]">
            {streaming ? "hourglass_top" : "play_arrow"}
          </span>
          {streaming ? "Streaming..." : streamDone ? "Re-run Analysis" : "Run Analysis"}
        </button>
      </div>

      {/* Idle state */}
      {!streaming && !streamDone && !streamError && (
        <div className="flex flex-col items-center justify-center py-32 opacity-50">
          <span className="material-symbols-outlined text-6xl text-primary mb-6">insights</span>
          <h3 className="text-2xl font-bold font-display text-white mb-2">Ready to Analyse</h3>
          <p className="text-gray-400 text-center max-w-sm">
            Click "Run Analysis" to stream the LangGraph orchestration pipeline live.
          </p>
        </div>
      )}

      {/* Streaming progress */}
      {(streaming || (streamDone && steps.length > 0)) && (
        <div className="mb-10 glass-panel rounded-none p-6">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-bold font-display text-white uppercase tracking-widest">
              Orchestration Pipeline
            </h3>
            <span className="text-xs font-mono text-gray-400">{progress}%</span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden mb-5">
            <div
              className="bg-gradient-to-r from-primary to-accent-neon h-full rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(204,255,0,0.4)]"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Steps */}
          <div className="flex flex-col gap-2">
            {steps.map((step) => (
              <div
                key={step.name}
                className={`flex items-center gap-3 py-2 px-3 rounded border transition-all ${
                  step.status === "completed"
                    ? "border-accent-neon/20 bg-accent-neon/5"
                    : step.status === "running"
                      ? "border-primary/40 bg-primary/10"
                      : step.status === "error"
                        ? "border-red-500/30 bg-red-500/5"
                        : "border-white/5 bg-white/[0.02]"
                }`}
              >
                <span
                  className={`material-symbols-outlined text-[18px] ${
                    step.status === "completed"
                      ? "text-accent-neon"
                      : step.status === "running"
                        ? "text-primary animate-spin-slow"
                        : step.status === "error"
                          ? "text-red-400"
                          : "text-gray-700"
                  }`}
                >
                  {step.status === "completed"
                    ? "check_circle"
                    : step.status === "running"
                      ? "sync"
                      : step.status === "error"
                        ? "error"
                        : "radio_button_unchecked"}
                </span>
                <span
                  className={`text-sm font-mono ${
                    step.status === "pending" ? "text-gray-600" : "text-gray-200"
                  }`}
                >
                  {stepLabel(step.name)}
                </span>
                {step.message && step.status === "running" && (
                  <span className="text-xs text-gray-500 ml-auto">{step.message}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {streamError && (
        <div className="p-6 bg-red-500/10 border border-red-500/30 rounded-none text-red-400 text-center flex flex-col items-center gap-4 mb-8">
          <span className="material-symbols-outlined text-4xl">error</span>
          <div>
            <h3 className="font-bold mb-1">Orchestration Failed</h3>
            <p className="text-sm opacity-80">
              Unable to connect to the analysis stream. Check backend connection.
            </p>
          </div>
          <button
            onClick={() => void startStream()}
            className="px-4 py-2 rounded-lg border border-red-500/30 text-sm text-red-300 hover:bg-red-500/10 hover:text-red-200 transition-colors flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            Retry
          </button>
        </div>
      )}

      {/* Synthesis result */}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* Main Narrative */}
          <div className="lg:col-span-8 glass-card rounded-none p-8 md:p-10 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-accent-info/5 to-transparent rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2" />

            <h2 className="text-2xl font-bold font-display text-white mb-6 flex items-center gap-3 relative z-10">
              <span className="w-8 h-8 rounded-full bg-accent-info/20 flex items-center justify-center text-accent-info">
                <span className="material-symbols-outlined text-[18px]">psychiatry</span>
              </span>
              Team Dynamics Narrative
            </h2>

            <div className="relative z-10">
              <span className="material-symbols-outlined text-6xl text-white/5 absolute -top-4 -left-4">
                format_quote
              </span>
              <p className="text-lg text-gray-300 leading-relaxed relative z-10 pl-6 border-l-2 border-accent-info/30">
                {data.narrative}
              </p>
            </div>

            <div className="mt-12 pt-6 border-t border-white/40 relative z-10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-yellow-500/60 text-[18px]">info</span>
                <p className="text-xs text-gray-500 font-mono tracking-wide">
                  {data.uncertainty_note}
                </p>
              </div>
              <span className="px-3 py-1 rounded bg-white/5 border border-white/40 text-[10px] uppercase text-gray-400 font-bold tracking-widest">
                Confidence: High
              </span>
            </div>
          </div>

          {/* Recommendations */}
          <div className="lg:col-span-4 flex flex-col gap-6 relative z-10">
            <div className="glass-panel rounded-none p-6 h-full flex flex-col">
              <h3 className="text-lg font-bold font-display text-white mb-6 flex items-center gap-2">
                <span className="material-symbols-outlined text-accent-neon text-[20px]">lightbulb</span>
                Key Recommendations
              </h3>

              <div className="flex-1 flex flex-col gap-4">
                {data.recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="bg-white/5 border border-white/40 rounded-none p-4 flex gap-4 hover:bg-white/10 hover:border-primary/30 transition-all group"
                  >
                    <div className="w-6 h-6 rounded-full bg-black/50 border border-white/40 flex items-center justify-center text-xs font-bold text-gray-400 shrink-0 group-hover:text-primary group-hover:border-primary/50 transition-colors">
                      {idx + 1}
                    </div>
                    <p className="text-sm text-gray-300 leading-relaxed flex-1">{rec}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Card */}
            <div className="glass-panel rounded-none p-6 bg-gradient-to-br from-primary/10 to-transparent border-primary/20">
              <h4 className="font-bold text-white text-sm mb-2 font-display">Export Findings</h4>
              <p className="text-xs text-gray-400 mb-4">
                Share this synthesis report with your engineering leadership.
              </p>
              <button className="w-full py-2 bg-white/10 hover:bg-white/20 border border-white/40 rounded-lg text-sm font-bold text-white transition-colors flex items-center justify-center gap-2">
                <span className="material-symbols-outlined text-[18px]">ios_share</span>
                Share Report
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export function InsightsClient() {
  return (
    <ErrorBoundary fallbackMessage="Insights failed to load">
      <InsightsInner />
    </ErrorBoundary>
  );
}

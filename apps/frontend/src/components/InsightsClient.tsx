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

// ---------------------------------------------------------------------------
// Markdown renderer — parses Claude's structured output into proper JSX
// ---------------------------------------------------------------------------

type MdSection = { heading: string; bullets: string[]; paragraphs: string[] };

function parseNarrative(text: string): MdSection[] {
  const lines = text.split("\n").map((l) => l.trim());
  const sections: MdSection[] = [];
  let cur: MdSection = { heading: "", bullets: [], paragraphs: [] };

  const flush = () => {
    if (cur.heading || cur.bullets.length || cur.paragraphs.length) {
      sections.push({ ...cur });
    }
    cur = { heading: "", bullets: [], paragraphs: [] };
  };

  for (const line of lines) {
    if (!line) continue;
    if (line.startsWith("## ")) {
      flush();
      cur.heading = line.replace(/^## /, "").trim();
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      cur.bullets.push(line.replace(/^[-*]\s+/, "").trim());
    } else if (/^\d+\.\s/.test(line)) {
      cur.bullets.push(line.replace(/^\d+\.\s+/, "").trim());
    } else {
      cur.paragraphs.push(line);
    }
  }
  flush();
  return sections;
}

function Inline({ text }: { text: string }) {
  // Render **bold** inline patterns
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="text-white font-semibold">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

// Section icon map
const SECTION_ICONS: Record<string, string> = {
  "Team Alignment Summary": "analytics",
  "Key Strengths": "thumb_up",
  "Friction Risks": "warning",
  "Recommended Meeting Windows": "schedule",
  "Hiring Gap Analysis": "person_search",
};

function NarrativeCard({ narrative }: { narrative: string }) {
  const [expanded, setExpanded] = useState(false);
  const sections = parseNarrative(narrative);

  if (sections.length === 0) {
    // Fallback: plain text, strip any stray markdown
    const clean = narrative.replace(/#{1,6}\s/g, "").replace(/\*\*/g, "").trim();
    return (
      <div className="relative z-10">
        <p className="text-lg text-gray-300 leading-relaxed pl-6 border-l-2 border-accent-info/30">
          {clean}
        </p>
      </div>
    );
  }

  const preview = sections.slice(0, expanded ? sections.length : 2);

  return (
    <div className="space-y-6 relative z-10">
      {preview.map((section, idx) => (
        <div key={idx} className={idx > 0 ? "border-t border-white/10 pt-6" : ""}>
          {section.heading && (
            <div className="flex items-center gap-2 mb-3">
              <span className="material-symbols-outlined text-accent-info text-[16px]">
                {SECTION_ICONS[section.heading] ?? "circle"}
              </span>
              <h3 className="text-sm font-bold uppercase tracking-widest text-gray-400 font-mono">
                {section.heading}
              </h3>
            </div>
          )}
          {section.paragraphs.map((p, i) => (
            <p key={i} className="text-gray-300 leading-relaxed mb-2 text-sm">
              <Inline text={p} />
            </p>
          ))}
          {section.bullets.length > 0 && (
            <ul className="space-y-2 mt-2">
              {section.bullets.map((b, i) => (
                <li key={i} className="flex gap-3 text-sm text-gray-300 leading-relaxed">
                  <span className="text-accent-info mt-0.5 shrink-0">›</span>
                  <Inline text={b} />
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}

      {sections.length > 2 && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-bold text-primary hover:text-white transition-colors uppercase tracking-wider flex items-center gap-1 mt-2"
        >
          <span className="material-symbols-outlined text-sm">
            {expanded ? "expand_less" : "expand_more"}
          </span>
          {expanded ? "Show Less" : `Show ${sections.length - 2} More Sections`}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function InsightsInner() {
  const session = $session.get();
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;

  if (AUTH_REQUIRED && !session) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-10 pb-12 w-full max-w-3xl mx-auto">
        <section className="glass-panel p-8 rounded-none w-full text-center">
          <h3 className="text-xl font-bold font-display text-white">Authentication Required</h3>
          <p className="text-gray-400 mt-2 mb-6">Sign in on the auth page to view synthesis insights.</p>
          <a href="/auth" className="btn btn-primary justify-center">Go to Sign In</a>
        </section>
      </main>
    );
  }

  // Aggregate KPIs from saved reports in localStorage
  const savedReports = (() => {
    if (typeof window === "undefined") return [];
    try {
      return JSON.parse(localStorage.getItem("gitsyntropy.reports") ?? "[]") as {
        id: string; teamName: string; score: number; resilienceScore: number; createdAt: string;
      }[];
    } catch { return []; }
  })();

  const kpiTotalRuns = savedReports.length;
  const kpiAvgScore = savedReports.length
    ? Math.round(savedReports.reduce((s, r) => s + r.score, 0) / savedReports.length)
    : null;
  const kpiBest = savedReports.length
    ? savedReports.reduce((best, r) => (r.score > best.score ? r : best), savedReports[0])
    : null;
  const kpiLastDate = savedReports[0]
    ? new Date(savedReports[0].createdAt).toLocaleDateString(undefined, { month: "short", day: "numeric" })
    : null;

  const [streaming, setStreaming] = useState(false);
  const [streamDone, setStreamDone] = useState(false);
  const [streamError, setStreamError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [steps, setSteps] = useState<StreamStep[]>([]);
  const [data, setData] = useState<InsightResponse | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);

  const startStream = async () => {
    setStreaming(true);
    setStreamDone(false);
    setStreamError(false);
    setProgress(0);
    setData(null);
    setReportId(null);
    setSteps(STEP_ORDER.map((name) => ({ name, status: "pending" })));

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
              status:
                event.status === "completed"
                  ? "completed"
                  : event.status === "error"
                    ? "error"
                    : "running",
              message: event.message,
            };
          })
        );

        if (event.status === "completed" && event.step === "synthesis" && event.data?.synthesis) {
          const synth = event.data.synthesis as unknown as InsightResponse;
          setData(synth);
          // Save to localStorage for report page
          const id = `${Date.now()}`;
          setReportId(id);
          const reports = JSON.parse(localStorage.getItem("gitsyntropy.reports") ?? "[]") as object[];
          reports.unshift({
            id,
            teamId: "team_alpha",
            teamName: "Team Alpha",
            score: 28,
            resilienceScore: 78,
            summary: synth.narrative,
            createdAt: new Date().toISOString(),
          });
          localStorage.setItem("gitsyntropy.reports", JSON.stringify(reports.slice(0, 20)));
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
    <main className="relative z-10 w-full max-w-[1200px] mx-auto px-4 md:px-8 pt-10 pb-20 flex flex-col min-h-screen">

      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-6">
        <div>
          <span className="text-accent-info font-mono text-xs uppercase tracking-widest mb-2 flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">auto_awesome</span>
            AI Synthesis — Claude Sonnet
          </span>
          <h1 className="text-4xl md:text-5xl font-bold font-display text-white mb-2">
            Executive Summary
          </h1>
          <p className="text-gray-400 max-w-xl text-sm">
            Runs the full LangGraph pipeline (GitHub → Psychometric → Compatibility → Claude synthesis)
            and renders a structured team health report. Results are saved to{" "}
            <a href="/dashboard" className="text-primary underline-offset-2 hover:underline">Recent Reports</a>.
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <button
            onClick={startStream}
            disabled={streaming}
            className="btn btn-primary shadow-neon flex items-center gap-2 px-5 py-2.5"
          >
            <span className="material-symbols-outlined text-[20px]">
              {streaming ? "hourglass_top" : "play_arrow"}
            </span>
            {streaming ? "Streaming..." : streamDone ? "Re-run Analysis" : "Run Full Analysis"}
          </button>
          <p className="text-[10px] text-gray-600 font-mono">
            Analysing as: <span className="text-gray-400">{userId}</span>
          </p>
        </div>
      </div>

      {/* Aggregate KPI bar */}
      {kpiTotalRuns > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Runs", value: String(kpiTotalRuns), icon: "history", color: "text-primary" },
            { label: "Avg Team Score", value: kpiAvgScore !== null ? `${kpiAvgScore}/36` : "—", icon: "analytics", color: "text-accent-teal" },
            { label: "Best Team", value: kpiBest?.teamName ?? "—", icon: "emoji_events", color: "text-amber-400" },
            { label: "Last Analysis", value: kpiLastDate ?? "—", icon: "calendar_today", color: "text-purple-400" },
          ].map((kpi) => (
            <div key={kpi.label} className="glass-panel rounded-none p-4 flex items-start gap-3 border border-white/5">
              <span className={`material-symbols-outlined text-[20px] ${kpi.color} flex-shrink-0 mt-0.5`}>{kpi.icon}</span>
              <div className="min-w-0">
                <p className="text-xs text-gray-500 uppercase tracking-wider font-mono">{kpi.label}</p>
                <p className="text-lg font-bold text-white font-display truncate">{kpi.value}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* What does this page do — idle explanation */}
      {!streaming && !streamDone && !streamError && (
        <div className="mb-10 glass-panel rounded-none p-6 border-white/5">
          <h3 className="text-sm font-bold text-white font-display mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[18px]">info</span>
            What happens when you click "Run Full Analysis"
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { icon: "code", step: "1", title: "GitHub Analyst", desc: "Fetches commit history and PR activity to compute chronotype and collaboration index." },
              { icon: "psychology", step: "2", title: "Psychometric Profiler", desc: "Loads your 8-dimension behavioral profile from the Assessment page." },
              { icon: "hub", step: "3", title: "Compatibility Engine", desc: "Scores 8 Ashtakoot dimensions across the team, flagging weak and strong alignments." },
              { icon: "auto_awesome", step: "4", title: "Claude Synthesis", desc: "Streams a GPT-quality narrative report with strengths, risks, hiring gaps, and meeting windows." },
            ].map((item) => (
              <div key={item.step} className="flex flex-col gap-2 p-4 bg-white/[0.02] border border-white/5 rounded">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary/20 text-primary text-[10px] font-bold flex items-center justify-center font-mono">{item.step}</span>
                  <span className="material-symbols-outlined text-[16px] text-gray-400">{item.icon}</span>
                  <span className="text-xs font-bold text-white font-display">{item.title}</span>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
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

          <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden mb-5">
            <div
              className="bg-gradient-to-r from-primary to-accent-neon h-full rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(204,255,0,0.4)]"
              style={{ width: `${progress}%` }}
            />
          </div>

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
              Unable to connect to the analysis stream. Ensure the backend is running on port 8000.
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

            <div className="flex items-start justify-between mb-6 relative z-10">
              <h2 className="text-2xl font-bold font-display text-white flex items-center gap-3">
                <span className="w-8 h-8 rounded-full bg-accent-info/20 flex items-center justify-center text-accent-info">
                  <span className="material-symbols-outlined text-[18px]">psychiatry</span>
                </span>
                Team Dynamics Report
              </h2>
              {reportId && (
                <a
                  href={`/report?id=${reportId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs font-bold text-primary hover:text-white transition-colors uppercase tracking-wider shrink-0"
                >
                  <span className="material-symbols-outlined text-sm">open_in_new</span>
                  Full Report
                </a>
              )}
            </div>

            <NarrativeCard narrative={data.narrative} />

            <div className="mt-8 pt-6 border-t border-white/10 relative z-10 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-yellow-500/60 text-[18px]">info</span>
                <p className="text-xs text-gray-500 font-mono">{data.uncertainty_note}</p>
              </div>
              <span className="px-3 py-1 rounded bg-accent-neon/10 border border-accent-neon/20 text-[10px] uppercase text-accent-neon font-bold tracking-widest">
                Confidence: High
              </span>
            </div>
          </div>

          {/* Sidebar */}
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

            {/* Actions */}
            <div className="glass-panel rounded-none p-6 bg-gradient-to-br from-primary/10 to-transparent border-primary/20 flex flex-col gap-3">
              <h4 className="font-bold text-white text-sm font-display">Next Steps</h4>
              {reportId && (
                <a
                  href={`/report?id=${reportId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-2 btn btn-primary text-sm flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-[18px]">description</span>
                  View Full Report
                </a>
              )}
              <a
                href="/workspace"
                className="w-full py-2 bg-white/10 hover:bg-white/20 border border-white/40 rounded-lg text-sm font-bold text-white transition-colors flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">schema</span>
                Manage Team
              </a>
              <a
                href="/compatibility"
                className="w-full py-2 bg-white/10 hover:bg-white/20 border border-white/40 rounded-lg text-sm font-bold text-white transition-colors flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined text-[18px]">compare_arrows</span>
                Deep Pair Analysis
              </a>
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

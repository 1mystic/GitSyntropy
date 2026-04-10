import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import type { ReportEntry } from "@/components/DashboardClient";

const REPORTS_STORAGE_KEY = "gitsyntropy.reports";

function loadReports(): ReportEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(REPORTS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ReportEntry[]) : [];
  } catch {
    return [];
  }
}

function ScoreBadge({ score, max = 36 }: { score: number; max?: number }) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 80 ? "text-accent-neon border-accent-neon/30 bg-accent-neon/10"
    : pct >= 60 ? "text-amber-300 border-amber-300/30 bg-amber-300/10"
    : "text-red-400 border-red-400/30 bg-red-400/10";
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-sm font-bold ${color}`}>
      <span className="text-xl font-display">{pct}%</span>
      <span className="opacity-60 font-normal">· {score}/{max}</span>
    </span>
  );
}

export function ReportClient() {
  const [report, setReport] = useState<ReportEntry | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id");
    if (!id) { setNotFound(true); return; }
    const all = loadReports();
    const found = all.find((r) => r.id === id);
    if (found) setReport(found);
    else setNotFound(true);
  }, []);

  if (notFound) {
    return (
      <div className="flex-1 w-full max-w-3xl mx-auto px-4 pt-40 pb-24 text-center">
        <span className="material-symbols-outlined text-5xl text-gray-600 mb-4 block">description</span>
        <h2 className="text-xl font-semibold text-white font-display mb-2">Report not found</h2>
        <p className="text-gray-500 text-sm mb-6">This report may have been cleared or doesn't exist.</p>
        <a href="/dashboard" className="text-primary text-sm font-bold hover:text-white transition-colors">
          ← Back to Dashboard
        </a>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex-1 w-full max-w-3xl mx-auto px-4 pt-40 pb-24">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-white/10 rounded" />
          <div className="h-4 w-full bg-white/5 rounded" />
          <div className="h-4 w-3/4 bg-white/5 rounded" />
        </div>
      </div>
    );
  }

  const date = new Date(report.createdAt);
  const dateLabel = date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const timeLabel = date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="flex-1 w-full max-w-3xl mx-auto px-4 md:px-8 pt-36 pb-24">
      {/* Back link */}
      <a
        href="/dashboard"
        className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-primary transition-colors mb-8 uppercase tracking-wider font-mono"
      >
        <span className="material-symbols-outlined text-sm">arrow_back</span>
        Dashboard
      </a>

      {/* Header */}
      <div className="mb-8 pb-6 border-b border-white/10">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <p className="text-xs text-gray-500 font-mono uppercase tracking-widest mb-1">Team Analysis Report</p>
            <h1 className="text-3xl md:text-4xl font-bold text-white font-display tracking-tight">
              {report.teamName}
            </h1>
            <p className="text-sm text-gray-500 mt-1">{dateLabel} · {timeLabel}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <ScoreBadge score={report.score} />
            <span className="text-[10px] text-gray-600 font-mono uppercase">Resilience Score</span>
          </div>
        </div>

        {/* Score bar */}
        <div className="mt-6">
          <div className="flex justify-between text-[10px] text-gray-500 font-mono uppercase mb-1.5">
            <span>0</span>
            <span>Team Compatibility</span>
            <span>36</span>
          </div>
          <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-primary to-accent-neon h-full rounded-full shadow-[0_0_10px_rgba(204,255,0,0.4)] transition-all duration-700"
              style={{ width: `${(report.score / 36) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Report body — rendered markdown */}
      <article className="prose-report">
        <Markdown
          components={{
            h1: ({ children }) => (
              <h1 className="text-2xl font-bold text-white font-display mt-8 mb-3 tracking-tight">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xl font-semibold text-white font-display mt-8 mb-3 pb-2 border-b border-white/10 flex items-center gap-2">
                <span className="w-1 h-5 bg-primary rounded-full inline-block" />
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-base font-semibold text-gray-200 mt-6 mb-2">{children}</h3>
            ),
            p: ({ children }) => (
              <p className="text-gray-300 leading-relaxed mb-4 text-sm">{children}</p>
            ),
            ul: ({ children }) => (
              <ul className="mb-4 space-y-2">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="mb-4 space-y-2 list-decimal list-inside">{children}</ol>
            ),
            li: ({ children, ordered }) => (
              <li className={`text-sm text-gray-300 ${ordered ? "ml-4" : "flex items-start gap-2"}`}>
                {!ordered && <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />}
                <span>{children}</span>
              </li>
            ),
            strong: ({ children }) => (
              <strong className="text-white font-semibold">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="text-gray-300 italic">{children}</em>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-primary/50 pl-4 my-4 text-gray-400 italic text-sm">
                {children}
              </blockquote>
            ),
            hr: () => (
              <hr className="border-white/10 my-8" />
            ),
            code: ({ children }) => (
              <code className="text-accent-neon bg-white/5 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
            ),
          }}
        >
          {report.summary}
        </Markdown>
      </article>

      {/* Footer */}
      <div className="mt-12 pt-6 border-t border-white/10 flex justify-between items-center">
        <p className="text-xs text-gray-600 font-mono">Generated by LangGraph multi-agent pipeline · GitSyntropy v0.1</p>
        <button
          onClick={() => window.print()}
          className="text-xs text-gray-500 hover:text-primary transition-colors flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-sm">print</span>
          Print
        </button>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { useStore } from "@nanostores/react";
import { api, wsUrlForRun, type CompatibilityResponse, type GithubSyncResponse, type OrchestratorStreamEvent } from "@/lib/api";
import { $compatibility, $orchestrator, $session, $sync, $teams } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID, AUTH_REQUIRED } from "@/lib/featureFlags";
import { RadarChart } from "@/components/RadarChart";
import { ChronotypeHeatmap } from "@/components/ChronotypeHeatmap";
import { ErrorBoundary } from "@/components/ErrorBoundary";

function AssessmentSkeleton() {
  return (
    <div className="animate-pulse flex flex-col gap-3">
      <div className="h-12 w-16 bg-white/10 rounded" />
      <div className="h-3 w-32 bg-white/5 rounded" />
    </div>
  );
}

function DashboardInner() {
  const session = $session.get();
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;

  if (AUTH_REQUIRED && !session) {
    return (
      <section className="card col-12 container mt-32">
        <p className="pill">Protected</p>
        <h3 className="mt-2 text-xl font-display">Authentication required</h3>
        <p className="text-gray-400 mt-2">Sign in on the auth page to access dashboard data.</p>
      </section>
    );
  }

  const teams = useStore($teams);

  const [health, setHealth] = useState<{ status: string; version: string } | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [healthLoading, setHealthLoading] = useState(true);

  // Team selection
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");
  const [teamsLoading, setTeamsLoading] = useState(false);

  // Orchestrator + analysis
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<{ score: number; summary: string } | null>(null);
  const [orchStep, setOrchStep] = useState<string | null>(null);
  const [orchProgress, setOrchProgress] = useState(0);
  const [orchError, setOrchError] = useState(false);
  const orchCompatRef = useRef<CompatibilityResponse | null>(null);

  // GitHub sync
  const [githubHandle, setGithubHandle] = useState("night-architect");
  const [syncStarting, setSyncStarting] = useState(false);
  const [syncStartError, setSyncStartError] = useState(false);
  const [syncStatusError, setSyncStatusError] = useState(false);
  const [syncResult, setSyncResult] = useState<GithubSyncResponse | null>(null);

  // Assessment
  const [assessmentLoading, setAssessmentLoading] = useState(true);
  const [assessmentError, setAssessmentError] = useState(false);
  const [assessmentReady, setAssessmentReady] = useState(false);
  const [assessmentAnswered, setAssessmentAnswered] = useState(0);
  const [assessmentTotal, setAssessmentTotal] = useState(8);

  // Compatibility
  const [compatResult, setCompatResult] = useState<CompatibilityResponse | null>(null);

  const pushSyncStore = (data: GithubSyncResponse) => {
    $sync.set({
      syncId: data.sync_id,
      githubHandle: data.github_handle,
      chronotype: data.chronotype,
      activityRhythmScore: data.activity_rhythm_score,
      collaborationIndex: data.collaboration_index,
      status: data.status,
      prsLast30Days: data.prs_last_30_days,
      commitsLast30Days: data.commits_last_30_days,
      updatedAt: data.updated_at,
    });
  };

  useEffect(() => {
    void api
      .health()
      .then((data) => setHealth({ status: data.status, version: data.version }))
      .catch(() => setHealthError(true))
      .finally(() => setHealthLoading(false));
  }, []);

  // Load teams into store if not yet populated
  useEffect(() => {
    if (teams.length > 0) return;
    setTeamsLoading(true);
    void api.listTeams(userId)
      .then((data) => {
        $teams.set(data);
        if (data.length > 0) setSelectedTeamId(data[0].id);
      })
      .catch(() => {})
      .finally(() => setTeamsLoading(false));
  }, [userId]);

  // Sync selectedTeamId when teams populate from store
  useEffect(() => {
    if (teams.length > 0 && !selectedTeamId) {
      setSelectedTeamId(teams[0].id);
    }
  }, [teams]);

  const loadAssessment = () => {
    setAssessmentLoading(true);
    setAssessmentError(false);
    void api
      .assessmentResponse(userId)
      .then((data) => {
        setAssessmentReady(data.complete);
        setAssessmentAnswered(data.answered_count);
        setAssessmentTotal(data.total_questions);
      })
      .catch(() => setAssessmentError(true))
      .finally(() => setAssessmentLoading(false));
  };

  useEffect(() => { loadAssessment(); }, [userId]);

  const runAnalysis = async () => {
    setAnalysisLoading(true);
    setOrchError(false);
    setOrchStep(null);
    setOrchProgress(0);
    orchCompatRef.current = null;

    const teamId = selectedTeamId || teams[0]?.id || "team_alpha";

    try {
      const run = await api.orchestratorRun(teamId, userId);

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
        setOrchStep(event.step);
        setOrchProgress(event.progress_pct);

        $orchestrator.set({
          runId: run.run_id,
          currentStep: event.step,
          progressPct: event.progress_pct,
          status: event.status,
          events: [],
        });

        if (
          event.status === "completed" &&
          event.step === "compatibility_engine" &&
          event.data?.compatibility
        ) {
          const compat = event.data.compatibility as unknown as CompatibilityResponse;
          orchCompatRef.current = compat;
          setCompatResult(compat);
          $compatibility.set({
            totalScore: compat.total_score_36,
            label: compat.label,
            weakDimensions: compat.weak_dimensions,
          });
        }

        if (event.status === "completed" && event.step === "synthesis" && event.data?.synthesis) {
          const synth = event.data.synthesis as unknown as { narrative: string };
          const score = orchCompatRef.current?.total_score_36 ?? 28;
          setAnalysisResult({ score, summary: synth.narrative });
          setAnalysisLoading(false);
        }

        if (event.progress_pct >= 100) {
          setAnalysisLoading(false);
        }
      };

      ws.onerror = () => {
        setOrchError(true);
        setAnalysisLoading(false);
      };

      ws.onclose = () => {
        setAnalysisLoading(false);
      };
    } catch {
      setOrchError(true);
      setAnalysisLoading(false);
    }
  };

  const runSync = async () => {
    setSyncStarting(true);
    setSyncStartError(false);
    setSyncStatusError(false);
    try {
      const data = await api.githubSync(githubHandle.trim() || "night-architect");
      setSyncResult(data);
      pushSyncStore(data);
    } catch {
      setSyncStartError(true);
    } finally {
      setSyncStarting(false);
    }
  };

  useEffect(() => {
    if (!syncResult || syncResult.status === "complete") return;
    const interval = setInterval(() => {
      void api
        .githubSyncStatus(syncResult.sync_id)
        .then((data) => {
          setSyncStatusError(false);
          setSyncResult(data);
          pushSyncStore(data);
        })
        .catch(() => setSyncStatusError(true));
    }, 900);
    return () => clearInterval(interval);
  }, [syncResult]);

  const runCompatibility = async () => {
    // Use first two team members if available, else demo pair
    const memberA = teams.find((t) => t.id === selectedTeamId)?.members[0]?.user_id ?? "alice";
    const memberB = teams.find((t) => t.id === selectedTeamId)?.members[1]?.user_id ?? "bob";
    try {
      const data = await api.compatibility(memberA, memberB);
      setCompatResult(data);
      $compatibility.set({
        totalScore: data.total_score_36,
        label: data.label,
        weakDimensions: data.weak_dimensions,
      });
    } catch {
      // non-critical
    }
  };

  const resilienceScore = analysisResult
    ? Math.round((analysisResult.score / 36) * 100)
    : null;

  const activeTeam = teams.find((t) => t.id === selectedTeamId);

  return (
    <div className="flex-1 w-full max-w-[1400px] mx-auto px-4 md:px-8 pt-40 pb-24 flex flex-col min-h-screen">
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 px-2">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 font-display">
            Dashboard
          </h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${health?.status === "ok" ? "bg-accent-neon" : "bg-red-500"}`}
                />
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${health?.status === "ok" ? "bg-accent-neon" : "bg-red-500"}`}
                />
              </span>
              <p className="text-gray-400 text-sm font-medium">
                {healthLoading
                  ? "Checking API..."
                  : healthError
                    ? "Backend offline"
                    : `System operational · v${health?.version}`}
              </p>
            </div>
            {/* Team selector */}
            {(teamsLoading || teams.length > 0) && (
              <div className="flex items-center gap-2">
                <span className="text-gray-600 text-xs font-mono">TEAM</span>
                {teamsLoading ? (
                  <div className="w-28 h-7 bg-white/5 border border-white/10 rounded animate-pulse" />
                ) : (
                  <select
                    value={selectedTeamId}
                    onChange={(e) => setSelectedTeamId(e.target.value)}
                    className="bg-black/30 border border-white/10 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-primary transition-all"
                  >
                    {teams.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => void runAnalysis()}
            disabled={analysisLoading}
            className="btn btn-primary shadow-neon transition-all flex items-center gap-2 px-4 py-2 text-sm"
          >
            <span className="material-symbols-outlined text-[20px]">
              {analysisLoading ? "hourglass_top" : "play_arrow"}
            </span>
            {analysisLoading ? "Running..." : "Run Analysis"}
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 auto-rows-min pb-10">

        {/* Team Resilience Score */}
        <div className="col-span-1 md:col-span-2 xl:col-span-2 row-span-2 glass-card rounded-none p-8 relative overflow-hidden group border border-primary/20 bg-[radial-gradient(at_0%_0%,_hsla(270,60%,20%,0.5)_0,_transparent_50%),_radial-gradient(at_100%_100%,_hsla(260,80%,15%,0.5)_0,_transparent_50%)]">
          <div className="absolute -right-20 -top-20 w-64 h-64 bg-primary/20 blur-[80px] rounded-full" />
          <div className="absolute left-10 bottom-10 w-32 h-32 bg-accent-neon/10 blur-[50px] rounded-full" />

          <div className="relative z-10 flex flex-col h-full justify-between">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-gray-300 text-lg font-medium flex items-center gap-2 font-display">
                  <span className="material-symbols-outlined text-primary">psychology</span>
                  Team Compatibility Score
                  {activeTeam && (
                    <span className="text-xs font-normal text-gray-500 ml-1">· {activeTeam.name}</span>
                  )}
                </h2>
                <p className="text-gray-500 text-sm mt-1">
                  {analysisLoading ? "Multi-agent analysis running..." : "LangGraph multi-agent pipeline"}
                </p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold tracking-wider border ${
                  resilienceScore !== null
                    ? "bg-accent-neon/10 text-accent-neon border-accent-neon/20"
                    : "bg-gray-500/10 text-gray-400 border-gray-500/20"
                }`}
              >
                {resilienceScore !== null ? "HEALTHY" : "PENDING"}
              </span>
            </div>

            <div className="flex items-baseline gap-4 mt-8">
              <span className="text-8xl md:text-9xl font-bold tracking-tighter text-white drop-shadow-2xl font-display">
                {resilienceScore !== null ? `${resilienceScore}%` : "--"}
              </span>
            </div>

            {/* Orchestrator progress */}
            {analysisLoading && orchStep && (
              <div className="mt-4">
                <div className="flex justify-between items-center mb-1.5">
                  <span className="text-xs font-mono text-primary uppercase tracking-widest">
                    {orchStep.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-gray-500">{orchProgress}%</span>
                </div>
                <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-primary to-accent-neon h-full rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(204,255,0,0.4)]"
                    style={{ width: `${orchProgress}%` }}
                  />
                </div>
                <div className="flex gap-1 mt-3 flex-wrap">
                  {["github analyst", "psychometric profiler", "compatibility engine", "synthesis"].map(
                    (label, i) => {
                      const stepKey = ["github_analyst", "psychometric_profiler", "compatibility_engine", "synthesis"][i];
                      return (
                        <span
                          key={stepKey}
                          className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${
                            orchStep === stepKey
                              ? "border-primary/60 text-primary bg-primary/10"
                              : orchProgress >= 100
                                ? "border-accent-neon/30 text-accent-neon/60"
                                : "border-white/10 text-gray-600"
                          }`}
                        >
                          {label}
                        </span>
                      );
                    }
                  )}
                </div>
              </div>
            )}

            {orchError && (
              <div className="mt-4 flex items-center gap-3">
                <p className="text-xs text-red-400">Analysis failed — backend may be offline.</p>
                <button
                  onClick={() => void runAnalysis()}
                  className="text-xs text-primary hover:text-white flex items-center gap-1 transition-colors border border-primary/30 px-2 py-1 rounded"
                >
                  <span className="material-symbols-outlined text-sm">refresh</span>
                  Retry
                </button>
              </div>
            )}

            <div className="mt-6">
              <p className="text-sm text-gray-400 max-w-sm">
                {analysisResult
                  ? analysisResult.summary
                  : "Click 'Run Analysis' to start the multi-agent pipeline."}
              </p>
              {resilienceScore !== null && (
                <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden mt-4">
                  <div
                    className="bg-gradient-to-r from-primary to-accent-neon h-full rounded-full shadow-[0_0_10px_rgba(204,255,0,0.5)]"
                    style={{ width: `${resilienceScore}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* GitHub Sync */}
        <div className="col-span-1 md:col-span-1 xl:col-span-1 row-span-2 glass-card rounded-none p-6 flex flex-col relative">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-white font-semibold flex items-center gap-2 font-display">
              <span className="material-symbols-outlined text-amber-300">schedule</span>
              GitHub Sync
            </h3>
          </div>

          <div className="flex flex-col gap-4">
            <input
              value={githubHandle}
              onChange={(e) => setGithubHandle(e.target.value)}
              placeholder="GitHub handle"
              className="w-full bg-white/5 border border-white/40 rounded-none px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
            <button
              className="btn btn-secondary justify-center text-sm py-2"
              onClick={() => void runSync()}
              disabled={syncStarting || syncResult?.status === "syncing"}
            >
              {syncStarting
                ? "Starting..."
                : syncResult?.status === "syncing"
                  ? "Syncing..."
                  : "Sync Signals"}
            </button>
            {syncStartError && (
              <div className="flex items-center gap-2">
                <p className="text-red-400 text-xs flex-1">Sync failed.</p>
                <button onClick={() => void runSync()} className="text-xs text-primary hover:text-white flex items-center gap-1 transition-colors">
                  <span className="material-symbols-outlined text-sm">refresh</span>
                  Retry
                </button>
              </div>
            )}
            {syncStatusError && (
              <p className="text-yellow-400 text-xs">Refresh failed. Retrying...</p>
            )}
          </div>

          {syncResult && (
            <div className="mt-6 pt-4 border-t border-white/40 flex-1 flex flex-col">
              <div className="flex justify-between items-end mb-4">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-display">Handle</p>
                  <p className="font-bold text-white">{syncResult.github_handle}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400 uppercase tracking-wider font-display">Status</p>
                  <p className="font-bold text-accent-teal uppercase text-sm">{syncResult.status}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-white/5 rounded-lg p-3">
                  <p className="text-[10px] text-gray-400 uppercase">Chronotype</p>
                  <p className="font-medium text-white capitalize">{syncResult.chronotype}</p>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                  <p className="text-[10px] text-gray-400 uppercase">Collab Index</p>
                  <p className="font-medium text-white">{syncResult.collaboration_index}</p>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                  <p className="text-[10px] text-gray-400 uppercase">Commits (30d)</p>
                  <p className="font-medium text-white">{syncResult.commits_last_30_days}</p>
                </div>
                <div className="bg-white/5 rounded-lg p-3">
                  <p className="text-[10px] text-gray-400 uppercase">Rhythm Score</p>
                  <p className="font-medium text-white">{syncResult.activity_rhythm_score}</p>
                </div>
              </div>

              <div className="mt-2">
                <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-2 font-display">
                  Activity Pattern
                </p>
                <ChronotypeHeatmap
                  chronotype={syncResult.chronotype}
                  commitCount={syncResult.commits_last_30_days}
                />
              </div>
            </div>
          )}
        </div>

        {/* Assessment Readiness */}
        <div className="col-span-1 md:col-span-1 xl:col-span-1 glass-card rounded-none p-6 flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-white font-semibold text-sm font-display">Assessment Readiness</h3>
            {!assessmentLoading && !assessmentError && (
              <span
                className={`size-2 rounded-full ${assessmentReady ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" : "bg-yellow-500"}`}
              />
            )}
          </div>
          <div className="relative flex-1 flex flex-col justify-center py-4">
            {assessmentLoading ? (
              <AssessmentSkeleton />
            ) : assessmentError ? (
              <div className="flex flex-col gap-2">
                <p className="text-sm text-red-400">Failed to load status.</p>
                <button
                  onClick={loadAssessment}
                  className="text-xs text-primary hover:text-white flex items-center gap-1 transition-colors self-start"
                >
                  <span className="material-symbols-outlined text-sm">refresh</span>
                  Retry
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-end gap-2">
                  <span className="text-5xl font-bold text-white tracking-tighter">
                    {assessmentAnswered}
                  </span>
                  <span className="text-gray-500 pb-1">/ {assessmentTotal}</span>
                </div>
                <p className="text-sm text-gray-400 mt-2">
                  {assessmentReady ? "Ready for compatibility engine." : "Assessment incomplete."}
                </p>
              </>
            )}
          </div>
          <a
            href="/assessment"
            className="text-xs font-bold text-primary hover:text-white transition-colors uppercase tracking-wider"
          >
            {assessmentReady ? "Review Answers" : "Continue Assessment"} →
          </a>
        </div>

        {/* Compatibility Snapshot */}
        <div className="col-span-1 md:col-span-1 xl:col-span-1 glass-card rounded-none p-6 relative flex flex-col justify-between">
          <div>
            <h3 className="text-white font-semibold text-sm mb-1 font-display">
              Compatibility Snapshot
            </h3>
            {activeTeam && activeTeam.members.length >= 2 ? (
              <p className="text-[10px] text-gray-500 mb-3 font-mono">
                {activeTeam.members[0].github_handle ?? activeTeam.members[0].user_id} ↔{" "}
                {activeTeam.members[1].github_handle ?? activeTeam.members[1].user_id}
              </p>
            ) : (
              <p className="text-[10px] text-gray-500 mb-3">Add 2+ members to a team</p>
            )}
            <button
              className="w-full btn btn-secondary justify-center text-xs py-1.5"
              onClick={() => void runCompatibility()}
              disabled={!activeTeam || activeTeam.members.length < 2}
            >
              Run Pairing
            </button>
          </div>

          <div className="mt-4">
            {compatResult ? (
              <>
                <div className="flex justify-between items-end mb-2">
                  <span className="text-3xl font-bold text-white tracking-tighter">
                    {compatResult.total_score_36}{" "}
                    <span className="text-sm text-gray-500 font-normal">/ 36</span>
                  </span>
                  <span
                    className={`text-xs px-2 py-1 rounded font-bold uppercase ${
                      compatResult.total_score_36 >= 28
                        ? "bg-green-500/10 text-green-400"
                        : "bg-yellow-500/10 text-yellow-400"
                    }`}
                  >
                    {compatResult.label}
                  </span>
                </div>
                <div className="w-full bg-white/5 h-1.5 mt-2 rounded-full overflow-hidden mb-4">
                  <div
                    className="bg-gradient-to-r from-primary to-accent-teal h-full"
                    style={{ width: `${(compatResult.total_score_36 / 36) * 100}%` }}
                  />
                </div>
              </>
            ) : (
              <p className="text-sm text-gray-500 italic text-center py-4">
                Click run to calculate
              </p>
            )}
          </div>
        </div>

        {/* Team Dimension Radar — shown when compat data available */}
        {compatResult && (
          <div className="col-span-1 md:col-span-2 xl:col-span-4 glass-card rounded-none p-6 border border-primary/10">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-white font-semibold font-display flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">radar</span>
                Team Dimension Alignment
              </h3>
              <div className="flex gap-2">
                {compatResult.strong_dimensions.slice(0, 2).map((d) => (
                  <span key={d} className="text-[10px] px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 font-mono">
                    ↑ {d.replace(/_/g, " ")}
                  </span>
                ))}
                {compatResult.weak_dimensions.slice(0, 2).map((d) => (
                  <span key={d} className="text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-mono">
                    ↓ {d.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
            <RadarChart dimensionScores={compatResult.dimension_scores} />
          </div>
        )}
      </div>
    </div>
  );
}

export function DashboardClient() {
  return (
    <ErrorBoundary fallbackMessage="Dashboard failed to load">
      <DashboardInner />
    </ErrorBoundary>
  );
}

import { useEffect, useMemo, useState } from "react";

import { api, type OrchestratorStreamEvent, type Team, wsUrlForRun } from "@/lib/api";
import { $session, $teams } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID, AUTH_REQUIRED } from "@/lib/featureFlags";
import { ErrorBoundary } from "@/components/ErrorBoundary";

type StreamConnection = "idle" | "connecting" | "streaming" | "done" | "error";

function memberInitials(userId: string) {
  const clean = userId.replace(/[^a-zA-Z]/g, "");
  return clean.slice(0, 2).toUpperCase() || "??";
}

function WorkspaceInner() {
  const session = $session.get();
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;

  if (AUTH_REQUIRED && !session) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <section className="glass-panel p-8 rounded-none w-full max-w-md text-center">
          <h3 className="text-xl font-bold font-display text-white">Authentication Required</h3>
          <p className="text-gray-400 mt-2 mb-6">Sign in on the auth page to run orchestrated analysis.</p>
          <a href="/auth" className="btn btn-primary justify-center">Go to Sign In</a>
        </section>
      </main>
    );
  }

  // ── Team state ──────────────────────────────────────────────────────────
  const [teams, setTeams] = useState<Team[]>([]);
  const [activeTeam, setActiveTeam] = useState<Team | null>(null);
  const [teamsLoading, setTeamsLoading] = useState(false);

  // ── Create Team Wizard ──────────────────────────────────────────────────
  const [showWizard, setShowWizard] = useState(false);
  const [wStep, setWStep] = useState<1 | 2 | 3>(1);
  const [wName, setWName] = useState("");
  const [wDesc, setWDesc] = useState("");
  const [wCreatedTeam, setWCreatedTeam] = useState<Team | null>(null);
  const [wInvUserId, setWInvUserId] = useState("");
  const [wInvHandle, setWInvHandle] = useState("");
  const [wInvRole, setWInvRole] = useState("");
  const [wLoading, setWLoading] = useState(false);
  const [wError, setWError] = useState<string | null>(null);

  // ── Invite Modal ────────────────────────────────────────────────────────
  const [showInvite, setShowInvite] = useState(false);
  const [invUserId, setInvUserId] = useState("");
  const [invHandle, setInvHandle] = useState("");
  const [invRole, setInvRole] = useState("");
  const [invLoading, setInvLoading] = useState(false);
  const [invError, setInvError] = useState<string | null>(null);

  // ── Orchestrator ────────────────────────────────────────────────────────
  const [events, setEvents] = useState<OrchestratorStreamEvent[]>([]);
  const [currentRun, setCurrentRun] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [connection, setConnection] = useState<StreamConnection>("idle");
  const [startingRun, setStartingRun] = useState(false);

  // ── Load teams on mount ─────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      setTeamsLoading(true);
      try {
        const data = await api.listTeams(userId);
        setTeams(data);
        $teams.set(data);
        if (data.length > 0) setActiveTeam((prev) => prev ?? data[0]);
      } catch {
        // silent
      } finally {
        setTeamsLoading(false);
      }
    })();
  }, [userId]);

  const syncTeams = (updated: Team) => {
    setTeams((prev) => {
      const next = prev.map((t) => (t.id === updated.id ? updated : t));
      $teams.set(next);
      return next;
    });
  };

  const refreshTeam = async (teamId: string) => {
    const updated = await api.getTeam(teamId);
    setActiveTeam(updated);
    syncTeams(updated);
  };

  // ── WebSocket for orchestrator ──────────────────────────────────────────
  useEffect(() => {
    if (!currentRun) return;
    setConnection("connecting");
    const ws = new WebSocket(wsUrlForRun(currentRun));
    let closedByClient = false;

    ws.onopen = () => setConnection("streaming");
    ws.onmessage = (evt) => {
      const payload = JSON.parse(evt.data) as OrchestratorStreamEvent;
      setEvents((prev) => [...prev, payload]);
      if (payload.status === "error") setConnection("error");
      else if (payload.step === "orchestration" && payload.status === "completed") setConnection("done");
    };
    ws.onerror = () => {
      setConnection("error");
      setRunError("WebSocket stream failed while receiving orchestrator updates.");
    };
    ws.onclose = () => {
      if (closedByClient) return;
      setConnection((s) => (s === "done" ? "done" : "error"));
    };
    return () => {
      closedByClient = true;
      ws.close();
    };
  }, [currentRun]);

  const latestProgress = useMemo(() => events.at(-1)?.progress_pct ?? 0, [events]);

  // ── Wizard handlers ─────────────────────────────────────────────────────
  const handleWizardCreate = async () => {
    if (!wName.trim()) return;
    setWLoading(true);
    setWError(null);
    try {
      const team = await api.createTeam(wName.trim(), wDesc.trim() || null, userId);
      setWCreatedTeam(team);
      setActiveTeam(team);
      setTeams((prev) => {
        const next = [...prev, team];
        $teams.set(next);
        return next;
      });
      setWStep(2);
    } catch {
      setWError("Failed to create team. Please try again.");
    } finally {
      setWLoading(false);
    }
  };

  const handleWizardInvite = async () => {
    if (!wCreatedTeam || !wInvUserId.trim()) return;
    setWLoading(true);
    setWError(null);
    try {
      await api.addMember(
        wCreatedTeam.id,
        wInvUserId.trim(),
        wInvHandle.trim() || undefined,
        wInvRole.trim() || undefined,
      );
      const updated = await api.getTeam(wCreatedTeam.id);
      setWCreatedTeam(updated);
      setActiveTeam(updated);
      syncTeams(updated);
      setWInvUserId("");
      setWInvHandle("");
      setWInvRole("");
    } catch {
      setWError("Failed to add member. They may already be in the team.");
    } finally {
      setWLoading(false);
    }
  };

  const closeWizard = () => {
    setShowWizard(false);
    setWStep(1);
    setWName("");
    setWDesc("");
    setWCreatedTeam(null);
    setWInvUserId("");
    setWInvHandle("");
    setWInvRole("");
    setWError(null);
  };

  // ── Invite modal handlers ───────────────────────────────────────────────
  const handleInvite = async () => {
    if (!activeTeam || !invUserId.trim()) return;
    setInvLoading(true);
    setInvError(null);
    try {
      await api.addMember(
        activeTeam.id,
        invUserId.trim(),
        invHandle.trim() || undefined,
        invRole.trim() || undefined,
      );
      await refreshTeam(activeTeam.id);
      setShowInvite(false);
      setInvUserId("");
      setInvHandle("");
      setInvRole("");
    } catch {
      setInvError("Failed to add member. They may already be in the team.");
    } finally {
      setInvLoading(false);
    }
  };

  const closeInvite = () => {
    setShowInvite(false);
    setInvUserId("");
    setInvHandle("");
    setInvRole("");
    setInvError(null);
  };

  // ── Remove member ───────────────────────────────────────────────────────
  const handleRemoveMember = async (memberId: string) => {
    if (!activeTeam) return;
    try {
      await api.removeMember(activeTeam.id, memberId);
      await refreshTeam(activeTeam.id);
    } catch {
      // silent
    }
  };

  // ── Run orchestrator ────────────────────────────────────────────────────
  const runOrchestrator = async () => {
    setStartingRun(true);
    setRunError(null);
    setConnection("idle");
    setEvents([]);
    setCurrentRun(null);
    try {
      const data = await api.orchestratorRun(activeTeam?.id ?? "team_alpha", userId, true);
      setCurrentRun(data.run_id);
    } catch {
      setRunError("Could not start orchestrator run.");
      setConnection("error");
    } finally {
      setStartingRun(false);
    }
  };

  return (
    <>
      {/* ── Create Team Wizard Modal ─────────────────────────────────────── */}
      {showWizard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
          <div className="glass-card w-full max-w-lg rounded-2xl border border-white/10 shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <div>
                <h2 className="text-lg font-bold font-display text-white">
                  {wStep === 1 && "Create a Team"}
                  {wStep === 2 && "Invite Members"}
                  {wStep === 3 && "Team Created!"}
                </h2>
                <div className="flex gap-2 mt-2">
                  {([1, 2, 3] as const).map((s) => (
                    <div
                      key={s}
                      className={`h-1 w-8 rounded-full transition-colors duration-300 ${s <= wStep ? "bg-primary" : "bg-white/10"}`}
                    />
                  ))}
                </div>
              </div>
              <button onClick={closeWizard} className="text-gray-400 hover:text-white transition-colors">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* Step 1: Team details */}
            {wStep === 1 && (
              <div className="p-6 space-y-4">
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block font-mono uppercase">Team Name *</label>
                  <input
                    type="text"
                    value={wName}
                    onChange={(e) => setWName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleWizardCreate()}
                    placeholder="e.g. Core Platform, Growth Squad..."
                    className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1.5 block font-mono uppercase">Description (optional)</label>
                  <textarea
                    value={wDesc}
                    onChange={(e) => setWDesc(e.target.value)}
                    placeholder="What does this team work on?"
                    rows={3}
                    className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none"
                  />
                </div>
                {wError && <p className="text-xs text-red-400">{wError}</p>}
                <button
                  onClick={handleWizardCreate}
                  disabled={!wName.trim() || wLoading}
                  className="w-full btn btn-primary py-3 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {wLoading ? "Creating..." : <>Create Team <span className="material-symbols-outlined text-sm">arrow_forward</span></>}
                </button>
              </div>
            )}

            {/* Step 2: Invite members */}
            {wStep === 2 && (
              <div className="p-6 space-y-4">
                <p className="text-sm text-gray-400">
                  Invite members by user ID. You can always add more later.
                </p>

                {wCreatedTeam && wCreatedTeam.members.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-mono uppercase text-gray-500 mb-2">
                      Members ({wCreatedTeam.members.length})
                    </p>
                    {wCreatedTeam.members.map((m) => (
                      <div
                        key={m.user_id}
                        className="flex items-center gap-2.5 py-2 px-3 bg-white/5 rounded-lg border border-white/5"
                      >
                        <div className="w-6 h-6 flex-shrink-0 rounded-full bg-gradient-to-tr from-primary to-purple-400 flex items-center justify-center text-[9px] font-bold text-white">
                          {memberInitials(m.user_id)}
                        </div>
                        <span className="text-xs text-white flex-1 font-mono truncate">{m.user_id}</span>
                        {m.role && (
                          <span className="text-[10px] text-gray-500 uppercase font-mono">{m.role}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div className="space-y-3 border-t border-white/10 pt-4">
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">User ID *</label>
                    <input
                      type="text"
                      value={wInvUserId}
                      onChange={(e) => setWInvUserId(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleWizardInvite()}
                      placeholder="user_github_abc123"
                      className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">GitHub Handle</label>
                      <input
                        type="text"
                        value={wInvHandle}
                        onChange={(e) => setWInvHandle(e.target.value)}
                        placeholder="handle"
                        className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">Role</label>
                      <input
                        type="text"
                        value={wInvRole}
                        onChange={(e) => setWInvRole(e.target.value)}
                        placeholder="Lead, Dev..."
                        className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                      />
                    </div>
                  </div>
                  {wError && <p className="text-xs text-red-400">{wError}</p>}
                  <button
                    onClick={handleWizardInvite}
                    disabled={!wInvUserId.trim() || wLoading}
                    className="w-full py-2.5 border border-dashed border-white/20 rounded-xl text-xs font-bold text-gray-400 hover:text-white hover:bg-white/10 hover:border-white/40 transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <span className="material-symbols-outlined text-sm">person_add</span>
                    {wLoading ? "Adding..." : "Add Member"}
                  </button>
                </div>

                <div className="flex gap-3 pt-1">
                  <button
                    onClick={() => setWStep(3)}
                    className="flex-1 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 transition-all"
                  >
                    Skip
                  </button>
                  <button
                    onClick={() => setWStep(3)}
                    className="flex-1 btn btn-primary py-2.5 rounded-xl text-sm"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}

            {/* Step 3: Done */}
            {wStep === 3 && (
              <div className="p-8 text-center space-y-5">
                <div className="w-16 h-16 rounded-2xl bg-accent-neon/10 border border-accent-neon/30 flex items-center justify-center mx-auto">
                  <span className="material-symbols-outlined text-3xl text-accent-neon">check_circle</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{wCreatedTeam?.name ?? wName}</h3>
                  <p className="text-sm text-gray-400 mt-1.5">
                    {wCreatedTeam?.members.length ?? 1} member{(wCreatedTeam?.members.length ?? 1) !== 1 ? "s" : ""} · Ready for full analysis
                  </p>
                  {wCreatedTeam?.description && (
                    <p className="text-xs text-gray-500 mt-2">{wCreatedTeam.description}</p>
                  )}
                </div>
                <button onClick={closeWizard} className="w-full btn btn-primary py-3 rounded-xl">
                  Go to Team
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Add Member Modal ─────────────────────────────────────────────── */}
      {showInvite && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
          <div className="glass-card w-full max-w-md rounded-2xl border border-white/10 shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <div>
                <h2 className="text-lg font-bold font-display text-white">Add Member</h2>
                {activeTeam && (
                  <p className="text-xs text-gray-500 mt-0.5 font-mono">{activeTeam.name}</p>
                )}
              </div>
              <button onClick={closeInvite} className="text-gray-400 hover:text-white transition-colors">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block font-mono uppercase">User ID *</label>
                <input
                  type="text"
                  value={invUserId}
                  onChange={(e) => setInvUserId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                  placeholder="user_github_abc123"
                  className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  autoFocus
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">GitHub Handle</label>
                  <input
                    type="text"
                    value={invHandle}
                    onChange={(e) => setInvHandle(e.target.value)}
                    placeholder="handle"
                    className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">Role</label>
                  <input
                    type="text"
                    value={invRole}
                    onChange={(e) => setInvRole(e.target.value)}
                    placeholder="Lead, Dev..."
                    className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  />
                </div>
              </div>
              {invError && <p className="text-xs text-red-400">{invError}</p>}
              <div className="flex gap-3">
                <button
                  onClick={closeInvite}
                  className="flex-1 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleInvite}
                  disabled={!invUserId.trim() || invLoading}
                  className="flex-1 btn btn-primary py-2.5 rounded-xl text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {invLoading ? "Adding..." : "Add Member"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Main Workspace ───────────────────────────────────────────────── */}
      <div className="flex-1 w-full max-w-[1400px] mx-auto px-4 md:px-8 pt-40 pb-24 flex flex-col min-h-screen relative z-10">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 px-2">
          <div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 font-display">
              Workspace
            </h1>
            <div className="flex items-center gap-2 mt-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-accent-neon"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-neon"></span>
              </span>
              <p className="text-gray-400 text-sm font-medium">Team Simulator v2.4</p>
            </div>
          </div>
        </header>

        <div className="flex flex-1 overflow-hidden glass-card rounded-2xl border border-white/10 min-h-[600px] mb-10 shadow-2xl">
          {/* Left Sidebar */}
          <aside className="w-80 border-r border-white/10 bg-white/5 flex flex-col z-10 overflow-y-auto backdrop-blur-md">
            {/* Team selector */}
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400 font-display">Team Setup</h2>
                <span className="material-symbols-outlined text-gray-500 text-sm">tune</span>
              </div>
              <p className="text-xs text-gray-600 mb-3">Select a team and run a full multi-agent analysis — GitHub signals, psychometrics, and Claude synthesis.</p>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block font-mono">TARGET TEAM</label>
                  {teamsLoading ? (
                    <div className="w-full h-9 bg-black/20 border border-white/10 rounded-lg animate-pulse" />
                  ) : teams.length > 0 ? (
                    <select
                      value={activeTeam?.id ?? ""}
                      onChange={(e) => {
                        const found = teams.find((t) => t.id === e.target.value);
                        if (found) setActiveTeam(found);
                      }}
                      className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    >
                      {teams.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-xs text-gray-500 py-1.5">No teams yet.</p>
                  )}
                </div>
                <button
                  onClick={() => setShowWizard(true)}
                  className="w-full py-2 border border-dashed border-white/20 rounded-lg text-xs font-bold text-gray-400 hover:text-white hover:bg-white/10 hover:border-white/40 transition-all flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-sm">add</span>
                  CREATE TEAM
                </button>
              </div>
            </div>

            {/* Members list */}
            <div className="p-6 flex-1">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400 font-display">
                  {activeTeam ? "Team Members" : "Talent Inventory"}
                </h2>
                {activeTeam && (
                  <span className="text-xs font-mono text-gray-500 bg-white/5 px-2 py-0.5 rounded">
                    {activeTeam.members.length}
                  </span>
                )}
              </div>

              {activeTeam ? (
                <div className="space-y-2">
                  {activeTeam.members.length === 0 ? (
                    <p className="text-xs text-gray-500">No members yet.</p>
                  ) : (
                    activeTeam.members.map((m, i) => (
                      <div
                        key={m.user_id}
                        className="glass-panel p-3 rounded-xl border-l-4 flex items-center justify-between group cursor-default hover:bg-white/10 transition-colors"
                        style={{ borderLeftColor: i % 2 === 0 ? "var(--color-primary, #ccff00)" : "var(--color-accent-teal, #00f0b5)" }}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div
                            className={`w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center text-xs font-bold text-white ${i % 2 === 0 ? "bg-gradient-to-tr from-primary to-purple-400" : "bg-gradient-to-tr from-accent-teal to-blue-400"}`}
                          >
                            {memberInitials(m.user_id)}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-white leading-none truncate max-w-[130px]">
                              {m.github_handle ? `@${m.github_handle}` : m.user_id}
                            </p>
                            <p className="text-[10px] text-gray-400 mt-1 uppercase font-mono">
                              {m.role ?? "Member"}
                            </p>
                          </div>
                        </div>
                        {m.user_id !== userId && (
                          <button
                            onClick={() => handleRemoveMember(m.user_id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-red-400 ml-1 flex-shrink-0"
                            title="Remove member"
                          >
                            <span className="material-symbols-outlined text-sm">person_remove</span>
                          </button>
                        )}
                      </div>
                    ))
                  )}
                  <button
                    onClick={() => setShowInvite(true)}
                    className="w-full mt-2 py-3 border border-dashed border-white/20 rounded-xl text-xs font-bold text-gray-400 hover:text-white hover:bg-white/10 hover:border-white/40 transition-all flex items-center justify-center gap-2"
                  >
                    <span className="material-symbols-outlined text-sm">person_add</span>
                    ADD MEMBER
                  </button>
                </div>
              ) : (
                <p className="text-xs text-gray-500">Select or create a team to manage members.</p>
              )}
            </div>

            {/* Run button */}
            <div className="p-6 border-t border-white/10 bg-black/20">
              <button
                className="w-full btn btn-primary py-3.5 shadow-neon rounded-xl flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={runOrchestrator}
                disabled={startingRun || connection === "connecting" || connection === "streaming"}
              >
                <span className="material-symbols-outlined">play_arrow</span>
                {startingRun ? "Starting..." : connection === "streaming" ? "Running..." : "Run Full Analysis"}
              </button>
            </div>
          </aside>

          {/* Main Simulator Canvas */}
          <main className="flex-1 bg-black/40 relative flex flex-col overflow-hidden">
            <div className="absolute inset-0 bg-grid-pattern opacity-30 pointer-events-none"></div>

            <div className="flex-1 overflow-y-auto p-8 md:p-12 pb-32 z-10">
              {!currentRun && events.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-60">
                  <div className="w-20 h-20 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mb-6 shadow-2xl">
                    <span className="material-symbols-outlined text-5xl text-gray-400">schema</span>
                  </div>
                  <h3 className="text-2xl font-bold font-display text-white">Simulator Idle</h3>
                  <p className="text-sm text-gray-400 mt-3 max-w-sm">
                    {activeTeam
                      ? `Configure ${activeTeam.name} on the left and run the simulation to see real-time analysis.`
                      : "Create or select a team on the left, then run the simulation."}
                  </p>
                </div>
              ) : (
                <div className="max-w-3xl mx-auto flex flex-col gap-6">
                  {/* Pipeline Progress Header */}
                  <div className="glass-panel p-6 rounded-2xl mb-4 border-white/10 sticky top-0 z-20 bg-[#121215]/80 backdrop-blur-xl shadow-xl">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="font-bold font-display text-white flex items-center gap-2">
                        <span className={`material-symbols-outlined ${connection === "streaming" ? "text-primary animate-spin-slow" : "text-accent-neon"}`}>
                          {connection === "streaming" ? "sync" : "task_alt"}
                        </span>
                        {connection === "streaming" ? "Analysis in Progress..." : "Analysis Complete"}
                      </h3>
                      <span className="text-2xl font-bold font-mono text-primary">{latestProgress}%</span>
                    </div>
                    <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden mt-2">
                      <div
                        className="h-full bg-gradient-to-r from-primary to-accent-teal transition-all duration-300"
                        style={{ width: `${latestProgress}%` }}
                      />
                    </div>
                  </div>

                  {runError && (
                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-center gap-2">
                      <span className="material-symbols-outlined">error</span>
                      {runError}
                    </div>
                  )}

                  {/* Event Stream Log — filter out synthesis_token events (no step field) */}
                  {events.filter((e) => !!e.step).map((event, idx) => {
                    const isError = event.status === "error";
                    const isCompleted = event.status === "completed";
                    const isRunning = event.status === "running";

                    let icon = "pending";
                    let colorClass = "text-gray-400 border-white/5 bg-white/5";

                    if (isCompleted) {
                      icon = "check_circle";
                      colorClass = "text-accent-neon border-accent-neon/30 bg-accent-neon/5";
                    } else if (isError) {
                      icon = "error";
                      colorClass = "text-red-400 border-red-500/30 bg-red-500/5";
                    } else if (isRunning) {
                      icon = "sync";
                      colorClass = "text-primary border-primary/50 bg-primary/10 shadow-[0_0_15px_rgba(204,255,0,0.2)]";
                    }

                    return (
                      <div
                        key={`${event.step}-${idx}`}
                        className={`p-5 rounded-2xl border ${colorClass} transition-all duration-500 flex items-start gap-4`}
                      >
                        <span className={`material-symbols-outlined mt-0.5 ${isRunning ? "animate-spin-slow" : ""}`}>
                          {icon}
                        </span>
                        <div className="flex-1">
                          <div className="flex justify-between items-center mb-1">
                            <h4 className="font-bold uppercase tracking-wider text-sm font-display">
                              {event.step.replace(/_/g, " ")}
                            </h4>
                            <span className="text-xs font-mono opacity-60 bg-black/20 px-2 py-0.5 rounded">
                              {event.progress_pct}%
                            </span>
                          </div>
                          {event.message && <p className="text-sm opacity-80 mt-2">{event.message}</p>}
                        </div>
                      </div>
                    );
                  })}

                  {connection === "done" && (
                    <div className="mt-8 flex justify-center animate-pulse-slow">
                      <a href="/insights" className="btn btn-primary px-8 py-3 rounded-xl shadow-neon flex items-center gap-2">
                        View Full Synthesis
                        <span className="material-symbols-outlined text-sm">arrow_forward</span>
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          </main>
        </div>
      </div>
    </>
  );
}

export function WorkspaceClient() {
  return (
    <ErrorBoundary fallbackMessage="Workspace failed to load">
      <WorkspaceInner />
    </ErrorBoundary>
  );
}

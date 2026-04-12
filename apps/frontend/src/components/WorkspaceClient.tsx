import { useEffect, useMemo, useState } from "react";
import { useStore } from "@nanostores/react";
import { AnimatePresence, motion } from "framer-motion";
import { fadeInUp, scaleIn, slideDown, stagger } from "@/lib/motion";

import { api, type OrchestratorStreamEvent, type Team, type UserSearchResult, wsUrlForRun } from "@/lib/api";
import { $activeTeam, $session, $teams, setActiveTeam as setGlobalActiveTeam } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID, AUTH_REQUIRED } from "@/lib/featureFlags";
import { ErrorBoundary } from "@/components/ErrorBoundary";

type StreamConnection = "idle" | "connecting" | "streaming" | "done" | "error";

function memberInitials(userId: string) {
  const clean = userId.replace(/[^a-zA-Z]/g, "");
  return clean.slice(0, 2).toUpperCase() || "??";
}

function WorkspaceInner() {
  // mounted guard: server + first client render produce same output → no hydration mismatch
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const session = useStore($session);
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;

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
  const [wInvSearch, setWInvSearch] = useState("");
  const [wInvSearchResults, setWInvSearchResults] = useState<UserSearchResult[]>([]);
  const [wInvSearchLoading, setWInvSearchLoading] = useState(false);
  const [wInvSelectedUser, setWInvSelectedUser] = useState<UserSearchResult | null>(null);
  const [wInvShowDropdown, setWInvShowDropdown] = useState(false);

  // ── Team Edit Modal ─────────────────────────────────────────────────────
  const [showEditTeam, setShowEditTeam] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // ── Invite Modal ────────────────────────────────────────────────────────
  const [showInvite, setShowInvite] = useState(false);
  const [invUserId, setInvUserId] = useState("");
  const [invHandle, setInvHandle] = useState("");
  const [invRole, setInvRole] = useState("");
  const [invLoading, setInvLoading] = useState(false);
  const [invError, setInvError] = useState<string | null>(null);
  const [invSearch, setInvSearch] = useState("");
  const [invSearchResults, setInvSearchResults] = useState<UserSearchResult[]>([]);
  const [invSearchLoading, setInvSearchLoading] = useState(false);
  const [invSelectedUser, setInvSelectedUser] = useState<UserSearchResult | null>(null);
  const [invShowDropdown, setInvShowDropdown] = useState(false);

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
        if (data.length > 0) {
          const persisted = $activeTeam.get();
          const initialTeam = persisted ? (data.find((t) => t.id === persisted.id) ?? data[0]) : data[0];
          setActiveTeam(initialTeam);     // local state
          setGlobalActiveTeam(initialTeam); // global atom + localStorage
        }
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
      setGlobalActiveTeam(team);
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

  const handleWInvSearch = async (q: string) => {
    setWInvSearch(q);
    setWInvSelectedUser(null);
    if (q.length < 2) { setWInvSearchResults([]); setWInvShowDropdown(false); return; }
    setWInvSearchLoading(true);
    try {
      const results = await api.searchUsers(q);
      setWInvSearchResults(results);
      setWInvShowDropdown(true);
    } catch { setWInvSearchResults([]); } finally { setWInvSearchLoading(false); }
  };

  const handleWInvSelectUser = (u: UserSearchResult) => {
    setWInvSelectedUser(u);
    setWInvUserId(u.user_id);
    setWInvHandle(u.github_handle ?? "");
    setWInvSearch(u.display_name || u.github_handle || u.user_id);
    setWInvShowDropdown(false);
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
      setGlobalActiveTeam(updated);
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
    setWInvSearch("");
    setWInvSearchResults([]);
    setWInvSelectedUser(null);
    setWInvShowDropdown(false);
  };

  // ── Invite modal handlers ───────────────────────────────────────────────
  const handleInviteSearch = async (q: string) => {
    setInvSearch(q);
    setInvSelectedUser(null);
    if (q.length < 2) {
      setInvSearchResults([]);
      setInvShowDropdown(false);
      return;
    }
    setInvSearchLoading(true);
    try {
      const results = await api.searchUsers(q);
      setInvSearchResults(results);
      setInvShowDropdown(true);
    } catch {
      setInvSearchResults([]);
    } finally {
      setInvSearchLoading(false);
    }
  };

  const handleInviteSelectUser = (user: UserSearchResult) => {
    setInvSelectedUser(user);
    setInvUserId(user.user_id);
    setInvHandle(user.github_handle ?? "");
    setInvSearch(user.display_name || user.github_handle || user.user_id);
    setInvShowDropdown(false);
  };

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
    setInvSearch("");
    setInvSearchResults([]);
    setInvSelectedUser(null);
    setInvShowDropdown(false);
  };

  // ── Edit team ───────────────────────────────────────────────────────────
  const openEditTeam = () => {
    setEditName(activeTeam?.name ?? "");
    setEditDesc(activeTeam?.description ?? "");
    setEditError(null);
    setShowEditTeam(true);
  };

  const handleEditTeam = async () => {
    if (!activeTeam || !editName.trim()) return;
    setEditLoading(true);
    setEditError(null);
    try {
      const updated = await api.updateTeam(activeTeam.id, editName.trim(), editDesc.trim() || undefined);
      setActiveTeam(updated);
      setGlobalActiveTeam(updated);
      syncTeams(updated);
      setShowEditTeam(false);
    } catch {
      setEditError("Failed to update team.");
    } finally {
      setEditLoading(false);
    }
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

  if (!mounted) return <div className="min-h-screen" />;

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

  return (
    <>
      {/* ── Create Team Wizard Modal ─────────────────────────────────────── */}
      <AnimatePresence>
      {showWizard && (
        <motion.div variants={fadeInUp} initial="hidden" animate="visible" exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
          <motion.div variants={scaleIn} initial="hidden" animate="visible" className="glass-card w-full max-w-lg rounded-2xl border border-white/10 shadow-2xl">
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
                  Search for registered users by name or GitHub handle. You can always add more later.
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
                  {/* Search */}
                  <div className="relative">
                    <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">Search User</label>
                    <div className="relative">
                      <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-base pointer-events-none">search</span>
                      <input
                        type="text"
                        value={wInvSearch}
                        onChange={(e) => handleWInvSearch(e.target.value)}
                        onFocus={() => wInvSearchResults.length > 0 && setWInvShowDropdown(true)}
                        placeholder="Name or GitHub handle…"
                        className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                      />
                      {wInvSearchLoading && (
                        <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-base animate-spin">progress_activity</span>
                      )}
                    </div>
                    {wInvShowDropdown && wInvSearchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg shadow-xl overflow-hidden">
                        {wInvSearchResults.map((u) => (
                          <button key={u.user_id} onClick={() => handleWInvSelectUser(u)}
                            className="w-full flex items-center gap-3 px-3 py-2 hover:bg-white/5 text-left transition-colors">
                            {u.github_avatar_url ? (
                              <img src={u.github_avatar_url} alt="" className="w-6 h-6 rounded-full shrink-0" />
                            ) : (
                              <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                                <span className="text-[9px] font-bold text-primary">{(u.github_handle || u.user_id).slice(0, 2).toUpperCase()}</span>
                              </div>
                            )}
                            <div className="min-w-0">
                              <p className="text-xs text-white truncate">{u.display_name || u.github_handle || u.user_id}</p>
                              {u.github_handle && <p className="text-[10px] text-gray-500">@{u.github_handle}</p>}
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                    {wInvShowDropdown && wInvSearch.length >= 2 && wInvSearchResults.length === 0 && !wInvSearchLoading && (
                      <div className="absolute z-10 w-full mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-xs text-gray-500 text-center shadow-xl">
                        No users found
                      </div>
                    )}
                  </div>
                  {wInvSelectedUser && (
                    <div className="flex items-center gap-2 bg-primary/10 border border-primary/30 rounded-lg px-3 py-1.5">
                      {wInvSelectedUser.github_avatar_url && <img src={wInvSelectedUser.github_avatar_url} alt="" className="w-5 h-5 rounded-full" />}
                      <span className="text-xs text-white">{wInvSelectedUser.display_name || wInvSelectedUser.github_handle}</span>
                      {wInvSelectedUser.github_handle && <span className="text-[10px] text-gray-400 ml-auto">@{wInvSelectedUser.github_handle}</span>}
                    </div>
                  )}
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">Role (optional)</label>
                    <input
                      type="text"
                      value={wInvRole}
                      onChange={(e) => setWInvRole(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleWizardInvite()}
                      placeholder="Lead, Dev..."
                      className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    />
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
          </motion.div>
        </motion.div>
      )}
      </AnimatePresence>

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
              {/* Search box */}
              <div className="relative">
                <label className="text-xs text-gray-500 mb-1.5 block font-mono uppercase">Search User *</label>
                <div className="relative">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-base pointer-events-none">search</span>
                  <input
                    type="text"
                    value={invSearch}
                    onChange={(e) => handleInviteSearch(e.target.value)}
                    onFocus={() => invSearchResults.length > 0 && setInvShowDropdown(true)}
                    placeholder="Search by name or GitHub handle…"
                    className="w-full bg-black/20 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                    autoFocus
                  />
                  {invSearchLoading && (
                    <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-base animate-spin">progress_activity</span>
                  )}
                </div>
                {/* Dropdown results */}
                {invShowDropdown && invSearchResults.length > 0 && (
                  <div className="absolute z-10 w-full mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg shadow-xl overflow-hidden">
                    {invSearchResults.map((u) => (
                      <button
                        key={u.user_id}
                        onClick={() => handleInviteSelectUser(u)}
                        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 text-left transition-colors"
                      >
                        {u.github_avatar_url ? (
                          <img src={u.github_avatar_url} alt="" className="w-7 h-7 rounded-full shrink-0" />
                        ) : (
                          <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                            <span className="text-xs font-bold text-primary">{(u.github_handle || u.user_id).slice(0, 2).toUpperCase()}</span>
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="text-sm text-white truncate">{u.display_name || u.github_handle || u.user_id}</p>
                          {u.github_handle && <p className="text-xs text-gray-500 truncate">@{u.github_handle}</p>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                {invShowDropdown && invSearch.length >= 2 && invSearchResults.length === 0 && !invSearchLoading && (
                  <div className="absolute z-10 w-full mt-1 bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-3 text-xs text-gray-500 text-center shadow-xl">
                    No users found
                  </div>
                )}
              </div>
              {/* Selected user chip */}
              {invSelectedUser && (
                <div className="flex items-center gap-2 bg-primary/10 border border-primary/30 rounded-lg px-3 py-2">
                  {invSelectedUser.github_avatar_url && (
                    <img src={invSelectedUser.github_avatar_url} alt="" className="w-5 h-5 rounded-full" />
                  )}
                  <span className="text-sm text-white">{invSelectedUser.display_name || invSelectedUser.github_handle}</span>
                  {invSelectedUser.github_handle && <span className="text-xs text-gray-400 ml-auto">@{invSelectedUser.github_handle}</span>}
                </div>
              )}
              {/* Role */}
              <div>
                <label className="text-xs text-gray-500 mb-1 block font-mono uppercase">Role (optional)</label>
                <input
                  type="text"
                  value={invRole}
                  onChange={(e) => setInvRole(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleInvite()}
                  placeholder="Lead, Dev, Designer…"
                  className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
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

      {/* ── Edit Team Modal ─────────────────────────────────────────────── */}
      {showEditTeam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
          <div className="glass-card w-full max-w-md rounded-2xl border border-white/10 shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <h2 className="text-lg font-bold font-display text-white">Edit Team</h2>
              <button onClick={() => setShowEditTeam(false)} className="text-gray-400 hover:text-white transition-colors">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block font-mono uppercase">Team Name *</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleEditTeam()}
                  className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block font-mono uppercase">Description</label>
                <textarea
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  rows={3}
                  className="w-full bg-black/20 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none"
                />
              </div>
              {editError && <p className="text-xs text-red-400">{editError}</p>}
              <div className="flex gap-3">
                <button
                  onClick={() => setShowEditTeam(false)}
                  className="flex-1 py-2.5 text-sm text-gray-400 border border-white/10 rounded-xl hover:bg-white/5 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEditTeam}
                  disabled={!editName.trim() || editLoading}
                  className="flex-1 btn btn-primary py-2.5 rounded-xl text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {editLoading ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Main Workspace ───────────────────────────────────────────────── */}
      <motion.div variants={fadeInUp} initial="hidden" animate="visible" className="flex-1 w-full max-w-[1400px] mx-auto px-4 md:px-8 pt-10 pb-24 flex flex-col min-h-screen relative z-10">
        <motion.header variants={slideDown} initial="hidden" animate="visible" className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 px-2">
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
        </motion.header>

        <motion.div variants={scaleIn} initial="hidden" animate="visible" className="flex flex-col md:flex-row flex-1 overflow-hidden glass-card rounded-2xl border border-white/10 min-h-[600px] mb-10 shadow-2xl">
          {/* Left Sidebar */}
          <aside className="w-full md:w-80 border-b md:border-b-0 md:border-r border-white/10 bg-white/5 flex flex-col z-10 overflow-y-auto backdrop-blur-md">
            {/* Team selector */}
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-sm font-bold uppercase tracking-widest text-gray-400 font-display">Team Setup</h2>
                <button
                  onClick={openEditTeam}
                  disabled={!activeTeam}
                  className="text-gray-500 hover:text-primary transition-colors disabled:opacity-30"
                  title="Edit team"
                >
                  <span className="material-symbols-outlined text-sm">tune</span>
                </button>
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
                        if (found) { setActiveTeam(found); setGlobalActiveTeam(found); }
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

            {/* Compatibility shortcut */}
            {activeTeam && activeTeam.members.length >= 2 && (
              <div className="px-6 pb-4">
                <a
                  href="/compatibility"
                  className="w-full flex items-center justify-center gap-2 py-2.5 text-xs font-bold text-purple-400 border border-purple-400/20 rounded-lg hover:bg-purple-400/10 transition-all"
                >
                  <span className="material-symbols-outlined text-sm">compare_arrows</span>
                  Pairwise Compatibility
                </a>
              </div>
            )}

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
        </motion.div>
      </motion.div>
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

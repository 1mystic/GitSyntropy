import { useEffect, useRef, useState } from "react";
import { useStore } from "@nanostores/react";
import { api, type Team } from "@/lib/api";
import { $activeTeam, $session, $teams, hydrateActiveTeam, hydrateSession, setActiveTeam } from "@/lib/stores";

export function GlobalTeamSelector() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    hydrateSession();
    hydrateActiveTeam();
    setMounted(true);
  }, []);

  const session = useStore($session);
  const teams = useStore($teams);
  const activeTeam = useStore($activeTeam);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load teams if authenticated and store is empty
  useEffect(() => {
    if (!session || teams.length > 0) return;
    setLoading(true);
    void api
      .listTeams(session.userId)
      .then((data) => {
        $teams.set(data);
        // Auto-select first team if nothing persisted
        const persisted = $activeTeam.get();
        if (!persisted && data.length > 0) {
          setActiveTeam(data[0]);
        } else if (persisted) {
          // Refresh persisted team object in case it changed
          const fresh = data.find((t) => t.id === persisted.id);
          if (fresh) setActiveTeam(fresh);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [session?.userId]);

  // Keep activeTeam in sync when teams list updates and no active team
  useEffect(() => {
    if (teams.length > 0 && !$activeTeam.get()) {
      setActiveTeam(teams[0]);
    }
  }, [teams]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Don't render until mounted (avoids SSR mismatch) or if not logged in
  if (!mounted || !session) return null;

  const select = (team: Team) => {
    setActiveTeam(team);
    setOpen(false);
  };

  return (
    <div
      ref={dropdownRef}
      className="fixed top-4 right-4 z-[60] flex flex-col items-end"
    >
      {/* Trigger button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`flex items-center gap-2 px-3 py-2 rounded-xl border backdrop-blur-md shadow-lg transition-all text-sm font-medium ${
          open
            ? "bg-primary/20 border-primary/50 text-white"
            : "bg-[#080808]/90 border-white/10 text-gray-300 hover:border-white/30 hover:text-white"
        }`}
        title="Switch active team"
      >
        <span className="material-symbols-outlined text-[16px] text-primary">schema</span>
        <span className="max-w-[140px] truncate font-display text-xs">
          {loading ? "Loading…" : activeTeam?.name ?? "No team"}
        </span>
        <span className="material-symbols-outlined text-[14px] text-gray-500 transition-transform" style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}>
          expand_more
        </span>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="mt-2 w-64 bg-[#0d0d0f]/95 border border-white/10 rounded-xl shadow-2xl backdrop-blur-xl overflow-hidden">
          {teams.length === 0 ? (
            <div className="px-4 py-4 text-center">
              <p className="text-xs text-gray-500 mb-3">No teams yet</p>
              <a
                href="/workspace"
                className="text-xs font-bold text-primary hover:text-white transition-colors"
                onClick={() => setOpen(false)}
              >
                + Create your first team
              </a>
            </div>
          ) : (
            <>
              <div className="px-3 pt-2.5 pb-1">
                <p className="text-[10px] font-mono text-gray-600 uppercase tracking-widest">Active Team</p>
              </div>
              <div className="flex flex-col pb-2">
                {teams.map((team) => {
                  const isActive = team.id === activeTeam?.id;
                  return (
                    <button
                      key={team.id}
                      onClick={() => select(team)}
                      className={`flex items-center gap-3 px-3 py-2.5 text-left hover:bg-white/5 transition-colors ${
                        isActive ? "text-white" : "text-gray-400 hover:text-white"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                          isActive ? "bg-primary" : "bg-white/10"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate font-display">{team.name}</p>
                        <p className="text-[10px] text-gray-600 truncate">
                          {team.members.length} member{team.members.length !== 1 ? "s" : ""} ·{" "}
                          {team.members.find((m) => m.role === "owner")?.github_handle
                            ? `@${team.members.find((m) => m.role === "owner")!.github_handle}`
                            : "owner"}
                        </p>
                      </div>
                      {isActive && (
                        <span className="material-symbols-outlined text-primary text-[16px] flex-shrink-0">
                          check
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
              <div className="border-t border-white/5 px-3 py-2">
                <a
                  href="/workspace"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 text-xs text-gray-500 hover:text-primary transition-colors py-1"
                >
                  <span className="material-symbols-outlined text-[14px]">add</span>
                  Create new team
                </a>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

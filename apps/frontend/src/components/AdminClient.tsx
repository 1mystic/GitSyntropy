import { useEffect, useState } from "react";
import { useStore } from "@nanostores/react";
import { motion, AnimatePresence } from "framer-motion";
import { fadeInUp, stagger } from "@/lib/motion";
import { api, type AdminStatsResponse, type AdminUserResponse } from "@/lib/api";
import { $session, clearSession } from "@/lib/stores";

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------
function StatCard({ label, value, icon, color = "primary" }: { label: string; value: number; icon: string; color?: string }) {
  const colorMap: Record<string, string> = {
    primary: "text-primary bg-primary/10 border-primary/20",
    teal: "text-accent-teal bg-accent-teal/10 border-accent-teal/20",
    neon: "text-accent-neon bg-accent-neon/10 border-accent-neon/20",
    purple: "text-purple-400 bg-purple-400/10 border-purple-400/20",
    amber: "text-amber-400 bg-amber-400/10 border-amber-400/20",
  };
  return (
    <div className="glass-card rounded-none p-5 flex flex-col gap-2">
      <div className={`w-9 h-9 rounded-lg border flex items-center justify-center ${colorMap[color] ?? colorMap.primary}`}>
        <span className="material-symbols-outlined text-[18px]">{icon}</span>
      </div>
      <p className="text-2xl font-bold font-display">{value.toLocaleString()}</p>
      <p className="text-xs text-gray-500 uppercase tracking-wider font-mono">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// User row
// ---------------------------------------------------------------------------
function UserRow({ user, index }: { user: AdminUserResponse; index: number }) {
  const joinDate = user.created_at ? new Date(user.created_at).toLocaleDateString() : "—";
  const lastSeen = user.last_seen_at ? new Date(user.last_seen_at).toLocaleDateString() : "—";

  return (
    <motion.tr
      variants={fadeInUp}
      className="border-b border-white/5 hover:bg-white/3 transition-colors"
    >
      <td className="py-3 px-4 text-gray-500 text-xs font-mono w-8">{index + 1}</td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          {user.github_avatar_url ? (
            <img src={user.github_avatar_url} alt="" className="w-8 h-8 rounded-full ring-1 ring-white/10" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
              <span className="material-symbols-outlined text-[16px] text-gray-400">person</span>
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-white">
              {user.github_name || user.github_handle || user.user_id}
              {user.is_superadmin && (
                <span className="ml-2 text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-mono">admin</span>
              )}
            </p>
            {user.github_handle && (
              <a
                href={`https://github.com/${user.github_handle}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-gray-500 hover:text-white transition-colors"
              >
                @{user.github_handle}
              </a>
            )}
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-xs text-gray-400 font-mono hidden md:table-cell">
        {user.github_email || "—"}
      </td>
      <td className="py-3 px-4 text-center">
        <span className={`text-xs px-2 py-0.5 rounded font-mono ${user.assessment_complete ? "bg-accent-green/15 text-accent-neon" : "bg-white/5 text-gray-600"}`}>
          {user.assessment_complete ? "done" : "—"}
        </span>
      </td>
      <td className="py-3 px-4 text-center text-sm font-mono text-gray-300">{user.team_count}</td>
      <td className="py-3 px-4 text-center text-sm font-mono text-gray-300 hidden lg:table-cell">{user.github_syncs}</td>
      <td className="py-3 px-4 text-center text-sm font-mono text-gray-300 hidden lg:table-cell">{user.agent_runs}</td>
      <td className="py-3 px-4 text-xs text-gray-500 font-mono hidden xl:table-cell">{joinDate}</td>
      <td className="py-3 px-4 text-xs text-gray-500 font-mono hidden xl:table-cell">{lastSeen}</td>
    </motion.tr>
  );
}

// ---------------------------------------------------------------------------
// Main admin component
// ---------------------------------------------------------------------------
export function AdminClient() {
  const session = useStore($session);

  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [users, setUsers] = useState<AdminUserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  // Guard: must be logged in + superadmin
  if (!session) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="glass-panel p-10 rounded-none w-full max-w-md text-center flex flex-col items-center gap-6">
          <span className="material-symbols-outlined text-5xl text-red-400">lock</span>
          <h3 className="text-xl font-bold font-display">Sign in required</h3>
          <a href="/auth?next=/admin" className="btn btn-primary w-full justify-center">Sign in with GitHub</a>
        </div>
      </main>
    );
  }

  if (!session.isSuperadmin) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
        <div className="glass-panel p-10 rounded-none w-full max-w-md text-center flex flex-col items-center gap-4">
          <span className="material-symbols-outlined text-5xl text-red-400">gpp_bad</span>
          <h3 className="text-xl font-bold font-display text-red-400">Access Denied</h3>
          <p className="text-gray-400 text-sm">This page is restricted to the site administrator.</p>
          <a href="/workspace" className="btn btn-secondary">Back to Workspace</a>
        </div>
      </main>
    );
  }

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, u] = await Promise.all([
          api.adminStats(session.token),
          api.adminUsers(session.token),
        ]);
        setStats(s);
        setUsers(u);
      } catch (e) {
        setError("Failed to load admin data. Backend may be unavailable.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [session.token]);

  const filteredUsers = users.filter((u) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      u.github_handle?.toLowerCase().includes(q) ||
      u.github_name?.toLowerCase().includes(q) ||
      u.github_email?.toLowerCase().includes(q) ||
      u.user_id.toLowerCase().includes(q)
    );
  });

  return (
    <main className="relative z-10 px-4 md:px-8 pt-8 pb-16 w-full max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-primary text-sm">admin_panel_settings</span>
            <span className="text-xs text-primary font-mono uppercase tracking-widest">Superadmin</span>
          </div>
          <h1 className="text-3xl font-bold font-display">Platform Control</h1>
          <p className="text-gray-500 text-sm mt-1">
            Signed in as <span className="text-white font-mono">@{session.githubHandle}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a href="/workspace" className="btn btn-secondary text-sm py-2 px-4">
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            Workspace
          </a>
          <button onClick={() => clearSession()} className="btn btn-secondary text-sm py-2 px-4 text-red-400 border-red-400/30 hover:bg-red-400/5">
            Sign Out
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20 text-gray-500">
          <span className="material-symbols-outlined animate-spin mr-2">refresh</span>
          Loading platform data…
        </div>
      )}

      {error && (
        <div className="p-4 rounded-none bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-6">
          {error}
        </div>
      )}

      {!loading && stats && (
        <>
          {/* Stats grid */}
          <motion.div variants={stagger} initial="hidden" animate="visible" className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
            <motion.div variants={fadeInUp}><StatCard label="Total Users" value={stats.total_users} icon="group" color="primary" /></motion.div>
            <motion.div variants={fadeInUp}><StatCard label="Teams" value={stats.total_teams} icon="groups" color="teal" /></motion.div>
            <motion.div variants={fadeInUp}><StatCard label="Assessments" value={stats.total_assessments} icon="psychology" color="neon" /></motion.div>
            <motion.div variants={fadeInUp}><StatCard label="GitHub Syncs" value={stats.total_github_syncs} icon="sync" color="purple" /></motion.div>
            <motion.div variants={fadeInUp}><StatCard label="Agent Runs" value={stats.total_agent_runs} icon="smart_toy" color="amber" /></motion.div>
          </motion.div>

          {/* Users table */}
          <div className="glass-card rounded-none overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/8 gap-4 flex-wrap">
              <h2 className="font-bold font-display text-lg">All Users <span className="text-gray-500 text-sm font-normal ml-1">({filteredUsers.length})</span></h2>
              <input
                type="text"
                placeholder="Search by handle, name, or email…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-[#0A0A0B] border border-white/20 rounded-none px-4 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-primary transition-all w-full max-w-xs"
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/8 text-left">
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs w-8">#</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs">User</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs hidden md:table-cell">Email</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs text-center">Assessment</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs text-center">Teams</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs text-center hidden lg:table-cell">GH Syncs</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs text-center hidden lg:table-cell">Runs</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs hidden xl:table-cell">Joined</th>
                    <th className="py-3 px-4 text-gray-600 font-mono text-xs hidden xl:table-cell">Last Seen</th>
                  </tr>
                </thead>
                <motion.tbody variants={stagger} initial="hidden" animate="visible">
                  {filteredUsers.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-16 text-center text-gray-600 text-sm">
                        {search ? "No users match your search." : "No users yet."}
                      </td>
                    </tr>
                  ) : (
                    filteredUsers.map((u, i) => <UserRow key={u.user_id} user={u} index={i} />)
                  )}
                </motion.tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </main>
  );
}

import { useMemo, useState } from "react";
import { useStore } from "@nanostores/react";

import { type CompatibilityResponse, api } from "@/lib/api";
import { $session, $teams } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID, AUTH_REQUIRED } from "@/lib/featureFlags";

export function CompatibilityClient() {
  const _session = $session.get();
  if (AUTH_REQUIRED && !_session) {
    return (
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-10 pb-12 w-full max-w-3xl mx-auto">
        <section className="glass-panel p-8 rounded-none w-full text-center">
          <h3 className="text-xl font-bold font-display text-white">Authentication Required</h3>
          <p className="text-gray-400 mt-2 mb-6">Sign in on the auth page to view compatibility analysis.</p>
          <a href="/auth" className="btn btn-primary justify-center">Go to Sign In</a>
        </section>
      </main>
    );
  }

  const session = $session.get();
  const userId = session?.userId ?? AUTH_BYPASS_USER_ID;
  const teams = useStore($teams);

  // Build a flat list of all members from all teams for quick-select
  const allMembers = useMemo(() => {
    const seen = new Set<string>();
    const out: { id: string; label: string; teamName: string }[] = [];
    for (const team of teams) {
      for (const m of team.members) {
        if (!seen.has(m.user_id)) {
          seen.add(m.user_id);
          out.push({
            id: m.user_id,
            label: m.github_handle ? `@${m.github_handle} (${m.user_id})` : m.user_id,
            teamName: team.name,
          });
        }
      }
    }
    return out;
  }, [teams]);

  const [loading, setLoading] = useState(false);
  const [memberA, setMemberA] = useState(userId);
  const [memberB, setMemberB] = useState("");
  const [dataMode, setDataMode] = useState<"full" | "incomplete">("full");
  const [data, setData] = useState<CompatibilityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setError(null);
    setLoading(true);
    try {
      const result = await api.compatibility(memberA.trim() || "alice", memberB.trim() || "bob", dataMode);
      setData(result);
    } catch {
      setError("Compatibility run failed. Please retry.");
    } finally {
      setLoading(false);
    }
  };

  const scoreTone = useMemo(() => {
    const level = data?.level;
    if (level === "excellent") return "text-accent-neon bg-accent-neon/10 border-accent-neon/30";
    if (level === "good") return "text-accent-info bg-accent-info/10 border-accent-info/30";
    if (level === "fair") return "text-yellow-400 bg-yellow-400/10 border-yellow-400/30";
    return "text-red-400 bg-red-400/10 border-red-400/30";
  }, [data?.level]);

  return (
    <main className="relative z-10 w-full max-w-[1200px] mx-auto px-4 md:px-8 pt-10 pb-20 flex flex-col min-h-screen">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6">
        <div>
          <span className="text-primary font-mono text-xs uppercase tracking-widest mb-2 block">Compatibility Engine</span>
          <h1 className="text-4xl md:text-5xl font-bold font-display text-white mb-2">
            Pairwise Score Breakdown
          </h1>
          <p className="text-gray-400 max-w-xl">
            Weighted Ashtakoot score across 8 dimensions with weak-signal flags.
          </p>
        </div>
      </div>

      <div className="glass-panel p-6 md:p-8 rounded-none mb-12 border-white/40">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="flex flex-col gap-2">
            <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">Member A</label>
            {allMembers.length > 0 ? (
              <select
                value={memberA}
                onChange={(e) => setMemberA(e.target.value)}
                className="bg-white/5 border border-white/40 rounded-none px-4 py-3 text-white focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all appearance-none"
              >
                {allMembers.map((m) => (
                  <option key={m.id} value={m.id} className="bg-[#121212]">{m.label}</option>
                ))}
              </select>
            ) : (
              <input
                value={memberA}
                onChange={(e) => setMemberA(e.target.value)}
                placeholder="e.g. alice, 1mystic"
                className="bg-white/5 border border-white/40 rounded-none px-4 py-3 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all"
              />
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">Member B</label>
            {allMembers.length > 0 ? (
              <select
                value={memberB}
                onChange={(e) => setMemberB(e.target.value)}
                className="bg-white/5 border border-white/40 rounded-none px-4 py-3 text-white focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all appearance-none"
              >
                <option value="" className="bg-[#121212]">— select member —</option>
                {allMembers.map((m) => (
                  <option key={m.id} value={m.id} className="bg-[#121212]">{m.label}</option>
                ))}
              </select>
            ) : (
              <input
                value={memberB}
                onChange={(e) => setMemberB(e.target.value)}
                placeholder="e.g. bob, dev_user"
                className="bg-white/5 border border-white/40 rounded-none px-4 py-3 text-white placeholder-gray-600 focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all"
              />
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-xs text-gray-500 font-mono uppercase tracking-wider">Data Mode</label>
            <select
              value={dataMode}
              onChange={(e) => setDataMode(e.target.value as "full" | "incomplete")}
              className="bg-white/5 border border-white/40 rounded-none px-4 py-3 text-white focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all appearance-none"
            >
              <option value="full" className="bg-[#121212]">Full Data</option>
              <option value="incomplete" className="bg-[#121212]">Incomplete (Mock)</option>
            </select>
          </div>
          <div className="flex items-end">
            <button 
              className="w-full btn btn-primary justify-center h-[50px] text-sm shadow-[0_0_15px_rgba(204,255,0,0.4)]"
              onClick={run}
              disabled={loading}
            >
              {loading ? "Running..." : "Compute Compatibility"}
              {!loading && <span className="material-symbols-outlined text-sm">magic_button</span>}
            </button>
          </div>
        </div>
        {error && <p className="text-red-400 text-sm mt-4">{error}</p>}
        <p className="text-xs text-gray-600 mt-4">
          Enter user IDs or GitHub handles of any two team members. Use "Full Data" for real assessment scores, or "Incomplete (Mock)" to test with simulated data.
        </p>
      </div>

      {data && (
        <div className="mb-8 glass-panel rounded-none p-5 border border-primary/20 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-white mb-1">Ready to go deeper?</p>
            <p className="text-xs text-gray-400">Run a full multi-agent team analysis or view all pairings in the dashboard.</p>
          </div>
          <div className="flex gap-3 flex-shrink-0">
            <a href="/workspace" className="btn btn-primary text-xs px-4 py-2 flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">schema</span>
              Full Team Analysis
            </a>
            <a href="/dashboard" className="btn btn-secondary text-xs px-4 py-2 flex items-center gap-1">
              <span className="material-symbols-outlined text-sm">dashboard</span>
              Dashboard
            </a>
          </div>
        </div>
      )}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Score Card */}
          <div className="lg:col-span-1 glass-card rounded-none p-8 flex flex-col justify-center items-center text-center relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-[60px] -translate-y-1/2 translate-x-1/2"></div>
            
            <h3 className="text-gray-400 font-display uppercase tracking-widest text-sm mb-6">Aggregate Sync Score</h3>
            
            <div className="relative">
              <svg className="w-48 h-48 transform -rotate-90">
                <circle cx="96" cy="96" r="88" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
                <circle 
                  cx="96" 
                  cy="96" 
                  r="88" 
                  fill="none" 
                  stroke="var(--primary-solid)" 
                  strokeWidth="8" 
                  strokeDasharray="552" 
                  strokeDashoffset={552 - (552 * data.total_score_36) / 36}
                  strokeLinecap="round"
                  className="drop-shadow-[0_0_10px_rgba(204,255,0,0.6)] transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-5xl font-bold font-display text-white">{data.total_score_36}</span>
                <span className="text-gray-500 font-mono text-sm">/ 36</span>
              </div>
            </div>
            
            <div className={`mt-8 px-6 py-2 rounded-full border text-sm font-bold uppercase tracking-widest ${scoreTone}`}>
              {data.label}
            </div>
            
            {data.risk_flags && data.risk_flags.length > 0 && (
              <div className="mt-8 w-full p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-none text-left">
                <p className="text-yellow-400 text-xs font-bold uppercase mb-2 flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">warning</span> Risk Flags
                </p>
                <ul className="text-xs text-gray-400 space-y-1 list-disc pl-4">
                  {data.risk_flags.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Breakdown Dimensions */}
          <div className="lg:col-span-2 glass-panel rounded-none p-8 relative">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold font-display text-white">Dimension Breakdown</h3>
              <span className="text-sm text-gray-500 font-mono">{data.dimension_breakdown?.length ?? 0} Vectors</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
              {(data.dimension_breakdown ?? []).map((item) => {
                const isWeak = data.weak_dimensions.includes(item.dimension);
                const pct = (item.score / item.weight) * 100;

                return (
                  <div key={item.dimension} className="flex flex-col gap-2">
                    <div className="flex justify-between items-end">
                      <span className="text-sm font-medium text-gray-300 capitalize flex items-center gap-2">
                        {item.dimension.replace(/_/g, ' ')}
                        {isWeak && <span className="material-symbols-outlined text-[14px] text-red-400" title="Weak Signal">error</span>}
                      </span>
                      <span className="text-xs font-mono text-gray-500">
                        <span className="text-white font-bold">{item.score}</span> / {item.weight}
                      </span>
                    </div>
                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${isWeak ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'bg-primary shadow-[0_0_8px_rgba(204,255,0,0.4)]'}`}
                        style={{ width: `${pct}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
            
            {data.weak_dimensions.length > 0 && (
              <div className="mt-10 pt-6 border-t border-white/40">
                <h4 className="text-sm font-bold text-red-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]">gpp_bad</span> Critical Vulnerabilities
                </h4>
                <div className="flex flex-wrap gap-2">
                  {data.weak_dimensions.map((dim) => (
                    <span key={dim} className="px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-mono capitalize">
                      {dim.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}
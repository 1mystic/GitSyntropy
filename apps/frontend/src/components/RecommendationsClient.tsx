import { useState } from "react";
import { useStore } from "@nanostores/react";
import { AnimatePresence, motion } from "framer-motion";
import { fadeInUp, stagger } from "@/lib/motion";

import { type TeammateRecommendation, api } from "@/lib/api";
import { $session, $activeTeam } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID } from "@/lib/featureFlags";

/**
 * Reciprocal teammate recommendations for the active team.
 *
 * Ranks candidates by the harmonic mean of two directional fit scores (how well the candidate
 * satisfies the seeker AND vice-versa) so one-sided matches are penalised. The seeker is the
 * current user; the candidate pool is everyone who has completed the adaptive assessment, minus
 * existing team members.
 */
function initials(name: string): string {
  const parts = name.replace(/^@/, "").replace(/[_-]+/g, " ").trim().split(/\s+/);
  return (parts[0]?.[0] ?? "?").toUpperCase() + (parts[1]?.[0] ?? "").toUpperCase();
}

export function RecommendationsClient({ teamId: teamIdProp }: { teamId?: string }) {
  const session = useStore($session);
  const activeTeam = useStore($activeTeam);
  const seekerId = session?.userId ?? AUTH_BYPASS_USER_ID;
  const teamId = teamIdProp ?? activeTeam?.id ?? "";

  const [recs, setRecs] = useState<TeammateRecommendation[]>([]);
  const [poolSize, setPoolSize] = useState<number | null>(null);
  const [coldStart, setColdStart] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadRecommendations() {
    if (!session?.token) {
      setError("Sign in to get recommendations.");
      return;
    }
    if (!teamId) {
      setError("Select or create a team first — recommendations exclude its existing members.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.teamRecommendations(teamId, seekerId, session.token, 5);
      setRecs(res.recommendations);
      setPoolSize(res.candidate_pool_size);
      setColdStart(res.cold_start);
      setHasRun(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recommendations.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.section
      variants={fadeInUp}
      initial="hidden"
      animate="visible"
      className="glass-panel rounded-none p-6 md:p-8 border border-white/40 mt-12"
    >
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div>
          <span className="text-primary font-mono text-xs uppercase tracking-widest mb-2 block">
            Reciprocal Recommender
          </span>
          <h3 className="text-2xl font-semibold text-white">Recommended teammates</h3>
          <p className="text-sm text-gray-400 mt-1 max-w-xl">
            Scored both ways — a match only ranks high when it works for{" "}
            <span className="text-primary-text">both</span> people.
          </p>
        </div>
        <button
          onClick={() => void loadRecommendations()}
          disabled={loading}
          className="btn btn-primary text-sm px-6 py-3 shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Matching…" : "Find matches"}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-none text-red-400 text-sm">
          {error}
        </div>
      )}

      {poolSize !== null && (
        <p className="text-xs font-mono text-gray-500 mb-5">
          Ranked against {poolSize} assessed {poolSize === 1 ? "user" : "users"}
          {coldStart && " · content-based (cold-start safe)"}
        </p>
      )}

      <AnimatePresence mode="wait">
        {recs.length > 0 ? (
          <motion.ol
            key="list"
            variants={stagger}
            initial="hidden"
            animate="visible"
            className="flex flex-col gap-3"
          >
            {recs.map((r, i) => {
              const name = r.github_name ?? (r.github_handle ? `@${r.github_handle}` : r.user_id);
              const pct = Math.round(r.score * 100);
              return (
                <motion.li
                  key={r.user_id}
                  variants={fadeInUp}
                  className="glass-card rounded-none p-4 flex items-center gap-4 border border-white/10 hover:border-primary/40 transition-colors"
                >
                  <span className="text-primary font-mono text-sm w-6 shrink-0">#{i + 1}</span>
                  <div className="w-10 h-10 shrink-0 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary font-mono text-sm">
                    {initials(name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                      <span className="text-white font-medium truncate">{name}</span>
                      <span className="text-primary font-mono text-sm shrink-0">{pct}%</span>
                    </div>
                    <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-primary rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.6, delay: i * 0.05 }}
                      />
                    </div>
                    <div className="flex gap-4 mt-1.5 text-[11px] font-mono text-gray-500">
                      <span title="How well the candidate satisfies you">
                        to you {Math.round(r.directional_to_seeker * 100)}%
                      </span>
                      <span title="How well you satisfy the candidate">
                        to them {Math.round(r.directional_from_seeker * 100)}%
                      </span>
                    </div>
                  </div>
                </motion.li>
              );
            })}
          </motion.ol>
        ) : hasRun && !loading ? (
          <motion.p key="empty" variants={fadeInUp} initial="hidden" animate="visible"
            className="text-sm text-gray-500 py-6 text-center">
            No candidates yet — add more assessed users to the pool, or seed demo data locally.
          </motion.p>
        ) : null}
      </AnimatePresence>
    </motion.section>
  );
}

export default RecommendationsClient;

import { useState } from "react";
import { useStore } from "@nanostores/react";
import { AnimatePresence, motion } from "framer-motion";
import { fadeInUp, stagger } from "@/lib/motion";

import { type TeammateRecommendation, api } from "@/lib/api";
import { $session } from "@/lib/stores";
import { AUTH_BYPASS_USER_ID } from "@/lib/featureFlags";

/**
 * Reciprocal teammate recommendations for a team.
 *
 * Ranks candidates by the harmonic mean of two directional fit scores (how well the candidate
 * satisfies the seeker AND vice-versa) so one-sided matches are penalised. The seeker is the
 * current user; the candidate pool is everyone who has completed the adaptive assessment, minus
 * existing team members.
 */
export function RecommendationsClient({ teamId }: { teamId: string }) {
  const session = useStore($session);
  const seekerId = session?.userId ?? AUTH_BYPASS_USER_ID;

  const [recs, setRecs] = useState<TeammateRecommendation[]>([]);
  const [poolSize, setPoolSize] = useState<number | null>(null);
  const [coldStart, setColdStart] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadRecommendations() {
    if (!session?.token) {
      setError("Sign in to get recommendations.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.teamRecommendations(teamId, seekerId, session.token, 5);
      setRecs(res.recommendations);
      setPoolSize(res.candidate_pool_size);
      setColdStart(res.cold_start);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recommendations.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rec-panel">
      <header className="rec-panel__head">
        <div>
          <h3>Recommended teammates</h3>
          <p className="rec-panel__sub">
            Reciprocal matches — scored both ways, so a recommendation is only strong when it works
            for both people.
          </p>
        </div>
        <button className="btn btn--primary" onClick={loadRecommendations} disabled={loading}>
          {loading ? "Matching…" : "Find matches"}
        </button>
      </header>

      {error && <p className="rec-panel__error">{error}</p>}

      {poolSize !== null && (
        <p className="rec-panel__meta">
          Ranked against {poolSize} assessed {poolSize === 1 ? "user" : "users"}
          {coldStart && " · content-based (cold-start safe)"}
        </p>
      )}

      <AnimatePresence>
        {recs.length > 0 && (
          <motion.ol className="rec-list" variants={stagger} initial="hidden" animate="show">
            {recs.map((r, i) => (
              <motion.li key={r.user_id} className="rec-list__item" variants={fadeInUp}>
                <span className="rec-list__rank">#{i + 1}</span>
                <span className="rec-list__who">
                  {r.github_name ?? (r.github_handle ? `@${r.github_handle}` : r.user_id)}
                </span>
                <span className="rec-list__score" title="Reciprocal match score">
                  {(r.score * 100).toFixed(0)}%
                </span>
                <span className="rec-list__dir" title="Directional fit (to / from seeker)">
                  {(r.directional_to_seeker * 100).toFixed(0)}↔{(r.directional_from_seeker * 100).toFixed(0)}
                </span>
              </motion.li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
    </section>
  );
}

export default RecommendationsClient;

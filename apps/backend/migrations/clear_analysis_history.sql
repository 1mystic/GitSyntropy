-- MAINTENANCE (manual, destructive) — clear all analysis history so every team can re-run fresh.
--
-- Run this ONCE in the Supabase SQL editor when you want to wipe:
--   * team_scores  — every saved compatibility report / Recent Report / Insights entry
--   * agent_runs   — every orchestrator run + its persisted trace (incl. the old failed
--                    "name 'asyncio' is not defined" runs shown in the Agent Trace View)
--
-- It does NOT touch users, teams, memberships, psychometric profiles, or GitHub profiles —
-- only the analysis *outputs*. After running it, every team shows a clean slate and can
-- re-run analysis (which now works once the asyncio fix is deployed).
--
-- ⚠️ Irreversible. There is no undo. Make a Supabase backup/branch first if unsure.

BEGIN;

DELETE FROM team_scores;
DELETE FROM agent_runs;

COMMIT;

-- Optional sanity check (run separately):
--   SELECT (SELECT count(*) FROM team_scores) AS reports, (SELECT count(*) FROM agent_runs) AS runs;
-- Both should be 0.

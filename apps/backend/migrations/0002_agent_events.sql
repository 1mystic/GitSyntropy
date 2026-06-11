-- Migration 0002: add agent_events to agent_runs (WS-4 agent trace).
--
-- The orchestrator now persists per-node trace events (node name + duration) into
-- agent_runs.agent_events so the admin trace view can replay a run. Fresh databases
-- already get this column from 001_initial_schema.sql, but an EXISTING production
-- table created before this column will not — `CREATE TABLE IF NOT EXISTS` does not
-- alter existing tables. Run this once on the live Supabase database.
--
-- Idempotent: safe to run repeatedly.

ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS agent_events JSONB;

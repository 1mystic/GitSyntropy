-- GitSyntropy Initial Schema — run this in Supabase SQL Editor
-- Compatible with SQLAlchemy create_all() (tables created automatically on startup)
-- Run manually in Supabase for production or let SQLAlchemy create them locally.

-- GitHub behavioral profiles (one per sync job; user_id not yet UUID)
CREATE TABLE IF NOT EXISTS github_profiles (
    id                      VARCHAR(36) PRIMARY KEY,
    user_id                 VARCHAR(255) NOT NULL,
    github_handle           VARCHAR(255) NOT NULL,
    chronotype              VARCHAR(20),
    activity_rhythm_score   FLOAT,
    collaboration_index     FLOAT,
    total_commits           INTEGER,
    prs_last_30_days        INTEGER,
    commits_last_30_days    INTEGER,
    sync_status             VARCHAR(20) DEFAULT 'queued',
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    raw_data                JSONB
);

CREATE INDEX IF NOT EXISTS idx_github_profiles_user_id ON github_profiles(user_id);

-- Psychometric profiles (one per user, upserted on assessment submit)
CREATE TABLE IF NOT EXISTS psychometric_profiles (
    id                   VARCHAR(36) PRIMARY KEY,
    user_id              VARCHAR(255) UNIQUE NOT NULL,
    answers              JSONB NOT NULL,
    scores               JSONB NOT NULL,
    answered_count       INTEGER DEFAULT 0,
    total_questions      INTEGER DEFAULT 8,
    missing_question_ids JSONB DEFAULT '[]',
    complete             BOOLEAN DEFAULT FALSE,
    submitted_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_psychometric_profiles_user_id ON psychometric_profiles(user_id);

-- Orchestrator agent run audit log
CREATE TABLE IF NOT EXISTS agent_runs (
    id                  VARCHAR(36) PRIMARY KEY,
    team_id             VARCHAR(255) NOT NULL,
    user_id             VARCHAR(255) NOT NULL,
    include_candidates  BOOLEAN DEFAULT FALSE,
    status              VARCHAR(20) DEFAULT 'started',
    error               TEXT,
    agent_events        JSONB,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

-- Teams
CREATE TABLE IF NOT EXISTS teams (
    id           VARCHAR(36) PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    description  TEXT,
    created_by   VARCHAR(255),
    invite_token VARCHAR(64) UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Team membership
CREATE TABLE IF NOT EXISTS team_members (
    team_id       VARCHAR(36) NOT NULL,
    user_id       VARCHAR(255) NOT NULL,
    role          VARCHAR(100),
    github_handle VARCHAR(255),
    joined_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(user_id);

-- Team scores (versioned per run)
CREATE TABLE IF NOT EXISTS team_scores (
    id                 VARCHAR(36) PRIMARY KEY,
    team_id            VARCHAR(255) NOT NULL,
    agent_run_id       VARCHAR(36),
    resilience_score   FLOAT NOT NULL,
    compatibility_pct  FLOAT NOT NULL,
    level              VARCHAR(20),
    confidence         FLOAT,
    dimension_scores   JSONB NOT NULL,
    weak_dimensions    JSONB,
    strong_dimensions  JSONB,
    risk_flags         JSONB,
    narrative_report   TEXT,
    pairwise_scores    JSONB,
    calculated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_team_scores_team_id ON team_scores(team_id);
CREATE INDEX IF NOT EXISTS idx_team_scores_calculated_at ON team_scores(calculated_at DESC);

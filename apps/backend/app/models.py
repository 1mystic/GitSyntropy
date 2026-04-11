"""SQLAlchemy 2.0 ORM models — mirrors the Supabase schema in 01_GitSyntropy_Architecture.md.

User IDs are VARCHAR in this phase (Feature 1). Feature 2 migrates to UUID once real
GitHub OAuth produces stable UUID-keyed users.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class GithubProfile(Base):
    """One row per (user_id, github_handle) — upserted on every sync."""

    __tablename__ = "github_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4 as string
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    github_handle: Mapped[str] = mapped_column(String(255), nullable=False)

    # Chronotype
    chronotype: Mapped[str | None] = mapped_column(String(20))

    # Work rhythm metrics
    activity_rhythm_score: Mapped[float | None] = mapped_column(Float)
    collaboration_index: Mapped[float | None] = mapped_column(Float)
    total_commits: Mapped[int | None] = mapped_column(Integer)
    prs_last_30_days: Mapped[int | None] = mapped_column(Integer)
    commits_last_30_days: Mapped[int | None] = mapped_column(Integer)

    # Sync lifecycle
    sync_status: Mapped[str] = mapped_column(String(20), default="queued")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Raw GitHub API response for future re-processing
    raw_data: Mapped[dict | None] = mapped_column(JSONB)


class PsychometricProfile(Base):
    """One row per user — upserted on assessment submit."""

    __tablename__ = "psychometric_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4 as string
    user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Raw answers keyed by question ID: {"q1": 3, "q2": 5, ...}
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Computed dimension scores: {"nadi_chronotype_sync": 6.4, ...}
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)

    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=8)
    missing_question_ids: Mapped[list] = mapped_column(JSONB, default=list)
    complete: Mapped[bool] = mapped_column(Boolean, default=False)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentRun(Base):
    """Tracks each orchestrator run — persists run_id so WebSocket can reconnect."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid4 as string (run_id)
    team_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    include_candidates: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="started")
    error: Mapped[str | None] = mapped_column(Text)
    agent_events: Mapped[list | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Team(Base):
    """Teams — created and managed by users."""

    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(255))
    invite_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeamMember(Base):
    """Many-to-many: teams ↔ users."""

    __tablename__ = "team_members"

    team_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    role: Mapped[str | None] = mapped_column(String(100))
    github_handle: Mapped[str | None] = mapped_column(String(255))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    """One row per authenticated user — upserted on every OAuth login."""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    github_handle: Mapped[str | None] = mapped_column(String(255), index=True)
    github_name: Mapped[str | None] = mapped_column(String(255))
    github_email: Mapped[str | None] = mapped_column(String(255))
    github_avatar_url: Mapped[str | None] = mapped_column(Text)
    # User-editable display name (overrides github_name in UI)
    display_name: Mapped[str | None] = mapped_column(String(80))
    # Encrypted in production via GS_JWT_SECRET; stored for re-syncing
    github_access_token: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TeamScore(Base):
    """Versioned team Ashtakoot scores — one row per run."""

    __tablename__ = "team_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    agent_run_id: Mapped[str | None] = mapped_column(String(36))

    resilience_score: Mapped[float] = mapped_column(Float, nullable=False)
    compatibility_pct: Mapped[float] = mapped_column(Float, nullable=False)
    level: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)

    dimension_scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    weak_dimensions: Mapped[list | None] = mapped_column(JSONB)
    strong_dimensions: Mapped[list | None] = mapped_column(JSONB)
    risk_flags: Mapped[list | None] = mapped_column(JSONB)

    narrative_report: Mapped[str | None] = mapped_column(Text)
    pairwise_scores: Mapped[dict | None] = mapped_column(JSONB)

    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

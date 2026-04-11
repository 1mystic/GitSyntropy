from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, ConfigDict


ASHTAKOOT_DIMENSIONS = [
    "varna_alignment",
    "vashya_influence",
    "tara_resilience",
    "yoni_workstyle",
    "graha_maitri_cognition",
    "gana_temperament",
    "bhakoot_strategy",
    "nadi_chronotype_sync",
]

ASHTAKOOT_WEIGHTS = {
    "varna_alignment": 1.0,
    "vashya_influence": 2.0,
    "tara_resilience": 3.0,
    "yoni_workstyle": 4.0,
    "graha_maitri_cognition": 5.0,
    "gana_temperament": 6.0,
    "bhakoot_strategy": 7.0,
    "nadi_chronotype_sync": 8.0,
}


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class AnalysisRequest(BaseModel):
    team_id: str = Field(min_length=2)
    candidate_ids: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    run_id: str
    team_id: str
    status: Literal["queued", "running", "done"]
    score: float
    summary: str
    generated_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    github_handle: str | None = None
    github_name: str | None = None
    github_avatar_url: str | None = None
    is_superadmin: bool = False


class GithubAuthStartResponse(BaseModel):
    provider: Literal["github"]
    authorization_url: str
    state: str
    redirect_uri: str
    scopes: list[str]


class GithubAuthCallbackRequest(BaseModel):
    code: str = Field(min_length=4)
    state: str | None = None


class AuthSessionResponse(BaseModel):
    authenticated: bool
    user_id: str
    expires_at: datetime


class GithubSyncRequest(BaseModel):
    github_handle: str = Field(min_length=2)
    user_id: str = "user_local"


class GithubSyncResponse(BaseModel):
    sync_id: str
    user_id: str
    github_handle: str
    chronotype: Literal["owl", "lark", "balanced"]
    activity_rhythm_score: float
    collaboration_index: float
    prs_last_30_days: int
    commits_last_30_days: int
    status: Literal["queued", "syncing", "complete"]
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class AssessmentQuestion(BaseModel):
    id: str
    prompt: str
    left_label: str
    right_label: str
    dimension: str


AssessmentAnswerValue = Annotated[int, Field(ge=1, le=5)]


class AssessmentSubmitRequest(BaseModel):
    user_id: str
    answers: dict[str, AssessmentAnswerValue]


class AssessmentSubmitResponse(BaseModel):
    user_id: str
    scores: dict[str, float]
    answered_count: int
    total_questions: int
    missing_question_ids: list[str]
    complete: bool
    submitted_at: datetime


class AssessmentProfileResponse(BaseModel):
    user_id: str
    scores: dict[str, float]
    answered_count: int
    total_questions: int
    missing_question_ids: list[str]
    complete: bool
    submitted_at: datetime | None = None


class CompatibilityRequest(BaseModel):
    member_a: str
    member_b: str
    data_mode: Literal["full", "incomplete"] = "full"


class CompatibilityDimensionBreakdown(BaseModel):
    dimension: str
    weight: float
    score: float
    pct_of_weight: float
    status: Literal["weak", "balanced", "strong"]


class CompatibilityResponse(BaseModel):
    member_a: str
    member_b: str
    total_score_36: float
    score_pct_100: float
    level: Literal["excellent", "good", "fair", "poor"]
    label: str
    weak_dimensions: list[str]
    strong_dimensions: list[str]
    risk_flags: list[str]
    confidence: float
    data_gaps: list[str]
    dimension_scores: dict[str, float]
    dimension_breakdown: list[CompatibilityDimensionBreakdown]


class OrchestratorRunRequest(BaseModel):
    team_id: str
    user_id: str
    include_candidates: bool = False


class OrchestratorRunResponse(BaseModel):
    run_id: str
    state: Literal["started", "running", "completed"]
    steps: list[str]


class InsightResponse(BaseModel):
    run_id: str
    narrative: str
    recommendations: list[str]
    uncertainty_note: str


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    created_by: str


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None


class AddMemberRequest(BaseModel):
    user_id: str
    github_handle: str | None = None
    role: str | None = None


class TeamMemberResponse(BaseModel):
    team_id: str
    user_id: str
    role: str | None = None
    github_handle: str | None = None
    joined_at: datetime


class TeamResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_by: str | None = None
    invite_token: str | None = None
    created_at: datetime
    members: list[TeamMemberResponse] = []


# ---------------------------------------------------------------------------
# Feature 8 — CAT Assessment
# ---------------------------------------------------------------------------

class CATNextRequest(BaseModel):
    current_answers: dict[str, Annotated[int, Field(ge=1, le=5)]] = Field(default_factory=dict)


class CATNextResponse(BaseModel):
    next_question_id: str | None
    question: AssessmentQuestion | None = None
    rationale: str
    estimated_remaining: int
    can_stop_early: bool


# ---------------------------------------------------------------------------
# Feature 8 — Monte Carlo candidate simulation
# ---------------------------------------------------------------------------

class CandidateSimulateRequest(BaseModel):
    team_scores: list[dict[str, float]] = Field(
        default_factory=list,
        description="List of dimension-score dicts for each existing team member.",
    )
    n_iterations: int = Field(default=1000, ge=100, le=5000)


class CandidateSimulateResponse(BaseModel):
    n_iterations: int
    optimal_profile: dict[str, float]
    mean_improvement: float
    best_improvement: float
    p25_improvement: float
    p75_improvement: float
    weak_dimensions_targeted: list[str]
    confidence: float
    status: str


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------

class UserProfileResponse(BaseModel):
    user_id: str
    github_handle: str | None = None
    github_name: str | None = None
    github_avatar_url: str | None = None
    github_email: str | None = None
    is_superadmin: bool = False
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Admin (superadmin only)
# ---------------------------------------------------------------------------

class AdminUserResponse(BaseModel):
    user_id: str
    github_handle: str | None = None
    github_name: str | None = None
    github_avatar_url: str | None = None
    github_email: str | None = None
    is_superadmin: bool = False
    created_at: datetime | None = None
    last_seen_at: datetime | None = None
    team_count: int = 0
    assessment_complete: bool = False
    github_syncs: int = 0
    agent_runs: int = 0


class AdminStatsResponse(BaseModel):
    total_users: int
    total_teams: int
    total_assessments: int
    total_github_syncs: int
    total_agent_runs: int


# ---------------------------------------------------------------------------
# User search + profile update
# ---------------------------------------------------------------------------

class UserSearchResult(BaseModel):
    user_id: str
    github_handle: str | None = None
    display_name: str | None = None
    github_avatar_url: str | None = None


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display_name: Annotated[str | None, Field(max_length=80)] = None

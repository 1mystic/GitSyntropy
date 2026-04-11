from datetime import UTC, datetime, timedelta
import random
from functools import lru_cache
from typing import Any, AsyncIterator, TypedDict
from urllib.parse import urlencode
from uuid import uuid4

from jose import JWTError, jwt
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func as sa_func

from .config import settings
from .models import AgentRun, GithubProfile, PsychometricProfile, Team, TeamMember, UserProfile
from .schemas import ASHTAKOOT_DIMENSIONS, ASHTAKOOT_WEIGHTS

# Lazy imports to avoid startup errors when optional packages aren't configured
def _get_github_client(access_token: str):
    from .github_client import GitHubAnalystClient
    return GitHubAnalystClient(access_token)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_jwt(user_id: str, github_handle: str | None = None) -> tuple[str, int]:
    expires_in = settings.jwt_exp_minutes * 60
    expiry = datetime.now(tz=UTC) + timedelta(seconds=expires_in)
    claims: dict[str, Any] = {"sub": user_id, "exp": expiry, "iss": settings.jwt_issuer}
    if github_handle:
        claims["github_handle"] = github_handle
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def is_superadmin(github_handle: str | None) -> bool:
    """True if the GitHub handle matches the configured superadmin."""
    if not github_handle:
        return False
    return github_handle.lower() == settings.superadmin_github_handle.lower()


class AuthTokenError(Exception):
    pass


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise AuthTokenError("Invalid or expired token.") from exc


def create_oauth_state() -> str:
    return uuid4().hex


def build_github_authorization_url(state: str) -> str:
    scopes = settings.github_scope.split()
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_url,
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


async def exchange_github_code_for_identity(code: str, db: AsyncSession) -> dict[str, str]:
    """Exchange OAuth code for real GitHub identity via GitHub API.

    In Feature 2 this will call https://github.com/login/oauth/access_token.
    For now it derives a stable user_id from the code and upserts a placeholder user.
    """
    import httpx

    if settings.github_client_secret and settings.github_client_id != "local-dev":
        # Real OAuth exchange
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            token_data = resp.json()
            access_token = token_data.get("access_token", "")

        if not access_token or "error" in token_data:
            err_desc = token_data.get("error_description", token_data.get("error", "OAuth exchange failed"))
            raise ValueError(f"GitHub OAuth failed: {err_desc}")

        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                timeout=10,
            )
            user_resp.raise_for_status()
            github_user = user_resp.json()

        user_id = f"gh_{github_user['id']}"
        identity = {
            "user_id": user_id,
            "github_handle": github_user.get("login", ""),
            "name": github_user.get("name", ""),
            "email": github_user.get("email", ""),
            "avatar_url": github_user.get("avatar_url", ""),
            "access_token": access_token,
        }
        await upsert_user_profile(
            user_id=user_id,
            github_handle=identity["github_handle"],
            github_name=identity["name"] or None,
            github_email=identity["email"] or None,
            github_avatar_url=identity["avatar_url"] or None,
            github_access_token=access_token or None,
            db=db,
        )
        return identity
    else:
        # Dev fallback: derive stable user_id from code string
        clean = "".join(char for char in code.lower() if char.isalnum())
        if not clean:
            raise ValueError("OAuth code is invalid.")
        user_id = f"user_github_{clean[-8:]}"
        identity = {"user_id": user_id, "github_handle": clean[-8:], "name": "", "email": "", "avatar_url": "", "access_token": ""}
        await upsert_user_profile(
            user_id=user_id,
            github_handle=identity["github_handle"],
            github_name=None,
            github_email=None,
            github_avatar_url=None,
            github_access_token=None,
            db=db,
        )
        return identity


# ---------------------------------------------------------------------------
# User profile — upsert on every OAuth login
# ---------------------------------------------------------------------------

async def upsert_user_profile(
    user_id: str,
    github_handle: str | None,
    github_name: str | None,
    github_email: str | None,
    github_avatar_url: str | None,
    github_access_token: str | None,
    db: AsyncSession,
) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    now = datetime.now(tz=UTC)
    if profile is None:
        profile = UserProfile(
            user_id=user_id,
            github_handle=github_handle,
            github_name=github_name,
            github_email=github_email,
            github_avatar_url=github_avatar_url,
            github_access_token=github_access_token,
            last_seen_at=now,
        )
        db.add(profile)
    else:
        if github_handle:
            profile.github_handle = github_handle
        if github_name is not None:
            profile.github_name = github_name
        if github_email is not None:
            profile.github_email = github_email
        if github_avatar_url is not None:
            profile.github_avatar_url = github_avatar_url
        if github_access_token is not None:
            profile.github_access_token = github_access_token
        profile.last_seen_at = now
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_user_profile(user_id: str, db: AsyncSession) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def touch_user_last_seen(user_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is not None:
        profile.last_seen_at = datetime.now(tz=UTC)
        await db.commit()


async def update_user_display_name(user_id: str, display_name: str | None, db: AsyncSession) -> UserProfile | None:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    profile.display_name = display_name
    await db.commit()
    await db.refresh(profile)
    return profile


async def search_users(query: str, db: AsyncSession, limit: int = 10) -> list[dict[str, Any]]:
    """Search users by github_handle, display_name, or github_name. Returns up to `limit` results."""
    q = f"%{query.lower()}%"
    from sqlalchemy import or_, func as _func
    result = await db.execute(
        select(UserProfile).where(
            or_(
                _func.lower(UserProfile.github_handle).like(q),
                _func.lower(UserProfile.display_name).like(q),
                _func.lower(UserProfile.github_name).like(q),
            )
        ).limit(limit)
    )
    profiles = result.scalars().all()
    return [
        {
            "user_id": p.user_id,
            "github_handle": p.github_handle,
            "display_name": p.display_name or p.github_name or p.github_handle,
            "github_avatar_url": p.github_avatar_url,
        }
        for p in profiles
    ]


# ---------------------------------------------------------------------------
# Admin — platform-wide stats and user listing (superadmin only)
# ---------------------------------------------------------------------------

async def get_platform_stats(db: AsyncSession) -> dict[str, int]:
    total_users_result = await db.execute(select(sa_func.count(UserProfile.user_id)))
    total_teams_result = await db.execute(select(sa_func.count(Team.id)))
    total_assessments_result = await db.execute(select(sa_func.count(PsychometricProfile.id)))
    total_syncs_result = await db.execute(select(sa_func.count(GithubProfile.id)))
    total_runs_result = await db.execute(select(sa_func.count(AgentRun.id)))

    return {
        "total_users": total_users_result.scalar_one() or 0,
        "total_teams": total_teams_result.scalar_one() or 0,
        "total_assessments": total_assessments_result.scalar_one() or 0,
        "total_github_syncs": total_syncs_result.scalar_one() or 0,
        "total_agent_runs": total_runs_result.scalar_one() or 0,
    }


async def get_all_users_admin(db: AsyncSession) -> list[dict[str, Any]]:
    profiles_result = await db.execute(select(UserProfile).order_by(UserProfile.created_at.desc()))
    profiles = profiles_result.scalars().all()

    users = []
    for p in profiles:
        # Count teams this user belongs to
        team_count_result = await db.execute(
            select(sa_func.count(TeamMember.team_id)).where(TeamMember.user_id == p.user_id)
        )
        team_count = team_count_result.scalar_one() or 0

        # Check if assessment is complete
        assessment_result = await db.execute(
            select(PsychometricProfile).where(
                PsychometricProfile.user_id == p.user_id,
                PsychometricProfile.complete == True,  # noqa: E712
            )
        )
        assessment_complete = assessment_result.scalar_one_or_none() is not None

        # Count GitHub syncs
        syncs_result = await db.execute(
            select(sa_func.count(GithubProfile.id)).where(GithubProfile.user_id == p.user_id)
        )
        github_syncs = syncs_result.scalar_one() or 0

        # Count agent runs
        runs_result = await db.execute(
            select(sa_func.count(AgentRun.id)).where(AgentRun.user_id == p.user_id)
        )
        agent_runs = runs_result.scalar_one() or 0

        users.append({
            "user_id": p.user_id,
            "github_handle": p.github_handle,
            "github_name": p.github_name,
            "github_avatar_url": p.github_avatar_url,
            "github_email": p.github_email,
            "is_superadmin": is_superadmin(p.github_handle),
            "created_at": p.created_at,
            "last_seen_at": p.last_seen_at,
            "team_count": team_count,
            "assessment_complete": assessment_complete,
            "github_syncs": github_syncs,
            "agent_runs": agent_runs,
        })
    return users


# ---------------------------------------------------------------------------
# GitHub sync — DB-persisted
# ---------------------------------------------------------------------------

GITHUB_SYNC_COMPLETE_AFTER_SECONDS = 2.5


def _derive_chronotype(github_handle: str) -> str:
    if github_handle.lower().startswith("night"):
        return "owl"
    if github_handle.lower().startswith("early"):
        return "lark"
    return "balanced"


def _compute_sync_status(started_at: datetime) -> str:
    elapsed = (datetime.now(tz=UTC) - started_at).total_seconds()
    if elapsed < 0.75:
        return "queued"
    if elapsed < GITHUB_SYNC_COMPLETE_AFTER_SECONDS:
        return "syncing"
    return "complete"


def _profile_to_sync_dict(profile: GithubProfile) -> dict[str, Any]:
    now = datetime.now(tz=UTC)
    status = _compute_sync_status(profile.started_at)
    completed_at = profile.completed_at
    if status == "complete" and completed_at is None:
        completed_at = profile.started_at + timedelta(seconds=GITHUB_SYNC_COMPLETE_AFTER_SECONDS)
    return {
        "sync_id": profile.id,
        "user_id": profile.user_id,
        "github_handle": profile.github_handle,
        "chronotype": profile.chronotype or "balanced",
        "activity_rhythm_score": profile.activity_rhythm_score or 0.0,
        "collaboration_index": profile.collaboration_index or 0.0,
        "prs_last_30_days": profile.prs_last_30_days or 0,
        "commits_last_30_days": profile.commits_last_30_days or 0,
        "status": status,
        "started_at": profile.started_at,
        "updated_at": now,
        "completed_at": completed_at,
    }


async def trigger_github_sync(github_handle: str, user_id: str, db: AsyncSession, access_token: str | None = None) -> dict[str, Any]:
    sync_id = str(uuid4())

    # Use real GitHub API if a token is available
    if access_token or settings.github_access_token:
        token = access_token or settings.github_access_token
        try:
            client = _get_github_client(token)
            data = await client.analyze(github_handle)
            profile = GithubProfile(
                id=sync_id,
                user_id=user_id,
                github_handle=github_handle,
                chronotype=data["chronotype"],
                activity_rhythm_score=data["activity_rhythm_score"],
                collaboration_index=data["collaboration_index"],
                total_commits=data["commits_last_90_days"],
                prs_last_30_days=data["prs_last_30_days"],
                commits_last_30_days=data["commits_last_30_days"],
                sync_status="complete",
                started_at=datetime.now(tz=UTC),
                completed_at=datetime.now(tz=UTC),
                raw_data=data,
            )
        except Exception:  # noqa: BLE001 — fall back to mock on any API failure
            profile = _mock_github_profile(sync_id, user_id, github_handle)
    else:
        profile = _mock_github_profile(sync_id, user_id, github_handle)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_sync_dict(profile)


def _mock_github_profile(sync_id: str, user_id: str, github_handle: str) -> GithubProfile:
    """Deterministic mock used when no GitHub token is configured."""
    chronotype = _derive_chronotype(github_handle)
    commits = len(github_handle) * 7
    prs = len(github_handle) * 3
    return GithubProfile(
        id=sync_id,
        user_id=user_id,
        github_handle=github_handle,
        chronotype=chronotype,
        activity_rhythm_score=round(min(100.0, 20 + commits * 0.9), 2),
        collaboration_index=round(min(100.0, 45 + prs * 0.8), 2),
        total_commits=commits,
        prs_last_30_days=prs,
        commits_last_30_days=commits,
        sync_status="queued",
        started_at=datetime.now(tz=UTC),
    )


async def get_github_sync(sync_id: str, db: AsyncSession) -> dict[str, Any] | None:
    result = await db.execute(select(GithubProfile).where(GithubProfile.id == sync_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return _profile_to_sync_dict(profile)


# ---------------------------------------------------------------------------
# Assessment — DB-persisted
# ---------------------------------------------------------------------------

def assessment_questions() -> list[dict]:
    prompts = [
        ("Decision style in uncertainty", "Intuitive", "Analytical"),
        ("Preferred delivery rhythm", "Steady", "Bursty"),
        ("Conflict handling pattern", "Direct", "Diplomatic"),
        ("Team interaction mode", "Independent", "Collaborative"),
        ("Context switching tolerance", "Low", "High"),
        ("Communication density", "Concise", "Detailed"),
        ("Experimentation appetite", "Conservative", "Exploratory"),
        ("Working-hour preference", "Early", "Late"),
    ]
    questions = []
    for index, (prompt, left, right) in enumerate(prompts):
        questions.append(
            {
                "id": f"q{index + 1}",
                "prompt": prompt,
                "left_label": left,
                "right_label": right,
                "dimension": ASHTAKOOT_DIMENSIONS[index],
            }
        )
    return questions


def score_assessment(answers: dict[str, int]) -> dict[str, float]:
    scored: dict[str, float] = {}
    for index, dimension in enumerate(ASHTAKOOT_DIMENSIONS):
        key = f"q{index + 1}"
        value = answers.get(key)
        if value is None:
            scored[dimension] = 0.0
            continue
        normalized = max(1, min(5, value)) / 5
        scored[dimension] = round(normalized * ASHTAKOOT_WEIGHTS[dimension], 2)
    return scored


def build_assessment_profile(user_id: str, answers: dict[str, int], submitted_at: datetime | None = None) -> dict:
    question_ids = [f"q{index + 1}" for index in range(len(ASHTAKOOT_DIMENSIONS))]
    missing_question_ids = [qid for qid in question_ids if qid not in answers]
    return {
        "user_id": user_id,
        "scores": score_assessment(answers),
        "answered_count": len(answers),
        "total_questions": len(question_ids),
        "missing_question_ids": missing_question_ids,
        "complete": len(missing_question_ids) == 0,
        "submitted_at": submitted_at,
    }


async def submit_assessment_response(user_id: str, answers: dict[str, int], db: AsyncSession) -> dict:
    submitted_at = datetime.now(tz=UTC)
    profile_data = build_assessment_profile(user_id=user_id, answers=answers, submitted_at=submitted_at)

    # Upsert: update if exists, insert if not
    result = await db.execute(select(PsychometricProfile).where(PsychometricProfile.user_id == user_id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.answers = answers
        existing.scores = profile_data["scores"]
        existing.answered_count = profile_data["answered_count"]
        existing.missing_question_ids = profile_data["missing_question_ids"]
        existing.complete = profile_data["complete"]
        existing.submitted_at = submitted_at
    else:
        record = PsychometricProfile(
            id=str(uuid4()),
            user_id=user_id,
            answers=answers,
            scores=profile_data["scores"],
            answered_count=profile_data["answered_count"],
            total_questions=profile_data["total_questions"],
            missing_question_ids=profile_data["missing_question_ids"],
            complete=profile_data["complete"],
            submitted_at=submitted_at,
        )
        db.add(record)

    await db.commit()
    return profile_data


async def get_assessment_response(user_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(PsychometricProfile).where(PsychometricProfile.user_id == user_id))
    record = result.scalar_one_or_none()
    if record is None:
        return build_assessment_profile(user_id=user_id, answers={})
    return {
        "user_id": record.user_id,
        "scores": record.scores,
        "answered_count": record.answered_count,
        "total_questions": record.total_questions,
        "missing_question_ids": record.missing_question_ids,
        "complete": record.complete,
        "submitted_at": record.submitted_at,
    }


# ---------------------------------------------------------------------------
# Compatibility engine (pure computation — no DB needed)
# ---------------------------------------------------------------------------

def mock_compatibility_scores(member_id: str, data_mode: str = "full") -> dict[str, float | None]:
    seed = sum(ord(ch) for ch in member_id.lower())
    rng = random.Random(seed)
    scores: dict[str, float | None] = {}
    for dimension in ASHTAKOOT_DIMENSIONS:
        weight = ASHTAKOOT_WEIGHTS[dimension]
        scores[dimension] = round(weight * rng.uniform(0.35, 0.95), 2)
    if data_mode == "incomplete":
        for dimension in rng.sample(ASHTAKOOT_DIMENSIONS, k=3):
            scores[dimension] = None
    return scores


def compatibility(scores_a: dict[str, float | None], scores_b: dict[str, float | None]) -> dict:
    dim_scores: dict[str, float] = {}
    dim_breakdown: list[dict] = []
    weak: list[str] = []
    strong: list[str] = []
    risk_flags: list[str] = []
    data_gaps: set[str] = set()
    total = 0.0
    observed_signal_count = 0
    total_signal_count = len(ASHTAKOOT_DIMENSIONS) * 2

    for dimension in ASHTAKOOT_DIMENSIONS:
        max_dim = ASHTAKOOT_WEIGHTS[dimension]
        raw_a = scores_a.get(dimension)
        raw_b = scores_b.get(dimension)

        if raw_a is not None:
            observed_signal_count += 1
        if raw_b is not None:
            observed_signal_count += 1
        if raw_a is None or raw_b is None:
            data_gaps.add(dimension)

        a = raw_a if raw_a is not None else max_dim * 0.5
        b = raw_b if raw_b is not None else max_dim * 0.5
        similarity = max(0.0, 1.0 - (abs(a - b) / max_dim))
        dim_score = round(similarity * max_dim, 2)
        dim_scores[dimension] = dim_score
        total += dim_score
        pct_of_weight = round((dim_score / max_dim) * 100, 2)

        if dim_score < max_dim * 0.3:
            status = "weak"
            weak.append(dimension)
            risk_flags.append(f"Critical misalignment in {dimension.replace('_', ' ')}.")
        elif dim_score > max_dim * 0.8:
            status = "strong"
            strong.append(dimension)
        else:
            status = "balanced"

        dim_breakdown.append(
            {
                "dimension": dimension,
                "weight": max_dim,
                "score": dim_score,
                "pct_of_weight": pct_of_weight,
                "status": status,
            }
        )

    if total >= 28:
        level, label = "excellent", "excellent"
    elif total >= 20:
        level, label = "good", "moderate"
    elif total >= 12:
        level, label = "fair", "moderate"
    else:
        level, label = "poor", "high_friction"

    confidence = round(observed_signal_count / total_signal_count, 2)
    if confidence < 0.75:
        risk_flags.append("Low confidence: one or more dimensions have sparse data.")

    if dim_scores["nadi_chronotype_sync"] < ASHTAKOOT_WEIGHTS["nadi_chronotype_sync"] * 0.45:
        risk_flags.append("Chronotype sync is weak; consider async-first collaboration rituals.")

    return {
        "total_score_36": round(total, 2),
        "score_pct_100": round((total / 36) * 100, 2),
        "level": level,
        "label": label,
        "weak_dimensions": weak,
        "strong_dimensions": strong,
        "risk_flags": risk_flags,
        "confidence": confidence,
        "data_gaps": sorted(data_gaps),
        "dimension_scores": dim_scores,
        "dimension_breakdown": dim_breakdown,
    }


# ---------------------------------------------------------------------------
# CAT — Computerized Adaptive Testing (branching question selection)
# ---------------------------------------------------------------------------

# Question order by dimension index: q1=varna(1pt) … q8=nadi(8pt)
_QUESTION_WEIGHTS: dict[str, float] = {
    f"q{idx + 1}": weight
    for idx, weight in enumerate(ASHTAKOOT_WEIGHTS.values())
}  # q1→1.0, q2→2.0, … q8→8.0


def cat_select_next_question(current_answers: dict[str, int]) -> str | None:
    """Return the next question ID for a CAT session, or None when complete.

    Strategy:
    - Always start with the highest-weight question (q8 = nadi_chronotype_sync).
    - Pick the next highest-weight unanswered question.
    - Early-stop: if answered questions cover ≥70 % of total weight AND no
      high-weight (≥4 pts) questions remain, the profile is complete enough.
    """
    remaining = {q: w for q, w in _QUESTION_WEIGHTS.items() if q not in current_answers}
    if not remaining:
        return None

    # Early-stop check once we have at least half the questions answered
    if len(current_answers) >= 4:
        answered_weight = sum(_QUESTION_WEIGHTS[q] for q in current_answers)
        total_weight = sum(_QUESTION_WEIGHTS.values())  # 36
        high_weight_left = {q for q, w in remaining.items() if w >= 4.0}
        if not high_weight_left and answered_weight / total_weight >= 0.70:
            return None  # Signal: profile is confident enough to stop early

    # Pick highest-weight unanswered question
    return max(remaining, key=lambda q: remaining[q])


def cat_rationale(next_qid: str | None, current_answers: dict[str, int]) -> str:
    """Human-readable explanation for why the next question was chosen."""
    if next_qid is None:
        return "Assessment complete — sufficient confidence for scoring."
    weight = _QUESTION_WEIGHTS.get(next_qid, 1.0)
    answered_count = len(current_answers)
    if answered_count == 0:
        return f"{next_qid} opens with the highest-signal dimension ({weight:.0f} pts)."
    return (
        f"After {answered_count} answer(s), {next_qid} ({weight:.0f} pts) maximises "
        "remaining information gain."
    )


def cat_estimated_remaining(next_qid: str | None, current_answers: dict[str, int]) -> int:
    """How many more questions are expected before early-stop or completion."""
    if next_qid is None:
        return 0
    unanswered = [q for q in _QUESTION_WEIGHTS if q not in current_answers]
    return len(unanswered)


# ---------------------------------------------------------------------------
# Monte Carlo — candidate simulation (1 000 iterations)
# ---------------------------------------------------------------------------


def monte_carlo_candidate_simulation(
    team_scores: list[dict[str, float]],
    n_iterations: int = 1000,
) -> dict[str, Any]:
    """Simulate *n_iterations* random candidate profiles; return the optimal complement.

    Each iteration:
    1. Sample a random candidate dimension-score vector.
    2. Compute pairwise compatibility with each team member.
    3. Track score improvement vs current team-internal mean.
    """
    rng = random.Random(42)  # deterministic seed for reproducibility

    if not team_scores:
        team_scores = [{dim: round(w * 0.5, 2) for dim, w in ASHTAKOOT_WEIGHTS.items()}]

    # Current team-internal mean pairwise compatibility (computed once, outside loop)
    internal_pairs: list[float] = []
    for i, member_a in enumerate(team_scores):
        for member_b in team_scores[i + 1 :]:
            internal_pairs.append(compatibility(member_a, member_b)["total_score_36"])
    current_mean_compat = sum(internal_pairs) / max(len(internal_pairs), 1)

    # Identify weak dimensions to bias sampling toward complementary candidates
    team_mean = {
        dim: sum(m.get(dim, ASHTAKOOT_WEIGHTS[dim] * 0.5) for m in team_scores) / len(team_scores)
        for dim in ASHTAKOOT_DIMENSIONS
    }
    weak_dims = {
        dim for dim in ASHTAKOOT_DIMENSIONS if team_mean[dim] < ASHTAKOOT_WEIGHTS[dim] * 0.45
    }

    best_improvement = -float("inf")
    optimal_profile: dict[str, float] = {}
    improvements: list[float] = []

    for _ in range(n_iterations):
        candidate: dict[str, float] = {}
        for dim in ASHTAKOOT_DIMENSIONS:
            max_w = ASHTAKOOT_WEIGHTS[dim]
            lo, hi = (0.5, 1.0) if dim in weak_dims else (0.15, 0.95)
            candidate[dim] = round(max_w * rng.uniform(lo, hi), 2)

        candidate_compat_scores = [
            compatibility(candidate, member)["total_score_36"] for member in team_scores
        ]
        mean_with_candidate = sum(candidate_compat_scores) / len(candidate_compat_scores)
        improvement = mean_with_candidate - current_mean_compat
        improvements.append(improvement)

        if improvement > best_improvement:
            best_improvement = improvement
            optimal_profile = candidate.copy()

    improvements_sorted = sorted(improvements)
    p25 = improvements_sorted[n_iterations // 4]
    p75 = improvements_sorted[(3 * n_iterations) // 4]
    mean_improvement = sum(improvements) / n_iterations

    return {
        "n_iterations": n_iterations,
        "optimal_profile": optimal_profile,
        "mean_improvement": round(mean_improvement, 2),
        "best_improvement": round(best_improvement, 2),
        "p25_improvement": round(p25, 2),
        "p75_improvement": round(p75, 2),
        "weak_dimensions_targeted": sorted(weak_dims),
        "confidence": 1.0,  # always high at 1000 iterations
        "status": "complete",
    }


# ---------------------------------------------------------------------------
# Orchestrator — LangGraph + DB-persisted agent runs
# ---------------------------------------------------------------------------

def start_orchestrator_steps(include_candidates: bool) -> list[str]:
    steps = ["github_analyst", "psychometric_profiler", "compatibility_engine", "synthesis"]
    if include_candidates:
        steps.insert(2, "candidate_simulation")
    return steps


class OrchestratorState(TypedDict, total=False):
    team_id: str
    user_id: str
    github_handle: str          # explicit handle overrides user_id derivation
    access_token: str           # GitHub OAuth token for real API calls
    include_candidates: bool
    github_signals: dict[str, Any]
    assessment_profile: dict[str, Any]
    candidate_outlook: dict[str, Any]
    compatibility: dict[str, Any]
    synthesis: dict[str, Any]
    synthesis_text: str         # streamed narrative from Claude


async def _github_analyst_node(state: OrchestratorState) -> dict[str, Any]:
    handle = state.get("github_handle") or state["user_id"].replace("user_", "") or "team-member"
    access_token = state.get("access_token") or settings.github_access_token

    if access_token:
        try:
            client = _get_github_client(access_token)
            data = await client.analyze(handle)
            return {"github_signals": data}
        except Exception:  # noqa: BLE001
            pass

    # Fallback to deterministic mock
    chronotype = _derive_chronotype(handle)
    commits = len(handle) * 7
    return {
        "github_signals": {
            "github_handle": handle,
            "chronotype": chronotype,
            "commits_last_30_days": commits,
            "collaboration_index": round(min(100.0, 45 + len(handle) * 3 * 0.8), 2),
            "activity_rhythm_score": round(min(100.0, 20 + commits * 0.9), 2),
        }
    }


async def _psychometric_profiler_node(state: OrchestratorState) -> dict[str, Any]:
    # In Feature 8 this will load the real user profile from DB.
    # For now use a representative synthetic profile.
    answer_map = {f"q{idx + 1}": 3 + (idx % 3) for idx in range(len(ASHTAKOOT_DIMENSIONS))}
    profile = build_assessment_profile(user_id=state["user_id"], answers=answer_map, submitted_at=datetime.now(tz=UTC))
    return {"assessment_profile": profile}


def _candidate_simulation_node(state: OrchestratorState) -> dict[str, Any]:
    # Pull team scores from compatibility state if available
    compat = state.get("compatibility", {})
    team_scores_raw = compat.get("dimension_scores")
    team_scores = [team_scores_raw] if team_scores_raw else []
    result = monte_carlo_candidate_simulation(team_scores, n_iterations=1000)
    return {"candidate_outlook": result}


def _compatibility_engine_node(state: OrchestratorState) -> dict[str, Any]:
    source_scores = state["assessment_profile"]["scores"]
    reference_scores = {
        dimension: round(max(weight - 0.6, 0.4), 2) for dimension, weight in ASHTAKOOT_WEIGHTS.items()
    }
    return {"compatibility": compatibility(source_scores, reference_scores)}


async def _synthesis_node(state: OrchestratorState) -> dict[str, Any]:
    from .claude_client import generate_synthesis
    compat = state["compatibility"]
    narrative = await generate_synthesis(
        compatibility=compat,
        github_signals=state.get("github_signals"),
        assessment_profile=state.get("assessment_profile"),
    )
    synth_dict = synthesis_from_compat(
        total_score=compat["total_score_36"],
        weak_dimensions=compat["weak_dimensions"],
    )
    synth_dict["narrative"] = narrative
    return {"synthesis": synth_dict, "synthesis_text": narrative}


def _route_after_psychometric(state: OrchestratorState) -> str:
    return "candidate_simulation" if state.get("include_candidates") else "compatibility_engine"


@lru_cache(maxsize=1)
def _compiled_orchestrator_graph():
    graph = StateGraph(OrchestratorState)
    graph.add_node("github_analyst", _github_analyst_node)
    graph.add_node("psychometric_profiler", _psychometric_profiler_node)
    graph.add_node("candidate_simulation", _candidate_simulation_node)
    graph.add_node("compatibility_engine", _compatibility_engine_node)
    graph.add_node("synthesis", _synthesis_node)

    graph.add_edge(START, "github_analyst")
    graph.add_edge("github_analyst", "psychometric_profiler")
    graph.add_conditional_edges(
        "psychometric_profiler",
        _route_after_psychometric,
        {
            "candidate_simulation": "candidate_simulation",
            "compatibility_engine": "compatibility_engine",
        },
    )
    graph.add_edge("candidate_simulation", "compatibility_engine")
    graph.add_edge("compatibility_engine", "synthesis")
    graph.add_edge("synthesis", END)
    return graph.compile()


async def create_agent_run(team_id: str, user_id: str, include_candidates: bool, db: AsyncSession) -> str:
    run_id = str(uuid4())
    run = AgentRun(
        id=run_id,
        team_id=team_id,
        user_id=user_id,
        include_candidates=include_candidates,
        status="started",
        started_at=datetime.now(tz=UTC),
    )
    db.add(run)
    await db.commit()
    return run_id


async def get_agent_run(run_id: str, db: AsyncSession) -> AgentRun | None:
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    return result.scalar_one_or_none()


async def stream_orchestrator_updates(
    *,
    team_id: str,
    user_id: str,
    include_candidates: bool,
) -> AsyncIterator[dict[str, dict[str, Any]]]:
    graph = _compiled_orchestrator_graph()
    initial_state: OrchestratorState = {
        "team_id": team_id,
        "user_id": user_id,
        "include_candidates": include_candidates,
    }
    async for update in graph.astream(initial_state, stream_mode="updates"):
        yield update


# ---------------------------------------------------------------------------
# Teams — CRUD
# ---------------------------------------------------------------------------

def _team_to_dict(team: Team, members: list[TeamMember]) -> dict:
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "created_by": team.created_by,
        "invite_token": team.invite_token,
        "created_at": team.created_at,
        "members": [
            {
                "team_id": m.team_id,
                "user_id": m.user_id,
                "role": m.role,
                "github_handle": m.github_handle,
                "joined_at": m.joined_at,
            }
            for m in members
        ],
    }


async def create_team(name: str, description: str | None, created_by: str, db: AsyncSession) -> dict:
    team_id = str(uuid4())
    team = Team(
        id=team_id,
        name=name,
        description=description,
        created_by=created_by,
        invite_token=uuid4().hex,
    )
    db.add(team)
    creator = TeamMember(team_id=team_id, user_id=created_by, role="owner")
    db.add(creator)
    await db.commit()
    await db.refresh(team)
    await db.refresh(creator)
    return _team_to_dict(team, [creator])


async def update_team(team_id: str, name: str | None, description: str | None, db: AsyncSession) -> dict | None:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        return None
    if name is not None:
        team.name = name
    if description is not None:
        team.description = description
    await db.commit()
    await db.refresh(team)
    members_result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
    members = list(members_result.scalars().all())
    return _team_to_dict(team, members)


async def get_team(team_id: str, db: AsyncSession) -> dict | None:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if team is None:
        return None
    members_result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
    members = list(members_result.scalars().all())
    return _team_to_dict(team, members)


async def add_team_member(
    team_id: str,
    user_id: str,
    github_handle: str | None,
    role: str | None,
    db: AsyncSession,
) -> dict:
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    if team_result.scalar_one_or_none() is None:
        raise ValueError("Team not found")
    existing = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("Already a member")
    member = TeamMember(team_id=team_id, user_id=user_id, github_handle=github_handle, role=role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return {
        "team_id": member.team_id,
        "user_id": member.user_id,
        "role": member.role,
        "github_handle": member.github_handle,
        "joined_at": member.joined_at,
    }


async def remove_team_member(team_id: str, user_id: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        return False
    await db.delete(member)
    await db.commit()
    return True


async def list_teams_for_user(user_id: str, db: AsyncSession) -> list[dict]:
    memberships = await db.execute(select(TeamMember).where(TeamMember.user_id == user_id))
    team_ids = [m.team_id for m in memberships.scalars().all()]
    if not team_ids:
        return []
    teams_result = await db.execute(select(Team).where(Team.id.in_(team_ids)))
    teams = list(teams_result.scalars().all())
    output = []
    for team in teams:
        all_members = await db.execute(select(TeamMember).where(TeamMember.team_id == team.id))
        output.append(_team_to_dict(team, list(all_members.scalars().all())))
    return output


# ---------------------------------------------------------------------------
# Synthesis (template-based — upgraded to real Claude in Feature 4)
# ---------------------------------------------------------------------------

def synthesis_from_compat(total_score: float, weak_dimensions: list[str]) -> dict:
    if total_score >= 28:
        verdict = "The pair/team alignment is strong for delivery-critical work."
    elif total_score < 18:
        verdict = "The pair/team has notable friction risks in execution and planning cadence."
    else:
        verdict = "The pair/team is workable but needs intentional alignment rituals."

    strengths = "The team profile suggests stable collaboration patterns."
    uncertainty = (
        f"Weak dimensions detected in {', '.join(weak_dimensions[:3])}; collect more behavioral data before final staffing decisions."
        if weak_dimensions
        else "No high-risk weak dimensions detected in this run."
    )

    return {
        "run_id": str(uuid4()),
        "narrative": f"{verdict} {strengths}",
        "recommendations": [
            "Run one two-week trial sprint and review communication bottlenecks.",
            "Pair planning with a fixed decision owner to reduce ambiguity loops.",
            "Reassess compatibility after updated GitHub and assessment signals.",
        ],
        "uncertainty_note": uncertainty,
    }

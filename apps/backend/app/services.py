from datetime import UTC, datetime, timedelta
import math
import random
import secrets
from functools import lru_cache
from typing import Any, AsyncIterator, TypedDict
from urllib.parse import urlencode
from uuid import uuid4

from jose import JWTError, jwt
from langgraph.graph import END, START, StateGraph
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func as sa_func

from .config import settings
from .memory import MemoryManager
from .models import AgentRun, GithubProfile, PsychometricProfile, Team, TeamMember, TeamScore, UserProfile
from .schemas import ASHTAKOOT_DIMENSIONS, ASHTAKOOT_WEIGHTS

_oauth_state_store: dict[str, datetime] = {}
memory_manager = MemoryManager()

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


def register_oauth_state(state: str) -> None:
    _oauth_state_store[state] = datetime.now(tz=UTC)


def consume_oauth_state(state: str | None, max_age_seconds: int = 600) -> bool:
    if not state:
        return False
    created_at = _oauth_state_store.pop(state, None)
    if created_at is None:
        return False
    return (datetime.now(tz=UTC) - created_at).total_seconds() <= max_age_seconds


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
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://github.com/login/oauth/access_token",
                    json={
                        "client_id": settings.github_client_id,
                        "client_secret": settings.github_client_secret,
                        "code": code,
                        "redirect_uri": settings.github_redirect_url,
                    },
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
                resp.raise_for_status()
                token_data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"GitHub token exchange failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise ValueError(f"GitHub token exchange network error: {exc}") from exc

        access_token = token_data.get("access_token", "")
        if not access_token or "error" in token_data:
            err_desc = token_data.get("error_description", token_data.get("error", "OAuth exchange failed"))
            raise ValueError(f"GitHub OAuth failed: {err_desc}")

        try:
            async with httpx.AsyncClient() as client:
                user_resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                    timeout=10,
                )
                user_resp.raise_for_status()
                github_user = user_resp.json()
        except httpx.HTTPStatusError as exc:
            raise ValueError(f"GitHub user API failed: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise ValueError(f"GitHub user API network error: {exc}") from exc

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


DIMENSION_PRIOR_RATIOS: dict[str, float] = {
    "varna_alignment": 0.52,
    "vashya_influence": 0.48,
    "tara_resilience": 0.55,
    "yoni_workstyle": 0.51,
    "graha_maitri_cognition": 0.50,
    "gana_temperament": 0.46,
    "bhakoot_strategy": 0.54,
    "nadi_chronotype_sync": 0.49,
}


def _confidence_band(confidence: float) -> tuple[str, str]:
    if confidence >= 0.8:
        return "high", "low"
    if confidence >= 0.6:
        return "medium", "moderate"
    return "low", "high"


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

        if raw_a is None and raw_b is None:
            dim_score = 0.0
            dim_scores[dimension] = dim_score
            weak.append(dimension)
            risk_flags.append(
                f"Insufficient signal in {dimension.replace('_', ' ')}; cannot score reliably."
            )
            dim_breakdown.append(
                {
                    "dimension": dimension,
                    "weight": max_dim,
                    "score": dim_score,
                    "pct_of_weight": 0.0,
                    "status": "weak",
                }
            )
            continue

        prior = DIMENSION_PRIOR_RATIOS.get(dimension, 0.5)
        a = raw_a if raw_a is not None else max_dim * prior
        b = raw_b if raw_b is not None else max_dim * prior
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
    confidence_label, uncertainty_band = _confidence_band(confidence)
    insufficient_confidence = confidence < 0.6 or len(data_gaps) >= 4
    if insufficient_confidence:
        risk_flags.append("Low confidence: one or more dimensions have sparse data.")

    if insufficient_confidence:
        level, label = "insufficient", "insufficient_data"

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
        "confidence_label": confidence_label,
        "insufficient_confidence": insufficient_confidence,
        "uncertainty_band": uncertainty_band,
        "data_gaps": sorted(data_gaps),
        "dimension_scores": dim_scores,
        "dimension_breakdown": dim_breakdown,
    }


# ---------------------------------------------------------------------------
# CAT — Computerized Adaptive Testing (branching question selection)
# ---------------------------------------------------------------------------

# IRT item setup by dimension index: q1=varna … q8=nadi
_QUESTION_WEIGHTS: dict[str, float] = {
    f"q{idx + 1}": weight
    for idx, weight in enumerate(ASHTAKOOT_WEIGHTS.values())
}
_QUESTION_IRT_PARAMS: dict[str, tuple[float, float]] = {
    qid: (1.0 + (weight / 8.0), (4.5 - weight) / 2.0)
    for qid, weight in _QUESTION_WEIGHTS.items()
}


def _estimate_theta(current_answers: dict[str, int]) -> float:
    if not current_answers:
        return 0.0
    transformed: list[float] = []
    for qid, answer in current_answers.items():
        a, b = _QUESTION_IRT_PARAMS.get(qid, (1.0, 0.0))
        p = min(0.95, max(0.05, (answer - 1) / 4))
        transformed.append((math.log(p / (1 - p)) / a) + b)
    return float(sum(transformed) / max(1, len(transformed)))


def _question_information(qid: str, theta: float) -> float:
    a, b = _QUESTION_IRT_PARAMS[qid]
    p = 1 / (1 + math.exp(-a * (theta - b)))
    return a * a * p * (1 - p)


def _test_information(current_answers: dict[str, int]) -> float:
    theta = _estimate_theta(current_answers)
    return sum(_question_information(qid, theta) for qid in current_answers if qid in _QUESTION_IRT_PARAMS)


def cat_select_next_question(current_answers: dict[str, int]) -> str | None:
    """Return the next question ID for a CAT session, or None when complete.

    Strategy:
    - Cold start with q8 for strongest initial signal.
    - Estimate latent trait (theta) from current responses.
    - Select next unanswered question with highest Fisher information.
    - Early-stop when accumulated test information passes threshold.
    """
    remaining = {q: w for q, w in _QUESTION_WEIGHTS.items() if q not in current_answers}
    if not remaining:
        return None

    if not current_answers:
        return "q8"

    if len(current_answers) >= 5 and _test_information(current_answers) >= 3.2:
        return None

    theta = _estimate_theta(current_answers)
    return max(remaining, key=lambda qid: _question_information(qid, theta))


def cat_rationale(next_qid: str | None, current_answers: dict[str, int]) -> str:
    """Human-readable explanation for why the next question was chosen."""
    if next_qid is None:
        return "Assessment complete — IRT information threshold reached."
    weight = _QUESTION_WEIGHTS.get(next_qid, 1.0)
    info = _question_information(next_qid, _estimate_theta(current_answers))
    answered_count = len(current_answers)
    if answered_count == 0:
        return f"{next_qid} opens with the highest-signal dimension ({weight:.0f} pts)."
    return (
        f"After {answered_count} answer(s), {next_qid} ({weight:.0f} pts) maximises "
        f"remaining information gain (I={info:.2f})."
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
    random_seed: int | None = None,
    bootstrap_runs: int = 5,
) -> dict[str, Any]:
    """Simulate *n_iterations* random candidate profiles; return the optimal complement.

    Each iteration:
    1. Sample a random candidate dimension-score vector.
    2. Compute pairwise compatibility with each team member.
    3. Track score improvement vs current team-internal mean.
    """
    seed = random_seed if random_seed is not None else secrets.randbelow(2_147_483_647)

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
    bootstrap_means: list[float] = []

    for run_idx in range(bootstrap_runs):
        run_rng = random.Random(seed + run_idx)
        run_improvements: list[float] = []
        for _ in range(n_iterations):
            candidate: dict[str, float] = {}
            for dim in ASHTAKOOT_DIMENSIONS:
                max_w = ASHTAKOOT_WEIGHTS[dim]
                lo, hi = (0.5, 1.0) if dim in weak_dims else (0.15, 0.95)
                candidate[dim] = round(max_w * run_rng.uniform(lo, hi), 2)

            candidate_compat_scores = [
                compatibility(candidate, member)["total_score_36"] for member in team_scores
            ]
            mean_with_candidate = sum(candidate_compat_scores) / len(candidate_compat_scores)
            improvement = mean_with_candidate - current_mean_compat
            run_improvements.append(improvement)
            improvements.append(improvement)

            if improvement > best_improvement:
                best_improvement = improvement
                optimal_profile = candidate.copy()

        bootstrap_means.append(float(np.mean(run_improvements)))

    improvements_sorted = sorted(improvements)
    total_samples = len(improvements_sorted)
    p05 = improvements_sorted[int(total_samples * 0.05)]
    p25 = improvements_sorted[int(total_samples * 0.25)]
    p75 = improvements_sorted[int(total_samples * 0.75)]
    p95 = improvements_sorted[int(total_samples * 0.95)]
    mean_improvement = float(np.mean(improvements))
    std_improvement = float(np.std(improvements))
    sem = std_improvement / math.sqrt(max(1, total_samples))
    confidence = max(0.35, min(0.99, 1.0 - min(0.65, sem / (abs(mean_improvement) + 1.0))))
    sensitivity_spread = max(bootstrap_means) - min(bootstrap_means) if bootstrap_means else 0.0

    return {
        "n_iterations": n_iterations,
        "optimal_profile": optimal_profile,
        "mean_improvement": round(mean_improvement, 2),
        "std_improvement": round(std_improvement, 3),
        "best_improvement": round(best_improvement, 2),
        "p05_improvement": round(p05, 2),
        "p25_improvement": round(p25, 2),
        "p75_improvement": round(p75, 2),
        "p95_improvement": round(p95, 2),
        "weak_dimensions_targeted": sorted(weak_dims),
        "confidence": round(confidence, 3),
        "random_seed": seed,
        "sensitivity_spread": round(sensitivity_spread, 3),
        "status": "complete",
    }


# ---------------------------------------------------------------------------
# Orchestrator helpers — preload DB data before graph runs
# ---------------------------------------------------------------------------

async def _load_member_profiles(team_id: str, db: AsyncSession) -> list[dict[str, Any]]:
    """Load all team members with their UserProfile, GithubProfile, and PsychometricProfile."""
    members_result = await db.execute(select(TeamMember).where(TeamMember.team_id == team_id))
    members = members_result.scalars().all()

    profiles = []
    for member in members:
        uid = member.user_id

        up_result = await db.execute(select(UserProfile).where(UserProfile.user_id == uid))
        up = up_result.scalar_one_or_none()

        gp_result = await db.execute(
            select(GithubProfile)
            .where(GithubProfile.user_id == uid, GithubProfile.sync_status == "complete")
            .order_by(GithubProfile.completed_at.desc())
            .limit(1)
        )
        gp = gp_result.scalar_one_or_none()

        pp_result = await db.execute(select(PsychometricProfile).where(PsychometricProfile.user_id == uid))
        pp = pp_result.scalar_one_or_none()

        profiles.append({
            "user_id": uid,
            "github_handle": member.github_handle or (up.github_handle if up else None),
            "role": member.role,
            "access_token": up.github_access_token if up else None,
            "github_data": {
                "chronotype": gp.chronotype,
                "activity_rhythm_score": gp.activity_rhythm_score,
                "collaboration_index": gp.collaboration_index,
                "commits_last_30_days": gp.commits_last_30_days,
                "prs_last_30_days": gp.prs_last_30_days,
                "raw_data": gp.raw_data,
            } if gp else None,
            "psychometric_scores": pp.scores if (pp and pp.complete) else None,
            "psychometric_answers": pp.answers if pp else None,
        })

    return profiles


async def save_team_score(
    team_id: str,
    run_id: str,
    compat: dict[str, Any],
    narrative: str | None,
    db: AsyncSession,
) -> None:
    """Persist compatibility results to TeamScore after an orchestrator run completes."""
    ts = TeamScore(
        id=str(uuid4()),
        team_id=team_id,
        agent_run_id=run_id,
        resilience_score=compat.get("total_score_36", 0.0),
        compatibility_pct=compat.get("score_pct_100", 0.0),
        level=compat.get("level"),
        confidence=compat.get("confidence"),
        dimension_scores=compat.get("dimension_scores", {}),
        weak_dimensions=compat.get("weak_dimensions", []),
        strong_dimensions=compat.get("strong_dimensions", []),
        risk_flags=compat.get("risk_flags", []),
        narrative_report=narrative,
        pairwise_scores=compat.get("pairwise_scores"),
        calculated_at=datetime.now(tz=UTC),
    )
    db.add(ts)
    await db.commit()


async def get_real_scores_for_user(
    user_id: str, data_mode: str, db: AsyncSession
) -> dict[str, float | None]:
    """Return real PsychometricProfile scores, falling back to deterministic mock."""
    result = await db.execute(
        select(PsychometricProfile).where(PsychometricProfile.user_id == user_id)
    )
    pp = result.scalar_one_or_none()
    if pp and pp.complete:
        return dict(pp.scores)
    return mock_compatibility_scores(user_id, data_mode=data_mode)


# ---------------------------------------------------------------------------
# Orchestrator — LangGraph + DB-persisted agent runs
# ---------------------------------------------------------------------------

def start_orchestrator_steps(include_candidates: bool) -> list[str]:
    steps = ["github_analyst", "psychometric_profiler", "compatibility_engine", "synthesis"]
    if include_candidates:
        steps.insert(2, "candidate_simulation")
    return steps


def orchestrator_step_contracts() -> dict[str, dict[str, Any]]:
    return {
        "github_analyst": {
            "role": "Data Retriever",
            "allowed_tools": ["github_api", "cached_db_profile"],
            "max_retries": 2,
            "output_contract": ["github_handle", "chronotype", "collaboration_index"],
        },
        "psychometric_profiler": {
            "role": "Model Runner",
            "allowed_tools": ["assessment_store"],
            "max_retries": 1,
            "output_contract": ["scores", "complete", "submitted_at"],
        },
        "candidate_simulation": {
            "role": "Risk Auditor",
            "allowed_tools": ["simulation_engine"],
            "max_retries": 1,
            "output_contract": ["optimal_profile", "mean_improvement", "confidence"],
        },
        "compatibility_engine": {
            "role": "Risk Auditor",
            "allowed_tools": ["compatibility_engine"],
            "max_retries": 1,
            "output_contract": ["total_score_36", "risk_flags", "uncertainty_band"],
        },
        "synthesis": {
            "role": "Report Writer",
            "allowed_tools": ["claude_synthesis", "template_fallback"],
            "max_retries": 1,
            "output_contract": ["narrative", "recommendations", "uncertainty_note"],
        },
    }


class OrchestratorState(TypedDict, total=False):
    team_id: str
    user_id: str
    github_handle: str          # explicit handle overrides user_id derivation
    access_token: str           # GitHub OAuth token for real API calls
    include_candidates: bool
    member_profiles: list[dict[str, Any]]   # preloaded from DB before graph starts
    github_signals: dict[str, Any]
    assessment_profile: dict[str, Any]
    candidate_outlook: dict[str, Any]
    compatibility: dict[str, Any]
    synthesis: dict[str, Any]
    synthesis_text: str         # streamed narrative from Claude


async def _github_analyst_node(state: OrchestratorState) -> dict[str, Any]:
    handle = state.get("github_handle") or state["user_id"].replace("user_", "") or "team-member"
    access_token = state.get("access_token") or settings.github_access_token

    # 1. Try real GitHub API
    if access_token:
        try:
            client = _get_github_client(access_token)
            data = await client.analyze(handle)
            return {"github_signals": data}
        except Exception:  # noqa: BLE001
            pass

    # 2. Fallback: use preloaded DB data for the primary user
    user_id = state.get("user_id", "")
    for mp in state.get("member_profiles", []):
        if mp["user_id"] == user_id and mp.get("github_data"):
            gd = mp["github_data"]
            signals = {
                "github_handle": handle,
                "chronotype": gd.get("chronotype") or "flexible",
                "commits_last_30_days": gd.get("commits_last_30_days") or 0,
                "collaboration_index": gd.get("collaboration_index") or 50.0,
                "activity_rhythm_score": gd.get("activity_rhythm_score") or 50.0,
                "prs_last_30_days": gd.get("prs_last_30_days") or 0,
            }
            if gd.get("raw_data"):
                signals.update(gd["raw_data"])
            return {"github_signals": signals}

    # 3. Last resort: deterministic mock
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
    user_id = state.get("user_id", "")
    # Find primary user's profile from preloaded data
    for mp in state.get("member_profiles", []):
        if mp["user_id"] == user_id and mp.get("psychometric_scores"):
            answers = mp.get("psychometric_answers") or {}
            profile = {
                "user_id": user_id,
                "scores": mp["psychometric_scores"],
                "answers": answers,
                "complete": True,
                "submitted_at": datetime.now(tz=UTC),
            }
            return {"assessment_profile": profile}

    # No assessment found: preserve missingness so downstream uncertainty is explicit
    profile = {
        "user_id": user_id,
        "scores": {dim: None for dim in ASHTAKOOT_DIMENSIONS},
        "answers": {},
        "complete": False,
        "submitted_at": None,
    }
    return {"assessment_profile": profile}


def _candidate_simulation_node(state: OrchestratorState) -> dict[str, Any]:
    # Pull team scores from compatibility state if available
    compat = state.get("compatibility", {})
    team_scores_raw = compat.get("dimension_scores")
    team_scores = [team_scores_raw] if team_scores_raw else []
    result = monte_carlo_candidate_simulation(team_scores, n_iterations=1000)
    return {"candidate_outlook": result}


def _compatibility_engine_node(state: OrchestratorState) -> dict[str, Any]:
    # Collect all team members who have complete psychometric scores
    scored = [
        mp for mp in state.get("member_profiles", [])
        if mp.get("psychometric_scores")
    ]

    if len(scored) >= 2:
        # Pairwise compatibility across all team member combinations
        pair_results: list[dict] = []
        pairwise_scores: dict[str, Any] = {}
        for i, ma in enumerate(scored):
            for mb in scored[i + 1:]:
                result = compatibility(ma["psychometric_scores"], mb["psychometric_scores"])
                key = f"{ma['github_handle'] or ma['user_id']}_vs_{mb['github_handle'] or mb['user_id']}"
                pairwise_scores[key] = {
                    "total_score_36": result["total_score_36"],
                    "score_pct_100": result["score_pct_100"],
                    "level": result["level"],
                }
                pair_results.append(result)

        n = len(pair_results)
        avg_total = round(sum(r["total_score_36"] for r in pair_results) / n, 2)
        avg_pct = round(sum(r["score_pct_100"] for r in pair_results) / n, 1)
        avg_dim = {
            d: round(sum(r["dimension_scores"].get(d, 0.0) for r in pair_results) / n, 2)
            for d in ASHTAKOOT_DIMENSIONS
        }
        # Weak = any pair flagged weak; Strong = all pairs flagged strong
        all_weak = sorted({d for r in pair_results for d in r.get("weak_dimensions", [])})
        all_strong = sorted(
            {d for d in ASHTAKOOT_DIMENSIONS
             if all(d in r.get("strong_dimensions", []) for r in pair_results)}
        )
        all_risk = list(dict.fromkeys(f for r in pair_results for f in r.get("risk_flags", [])))
        avg_conf = round(sum(r.get("confidence", 1.0) for r in pair_results) / n, 3)

        if avg_total >= 28:
            level = "excellent"
        elif avg_total >= 20:
            level = "good"
        elif avg_total >= 12:
            level = "fair"
        else:
            level = "poor"

        return {"compatibility": {
            "total_score_36": avg_total,
            "score_pct_100": avg_pct,
            "level": level,
            "label": level,
            "weak_dimensions": all_weak,
            "strong_dimensions": all_strong,
            "risk_flags": all_risk,
            "confidence": avg_conf,
            "data_gaps": [],
            "dimension_scores": avg_dim,
            "dimension_breakdown": [
                {"dimension": d, "weight": ASHTAKOOT_WEIGHTS[d], "score": avg_dim[d],
                 "pct_of_weight": round((avg_dim[d] / ASHTAKOOT_WEIGHTS[d]) * 100, 1),
                 "status": "weak" if d in all_weak else ("strong" if d in all_strong else "balanced")}
                for d in ASHTAKOOT_DIMENSIONS
            ],
            "pairwise_scores": pairwise_scores,
            "member_count": len(scored),
        }}

    # Single or no scored members: compare primary user vs balanced reference
    source_scores = state.get("assessment_profile", {}).get("scores") or {
        d: round(ASHTAKOOT_WEIGHTS[d] * 0.5, 2) for d in ASHTAKOOT_DIMENSIONS
    }
    reference_scores = {d: round(max(w - 0.6, 0.4), 2) for d, w in ASHTAKOOT_WEIGHTS.items()}
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
    github_handle: str | None = None,
    access_token: str | None = None,
    include_candidates: bool,
    db: AsyncSession,
) -> AsyncIterator[dict[str, dict[str, Any]]]:
    # Preload all team member data from DB before graph starts
    member_profiles = await _load_member_profiles(team_id, db)

    graph = _compiled_orchestrator_graph()
    contracts = orchestrator_step_contracts()
    initial_state: OrchestratorState = {
        "team_id": team_id,
        "user_id": user_id,
        "github_handle": github_handle or "",
        "access_token": access_token or settings.github_access_token,
        "include_candidates": include_candidates,
        "member_profiles": member_profiles,
    }
    async for update in graph.astream(initial_state, stream_mode="updates"):
        step_name, step_payload = next(iter(update.items()))
        contract = contracts.get(step_name, {})
        if isinstance(step_payload, dict):
            step_payload["agent_contract"] = contract
        memory_manager.put(
            tier="short",
            key=team_id,
            value={"run_id": str(uuid4()), "step": step_name, "payload": step_payload or {}},
            provenance=f"orchestrator:{step_name}",
            ttl_seconds=60 * 30,
        )
        if step_name == "synthesis":
            memory_manager.put(
                tier="session",
                key=team_id,
                value={"step": "synthesis", "narrative": str(step_payload.get("synthesis_text", ""))[:4000]},
                provenance="orchestrator:synthesis",
                ttl_seconds=60 * 60 * 24,
            )
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
    # Look up the creator's github_handle so it shows correctly in the team roster
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == created_by))
    creator_profile = profile_result.scalar_one_or_none()
    creator = TeamMember(
        team_id=team_id,
        user_id=created_by,
        role="owner",
        github_handle=creator_profile.github_handle if creator_profile else None,
    )
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
        f"Weak dimensions detected in {', '.join(weak_dimensions[:3])}; collect more behavioral data before making high-impact team changes."
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

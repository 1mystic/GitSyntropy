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

from .config import settings
from .models import AgentRun, GithubProfile, PsychometricProfile, Team, TeamMember
from .schemas import ASHTAKOOT_DIMENSIONS, ASHTAKOOT_WEIGHTS

# Lazy imports to avoid startup errors when optional packages aren't configured
def _get_github_client(access_token: str):
    from .github_client import GitHubAnalystClient
    return GitHubAnalystClient(access_token)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_jwt(user_id: str) -> tuple[str, int]:
    expires_in = settings.jwt_exp_minutes * 60
    expiry = datetime.now(tz=UTC) + timedelta(seconds=expires_in)
    token = jwt.encode(
        {"sub": user_id, "exp": expiry, "iss": settings.jwt_issuer},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


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

        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                timeout=10,
            )
            user_resp.raise_for_status()
            github_user = user_resp.json()

        user_id = f"gh_{github_user['id']}"
        return {
            "user_id": user_id,
            "github_handle": github_user.get("login", ""),
            "name": github_user.get("name", ""),
            "email": github_user.get("email", ""),
            "avatar_url": github_user.get("avatar_url", ""),
            "access_token": access_token,
        }
    else:
        # Dev fallback: derive stable user_id from code string
        clean = "".join(char for char in code.lower() if char.isalnum())
        if not clean:
            raise ValueError("OAuth code is invalid.")
        user_id = f"user_github_{clean[-8:]}"
        return {"user_id": user_id, "github_handle": clean[-8:], "name": "", "email": "", "avatar_url": "", "access_token": ""}


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


async def trigger_github_sync(github_handle: str, user_id: str, db: AsyncSession) -> dict[str, Any]:
    chronotype = _derive_chronotype(github_handle)
    commits = len(github_handle) * 7
    prs = len(github_handle) * 3

    sync_id = str(uuid4())
    profile = GithubProfile(
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
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_sync_dict(profile)


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
    include_candidates: bool
    github_signals: dict[str, Any]
    assessment_profile: dict[str, Any]
    candidate_outlook: dict[str, Any]
    compatibility: dict[str, Any]
    synthesis: dict[str, Any]


def _github_analyst_node(state: OrchestratorState) -> dict[str, Any]:
    handle = state["user_id"].replace("user_", "") or "team-member"
    # Sync version for LangGraph node (real async version in Feature 3)
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


def _psychometric_profiler_node(state: OrchestratorState) -> dict[str, Any]:
    answer_map = {f"q{idx + 1}": 3 + (idx % 3) for idx in range(len(ASHTAKOOT_DIMENSIONS))}
    profile = build_assessment_profile(user_id=state["user_id"], answers=answer_map, submitted_at=datetime.now(tz=UTC))
    return {"assessment_profile": profile}


def _candidate_simulation_node(_: OrchestratorState) -> dict[str, Any]:
    return {
        "candidate_outlook": {
            "status": "simulated",
            "recommended_match": "candidate_delta",
            "confidence": 0.71,
        }
    }


def _compatibility_engine_node(state: OrchestratorState) -> dict[str, Any]:
    source_scores = state["assessment_profile"]["scores"]
    reference_scores = {
        dimension: round(max(weight - 0.6, 0.4), 2) for dimension, weight in ASHTAKOOT_WEIGHTS.items()
    }
    return {"compatibility": compatibility(source_scores, reference_scores)}


def _synthesis_node(state: OrchestratorState) -> dict[str, Any]:
    compat = state["compatibility"]
    return {
        "synthesis": synthesis_from_compat(
            total_score=compat["total_score_36"],
            weak_dimensions=compat["weak_dimensions"],
        )
    }


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

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import create_tables, get_db
from .schemas import (
    AddMemberRequest,
    AnalysisRequest,
    AnalysisResponse,
    AssessmentQuestion,
    AssessmentProfileResponse,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    AuthSessionResponse,
    AuthTokenResponse,
    CompatibilityRequest,
    CompatibilityResponse,
    GithubAuthCallbackRequest,
    GithubAuthStartResponse,
    GithubSyncRequest,
    GithubSyncResponse,
    HealthResponse,
    InsightResponse,
    LoginRequest,
    OrchestratorRunRequest,
    OrchestratorRunResponse,
    TeamCreateRequest,
    TeamMemberResponse,
    TeamResponse,
)
from .services import (
    AuthTokenError,
    add_team_member,
    assessment_questions,
    build_github_authorization_url,
    compatibility,
    create_agent_run,
    create_jwt,
    create_oauth_state,
    create_team,
    decode_jwt,
    exchange_github_code_for_identity,
    get_agent_run,
    get_assessment_response,
    get_github_sync,
    get_team,
    list_teams_for_user,
    mock_compatibility_scores,
    remove_team_member,
    start_orchestrator_steps,
    stream_orchestrator_updates,
    submit_assessment_response,
    synthesis_from_compat,
    trigger_github_sync,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_tables()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:4321", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token",
        )
    return parts[1]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)


# ---------------------------------------------------------------------------
# Mock analysis (kept for backward compat with frontend)
# ---------------------------------------------------------------------------

@app.post(f"{settings.api_prefix}/analysis/mock", response_model=AnalysisResponse)
async def mock_analysis(payload: AnalysisRequest) -> AnalysisResponse:
    return AnalysisResponse(
        run_id=str(uuid4()),
        team_id=payload.team_id,
        status="done",
        score=29.4,
        summary="Mock analysis completed. Team rhythm alignment is stable with manageable friction.",
        generated_at=datetime.now(tz=UTC),
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.get(f"{settings.api_prefix}/auth/github/start", response_model=GithubAuthStartResponse)
async def auth_github_start() -> GithubAuthStartResponse:
    state = create_oauth_state()
    return {
        "provider": "github",
        "authorization_url": build_github_authorization_url(state),
        "state": state,
        "redirect_uri": settings.github_redirect_url,
        "scopes": settings.github_scope.split(),
    }


@app.post(f"{settings.api_prefix}/auth/github/callback", response_model=AuthTokenResponse)
async def auth_github_callback(payload: GithubAuthCallbackRequest, db: AsyncSession = Depends(get_db)) -> AuthTokenResponse:
    identity = await exchange_github_code_for_identity(payload.code, db)
    user_id = identity["user_id"]
    token, expires_in = create_jwt(user_id=user_id)
    return AuthTokenResponse(access_token=token, expires_in=expires_in, user_id=user_id)


@app.post(f"{settings.api_prefix}/auth/login", response_model=AuthTokenResponse)
async def auth_login(payload: LoginRequest) -> AuthTokenResponse:
    user_id = f"user_{payload.email.split('@')[0]}"
    token, expires_in = create_jwt(user_id=user_id)
    return AuthTokenResponse(access_token=token, expires_in=expires_in, user_id=user_id)


@app.get(f"{settings.api_prefix}/auth/session", response_model=AuthSessionResponse)
async def auth_session(token: str = Depends(_require_bearer_token)) -> AuthSessionResponse:
    try:
        claims = decode_jwt(token)
        user_id = str(claims.get("sub", ""))
        exp_raw = claims.get("exp")
        if not user_id or exp_raw is None:
            raise ValueError("Malformed token claims.")
        if isinstance(exp_raw, datetime):
            expires_at = exp_raw
        else:
            expires_at = datetime.fromtimestamp(int(exp_raw), tz=UTC)
    except (AuthTokenError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from None
    return AuthSessionResponse(authenticated=True, user_id=user_id, expires_at=expires_at)


# ---------------------------------------------------------------------------
# GitHub sync
# ---------------------------------------------------------------------------

@app.post(f"{settings.api_prefix}/github/sync", response_model=GithubSyncResponse)
async def github_sync(payload: GithubSyncRequest, db: AsyncSession = Depends(get_db)) -> GithubSyncResponse:
    data = await trigger_github_sync(payload.github_handle, user_id=payload.user_id, db=db)
    return GithubSyncResponse(**data)


@app.get(f"{settings.api_prefix}/github/sync/{{sync_id}}", response_model=GithubSyncResponse)
async def github_sync_status(sync_id: str, db: AsyncSession = Depends(get_db)) -> GithubSyncResponse:
    data = await get_github_sync(sync_id, db=db)
    if data is None:
        raise HTTPException(status_code=404, detail="Sync job not found")
    return GithubSyncResponse(**data)


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------

@app.get(f"{settings.api_prefix}/assessment/questions", response_model=list[AssessmentQuestion])
async def get_assessment_questions() -> list[AssessmentQuestion]:
    return [AssessmentQuestion(**q) for q in assessment_questions()]


@app.get(f"{settings.api_prefix}/assessment/responses/{{user_id}}", response_model=AssessmentProfileResponse)
async def get_assessment(user_id: str, db: AsyncSession = Depends(get_db)) -> AssessmentProfileResponse:
    profile = await get_assessment_response(user_id, db=db)
    return AssessmentProfileResponse(**profile)


@app.post(f"{settings.api_prefix}/assessment/responses", response_model=AssessmentSubmitResponse)
async def submit_assessment_response_api(payload: AssessmentSubmitRequest, db: AsyncSession = Depends(get_db)) -> AssessmentSubmitResponse:
    profile = await submit_assessment_response(user_id=payload.user_id, answers=payload.answers, db=db)
    return AssessmentSubmitResponse(**profile)


@app.post(f"{settings.api_prefix}/assessment/submit", response_model=AssessmentSubmitResponse)
async def submit_assessment(payload: AssessmentSubmitRequest, db: AsyncSession = Depends(get_db)) -> AssessmentSubmitResponse:
    profile = await submit_assessment_response(user_id=payload.user_id, answers=payload.answers, db=db)
    return AssessmentSubmitResponse(**profile)


# ---------------------------------------------------------------------------
# Compatibility
# ---------------------------------------------------------------------------

@app.post(f"{settings.api_prefix}/compatibility/run", response_model=CompatibilityResponse)
async def run_compatibility(payload: CompatibilityRequest) -> CompatibilityResponse:
    sample_a = mock_compatibility_scores(payload.member_a, data_mode=payload.data_mode)
    sample_b = mock_compatibility_scores(payload.member_b, data_mode=payload.data_mode)
    result = compatibility(sample_a, sample_b)
    return CompatibilityResponse(member_a=payload.member_a, member_b=payload.member_b, **result)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

@app.post(f"{settings.api_prefix}/orchestrator/run", response_model=OrchestratorRunResponse)
async def orchestrator_run(payload: OrchestratorRunRequest, db: AsyncSession = Depends(get_db)) -> OrchestratorRunResponse:
    run_id = await create_agent_run(
        team_id=payload.team_id,
        user_id=payload.user_id,
        include_candidates=payload.include_candidates,
        db=db,
    )
    return OrchestratorRunResponse(
        run_id=run_id,
        state="started",
        steps=start_orchestrator_steps(payload.include_candidates),
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

@app.post(f"{settings.api_prefix}/teams", response_model=TeamResponse, status_code=201)
async def create_team_route(payload: TeamCreateRequest, db: AsyncSession = Depends(get_db)) -> TeamResponse:
    data = await create_team(payload.name, payload.description, payload.created_by, db)
    return TeamResponse(**data)


@app.get(f"{settings.api_prefix}/teams", response_model=list[TeamResponse])
async def list_teams_route(user_id: str, db: AsyncSession = Depends(get_db)) -> list[TeamResponse]:
    teams = await list_teams_for_user(user_id, db)
    return [TeamResponse(**t) for t in teams]


@app.get(f"{settings.api_prefix}/teams/{{team_id}}", response_model=TeamResponse)
async def get_team_route(team_id: str, db: AsyncSession = Depends(get_db)) -> TeamResponse:
    data = await get_team(team_id, db)
    if data is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamResponse(**data)


@app.post(f"{settings.api_prefix}/teams/{{team_id}}/members", response_model=TeamMemberResponse, status_code=201)
async def add_member_route(team_id: str, payload: AddMemberRequest, db: AsyncSession = Depends(get_db)) -> TeamMemberResponse:
    try:
        data = await add_team_member(team_id, payload.user_id, payload.github_handle, payload.role, db)
    except ValueError as exc:
        code = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return TeamMemberResponse(**data)


@app.delete(f"{settings.api_prefix}/teams/{{team_id}}/members/{{user_id}}", status_code=204)
async def remove_member_route(team_id: str, user_id: str, db: AsyncSession = Depends(get_db)) -> None:
    found = await remove_team_member(team_id, user_id, db)
    if not found:
        raise HTTPException(status_code=404, detail="Member not found")


# ---------------------------------------------------------------------------

@app.get(f"{settings.api_prefix}/insights/synthesis", response_model=InsightResponse)
async def synthesis() -> InsightResponse:
    data = synthesis_from_compat(total_score=28.7, weak_dimensions=["vashya_influence"])
    return InsightResponse(**data)


# ---------------------------------------------------------------------------
# WebSocket — LangGraph streaming
# ---------------------------------------------------------------------------

@app.websocket("/ws/analysis/{run_id}")
async def analysis_stream(websocket: WebSocket, run_id: str, db: AsyncSession = Depends(get_db)) -> None:
    await websocket.accept()

    # Load run from DB; fall back to defaults if not found
    run = await get_agent_run(run_id, db=db)
    if run is not None:
        team_id = run.team_id
        user_id = run.user_id
        include_candidates = run.include_candidates
    else:
        team_id, user_id, include_candidates = "team_alpha", "user_local", False

    steps = start_orchestrator_steps(include_candidates)
    try:
        completed_count = 0
        await websocket.send_json(
            jsonable_encoder({
                "run_id": run_id,
                "step": steps[0],
                "status": "running",
                "progress_pct": 0,
                "message": f"Starting {steps[0]}",
                "timestamp": datetime.now(tz=UTC).isoformat(),
            })
        )

        async for step_update in stream_orchestrator_updates(
            team_id=team_id,
            user_id=user_id,
            include_candidates=include_candidates,
        ):
            step_name, step_data = next(iter(step_update.items()))
            completed_count += 1
            progress_pct = int((completed_count / len(steps)) * 100)

            await websocket.send_json(
                jsonable_encoder({
                    "run_id": run_id,
                    "step": step_name,
                    "status": "completed",
                    "progress_pct": progress_pct,
                    "message": f"{step_name} completed",
                    "data": step_data,
                    "timestamp": datetime.now(tz=UTC).isoformat(),
                })
            )

            if completed_count < len(steps):
                next_step = steps[completed_count]
                await websocket.send_json(
                    jsonable_encoder({
                        "run_id": run_id,
                        "step": next_step,
                        "status": "running",
                        "progress_pct": progress_pct,
                        "message": f"Running {next_step}",
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                    })
                )

        await websocket.send_json(
            jsonable_encoder({
                "run_id": run_id,
                "step": "orchestration",
                "status": "completed",
                "progress_pct": 100,
                "message": "LangGraph orchestration completed",
                "timestamp": datetime.now(tz=UTC).isoformat(),
            })
        )
        await websocket.close()
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await websocket.send_json(
            jsonable_encoder({
                "run_id": run_id,
                "step": "orchestration",
                "status": "error",
                "progress_pct": 0,
                "message": f"Orchestration failed: {exc}",
                "timestamp": datetime.now(tz=UTC).isoformat(),
            })
        )
        await websocket.close(code=1011)

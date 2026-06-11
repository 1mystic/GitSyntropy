"""Seed a LOCAL demo population so the reciprocal-recommendation panel has data to show.

The recommender needs several users with completed assessments before it can return matches. A
fresh local SQLite DB only has your own user, so this script inserts ~10 synthetic assessed users
(and, optionally, completes the seeker's own assessment) purely for local demoing.

SAFETY - local only, never touches the deployed instance or real auth:
  * Refuses to run unless the configured database is SQLite (aborts on a Supabase/Postgres URL).
  * All demo users use the `seed_demo_` user_id prefix and fake handles; they cannot collide with
    real GitHub-authenticated accounts.
  * No OAuth tokens are written; these rows are inert w.r.t. GitHub auth.
  * `--clear` removes ONLY the `seed_demo_` rows, leaving your real/seeker data untouched.

Usage (from the backend dir):
  uv run python ../../scripts/seed_demo.py                 # seed 10 demo users + seeker profile
  uv run python ../../scripts/seed_demo.py --users 15      # seed 15
  uv run python ../../scripts/seed_demo.py --no-seeker     # don't create the seeker's own profile
  uv run python ../../scripts/seed_demo.py --clear         # remove all seed_demo_* rows
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

THIS = Path(__file__).resolve()
BACKEND = THIS.parents[1] / "apps" / "backend"
if (BACKEND / "app").exists():
    sys.path.insert(0, str(BACKEND))

from sqlalchemy import delete, select  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.models import AgentRun, PsychometricProfile, Team, TeamMember, TeamScore, UserProfile  # noqa: E402
from app.services import (  # noqa: E402
    add_team_member,
    compatibility,
    create_team,
    get_real_scores_for_user,
    save_team_score,
    submit_assessment_response,
    synthesis_from_compat,
    upsert_user_profile,
)

SEED_PREFIX = "seed_demo_"
DEFAULT_SEEKER = "user_1mystic"  # the local-login superadmin user_id
DEMO_TEAM_NAME = "Demo Squad (seed)"  # only seeded teams use this exact name

_FIRST = ["alex", "priya", "sam", "ravi", "mei", "omar", "lena", "diego", "aisha", "noah",
          "yuki", "tara", "ivan", "zoe", "kabir"]
_LAST = ["chen", "patel", "kim", "silva", "ahmed", "novak", "khan", "ortiz", "haas", "rao"]


def _guard_local() -> None:
    url = settings.database_url
    if not url.startswith("sqlite"):
        print(f"ABORT: database_url is '{url}'.\n"
              "This script is local-only and refuses to seed a non-SQLite database "
              "(it must never touch your deployed Supabase instance). "
              "Unset GS_DATABASE_URL to use the default local SQLite file.")
        raise SystemExit(2)
    print(f"Local DB OK: {url}")


async def _ensure_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _random_answers(rng: random.Random) -> dict[str, int]:
    # Varied profiles so recommendations are non-trivial: bias each user toward a random "type".
    centre = rng.choice([2, 3, 4])
    return {f"q{i}": min(5, max(1, centre + rng.randint(-1, 1))) for i in range(1, 9)}


async def _seed_agent_run(db, team_id: str, seeker_id: str) -> bool:
    """Insert one completed orchestrator run with per-node trace events.

    Lets the Admin -> Agent Trace View show data immediately, without the user having to run a
    live analysis first. Idempotent: skips if a run already exists for the team.
    """
    existing = await db.execute(select(AgentRun).where(AgentRun.team_id == team_id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return False

    nodes = [
        ("github_analyst", "Analysed GitHub commit/PR signals + chronotype", 1820),
        ("psychometric_profiler", "Loaded psychometric profiles for all members", 640),
        ("compatibility_engine", "Scored 8 weighted dimensions across the team", 2470),
        ("synthesis", "Generated team-health narrative + recommendations", 3310),
        ("orchestration", "Run complete", 120),
    ]
    base = datetime.now(timezone.utc) - timedelta(seconds=10)
    t = base
    events = []
    for i, (step, msg, dur) in enumerate(nodes):
        events.append({
            "type": "step",
            "step": step,
            "status": "completed",
            "progress_pct": round((i + 1) / len(nodes) * 100),
            "message": msg,
            "timestamp": t.isoformat(),
            "duration_ms": dur,
        })
        t = t + timedelta(milliseconds=dur + 180)

    db.add(AgentRun(
        id=str(uuid4()),
        team_id=team_id,
        user_id=seeker_id,
        include_candidates=False,
        status="completed",
        error=None,
        agent_events=events,
        started_at=base,
        completed_at=t,
    ))
    await db.commit()
    return True


async def seed(n_users: int, include_seeker: bool, seeker_id: str) -> None:
    rng = random.Random(42)
    async with AsyncSessionLocal() as db:
        handles: dict[str, str] = {}
        for i in range(n_users):
            uid = f"{SEED_PREFIX}{i:02d}"
            handle = f"{rng.choice(_FIRST)}_{rng.choice(_LAST)}{i:02d}"
            handles[uid] = handle
            await upsert_user_profile(
                user_id=uid,
                github_handle=handle,
                github_name=handle.replace("_", " ").title(),
                github_email=f"{handle}@example.local",
                github_avatar_url=None,
                github_access_token=None,  # inert w.r.t. GitHub auth
                db=db,
            )
            await submit_assessment_response(uid, _random_answers(rng), db)
        print(f"Seeded {n_users} demo users (complete assessments).")

        if include_seeker:
            res = await db.execute(
                select(PsychometricProfile).where(PsychometricProfile.user_id == seeker_id)
            )
            prof = res.scalar_one_or_none()
            if prof and prof.complete:
                print(f"Seeker '{seeker_id}' already has a completed assessment - left untouched.")
            else:
                await submit_assessment_response(seeker_id, _random_answers(rng), db)
                print(f"Created a demo assessment for seeker '{seeker_id}'.")

        # Build a demo team owned by the seeker so the dashboard (teams / pairs / hire-sim /
        # insights) populates with seeded data - not just the recommendation pool.
        team_res = await db.execute(
            select(Team).where(Team.name == DEMO_TEAM_NAME, Team.created_by == seeker_id)
        )
        team = team_res.scalar_one_or_none()
        if team is None:
            team_dict = await create_team(
                DEMO_TEAM_NAME, "Seeded demo team for local testing.", seeker_id, db
            )
            team_id = team_dict["id"]
            print(f"Created team '{DEMO_TEAM_NAME}' (owner: {seeker_id}).")
        else:
            team_id = team.id
            print(f"Reusing existing team '{DEMO_TEAM_NAME}'.")

        member_ids = [f"{SEED_PREFIX}{i:02d}" for i in range(min(5, n_users))]
        added = 0
        for uid in member_ids:
            try:
                await add_team_member(team_id, uid, handles.get(uid), "member", db)
                added += 1
            except ValueError:
                pass  # already a member (idempotent re-run)
        print(f"Added {added} member(s) to the team (plus the owner).")

        # Generate one real compatibility report so Insights / Recent Reports show seeded data.
        if member_ids:
            a = await get_real_scores_for_user(seeker_id, "full", db)
            b = await get_real_scores_for_user(member_ids[0], "full", db)
            compat = compatibility(a, b)
            syn = synthesis_from_compat(compat["total_score_36"], compat["weak_dimensions"])
            await save_team_score(team_id, syn["run_id"], compat, syn["narrative"], db)
            print(f"Saved a demo report ({compat['score_pct_100']:.0f}% / "
                  f"{compat['total_score_36']:.1f}/36).")

        # Seed one completed agent run so the Admin -> Agent Trace View has data immediately.
        if await _seed_agent_run(db, team_id, seeker_id):
            print("Seeded a completed agent run (visible in Admin -> Agent Trace View).")
        else:
            print("Agent run already exists for the team - left untouched.")

    print("\nDone. Reload the app and select 'Demo Squad (seed)' in the team picker. You'll see:\n"
          "  * Compatibility page -> pairwise scores + the Recommended-teammates panel (Find matches)\n"
          "  * Insights / Recent Reports -> the seeded report\n"
          "  * Admin Panel -> Agent Trace View -> the seeded run with per-node timings\n"
          "  * Dashboard -> Hire Simulation card appears AFTER you click 'Run Analysis' (it needs a\n"
          "    live compatibility result in the page state); then click 'Run Hire Sim'.")


async def clear() -> None:
    async with AsyncSessionLocal() as db:
        # Remove the seeded demo team(s) (only those with the exact seed name) + their
        # members and reports - leaves any real teams (e.g. "Team Alpha", "test") untouched.
        team_res = await db.execute(select(Team).where(Team.name == DEMO_TEAM_NAME))
        demo_team_ids = [t.id for t in team_res.scalars().all()]
        teams_removed = 0
        for tid in demo_team_ids:
            await db.execute(delete(TeamScore).where(TeamScore.team_id == tid))
            await db.execute(delete(AgentRun).where(AgentRun.team_id == tid))
            await db.execute(delete(TeamMember).where(TeamMember.team_id == tid))
            await db.execute(delete(Team).where(Team.id == tid))
            teams_removed += 1

        r1 = await db.execute(
            delete(PsychometricProfile).where(PsychometricProfile.user_id.like(f"{SEED_PREFIX}%"))
        )
        r2 = await db.execute(
            delete(UserProfile).where(UserProfile.user_id.like(f"{SEED_PREFIX}%"))
        )
        await db.commit()
        print(f"Removed: {teams_removed} demo team(s), {r1.rowcount} profiles, {r2.rowcount} users. "
              "Real teams/reports and the seeker account are untouched.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed a local-only demo population for GitSyntropy.")
    ap.add_argument("--users", type=int, default=10, help="number of demo users to create")
    ap.add_argument("--seeker", default=DEFAULT_SEEKER, help="user_id to give a profile so recs work after login")
    ap.add_argument("--no-seeker", action="store_true", help="do not create the seeker's own profile")
    ap.add_argument("--clear", action="store_true", help="remove all seed_demo_* rows and exit")
    args = ap.parse_args()

    _guard_local()

    async def _run():
        await _ensure_tables()
        if args.clear:
            await clear()
        else:
            await seed(args.users, include_seeker=not args.no_seeker, seeker_id=args.seeker)

    asyncio.run(_run())


if __name__ == "__main__":
    main()

"""Claude Synthesis Client — real Anthropic API with streaming.

Generates narrative team health reports from compatibility + GitHub + assessment signals.
Streams text token-by-token via async generator so the WebSocket can forward each chunk.
"""

from collections.abc import AsyncGenerator
from typing import Any

import anthropic

from .config import settings
from .schemas import ASHTAKOOT_WEIGHTS


_SYSTEM_PROMPT = """You are GitSyntropy's synthesis engine. You analyze engineering team
composition using the Vedic Ashtakoot framework adapted for modern software teams.

The 8 dimensions (with max points) are:
- Nadi / Chronotype Sync (8 pts): overlap in peak productive hours
- Bhakoot / Stress Response (7 pts): how team members handle pressure
- Gana / Risk Tolerance (6 pts): bold vs cautious decision-making alignment
- Graha Maitri / Decision Framework (5 pts): data-driven vs intuition alignment
- Yoni / Conflict Resolution (4 pts): how disagreements are handled
- Maitri / Social Compatibility (3 pts): communication style fit
- Vashya / Leadership Orientation (2 pts): authority and influence patterns
- Varna / Innovation Drive (1 pt): creative vs stability orientation
Total: 36 points. Score >28 = excellent, 18–28 = workable, <18 = high friction.

Write in a direct, data-informed tone. Be specific about which dimensions drive the score.
Avoid generic advice. Ground every recommendation in the data provided."""


def _build_synthesis_prompt(
    compatibility: dict[str, Any],
    github_signals: dict[str, Any] | None = None,
    assessment_profile: dict[str, Any] | None = None,
    team_size: int = 2,
) -> str:
    total = compatibility.get("total_score_36", 0)
    pct = compatibility.get("score_pct_100", 0)
    level = compatibility.get("level", "fair")
    weak = compatibility.get("weak_dimensions", [])
    strong = compatibility.get("strong_dimensions", [])
    risk_flags = compatibility.get("risk_flags", [])
    dim_scores = compatibility.get("dimension_scores", {})
    confidence = compatibility.get("confidence", 0.5)

    dim_lines = []
    for dim, score in dim_scores.items():
        max_w = ASHTAKOOT_WEIGHTS.get(dim, 1)
        pct_dim = round(score / max_w * 100) if max_w else 0
        dim_lines.append(f"  {dim}: {score:.1f}/{max_w:.0f} ({pct_dim}%)")

    github_section = ""
    if github_signals:
        chrono = github_signals.get("chronotype", "unknown")
        commits = github_signals.get("commits_last_30_days", 0)
        collab = github_signals.get("collaboration_index", 0)
        github_section = f"""
GitHub behavioral signals:
  Chronotype: {chrono}
  Commits (30d): {commits}
  Collaboration index: {collab}/100"""

    assessment_section = ""
    if assessment_profile and assessment_profile.get("complete"):
        answered = assessment_profile.get("answered_count", 0)
        assessment_section = f"""
Psychometric assessment: {answered}/8 questions answered (complete)"""

    risk_section = ""
    if risk_flags:
        risk_section = "\nRisk flags detected:\n" + "\n".join(f"  - {r}" for r in risk_flags)

    return f"""Analyze this team composition data and write a concise team health report.

Team size: {team_size} members
Overall Ashtakoot score: {total:.1f}/36 ({pct:.0f}%) — {level.upper()}
Data confidence: {confidence:.0%}

Dimension breakdown:
{chr(10).join(dim_lines)}

Weak dimensions: {', '.join(weak) if weak else 'none'}
Strong dimensions: {', '.join(strong) if strong else 'none'}
{github_section}{assessment_section}{risk_section}

Write a team health report with these sections (use markdown headers):
## Team Alignment Summary
2-3 sentences on the overall score and what it means for this team's ability to ship.

## Key Strengths
Bullet points for the 2-3 strongest alignment areas with practical implications.

## Friction Risks
Bullet points for weak dimensions with specific, actionable mitigations (not generic advice).

## Recommended Meeting Windows
Based on chronotype data (or lack thereof), suggest 2 concrete meeting time slots with reasoning.

## Hiring Gap Analysis
What psychometric profile would most improve this team's composite score? Be specific about which dimensions need complementing.

Keep the total report under 400 words. Be direct and specific."""


async def stream_synthesis(
    compatibility: dict[str, Any],
    github_signals: dict[str, Any] | None = None,
    assessment_profile: dict[str, Any] | None = None,
    team_size: int = 2,
) -> AsyncGenerator[str, None]:
    """Yield synthesis text token by token from Claude API.

    Usage:
        async for token in stream_synthesis(compat_data, github_data):
            await websocket.send_json({"type": "synthesis_token", "token": token})
    """
    if not settings.anthropic_api_key:
        # Fallback if key not configured
        yield _fallback_synthesis(compatibility)
        return

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    prompt = _build_synthesis_prompt(compatibility, github_signals, assessment_profile, team_size)

    async with client.messages.stream(
        model=settings.anthropic_model,
        max_tokens=600,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def generate_synthesis(
    compatibility: dict[str, Any],
    github_signals: dict[str, Any] | None = None,
    assessment_profile: dict[str, Any] | None = None,
    team_size: int = 2,
) -> str:
    """Non-streaming version — returns full synthesis text at once."""
    parts = []
    async for token in stream_synthesis(compatibility, github_signals, assessment_profile, team_size):
        parts.append(token)
    return "".join(parts)


def _fallback_synthesis(compatibility: dict[str, Any]) -> str:
    """Template synthesis used when Anthropic API key is not configured."""
    total = compatibility.get("total_score_36", 0)
    weak = compatibility.get("weak_dimensions", [])

    if total >= 28:
        verdict = "The team alignment is strong for delivery-critical work."
    elif total < 18:
        verdict = "The team has notable friction risks in execution and planning cadence."
    else:
        verdict = "The team is workable but needs intentional alignment rituals."

    weak_text = f"Weak dimensions: {', '.join(weak[:3])}." if weak else "No critical weak dimensions detected."
    return f"{verdict} {weak_text}"

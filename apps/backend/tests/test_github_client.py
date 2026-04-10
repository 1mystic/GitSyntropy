"""Tests for github_client.py — chronotype detection and GitHubAnalystClient."""

import asyncio
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.github_client import (
    GitHubAnalystClient,
    _classify_peak_hour,
    _hour_to_circular,
    detect_chronotype,
)


# ---------------------------------------------------------------------------
# Unit tests — _hour_to_circular
# ---------------------------------------------------------------------------


def test_hour_to_circular_midnight() -> None:
    cos_v, sin_v = _hour_to_circular(0)
    assert abs(cos_v - 1.0) < 1e-9
    assert abs(sin_v) < 1e-9


def test_hour_to_circular_noon() -> None:
    cos_v, sin_v = _hour_to_circular(12)
    assert abs(cos_v - (-1.0)) < 1e-6
    assert abs(sin_v) < 1e-6


def test_hour_to_circular_six_am() -> None:
    cos_v, sin_v = _hour_to_circular(6)
    assert abs(cos_v) < 1e-6
    assert abs(sin_v - 1.0) < 1e-6


def test_hour_to_circular_returns_tuple() -> None:
    result = _hour_to_circular(8)
    assert len(result) == 2
    cos_v, sin_v = result
    # Should lie on the unit circle
    assert abs(cos_v ** 2 + sin_v ** 2 - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Unit tests — _classify_peak_hour
# ---------------------------------------------------------------------------


def test_classify_lark() -> None:
    assert _classify_peak_hour(6) == "lark"
    assert _classify_peak_hour(10) == "lark"


def test_classify_daytime() -> None:
    assert _classify_peak_hour(11) == "daytime"
    assert _classify_peak_hour(14) == "daytime"
    assert _classify_peak_hour(18) == "daytime"


def test_classify_evening() -> None:
    assert _classify_peak_hour(19) == "evening"
    assert _classify_peak_hour(22) == "evening"


def test_classify_owl() -> None:
    assert _classify_peak_hour(23) == "owl"
    assert _classify_peak_hour(2) == "owl"
    assert _classify_peak_hour(4) == "owl"


# ---------------------------------------------------------------------------
# Unit tests — detect_chronotype
# ---------------------------------------------------------------------------


def test_detect_chronotype_empty_input() -> None:
    result = detect_chronotype([])
    assert result["chronotype"] == "flexible"
    assert result["peak_hour"] == 12.0
    assert result["confidence"] == 0.0
    assert len(result["histogram"]) == 24


def test_detect_chronotype_small_sample() -> None:
    """Fewer than 10 commits → uses histogram peak, confidence = 0.4."""
    result = detect_chronotype([9, 9, 9, 8])  # morning commits
    assert result["confidence"] == 0.4
    assert result["chronotype"] == "lark"


def test_detect_chronotype_lark_cluster() -> None:
    """Many morning commits → lark chronotype."""
    hours = [8, 8, 9, 9, 9, 10, 10, 8, 9, 7, 9, 8, 8, 9, 10]
    result = detect_chronotype(hours)
    assert result["chronotype"] in {"lark", "daytime"}
    assert 0 < result["confidence"] <= 1.0
    assert len(result["histogram"]) == 24


def test_detect_chronotype_owl_cluster() -> None:
    """Night commits → owl chronotype."""
    hours = [23, 23, 0, 1, 23, 22, 23, 0, 1, 23, 23, 22, 0, 1, 2]
    result = detect_chronotype(hours)
    assert result["chronotype"] in {"owl", "evening"}


def test_detect_chronotype_uniform_distribution() -> None:
    """Uniformly spread commits → flexible (high entropy)."""
    hours = list(range(24)) * 5  # exactly uniform
    result = detect_chronotype(hours)
    assert result["chronotype"] == "flexible"


def test_detect_chronotype_histogram_sums_to_one() -> None:
    hours = [9, 9, 10, 10, 14, 14, 14, 14, 14, 15, 22, 22, 22]
    result = detect_chronotype(hours)
    assert abs(sum(result["histogram"]) - 1.0) < 1e-4  # rounding to 4 decimal places


def test_detect_chronotype_histogram_length() -> None:
    result = detect_chronotype([9] * 20)
    assert len(result["histogram"]) == 24


# ---------------------------------------------------------------------------
# Unit tests — GitHubAnalystClient (mocked PyGithub)
# ---------------------------------------------------------------------------


def _make_mock_commit(hour: int):
    """Build a minimal mock commit object."""
    from datetime import UTC, datetime
    commit = MagicMock()
    commit.commit.author.date = datetime(2025, 1, 15, hour, 0, tzinfo=UTC)
    return commit


def _make_mock_repo(commits=(), prs=(), review_comments=()):
    from datetime import UTC, datetime
    repo = MagicMock()
    repo.pushed_at = datetime(2025, 3, 1, tzinfo=UTC)
    repo.get_commits.return_value = list(commits)
    repo.get_pulls.return_value = list(prs)
    repo.get_pulls_review_comments.return_value = list(review_comments)
    return repo


@pytest.fixture()
def mock_gh_user():
    user = MagicMock()
    user.login = "testuser"
    repo = _make_mock_repo(
        commits=[_make_mock_commit(9), _make_mock_commit(10), _make_mock_commit(9)],
    )
    user.get_repos.return_value = [repo]
    return user


def test_client_init() -> None:
    with patch("app.github_client.Github"), patch("app.github_client.Auth"):
        client = GitHubAnalystClient("fake-token")
        assert client._gh is not None


@pytest.mark.asyncio
async def test_fetch_user_commit_hours_returns_list(mock_gh_user) -> None:
    with patch("app.github_client.Github") as MockGh, patch("app.github_client.Auth"):
        MockGh.return_value.get_user.return_value = mock_gh_user
        client = GitHubAnalystClient("fake-token")
        hours = await client.fetch_user_commit_hours("testuser", days=30)
        assert isinstance(hours, list)
        assert all(isinstance(h, int) for h in hours)


@pytest.mark.asyncio
async def test_fetch_pr_metrics_returns_dict(mock_gh_user) -> None:
    from datetime import UTC, datetime

    pr = MagicMock()
    pr.created_at = datetime(2025, 3, 10, 14, 0, tzinfo=UTC)
    pr.closed_at = datetime(2025, 3, 11, 10, 0, tzinfo=UTC)
    pr.user.login = "testuser"

    repo = _make_mock_repo(prs=[pr])
    repo.pushed_at = datetime(2025, 3, 15, tzinfo=UTC)
    mock_gh_user.get_repos.return_value = [repo]

    with patch("app.github_client.Github") as MockGh, patch("app.github_client.Auth"):
        MockGh.return_value.get_user.return_value = mock_gh_user
        client = GitHubAnalystClient("fake-token")
        metrics = await client.fetch_pr_metrics("testuser", days=90)

        assert "prs_last_30_days" in metrics
        assert "avg_pr_response_hours" in metrics
        assert "async_ratio" in metrics
        assert isinstance(metrics["prs_last_30_days"], int)


@pytest.mark.asyncio
async def test_fetch_collaboration_index_returns_float(mock_gh_user) -> None:
    from datetime import UTC, datetime

    comment = MagicMock()
    comment.user.login = "testuser"
    comment.created_at = datetime(2025, 3, 10, tzinfo=UTC)
    repo = _make_mock_repo(review_comments=[comment])
    repo.pushed_at = datetime(2025, 3, 15, tzinfo=UTC)
    mock_gh_user.get_repos.return_value = [repo]

    with patch("app.github_client.Github") as MockGh, patch("app.github_client.Auth"):
        MockGh.return_value.get_user.return_value = mock_gh_user
        client = GitHubAnalystClient("fake-token")
        idx = await client.fetch_collaboration_index("testuser", days=90)
        assert 0.0 <= idx <= 100.0


@pytest.mark.asyncio
async def test_analyze_returns_full_profile(mock_gh_user) -> None:
    from datetime import UTC, datetime

    with patch("app.github_client.Github") as MockGh, patch("app.github_client.Auth"):
        MockGh.return_value.get_user.return_value = mock_gh_user
        client = GitHubAnalystClient("fake-token")
        result = await client.analyze("testuser", days=90)

        required_keys = {
            "github_handle", "chronotype", "commits_last_90_days",
            "commits_last_30_days", "activity_rhythm_score",
            "collaboration_index", "prs_last_30_days",
        }
        assert required_keys <= result.keys()
        assert result["github_handle"] == "testuser"
        assert result["chronotype"] in {"lark", "owl", "daytime", "evening", "flexible"}


@pytest.mark.asyncio
async def test_analyze_gracefully_handles_fetch_errors() -> None:
    """If any sub-fetch raises, analyze() should return fallback values."""
    from github import GithubException

    user = MagicMock()
    user.get_repos.side_effect = GithubException(403, "rate limited", None)

    with patch("app.github_client.Github") as MockGh, patch("app.github_client.Auth"):
        MockGh.return_value.get_user.return_value = user
        client = GitHubAnalystClient("fake-token")
        result = await client.analyze("erroruser", days=30)

        # Should still return a complete dict with fallbacks
        assert result["commits_last_90_days"] == 0
        assert result["prs_last_30_days"] == 0

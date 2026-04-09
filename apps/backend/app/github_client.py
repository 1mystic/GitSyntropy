"""GitHub Analyst Client — real API integration with K-Means chronotype detection.

Uses PyGithub (REST) for commit history and PR activity.
K-Means operates on circular time coordinates to handle the 0/24 boundary correctly.
Rate limit budget: 5000 pts/hr; each user analysis costs ~15-30 pts.
"""

import asyncio
import math
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from github import Auth, Github, GithubException
from sklearn.cluster import KMeans


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hour_to_circular(hour: int) -> tuple[float, float]:
    """Map hour 0–23 to a point on the unit circle (handles midnight boundary)."""
    angle = 2 * math.pi * hour / 24
    return math.cos(angle), math.sin(angle)


def _classify_peak_hour(hour: float) -> str:
    """Map a peak hour (float 0–24) to a chronotype label."""
    if 5 <= hour < 11:
        return "lark"          # early bird
    if 11 <= hour < 19:
        return "daytime"
    if 19 <= hour < 23:
        return "evening"
    return "owl"               # night owl (23–5)


def detect_chronotype(commit_hours: list[int]) -> dict[str, Any]:
    """K-Means on circular time coordinates → chronotype label + confidence.

    Returns:
        chronotype: "owl" | "lark" | "daytime" | "flexible"
        peak_hour: float (dominant cluster center, 0–24)
        confidence: float (0–1, fraction of commits in dominant cluster)
        histogram: list[float] (24-bin normalized distribution)
    """
    if not commit_hours:
        return {
            "chronotype": "flexible",
            "peak_hour": 12.0,
            "confidence": 0.0,
            "histogram": [0.0] * 24,
        }

    # Build 24-bin histogram for reference
    hist = [0] * 24
    for h in commit_hours:
        hist[h % 24] += 1
    total = len(commit_hours)
    norm_hist = [c / total for c in hist]

    # Need at least 10 commits for meaningful clustering
    if total < 10:
        peak_hour = max(range(24), key=lambda h: hist[h])
        return {
            "chronotype": _classify_peak_hour(peak_hour),
            "peak_hour": float(peak_hour),
            "confidence": 0.4,
            "histogram": norm_hist,
        }

    # Convert hours to 2D circular coordinates
    coords = np.array([_hour_to_circular(h) for h in commit_hours])

    k = min(3, len(set(commit_hours)))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(coords)

    # Find dominant cluster (most commits)
    cluster_counts = np.bincount(labels, minlength=k)
    dominant_cluster = int(np.argmax(cluster_counts))
    confidence = float(cluster_counts[dominant_cluster] / total)

    # Convert cluster center back to hour
    cx, cy = kmeans.cluster_centers_[dominant_cluster]
    angle = math.atan2(cy, cx)
    if angle < 0:
        angle += 2 * math.pi
    peak_hour = angle * 24 / (2 * math.pi)

    # Entropy check: very flat distribution → flexible
    entropy = -sum(p * math.log(p + 1e-9) for p in norm_hist)
    max_entropy = math.log(24)
    if entropy / max_entropy > 0.92:
        chronotype = "flexible"
    else:
        chronotype = _classify_peak_hour(peak_hour)

    return {
        "chronotype": chronotype,
        "peak_hour": round(peak_hour, 2),
        "confidence": round(confidence, 3),
        "histogram": [round(v, 4) for v in norm_hist],
    }


# ---------------------------------------------------------------------------
# GitHubAnalystClient
# ---------------------------------------------------------------------------

class GitHubAnalystClient:
    """Async wrapper around PyGithub (synchronous) using asyncio.to_thread."""

    def __init__(self, access_token: str) -> None:
        self._gh = Github(Auth.Token(access_token), per_page=100)

    async def _run(self, fn, *args, **kwargs):
        """Run a blocking PyGithub call in a thread."""
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def fetch_user_commit_hours(self, username: str, days: int = 90) -> list[int]:
        """Return list of commit hours (0–23) from the last `days` days."""
        since = datetime.now(tz=UTC) - timedelta(days=days)

        def _fetch():
            try:
                user = self._gh.get_user(username)
                hours = []
                for repo in user.get_repos(type="owner", sort="pushed"):
                    if repo.pushed_at and repo.pushed_at < since:
                        continue
                    try:
                        commits = repo.get_commits(author=username, since=since)
                        for commit in commits:
                            if commit.commit.author and commit.commit.author.date:
                                dt = commit.commit.author.date
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=UTC)
                                hours.append(dt.hour)
                    except GithubException:
                        continue
                return hours
            except GithubException as exc:
                raise RuntimeError(f"GitHub API error: {exc.status} {exc.data}") from exc

        return await self._run(_fetch)

    async def fetch_pr_metrics(self, username: str, days: int = 90) -> dict[str, Any]:
        """Compute PR activity metrics: count, avg response time, async ratio."""
        since = datetime.now(tz=UTC) - timedelta(days=days)

        def _fetch():
            try:
                user = self._gh.get_user(username)
                pr_count = 0
                response_times: list[float] = []
                after_hours_prs = 0

                for repo in user.get_repos(type="owner", sort="pushed"):
                    if repo.pushed_at and repo.pushed_at < since:
                        continue
                    try:
                        pulls = repo.get_pulls(state="closed", sort="updated", direction="desc")
                        for pr in pulls:
                            if pr.created_at < since:
                                break
                            if pr.user and pr.user.login == username:
                                pr_count += 1
                                if pr.closed_at and pr.created_at:
                                    hrs = (pr.closed_at - pr.created_at).total_seconds() / 3600
                                    response_times.append(hrs)
                                if pr.created_at.hour >= 20 or pr.created_at.hour < 7:
                                    after_hours_prs += 1
                    except GithubException:
                        continue

                avg_response = sum(response_times) / len(response_times) if response_times else 0.0
                async_ratio = after_hours_prs / max(pr_count, 1)
                return {
                    "prs_last_30_days": max(0, int(pr_count * 30 / days)),
                    "avg_pr_response_hours": round(avg_response, 1),
                    "async_ratio": round(async_ratio, 3),
                }
            except GithubException as exc:
                raise RuntimeError(f"GitHub API error: {exc.status}") from exc

        return await self._run(_fetch)

    async def fetch_collaboration_index(self, username: str, days: int = 90) -> float:
        """Score 0–100: reviews given + cross-repo contributions + PR comments."""
        since = datetime.now(tz=UTC) - timedelta(days=days)

        def _fetch():
            try:
                user = self._gh.get_user(username)
                score = 0
                for repo in user.get_repos(type="owner", sort="pushed"):
                    if repo.pushed_at and repo.pushed_at < since:
                        continue
                    try:
                        # Count review comments (proxy for collab)
                        for comment in repo.get_pulls_review_comments():
                            if comment.user and comment.user.login == username:
                                if comment.created_at >= since:
                                    score += 2
                    except GithubException:
                        continue
                return min(100.0, float(score))
            except GithubException:
                return 50.0

        return await self._run(_fetch)

    async def analyze(self, username: str, days: int = 90) -> dict[str, Any]:
        """Full analysis: chronotype + PR metrics + collaboration index.

        Returns a dict ready to upsert into GithubProfile.
        """
        # Run all three fetches concurrently
        commit_hours, pr_metrics, collab_index = await asyncio.gather(
            self.fetch_user_commit_hours(username, days),
            self.fetch_pr_metrics(username, days),
            self.fetch_collaboration_index(username, days),
            return_exceptions=True,
        )

        # Graceful fallback if any fetch errored
        if isinstance(commit_hours, Exception):
            commit_hours = []
        if isinstance(pr_metrics, Exception):
            pr_metrics = {"prs_last_30_days": 0, "avg_pr_response_hours": 0.0, "async_ratio": 0.0}
        if isinstance(collab_index, Exception):
            collab_index = 50.0

        chrono = detect_chronotype(commit_hours)

        return {
            "github_handle": username,
            "chronotype": chrono["chronotype"],
            "chronotype_confidence": chrono["confidence"],
            "peak_hour": chrono["peak_hour"],
            "histogram": chrono["histogram"],
            "commits_last_90_days": len(commit_hours),
            "commits_last_30_days": max(0, int(len(commit_hours) * 30 / days)),
            "activity_rhythm_score": min(100.0, round(len(commit_hours) * 1.1, 2)),
            "collaboration_index": collab_index,
            "prs_last_30_days": pr_metrics.get("prs_last_30_days", 0),
            "avg_pr_response_hours": pr_metrics.get("avg_pr_response_hours", 0.0),
            "async_ratio": pr_metrics.get("async_ratio", 0.0),
            "analyzed_days": days,
        }

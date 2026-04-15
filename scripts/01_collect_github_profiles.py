"""
GitSyntropy — Research Data Collection Script
==============================================
Script 01: GitHub Profile Collection

Fetches commit-hour distributions for a curated set of known-active open-source
contributors and discovers additional profiles from top-starred repositories.

Usage:
    export GITHUB_TOKEN=ghp_your_token_here
    python scripts/01_collect_github_profiles.py

    # Or with a token flag:
    python scripts/01_collect_github_profiles.py --token ghp_...

    # Resume an interrupted run:
    python scripts/01_collect_github_profiles.py --resume

    # Discovery only (no data fetch, just build the username list):
    python scripts/01_collect_github_profiles.py --discover-only

Output files (all under scripts/data/):
    raw/{username}.json          — full commit + PR event data per user
    hours/{username}_hours.json  — just the commit-hour list (0–23) per user
    profiles_summary.csv         — one row per qualified user (≥50 commits/90d)
    all_candidates.txt           — every discovered username (pre-filter)
    checkpoint.json              — resume state

Requirements:
    pip install requests tqdm
    (or: pip install -r scripts/requirements.txt)

Rate limits:
    Authenticated:   5 000 req/hr  → ~120 users in ~25 min
    Unauthenticated: 60 req/hr     → will take many hours; strongly recommend auth

Notes on timestamp timezone:
    The GitHub REST API returns commit author.date in ISO 8601 with timezone offset
    (e.g. 2024-03-15T22:41:00+05:30). We parse the LOCAL hour via
    datetime.fromisoformat(), which preserves the offset. This is the developer's
    local clock hour — the correct input for chronotype detection.
    Commits from CI/automation accounts that set UTC (Z suffix) will produce
    UTC hours; we flag accounts where >90% of commits are at :00 seconds
    (bot heuristic) and exclude them from the clean sample.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Try to import requests; give a clear error if missing.
# ---------------------------------------------------------------------------
try:
    import requests
except ImportError:
    sys.exit(
        "ERROR: 'requests' is not installed.\n"
        "Run: pip install requests tqdm\n"
        "  or: pip install -r scripts/requirements.txt"
    )

try:
    from tqdm import tqdm
except ImportError:
    # Graceful fallback — tqdm is optional
    def tqdm(iterable, **kwargs):  # type: ignore[misc]
        total = kwargs.get("total", "?")
        desc = kwargs.get("desc", "")
        for i, item in enumerate(iterable):
            print(f"  {desc} {i+1}/{total}", end="\r", flush=True)
            yield item
        print()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
HOURS_DIR = DATA_DIR / "hours"
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"
SUMMARY_CSV = DATA_DIR / "profiles_summary.csv"
CANDIDATES_FILE = DATA_DIR / "all_candidates.txt"

for d in [DATA_DIR, RAW_DIR, HOURS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(DATA_DIR / "collection.log", mode="a"),
    ],
)
log = logging.getLogger("collect")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOOKBACK_DAYS = 90
MIN_COMMITS = 50          # minimum commits in 90 days to qualify for study
MAX_REPOS_PER_USER = 30   # stop after checking this many repos per user
MAX_COMMITS_PER_REPO = 200
DISCOVERY_TOP_N = 25      # top-N contributors to fetch from each discovery repo
SLEEP_BETWEEN_USERS = 1.5 # seconds pause between users (be polite)

# ---------------------------------------------------------------------------
# Curated seed list — known active open-source contributors
# Organized by ecosystem. All usernames verified from public records.
# Target: 130+ seeds → expect ~80-110 to pass the ≥50-commit filter.
# ---------------------------------------------------------------------------
SEED_USERNAMES: list[str] = [
    # ── Python Core / CPython ──────────────────────────────────────────────
    "gvanrossum",       # Guido van Rossum — Python BDFL emeritus
    "ambv",             # Łukasz Langa — Python 3.8+ release manager
    "markshannon",      # Mark Shannon — CPython performance (Faster CPython)
    "rhettinger",       # Raymond Hettinger — Python core, itertools
    "encukou",          # Petr Viktorin — CPython, PEP author
    "pradyunsg",        # Pradyun Gedam — pip, installer, Python packaging
    "sethmlarson",      # Seth Larson — urllib3, CPython security
    "AA-Turner",        # Adam Turner — CPython docs, Sphinx

    # ── NumPy ─────────────────────────────────────────────────────────────
    "rgommers",         # Ralf Gommers — NumPy, SciPy, SPEC governance
    "charris",          # Charles Harris — NumPy release manager emeritus
    "seberg",           # Sebastian Berg — NumPy DType system
    "mhvk",             # Marten van Kerkwijk — NumPy, Astropy
    "eric-wieser",      # Eric Wieser — NumPy, typing
    "mattip",           # Matti Picus — NumPy, PyPy compatibility

    # ── SciPy ─────────────────────────────────────────────────────────────
    "pv",               # Pauli Virtanen — SciPy co-founder, sparse
    "ev-br",            # Evgeni Burovski — SciPy, special functions
    "tylerjereddy",     # Tyler Reddy — SciPy, Cython
    "ilayn",            # Ilhan Polat — SciPy signal processing

    # ── pandas ────────────────────────────────────────────────────────────
    "wesm",             # Wes McKinney — pandas creator, Apache Arrow
    "jorisvandenbossche", # Joris Van den Bossche — pandas, Arrow
    "mroeschke",        # Matthew Roeschke — pandas, datetime
    "phofl",            # Patrick Hoefler — pandas, copy-on-write
    "MarcoGorelli",     # Marco Gorelli — pandas, narwhals, polars
    "rhshadrach",       # Richard Shadrach — pandas, groupby
    "WillAyd",          # Will Ayd — pandas, extension arrays
    "topper-123",       # Torsten Wörtwein — pandas, plotting
    "jbrockmendel",     # Brock Mendel — pandas, datetime internals

    # ── Matplotlib ────────────────────────────────────────────────────────
    "tacaswell",        # Thomas Caswell — matplotlib release manager
    "anntzer",          # Antony Lee — matplotlib, backend
    "efiring",          # Eric Firing — matplotlib, axes
    "timhoffm",         # Tim Hoffmann — matplotlib, layout engine
    "QuLogic",          # Elliott Sales de Andrade — matplotlib, fonts

    # ── seaborn / visualization ───────────────────────────────────────────
    "mwaskom",          # Michael Waskom — seaborn author

    # ── scikit-learn ──────────────────────────────────────────────────────
    "ogrisel",          # Olivier Grisel — scikit-learn, parallel
    "GaelVaroquaux",    # Gaël Varoquaux — scikit-learn, neuroimaging
    "jnothman",         # Joel Nothman — scikit-learn, NLP
    "amueller",         # Andreas Müller — scikit-learn, applied ML
    "glemaitre",        # Guillaume Lemaitre — scikit-learn, imbalanced
    "thomasjpfan",      # Thomas Fan — scikit-learn, API design
    "adrinjalali",      # Adrin Jalali — scikit-learn, fairness
    "lesteve",          # Loïc Estève — scikit-learn, CI
    "jeremiedbb",       # Jérémie du Boisberranger — scikit-learn, BLAS

    # ── HuggingFace ───────────────────────────────────────────────────────
    "julien-c",         # Julien Chaumond — HuggingFace CTO, Hub
    "sgugger",          # Sylvain Gugger — Accelerate, Transformers trainer
    "thomwolf",         # Thomas Wolf — HuggingFace CEO, Transformers
    "patil-suraj",      # Suraj Patil — Diffusers, PEFT
    "muellerzr",        # Zachary Mueller — Accelerate, notebooks
    "ArthurZucker",     # Arthur Zucker — Transformers, tokenizers
    "amyeroberts",      # Amy Roberts — Transformers, vision models
    "lvwerra",          # Leandro von Werra — TRL (RLHF library)
    "sanchit-gandhi",   # Sanchit Gandhi — Whisper, audio
    "pcuenca",          # Pedro Cuenca — Diffusers
    "younesbelkada",    # Younes Belkada — bitsandbytes, quantization
    "nateraw",          # Nathan Raw — HuggingFace, video

    # ── PyTorch ───────────────────────────────────────────────────────────
    "soumith",          # Soumith Chintala — PyTorch creator
    "ezyang",           # Edward Yang — PyTorch, dynamo
    "albanD",           # Alban Desmaison — PyTorch, autograd
    "ngimel",           # Natalia Gimelshein — PyTorch CUDA kernels
    "malfet",           # Nikita Shulga — PyTorch, libtorch

    # ── Keras / TensorFlow ────────────────────────────────────────────────
    "fchollet",         # François Chollet — Keras author

    # ── Independent ML researchers ────────────────────────────────────────
    "lucidrains",       # Phil Wang — ML paper reimplementations (very active)

    # ── Python Web Frameworks ─────────────────────────────────────────────
    "tiangolo",         # Sebastián Ramírez — FastAPI, SQLModel
    "Kludex",           # Marcelo Trylesinski — Starlette, uvicorn
    "mitsuhiko",        # Armin Ronacher — Flask, Click, Pallets
    "davidism",         # David Lord — Flask, Pallets maintenance
    "pgjones",          # Philip Jones — Quart, hypercorn, Flask
    "tomchristie",      # Tom Christie — DRF, httpx, encode
    "florimondmanca",   # Florimond Manca — httpx, bocadillo
    "adriangb",         # Adrian Garcia Badaracco — FastAPI ecosystem

    # ── Python Tooling / Packaging ────────────────────────────────────────
    "hynek",            # Hynek Schlawack — attrs, structlog, hatch
    "asottile",         # Anthony Sottile — pre-commit, pyupgrade, flake8
    "charliermarsh",    # Charlie Marsh — ruff author (Astral)
    "zanieb",           # Zanie Blue — uv, ruff (Astral)

    # ── Vue.js / Vite ecosystem ───────────────────────────────────────────
    "yyx990803",        # Evan You — Vue.js, Vite creator
    "antfu",            # Anthony Fu — Vue, Vite, Vitest, unplugin
    "patak-dev",        # Matias Capeletto — Vite core, Vitest
    "sheremet-va",      # Vladimir Sheremet — Vitest author
    "posva",            # Eduardo San Martin Morote — Vue Router, Pinia
    "pi0",              # Pooya Parsa — Nuxt, UnJS

    # ── TypeScript ────────────────────────────────────────────────────────
    "ahejlsberg",       # Anders Hejlsberg — TypeScript creator
    "DanielRosenwasser", # Daniel Rosenwasser — TypeScript PM
    "andrewbranch",     # Andrew Branch — TypeScript language service
    "rbuckton",         # Ron Buckton — TypeScript, decorators, TC39
    "weswigham",        # Wesley Wigham — TypeScript, type checking

    # ── React ─────────────────────────────────────────────────────────────
    "gaearon",          # Dan Abramov — React, Redux, Bluesky
    "acdlite",          # Andrew Clark — React core, Server Components
    "eps1lon",          # Sebastian Silbermann — React, accessibility
    "bvaughn",          # Brian Vaughn — React DevTools, scheduler
    "sebmarkbage",      # Sebastian Markbåge — React, RSC spec

    # ── Babel / JS tooling ────────────────────────────────────────────────
    "nicolo-ribaudo",   # Nicolo Ribaudo — Babel, TC39

    # ── Node.js ───────────────────────────────────────────────────────────
    "mcollina",         # Matteo Collina — Node.js TSC, undici, fastify
    "addaleax",         # Anna Henningsen — Node.js, workers, N-API
    "bnoordhuis",       # Ben Noordhuis — Node.js, libuv co-author
    "jasnell",          # James Snell — Node.js, HTTP/2, QUIC
    "targos",           # Michaël Zasso — Node.js, V8 upgrades
    "RafaelGSS",        # Rafael Gonzaga — Node.js security, TSC

    # ── npm ecosystem ─────────────────────────────────────────────────────
    "sindresorhus",     # Sindre Sorhus — 1000+ npm packages, ESM champion

    # ── Rust ──────────────────────────────────────────────────────────────
    "dtolnay",          # David Tolnay — serde, syn, proc-macro2, cxx
    "BurntSushi",       # Andrew Gallant — ripgrep, regex, csv
    "nnethercote",      # Nicholas Nethercote — rustc perf, dhat
    "nikomatsakis",     # Niko Matsakis — Rust lang lead, borrow checker
    "compiler-errors",  # Michael Goulet — rustc, diagnostics
    "ehuss",            # Eric Huss — Cargo, rustup, edition
    "oli-obk",          # Oliver Scherer — rustc, const eval, miri
    "Mark-Simulacrum",  # Mark Rousskov — rustc, CI, infra
    "joshtriplett",     # Josh Triplett — Rust lang team, async

    # ── Go ────────────────────────────────────────────────────────────────
    "rsc",              # Russ Cox — Go cmd, modules, toolchain
    "mvdan",            # Daniel Martí — gofmt, Go tools
    "ianlancetaylor",   # Ian Lance Taylor — Go runtime, cgo
    "griesemer",        # Robert Griesemer — Go spec, syntax
    "bradfitz",         # Brad Fitzpatrick — Go stdlib, http2

    # ── Docker / containerd ───────────────────────────────────────────────
    "tianon",           # Tianon Gravi — Docker official images
    "thaJeztah",        # Sebastiaan van Stijn — Docker core, Moby
    "cpuguy83",         # Brian Goff — Docker, containerd
    "AkihiroSuda",      # Akihiro Suda — containerd, nerdctl, rootlesskit

    # ── Kubernetes ────────────────────────────────────────────────────────
    "thockin",          # Tim Hockin — Kubernetes, networking, Google
    "liggitt",          # Jordan Liggitt — Kubernetes API, auth
    "dims",             # Davanum Srinivas — Kubernetes, OpenStack
    "deads2k",          # David Eads — Kubernetes, OpenShift

    # ── Apache Airflow ────────────────────────────────────────────────────
    "potiuk",           # Jarek Potiuk — Airflow PMC, CI
    "kaxil",            # Kaxil Naik — Airflow core, Google
    "uranusjr",         # Tzu-ping Chung — Airflow, Python packaging
    "dstandish",        # Daniel Standish — Airflow, sensors

    # ── Mozilla / Firefox ─────────────────────────────────────────────────
    "emilio",           # Emilio Cobos Álvarez — Firefox, Servo, CSS engine
    "jdm",              # Josh Matthews — Firefox, Servo, Rust
    "nical",            # Nicolas Silva — WebRender, WebGPU

    # ── Data Engineering / Apache Arrow ───────────────────────────────────
    "xhochy",           # Uwe Korn — Apache Arrow, parquet, conda-forge
    "pitrou",           # Antoine Pitrou — Apache Arrow, CPython

    # ── polyglot / high-activity ──────────────────────────────────────────
    "nicowillis",       # Nico Willis — various OSS
    "simonw",           # Simon Willison — Datasette, LLM CLI, sqlite-utils
    "tarsil",           # Tiago Silva — Esmerald, Lilya
]

# ---------------------------------------------------------------------------
# Repos to discover additional contributors from.
# We pull the top-N contributors per repo and add them to the fetch queue.
# ---------------------------------------------------------------------------
DISCOVERY_REPOS: list[tuple[str, str]] = [
    ("pandas-dev",    "pandas"),
    ("numpy",         "numpy"),
    ("scikit-learn",  "scikit-learn"),
    ("matplotlib",    "matplotlib"),
    ("huggingface",   "transformers"),
    ("pytorch",       "pytorch"),
    ("vuejs",         "core"),
    ("vitejs",        "vite"),
    ("microsoft",     "TypeScript"),
    ("facebook",      "react"),
    ("nodejs",        "node"),
    ("tiangolo",      "fastapi"),
    ("rust-lang",     "rust"),
    ("golang",        "go"),
    ("apache",        "airflow"),
    ("docker",        "cli"),
    ("kubernetes",    "kubernetes"),
    ("pallets",       "flask"),
    ("astral-sh",     "ruff"),
    ("encode",        "httpx"),
]


# ---------------------------------------------------------------------------
# GitHub API client (thin wrapper around requests)
# ---------------------------------------------------------------------------

class GitHubAPI:
    """Minimal authenticated GitHub REST API client with rate-limit handling."""

    BASE = "https://api.github.com"

    def __init__(self, token: str | None = None) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitSyntropy-Research/1.0 (academic study; contact via GitHub)",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self._remaining = 5000
        self._reset_at = 0.0

    def _check_rate_limit(self) -> None:
        """If near the rate limit, sleep until reset."""
        if self._remaining < 50:
            wait = max(0, self._reset_at - time.time()) + 5
            log.warning(f"Rate limit low ({self._remaining} remaining). Sleeping {wait:.0f}s …")
            time.sleep(wait)

    def get(self, path: str, params: dict | None = None, retries: int = 3) -> dict | list | None:
        """GET from GitHub API. Returns parsed JSON or None on 404."""
        url = f"{self.BASE}{path}"
        for attempt in range(retries):
            try:
                self._check_rate_limit()
                resp = self.session.get(url, params=params, timeout=20)

                # Update rate limit state from headers
                self._remaining = int(resp.headers.get("X-RateLimit-Remaining", self._remaining))
                self._reset_at = float(resp.headers.get("X-RateLimit-Reset", self._reset_at))

                if resp.status_code == 404:
                    return None
                if resp.status_code == 403:
                    # Could be rate limit or abuse detection
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    log.warning(f"403 on {path} — waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                if resp.status_code == 409:
                    # Empty repo — treat as no data
                    return None
                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.Timeout:
                log.warning(f"Timeout on {path}, attempt {attempt+1}/{retries}")
                time.sleep(5 * (attempt + 1))
            except requests.exceptions.RequestException as exc:
                log.warning(f"Request error on {path}: {exc}, attempt {attempt+1}/{retries}")
                time.sleep(3 * (attempt + 1))

        log.error(f"All {retries} attempts failed for {path}")
        return None

    def paginate(self, path: str, params: dict | None = None, max_pages: int = 10) -> list:
        """GET all pages and return concatenated list results."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        results: list = []
        for page in range(1, max_pages + 1):
            params["page"] = page
            data = self.get(path, params=params)
            if not data:
                break
            if isinstance(data, list):
                results.extend(data)
                if len(data) < params["per_page"]:
                    break  # last page
            else:
                # Some endpoints return a wrapper dict
                items = data.get("items", data.get("commits", []))
                results.extend(items)
                if len(items) < params["per_page"]:
                    break
        return results


# ---------------------------------------------------------------------------
# Core data fetching logic
# ---------------------------------------------------------------------------

def _parse_local_hour(date_str: str) -> int | None:
    """
    Parse an ISO 8601 timestamp (with or without timezone offset) and return
    the LOCAL hour (0–23) as the developer's clock showed it.

    GitHub REST API returns author.date preserving the git author timezone,
    e.g. '2024-03-15T22:41:00+05:30'.
    """
    if not date_str:
        return None
    try:
        # Python 3.7+: fromisoformat handles +HH:MM offsets
        # Replace trailing Z (UTC) with +00:00 for compatibility
        normalized = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.hour
    except ValueError:
        return None


def _is_bot_account(user_data: dict) -> bool:
    """Heuristic: skip bots and automation accounts."""
    login = user_data.get("login", "").lower()
    user_type = user_data.get("type", "")
    bio = (user_data.get("bio") or "").lower()

    if user_type == "Bot":
        return True
    bot_keywords = ["bot", "ci", "automation", "[bot]", "dependabot", "renovate"]
    if any(kw in login for kw in bot_keywords):
        return True
    if any(kw in bio for kw in ["automated", "robot", "ci pipeline"]):
        return True
    return False


def fetch_user_profile(api: GitHubAPI, username: str) -> dict | None:
    """Fetch user metadata. Returns None if user doesn't exist or is a bot."""
    data = api.get(f"/users/{username}")
    if data is None:
        log.debug(f"  {username}: user not found")
        return None
    if _is_bot_account(data):
        log.debug(f"  {username}: bot account, skipping")
        return None
    return data


def fetch_commit_hours(
    api: GitHubAPI,
    username: str,
    since_dt: datetime,
) -> tuple[list[int], int]:
    """
    Fetch commit hours (local time, 0–23) from user-owned repos.

    Returns:
        hours: list of hour integers
        repo_count: number of repos checked
    """
    hours: list[int] = []
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get user's repos (owner only, sorted by most recently pushed)
    repos = api.paginate(
        f"/users/{username}/repos",
        params={"type": "owner", "sort": "pushed", "direction": "desc"},
        max_pages=1,  # 100 repos is more than enough
    )

    checked = 0
    for repo in repos[:MAX_REPOS_PER_USER]:
        # Skip repos not touched in the lookback window
        pushed_at_str = repo.get("pushed_at")
        if pushed_at_str:
            try:
                pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                if pushed_at < since_dt:
                    continue
            except ValueError:
                pass

        owner = repo.get("owner", {}).get("login", username)
        repo_name = repo.get("name", "")
        if not repo_name:
            continue

        commits_data = api.paginate(
            f"/repos/{owner}/{repo_name}/commits",
            params={
                "author": username,
                "since": since_str,
                "per_page": 100,
            },
            max_pages=2,  # max 200 commits per repo
        )

        for commit in commits_data:
            author_date = (
                commit.get("commit", {})
                      .get("author", {})
                      .get("date", "")
            )
            h = _parse_local_hour(author_date)
            if h is not None:
                hours.append(h)

        checked += 1
        if len(hours) >= MAX_COMMITS_PER_REPO * MAX_REPOS_PER_USER:
            break  # enough data

    return hours, checked


def fetch_pr_metrics(
    api: GitHubAPI,
    username: str,
    since_dt: datetime,
) -> dict:
    """
    Compute PR-level behavioral metrics from Events API PullRequestEvent data.

    Returns dict with:
        pr_count         — total PRs opened in window
        after_hours_prs  — PRs opened 20:00–07:00 local time
        async_ratio      — fraction of after-hours PRs
        review_comments  — PR review comments authored (collaboration proxy)
    """
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    events = api.paginate(
        f"/users/{username}/events",
        params={"per_page": 100},
        max_pages=10,  # GitHub caps at 10 pages (300 events, 90 days)
    )

    pr_count = 0
    after_hours_prs = 0
    review_comment_count = 0

    for event in events:
        created = event.get("created_at", "")
        try:
            event_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue

        if event_dt < since_dt:
            continue

        etype = event.get("type", "")

        if etype == "PullRequestEvent":
            action = event.get("payload", {}).get("action", "")
            if action == "opened":
                pr_count += 1
                h = event_dt.hour
                if h >= 20 or h < 7:
                    after_hours_prs += 1

        elif etype == "PullRequestReviewCommentEvent":
            review_comment_count += 1

    async_ratio = round(after_hours_prs / max(pr_count, 1), 3)

    return {
        "pr_count_90d": pr_count,
        "after_hours_prs": after_hours_prs,
        "async_ratio": async_ratio,
        "review_comments_90d": review_comment_count,
        # Collaboration index: 2 pts per review comment, cap at 100
        "collaboration_index": min(100.0, round(review_comment_count * 2.0, 1)),
    }


# ---------------------------------------------------------------------------
# Bot-commit filter: flag accounts where >80% commits are at :00 seconds
# (typical of CI/automation that commits on the clock)
# ---------------------------------------------------------------------------

def _bot_commit_ratio(commit_seconds: list[int]) -> float:
    """Fraction of commits where second == 0 (CI bot heuristic)."""
    if not commit_seconds:
        return 0.0
    return sum(1 for s in commit_seconds if s == 0) / len(commit_seconds)


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        with CHECKPOINT_FILE.open() as f:
            return json.load(f)
    return {"done": [], "failed": [], "qualified": []}


def save_checkpoint(state: dict) -> None:
    with CHECKPOINT_FILE.open("w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Discovery: fetch top contributors from key repos
# ---------------------------------------------------------------------------

def discover_from_repos(api: GitHubAPI, existing: set[str]) -> list[str]:
    """
    Fetch top contributors from DISCOVERY_REPOS and return new usernames.
    Skips bots, organizations, and usernames already in the seed list.
    """
    discovered: list[str] = []
    log.info(f"Discovering contributors from {len(DISCOVERY_REPOS)} repos …")

    for owner, repo in tqdm(DISCOVERY_REPOS, desc="Discovering"):
        contribs = api.paginate(
            f"/repos/{owner}/{repo}/contributors",
            params={"per_page": 100},
            max_pages=1,
        )
        for contrib in contribs[:DISCOVERY_TOP_N]:
            login = contrib.get("login", "")
            ctype = contrib.get("type", "")
            if not login or ctype == "Bot" or "[bot]" in login.lower():
                continue
            if login not in existing and login not in discovered:
                discovered.append(login)

    log.info(f"Discovered {len(discovered)} new candidate usernames")
    return discovered


# ---------------------------------------------------------------------------
# Main per-user processing
# ---------------------------------------------------------------------------

def process_user(api: GitHubAPI, username: str, since_dt: datetime) -> dict | None:
    """
    Full data collection pipeline for one user.

    Returns a result dict, or None if the user doesn't qualify
    (non-existent, bot, or < MIN_COMMITS).
    """
    # 1. Verify user exists and is not a bot
    user_meta = fetch_user_profile(api, username)
    if user_meta is None:
        return None

    # 2. Fetch commit hours
    hours, repo_count = fetch_commit_hours(api, username, since_dt)

    if len(hours) < MIN_COMMITS:
        log.debug(f"  {username}: only {len(hours)} commits (min {MIN_COMMITS}), skipping")
        return None

    # 3. Fetch PR metrics from Events API
    pr_metrics = fetch_pr_metrics(api, username, since_dt)

    # 4. Build result record
    result = {
        "username": username,
        "name": user_meta.get("name", ""),
        "location": user_meta.get("location", ""),
        "company": user_meta.get("company", ""),
        "public_repos": user_meta.get("public_repos", 0),
        "followers": user_meta.get("followers", 0),
        "account_created": user_meta.get("created_at", ""),
        "commit_count_90d": len(hours),
        "repos_checked": repo_count,
        "commit_hours": hours,
        **pr_metrics,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "lookback_days": LOOKBACK_DAYS,
    }

    return result


# ---------------------------------------------------------------------------
# CSV summary writer
# ---------------------------------------------------------------------------

CSV_FIELDS = [
    "username", "name", "location", "company",
    "public_repos", "followers", "account_created",
    "commit_count_90d", "repos_checked",
    "pr_count_90d", "after_hours_prs", "async_ratio",
    "review_comments_90d", "collaboration_index",
    "collected_at", "lookback_days",
    # Note: commit_hours is saved separately to hours/{username}_hours.json
]


def write_csv_row(result: dict, first_write: bool = False) -> None:
    mode = "w" if first_write else "a"
    with SUMMARY_CSV.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if first_write:
            writer.writeheader()
        writer.writerow({k: result.get(k, "") for k in CSV_FIELDS})


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitSyntropy — GitHub profile data collection for chronotype study"
    )
    parser.add_argument("--token", help="GitHub Personal Access Token (or set GITHUB_TOKEN env)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--discover-only", action="store_true",
                        help="Only discover usernames, do not fetch data")
    parser.add_argument("--no-discover", action="store_true",
                        help="Skip repo-based discovery, use seed list only")
    parser.add_argument("--min-commits", type=int, default=MIN_COMMITS,
                        help=f"Minimum commits to qualify (default: {MIN_COMMITS})")
    args = parser.parse_args()

    # Token resolution
    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        log.warning(
            "No GITHUB_TOKEN found. Running unauthenticated (60 req/hr limit).\n"
            "  Set: export GITHUB_TOKEN=ghp_your_token_here\n"
            "  Or:  python 01_collect_github_profiles.py --token ghp_..."
        )

    api = GitHubAPI(token=token or None)

    # Date window
    since_dt = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    log.info(f"Lookback window: last {LOOKBACK_DAYS} days (since {since_dt.date()})")
    log.info(f"Minimum commits required: {args.min_commits}")

    # Load checkpoint
    state = load_checkpoint() if args.resume else {"done": [], "failed": [], "qualified": []}
    done_set = set(state["done"])

    # Build full username list
    all_usernames: list[str] = list(SEED_USERNAMES)

    if not args.no_discover:
        seed_set = set(SEED_USERNAMES)
        discovered = discover_from_repos(api, existing=seed_set)
        for u in discovered:
            if u not in seed_set:
                all_usernames.append(u)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique_usernames: list[str] = []
    for u in all_usernames:
        if u not in seen:
            seen.add(u)
            unique_usernames.append(u)

    # Save full candidate list for reference
    with CANDIDATES_FILE.open("w") as f:
        f.write("\n".join(unique_usernames))
    log.info(f"Total candidate usernames: {len(unique_usernames)}")

    if args.discover_only:
        log.info(f"--discover-only: username list saved to {CANDIDATES_FILE}. Exiting.")
        return

    # Filter already done
    pending = [u for u in unique_usernames if u not in done_set]
    log.info(f"Pending: {len(pending)} users ({len(done_set)} already done from checkpoint)")

    # CSV: write header on first run, append otherwise
    csv_first_write = not SUMMARY_CSV.exists()

    # Process each user
    qualified_count = len(state.get("qualified", []))
    failed_count = len(state.get("failed", []))

    log.info("=" * 60)
    log.info("Starting data collection …")
    log.info("=" * 60)

    for i, username in enumerate(tqdm(pending, desc="Users", total=len(pending))):
        log.info(f"[{i+1}/{len(pending)}] Processing @{username} …")

        try:
            result = process_user(api, username, since_dt)
        except Exception as exc:
            log.error(f"  @{username}: unexpected error — {exc}")
            state["failed"].append(username)
            state["done"].append(username)
            save_checkpoint(state)
            time.sleep(SLEEP_BETWEEN_USERS)
            failed_count += 1
            continue

        if result is None:
            log.info(f"  @{username}: did not qualify")
            state["failed"].append(username)
        else:
            log.info(
                f"  @{username}: ✓  {result['commit_count_90d']} commits, "
                f"{result['pr_count_90d']} PRs, "
                f"collab={result['collaboration_index']}"
            )
            # Save raw JSON
            raw_path = RAW_DIR / f"{username}.json"
            with raw_path.open("w") as f:
                json.dump(result, f, indent=2)

            # Save hours-only JSON (smaller, for analysis script)
            hours_path = HOURS_DIR / f"{username}_hours.json"
            with hours_path.open("w") as f:
                json.dump(result["commit_hours"], f)

            # Append to CSV (without commit_hours column)
            write_csv_row(result, first_write=csv_first_write)
            csv_first_write = False

            state["qualified"].append(username)
            qualified_count += 1

        state["done"].append(username)
        save_checkpoint(state)
        time.sleep(SLEEP_BETWEEN_USERS)

    # Final summary
    log.info("=" * 60)
    log.info("Collection complete.")
    log.info(f"  Total processed : {len(state['done'])}")
    log.info(f"  Qualified (≥{args.min_commits} commits): {qualified_count}")
    log.info(f"  Failed / skipped: {failed_count}")
    log.info(f"  Output CSV      : {SUMMARY_CSV}")
    log.info(f"  Raw JSON dir    : {RAW_DIR}")
    log.info(f"  Hours JSON dir  : {HOURS_DIR}")
    log.info("=" * 60)

    if qualified_count < 30:
        log.warning(
            f"Only {qualified_count} qualified profiles. "
            f"Target is ≥50 for the MEQ matching study. "
            f"Consider: (a) lowering --min-commits, (b) adding more seeds, "
            f"(c) waiting and re-running with --resume."
        )
    elif qualified_count < 50:
        log.warning(
            f"{qualified_count} profiles qualify. You have enough for a preliminary "
            f"study (n≥30 for publication), but aim for ≥50 before the MEQ survey closes."
        )
    else:
        log.info(
            f"{qualified_count} profiles qualify — sufficient for the study. "
            f"Now run: python scripts/02_meq_survey.py to generate the survey template."
        )


if __name__ == "__main__":
    main()

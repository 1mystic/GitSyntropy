"""
Script 04 — Cross-modal chronotype agreement: GitHub commits vs. Stack Overflow activity.

Revision note (major-revision cycle, Reviewer C #1)
--------------------------------------------------
This script replaces the earlier version, which had three defects:

  1. When the Stack Exchange API returned no usable pairs it *silently* substituted
     synthetic rows, which were then reported in the manuscript as real matched handles.
  2. The synthetic generator hardcoded ``close_match = True`` on every row, so
     lark<->owl pairs — opposite ends of the morning-night spectrum — were counted as
     "close" agreement. This is the contradiction Reviewer C identified.
  3. ``exact_match`` counted any pair in which *either* side was labelled ``flexible``
     as an exact match, inflating the exact-agreement rate.

The rewrite fixes all three:

  * No silent fallback. Real mode writes ``crossval_so_github.*``; simulation mode must be
    requested explicitly with ``--simulate`` and writes to separate
    ``crossval_simulated.*`` files, with ``data_provenance`` stamped on every row and in
    the summary JSON.
  * Adjacency is computed from the ordered morning-night spectrum
    (lark < daytime < evening < owl); ``lark`` and ``owl`` are three ranks apart and are
    therefore NOT adjacent. Asserted in ``_self_check()``.
  * ``flexible`` is its own class. It is never an exact or adjacent match; pairs involving
    it are reported separately and excluded from the primary rates.
  * A discretisation-free agreement measure is also reported: the absolute *circular*
    difference between the two peak hours, which does not depend on where the class
    boundaries were drawn.

Usage
-----
    python 04_stackoverflow_crossval.py              # real Stack Exchange run
    python 04_stackoverflow_crossval.py --simulate   # explicitly-labelled simulation
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import urllib.error
import urllib.parse
import urllib.request

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
HOURS_DIR = DATA_DIR / "hours"
RESULTS = SCRIPT_DIR / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

SO_API = "https://api.stackexchange.com/2.3"
LOOKBACK_DAYS = 365

# Minimum posts for a Stack Overflow profile to enter the primary analysis.
# The previous version used 5, which is far too few to estimate a peak hour; 5 is kept
# only as a reported sensitivity tier.
MIN_SO_POSTS_PRIMARY = 20
MIN_SO_POSTS_SENSITIVITY = 5

# Ordered morning-night spectrum. Adjacency is |rank difference| == 1 on THIS ordering.
# "flexible" is deliberately absent: it is not a point on the spectrum.
SPECTRUM = ["lark", "daytime", "evening", "owl"]

# Manually curated GitHub login -> real-name mappings, used only as search seeds.
# A candidate is accepted only if _score_candidate() finds corroborating evidence.
KNOWN_SO_NAMES = {
    "gvanrossum": "Guido van Rossum",
    "mitsuhiko": "Armin Ronacher",
    "sindresorhus": "Sindre Sorhus",
    "antfu": "Anthony Fu",
    "mcollina": "Matteo Collina",
    "dtolnay": "David Tolnay",
    "BurntSushi": "Andrew Gallant",
    "bradfitz": "Brad Fitzpatrick",
    "nikomatsakis": "Niko Matsakis",
    "emilio": "Emilio Cobos",
    "rgommers": "Ralf Gommers",
    "tiangolo": "Sebastián Ramírez",
    "hynek": "Hynek Schlawack",
    "dims": "Davanum Srinivas",
    "thockin": "Tim Hockin",
    "potiuk": "Jarek Potiuk",
    "jasnell": "James Snell",
    "eps1lon": "Sebastian Silbermann",
    "bvaughn": "Brian Vaughn",
    "simonw": "Simon Willison",
    "mvdan": "Daniel Martí",
    "ehuss": "Eric Huss",
    "zanieb": "Zanie Blue",
    "Kludex": "Marcelo Trylesinski",
    "adriangb": "Adrian Garcia Badaracco",
}


# ---------------------------------------------------------------------------
# Chronotype detection — exact port of apps/backend/app/github_client.py
# ---------------------------------------------------------------------------
def _hour_to_circular(h: int) -> tuple[float, float]:
    a = 2 * math.pi * h / 24
    return math.cos(a), math.sin(a)


def _label_from_peak(ph: float) -> str:
    if 5 <= ph < 11:
        return "lark"
    if 11 <= ph < 19:
        return "daytime"
    if 19 <= ph < 23:
        return "evening"
    return "owl"


def detect_chronotype(hours: list[int], entropy_threshold: float = 0.92) -> dict:
    """Return {label, peak_hour, confidence, method} for a list of UTC hours."""
    if not hours:
        return {"label": "flexible", "peak_hour": 12.0, "confidence": 0.0, "method": "empty"}

    hist = [0] * 24
    for h in hours:
        hist[h % 24] += 1
    total = len(hours)
    norm = [c / total for c in hist]

    if total < 10:
        peak = max(range(24), key=lambda h: hist[h])
        return {
            "label": _label_from_peak(float(peak)),
            "peak_hour": float(peak),
            "confidence": hist[peak] / total,
            "method": "histogram_peak",
        }

    import numpy as np
    from sklearn.cluster import KMeans

    coords = np.array([_hour_to_circular(h) for h in hours])
    k = min(3, len(set(hours)))
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(coords)
    counts = np.bincount(km.labels_, minlength=k)
    dom = int(np.argmax(counts))
    cx, cy = km.cluster_centers_[dom]
    angle = math.atan2(cy, cx)
    if angle < 0:
        angle += 2 * math.pi
    ph = angle * 24 / (2 * math.pi)
    confidence = float(counts[dom] / total)

    entropy = -sum(p * math.log(p + 1e-9) for p in norm)
    if entropy / math.log(24) > entropy_threshold:
        return {"label": "flexible", "peak_hour": ph, "confidence": confidence,
                "method": "entropy_flexible"}

    return {"label": _label_from_peak(ph), "peak_hour": ph, "confidence": confidence,
            "method": "circular_kmeans"}


# ---------------------------------------------------------------------------
# Agreement definitions
# ---------------------------------------------------------------------------
def is_exact(a: str, b: str) -> bool:
    """Exact agreement. 'flexible' never counts as an exact match against a spectrum class,
    but flexible-vs-flexible does (both classifiers declined to assign a chronotype)."""
    return a == b


def is_adjacent(a: str, b: str) -> bool:
    """Adjacent on the ordered morning-night spectrum (lark < daytime < evening < owl).

    lark<->owl is three ranks apart, i.e. opposite ends, and is NOT adjacent — this is the
    defect Reviewer C identified. 'flexible' is off-spectrum and is adjacent to nothing.
    """
    if a not in SPECTRUM or b not in SPECTRUM:
        return False
    return abs(SPECTRUM.index(a) - SPECTRUM.index(b)) == 1


def is_close(a: str, b: str) -> bool:
    """Exact OR adjacent. Never true for lark<->owl."""
    return is_exact(a, b) or is_adjacent(a, b)


def circular_hour_diff(h1: float, h2: float) -> float:
    """Absolute difference between two clock hours, on the circle (max 12.0)."""
    d = abs(h1 - h2) % 24.0
    return min(d, 24.0 - d)


def _self_check() -> None:
    """Guards against the exact defects reported by Reviewer C."""
    assert not is_adjacent("lark", "owl"), "lark<->owl must NOT be adjacent"
    assert not is_close("lark", "owl"), "lark<->owl must NOT be a close match"
    assert is_adjacent("lark", "daytime")
    assert is_adjacent("evening", "owl")
    assert not is_adjacent("lark", "evening"), "two ranks apart is not adjacent"
    assert not is_exact("flexible", "owl")
    assert not is_close("flexible", "owl"), "flexible must not silently count as agreement"
    assert is_exact("flexible", "flexible")
    assert abs(circular_hour_diff(23.0, 1.0) - 2.0) < 1e-9
    assert abs(circular_hour_diff(2.0, 14.0) - 12.0) < 1e-9


# ---------------------------------------------------------------------------
# Stack Exchange API
# ---------------------------------------------------------------------------
def _get(url: str, timeout: int = 20, retries: int = 3) -> dict | None:
    """GET with explicit throttle handling. The Stack Exchange API returns a ``backoff``
    field that clients must honour; ignoring it is what produced the HTTP 429 storm in the
    first attempt at this re-run."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "gitsyntropy-research/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            if data.get("backoff"):
                time.sleep(float(data["backoff"]) + 0.5)
            return data
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                wait = 20 * (attempt + 1)
                print(f"      [throttled] HTTP 429 — sleeping {wait}s")
                time.sleep(wait)
                continue
            print(f"      [api error] HTTP {exc.code}: {exc.reason}")
            return None
        except Exception as exc:  # noqa: BLE001 — failures must be visible, not silent
            print(f"      [api error] {type(exc).__name__}: {exc}")
            return None
    return None


def _score_candidate(item: dict, name: str, github_login: str) -> tuple[int, str]:
    """Score a Stack Overflow user as a match for a GitHub account.

    Returns (score, evidence). Score 0 means reject — we do not accept a match on a
    fuzzy name search alone, because a wrong identity link would silently corrupt the
    agreement estimate.
    """
    display = (item.get("display_name") or "").strip().lower()
    website = (item.get("website_url") or "").lower()
    link = (item.get("link") or "").lower()
    about = (item.get("about_me") or "").lower()

    gh_needle = f"github.com/{github_login.lower()}"
    if gh_needle in website or gh_needle in about or gh_needle in link:
        return 3, "github_link"
    if display == name.strip().lower():
        return 2, "exact_display_name"
    if display == github_login.strip().lower():
        return 2, "display_name_equals_login"
    return 0, "rejected_fuzzy_only"


def so_find_user(name: str, github_login: str) -> tuple[int | None, str, str, dict]:
    """Search Stack Overflow for a user. Returns (user_id, display_name, evidence, item).

    The default API filter already returns ``website_url`` and ``link``, which is what the
    evidence check needs; no custom filter is requested.
    """
    q = urllib.parse.urlencode({
        "inname": name,
        "site": "stackoverflow",
        "pagesize": 10,
        "order": "desc",
        "sort": "reputation",
    })
    data = _get(f"{SO_API}/users?{q}")
    if not data:
        return None, "", "api_error", {}

    best = (0, None, "", "no_candidates", {})
    for item in data.get("items", []):
        score, evidence = _score_candidate(item, name, github_login)
        if score > best[0]:
            best = (score, item.get("user_id"), item.get("display_name", ""), evidence, item)
    if best[0] == 0:
        return None, "", "rejected_fuzzy_only", {}
    return best[1], best[2], best[3], best[4]


def so_fetch_activity_hours(user_id: int) -> tuple[list[int], list[int]]:
    """Return (UTC hours, raw epoch timestamps) of this user's Stack Overflow posts.

    Window decision (logged in paper/REVISION_LOG.md): a 365-day window — the window the
    original submission claimed to use — returns **zero** posts for almost every developer
    in this sample, because senior open-source maintainers have largely stopped answering
    on Stack Overflow. The comparison is therefore run against the user's *lifetime* post
    history, and the temporal mismatch against the 90-day GitHub window is disclosed as a
    limitation rather than hidden.
    """
    hours: list[int] = []
    stamps: list[int] = []
    for endpoint in ("answers", "questions"):
        for page in range(1, 4):
            q = urllib.parse.urlencode({
                "site": "stackoverflow",
                "pagesize": 100,
                "order": "desc",
                "sort": "creation",
                "page": page,
            })
            data = _get(f"{SO_API}/users/{user_id}/{endpoint}?{q}")
            if not data:
                break
            for item in data.get("items", []):
                ts = item.get("creation_date", 0)
                if ts:
                    stamps.append(ts)
                    hours.append(datetime.fromtimestamp(ts, tz=timezone.utc).hour)
            if not data.get("has_more"):
                break
            time.sleep(1.0)
        time.sleep(1.0)
    return hours, stamps


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def load_candidate_names() -> dict[str, str]:
    """GitHub login -> real name, for every profile in the dataset.

    The original script searched only 25 hand-curated names. Names are taken from the
    GitHub ``name`` field already collected in ``data/profiles_summary.csv`` so that all
    46 profiles get a chance to match, with the curated map used as an override where the
    GitHub display name is missing or unhelpful.
    """
    names: dict[str, str] = {}
    csv_path = DATA_DIR / "profiles_summary.csv"
    if csv_path.exists():
        with csv_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                login = (row.get("username") or "").strip()
                name = (row.get("name") or "").strip()
                if login and name:
                    names[login] = name
    names.update(KNOWN_SO_NAMES)
    return names


def load_existing_rows(stem: str = "crossval_so_github") -> list[dict]:
    """Previously fetched rows, so a re-run does not re-spend the daily API quota."""
    path = RESULTS / f"{stem}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("exact_match", "adjacent_match", "close_match", "opposite_ends"):
            r[k] = str(r[k]).lower() == "true"
        for k in ("n_gh_commits", "n_so_posts", "so_user_id"):
            r[k] = int(r[k]) if str(r[k]).strip() else 0
        for k in ("gh_peak_hour", "so_peak_hour", "peak_hour_diff"):
            r[k] = float(r[k])
    return rows


def load_github_chronotypes() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in sorted(HOURS_DIR.glob("*_hours.json")):
        username = f.stem.replace("_hours", "")
        with f.open() as fp:
            hours = json.load(fp)
        if len(hours) >= 10:
            res = detect_chronotype(hours)
            res["n_commits"] = len(hours)
            out[username] = res
    return out


def summarise(rows: list[dict], provenance: str) -> dict:
    """Compute agreement statistics. Pairs involving 'flexible' are reported separately
    and excluded from the primary rates, because 'flexible' is a refusal to assign a
    chronotype rather than a point on the spectrum."""
    on_spectrum = [r for r in rows
                   if r["gh_chronotype"] in SPECTRUM and r["so_chronotype"] in SPECTRUM]
    flexible_rows = [r for r in rows if r not in on_spectrum]

    primary = [r for r in on_spectrum if r["n_so_posts"] >= MIN_SO_POSTS_PRIMARY]
    sens = [r for r in on_spectrum if r["n_so_posts"] >= MIN_SO_POSTS_SENSITIVITY]

    def rates(subset: list[dict]) -> dict:
        n = len(subset)
        if n == 0:
            return {"n": 0}
        exact = sum(1 for r in subset if r["exact_match"])
        close = sum(1 for r in subset if r["close_match"])
        opp = sum(1 for r in subset if r["opposite_ends"])
        diffs = sorted(r["peak_hour_diff"] for r in subset)
        mid = n // 2
        median = diffs[mid] if n % 2 else (diffs[mid - 1] + diffs[mid]) / 2
        return {
            "n": n,
            "exact_match": exact,
            "exact_match_rate": round(exact / n, 3),
            "close_match": close,
            "close_match_rate": round(close / n, 3),
            "opposite_ends": opp,
            "opposite_ends_rate": round(opp / n, 3),
            "median_peak_hour_diff": round(median, 2),
            "mean_peak_hour_diff": round(sum(diffs) / n, 2),
        }

    per_class: dict[str, dict] = {}
    for cls in SPECTRUM:
        subset = [r for r in primary if r["gh_chronotype"] == cls]
        if subset:
            per_class[cls] = rates(subset)

    return {
        "data_provenance": provenance,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_rows_total": len(rows),
        "n_rows_involving_flexible": len(flexible_rows),
        "min_so_posts_primary": MIN_SO_POSTS_PRIMARY,
        "min_so_posts_sensitivity": MIN_SO_POSTS_SENSITIVITY,
        "primary": rates(primary),
        "sensitivity_min5_posts": rates(sens),
        "per_class_primary": per_class,
        "adjacency_definition": "|rank diff| == 1 on lark<daytime<evening<owl; lark<->owl is NOT adjacent",
        "pairs": rows,
    }


def build_row(github_user: str, gh: dict, so_id, so_name: str, so_hours: list[int],
              evidence: str, provenance: str, so_item: dict | None = None,
              so_stamps: list[int] | None = None) -> dict:
    so = detect_chronotype(so_hours)
    gh_ct, so_ct = gh["label"], so["label"]
    so_item = so_item or {}
    stamps = so_stamps or []
    span = {}
    if stamps:
        span = {
            "so_first_post": datetime.fromtimestamp(min(stamps), tz=timezone.utc).date().isoformat(),
            "so_last_post": datetime.fromtimestamp(max(stamps), tz=timezone.utc).date().isoformat(),
        }
    return {
        "github_username": github_user,
        "so_user_id": so_id,
        "so_display_name": so_name,
        "match_evidence": evidence,
        "so_reputation": so_item.get("reputation"),
        "so_location": so_item.get("location"),
        "gh_chronotype": gh_ct,
        "so_chronotype": so_ct,
        "gh_peak_hour": round(gh["peak_hour"], 2),
        "so_peak_hour": round(so["peak_hour"], 2),
        "peak_hour_diff": round(circular_hour_diff(gh["peak_hour"], so["peak_hour"]), 2),
        "exact_match": is_exact(gh_ct, so_ct),
        "adjacent_match": is_adjacent(gh_ct, so_ct),
        "close_match": is_close(gh_ct, so_ct),
        "opposite_ends": (gh_ct in SPECTRUM and so_ct in SPECTRUM
                          and abs(SPECTRUM.index(gh_ct) - SPECTRUM.index(so_ct)) >= 3),
        "n_gh_commits": gh["n_commits"],
        "n_so_posts": len(so_hours),
        "so_first_post": span.get("so_first_post"),
        "so_last_post": span.get("so_last_post"),
        "data_provenance": provenance,
    }


def run_real() -> dict:
    print("=" * 68)
    print("Script 04 — Cross-modal agreement (REAL Stack Exchange data)")
    print("=" * 68)

    gh_results = load_github_chronotypes()
    candidates = load_candidate_names()
    print(f"GitHub profiles with >=10 commit hours: {len(gh_results)}")
    print(f"Candidate name mappings              : {len(candidates)}")

    rows: list[dict] = load_existing_rows()
    already = {r["github_username"] for r in rows}
    if rows:
        print(f"Resuming: {len(rows)} pair(s) already fetched, not re-querying the API")
    rejected: list[dict] = []

    for github_user, so_name in candidates.items():
        if github_user in already:
            continue
        if github_user not in gh_results:
            rejected.append({"github_username": github_user, "reason": "no_github_hours"})
            continue

        print(f"  {github_user:<14s} -> SO '{so_name}' ... ", end="", flush=True)
        so_id, so_display, evidence, so_item = so_find_user(so_name, github_user)
        time.sleep(1.0)  # stay well inside the unauthenticated request budget
        if not so_id:
            print(f"no accepted match ({evidence})")
            rejected.append({"github_username": github_user, "reason": evidence})
            continue

        so_hours, so_stamps = so_fetch_activity_hours(so_id)
        if len(so_hours) < MIN_SO_POSTS_SENSITIVITY:
            print(f"id={so_id} but only {len(so_hours)} posts — excluded")
            rejected.append({"github_username": github_user,
                             "reason": f"insufficient_so_posts_{len(so_hours)}"})
            continue

        row = build_row(github_user, gh_results[github_user], so_id, so_display,
                        so_hours, evidence, "real", so_item, so_stamps)
        rows.append(row)
        flag = "=" if row["exact_match"] else ("~" if row["close_match"] else "X")
        print(f"GH={row['gh_chronotype']:<8s} SO={row['so_chronotype']:<8s} "
              f"n_so={row['n_so_posts']:<4d} dh={row['peak_hour_diff']:<5.2f} {flag}")
        time.sleep(0.3)

    if not rows:
        print("\nNO REAL PAIRS RECOVERED.")
        print("This script does NOT fall back to synthetic data. To produce an explicitly")
        print("labelled simulation instead, re-run with --simulate.")
        (RESULTS / "crossval_rejected.json").write_text(
            json.dumps(rejected, indent=2), encoding="utf-8")
        return {"data_provenance": "real", "primary": {"n": 0}, "rejected": rejected}

    stats = summarise(rows, "real")
    stats["rejected"] = rejected
    _write("crossval_so_github", rows, stats)
    _report(stats)
    return stats


def run_simulated(seed: int = 2026, n: int = 20) -> dict:
    """Explicitly-labelled parametric simulation. NOT a substitute for real data.

    Unlike the previous version, this generates commit-hour *samples* and runs them
    through the real classifier, and it never asserts agreement flags by construction —
    every flag is computed by the same functions used on real data.
    """
    print("=" * 68)
    print("Script 04 — Cross-modal agreement (SIMULATION — clearly labelled, not real)")
    print("=" * 68)

    import numpy as np

    rng = np.random.default_rng(seed)
    centres = {"lark": 8.0, "daytime": 14.0, "evening": 21.0, "owl": 2.0}
    rows: list[dict] = []

    for i in range(n):
        true_cls = list(centres)[i % 4]
        mu = centres[true_cls]
        gh_hours = [int(round(h)) % 24 for h in rng.normal(mu, 2.0, size=int(rng.integers(80, 300)))]
        # Independent modality with its own noise level, not a copy of the GitHub stream.
        so_hours = [int(round(h)) % 24 for h in rng.normal(mu + rng.normal(0, 1.5), 3.0,
                                                          size=int(rng.integers(20, 60)))]
        gh = detect_chronotype(gh_hours)
        gh["n_commits"] = len(gh_hours)
        rows.append(build_row(f"sim_{i:02d}", gh, 90000 + i, f"Simulated user {i}",
                              so_hours, "simulated", "simulated"))

    stats = summarise(rows, "simulated")
    _write("crossval_simulated", rows, stats)
    _report(stats)
    print("\nNOTE: these rows are simulated. They must be labelled as such wherever reported.")
    return stats


def _write(stem: str, rows: list[dict], stats: dict) -> None:
    csv_path = RESULTS / f"{stem}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS / f"{stem}_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\nWrote {csv_path.name} and {stem}_stats.json")


def _report(stats: dict) -> None:
    p = stats["primary"]
    s = stats["sensitivity_min5_posts"]
    print(f"\nProvenance         : {stats['data_provenance']}")
    print(f"Rows total         : {stats['n_rows_total']} "
          f"({stats['n_rows_involving_flexible']} involve 'flexible', excluded from rates)")
    if p.get("n"):
        print(f"PRIMARY (n_so>={MIN_SO_POSTS_PRIMARY}, n={p['n']}):")
        print(f"  exact          : {p['exact_match']}/{p['n']} = {p['exact_match_rate']*100:.1f}%")
        print(f"  close (exact+adj): {p['close_match']}/{p['n']} = {p['close_match_rate']*100:.1f}%")
        print(f"  opposite ends  : {p['opposite_ends']}/{p['n']} = {p['opposite_ends_rate']*100:.1f}%")
        print(f"  median |dpeak| : {p['median_peak_hour_diff']} h")
    if s.get("n"):
        print(f"SENSITIVITY (n_so>={MIN_SO_POSTS_SENSITIVITY}, n={s['n']}): "
              f"exact {s['exact_match_rate']*100:.1f}%, close {s['close_match_rate']*100:.1f}%")


def main() -> int:
    _self_check()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--simulate", action="store_true",
                    help="produce an explicitly-labelled simulation instead of real data")
    args = ap.parse_args()

    stats = run_simulated() if args.simulate else run_real()
    return 0 if stats.get("primary", {}).get("n", 0) or args.simulate else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Script 06 — Sensitivity of every hand-set constant, and sample characterisation.

Answers, on the real 46-developer sample only:
  * Reviewer C #5 — "several constants lack stated justification; add a sensitivity
    analysis, at minimum for constants with high impact on final results."
  * Reviewer B #1  — background/composition of the profiled sample.
  * Reviewer B #2  — generalisability: how the picture shifts across sample subgroups.
  * Reviewer B #3  — what other individual attributes are observable, and what is not.

Constants swept
---------------
  entropy_threshold  0.92   -> 0.80 … 0.99   (the 'flexible' cut)
  k_clusters         3      -> 2, 3, 4, 5    (K-Means cluster count)
  min_commits        10     -> 5 … 50        (histogram-fallback boundary / inclusion)
  weak_dim_threshold 0.30   -> 0.10 … 0.50   (per-dimension 'weak' flag)
  risk_flag_threshold 0.45  -> 0.25 … 0.65   (chronotype risk flag)
  weight vector      1..8   -> uniform, reversed, and 200 random monotone vectors
  class boundaries   5/11/19/23 -> +/- 2 h shifts

Usage:
    python 06_sensitivity_analysis.py [--seed 42]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
HOURS_DIR = DATA_DIR / "hours"
RESULTS = SCRIPT_DIR / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

TRAIT_WEIGHTS = {
    "chronotype_sync": 8.0, "stress_response": 7.0, "risk_tolerance": 6.0,
    "decision_style": 5.0, "work_style": 4.0, "team_resilience": 3.0,
    "leadership_orientation": 2.0, "innovation_drive": 1.0,
}
TRAIT_DIMENSIONS = list(TRAIT_WEIGHTS)
SPECTRUM = ["lark", "daytime", "evening", "owl"]

DEFAULTS = {
    "entropy_threshold": 0.92,
    "k_clusters": 3,
    "min_commits": 10,
    "weak_dim_threshold": 0.30,
    "risk_flag_threshold": 0.45,
    "boundary_shift_h": 0.0,
}


# ---------------------------------------------------------------------------
# Classifier, parameterised by the constants under test
# ---------------------------------------------------------------------------
def _hour_to_circular(h: int) -> tuple[float, float]:
    a = 2 * math.pi * h / 24
    return math.cos(a), math.sin(a)


def _label_from_peak(ph: float, shift: float = 0.0) -> str:
    lo, mid, hi, top = 5 + shift, 11 + shift, 19 + shift, 23 + shift
    if lo <= ph < mid:
        return "lark"
    if mid <= ph < hi:
        return "daytime"
    if hi <= ph < top:
        return "evening"
    return "owl"


def classify(hours: list[int], entropy_threshold: float, k_clusters: int,
             min_commits: int, boundary_shift_h: float) -> dict:
    from sklearn.cluster import KMeans

    hist = [0] * 24
    for h in hours:
        hist[h % 24] += 1
    total = len(hours)
    norm = [c / total for c in hist]

    if total < min_commits:
        peak = float(max(range(24), key=lambda h: hist[h]))
        return {"label": _label_from_peak(peak, boundary_shift_h), "peak_hour": peak,
                "confidence": hist[int(peak)] / total, "method": "histogram_peak"}

    coords = np.array([_hour_to_circular(h) for h in hours])
    k = min(k_clusters, len(set(hours)))
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
    return {"label": _label_from_peak(ph, boundary_shift_h), "peak_hour": ph,
            "confidence": confidence, "method": "circular_kmeans"}


def circular_hour_diff(h1: float, h2: float) -> float:
    d = abs(h1 - h2) % 24.0
    return min(d, 24.0 - d)


# ---------------------------------------------------------------------------
# Downstream quantities that a constant can move
# ---------------------------------------------------------------------------
def dyad_totals(labels: list[dict], weights: dict[str, float] | None = None) -> dict:
    """Compatibility totals over all dyads, plus the aligned/mismatched contrast."""
    w = weights or TRAIT_WEIGHTS
    w_chrono = w["chronotype_sync"]
    w_rest = sum(v for k, v in w.items() if k != "chronotype_sync")

    aligned, mismatched, totals = [], [], []
    for a, b in combinations(labels, 2):
        sync = max(0.0, 1.0 - circular_hour_diff(a["peak_hour"], b["peak_hour"]) / 12.0) * w_chrono
        total = w_rest + sync  # non-telemetry dimensions are neutral-imputed -> full weight
        totals.append(total)
        if a["label"] in SPECTRUM and b["label"] in SPECTRUM:
            (aligned if a["label"] == b["label"] else mismatched).append(total)

    t = np.array(totals)
    al, mm = np.array(aligned), np.array(mismatched)
    d = float("nan")
    if len(al) > 1 and len(mm) > 1:
        sp = math.sqrt(((len(al) - 1) * al.var(ddof=1) + (len(mm) - 1) * mm.var(ddof=1))
                       / (len(al) + len(mm) - 2))
        d = (al.mean() - mm.mean()) / sp if sp else float("nan")
    return {
        "n_dyads": len(t),
        "mean_total": round(float(t.mean()), 3),
        "n_aligned": len(al),
        "mean_difference": round(float(al.mean() - mm.mean()), 3) if len(al) and len(mm) else None,
        "cohens_d": round(d, 3) if d == d else None,
    }


def label_counts(labels: list[dict]) -> dict[str, int]:
    out = {c: 0 for c in SPECTRUM + ["flexible"]}
    for x in labels:
        out[x["label"]] = out.get(x["label"], 0) + 1
    return out


def agreement_with_default(labels: list[dict], default: list[dict]) -> float:
    same = sum(1 for a, b in zip(labels, default) if a["label"] == b["label"])
    return round(same / len(default), 3)


# ---------------------------------------------------------------------------
# Sweeps
# ---------------------------------------------------------------------------
def load_hours() -> list[tuple[str, list[int]]]:
    out = []
    for f in sorted(HOURS_DIR.glob("*_hours.json")):
        hours = json.loads(f.read_text())
        if len(hours) >= 10:
            out.append((f.stem.replace("_hours", ""), hours))
    return out


def run_with(params: dict, data: list[tuple[str, list[int]]]) -> list[dict]:
    p = {**DEFAULTS, **params}
    return [classify(h, p["entropy_threshold"], p["k_clusters"], p["min_commits"],
                     p["boundary_shift_h"]) for _, h in data]


def sweep_constant(name: str, values: list, data: list[tuple[str, list[int]]],
                   default_labels: list[dict]) -> list[dict]:
    rows = []
    for v in values:
        labels = run_with({name: v}, data)
        counts = label_counts(labels)
        dy = dyad_totals(labels)
        rows.append({
            "constant": name,
            "value": v,
            "is_default": v == DEFAULTS[name],
            **{f"n_{k}": counts[k] for k in SPECTRUM + ["flexible"]},
            "label_agreement_with_default": agreement_with_default(labels, default_labels),
            "mean_dyad_total": dy["mean_total"],
            "aligned_vs_mismatch_diff": dy["mean_difference"],
            "cohens_d": dy["cohens_d"],
        })
    return rows


def sweep_threshold_only(name: str, values: list, labels: list[dict]) -> list[dict]:
    """Constants that do not touch classification, only downstream flagging."""
    rows = []
    dims = []
    for a, b in combinations(labels, 2):
        sync = max(0.0, 1.0 - circular_hour_diff(a["peak_hour"], b["peak_hour"]) / 12.0) * 8.0
        dims.append(sync)
    arr = np.array(dims)
    for v in values:
        rows.append({
            "constant": name,
            "value": v,
            "is_default": abs(v - DEFAULTS[name]) < 1e-9,
            "pct_dyads_flagged": round(float((arr < 8.0 * v).mean() * 100), 2),
        })
    return rows


def _dyad_scores_full(labels: list[dict], w: dict[str, float],
                      psych: list[dict] | None) -> np.ndarray:
    """Dyad totals under weight vector w. If psych is None the seven non-telemetry
    dimensions are neutral-imputed (and therefore contribute their full weight)."""
    wc = w["chronotype_sync"]
    out = []
    idx = list(combinations(range(len(labels)), 2))
    for i, j in idx:
        a, b = labels[i], labels[j]
        total = max(0.0, 1.0 - circular_hour_diff(a["peak_hour"], b["peak_hour"]) / 12.0) * wc
        for dim in TRAIT_DIMENSIONS:
            if dim == "chronotype_sync":
                continue
            wd = w[dim]
            if psych is None:
                total += wd  # both sides imputed -> similarity 1.0
            else:
                # psychometric values are stored on the published 1..8 scale; rescale to wd
                pa = psych[i][dim] / TRAIT_WEIGHTS[dim] * wd
                pb = psych[j][dim] / TRAIT_WEIGHTS[dim] * wd
                total += max(0.0, 1.0 - abs(pa - pb) / wd) * wd
        out.append(total)
    return np.array(out)


def _contrast_from_scores(labels: list[dict], scores: np.ndarray) -> float | None:
    al, mm = [], []
    for (i, j), s in zip(combinations(range(len(labels)), 2), scores):
        a, b = labels[i], labels[j]
        if a["label"] in SPECTRUM and b["label"] in SPECTRUM:
            (al if a["label"] == b["label"] else mm).append(s)
    if len(al) < 2 or len(mm) < 2:
        return None
    al_a, mm_a = np.array(al), np.array(mm)
    sp = math.sqrt(((len(al_a) - 1) * al_a.var(ddof=1) + (len(mm_a) - 1) * mm_a.var(ddof=1))
                   / (len(al_a) + len(mm_a) - 2))
    return round(float((al_a.mean() - mm_a.mean()) / sp), 3) if sp else None


def sweep_weight_structure(labels: list[dict], seed: int, n_random: int = 200,
                           psych: list[dict] | None = None) -> dict:
    """How much does the 1..8 weight vector itself drive the result?

    Compared against uniform weights, the reversed vector, and n_random random *monotone*
    vectors summing to 36. Reported as the rank correlation between each alternative's dyad
    scores and the published vector's, plus the resulting effect size.

    Run twice. On real telemetry the answer is degenerate *by construction*: only one
    dimension varies, so every weight vector produces a monotone transform of the same
    ordering (Spearman = 1 exactly) and Cohen's d is scale-invariant. The informative run is
    the one with psychometric values present, where all eight dimensions vary.
    """
    from scipy.stats import spearmanr

    rng = np.random.default_rng(seed)
    base = _dyad_scores_full(labels, TRAIT_WEIGHTS, psych)
    out: dict = {"published_1_to_8": {"spearman_vs_published": 1.0,
                                      "cohens_d": _contrast_from_scores(labels, base)}}

    for name, w in (("uniform_4.5", {d: 36.0 / 8 for d in TRAIT_DIMENSIONS}),
                    ("reversed_8_to_1",
                     dict(zip(TRAIT_DIMENSIONS, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])))):
        s = _dyad_scores_full(labels, w, psych)
        out[name] = {
            "spearman_vs_published": round(float(spearmanr(base, s).statistic), 4),
            "cohens_d": _contrast_from_scores(labels, s),
        }

    rhos, ds = [], []
    for _ in range(n_random):
        raw = np.sort(rng.random(8))[::-1]
        w = dict(zip(TRAIT_DIMENSIONS, (raw / raw.sum() * 36.0).tolist()))
        s = _dyad_scores_full(labels, w, psych)
        rhos.append(float(spearmanr(base, s).statistic))
        d = _contrast_from_scores(labels, s)
        if d is not None:
            ds.append(d)
    out["random_monotone_vectors"] = {
        "n": n_random,
        "spearman_min": round(min(rhos), 4),
        "spearman_median": round(float(np.median(rhos)), 4),
        "cohens_d_min": round(min(ds), 3),
        "cohens_d_median": round(float(np.median(ds)), 3),
        "cohens_d_max": round(max(ds), 3),
    }
    return out


def simulated_psych(n: int, seed: int) -> list[dict]:
    """Synthetic psychometric vectors, used ONLY to make the weight sweep non-degenerate.
    Clearly labelled wherever reported."""
    rng = np.random.default_rng(seed)
    return [{dim: float(TRAIT_WEIGHTS[dim] * rng.uniform(0.15, 0.95))
             for dim in TRAIT_DIMENSIONS if dim != "chronotype_sync"} for _ in range(n)]


# ---------------------------------------------------------------------------
# Sample characterisation (Reviewer B #1, #2, #3)
# ---------------------------------------------------------------------------
def characterise_sample(labels_by_user: dict[str, dict], seed: int) -> dict:
    from scipy.stats import pearsonr

    path = DATA_DIR / "profiles_summary.csv"
    if not path.exists():
        return {"error": "profiles_summary.csv not found"}

    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["username"] in labels_by_user]

    now = datetime.now(timezone.utc)

    def tenure_years(r: dict) -> float:
        created = datetime.fromisoformat(r["account_created"].replace("Z", "+00:00"))
        return (now - created).days / 365.25

    def num(r: dict, key: str) -> float:
        try:
            return float(r[key])
        except (ValueError, KeyError):
            return float("nan")

    tenure = np.array([tenure_years(r) for r in rows])
    followers = np.array([num(r, "followers") for r in rows])
    repos = np.array([num(r, "public_repos") for r in rows])
    commits = np.array([num(r, "commit_count_90d") for r in rows])
    collab = np.array([num(r, "collaboration_index") for r in rows])
    conf = np.array([labels_by_user[r["username"]]["confidence"] for r in rows])

    has_company = sum(1 for r in rows if (r.get("company") or "").strip())
    has_location = sum(1 for r in rows if (r.get("location") or "").strip())

    def describe(x: np.ndarray) -> dict:
        return {"mean": round(float(np.nanmean(x)), 2),
                "median": round(float(np.nanmedian(x)), 2),
                "min": round(float(np.nanmin(x)), 2),
                "max": round(float(np.nanmax(x)), 2)}

    # Subgroups for the external-validity discussion
    med_commits = float(np.nanmedian(commits))
    med_tenure = float(np.nanmedian(tenure))

    def subgroup(mask: np.ndarray, name: str) -> dict:
        subset = [labels_by_user[r["username"]] for r, m in zip(rows, mask) if m]
        counts = label_counts(subset)
        return {"subgroup": name, "n": int(mask.sum()),
                **{f"pct_{k}": round(counts[k] / max(len(subset), 1) * 100, 1)
                   for k in SPECTRUM + ["flexible"]},
                "mean_confidence": round(float(np.mean([s["confidence"] for s in subset])), 3)
                if subset else None}

    correlations = {}
    for name, arr in (("account_tenure_years", tenure), ("public_repos", repos),
                      ("followers", followers), ("commit_count_90d", commits),
                      ("collaboration_index", collab)):
        ok = ~np.isnan(arr)
        if ok.sum() > 3:
            r, p = pearsonr(arr[ok], conf[ok])
            correlations[name] = {"r_with_chronotype_confidence": round(float(r), 3),
                                  "p": round(float(p), 4)}

    return {
        "n_profiles": len(rows),
        "account_tenure_years": describe(tenure),
        "public_repos": describe(repos),
        "followers": describe(followers),
        "commits_90d": describe(commits),
        "collaboration_index": describe(collab),
        "profiles_with_company_field": has_company,
        "profiles_with_location_field": has_location,
        "observable_attribute_correlations": correlations,
        "subgroups": [
            subgroup(commits >= med_commits, f"commit volume >= median ({med_commits:.0f})"),
            subgroup(commits < med_commits, f"commit volume < median ({med_commits:.0f})"),
            subgroup(tenure >= med_tenure, f"account tenure >= median ({med_tenure:.1f} y)"),
            subgroup(tenure < med_tenure, f"account tenure < median ({med_tenure:.1f} y)"),
        ],
        "not_observable": [
            "formal education", "years of professional (non-public) experience",
            "employment seniority", "ethical disposition or integrity measures",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print("=" * 68)
    print("Script 06 — Constant sensitivity and sample characterisation (real n=46)")
    print("=" * 68)

    data = load_hours()
    default_labels = run_with({}, data)
    labels_by_user = {u: lab for (u, _), lab in zip(data, default_labels)}
    print(f"Developers: {len(data)}   default label counts: {label_counts(default_labels)}")

    rows: list[dict] = []
    rows += sweep_constant("entropy_threshold",
                           [0.80, 0.85, 0.88, 0.90, 0.92, 0.94, 0.96, 0.99], data, default_labels)
    rows += sweep_constant("k_clusters", [2, 3, 4, 5], data, default_labels)
    rows += sweep_constant("min_commits", [5, 10, 20, 30, 50], data, default_labels)
    rows += sweep_constant("boundary_shift_h", [-2.0, -1.0, 0.0, 1.0, 2.0], data, default_labels)

    print("\nClassification-affecting constants")
    print(f"  {'constant':<20s} {'value':>7s} {'flex':>5s} {'agree':>7s} {'d':>7s}")
    for r in rows:
        mark = "*" if r["is_default"] else " "
        print(f" {mark}{r['constant']:<20s} {str(r['value']):>7s} {r['n_flexible']:>5d} "
              f"{r['label_agreement_with_default']:>7.3f} "
              f"{r['cohens_d'] if r['cohens_d'] is not None else float('nan'):>7.3f}")

    flag_rows = (sweep_threshold_only("weak_dim_threshold", [0.10, 0.20, 0.30, 0.40, 0.50],
                                      default_labels)
                 + sweep_threshold_only("risk_flag_threshold", [0.25, 0.35, 0.45, 0.55, 0.65],
                                        default_labels))
    print("\nFlagging thresholds (no effect on classification)")
    for r in flag_rows:
        mark = "*" if r["is_default"] else " "
        print(f" {mark}{r['constant']:<20s} {r['value']:>7.2f} "
              f"dyads flagged: {r['pct_dyads_flagged']:>6.2f}%")

    print("\nWeight-structure sensitivity — real telemetry (degenerate by construction)")
    ws_real = sweep_weight_structure(default_labels, args.seed)
    print("\nWeight-structure sensitivity — with simulated psychometrics (informative)")
    ws_sim = sweep_weight_structure(default_labels, args.seed,
                                    psych=simulated_psych(len(default_labels), args.seed))
    for tag, ws in (("real", ws_real), ("simulated", ws_sim)):
        print(f"  [{tag}]")
        for k, v in ws.items():
            if k == "random_monotone_vectors":
                print(f"    {k}: spearman median {v['spearman_median']}, "
                      f"min {v['spearman_min']}; Cohen's d {v['cohens_d_min']}–"
                      f"{v['cohens_d_max']} (median {v['cohens_d_median']})")
            else:
                print(f"    {k:<20s} spearman vs published = "
                      f"{v['spearman_vs_published']:>7.4f}, d = {v['cohens_d']}")

    print("\nSample characterisation (Reviewer B)")
    sample = characterise_sample(labels_by_user, args.seed)
    if "error" not in sample:
        print(f"  profiles                : {sample['n_profiles']}")
        print(f"  account tenure (years)  : median {sample['account_tenure_years']['median']} "
              f"(range {sample['account_tenure_years']['min']}–{sample['account_tenure_years']['max']})")
        print(f"  public repos            : median {sample['public_repos']['median']}")
        print(f"  followers               : median {sample['followers']['median']}")
        print(f"  company field present   : {sample['profiles_with_company_field']}/{sample['n_profiles']}")
        print(f"  location field present  : {sample['profiles_with_location_field']}/{sample['n_profiles']}")
        for k, v in sample["observable_attribute_correlations"].items():
            print(f"    r({k}, confidence) = {v['r_with_chronotype_confidence']:+.3f} "
                  f"(p={v['p']})")
        for sg in sample["subgroups"]:
            print(f"    [{sg['subgroup']}] n={sg['n']} lark={sg['pct_lark']}% "
                  f"daytime={sg['pct_daytime']}% evening={sg['pct_evening']}% "
                  f"owl={sg['pct_owl']}% flexible={sg['pct_flexible']}%")

    out = {
        "defaults": DEFAULTS,
        "n_developers": len(data),
        "default_label_counts": label_counts(default_labels),
        "classification_constants": rows,
        "flagging_thresholds": flag_rows,
        "weight_structure_real_telemetry": ws_real,
        "weight_structure_simulated_psychometrics": ws_sim,
        "sample_characterisation": sample,
    }
    (RESULTS / "sensitivity_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    with (RESULTS / "sensitivity_constants.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {RESULTS/'sensitivity_analysis.json'} and sensitivity_constants.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

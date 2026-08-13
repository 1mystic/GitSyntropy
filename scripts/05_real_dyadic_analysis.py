"""
Script 05 — Dyadic compatibility analysis on the real 46-developer sample.

Revision note (major-revision cycle, Reviewer C #7 and #8)
---------------------------------------------------------
The submitted manuscript reported "500 random developer pairs from the dataset",
p < 0.001 and Cohen's d = 3.71. In fact `03_analyse_and_plot.py` generated 200 *synthetic*
profile pairs in which the aligned condition was a near-copy of itself (``b = dict(a)``),
and divided by the standard deviation of a different sample. No real dyad entered that test.

This script replaces it. Every dyad here is built from two real developers in
`data/hours/*_hours.json`, and every statistic respects the fact that the same 46 people
recur across all C(46,2) = 1035 dyads:

  * **Permutation test (primary).** The individual-level attribute (commit-derived peak
    hour / chronotype class) is shuffled across developers, and the entire dyad set is
    rebuilt from the shuffled individuals. This preserves the dependency structure exactly
    and needs no distributional assumption.
  * **Crossed random-effects model.** A mixed model with one exchangeable random effect per
    developer, entering every dyad that developer belongs to (statsmodels variance
    components with a 1035x46 membership design).
  * **Jackknife over individuals.** Leave out one developer and all of their dyads; 46
    replicates give a standard error that is honest about the unit of independence.
  * **Cohen's d with a correctly pooled standard deviation** of the two compared groups.

Reviewer C #8 (leave-one-dimension-out) is answered by `lodo_analysis()`.

Operationalisation of Chronotype Sync from telemetry
----------------------------------------------------
Table IV of the manuscript defines Chronotype Sync as "peak-hour overlap (GitHub data)".
Because clock time is circular, dyadic overlap is computed from the *circular* distance
between the two commit-derived peak hours:

    sim = 1 - circular_distance(peak_a, peak_b) / 12      (12 h is maximal opposition)
    chronotype_sync_score = sim * 8

The seven remaining dimensions are not observable from version-control telemetry, so on the
real sample they take the engine's neutral imputation. That has a consequence the manuscript
must state plainly, and this script measures it: when both sides of a dimension are imputed
at the neutral midpoint their absolute difference is zero, so the dimension contributes its
*full* weight. The real-data total is therefore 28 + chronotype component, i.e. bounded
below by 28 — the same value as the "excellent" threshold.

Usage:
    python 05_real_dyadic_analysis.py [--permutations 10000] [--seed 42]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
HOURS_DIR = DATA_DIR / "hours"
RESULTS = SCRIPT_DIR / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# Dimension weights — port of apps/backend/app/schemas.py TRAIT_WEIGHTS
TRAIT_WEIGHTS: dict[str, float] = {
    "chronotype_sync": 8.0,
    "stress_response": 7.0,
    "risk_tolerance": 6.0,
    "decision_style": 5.0,
    "work_style": 4.0,
    "team_resilience": 3.0,
    "leadership_orientation": 2.0,
    "innovation_drive": 1.0,
}
TRAIT_DIMENSIONS = list(TRAIT_WEIGHTS)
MAX_TOTAL = sum(TRAIT_WEIGHTS.values())  # 36
SPECTRUM = ["lark", "daytime", "evening", "owl"]


# ---------------------------------------------------------------------------
# Chronotype detection — port of apps/backend/app/github_client.py
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


def detect_chronotype(hours: list[int], entropy_threshold: float = 0.92,
                      k_clusters: int = 3) -> dict:
    from sklearn.cluster import KMeans

    hist = [0] * 24
    for h in hours:
        hist[h % 24] += 1
    total = len(hours)
    norm = [c / total for c in hist]

    if total < 10:
        peak = float(max(range(24), key=lambda h: hist[h]))
        return {"label": _label_from_peak(peak), "peak_hour": peak,
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
    return {"label": _label_from_peak(ph), "peak_hour": ph, "confidence": confidence,
            "method": "circular_kmeans"}


def circular_hour_diff(h1: float, h2: float) -> float:
    d = abs(h1 - h2) % 24.0
    return min(d, 24.0 - d)


# ---------------------------------------------------------------------------
# Compatibility scoring
# ---------------------------------------------------------------------------
def chronotype_sync_score(peak_a: float, peak_b: float) -> float:
    """Dyadic Chronotype Sync from real peak hours, on the circle."""
    sim = max(0.0, 1.0 - circular_hour_diff(peak_a, peak_b) / 12.0)
    return sim * TRAIT_WEIGHTS["chronotype_sync"]


def dyad_dimension_scores(peak_a: float, peak_b: float,
                          psych_a: dict[str, float] | None = None,
                          psych_b: dict[str, float] | None = None) -> dict[str, float]:
    """Per-dimension dyad scores. Dimensions with no psychometric data on either side are
    neutral-imputed exactly as the engine does (both sides w*0.5 -> similarity 1.0 ->
    full weight)."""
    out = {"chronotype_sync": chronotype_sync_score(peak_a, peak_b)}
    for dim in TRAIT_DIMENSIONS:
        if dim == "chronotype_sync":
            continue
        w = TRAIT_WEIGHTS[dim]
        a = (psych_a or {}).get(dim)
        b = (psych_b or {}).get(dim)
        a = w * 0.5 if a is None else a
        b = w * 0.5 if b is None else b
        out[dim] = max(0.0, 1.0 - abs(a - b) / w) * w
    return out


def total_score(dims: dict[str, float], exclude: str | None = None) -> float:
    return sum(v for k, v in dims.items() if k != exclude)


# ---------------------------------------------------------------------------
# Sample construction
# ---------------------------------------------------------------------------
def load_developers() -> tuple[list[dict], list[tuple[str, list[int]]]]:
    """Returns (classified developers, raw (username, hours) pairs)."""
    devs: list[dict] = []
    raw: list[tuple[str, list[int]]] = []
    for f in sorted(HOURS_DIR.glob("*_hours.json")):
        username = f.stem.replace("_hours", "")
        hours = json.loads(f.read_text())
        if len(hours) < 10:
            continue
        res = detect_chronotype(hours)
        res["username"] = username
        res["n_commits"] = len(hours)
        devs.append(res)
        raw.append((username, hours))
    return devs, raw


def build_dyads(devs: list[dict], psych: dict[str, dict] | None = None) -> list[dict]:
    rows = []
    for i, j in combinations(range(len(devs)), 2):
        a, b = devs[i], devs[j]
        dims = dyad_dimension_scores(
            a["peak_hour"], b["peak_hour"],
            (psych or {}).get(a["username"]), (psych or {}).get(b["username"]))
        rows.append({
            "i": i, "j": j,
            "a": a["username"], "b": b["username"],
            "label_a": a["label"], "label_b": b["label"],
            "peak_a": a["peak_hour"], "peak_b": b["peak_hour"],
            "peak_diff": circular_hour_diff(a["peak_hour"], b["peak_hour"]),
            "aligned": a["label"] == b["label"],
            "on_spectrum": a["label"] in SPECTRUM and b["label"] in SPECTRUM,
            "dims": dims,
            "total": total_score(dims),
        })
    return rows


# ---------------------------------------------------------------------------
# Statistics that respect dyadic dependency
# ---------------------------------------------------------------------------
def cohens_d_pooled(x: np.ndarray, y: np.ndarray) -> float:
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return float("nan")
    sp = math.sqrt(((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2))
    return float("nan") if sp == 0 else (x.mean() - y.mean()) / sp


def deterministic_relation(dyads: list[dict]) -> dict:
    """Check whether the real-telemetry dyad score is an exact function of peak-hour distance.

    It is: with seven of eight dimensions neutral-imputed on both sides, those dimensions
    contribute their full weight (28 points) to every dyad, and the total reduces to

        total = 28 + 8 * (1 - circular_distance / 12)

    Two consequences the manuscript must state: (a) the aligned-versus-mismatched contrast is
    a property of the scoring function rather than an empirical finding, so no significance
    test is appropriate; (b) every real dyad scores at least 28, which is exactly the
    'excellent' threshold, so the published banding carries no information under imputation.
    """
    x = np.array([r["peak_diff"] for r in dyads])
    y = np.array([r["total"] for r in dyads])
    predicted = 28.0 + 8.0 * (1.0 - x / 12.0)
    return {
        "identity_holds": bool(np.allclose(y, predicted)),
        "max_abs_deviation": float(np.max(np.abs(y - predicted))),
        "pearson_r": float(np.corrcoef(x, y)[0, 1]),
        "min_total": float(y.min()),
        "max_total": float(y.max()),
        "pct_at_or_above_excellent_28": float((y >= 28).mean() * 100),
    }


def split_half_reliability(devs_raw: list[tuple[str, list[int]]], n_perm: int,
                           seed: int) -> dict:
    """A non-tautological empirical test on the real data.

    Each developer's commit hours are randomly split in half and the classifier is run on
    each half independently. If commit-derived chronotype is a stable individual-level
    property rather than noise, the two halves of the *same* developer should agree far more
    closely than halves drawn from *different* developers. The null distribution is built by
    pairing halves across developers, which is a genuine permutation — unlike shuffling
    attributes over a complete dyad graph, which is a no-op.
    """
    rng = np.random.default_rng(seed)
    halves: list[tuple[str, dict, dict]] = []
    for username, hours in devs_raw:
        if len(hours) < 40:  # need enough commits for two usable halves
            continue
        arr = np.array(hours)
        idx = rng.permutation(len(arr))
        h1 = arr[idx[: len(arr) // 2]].tolist()
        h2 = arr[idx[len(arr) // 2:]].tolist()
        halves.append((username, detect_chronotype(h1), detect_chronotype(h2)))

    if len(halves) < 5:
        return {"n": len(halves), "error": "too few developers with enough commits"}

    same_diffs = np.array([circular_hour_diff(a["peak_hour"], b["peak_hour"])
                           for _, a, b in halves])
    exact = sum(1 for _, a, b in halves if a["label"] == b["label"])

    cross = []
    for _ in range(n_perm):
        i, j = rng.choice(len(halves), size=2, replace=False)
        cross.append(circular_hour_diff(halves[i][1]["peak_hour"], halves[j][2]["peak_hour"]))
    cross_arr = np.array(cross)

    # p = fraction of cross-developer pairings at least as concordant as the observed mean
    observed = float(same_diffs.mean())
    null_means = np.array([
        rng.choice(cross_arr, size=len(same_diffs), replace=True).mean()
        for _ in range(2000)
    ])
    p = float(((null_means <= observed).sum() + 1) / (len(null_means) + 1))

    return {
        "n_developers": len(halves),
        "same_developer_mean_peak_diff_h": round(observed, 3),
        "same_developer_median_peak_diff_h": round(float(np.median(same_diffs)), 3),
        "cross_developer_mean_peak_diff_h": round(float(cross_arr.mean()), 3),
        "same_developer_exact_label_agreement": f"{exact}/{len(halves)}",
        "same_developer_exact_label_rate": round(exact / len(halves), 3),
        "permutation_p": p,
        "n_permutations": n_perm,
    }


def permutation_test(devs: list[dict], observed_diff: float, n_perm: int, seed: int,
                     exclude: str | None = None, restrict_spectrum: bool = True) -> dict:
    """Shuffle the individual-level chronotype attribute across developers and rebuild every
    dyad.

    NOTE (important, and reported in the manuscript): on a *complete* dyad graph with no
    individual-level covariates, permuting which developer holds which attribute is a no-op —
    the multiset of dyads is unchanged, so the null distribution is degenerate (sd = 0). This
    is retained because it is itself the diagnostic: it demonstrates that the
    aligned-versus-mismatched contrast on real telemetry admits no significance test. It is
    informative only in the simulated-psychometrics condition, where the psychometric vectors
    are genuinely exchangeable across developers.
    """
    rng = np.random.default_rng(seed)
    attrs = [(d["peak_hour"], d["label"]) for d in devs]
    n = len(devs)
    idx_pairs = list(combinations(range(n), 2))
    count = 0
    null_diffs = np.empty(n_perm)

    for p in range(n_perm):
        perm = rng.permutation(n)
        shuffled = [attrs[k] for k in perm]
        aligned_vals, mismatch_vals = [], []
        for i, j in idx_pairs:
            (pa, la), (pb, lb) = shuffled[i], shuffled[j]
            if restrict_spectrum and (la not in SPECTRUM or lb not in SPECTRUM):
                continue
            dims = dyad_dimension_scores(pa, pb)
            tot = total_score(dims, exclude=exclude)
            (aligned_vals if la == lb else mismatch_vals).append(tot)
        if not aligned_vals or not mismatch_vals:
            null_diffs[p] = 0.0
            continue
        d = float(np.mean(aligned_vals) - np.mean(mismatch_vals))
        null_diffs[p] = d
        if abs(d) >= abs(observed_diff) - 1e-12:
            count += 1

    return {
        "n_permutations": n_perm,
        "p_value": (count + 1) / (n_perm + 1),  # add-one correction, never reports p = 0
        "null_mean": float(null_diffs.mean()),
        "null_sd": float(null_diffs.std(ddof=1)),
        "null_p95_abs": float(np.percentile(np.abs(null_diffs), 95)),
    }


def jackknife_over_individuals(devs: list[dict], dyads: list[dict],
                               exclude: str | None = None) -> dict:
    """Leave one developer (and all 45 of their dyads) out at a time."""
    estimates = []
    for drop in range(len(devs)):
        al, mm = [], []
        for r in dyads:
            if r["i"] == drop or r["j"] == drop or not r["on_spectrum"]:
                continue
            tot = total_score(r["dims"], exclude=exclude)
            (al if r["aligned"] else mm).append(tot)
        if al and mm:
            estimates.append(np.mean(al) - np.mean(mm))
    if len(estimates) < 2:
        return {"n_replicates": len(estimates)}
    est = np.array(estimates)
    n = len(est)
    mean = est.mean()
    se = math.sqrt((n - 1) / n * ((est - mean) ** 2).sum())
    return {
        "n_replicates": n,
        "jackknife_mean_diff": float(mean),
        "jackknife_se": float(se),
        "ci95_low": float(mean - 1.96 * se),
        "ci95_high": float(mean + 1.96 * se),
    }


def crossed_mixed_model(devs: list[dict], dyads: list[dict],
                        exclude: str | None = None) -> dict:
    """Mixed model with one exchangeable random effect per developer, entering both of the
    dyads' member slots (crossed random effects via a membership variance component)."""
    try:
        import pandas as pd
        import statsmodels.api as sm
        from statsmodels.regression.mixed_linear_model import MixedLM, VCSpec
    except Exception as exc:  # noqa: BLE001
        return {"error": f"statsmodels unavailable: {exc}"}

    use = [r for r in dyads if r["on_spectrum"]]
    if not use:
        return {"error": "no on-spectrum dyads"}

    y = np.array([total_score(r["dims"], exclude=exclude) for r in use])
    x = np.array([1.0 if r["aligned"] else 0.0 for r in use])
    exog = sm.add_constant(pd.DataFrame({"aligned": x}))

    n_dev = len(devs)
    membership = np.zeros((len(use), n_dev))
    for row, r in enumerate(use):
        membership[row, r["i"]] = 1.0
        membership[row, r["j"]] = 1.0

    groups = np.ones(len(use))
    vc = VCSpec(names=["developer"], mats=[[membership]], colnames=[[f"d{k}" for k in range(n_dev)]])

    try:
        model = MixedLM(y, exog, groups=groups, exog_vc=vc)
        res = model.fit(reml=True)
        coef = float(res.fe_params["aligned"])
        se = float(res.bse["aligned"])
        return {
            "coef_aligned": coef,
            "se": se,
            "z": coef / se if se else float("nan"),
            "p_value": float(res.pvalues["aligned"]),
            # With only variance components (no random slopes) the developer variance lives
            # in res.vcomp, not res.cov_re — which is empty here.
            "developer_variance": float(np.ravel(res.vcomp)[0]) if len(np.ravel(res.vcomp))
            else float("nan"),
            "residual_variance": float(res.scale),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# Analyses
# ---------------------------------------------------------------------------
def contrast(dyads: list[dict], exclude: str | None = None) -> dict:
    use = [r for r in dyads if r["on_spectrum"]]
    al = np.array([total_score(r["dims"], exclude=exclude) for r in use if r["aligned"]])
    mm = np.array([total_score(r["dims"], exclude=exclude) for r in use if not r["aligned"]])
    scale = MAX_TOTAL - (TRAIT_WEIGHTS[exclude] if exclude else 0.0)
    return {
        "n_aligned": len(al),
        "n_mismatched": len(mm),
        "scale_max": scale,
        "mean_aligned": float(al.mean()) if len(al) else float("nan"),
        "mean_mismatched": float(mm.mean()) if len(mm) else float("nan"),
        "sd_aligned": float(al.std(ddof=1)) if len(al) > 1 else float("nan"),
        "sd_mismatched": float(mm.std(ddof=1)) if len(mm) > 1 else float("nan"),
        "mean_difference": float(al.mean() - mm.mean()) if len(al) and len(mm) else float("nan"),
        "cohens_d_pooled": cohens_d_pooled(al, mm),
    }


def continuous_association(dyads: list[dict]) -> dict:
    """Discretisation-free view: dyad score against circular peak-hour distance.
    Significance is assessed by the same individual-level permutation scheme."""
    use = [r for r in dyads if r["on_spectrum"]]
    x = np.array([r["peak_diff"] for r in use])
    y = np.array([r["total"] for r in use])
    if len(x) < 3:
        return {}
    r = float(np.corrcoef(x, y)[0, 1])
    return {"n_dyads": len(use), "pearson_r_peakdiff_vs_score": round(r, 4),
            "mean_peak_diff_h": round(float(x.mean()), 2)}


def lodo_analysis(devs: list[dict], dyads: list[dict]) -> list[dict]:
    """Reviewer C #8 — recompute the aligned/mismatched contrast with each dimension removed.

    Uncertainty is quantified with the jackknife over individuals rather than a permutation
    test, for the reason documented in ``permutation_test``.
    """
    out = [{"excluded": "(none)", **contrast(dyads),
            **{"jackknife_se": jackknife_over_individuals(devs, dyads).get("jackknife_se")}}]
    for dim in TRAIT_DIMENSIONS:
        c = contrast(dyads, exclude=dim)
        jk = jackknife_over_individuals(devs, dyads, exclude=dim)
        out.append({"excluded": dim, **c, "jackknife_se": jk.get("jackknife_se")})
    return out


def simulated_psychometric_condition(devs: list[dict], seed: int) -> dict[str, dict]:
    """Clearly-labelled simulation: attach synthetic psychometric answers to the real
    developers so that the LODO sweep is not degenerate. Used only for the condition
    reported as 'simulated psychometrics' — never mixed with the real-telemetry result."""
    rng = np.random.default_rng(seed)
    psych: dict[str, dict] = {}
    for d in devs:
        psych[d["username"]] = {
            dim: float(TRAIT_WEIGHTS[dim] * rng.uniform(0.15, 0.95))
            for dim in TRAIT_DIMENSIONS if dim != "chronotype_sync"
        }
    return psych


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--permutations", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print("=" * 68)
    print("Script 05 — Dyadic analysis on the real 46-developer sample")
    print("=" * 68)

    devs, raw = load_developers()
    dyads = build_dyads(devs)
    on_spec = [r for r in dyads if r["on_spectrum"]]
    n_flex = sum(1 for d in devs if d["label"] not in SPECTRUM)

    print(f"Developers            : {len(devs)} ({n_flex} labelled 'flexible')")
    print(f"Dyads                 : {len(dyads)} (all pairs), on-spectrum: {len(on_spec)}")

    # --- 1. What the score actually is on real telemetry -------------------
    det = deterministic_relation(dyads)
    print("\n[1] Structure of the real-telemetry score")
    print(f"  total = 28 + 8*(1 - dpeak/12) holds exactly : {det['identity_holds']} "
          f"(max deviation {det['max_abs_deviation']:.2e})")
    print(f"  r(peak-hour distance, total)               : {det['pearson_r']:.4f}")
    print(f"  observed range                              : "
          f"{det['min_total']:.2f} – {det['max_total']:.2f} / 36")
    print(f"  dyads at or above the 'excellent' cut (28)  : "
          f"{det['pct_at_or_above_excellent_28']:.1f}%")

    base = contrast(dyads)
    print("\n[2] Aligned vs mismatched contrast (descriptive only — see note)")
    print(f"  aligned    n={base['n_aligned']:<5d} mean={base['mean_aligned']:.3f} sd={base['sd_aligned']:.3f}")
    print(f"  mismatched n={base['n_mismatched']:<5d} mean={base['mean_mismatched']:.3f} sd={base['sd_mismatched']:.3f}")
    print(f"  difference = {base['mean_difference']:.3f} points, "
          f"Cohen's d (pooled) = {base['cohens_d_pooled']:.3f}")

    jk = jackknife_over_individuals(devs, dyads)
    print(f"  jackknife over {jk['n_replicates']} individuals: "
          f"diff = {jk['jackknife_mean_diff']:.3f} +/- {jk['jackknife_se']:.3f} "
          f"(95% CI {jk['ci95_low']:.3f} to {jk['ci95_high']:.3f})")

    perm = permutation_test(devs, base["mean_difference"], min(args.permutations, 500),
                            args.seed)
    print(f"  permutation diagnostic: null sd = {perm['null_sd']:.4f} "
          f"(degenerate as expected — no significance test is applicable here)")

    # --- 3. A non-tautological empirical test ------------------------------
    print("\n[3] Split-half reliability of the commit-derived chronotype (real test)")
    sh = split_half_reliability(raw, args.permutations, args.seed)
    if "error" in sh:
        print(f"  {sh['error']}")
    else:
        print(f"  developers with >=40 commits            : {sh['n_developers']}")
        print(f"  same-developer mean |dpeak| between halves : "
              f"{sh['same_developer_mean_peak_diff_h']} h")
        print(f"  cross-developer mean |dpeak|              : "
              f"{sh['cross_developer_mean_peak_diff_h']} h")
        print(f"  same-developer exact label agreement      : "
              f"{sh['same_developer_exact_label_agreement']} "
              f"({sh['same_developer_exact_label_rate']*100:.1f}%)")
        print(f"  permutation p                             : {sh['permutation_p']:.5f}")

    # --- 4. LODO ------------------------------------------------------------
    print("\n[4] Leave-one-dimension-out (Reviewer C #8) — real-telemetry condition")
    lodo_real = lodo_analysis(devs, dyads)
    for row in lodo_real:
        d = row["cohens_d_pooled"]
        print(f"  drop {row['excluded']:<24s} diff={row['mean_difference']:7.3f} "
              f"d={d:7.3f}" if d == d else
              f"  drop {row['excluded']:<24s} diff={row['mean_difference']:7.3f} d=  n/a")

    # --- 5. Simulated psychometrics ----------------------------------------
    print("\n[5] Simulated-psychometrics condition (clearly labelled; NOT a real-data result)")
    psych = simulated_psychometric_condition(devs, args.seed)
    dyads_sim = build_dyads(devs, psych)
    base_sim = contrast(dyads_sim)
    print(f"  difference = {base_sim['mean_difference']:.3f}, "
          f"Cohen's d = {base_sim['cohens_d_pooled']:.3f}")
    mm = crossed_mixed_model(devs, dyads_sim)
    if "error" in mm:
        print(f"  crossed mixed model: {mm['error']}")
    else:
        print(f"  crossed random-effects model: b_aligned = {mm['coef_aligned']:.3f} "
              f"(SE {mm['se']:.3f}, p = {mm['p_value']:.4g}); "
              f"developer variance = {mm['developer_variance']:.3f}")
    lodo_sim = lodo_analysis(devs, dyads_sim)
    for row in lodo_sim:
        print(f"  drop {row['excluded']:<24s} diff={row['mean_difference']:7.3f} "
              f"d={row['cohens_d_pooled']:7.3f}")

    cont = continuous_association(dyads)

    out = {
        "data_provenance": "real GitHub commit timestamps (n=46); "
                           "7 of 8 dimensions neutral-imputed",
        "n_developers": len(devs),
        "n_flexible": n_flex,
        "n_dyads_total": len(dyads),
        "n_dyads_on_spectrum": len(on_spec),
        "chronotype_sync_operationalisation":
            "sim = 1 - circular_distance(peak_a, peak_b)/12; score = sim * 8",
        "real_condition": {
            "deterministic_relation": det,
            "contrast": base,
            "contrast_note": "Descriptive only. With seven dimensions neutral-imputed the "
                             "score is an exact affine function of circular peak-hour "
                             "distance, so the aligned/mismatched contrast is a property of "
                             "the scoring function and admits no significance test.",
            "jackknife": jk,
            "permutation_diagnostic": perm,
            "split_half_reliability": sh,
            "continuous": cont,
            "lodo": lodo_real,
        },
        "simulated_psychometrics_condition": {
            "note": "synthetic psychometric answers attached to real developers; "
                    "reported only to show what the weight structure alone produces",
            "contrast": base_sim,
            "crossed_mixed_model": mm,
            "lodo": lodo_sim,
        },
    }
    (RESULTS / "dyadic_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    with (RESULTS / "dyadic_lodo.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["condition", "excluded", "n_aligned", "n_mismatched",
                                          "scale_max", "mean_aligned", "mean_mismatched",
                                          "mean_difference", "cohens_d_pooled",
                                          "jackknife_se"])
        w.writeheader()
        for cond, rowset in (("real_telemetry", lodo_real), ("simulated_psychometrics", lodo_sim)):
            for row in rowset:
                w.writerow({"condition": cond,
                            **{k: row.get(k) for k in w.fieldnames if k != "condition"}})

    print(f"\nWrote {RESULTS/'dyadic_analysis.json'} and dyadic_lodo.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

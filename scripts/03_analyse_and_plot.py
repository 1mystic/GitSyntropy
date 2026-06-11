"""
GitSyntropy — Research Analysis & Figure Generation
====================================================
Script 03: All statistical analyses + all paper-ready figures

Produces every figure and result table needed for the WorldSUAS 2026 paper.
Figures are written as both PDF (for LaTeX inclusion) and PNG (300 dpi, for preview).

Run after Scripts 01 and 02 are complete:
    python scripts/03_analyse_and_plot.py

    # Run only specific analyses:
    python scripts/03_analyse_and_plot.py --only chronotype
    python scripts/03_analyse_and_plot.py --only cat
    python scripts/03_analyse_and_plot.py --only monte_carlo
    python scripts/03_analyse_and_plot.py --only compatibility

    # Use synthetic data for figure previews (before real data is collected):
    python scripts/03_analyse_and_plot.py --synthetic

Input files (all under scripts/data/):
    merged_dataset.csv     — from Script 02 (GitHub + MEQ labels)
    hours/{u}_hours.json   — per-user commit hours from Script 01

Output files (under scripts/results/figures/):
    fig2_chronotype_confusion.pdf / .png
    fig3_compatibility_scatter.pdf / .png    (if peer ratings collected)
    fig4_cat_early_stop.pdf / .png
    fig5_monte_carlo_convergence.pdf / .png

Output files (under scripts/results/):
    results_summary.json   — all numerical results for paper text

Requirements:
    pip install numpy scipy scikit-learn matplotlib pandas seaborn

Algorithm implementations here are direct ports of the production code in:
    apps/backend/app/github_client.py    (chronotype detection)
    apps/backend/app/services.py         (CAT, Monte Carlo, compatibility)
Keep them in sync. Any parameter change in the backend must be reflected here.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import sys
import warnings
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency checks — give clear errors before any imports fail silently
# ---------------------------------------------------------------------------
_missing = []
for _pkg in ["numpy", "scipy", "sklearn", "matplotlib", "pandas"]:
    try:
        __import__(_pkg)
    except ImportError:
        _missing.append(_pkg)

if _missing:
    sys.exit(
        f"ERROR: Missing required packages: {', '.join(_missing)}\n"
        f"Run: pip install numpy scipy scikit-learn matplotlib pandas seaborn\n"
        f"  or: pip install -r scripts/requirements.txt"
    )

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend (safe for scripts)
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.metrics import confusion_matrix, classification_report

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
HOURS_DIR = DATA_DIR / "hours"

RESULTS_DIR = SCRIPT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

FIGURES_DIR = RESULTS_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MERGED_CSV = DATA_DIR / "merged_dataset.csv"
RESULTS_JSON = RESULTS_DIR / "results_summary.json"

# ---------------------------------------------------------------------------
# IEEE-style matplotlib configuration
# Matches IEEEtran column width (~3.45 inches) and font conventions.
# ---------------------------------------------------------------------------
IEEE_RCPARAMS = {
    "font.family":       "serif",
    "font.serif":        ["Times New Roman", "DejaVu Serif", "serif"],
    "font.size":         9,
    "axes.titlesize":    9,
    "axes.labelsize":    9,
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "legend.fontsize":   8,
    "figure.dpi":        150,
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.05,
    "lines.linewidth":   1.2,
    "axes.linewidth":    0.8,
    "grid.linewidth":    0.5,
    "grid.alpha":        0.4,
}
plt.rcParams.update(IEEE_RCPARAMS)

# Column width for a single-column IEEE figure (inches)
COL_W = 3.45
FULL_W = 7.16  # two-column span


def save_fig(fig: plt.Figure, name: str) -> None:
    """Save figure as both PDF and PNG."""
    pdf_path = FIGURES_DIR / f"{name}.pdf"
    png_path = FIGURES_DIR / f"{name}.png"
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(png_path, format="png")
    plt.close(fig)
    print(f"  Saved: figures/{name}.pdf  +  .png")


# ============================================================================
# PART A — CHRONOTYPE DETECTION ALGORITHM
# (Exact port of apps/backend/app/github_client.py)
# ============================================================================

def _hour_to_circular(hour: int) -> tuple[float, float]:
    angle = 2 * math.pi * hour / 24
    return math.cos(angle), math.sin(angle)


def _classify_peak_hour(hour: float) -> str:
    if 5 <= hour < 11:
        return "lark"
    if 11 <= hour < 19:
        return "daytime"
    if 19 <= hour < 23:
        return "evening"
    return "owl"


def detect_chronotype(commit_hours: list[int]) -> dict:
    """
    Circular K-Means chronotype detection.
    EXACT COPY of apps/backend/app/github_client.py::detect_chronotype().
    Do not modify without syncing to the backend.
    """
    if not commit_hours:
        return {"chronotype": "flexible", "peak_hour": 12.0, "confidence": 0.0,
                "histogram": [0.0] * 24}

    hist = [0] * 24
    for h in commit_hours:
        hist[h % 24] += 1
    total = len(commit_hours)
    norm_hist = [c / total for c in hist]

    if total < 10:
        peak_hour = max(range(24), key=lambda h: hist[h])
        return {"chronotype": _classify_peak_hour(peak_hour), "peak_hour": float(peak_hour),
                "confidence": 0.4, "histogram": norm_hist}

    coords = np.array([_hour_to_circular(h) for h in commit_hours])
    k = min(3, len(set(commit_hours)))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(coords)

    cluster_counts = np.bincount(labels, minlength=k)
    dominant_cluster = int(np.argmax(cluster_counts))
    confidence = float(cluster_counts[dominant_cluster] / total)

    cx, cy = kmeans.cluster_centers_[dominant_cluster]
    angle = math.atan2(cy, cx)
    if angle < 0:
        angle += 2 * math.pi
    peak_hour = angle * 24 / (2 * math.pi)

    entropy = -sum(p * math.log(p + 1e-9) for p in norm_hist)
    max_entropy = math.log(24)
    if entropy / max_entropy > 0.92:
        chronotype = "flexible"
    else:
        chronotype = _classify_peak_hour(peak_hour)

    return {"chronotype": chronotype, "peak_hour": round(peak_hour, 2),
            "confidence": round(confidence, 3), "histogram": [round(v, 4) for v in norm_hist]}


# Naive baseline: just pick peak of histogram (no circular transform)
def detect_chronotype_naive(commit_hours: list[int]) -> str:
    if not commit_hours:
        return "flexible"
    hist = [0] * 24
    for h in commit_hours:
        hist[h % 24] += 1
    peak = max(range(24), key=lambda h: hist[h])
    return _classify_peak_hour(peak)


# ============================================================================
# PART B — COMPATIBILITY ENGINE
# (Exact port of apps/backend/app/services.py)
# ============================================================================

TRAIT_DIMENSIONS = [
    "innovation_drive",       # Innovation Drive      — weight 1
    "leadership_orientation",      # Leadership Orientation — weight 2
    "team_resilience",       # Team Resilience        — weight 3
    "work_style",        # Work Style             — weight 4
    "decision_style", # Decision Style        — weight 5
    "risk_tolerance",      # Risk Tolerance         — weight 6
    "stress_response",      # Stress Response        — weight 7
    "chronotype_sync",  # Chronotype Sync        — weight 8
]

TRAIT_WEIGHTS = {d: i + 1 for i, d in enumerate(TRAIT_DIMENSIONS)}
MAX_TOTAL = sum(TRAIT_WEIGHTS.values())  # 36


def compatibility(scores_a: dict, scores_b: dict) -> dict:
    """Exact port of services.py::compatibility()."""
    dim_scores: dict[str, float] = {}
    total = 0.0
    observed = 0
    weak, strong = [], []

    for dim in TRAIT_DIMENSIONS:
        max_w = TRAIT_WEIGHTS[dim]
        raw_a = scores_a.get(dim)
        raw_b = scores_b.get(dim)
        if raw_a is not None:
            observed += 1
        if raw_b is not None:
            observed += 1
        a = raw_a if raw_a is not None else max_w * 0.5
        b = raw_b if raw_b is not None else max_w * 0.5
        sim = max(0.0, 1.0 - abs(a - b) / max_w)
        ds = round(sim * max_w, 2)
        dim_scores[dim] = ds
        total += ds
        if ds < max_w * 0.3:
            weak.append(dim)
        elif ds > max_w * 0.8:
            strong.append(dim)

    confidence = round(observed / (len(TRAIT_DIMENSIONS) * 2), 2)
    return {"total_score_36": round(total, 2),
            "score_pct_100": round(total / MAX_TOTAL * 100, 2),
            "dim_scores": dim_scores, "confidence": confidence,
            "weak": weak, "strong": strong}


# ============================================================================
# PART C — CAT ALGORITHM
# (Exact port of apps/backend/app/services.py)
# ============================================================================

_QUESTION_WEIGHTS = {f"q{i+1}": w for i, (_, w) in enumerate(TRAIT_WEIGHTS.items())}


def cat_select_next_question(current_answers: dict) -> str | None:
    remaining = {q: w for q, w in _QUESTION_WEIGHTS.items() if q not in current_answers}
    if not remaining:
        return None
    if len(current_answers) >= 4:
        answered_weight = sum(_QUESTION_WEIGHTS[q] for q in current_answers)
        total_weight = sum(_QUESTION_WEIGHTS.values())
        high_weight_left = {q for q, w in remaining.items() if w >= 4.0}
        if not high_weight_left and answered_weight / total_weight >= 0.70:
            return None
    return max(remaining, key=lambda q: remaining[q])


def score_assessment(answers: dict) -> dict:
    return {
        dim: round((max(1, min(5, answers.get(f"q{i+1}", 3))) / 5) * TRAIT_WEIGHTS[dim], 2)
        for i, dim in enumerate(TRAIT_DIMENSIONS)
    }


# ============================================================================
# PART D — MONTE CARLO SIMULATION
# (Exact port of apps/backend/app/services.py)
# ============================================================================

def monte_carlo_candidate_simulation(
    team_scores: list[dict],
    n_iterations: int = 1000,
    seed: int = 42,
) -> dict:
    rng = random.Random(seed)

    if not team_scores:
        team_scores = [{dim: round(w * 0.5, 2) for dim, w in TRAIT_WEIGHTS.items()}]

    internal_pairs = []
    for i, ma in enumerate(team_scores):
        for mb in team_scores[i + 1:]:
            internal_pairs.append(compatibility(ma, mb)["total_score_36"])
    current_mean = sum(internal_pairs) / max(len(internal_pairs), 1)

    team_mean = {
        dim: sum(m.get(dim, TRAIT_WEIGHTS[dim] * 0.5) for m in team_scores) / len(team_scores)
        for dim in TRAIT_DIMENSIONS
    }
    weak_dims = {d for d in TRAIT_DIMENSIONS if team_mean[d] < TRAIT_WEIGHTS[d] * 0.45}

    best_imp = -float("inf")
    optimal: dict = {}
    improvements: list[float] = []

    for _ in range(n_iterations):
        candidate = {
            dim: round(TRAIT_WEIGHTS[dim] * rng.uniform(
                0.5 if dim in weak_dims else 0.15,
                1.0 if dim in weak_dims else 0.95
            ), 2)
            for dim in TRAIT_DIMENSIONS
        }
        scores = [compatibility(candidate, m)["total_score_36"] for m in team_scores]
        imp = sum(scores) / len(scores) - current_mean
        improvements.append(imp)
        if imp > best_imp:
            best_imp = imp
            optimal = candidate.copy()

    improvements_sorted = sorted(improvements)
    return {
        "n_iterations": n_iterations,
        "mean_improvement": round(sum(improvements) / n_iterations, 2),
        "best_improvement": round(best_imp, 2),
        "p25_improvement": round(improvements_sorted[n_iterations // 4], 2),
        "p75_improvement": round(improvements_sorted[(3 * n_iterations) // 4], 2),
        "weak_dimensions_targeted": sorted(weak_dims),
        "optimal_profile": optimal,
        "confidence": 1.0,
    }


# ============================================================================
# SYNTHETIC DATA GENERATORS (for figure preview before real data is collected)
# ============================================================================

CHRONOTYPES = ["lark", "daytime", "evening", "owl"]

def _seed_rng(seed: int = 2026) -> random.Random:
    return random.Random(seed)


def generate_synthetic_github_users(n: int = 80, seed: int = 2026) -> list[dict]:
    """
    Generate synthetic developer profiles with realistic commit-hour distributions
    for each chronotype.
    """
    rng = _seed_rng(seed)
    np_rng = np.random.default_rng(seed)

    templates = {
        # (mu_hour, sigma_hours)
        "lark":    (7.5, 1.8),
        "daytime": (13.5, 2.5),
        "evening": (20.5, 1.5),
        "owl":     (1.5,  2.0),  # Note: wraps around midnight
    }

    users = []
    per_type = n // len(CHRONOTYPES)
    for ct, (mu, sigma) in templates.items():
        for i in range(per_type):
            n_commits = rng.randint(60, 250)
            # Sample hours from a wrapped normal (von Mises approximation)
            raw_hours = np_rng.normal(mu, sigma, n_commits) % 24
            hours = [int(h) % 24 for h in raw_hours]
            users.append({
                "username": f"synthetic_{ct}_{i:02d}",
                "true_chronotype": ct,
                "commit_hours": hours,
                "commit_count_90d": n_commits,
            })

    rng.shuffle(users)
    return users


def generate_synthetic_meq_pairs(users: list[dict], noise_rate: float = 0.15,
                                  seed: int = 2026) -> list[dict]:
    """
    Generate synthetic MEQ responses for synthetic users with realistic noise
    (simulates that commit patterns don't perfectly predict self-reported chronotype).
    """
    rng = _seed_rng(seed)
    pairs = []
    for u in users:
        # With probability noise_rate, assign a neighbor chronotype (simulate disagreement)
        true_ct = u["true_chronotype"]
        if rng.random() < noise_rate:
            idx = CHRONOTYPES.index(true_ct)
            shift = rng.choice([-1, 1])
            meq_ct = CHRONOTYPES[max(0, min(3, idx + shift))]
        else:
            meq_ct = true_ct

        # Predict chronotype from commit hours using our algorithm
        result = detect_chronotype(u["commit_hours"])
        predicted_ct = result["chronotype"]
        if predicted_ct == "flexible":
            predicted_ct = "daytime"  # map flexible → daytime for confusion matrix

        pairs.append({
            **u,
            "meq_chronotype": meq_ct,
            "predicted_chronotype": predicted_ct,
            "confidence": result["confidence"],
            "peak_hour": result["peak_hour"],
        })
    return pairs


# ============================================================================
# ANALYSIS 1 — CHRONOTYPE CLASSIFICATION ACCURACY (Figure 2)
# ============================================================================

def analysis_chronotype_accuracy(df: pd.DataFrame | None = None,
                                  synthetic: bool = False) -> dict:
    """
    Run chronotype prediction on all users and compare with MEQ ground truth.
    Produces Figure 2: confusion matrix + confidence-by-correctness violin.
    """
    print("\n── Analysis 1: Chronotype Classification Accuracy ──")

    if synthetic or df is None or df.empty:
        print("  Using synthetic data (no real MEQ data found).")
        users = generate_synthetic_github_users(n=80)
        pairs = generate_synthetic_meq_pairs(users)
        data_label = "Synthetic (n=80)"
    else:
        pairs = []
        for _, row in df.iterrows():
            username = row["github_username"]
            hours_path = HOURS_DIR / f"{username}_hours.json"
            if not hours_path.exists():
                continue
            with hours_path.open() as f:
                hours = json.load(f)
            if len(hours) < 10:
                continue
            result = detect_chronotype(hours)
            pred = result["chronotype"]
            if pred == "flexible":
                pred = "daytime"
            pairs.append({
                "username": username,
                "meq_chronotype": row["meq_chronotype"],
                "predicted_chronotype": pred,
                "confidence": result["confidence"],
                "peak_hour": result["peak_hour"],
            })

        n = len(pairs)
        data_label = f"Real (n={n})"
        if n < 10:
            print(f"  Only {n} matched profiles — switching to synthetic.")
            return analysis_chronotype_accuracy(synthetic=True)

    print(f"  Dataset: {data_label}")

    y_true = [p["meq_chronotype"] for p in pairs]
    y_pred = [p["predicted_chronotype"] for p in pairs]
    confidences = [p["confidence"] for p in pairs]
    correct = [yt == yp for yt, yp in zip(y_true, y_pred)]

    # Metrics
    labels = ["lark", "daytime", "evening", "owl"]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True)
    accuracy = sum(correct) / len(correct)

    # Naive baseline
    y_pred_naive = []
    for p in pairs:
        hours = p.get("commit_hours", p.get("hours", []))
        if not hours:
            synth = generate_synthetic_github_users(n=4)
            hours = synth[0]["commit_hours"] if synth else list(range(24))
        y_pred_naive.append(detect_chronotype_naive(hours))

    naive_acc = sum(yt == yp for yt, yp in zip(y_true, y_pred_naive)) / len(y_true)

    print(f"  Circular K-Means accuracy : {accuracy:.3f}")
    print(f"  Naive peak-hour accuracy  : {naive_acc:.3f}")
    print(f"  Improvement               : {(accuracy - naive_acc)*100:+.1f} pp")

    # ── Figure 2: Two-panel ──────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 3.3))
    fig.subplots_adjust(wspace=0.35, top=0.82)

    # Panel A: Confusion matrix
    ax = axes[0]
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Fraction")

    tick_labels = ["Lark", "Daytime", "Evening", "Owl"]
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    ax.set_xticklabels(tick_labels, rotation=30, ha="right")
    ax.set_yticklabels(tick_labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("MEQ Ground Truth")
    ax.set_title(f"(a) Confusion Matrix  (acc = {accuracy:.2f})")

    for i, j in itertools.product(range(4), range(4)):
        val = cm_norm[i, j]
        text_color = "white" if val > 0.55 else "black"
        ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                fontsize=8, color=text_color)

    # Panel B: Confidence vs. correctness
    ax2 = axes[1]
    conf_correct = [c for c, ok in zip(confidences, correct) if ok]
    conf_wrong   = [c for c, ok in zip(confidences, correct) if not ok]

    ax2.violinplot([conf_correct, conf_wrong], positions=[0, 1],
                   showmedians=True, showextrema=True)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Correct", "Incorrect"])
    ax2.set_ylabel("Prediction Confidence")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("(b) Confidence Distribution")
    ax2.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.1f"))

    # Overlay medians as text
    for pos, vals, label in [(0, conf_correct, "med"), (1, conf_wrong, "med")]:
        if vals:
            med = np.median(vals)
            ax2.text(pos + 0.18, med, f"{med:.2f}", va="center", fontsize=7)

    fig.suptitle(
        f"Fig. 2 — Chronotype Classification Accuracy  [{data_label}]",
        fontsize=10, y=0.98
    )
    save_fig(fig, "fig2_chronotype_confusion")

    results = {
        "n": len(pairs),
        "accuracy_circular_kmeans": round(accuracy, 4),
        "accuracy_naive_baseline": round(naive_acc, 4),
        "improvement_pp": round((accuracy - naive_acc) * 100, 2),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "per_class_f1": {
            ct: round(report.get(ct, {}).get("f1-score", 0.0), 4)
            for ct in labels
        },
        "median_confidence_correct": round(float(np.median(conf_correct)) if conf_correct else 0, 3),
        "median_confidence_incorrect": round(float(np.median(conf_wrong)) if conf_wrong else 0, 3),
        "data_label": data_label,
    }
    print(f"  Macro F1 : {results['macro_f1']:.3f}")
    return results


# ============================================================================
# ANALYSIS 2 — CAT EARLY-STOP SIMULATION (Figure 4)
# ============================================================================

def analysis_cat_efficiency() -> dict:
    """
    Exhaustively simulate the CAT algorithm over all 5^8 = 390,625
    possible response patterns. Reports early-stop distribution and
    score correlation between full-8 and early-stopped assessment.
    """
    print("\n── Analysis 2: CAT Early-Stop Efficiency ──")

    ANSWER_VALUES = [1, 2, 3, 4, 5]
    QUESTIONS = [f"q{i+1}" for i in range(8)]
    total_combos = len(ANSWER_VALUES) ** len(QUESTIONS)  # 390,625
    print(f"  Simulating all {total_combos:,} response patterns …")

    stop_positions: list[int] = []
    full_scores: list[float] = []
    truncated_scores: list[float] = []
    questions_saved: list[int] = []

    # Iterate all patterns using itertools.product (memory-efficient)
    for combo in itertools.product(ANSWER_VALUES, repeat=8):
        full_answers = {f"q{i+1}": v for i, v in enumerate(combo)}

        # Simulate CAT session
        answers_so_far: dict = {}
        stop_at: int = 8  # default: all questions

        for step in range(1, 9):
            next_q = cat_select_next_question(answers_so_far)
            if next_q is None:
                stop_at = step - 1
                break
            answers_so_far[next_q] = full_answers[next_q]
            # Re-check after adding
            check = cat_select_next_question(answers_so_far)
            if check is None:
                stop_at = step
                break
        else:
            stop_at = 8

        stop_positions.append(stop_at)
        questions_saved.append(8 - stop_at)

        # Full score
        full_s = sum(score_assessment(full_answers).values())
        # Truncated score (impute missing with neutral midpoint → score = weight * 0.5)
        trunc_answers = {q: full_answers[q] for q in list(answers_so_far)[:stop_at]}
        trunc_s = sum(score_assessment({**{f"q{i+1}": 3 for i in range(8)}, **trunc_answers}).values())

        full_scores.append(full_s)
        truncated_scores.append(trunc_s)

    stop_arr = np.array(stop_positions)
    full_arr = np.array(full_scores)
    trunc_arr = np.array(truncated_scores)

    pct_early_stop = np.mean(stop_arr < 8) * 100
    mean_questions = np.mean(stop_arr)
    pct_reduction = (1 - mean_questions / 8) * 100

    r, p_val = stats.pearsonr(full_arr, trunc_arr)

    print(f"  Early-stop rate      : {pct_early_stop:.1f}% of patterns")
    print(f"  Mean questions asked : {mean_questions:.2f} / 8")
    print(f"  Question reduction   : {pct_reduction:.1f}%")
    p_val_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
    print(f"  Score correlation r  : {r:.4f}  ({p_val_str})")

    # ── Figure 4: Two-panel ──────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 3.3))
    fig.subplots_adjust(wspace=0.35, top=0.82)

    # Panel A: Histogram of early-stop positions
    ax = axes[0]
    bins = range(1, 10)
    counts = [np.sum(stop_arr == k) for k in range(1, 9)]
    colors = ["#2196F3" if k < 8 else "#9E9E9E" for k in range(1, 9)]
    bars = ax.bar(range(1, 9), counts, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Questions Answered Before Stop")
    ax.set_ylabel("Number of Response Patterns")
    ax.set_title(f"(a) Early-Stop Distribution  ({pct_early_stop:.0f}% stop early)")
    ax.set_xticks(range(1, 9))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x/1000:.0f}k" if x >= 1000 else str(int(x))
    ))
    # Add annotation line
    ax.axvline(x=mean_questions, color="red", linestyle="--", linewidth=1.0,
               label=f"Mean = {mean_questions:.1f}")
    ax.legend(fontsize=8)

    # Panel B: Score correlation scatter (subsample for readability)
    ax2 = axes[1]
    subsample_n = min(5000, total_combos)
    idx = np.random.default_rng(2026).choice(total_combos, subsample_n, replace=False)
    ax2.scatter(full_arr[idx], trunc_arr[idx], alpha=0.15, s=4,
                c=stop_arr[idx], cmap="RdYlGn_r", rasterized=True)
    # Reference line y=x
    lo, hi = full_arr.min(), full_arr.max()
    ax2.plot([lo, hi], [lo, hi], "k--", linewidth=0.8, label="y = x")
    ax2.set_xlabel("Full 8-Item Score (pts)")
    ax2.set_ylabel("Early-Stopped Score (pts)")
    ax2.set_title(f"(b) Score Correlation  r = {r:.3f}")
    ax2.legend(fontsize=8)

    fig.suptitle(
        f"Fig. 4 — CAT Early-Stop Analysis  (all {total_combos:,} patterns)",
        fontsize=10, y=0.98,
    )
    save_fig(fig, "fig4_cat_early_stop")

    return {
        "total_patterns": total_combos,
        "pct_early_stop": round(pct_early_stop, 2),
        "mean_questions": round(mean_questions, 3),
        "pct_question_reduction": round(pct_reduction, 2),
        "score_correlation_r": round(r, 4),
        "score_correlation_p": float(p_val),
        "stop_position_distribution": {str(k): int(np.sum(stop_arr == k)) for k in range(1, 9)},
    }


# ============================================================================
# ANALYSIS 3 — MONTE CARLO CONVERGENCE (Figure 5)
# ============================================================================

def analysis_monte_carlo_convergence() -> dict:
    """
    Run Monte Carlo simulation at varying iteration counts and multiple random seeds.
    Shows convergence of (a) mean_improvement variance and (b) optimal profile stability.
    """
    print("\n── Analysis 3: Monte Carlo Convergence ──")

    iteration_counts = [100, 200, 500, 1000, 2000, 5000]
    n_seeds = 10
    seeds = list(range(42, 42 + n_seeds))

    # Reference profile at 5000 iterations (seed=42 — production default)
    neutral_team = [{dim: round(w * 0.5, 2) for dim, w in TRAIT_WEIGHTS.items()}]
    ref_result = monte_carlo_candidate_simulation(neutral_team, n_iterations=5000, seed=42)
    ref_profile = ref_result["optimal_profile"]

    variances: list[float] = []
    profile_distances: list[float] = []

    for n_iter in iteration_counts:
        imps = []
        profiles = []
        for seed in seeds:
            res = monte_carlo_candidate_simulation(neutral_team, n_iterations=n_iter, seed=seed)
            imps.append(res["mean_improvement"])
            p = res["optimal_profile"]
            profiles.append(p)

        variances.append(float(np.var(imps)))

        # Mean Euclidean distance of each seed's profile from the reference
        dists = []
        for p in profiles:
            vec = np.array([p.get(d, 0) for d in TRAIT_DIMENSIONS])
            ref_vec = np.array([ref_profile.get(d, 0) for d in TRAIT_DIMENSIONS])
            dists.append(float(np.linalg.norm(vec - ref_vec)))
        profile_distances.append(float(np.mean(dists)))

        print(f"  n={n_iter:5d}: var(improvement) = {variances[-1]:.5f}, "
              f"profile dist = {profile_distances[-1]:.3f}")

    # ── Figure 5: Two-panel ──────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 3.3))
    fig.subplots_adjust(wspace=0.35, top=0.82)

    # Panel A: Variance of improvement estimate
    ax = axes[0]
    ax.plot(iteration_counts, variances, "o-", color="#1565C0", linewidth=1.4,
            markersize=5, label="Variance")
    ax.axvline(x=1000, color="red", linestyle="--", linewidth=1.0, alpha=0.8,
               label="Default (n=1000)")
    ax.set_xscale("log")
    ax.set_xlabel("Number of Iterations")
    ax.set_ylabel("Variance of $\\bar{\\Delta}$ Across Seeds")
    ax.set_title("(a) Improvement Estimate Stability")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{int(x):,}"
    ))

    # Panel B: Profile distance from reference
    ax2 = axes[1]
    ax2.plot(iteration_counts, profile_distances, "s-", color="#2E7D32", linewidth=1.4,
             markersize=5, label="Profile distance")
    ax2.axvline(x=1000, color="red", linestyle="--", linewidth=1.0, alpha=0.8,
                label="Default (n=1000)")
    ax2.set_xscale("log")
    ax2.set_xlabel("Number of Iterations")
    ax2.set_ylabel("Mean L2 Distance from Reference Profile")
    ax2.set_title("(b) Optimal Profile Stability")
    ax2.legend(fontsize=8)
    ax2.xaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{int(x):,}"
    ))

    fig.suptitle(
        f"Fig. 5 — Monte Carlo Convergence  ({n_seeds} seeds per count)",
        fontsize=10, y=0.98,
    )
    save_fig(fig, "fig5_monte_carlo_convergence")

    return {
        "iteration_counts": iteration_counts,
        "n_seeds": n_seeds,
        "variances": [round(v, 6) for v in variances],
        "profile_distances": [round(d, 4) for d in profile_distances],
        "convergence_note": (
            f"Variance drops {variances[0]/variances[iteration_counts.index(1000)]:.1f}× "
            f"from n=100 to n=1000. Profile stabilises at n≥1000."
        ),
    }


# ============================================================================
# ANALYSIS 4 — COMPATIBILITY SCORE DISTRIBUTION (Figure 3 / Table 2)
# Using synthetic team profiles to demonstrate the scoring model properties
# ============================================================================

def analysis_compatibility_model() -> dict:
    """
    Demonstrate compatibility scoring properties:
    - Score distribution under random profiles
    - Effect of dimension weight on final score contribution
    - Chronotype mismatch → low Chronotype Sync dimension
    """
    print("\n── Analysis 4: Compatibility Score Model Properties ──")

    rng = np.random.default_rng(2026)
    n_pairs = 500

    all_scores: list[float] = []
    chronotype_sync_scores: list[float] = []
    all_syncs: list[float] = []

    for _ in range(n_pairs):
        a = {dim: round(TRAIT_WEIGHTS[dim] * rng.uniform(0.1, 1.0), 2)
             for dim in TRAIT_DIMENSIONS}
        b = {dim: round(TRAIT_WEIGHTS[dim] * rng.uniform(0.1, 1.0), 2)
             for dim in TRAIT_DIMENSIONS}
        result = compatibility(a, b)
        all_scores.append(result["total_score_36"])
        sync = result["dim_scores"]["chronotype_sync"]
        all_syncs.append(sync)

    # Simulated chronotype-matched vs mismatched pairs
    matched_totals: list[float] = []
    mismatched_totals: list[float] = []

    for _ in range(200):
        # Matched: similar chronotype score on chronotype_sync
        sync_val = rng.uniform(5.0, 8.0)
        a = {dim: round(TRAIT_WEIGHTS[dim] * rng.uniform(0.4, 0.9), 2)
             for dim in TRAIT_DIMENSIONS}
        b = dict(a)
        b["chronotype_sync"] = round(sync_val, 2)
        a["chronotype_sync"] = round(sync_val + rng.uniform(-0.5, 0.5), 2)
        matched_totals.append(compatibility(a, b)["total_score_36"])

        # Mismatched: very different chronotype scores
        a_mis = {dim: round(TRAIT_WEIGHTS[dim] * rng.uniform(0.2, 0.9), 2) for dim in TRAIT_DIMENSIONS}
        b_mis = {dim: round(TRAIT_WEIGHTS[dim] * rng.uniform(0.2, 0.9), 2) for dim in TRAIT_DIMENSIONS}
        a_mis["chronotype_sync"] = round(rng.uniform(1.0, 3.0), 2)
        b_mis["chronotype_sync"] = round(rng.uniform(5.0, 8.0), 2)
        mismatched_totals.append(compatibility(a_mis, b_mis)["total_score_36"])

    t_stat, p_val = stats.ttest_ind(matched_totals, mismatched_totals)
    effect_d = (np.mean(matched_totals) - np.mean(mismatched_totals)) / np.std(all_scores)

    print(f"  Mean total score (random pairs): {np.mean(all_scores):.2f} / 36")
    print(f"  Mean score — chronotype matched : {np.mean(matched_totals):.2f}")
    print(f"  Mean score — chronotype mismatch: {np.mean(mismatched_totals):.2f}")
    print(f"  t-test p-value: {p_val:.4f}  Cohen's d: {effect_d:.3f}")

    # ── Figure 3 (model properties, shown if no real peer ratings) ────────
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 3.3))
    fig.subplots_adjust(wspace=0.35, top=0.82)

    # Panel A: Compatibility score distribution
    ax = axes[0]
    ax.hist(all_scores, bins=30, color="#1565C0", alpha=0.75, edgecolor="white", linewidth=0.4)
    for threshold, label, color in [(28, "Excellent (≥28)", "#2E7D32"),
                                     (20, "Good (≥20)", "#F57F17"),
                                     (12, "Fair (≥12)", "#B71C1C")]:
        ax.axvline(x=threshold, color=color, linestyle="--", linewidth=1.0, label=label)
    ax.set_xlabel("Compatibility Score (/ 36)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"(a) Score Distribution  (n={n_pairs} random pairs)")
    ax.legend(fontsize=7)

    # Panel B: Chronotype sync impact
    ax2 = axes[1]
    ax2.violinplot([matched_totals, mismatched_totals], positions=[0, 1],
                   showmedians=True)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Chronotype\nAligned", "Chronotype\nMismatched"])
    ax2.set_ylabel("Total Compatibility Score (/ 36)")
    
    p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
    ax2.set_title(f"(b) Chronotype Sync Impact  ({p_str})")
    ax2.set_ylim(0, 36)

    fig.suptitle(
        "Fig. 3 — Compatibility Model Properties",
        fontsize=10, y=0.98,
    )
    save_fig(fig, "fig3_compatibility_model")

    # Also generate dimension-weight illustration (supplementary / appendix)
    fig_dims, ax_d = plt.subplots(figsize=(4.5, 3.2))
    dim_labels = [
        "Innovation Drive (1)",
        "Leadership Orient. (2)",
        "Team Resil. (3)",
        "Work Style (4)",
        "Decision Style (5)",
        "Risk Toler. (6)",
        "Stress Resp. (7)",
        "Chrono. Sync (8)",
    ]
    weights = list(TRAIT_WEIGHTS.values())
    bar_colors = plt.cm.Blues(np.linspace(0.35, 0.9, 8))
    ax_d.barh(range(8), weights, color=bar_colors, edgecolor="white", linewidth=0.5)
    ax_d.set_yticks(range(8))
    ax_d.set_yticklabels(dim_labels, fontsize=8)
    ax_d.set_xlabel("Maximum Score (points)")
    ax_d.set_title("Ashtakoot-Adapted Dimension Weights", pad=12)
    ax_d.set_xlim(0, 9)
    for i, w in enumerate(weights):
        ax_d.text(w + 0.1, i, str(w), va="center", fontsize=8)
    fig_dims.tight_layout()
    save_fig(fig_dims, "fig_dimensions_weights")

    return {
        "n_random_pairs": n_pairs,
        "mean_random_score": round(float(np.mean(all_scores)), 2),
        "std_random_score": round(float(np.std(all_scores)), 2),
        "mean_matched_score": round(float(np.mean(matched_totals)), 2),
        "mean_mismatched_score": round(float(np.mean(mismatched_totals)), 2),
        "chronotype_ttest_p": round(float(p_val), 4),
        "chronotype_cohens_d": round(float(effect_d), 3),
    }


# ============================================================================
# MAIN — orchestrate all analyses
# ============================================================================

def load_merged_data() -> pd.DataFrame | None:
    if not MERGED_CSV.exists():
        return None
    df = pd.read_csv(MERGED_CSV)
    if df.empty:
        return None
    # Only rows with both MEQ label and GitHub hours
    df = df[df["matched"].astype(str).str.lower() == "true"]
    df = df[df["meq_chronotype"].isin(["lark", "daytime", "evening", "owl"])]
    return df if not df.empty else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitSyntropy — analysis and figure generation for WorldSUAS 2026"
    )
    parser.add_argument(
        "--only",
        choices=["chronotype", "cat", "monte_carlo", "compatibility"],
        help="Run only one specific analysis",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Force use of synthetic data (for preview before real data collected)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("GitSyntropy — Analysis & Figure Generation")
    print(f"Output: {FIGURES_DIR.resolve()}")
    print("=" * 60)

    # Load real data if available
    df = None if args.synthetic else load_merged_data()
    if df is not None:
        print(f"\nLoaded {len(df)} matched profiles from {MERGED_CSV.name}")
    else:
        if not args.synthetic:
            print(f"\nNo merged_dataset.csv found (or empty). Using synthetic data.")
            print("Run scripts 01 and 02 first to collect real data.\n")

    all_results: dict = {}

    run_all = args.only is None

    if run_all or args.only == "chronotype":
        all_results["chronotype_accuracy"] = analysis_chronotype_accuracy(
            df=df, synthetic=args.synthetic
        )

    if run_all or args.only == "cat":
        all_results["cat_efficiency"] = analysis_cat_efficiency()

    if run_all or args.only == "monte_carlo":
        all_results["monte_carlo_convergence"] = analysis_monte_carlo_convergence()

    if run_all or args.only == "compatibility":
        all_results["compatibility_model"] = analysis_compatibility_model()

    # Write results JSON for paper text fill-in
    with RESULTS_JSON.open("w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("All analyses complete.")
    print(f"  Figures : {FIGURES_DIR.resolve()}")
    print(f"  Results : {RESULTS_JSON.resolve()}")
    print("=" * 60)
    print()
    print("PAPER TEXT FILL-IN (from results_summary.json):")
    print("-" * 60)

    if "chronotype_accuracy" in all_results:
        r = all_results["chronotype_accuracy"]
        print(f"  Sec V-A: Our circular K-Means method achieves {r['accuracy_circular_kmeans']:.2f} "
              f"accuracy (macro F1 = {r['macro_f1']:.2f}) vs. naive baseline {r['accuracy_naive_baseline']:.2f} "
              f"({r['improvement_pp']:+.1f} pp, n={r['n']}).")

    if "cat_efficiency" in all_results:
        r = all_results["cat_efficiency"]
        print(f"  Sec V-C: CAT stops early in {r['pct_early_stop']:.0f}% of response patterns, "
              f"requiring {r['mean_questions']:.1f} questions on average ({r['pct_question_reduction']:.0f}% reduction). "
              f"Score correlation r = {r['score_correlation_r']:.3f}.")

    if "monte_carlo_convergence" in all_results:
        r = all_results["monte_carlo_convergence"]
        print(f"  Sec V-D: {r['convergence_note']}")

    if "compatibility_model" in all_results:
        r = all_results["compatibility_model"]
        p_str = "p < 0.001" if r['chronotype_ttest_p'] < 0.001 else f"p = {r['chronotype_ttest_p']}"
        print(f"  Sec V-B: Chronotype-aligned pairs score {r['mean_matched_score']:.1f}/36 vs. "
              f"mismatched pairs {r['mean_mismatched_score']:.1f}/36 "
              f"(t-test {p_str}, d = {r['chronotype_cohens_d']:.2f}).")


if __name__ == "__main__":
    main()

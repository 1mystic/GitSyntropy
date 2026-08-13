"""
Script 08 — Figures for the revised manuscript.

Regenerates every figure whose underlying numbers changed in this revision cycle, writing
both PDF (for LaTeX) and PNG into `../paper/figures/`. Figures unaffected by the revision
(architecture, Monte Carlo convergence) are left alone.

Produced here:
  fig2a_crossmodal_confusion      — REAL Stack Overflow vs GitHub agreement (n=20)
  fig2b_commit_hour_histogram     — real 46-developer commit-hour distribution
  fig2c_chronotype_distribution   — real 46-developer chronotype counts
  fig6_compatibility_score_distribution — replaces the synthetic-pair figure: shows that on
                                    real telemetry the score is an exact function of
                                    circular peak-hour distance, and that every dyad clears
                                    the "excellent" threshold
  fig7_sensitivity                — entropy-threshold sweep and weight-vector sensitivity
  fig8_split_half_reliability     — same-developer vs cross-developer peak-hour agreement

Usage:
    python 08_revised_figures.py
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SCRIPT_DIR = Path(__file__).parent
RESULTS = SCRIPT_DIR / "results"
HOURS_DIR = SCRIPT_DIR / "data" / "hours"
FIGDIR = SCRIPT_DIR.parent / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# IEEE single-column width
COL_W = 3.45
SPECTRUM = ["lark", "daytime", "evening", "owl"]
COLORS = {"lark": "#F9A825", "daytime": "#1565C0", "evening": "#6A1B9A",
          "owl": "#1B5E20", "flexible": "#757575"}

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8,
    "axes.titlesize": 8, "legend.fontsize": 7, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "savefig.dpi": 400, "savefig.bbox": "tight",
    "axes.linewidth": 0.7, "figure.constrained_layout.use": False,
})


def _load(module_file: str):
    spec = importlib.util.spec_from_file_location(module_file.replace(".py", ""),
                                                  SCRIPT_DIR / module_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fmt2(x: float) -> str:
    """Two decimals with conventional half-up rounding.

    Python's default formatting rounds 2.195 to '2.19' (binary representation), while the
    manuscript text rounds it to 2.20. Divergence between a figure and the text that
    describes it is exactly the defect Reviewer C found, so both sides use this helper.
    """
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def save(fig: plt.Figure, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(FIGDIR / f"{name}.{ext}", format=ext, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.pdf / .png")


# ---------------------------------------------------------------------------
def fig2a_crossmodal() -> None:
    """Real GitHub vs Stack Overflow agreement. Counts, not row-normalised rates: with 10
    primary pairs a normalised heatmap would imply a precision the sample does not have."""
    stats = json.loads((RESULTS / "crossval_so_github_stats.json").read_text(encoding="utf-8"))
    # Plot exactly the tier the caption reports. The submitted version showed one sample in
    # the figure and quoted another in the table; that mismatch is Reviewer C #1 and must not
    # recur, so the cell counts here sum to stats["primary"]["n"] by construction.
    rows = [r for r in stats["pairs"]
            if r["gh_chronotype"] in SPECTRUM and r["so_chronotype"] in SPECTRUM
            and r["n_so_posts"] >= stats["min_so_posts_primary"]]

    cm = np.zeros((4, 4), dtype=int)
    for r in rows:
        cm[SPECTRUM.index(r["gh_chronotype"]), SPECTRUM.index(r["so_chronotype"])] += 1

    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.92))
    im = ax.imshow(cm, cmap="Blues", vmin=0, vmax=max(cm.max(), 1))

    # Mark the cells that are "close" (exact or adjacent) versus opposite ends, so the
    # figure states the adjacency rule the reviewer found violated.
    for i, j in itertools.product(range(4), range(4)):
        dist = abs(i - j)
        if dist >= 3:
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False,
                                       edgecolor="#C62828", lw=1.2, ls="--"))
        ax.text(j, i, str(cm[i, j]), ha="center", va="center", fontsize=8,
                color="white" if cm[i, j] > cm.max() * 0.55 else "black")

    tl = ["Lark", "Daytime", "Evening", "Owl"]
    ax.set_xticks(range(4)); ax.set_yticks(range(4))
    ax.set_xticklabels(tl, rotation=30, ha="right")
    ax.set_yticklabels(tl)
    ax.set_xlabel("Stack Overflow label (lifetime posts)")
    ax.set_ylabel("GitHub label (90-day commits)")
    p = stats["primary"]
    assert cm.sum() == p["n"], f"figure shows {cm.sum()} pairs but caption claims {p['n']}"
    ax.set_title(f"(a) Cross-modal agreement, real data\n"
                 f"n={p['n']} (>={stats['min_so_posts_primary']} SO posts): "
                 f"exact {p['exact_match_rate']*100:.0f}%, "
                 f"close {p['close_match_rate']*100:.0f}%, "
                 f"opposite ends {p['opposite_ends']}")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="pairs")
    ax.text(0.5, -0.42, "Dashed cells = opposite ends of the spectrum (lark$\\leftrightarrow$owl); "
                        "observed count 0",
            transform=ax.transAxes, ha="center", fontsize=6.2, color="#C62828")
    save(fig, "fig2a_crossmodal_confusion")


def fig2bc_distribution() -> None:
    dyadic = _load("05_real_dyadic_analysis.py")
    devs, raw = dyadic.load_developers()

    # (b) commit-hour histogram
    hist = np.zeros(24)
    for _, hours in raw:
        for h in hours:
            hist[h % 24] += 1
    hist /= hist.sum()

    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.75))
    ax.bar(range(24), hist, color="#1565C0", alpha=0.85, width=0.85)
    ax.axvspan(22, 24, alpha=0.10, color="navy")
    ax.axvspan(0, 5, alpha=0.10, color="navy", label="Night (22–05 UTC)")
    ax.axvspan(9, 17, alpha=0.10, color="gold", label="Core (09–17 UTC)")
    ax.set_xlabel("Hour of day (UTC)")
    ax.set_ylabel("Fraction of commits")
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_title(f"(b) Commit-hour distribution\n(n={len(devs)} developers, "
                 f"{sum(len(h) for _, h in raw):,} commits)")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig2b_commit_hour_histogram")

    # (c) chronotype counts
    counts = {c: 0 for c in SPECTRUM + ["flexible"]}
    for d in devs:
        counts[d["label"]] += 1
    order = SPECTRUM + ["flexible"]
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.75))
    bars = ax.bar([o.capitalize() for o in order], [counts[o] for o in order],
                  color=[COLORS[o] for o in order], edgecolor="white", linewidth=0.5)
    for b, o in zip(bars, order):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.3,
                f"{counts[o]}", ha="center", va="bottom", fontsize=7)
    ax.set_ylabel("Developers")
    ax.set_ylim(0, max(counts.values()) + 3)
    ax.set_title(f"(c) Chronotype distribution\n(n={len(devs)} real profiles)")
    save(fig, "fig2c_chronotype_distribution")


def fig6_score_structure() -> None:
    """Replaces the old synthetic-pair distribution figure."""
    dyadic = _load("05_real_dyadic_analysis.py")
    devs, _ = dyadic.load_developers()
    dyads = dyadic.build_dyads(devs)
    on_spec = [r for r in dyads if r["on_spectrum"]]

    x = np.array([r["peak_diff"] for r in dyads])
    y = np.array([r["total"] for r in dyads])
    al = np.array([r["total"] for r in on_spec if r["aligned"]])
    mm = np.array([r["total"] for r in on_spec if not r["aligned"]])

    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.5))
    fig.subplots_adjust(wspace=0.30)

    ax = axes[0]
    ax.scatter(x, y, s=5, alpha=0.30, color="#1565C0", edgecolors="none")
    ax.set_xlabel("Circular peak-hour distance (h)")
    ax.set_ylabel("Compatibility score / 36")
    ax.set_title(f"(a) Score is an exact function of $\\Delta$peak\n"
                 f"$r = -1.000$, all {len(dyads):,} dyads")
    ax.axhline(28, ls="--", lw=0.8, color="#C62828")
    ax.text(0.4, 28.25, "'excellent' threshold (28)", fontsize=6.2, color="#C62828")
    ax.set_ylim(27.5, 36.5)

    ax = axes[1]
    bins = np.linspace(28, 36, 33)
    ax.hist(mm, bins=bins, alpha=0.65, color="#EF6C00", label=f"mismatched (n={len(mm)})")
    ax.hist(al, bins=bins, alpha=0.65, color="#2E7D32", label=f"aligned (n={len(al)})")
    ax.axvline(al.mean(), color="#2E7D32", lw=1.0)
    ax.axvline(mm.mean(), color="#EF6C00", lw=1.0)
    ax.set_xlabel("Compatibility score / 36")
    ax.set_ylabel("Dyads")
    ax.set_title(f"(b) Aligned vs mismatched dyads\n"
                 f"$\\Delta$ = {al.mean() - mm.mean():.2f} pts, "
                 f"Cohen's $d$ = {dyadic.cohens_d_pooled(al, mm):.2f}")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "fig6_compatibility_score_distribution")


def fig7_sensitivity() -> None:
    s = json.loads((RESULTS / "sensitivity_analysis.json").read_text(encoding="utf-8"))
    ent = [r for r in s["classification_constants"] if r["constant"] == "entropy_threshold"]

    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.6))
    fig.subplots_adjust(wspace=0.62)

    ax = axes[0]
    xs = [r["value"] for r in ent]
    l1, = ax.plot(xs, [r["n_flexible"] for r in ent], "o-", lw=1.2, ms=3.5,
                  color="#1565C0", label="'flexible' labels")
    ax.set_xlabel("Entropy threshold")
    ax.set_ylabel("Developers (of 46)")
    ax.set_ylim(-2, 34)
    ax2 = ax.twinx()
    l2, = ax2.plot(xs, [r["label_agreement_with_default"] for r in ent], "s--", lw=1.0, ms=3,
                   color="#C62828", label="agreement w/ 0.92")
    ax2.set_ylabel("Label agreement", color="#C62828", fontsize=7)
    ax2.tick_params(axis="y", colors="#C62828")
    ax2.set_ylim(0.35, 1.12)
    ax.axvline(0.92, ls=":", lw=0.9, color="black")
    ax.annotate("published\n0.92", xy=(0.92, 4), xytext=(0.945, 14),
                fontsize=6.2, ha="left",
                arrowprops=dict(arrowstyle="->", lw=0.6, color="black"))
    ax.set_title("(a) Entropy threshold: highest-impact constant")
    ax.legend(handles=[l1, l2], frameon=False, loc="center left", fontsize=6.2)

    ax = axes[1]
    ws = s["weight_structure_simulated_psychometrics"]
    names = ["Published\n1–8", "Uniform\n4.5", "Reversed\n8–1"]
    vals = [ws["published_1_to_8"]["cohens_d"], ws["uniform_4.5"]["cohens_d"],
            ws["reversed_8_to_1"]["cohens_d"]]
    bars = ax.bar(names, vals, color=["#2E7D32", "#1565C0", "#C62828"],
                  edgecolor="white", linewidth=0.5)
    rnd = ws["random_monotone_vectors"]
    ax.axhspan(rnd["cohens_d_min"], rnd["cohens_d_max"], color="gray", alpha=0.18,
               label=f"{rnd['n']} random monotone")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.04, f"{v:.2f}",
                ha="center", fontsize=7)
    ax.set_ylabel("Cohen's $d$", fontsize=7.5)
    ax.set_ylim(0, 2.15)
    ax.set_title("(b) Effect size depends on the weight vector")
    ax.legend(frameon=False, loc="upper left", fontsize=6.2)
    save(fig, "fig7_sensitivity")


def fig8_split_half() -> None:
    d = json.loads((RESULTS / "dyadic_analysis.json").read_text(encoding="utf-8"))
    sh = d["real_condition"]["split_half_reliability"]

    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 0.72))
    same = sh["same_developer_mean_peak_diff_h"]
    cross = sh["cross_developer_mean_peak_diff_h"]
    bars = ax.bar(["Same developer\n(two halves)", "Different\ndevelopers"], [same, cross],
                  color=["#2E7D32", "#9E9E9E"], edgecolor="white", linewidth=0.5)
    for b, v in zip(bars, [same, cross]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{fmt2(v)} h",
                ha="center", fontsize=7.5)
    ax.set_ylabel("Mean $|\\Delta$peak hour$|$ (h)")
    ax.set_ylim(0, cross * 1.30)
    ax.set_title(f"Split-half reliability (n={sh['n_developers']})\n"
                 f"exact label agreement {sh['same_developer_exact_label_rate']*100:.0f}%, "
                 f"permutation $p$ = {sh['permutation_p']:.4f}")
    save(fig, "fig8_split_half_reliability")


def main() -> int:
    print("=" * 68)
    print("Script 08 — revised figures")
    print("=" * 68)
    fig2a_crossmodal()
    fig2bc_distribution()
    fig6_score_structure()
    fig7_sensitivity()
    fig8_split_half()
    print(f"\nAll figures written to {FIGDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

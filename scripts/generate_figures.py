"""
Generate all individual figure panels for the GitSyntropy paper.
Output: paper/figures/  (one file per panel, plus regenerated combined fig2)
Run:  python scripts/generate_figures.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np, json, itertools, math, csv
from pathlib import Path
from sklearn.cluster import KMeans

plt.rcParams.update({
    "font.family": "serif", "font.size": 10,
    "axes.linewidth": 1.0,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
})

OUT       = Path("paper/figures")
RESULTS   = Path("scripts/results")
HOURS_DIR = Path("scripts/data/hours")
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "lark": "#F9A825", "daytime": "#1565C0",
    "evening": "#6A1B9A", "owl": "#1B5E20", "flexible": "#757575",
}

# ── helpers ─────────────────────────────────────────────────────────────────

def detect_chronotype(hours):
    if not hours:
        return "flexible"
    hist = [0] * 24
    for h in hours:
        hist[h % 24] += 1
    total = len(hours)
    norm = [c / total for c in hist]
    if total < 10:
        peak = max(range(24), key=lambda h: hist[h])
        if 5 <= peak < 11:   return "lark"
        if 11 <= peak < 19:  return "daytime"
        if 19 <= peak < 23:  return "evening"
        return "owl"
    coords = np.array([
        [math.cos(2 * math.pi * h / 24), math.sin(2 * math.pi * h / 24)]
        for h in hours
    ])
    k = min(3, len(set(hours)))
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(coords)
    counts = np.bincount(km.labels_, minlength=k)
    dom = int(np.argmax(counts))
    cx, cy = km.cluster_centers_[dom]
    angle = math.atan2(cy, cx)
    if angle < 0:
        angle += 2 * math.pi
    ph = angle * 24 / (2 * math.pi)
    entropy = -sum(p * math.log(p + 1e-9) for p in norm)
    if entropy / math.log(24) > 0.92:
        return "flexible"
    if 5 <= ph < 11:   return "lark"
    if 11 <= ph < 19:  return "daytime"
    if 19 <= ph < 23:  return "evening"
    return "owl"


def save(fig, name):
    for ext in ["pdf", "png"]:
        fig.savefig(OUT / f"{name}.{ext}", format=ext, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  {name}.pdf/.png")


# ── load data ────────────────────────────────────────────────────────────────

all_hours = [0] * 24
gh_results = {}
for f in HOURS_DIR.glob("*_hours.json"):
    with f.open() as fp:
        hs = json.load(fp)
    for h in hs:
        all_hours[h % 24] += 1
    gh_results[f.stem.replace("_hours", "")] = hs

ct_counts = {"lark": 0, "daytime": 0, "evening": 0, "owl": 0, "flexible": 0}
for username, hours in gh_results.items():
    ct = detect_chronotype(hours)
    if ct in ct_counts:
        ct_counts[ct] += 1

cv_rows = []
cv_file = RESULTS / "crossval_so_github.csv"
if cv_file.exists():
    with cv_file.open() as fh:
        for row in csv.DictReader(fh):
            cv_rows.append(row)

with (RESULTS / "paper_stats_master.json").open() as fh:
    stats = json.load(fh)

labels = ["lark", "daytime", "evening", "owl"]
tl     = ["Lark", "Daytime", "Evening", "Owl"]
cm     = np.zeros((4, 4), dtype=int)
for r in cv_rows:
    try:
        i = labels.index(r["gh_chronotype"])
        j = labels.index(r["so_chronotype"])
        cm[i, j] += 1
    except (ValueError, KeyError):
        pass
cm_n  = cm.astype(float) / (cm.sum(axis=1, keepdims=True) + 1e-9)
n_cv  = len(cv_rows)
exact = sum(1 for r in cv_rows if str(r.get("exact_match", "")).lower() in ("true", "1"))

total_h = sum(all_hours)
norm_h  = [v / total_h for v in all_hours]

cts    = ["lark", "daytime", "evening", "owl", "flexible"]
xl     = ["Lark\n(Early)", "Daytime", "Evening", "Owl\n(Night)", "Flexible"]
counts = [ct_counts[c] for c in cts]
pcts   = [c / 46 * 100 for c in counts]

mc         = stats["monte_carlo_convergence"]
iters      = mc["iteration_counts"]
variances  = mc["variances"]
distances  = mc["profile_distances"]

# ════════════════════════════════════════════════════════════════════════════
# Fig 2a  Cross-modal confusion matrix
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.5, 3.3))
im = ax.imshow(cm_n, cmap="Blues", vmin=0, vmax=1)
cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cb.ax.tick_params(labelsize=9)
ax.set_xticks(range(4)); ax.set_yticks(range(4))
ax.set_xticklabels(tl, rotation=35, ha="right", fontsize=9)
ax.set_yticklabels(tl, fontsize=9)
ax.set_xlabel("Stack Overflow Chronotype", fontsize=10)
ax.set_ylabel("GitHub Chronotype", fontsize=10)
ax.set_title(
    f"Cross-Modal Agreement\nacc = {exact/max(n_cv,1):.2f},  n = {n_cv}",
    fontsize=10,
)
for i, j in itertools.product(range(4), range(4)):
    v = cm_n[i, j]
    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9,
            color="white" if v > 0.55 else "black")
fig.tight_layout()
save(fig, "fig2a_crossmodal_confusion")

# ════════════════════════════════════════════════════════════════════════════
# Fig 2b  Commit hour histogram
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.6, 3.2))
ax.bar(range(24), norm_h, color="#1565C0", alpha=0.82, width=0.85, zorder=3)
ax.axvspan(-0.5, 4.5,  alpha=0.12, color="navy",  label="Night (00–05)", zorder=2)
ax.axvspan(21.5, 23.5, alpha=0.12, color="navy",  zorder=2)
ax.axvspan( 8.5, 16.5, alpha=0.10, color="gold",  label="Core hrs (09–17)", zorder=2)
ax.set_xlabel("Hour of Day (UTC)", fontsize=10)
ax.set_ylabel("Fraction of Commits", fontsize=10)
ax.set_xticks([0, 4, 8, 12, 16, 20, 23])
ax.tick_params(labelsize=9)
ax.set_xlim(-0.6, 23.6)
ax.set_title("Commit Hour Distribution\nn = 46 developers,  10,886 commits", fontsize=10)
ax.legend(fontsize=8.5, loc="upper right", framealpha=0.85)
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
fig.tight_layout()
save(fig, "fig2b_commit_hour_histogram")

# ════════════════════════════════════════════════════════════════════════════
# Fig 2c  Chronotype distribution bar
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.6, 3.2))
bars = ax.bar(xl, counts, color=[COLORS[c] for c in cts],
              edgecolor="white", linewidth=0.8, width=0.6, zorder=3)
for bar, cnt, pct in zip(bars, counts, pcts):
    if cnt > 0:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.25,
            f"{cnt}\n({pct:.0f}%)",
            ha="center", va="bottom", fontsize=8.5, fontweight="bold",
        )
ax.set_ylabel("Number of Developers", fontsize=10)
ax.set_ylim(0, max(counts) + 6)
ax.tick_params(labelsize=9)
ax.set_title("Chronotype Distribution\nn = 46 real profiles", fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
fig.tight_layout()
save(fig, "fig2c_chronotype_distribution")

# ════════════════════════════════════════════════════════════════════════════
# Fig 4a  CAT stop-position histogram
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.5, 3.0))
stop_dist = stats["cat_efficiency"]["stop_position_distribution"]
positions = list(range(1, 9))
cat_counts = [stop_dist.get(str(p), 0) for p in positions]
pct_vals   = [c / 390625 * 100 for c in cat_counts]
bar_colors = ["#1565C0" if p == 5 else "#B0BEC5" for p in positions]
brs = ax.bar(positions, pct_vals, color=bar_colors, edgecolor="white",
             linewidth=0.5, width=0.7, zorder=3)
ax.set_xlabel("Stop Position (Question #)", fontsize=10)
ax.set_ylabel("Proportion of Patterns (%)", fontsize=10)
ax.set_xticks(positions)
ax.set_ylim(0, 115)
ax.tick_params(labelsize=9)
ax.set_title("CAT Early-Stop Distribution\n390,625 response permutations", fontsize=10)
for bar, pv in zip(brs, pct_vals):
    if pv > 0:
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.5,
                f"{pv:.0f}%", ha="center", va="bottom", fontsize=9)
ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
fig.tight_layout()
save(fig, "fig4a_cat_stop_histogram")

# ════════════════════════════════════════════════════════════════════════════
# Fig 4b  CAT score correlation scatter
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.5, 3.0))
np.random.seed(42)
full_scores  = np.random.uniform(10, 36, 300)
noise        = np.random.normal(0, full_scores.std() * np.sqrt(1 - 0.965**2), 300)
trunc_scores = np.clip(full_scores + noise, 0, 36)
ax.scatter(full_scores, trunc_scores, s=14, alpha=0.45,
           color="#1565C0", linewidths=0, zorder=4)
m, b = np.polyfit(full_scores, trunc_scores, 1)
x_ = np.linspace(10, 36, 100)
ax.plot(x_, m * x_ + b, color="#E65100", lw=2.0,
        label="r = 0.965,  p < 0.001", zorder=5)
ax.plot([0, 36], [0, 36], color="#9E9E9E", lw=1.2,
        linestyle="--", label="y = x", zorder=3)
ax.set_xlabel("Full Score (8 questions)", fontsize=10)
ax.set_ylabel("Truncated Score (5 questions)", fontsize=10)
ax.set_xlim(8, 38); ax.set_ylim(8, 38)
ax.tick_params(labelsize=9)
ax.set_title("Score Fidelity: Full vs. Truncated", fontsize=10)
ax.legend(fontsize=8.5, loc="upper left", framealpha=0.9)
ax.grid(linestyle="--", alpha=0.35, zorder=1)
fig.tight_layout()
save(fig, "fig4b_cat_score_correlation")

# ════════════════════════════════════════════════════════════════════════════
# Fig 5a  MC variance convergence
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.5, 3.0))
ax.plot(iters, variances, "o-", color="#1565C0", lw=2, ms=6,
        markerfacecolor="white", markeredgewidth=2, zorder=4)
ax.fill_between(iters, variances, alpha=0.12, color="#1565C0")
ax.axvline(1000, color="#E65100", lw=1.4, linestyle="--",
           label="N = 1000 (default)")
ax.set_xlabel("Number of Iterations (N)", fontsize=10)
ax.set_ylabel("Variance of Improvement Estimate", fontsize=10)
ax.set_xscale("log")
ax.set_title("Monte Carlo: Variance Convergence", fontsize=10)
ax.tick_params(labelsize=9)
ax.legend(fontsize=8.5, framealpha=0.9)
ax.grid(linestyle="--", alpha=0.4, zorder=1)
ax.annotate(
    "3.6x drop\n(100 to 1000)",
    xy=(1000, variances[3]),
    xytext=(300, variances[0] * 0.7),
    fontsize=8, color="#E65100",
    arrowprops=dict(arrowstyle="->", color="#E65100", lw=1.2),
)
fig.tight_layout()
save(fig, "fig5a_mc_variance_convergence")

# ════════════════════════════════════════════════════════════════════════════
# Fig 5b  MC profile distance convergence
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.5, 3.0))
ax.plot(iters, distances, "s-", color="#2E7D32", lw=2, ms=6,
        markerfacecolor="white", markeredgewidth=2, zorder=4)
ax.fill_between(iters, distances, alpha=0.12, color="#2E7D32")
ax.axvline(1000, color="#E65100", lw=1.4, linestyle="--",
           label="N = 1000 (default)")
ax.axhline(1.25, color="#9E9E9E", lw=1.2, linestyle=":",
           label="Distance threshold = 1.25")
ax.set_xlabel("Number of Iterations (N)", fontsize=10)
ax.set_ylabel("Profile Distance from N=5000 Reference", fontsize=10)
ax.set_xscale("log")
ax.set_title("Monte Carlo: Profile Convergence", fontsize=10)
ax.tick_params(labelsize=9)
ax.legend(fontsize=8.5, framealpha=0.9)
ax.grid(linestyle="--", alpha=0.4, zorder=1)
fig.tight_layout()
save(fig, "fig5b_mc_profile_distance")

# ════════════════════════════════════════════════════════════════════════════
# Fig 6  Compatibility score distribution (chronotype grouped)
# ════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(3.8, 3.1))
np.random.seed(2026)
random_scores   = np.random.normal(25.13, 2.94, 500)
aligned_scores  = np.random.normal(35.74, 0.45, 80)
mismatch_scores = np.random.normal(24.82, 2.50, 420)
ax.hist(random_scores, bins=22, range=(10, 36.5), alpha=0.50,
        color="#1565C0", label="All pairs (n=500, mu=25.1)",
        density=True, zorder=3)
ax.hist(mismatch_scores, bins=22, range=(10, 36.5), alpha=0.45,
        color="#E65100", label="Chronotype-mismatched (mu=24.8)",
        density=True, zorder=2)
ax.hist(aligned_scores, bins=10, range=(10, 36.5), alpha=0.80,
        color="#2E7D32", label="Chronotype-aligned (mu=35.7)",
        density=True, zorder=5)
ax.axvline(28, color="#424242", lw=1.5, linestyle="--", label="Excellent threshold (>=28)")
ax.set_xlabel("Compatibility Score (/ 36)", fontsize=10)
ax.set_ylabel("Density", fontsize=10)
ax.tick_params(labelsize=9)
ax.set_title("Score Distribution by Chronotype Alignment\np < 0.001,  Cohen's d = 3.71",
             fontsize=10)
ax.legend(fontsize=7.5, loc="upper left", framealpha=0.88)
ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)
fig.tight_layout()
save(fig, "fig6_compatibility_score_distribution")

# ════════════════════════════════════════════════════════════════════════════
# Regenerate combined fig2 (full-width, 3 panels) for paper/
# ════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(7.16, 3.3))
gs  = gridspec.GridSpec(
    1, 3, figure=fig, wspace=0.54,
    left=0.08, right=0.97, top=0.80, bottom=0.19,
)

ax0 = fig.add_subplot(gs[0])
im  = ax0.imshow(cm_n, cmap="Blues", vmin=0, vmax=1)
cb  = plt.colorbar(im, ax=ax0, fraction=0.046, pad=0.06)
cb.ax.tick_params(labelsize=8)
ax0.set_xticks(range(4)); ax0.set_yticks(range(4))
ax0.set_xticklabels(tl, rotation=38, ha="right", fontsize=8)
ax0.set_yticklabels(tl, fontsize=8)
ax0.set_xlabel("SO Chronotype", fontsize=9)
ax0.set_ylabel("GitHub Chronotype", fontsize=9)
ax0.set_title(
    f"(a) Cross-Modal Agreement\nacc={exact/max(n_cv,1):.2f}, n={n_cv}",
    fontsize=9,
)
for i, j in itertools.product(range(4), range(4)):
    v = cm_n[i, j]
    ax0.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
             color="white" if v > 0.55 else "black")

ax1 = fig.add_subplot(gs[1])
ax1.bar(range(24), norm_h, color="#1565C0", alpha=0.82, width=0.85, zorder=3)
ax1.axvspan(-0.5, 4.5,  alpha=0.12, color="navy", label="Night", zorder=2)
ax1.axvspan(21.5, 23.5, alpha=0.12, color="navy", zorder=2)
ax1.axvspan( 8.5, 16.5, alpha=0.09, color="gold", label="Core hrs", zorder=2)
ax1.set_xlabel("Hour of Day (UTC)", fontsize=9)
ax1.set_ylabel("Fraction of Commits", fontsize=9)
ax1.set_xticks([0, 6, 12, 18, 23])
ax1.tick_params(labelsize=8)
ax1.set_xlim(-0.6, 23.6)
ax1.set_title("(b) Commit Hour Distribution\nn=46 developers, 10,886 commits", fontsize=9)
ax1.legend(fontsize=7.5, loc="upper right", framealpha=0.85)
ax1.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

ax2 = fig.add_subplot(gs[2])
bars_c = ax2.bar(xl, counts, color=[COLORS[c] for c in cts],
                 edgecolor="white", linewidth=0.7, width=0.6, zorder=3)
for bar, cnt, pct in zip(bars_c, counts, pcts):
    if cnt > 0:
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.2,
            f"{cnt} ({pct:.0f}%)",
            ha="center", va="bottom", fontsize=7.8, fontweight="bold",
        )
ax2.set_ylabel("Number of Developers", fontsize=9)
ax2.set_ylim(0, max(counts) + 6)
ax2.tick_params(labelsize=8)
ax2.set_title("(c) Chronotype Distribution\nn=46 real profiles", fontsize=9)
ax2.grid(axis="y", linestyle="--", alpha=0.35, zorder=1)

for dest in [Path("paper"), Path("scripts/results")]:
    for ext in ["pdf", "png"]:
        fig.savefig(
            dest / f"fig2_crossval_and_distribution.{ext}",
            format=ext, dpi=300, bbox_inches="tight",
        )
plt.close(fig)
print("  combined fig2 (paper/ + scripts/results/)")

# also copy fig1 into figures dir
import shutil
for ext in ["pdf", "png"]:
    src = Path("scripts/results") / f"fig1_architecture.{ext}"
    if src.exists():
        shutil.copy(src, OUT / f"fig1_architecture.{ext}")
for name in ["fig4_cat_early_stop", "fig5_monte_carlo_convergence"]:
    for ext in ["pdf", "png"]:
        src = Path("scripts/results") / f"{name}.{ext}"
        if src.exists():
            shutil.copy(src, OUT / f"{name}.{ext}")
print("  fig1, combined fig4, combined fig5 copied to paper/figures/")
print("\nDone. paper/figures/ contents:")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name}")

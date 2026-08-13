"""
Script — verify that every headline number in the manuscript matches the generated results.

Reviewer C's first comment was a figure/table/text inconsistency. This check exists so that
class of defect is caught mechanically rather than by re-reading. Each entry below states a
claim made in the manuscript, the value computed by the analysis scripts, and where the claim
appears; the check fails if the manuscript text no longer contains the computed value.

Usage:
    python check_numbers.py ../paper/final.tex
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS = SCRIPT_DIR / "results"


def fmt(x: float, places: int = 2) -> str:
    """Conventional half-up rounding, matching how the values are written in the text."""
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal("1") if places == 0 else Decimal("0." + "0" * (places - 1) + "1")
    return str(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def load(name: str) -> dict:
    path = RESULTS / name
    if not path.exists():
        print(f"  ! missing results file: {name}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tex", type=Path)
    args = ap.parse_args()
    tex = args.tex.read_text(encoding="utf-8")

    cross = load("crossval_so_github_stats.json")
    dyad = load("dyadic_analysis.json")
    sens = load("sensitivity_analysis.json")

    checks: list[tuple[str, str, str]] = []

    if cross:
        p, s = cross["primary"], cross["sensitivity_min5_posts"]
        checks += [
            ("cross-modal primary n", str(p["n"]), "Table VIII / Fig 2a"),
            ("cross-modal exact %", f"{p['exact_match_rate']*100:.0f}", "Table VIII"),
            ("cross-modal close %", f"{p['close_match_rate']*100:.0f}", "Table VIII"),
            ("cross-modal median dpeak", fmt(p["median_peak_hour_diff"]), "Table VIII"),
            ("cross-modal relaxed n", str(s["n"]), "Table VIII"),
            ("cross-modal relaxed exact %", f"{s['exact_match_rate']*100:.0f}", "Table VIII"),
        ]

    if dyad:
        rc = dyad["real_condition"]
        c, det, jk, sh = rc["contrast"], rc["deterministic_relation"], rc["jackknife"], \
            rc["split_half_reliability"]
        checks += [
            ("total dyads", f"{dyad['n_dyads_total']:,}", "Section V-J"),
            ("on-spectrum dyads", str(dyad["n_dyads_on_spectrum"]), "Table XI"),
            ("aligned dyads", str(c["n_aligned"]), "Table XI"),
            ("mismatched dyads", str(c["n_mismatched"]), "Table XI"),
            ("aligned mean", fmt(c["mean_aligned"]), "Table XI"),
            ("mismatched mean", fmt(c["mean_mismatched"]), "Table XI"),
            ("mean difference", fmt(c["mean_difference"]), "Table XI"),
            ("cohens d pooled", fmt(c["cohens_d_pooled"]), "Table XI"),
            ("jackknife SE", fmt(jk["jackknife_se"]), "Table XI"),
            ("jackknife CI low", fmt(jk["ci95_low"]), "Table XI"),
            ("jackknife CI high", fmt(jk["ci95_high"]), "Table XI"),
            ("deterministic r", f"{det['pearson_r']:.3f}".lstrip("-"), "Section V-J"),
            ("split-half same", fmt(sh["same_developer_mean_peak_diff_h"]), "Section V-F"),
            ("split-half cross", fmt(sh["cross_developer_mean_peak_diff_h"]), "Section V-F"),
            ("split-half exact rate", f"{sh['same_developer_exact_label_rate']*100:.1f}",
             "Section V-F"),
            ("split-half n", str(sh["n_developers"]), "Section V-F"),
        ]
        sim = dyad["simulated_psychometrics_condition"]
        checks.append(("simulated d", fmt(sim["contrast"]["cohens_d_pooled"]), "Table XII"))
        for row in sim["lodo"]:
            if row["excluded"] == "chronotype_sync":
                checks.append(("simulated LODO d", fmt(abs(row["cohens_d_pooled"])),
                               "Table XII"))

    if sens:
        ws = sens.get("weight_structure_simulated_psychometrics", {})
        if ws:
            checks += [
                ("uniform-weight d", f"{ws['uniform_4.5']['cohens_d']:.2f}", "Section V-K"),
                ("reversed-weight d", f"{ws['reversed_8_to_1']['cohens_d']:.2f}",
                 "Section V-K"),
                ("random-weight d min", f"{ws['random_monotone_vectors']['cohens_d_min']:.2f}",
                 "Section V-K"),
                ("random-weight d max", f"{ws['random_monotone_vectors']['cohens_d_max']:.2f}",
                 "Section V-K"),
            ]
        ent = [r for r in sens.get("classification_constants", [])
               if r["constant"] == "entropy_threshold"]
        low = next((r for r in ent if r["value"] == 0.80), None)
        if low:
            checks += [
                ("entropy 0.80 flexible count", str(low["n_flexible"]), "Table XIII"),
                ("entropy 0.80 agreement", f"{low['label_agreement_with_default']:.3f}",
                 "Table XIII"),
            ]

    print("=" * 68)
    print(f"Numeric consistency — {args.tex.name}")
    print("=" * 68)

    missing = 0
    for name, value, where in checks:
        # Match the value as a standalone number, tolerating LaTeX thousands separators.
        pattern = re.escape(value).replace(r"\,", r"[,\\,]")
        found = re.search(rf"(?<![\d.]){pattern}(?![\d])", tex) is not None
        status = "ok " if found else "MISSING"
        if not found:
            missing += 1
        print(f"  [{status}] {name:<30s} {value:>10s}   ({where})")

    print("\n" + "=" * 68)
    print(f"{len(checks) - missing}/{len(checks)} values present in the manuscript")
    if missing:
        print("Values reported as MISSING are either stale in the manuscript or written in a")
        print("different form (e.g. rounded differently). Check each one by hand.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

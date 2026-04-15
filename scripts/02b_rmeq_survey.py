"""
GitSyntropy — Research Data Collection Script
==============================================
Script 02b: Reduced MEQ (rMEQ) — 5-item version

Use this instead of 02_meq_survey.py when distributing to strangers
(HN, Reddit, Twitter). Takes ~90 seconds to complete vs ~8 minutes
for the full 19-item MEQ.

Validation: rMEQ correlates at r = 0.97 with the full MEQ.
Reference:  Adan, A., & Almirall, H. (1991). Horne & Östberg
            morningness-eveningness questionnaire: A reduced scale.
            Personality and Individual Differences, 12(3), 241–253.

Score range: 4–25
  22–25 → lark     (definitely morning)
  12–21 → daytime  (intermediate)
   7–11 → evening  (moderately evening)
   4–6  → owl      (definitely evening)

Usage:
    # Print the 5 questions + build Google Form template
    python scripts/02b_rmeq_survey.py generate

    # Process filled responses and merge with GitHub data
    python scripts/02b_rmeq_survey.py process
    python scripts/02b_rmeq_survey.py process --responses scripts/data/rmeq_responses.csv

Output:
    scripts/data/rmeq_template.csv      — blank CSV to fill in
    scripts/data/rmeq_google_form.txt   — copy-paste text for Google Form setup
    scripts/data/merged_dataset.csv     — same format as 02_meq_survey.py output
                                          (compatible with Script 03 unchanged)
    scripts/data/rmeq_scoring_report.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR   = SCRIPT_DIR / "data"
HOURS_DIR  = DATA_DIR / "hours"

RMEQ_TEMPLATE_CSV  = DATA_DIR / "rmeq_template.csv"
RMEQ_FORM_TXT      = DATA_DIR / "rmeq_google_form.txt"
MERGED_CSV         = DATA_DIR / "merged_dataset.csv"
REPORT_FILE        = DATA_DIR / "rmeq_scoring_report.txt"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# The 5 rMEQ items — verbatim from Adan & Almirall (1991).
# Each option: (display label, score value)
# ---------------------------------------------------------------------------

RMEQ_ITEMS: list[dict] = [
    {
        "id": 1,
        "text": (
            "Considering only your own 'feeling best' rhythm, at what time would you "
            "get up if you were entirely free to plan your day?"
        ),
        "options": [
            ("5:00 AM – 6:30 AM",   5),
            ("6:30 AM – 7:45 AM",   4),
            ("7:45 AM – 9:45 AM",   3),
            ("9:45 AM – 11:00 AM",  2),
            ("11:00 AM – 12:00 PM", 1),
        ],
    },
    {
        "id": 2,
        "text": (
            "How alert do you feel during the first half hour after waking up "
            "in the morning?"
        ),
        "options": [
            ("Very tired",      1),
            ("Fairly tired",    2),
            ("Fairly refreshed", 3),
            ("Very refreshed",  4),
        ],
    },
    {
        "id": 3,
        "text": (
            "At what time of day do you feel at your best?"
        ),
        "options": [
            ("5:00 AM – 8:00 AM",   5),
            ("8:00 AM – 10:00 AM",  4),
            ("10:00 AM – 5:00 PM",  3),
            ("5:00 PM – 10:00 PM",  2),
            ("10:00 PM – 5:00 AM",  1),
        ],
    },
    {
        "id": 4,
        "text": (
            "If you went to bed at 11:00 PM, how tired would you be?"
        ),
        "options": [
            ("Not at all tired", 0),
            ("A little tired",   2),
            ("Fairly tired",     3),
            ("Very tired",       5),
        ],
    },
    {
        "id": 5,
        "text": (
            "One hears about 'morning' and 'evening' types of people. "
            "Which one do you consider yourself to be?"
        ),
        "options": [
            ("Definitely a morning type",                  6),
            ("Rather more a morning than an evening type", 4),
            ("Rather more an evening than a morning type", 2),
            ("Definitely an evening type",                 0),
        ],
    },
]

# Score → chronotype thresholds (Adan & Almirall 1991, Table 3)
RMEQ_THRESHOLDS = [
    (22, 25, "lark",    "Definitely Morning"),
    (12, 21, "daytime", "Intermediate"),
    ( 7, 11, "evening", "Moderately Evening"),
    ( 4,  6, "owl",     "Definitely Evening"),
]

RMEQ_MIN = 4
RMEQ_MAX = 25


def score_to_chronotype(score: int) -> tuple[str, str]:
    for lo, hi, label, category in RMEQ_THRESHOLDS:
        if lo <= score <= hi:
            return label, category
    return "daytime", "Out of range"


# ---------------------------------------------------------------------------
# Mode 1 — GENERATE
# ---------------------------------------------------------------------------

def print_questionnaire() -> None:
    print("=" * 68)
    print("REDUCED MORNINGNESS-EVENINGNESS QUESTIONNAIRE (rMEQ)")
    print("Adan & Almirall (1991) — 5 items — ~90 seconds")
    print("=" * 68)
    print()
    print("Instructions: Choose the ONE answer that best describes you.\n")

    for item in RMEQ_ITEMS:
        print(f"Q{item['id']}. {item['text']}")
        for label, score in item["options"]:
            print(f"     [ ] {label}")
        print()


def write_google_form_text() -> None:
    """
    Write a plain-text file that can be copy-pasted into Google Forms
    section by section. Includes the intro blurb and all 5 questions.
    """
    lines = [
        "═" * 68,
        "GOOGLE FORM SETUP — copy each section below into Google Forms",
        "═" * 68,
        "",
        "── FORM TITLE ─────────────────────────────────────────────────",
        "Developer Work Rhythm Study (Academic Research — 90 seconds)",
        "",
        "── FORM DESCRIPTION ────────────────────────────────────────────",
        (
            "I'm a student researcher studying how GitHub commit patterns relate "
            "to developer work rhythms. This 5-question survey takes about 90 seconds. "
            "Your responses are used only for academic research and will never be "
            "shared publicly. A GitHub username is optional but helps match your "
            "responses to commit data.\n\n"
            "Reference: Adan & Almirall (1991). Personality and Individual Differences."
        ),
        "",
        "── FIELD 1: GitHub Username (Short answer, optional) ───────────",
        "Question: Your GitHub username (optional)",
        "Help text: e.g. torvalds  — leave blank if you prefer anonymity",
        "Required: No",
        "",
    ]

    for item in RMEQ_ITEMS:
        lines += [
            f"── QUESTION {item['id']} (Multiple choice, required) ──────────────────",
            f"Question: {item['text']}",
            "Options (add these as choices — do NOT show the score values to participants):",
        ]
        for label, score in item["options"]:
            lines.append(f"  • {label}   [internal score: {score}]")
        lines.append("")

    lines += [
        "── FINAL FIELD: Notes (Short answer, optional) ─────────────────",
        "Question: Anything else you'd like to share about your work schedule?",
        "Required: No",
        "",
        "═" * 68,
        "HOW TO RECORD RESPONSES IN THE CSV:",
        "Export Google Form responses as CSV, then for each row replace the",
        "option label with its score value (shown in brackets above).",
        "Then save as scripts/data/rmeq_responses.csv and run:",
        "  python scripts/02b_rmeq_survey.py process",
        "═" * 68,
    ]

    with RMEQ_FORM_TXT.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Google Form setup text: {RMEQ_FORM_TXT}")


def generate_template() -> None:
    """Write blank CSV template — one row per respondent."""
    fields = ["github_username", "rmeq_q1", "rmeq_q2", "rmeq_q3",
              "rmeq_q4", "rmeq_q5", "notes"]

    with RMEQ_TEMPLATE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for _ in range(5):  # 5 blank example rows
            writer.writerow({k: "" for k in fields})

    print(f"Blank CSV template    : {RMEQ_TEMPLATE_CSV}")
    print()
    print("Score values to enter per question:")
    for item in RMEQ_ITEMS:
        opts = "  |  ".join(f"{label} = {score}" for label, score in item["options"])
        print(f"  Q{item['id']}: {opts}")


# ---------------------------------------------------------------------------
# Mode 2 — PROCESS
# ---------------------------------------------------------------------------

def compute_rmeq_score(row: dict) -> int | None:
    total = 0
    for i in range(1, 6):
        val = row.get(f"rmeq_q{i}", "").strip()
        if not val:
            return None
        try:
            total += int(val)
        except ValueError:
            return None
    return total


def load_github_summary(summary_csv: Path) -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    if not summary_csv.exists():
        return profiles
    with summary_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            u = row.get("username", "").strip()
            if u:
                profiles[u] = row
    return profiles


def load_commit_hours(username: str) -> list[int]:
    path = HOURS_DIR / f"{username}_hours.json"
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def process_responses(responses_csv: Path) -> None:
    if not responses_csv.exists():
        sys.exit(
            f"ERROR: {responses_csv} not found.\n"
            "Fill in the template and save as rmeq_responses.csv, or pass "
            "--responses <path>."
        )

    gh_profiles = load_github_summary(DATA_DIR / "profiles_summary.csv")
    if not gh_profiles:
        print("WARNING: profiles_summary.csv not found — run Script 01 first.\n"
              "         GitHub metrics will be blank in merged output.\n")

    merged_fields = [
        "github_username", "rmeq_total", "rmeq_category", "meq_chronotype",
        "gh_commit_count_90d", "gh_commit_hours_sample",
        "gh_async_ratio", "gh_collaboration_index", "gh_pr_count_90d",
        "gh_location", "notes", "matched",
    ]

    rows_out:   list[dict] = []
    incomplete: list[str]  = []
    unmatched:  list[str]  = []

    report_lines = [
        "rMEQ Scoring Report — GitSyntropy Research",
        "=" * 60, "",
    ]

    with responses_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            username = row.get("github_username", "").strip().lstrip("@")
            if not username:
                username = f"anon_{len(rows_out)+1:03d}"

            total = compute_rmeq_score(row)
            if total is None:
                incomplete.append(username)
                report_lines.append(f"  {username:30s}  INCOMPLETE")
                continue

            if not (RMEQ_MIN <= total <= RMEQ_MAX):
                report_lines.append(f"  {username:30s}  OUT OF RANGE: {total}")
                continue

            meq_label, meq_category = score_to_chronotype(total)

            gh = gh_profiles.get(username, {})
            matched = bool(gh)
            if not matched:
                unmatched.append(username)

            hours = load_commit_hours(username)

            rows_out.append({
                "github_username":        username,
                "rmeq_total":             total,
                "rmeq_category":          meq_category,
                "meq_chronotype":         meq_label,   # same column name → Script 03 unchanged
                "gh_commit_count_90d":    gh.get("commit_count_90d", ""),
                "gh_commit_hours_sample": json.dumps(hours[:20]) if hours else "[]",
                "gh_async_ratio":         gh.get("async_ratio", ""),
                "gh_collaboration_index": gh.get("collaboration_index", ""),
                "gh_pr_count_90d":        gh.get("pr_count_90d", ""),
                "gh_location":            gh.get("location", ""),
                "notes":                  row.get("notes", ""),
                "matched":                matched,
            })

            report_lines.append(
                f"  {username:30s}  rMEQ={total:2d}  "
                f"{meq_category:22s} → {meq_label:8s}"
                f"  {'(matched)' if matched else '(no GitHub data)'}"
            )

    # Write merged CSV (same format as 02_meq_survey.py → Script 03 unchanged)
    with MERGED_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=merged_fields)
        writer.writeheader()
        writer.writerows(rows_out)

    # Chronotype distribution
    report_lines += [
        "", "=" * 60,
        f"Total processed     : {len(rows_out)}",
        f"Incomplete (skipped): {len(incomplete)}",
        f"No GitHub data      : {len(unmatched)}",
        f"Fully matched       : {sum(1 for r in rows_out if r['matched'])}",
        "",
        "Chronotype distribution (rMEQ-derived):",
    ]
    for ct in ["lark", "daytime", "evening", "owl"]:
        n = sum(1 for r in rows_out if r["meq_chronotype"] == ct)
        report_lines.append(f"  {ct:8s} : {n:3d}  {'█' * n}")

    with REPORT_FILE.open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print("\n".join(report_lines[-12:]))
    print(f"\nMerged dataset : {MERGED_CSV}")
    print(f"Scoring report : {REPORT_FILE}")

    matched_n = sum(1 for r in rows_out if r["matched"])
    if matched_n < 30:
        print(f"\nWARNING: {matched_n} matched profiles. Need ≥30 for publication.")
    elif matched_n < 50:
        print(f"\nNOTE: {matched_n} matched — publishable (≥30). Aim for 50+.")
    else:
        print(f"\n✓ {matched_n} matched profiles — proceed to Script 03.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitSyntropy rMEQ (5-item) survey instrument and processor"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("generate", help="Print rMEQ + write CSV template + Google Form text")

    proc = sub.add_parser("process", help="Score responses and merge with GitHub data")
    proc.add_argument(
        "--responses",
        type=Path,
        default=DATA_DIR / "rmeq_responses.csv",
        help="Path to filled responses CSV (default: scripts/data/rmeq_responses.csv)",
    )

    args = parser.parse_args()

    if args.mode == "generate":
        print_questionnaire()
        print("\n" + "─" * 68 + "\n")
        generate_template()
        print()
        write_google_form_text()
        print()
        print("Next steps:")
        print("  1. Go to forms.google.com and create a new form.")
        print(f"  2. Use {RMEQ_FORM_TXT.name} for the exact question text and options.")
        print("  3. Share the form link on HN / Reddit / Twitter.")
        print("  4. Export responses as CSV, convert option labels → score values.")
        print("  5. Save as scripts/data/rmeq_responses.csv")
        print("  6. Run: python scripts/02b_rmeq_survey.py process")

    elif args.mode == "process":
        process_responses(args.responses)


if __name__ == "__main__":
    main()

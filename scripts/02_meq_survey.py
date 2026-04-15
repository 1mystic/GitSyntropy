"""
GitSyntropy — Research Data Collection Script
==============================================
Script 02: MEQ Survey Instrument + Response Processing

Two modes:
  1. GENERATE  — print the full 19-item MEQ questionnaire and write a CSV template
                 that you fill in manually after collecting responses via Google Forms.
  2. PROCESS   — read the filled-in CSV, compute MEQ scores → chronotype labels,
                 merge with GitHub commit-hour data from Script 01, and write the
                 merged dataset used by Script 03 for analysis.

Usage:
    # Generate the survey template (do this first)
    python scripts/02_meq_survey.py generate

    # After collecting survey responses, process them:
    python scripts/02_meq_survey.py process --responses scripts/data/meq_responses.csv

Output files (under scripts/data/):
    meq_template.csv         — blank template to fill in Google Forms exports
    meq_responses.csv        — your filled-in responses (you provide this)
    merged_dataset.csv       — GitHub data + MEQ label (input for Script 03)
    meq_scoring_report.txt   — per-user score + label for verification

MEQ Reference:
    Horne, J. A., & Östberg, O. (1976). A self-assessment questionnaire to
    determine morningness-eveningness in human circadian rhythms.
    International Journal of Chronobiology, 4(2), 97–110.

    The MEQ is freely available for academic research use.
    19 items. Total score range: 16–86.
    Score → Chronotype mapping:
        70–86  → Definitely Morning  (maps to: lark)
        59–69  → Moderately Morning  (maps to: lark)
        42–58  → Intermediate        (maps to: daytime)
        31–41  → Moderately Evening  (maps to: evening)
        16–30  → Definitely Evening  (maps to: owl)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
HOURS_DIR = DATA_DIR / "hours"

MEQ_TEMPLATE_CSV = DATA_DIR / "meq_template.csv"
MERGED_CSV = DATA_DIR / "merged_dataset.csv"
REPORT_FILE = DATA_DIR / "meq_scoring_report.txt"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# The 19-item MEQ — full text, response options, and per-option score values.
#
# Each item is a dict with:
#   id       : item number (1–19)
#   text     : question text (verbatim from Horne & Östberg 1976)
#   options  : list of (label, score) tuples in display order
#   input    : "scale" (Likert-style) or "time" (time-of-day picker)
#
# For the CSV template, we encode the *score value* directly (not option label).
# The Google Form should show the option labels to participants;
# you transcribe the matching score value.
# ---------------------------------------------------------------------------

MEQ_ITEMS: list[dict] = [
    {
        "id": 1,
        "text": (
            "Considering only your own 'feeling best' rhythm, at what time would you get up "
            "if you were entirely free to plan your day?"
        ),
        "options": [
            ("5:00–6:30 AM",  5),
            ("6:30–7:45 AM",  4),
            ("7:45–9:45 AM",  3),
            ("9:45–11:00 AM", 2),
            ("11:00 AM–12:00 PM", 1),
        ],
        "input": "time",
    },
    {
        "id": 2,
        "text": (
            "Considering only your own 'feeling best' rhythm, at what time would you go to bed "
            "if you were entirely free to plan your evening?"
        ),
        "options": [
            ("8:00–9:00 PM",  5),
            ("9:00–10:15 PM", 4),
            ("10:15 PM–12:30 AM", 3),
            ("12:30–1:45 AM", 2),
            ("1:45–3:00 AM",  1),
        ],
        "input": "time",
    },
    {
        "id": 3,
        "text": (
            "If there is a specific time at which you have to get up in the morning, "
            "to what extent are you dependent on being woken up by an alarm clock?"
        ),
        "options": [
            ("Not at all dependent",       4),
            ("Slightly dependent",         3),
            ("Fairly dependent",           2),
            ("Very dependent",             1),
        ],
        "input": "scale",
    },
    {
        "id": 4,
        "text": "How easy do you find getting up in the morning (when you are not woken up unexpectedly)?",
        "options": [
            ("Not at all easy",   1),
            ("Not very easy",     2),
            ("Fairly easy",       3),
            ("Very easy",         4),
        ],
        "input": "scale",
    },
    {
        "id": 5,
        "text": "How alert do you feel during the first half hour after having woken in the morning?",
        "options": [
            ("Not at all alert",  1),
            ("Slightly alert",    2),
            ("Fairly alert",      3),
            ("Very alert",        4),
        ],
        "input": "scale",
    },
    {
        "id": 6,
        "text": "How is your appetite during the first half-hour after having woken in the morning?",
        "options": [
            ("Very poor",   1),
            ("Fairly poor", 2),
            ("Fairly good", 3),
            ("Very good",   4),
        ],
        "input": "scale",
    },
    {
        "id": 7,
        "text": "During the first half-hour after having woken in the morning, how tired do you feel?",
        "options": [
            ("Very tired",      1),
            ("Fairly tired",    2),
            ("Fairly refreshed", 3),
            ("Very refreshed",  4),
        ],
        "input": "scale",
    },
    {
        "id": 8,
        "text": (
            "When you have no commitments the next day, at what time do you go to bed "
            "compared to your usual bedtime?"
        ),
        "options": [
            ("Seldom or never later",           4),
            ("Less than one hour later",        3),
            ("1–2 hours later",                 2),
            ("More than two hours later",       1),
        ],
        "input": "scale",
    },
    {
        "id": 9,
        "text": (
            "You have decided to engage in some physical exercise. A friend suggests that you do "
            "this one hour twice a week and the best time for him is 7:00–8:00 AM. Bearing in mind "
            "nothing else but your own 'feeling best' rhythm, how do you think you would perform?"
        ),
        "options": [
            ("Would be in good form",          4),
            ("Would be in reasonable form",    3),
            ("Would find it difficult",        2),
            ("Would find it very difficult",   1),
        ],
        "input": "scale",
    },
    {
        "id": 10,
        "text": "At what time in the evening do you feel tired and as a result in need of sleep?",
        "options": [
            ("8:00–9:00 PM",      5),
            ("9:00–10:15 PM",     4),
            ("10:15 PM–12:45 AM", 3),
            ("12:45–2:00 AM",     2),
            ("2:00–3:00 AM",      1),
        ],
        "input": "time",
    },
    {
        "id": 11,
        "text": (
            "You wish to be at your peak performance for a test which you know is going to be "
            "mentally exhausting and lasting for two hours. You are entirely free to plan your day "
            "and considering only your own 'feeling best' rhythm, which ONE of the four testing "
            "times would you choose?"
        ),
        "options": [
            ("8:00–10:00 AM",  6),
            ("11:00 AM–1:00 PM", 4),
            ("3:00–5:00 PM",   2),
            ("7:00–9:00 PM",   0),
        ],
        "input": "scale",
    },
    {
        "id": 12,
        "text": "If you went to bed at 11:00 PM, at what level of tiredness would you be?",
        "options": [
            ("Not at all tired",        0),
            ("A little tired",          2),
            ("Fairly tired",            3),
            ("Very tired",              5),
        ],
        "input": "scale",
    },
    {
        "id": 13,
        "text": (
            "For some reason you have gone to bed several hours later than usual, "
            "but there is no need to get up at any particular time the next morning. "
            "Which ONE of the following events are you most likely to experience?"
        ),
        "options": [
            ("Will wake up at usual time and will NOT fall asleep",                4),
            ("Will wake up at usual time and will doze thereafter",               3),
            ("Will wake up at usual time but will fall asleep again",             2),
            ("Will NOT wake up until later than usual",                           1),
        ],
        "input": "scale",
    },
    {
        "id": 14,
        "text": (
            "One night you have to remain awake between 4:00–6:00 AM in order to carry out "
            "a night watch. You have no commitments the next day. Which ONE of the following "
            "alternatives will suit you best?"
        ),
        "options": [
            ("Would NOT go to bed until watch was over",          1),
            ("Would take a nap before and sleep after",           2),
            ("Would take a good sleep before and nap after",      3),
            ("Would take ALL sleep before watch",                  4),
        ],
        "input": "scale",
    },
    {
        "id": 15,
        "text": (
            "You have to do two hours of hard physical work. You are entirely free to plan your "
            "day and considering only your own 'feeling best' rhythm, which ONE of the following "
            "times would you choose?"
        ),
        "options": [
            ("8:00–10:00 AM",    4),
            ("11:00 AM–1:00 PM", 3),
            ("3:00–5:00 PM",     2),
            ("7:00–9:00 PM",     1),
        ],
        "input": "scale",
    },
    {
        "id": 16,
        "text": (
            "You have decided to engage in hard physical exercise. A friend suggests that you do "
            "this for one hour twice a week and the best time for him is 10:00–11:00 PM. Bearing in "
            "mind nothing else but your own 'feeling best' rhythm, how well do you think you "
            "would perform?"
        ),
        "options": [
            ("Would be in good form",        1),
            ("Would be in reasonable form",  2),
            ("Would find it difficult",      3),
            ("Would find it very difficult", 4),
        ],
        "input": "scale",
    },
    {
        "id": 17,
        "text": "Suppose that you can choose your own work hours. Assume that you worked a FIVE-hour day (including breaks). When would you prefer to BEGIN?",
        "options": [
            ("5:00–8:00 AM",   5),
            ("8:00–9:00 AM",   4),
            ("9:00 AM–2:00 PM", 3),
            ("2:00–5:00 PM",   2),
            ("5:00 PM–4:00 AM", 1),
        ],
        "input": "time",
    },
    {
        "id": 18,
        "text": "At what time of the day do you think that you reach your 'feeling best' peak?",
        "options": [
            ("5:00–8:00 AM",   5),
            ("8:00–10:00 AM",  4),
            ("10:00 AM–5:00 PM", 3),
            ("5:00–10:00 PM",  2),
            ("10:00 PM–5:00 AM", 1),
        ],
        "input": "time",
    },
    {
        "id": 19,
        "text": "One hears about 'morning' and 'evening' types of people. Which ONE of these types do you consider yourself to be?",
        "options": [
            ("Definitely a morning type",          6),
            ("Rather more a morning than evening type", 4),
            ("Rather more an evening than morning type", 2),
            ("Definitely an evening type",         0),
        ],
        "input": "scale",
    },
]

# Score → chronotype mapping (Horne & Östberg 1976, Table 4)
MEQ_SCORE_THRESHOLDS = [
    (70, 86, "lark",    "Definitely Morning"),
    (59, 69, "lark",    "Moderately Morning"),
    (42, 58, "daytime", "Intermediate"),
    (31, 41, "evening", "Moderately Evening"),
    (16, 30, "owl",     "Definitely Evening"),
]

MEQ_MIN = 16
MEQ_MAX = 86


def score_to_chronotype(score: int) -> tuple[str, str]:
    """Map a total MEQ score to (chronotype_label, meq_category)."""
    for lo, hi, label, category in MEQ_SCORE_THRESHOLDS:
        if lo <= score <= hi:
            return label, category
    return "daytime", "Out of range"  # fallback


# ---------------------------------------------------------------------------
# Mode 1: GENERATE — print questionnaire and write CSV template
# ---------------------------------------------------------------------------

def print_questionnaire() -> None:
    """Print the full MEQ in a human-readable format for reference."""
    print("=" * 72)
    print("MORNINGNESS-EVENINGNESS QUESTIONNAIRE (MEQ)")
    print("Horne & Östberg (1976) — For Academic Research Use")
    print("=" * 72)
    print()
    print("Instructions: For each question, please select the ONE answer that")
    print("best describes you. Please answer ALL questions. There are no right")
    print("or wrong answers.\n")

    for item in MEQ_ITEMS:
        print(f"Q{item['id']:02d}. {item['text']}")
        for label, score in item["options"]:
            print(f"     [ ] {label}  (score: {score})")
        print()


def generate_template() -> None:
    """
    Write CSV template with columns:
        github_username, meq_q1, meq_q2, … meq_q19, meq_total, notes

    You (the researcher) fill in the meq_q{n} columns with the SCORE VALUE
    for each participant's chosen option.
    """
    fields = ["github_username"] + [f"meq_q{i}" for i in range(1, 20)] + ["notes"]

    with MEQ_TEMPLATE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        # Write 3 example blank rows
        for _ in range(3):
            writer.writerow({k: "" for k in fields})

    print(f"Template written to: {MEQ_TEMPLATE_CSV}")
    print()
    print("HOW TO USE:")
    print("  1. Share the MEQ questionnaire with GitHub contributors.")
    print("  2. Ask them to provide their GitHub username in the form.")
    print("  3. For each response, enter the SCORE VALUE (not the label text)")
    print("     for each question into the CSV.")
    print("  4. Save as meq_responses.csv in scripts/data/")
    print("  5. Run: python scripts/02_meq_survey.py process")
    print()
    print("Score values per question option:")
    for item in MEQ_ITEMS:
        opts = ", ".join(f"{label!r}={score}" for label, score in item["options"])
        print(f"  Q{item['id']:02d}: {opts}")


# ---------------------------------------------------------------------------
# Mode 2: PROCESS — read responses, score, merge with GitHub data
# ---------------------------------------------------------------------------

def compute_meq_score(row: dict) -> int | None:
    """Sum all 19 item scores. Returns None if any item is missing."""
    total = 0
    for i in range(1, 20):
        val = row.get(f"meq_q{i}", "").strip()
        if not val:
            return None
        try:
            total += int(val)
        except ValueError:
            return None
    return total


def load_github_summary(summary_csv: Path) -> dict[str, dict]:
    """Load profiles_summary.csv from Script 01 keyed by username."""
    profiles: dict[str, dict] = {}
    if not summary_csv.exists():
        return profiles
    with summary_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            username = row.get("username", "").strip()
            if username:
                profiles[username] = row
    return profiles


def load_commit_hours(username: str) -> list[int]:
    """Load per-user hours JSON from Script 01 output."""
    path = HOURS_DIR / f"{username}_hours.json"
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def process_responses(responses_csv: Path) -> None:
    """
    Read MEQ responses CSV, compute scores, merge with GitHub data,
    write merged_dataset.csv and a scoring report.
    """
    if not responses_csv.exists():
        sys.exit(
            f"ERROR: Responses file not found: {responses_csv}\n"
            "Fill in scripts/data/meq_template.csv and save as meq_responses.csv"
        )

    # Load GitHub summaries from Script 01
    summary_path = DATA_DIR / "profiles_summary.csv"
    gh_profiles = load_github_summary(summary_path)
    if not gh_profiles:
        print("WARNING: profiles_summary.csv not found. GitHub metrics will be empty.")
        print("         Run 01_collect_github_profiles.py first.\n")

    merged_fields = [
        "github_username",
        "meq_total",
        "meq_category",
        "meq_chronotype",          # MEQ-derived label: lark/daytime/evening/owl
        "gh_commit_count_90d",
        "gh_commit_hours_sample",  # JSON list of first 20 hours (for spot check)
        "gh_async_ratio",
        "gh_collaboration_index",
        "gh_pr_count_90d",
        "gh_location",
        "notes",
        "matched",                  # True if GitHub data found for this user
    ]

    rows_out: list[dict] = []
    report_lines: list[str] = [
        "MEQ Scoring Report — GitSyntropy Research",
        "=" * 60,
        "",
    ]

    unmatched: list[str] = []
    incomplete: list[str] = []

    with responses_csv.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row.get("github_username", "").strip().lstrip("@")
            if not username:
                continue

            # Score MEQ
            total = compute_meq_score(row)
            if total is None:
                incomplete.append(username)
                report_lines.append(f"  {username:30s}  INCOMPLETE (missing items)")
                continue

            if not (MEQ_MIN <= total <= MEQ_MAX):
                report_lines.append(
                    f"  {username:30s}  SCORE OUT OF RANGE: {total} (expected {MEQ_MIN}–{MEQ_MAX})"
                )
                continue

            meq_label, meq_category = score_to_chronotype(total)

            # Merge with GitHub data
            gh = gh_profiles.get(username, {})
            matched = bool(gh)
            if not matched:
                unmatched.append(username)

            hours = load_commit_hours(username)

            out_row = {
                "github_username": username,
                "meq_total": total,
                "meq_category": meq_category,
                "meq_chronotype": meq_label,
                "gh_commit_count_90d": gh.get("commit_count_90d", ""),
                "gh_commit_hours_sample": json.dumps(hours[:20]) if hours else "[]",
                "gh_async_ratio": gh.get("async_ratio", ""),
                "gh_collaboration_index": gh.get("collaboration_index", ""),
                "gh_pr_count_90d": gh.get("pr_count_90d", ""),
                "gh_location": gh.get("location", ""),
                "notes": row.get("notes", ""),
                "matched": matched,
            }
            rows_out.append(out_row)

            report_lines.append(
                f"  {username:30s}  MEQ={total:3d}  {meq_category:25s} → {meq_label:8s}"
                f"  {'(GitHub matched)' if matched else '(NO GitHub data)'}"
            )

    # Write merged CSV
    with MERGED_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=merged_fields)
        writer.writeheader()
        writer.writerows(rows_out)

    # Write report
    report_lines.extend([
        "",
        "=" * 60,
        f"Total processed    : {len(rows_out)}",
        f"Incomplete (skipped): {len(incomplete)} — {', '.join(incomplete) or 'none'}",
        f"No GitHub data     : {len(unmatched)} — {', '.join(unmatched) or 'none'}",
        f"Fully matched      : {sum(1 for r in rows_out if r['matched'])}",
        "",
        "Chronotype distribution (MEQ-derived):",
    ])
    for ct in ["lark", "daytime", "evening", "owl"]:
        n = sum(1 for r in rows_out if r["meq_chronotype"] == ct)
        bar = "█" * n
        report_lines.append(f"  {ct:8s} : {n:3d}  {bar}")

    with REPORT_FILE.open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    # Print summary to console
    print("\n".join(report_lines[-15:]))
    print(f"\nMerged dataset : {MERGED_CSV}")
    print(f"Scoring report : {REPORT_FILE}")

    if rows_out:
        matched_n = sum(1 for r in rows_out if r["matched"])
        print(f"\nFully matched profiles for analysis: {matched_n}")
        if matched_n < 30:
            print("WARNING: Need ≥30 matched profiles for publication. Collect more responses.")
        elif matched_n < 50:
            print("NOTE: 30+ profiles is publishable; 50+ is preferred.")
        else:
            print("✓ Sufficient matched profiles. Proceed to Script 03.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitSyntropy MEQ survey instrument and response processor"
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    sub.add_parser("generate", help="Print MEQ and write CSV template")

    proc = sub.add_parser("process", help="Process filled-in MEQ responses")
    proc.add_argument(
        "--responses",
        type=Path,
        default=DATA_DIR / "meq_responses.csv",
        help="Path to filled-in MEQ responses CSV (default: scripts/data/meq_responses.csv)",
    )
    proc.add_argument(
        "--print-questionnaire",
        action="store_true",
        help="Also print the full questionnaire text",
    )

    args = parser.parse_args()

    if args.mode == "generate":
        print_questionnaire()
        print("\n" + "=" * 72 + "\n")
        generate_template()

    elif args.mode == "process":
        if getattr(args, "print_questionnaire", False):
            print_questionnaire()
        process_responses(args.responses)


if __name__ == "__main__":
    main()

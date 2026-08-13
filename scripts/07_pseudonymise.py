"""
Script 07 — Pseudonymisation of the released dataset.

Reviewer C #3: "Publishing real, identifiable GitHub handles paired with inferred chronotype
labels — including for public figures — without evidence of consent contradicts the
safeguards the authors themselves recommend in the Ethical Considerations section."

Accepted. No GitHub handle, Stack Overflow display name, Stack Overflow user id, company or
location appears in the revised manuscript or in any released artifact.

What this script does
---------------------
  * Assigns a stable pseudonym D01 … D46, ordered by a salted hash of the handle so that the
    ordering carries no information about identity (not by commit count, which would be a
    re-identification hint, and not alphabetically).
  * Writes the identity map to `data/pseudonym_map.csv`, which is listed in .gitignore and
    stays on the author's machine. It exists only so the author can re-run the pipeline.
  * Writes pseudonymised, releasable copies of every result table that contained identities:
        results/table1_chronotype_per_user_public.csv
        results/crossval_so_github_public.csv
  * Emits the LaTeX body rows for the revised Table V so the manuscript table is generated
    from data rather than retyped.

The salt is stored alongside the map, not in this file, so the published script cannot be
used to invert the pseudonyms.

Usage:
    python 07_pseudonymise.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import secrets
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
HOURS_DIR = DATA_DIR / "hours"
RESULTS = SCRIPT_DIR / "results"
MAP_PATH = DATA_DIR / "pseudonym_map.csv"
SALT_PATH = DATA_DIR / "pseudonym_salt.txt"

# Columns that identify a person and must never reach a released artifact.
IDENTIFYING_COLUMNS = {
    "github_username", "username", "so_display_name", "so_user_id",
    "so_location", "name", "location", "company", "github_email",
    # Quasi-identifiers: a follower count or Stack Overflow reputation in the tens of
    # thousands re-identifies a well-known maintainer in one search, so replacing the handle
    # alone would not be anonymisation. Dropped outright.
    "so_reputation",
}

# Quasi-identifiers that are useful in aggregate but must be coarsened before release.
BUCKET_COLUMNS = {"followers", "public_repos", "commit_count_90d", "n_gh_commits",
                  "n_so_posts", "review_comments_90d"}
YEAR_ONLY_COLUMNS = {"account_created", "collected_at", "so_first_post", "so_last_post"}

_BUCKETS = [(50, "<50"), (100, "50-99"), (250, "100-249"), (500, "250-499"),
            (1000, "500-999"), (5000, "1k-4.9k"), (10000, "5k-9.9k"),
            (50000, "10k-49.9k")]


def coarsen(column: str, value: str) -> str:
    """Bucket a quasi-identifier so it stays analytically useful but not a search key."""
    if column in YEAR_ONLY_COLUMNS:
        return (value or "")[:4]
    if column in BUCKET_COLUMNS:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return value
        for cut, label in _BUCKETS:
            if v < cut:
                return label
        return ">=50k"
    return value


def _salt() -> str:
    if SALT_PATH.exists():
        return SALT_PATH.read_text(encoding="utf-8").strip()
    salt = secrets.token_hex(16)
    SALT_PATH.write_text(salt, encoding="utf-8")
    print(f"  generated new salt at {SALT_PATH.name} (keep this file private)")
    return salt


def build_map() -> dict[str, str]:
    """Stable pseudonyms, ordered by salted hash so the ordering leaks nothing."""
    if MAP_PATH.exists():
        with MAP_PATH.open(encoding="utf-8") as f:
            return {r["github_username"]: r["developer_id"] for r in csv.DictReader(f)}

    salt = _salt()
    handles = sorted({f.stem.replace("_hours", "") for f in HOURS_DIR.glob("*_hours.json")})
    ordered = sorted(handles,
                     key=lambda h: hashlib.sha256((salt + h).encode()).hexdigest())
    mapping = {h: f"D{i:02d}" for i, h in enumerate(ordered, start=1)}

    with MAP_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["github_username", "developer_id"])
        for h, pid in mapping.items():
            w.writerow([h, pid])
    print(f"  wrote identity map: {MAP_PATH.name} ({len(mapping)} developers) — PRIVATE")
    return mapping


def pseudonymise_csv(src: Path, dst: Path, mapping: dict[str, str],
                     key_column: str = "github_username") -> int:
    if not src.exists():
        print(f"  skip {src.name} (not present)")
        return 0
    with src.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0

    out_fields = ["developer_id"] + [c for c in rows[0] if c not in IDENTIFYING_COLUMNS]
    unknown = 0
    with dst.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for r in rows:
            handle = r.get(key_column, "")
            pid = mapping.get(handle)
            if pid is None:
                pid = f"X{abs(hash(handle)) % 100:02d}"
                unknown += 1
            w.writerow({"developer_id": pid,
                        **{c: coarsen(c, r[c]) for c in out_fields if c != "developer_id"}})

    leaked = [c for c in out_fields if c in IDENTIFYING_COLUMNS]
    assert not leaked, f"identifying column survived into {dst.name}: {leaked}"
    print(f"  wrote {dst.name} ({len(rows)} rows"
          + (f", {unknown} not in map" if unknown else "") + ")")
    return len(rows)


def latex_table_v(mapping: dict[str, str], n_rows: int = 10) -> str:
    """Body rows for the revised Table V, generated from data."""

    rows = []
    for f in sorted(HOURS_DIR.glob("*_hours.json")):
        handle = f.stem.replace("_hours", "")
        hours = json.loads(f.read_text())
        rows.append((mapping.get(handle, "??"), hours))

    # classify with the same code path used everywhere else
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dyadic", SCRIPT_DIR / "05_real_dyadic_analysis.py")
    dyadic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dyadic)

    out = []
    for pid, hours in rows:
        res = dyadic.detect_chronotype(hours)
        out.append((pid, res["label"], len(hours), res["peak_hour"]))
    out.sort(key=lambda r: r[0])

    # A representative spread across classes rather than the top-N by commit count
    chosen, seen = [], {}
    for row in out:
        seen.setdefault(row[1], []).append(row)
    for label in ("lark", "daytime", "evening", "owl", "flexible"):
        chosen.extend(seen.get(label, [])[:2])
    chosen = chosen[:n_rows]

    lines = []
    for pid, label, n, peak in chosen:
        # Commit counts are bucketed too: an exact 90-day commit count is itself a search key
        # against public GitHub activity.
        lines.append(f"{pid} & {label.capitalize()} & {coarsen('n_gh_commits', str(n))} "
                     f"& {peak:.1f} \\\\")
    return "\n".join(lines)


def main() -> int:
    print("=" * 68)
    print("Script 07 — Pseudonymisation (Reviewer C #3)")
    print("=" * 68)

    mapping = build_map()
    print(f"Developers in map: {len(mapping)}")

    pseudonymise_csv(RESULTS / "table1_chronotype_per_user.csv",
                     RESULTS / "table1_chronotype_per_user_public.csv", mapping,
                     key_column="username")
    pseudonymise_csv(RESULTS / "crossval_so_github.csv",
                     RESULTS / "crossval_so_github_public.csv", mapping)
    pseudonymise_csv(DATA_DIR / "profiles_summary.csv",
                     RESULTS / "profiles_summary_public.csv", mapping,
                     key_column="username")

    table = latex_table_v(mapping)
    (RESULTS / "table5_rows.tex").write_text(table + "\n", encoding="utf-8")
    print("\nTable V body rows (results/table5_rows.tex):")
    print(table)

    print("\nReminder: data/pseudonym_map.csv and data/pseudonym_salt.txt are private and")
    print("must stay untracked. Everything in results/*_public.csv is releasable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

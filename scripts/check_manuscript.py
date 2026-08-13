"""
Script — pre-submission checks on the manuscript.

No LaTeX toolchain is assumed, so this does not replace compiling the document; it catches
the failure modes that would otherwise only surface at compile time or, worse, in review:

  1. Every \label is unique; every \ref and \eqref resolves to a defined label.
  2. Every \cite key resolves to a \bibitem; every \bibitem is cited at least once.
  3. Environments (\begin/\end) are balanced and correctly nested; braces balance.
  4. Every \includegraphics target exists on disk.
  5. No real GitHub handle, Stack Overflow display name, or the delisted-journal name
     survives anywhere in the manuscript (Reviewer C #2 and #3).
  6. Glued-word artifacts of the kind Reviewer B reported ("chronotypethe", "isto") — run
     over the .tex source and, if given, over the extracted text of the final PDF or DOCX.

Usage:
    python check_manuscript.py ../paper/final.tex [--pdf ../paper/final.pdf]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

GLUE_WORDS = ("the", "and", "is", "to", "of", "in", "a", "that", "with", "for")
FORBIDDEN_SUBSTRINGS = [
    "Testing, Psychometrics, Methodology in Applied Psychology",
    "maiti2025", "bhuvaneswari2025",
]


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", text)


def prose_only(text: str) -> str:
    """Approximate the rendered prose: drop macro names, cross-reference arguments, math,
    and verbatim-ish content, so that scans for identifiers and glued words do not trip over
    LaTeX syntax (``\\renewcommand``, ``tab:dims``, ``\\texttt{...}``)."""
    out = re.sub(r"\\(label|ref|eqref|cite|includegraphics|bibitem|texttt|url|input)"
                 r"(\[[^\]]*\])?\{[^}]*\}", " ", text)
    out = re.sub(r"\$[^$]*\$", " ", out)
    out = re.sub(r"\\[A-Za-z@]+", " ", out)   # remaining macro names
    return out


def check_refs(src: str) -> list[str]:
    problems = []
    labels = re.findall(r"\\label\{([^}]+)\}", src)
    dupes = {l for l in labels if labels.count(l) > 1}
    problems += [f"duplicate label: {l}" for l in sorted(dupes)]

    refs = set(re.findall(r"\\(?:eq)?ref\{([^}]+)\}", src))
    for r in sorted(refs - set(labels)):
        problems.append(f"undefined reference: \\ref{{{r}}}")

    unused = set(labels) - refs
    for l in sorted(unused):
        problems.append(f"note: label never referenced: {l}")
    return problems


def check_citations(src: str) -> list[str]:
    problems = []
    keys: list[str] = []
    for group in re.findall(r"\\cite\{([^}]+)\}", src):
        keys += [k.strip() for k in group.split(",")]
    bibitems = re.findall(r"\\bibitem\{([^}]+)\}", src)

    for k in sorted(set(keys) - set(bibitems)):
        problems.append(f"citation with no bibitem: {k}")
    for b in sorted(set(bibitems) - set(keys)):
        problems.append(f"bibitem never cited: {b}")
    dupes = {b for b in bibitems if bibitems.count(b) > 1}
    problems += [f"duplicate bibitem: {b}" for b in sorted(dupes)]
    return problems


def check_environments(src: str) -> list[str]:
    problems, stack = [], []
    for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", src):
        kind, name = m.group(1), m.group(2)
        line = src[:m.start()].count("\n") + 1
        if kind == "begin":
            stack.append((name, line))
        else:
            if not stack:
                problems.append(f"line {line}: \\end{{{name}}} with no matching \\begin")
            elif stack[-1][0] != name:
                problems.append(f"line {line}: \\end{{{name}}} closes "
                                f"\\begin{{{stack[-1][0]}}} from line {stack[-1][1]}")
                stack.pop()
            else:
                stack.pop()
    for name, line in stack:
        problems.append(f"line {line}: \\begin{{{name}}} never closed")

    depth = 0
    for i, ch in enumerate(src):
        if ch == "{" and (i == 0 or src[i - 1] != "\\"):
            depth += 1
        elif ch == "}" and (i == 0 or src[i - 1] != "\\"):
            depth -= 1
            if depth < 0:
                problems.append(f"line {src[:i].count(chr(10)) + 1}: unbalanced closing brace")
                depth = 0
    if depth:
        problems.append(f"unbalanced braces: {depth} unclosed")
    return problems


def check_graphics(src: str, tex_path: Path) -> list[str]:
    problems = []
    search_dirs = [tex_path.parent, tex_path.parent / "figures"]
    for target in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", src):
        found = any((d / f"{target}{ext}").exists()
                    for d in search_dirs for ext in ("", ".pdf", ".png", ".eps"))
        if not found:
            problems.append(f"missing figure: {target}")
    return problems


def check_identifiers(src: str, tex_path: Path) -> list[str]:
    """No real handle may survive anywhere in the manuscript."""
    problems = []
    for bad in FORBIDDEN_SUBSTRINGS:
        if bad in src:
            problems.append(f"forbidden string present: {bad!r}")

    map_path = tex_path.parent.parent / "scripts" / "data" / "pseudonym_map.csv"
    if map_path.exists():
        with map_path.open(encoding="utf-8") as f:
            handles = [r["github_username"] for r in csv.DictReader(f)]
        for h in handles:
            if re.search(rf"(?<![\w/-]){re.escape(h)}(?![\w-])", src):
                problems.append(f"real GitHub handle present in manuscript: {h}")
    else:
        problems.append("note: pseudonym_map.csv not found — handle check skipped")
    return problems


def check_glued_words(text: str, label: str) -> list[str]:
    problems = []
    pattern = re.compile(r"\b[a-z]{4,}(" + "|".join(GLUE_WORDS) + r")\b")
    known_ok = {"analysis", "hypothesis", "synthesis", "within", "sustain", "certain",
                "domain", "obtain", "maintain", "contain", "explain", "remain", "again",
                "brain", "chain", "plain", "train", "grain", "retain", "detain", "villain",
                "captain", "curtain", "mountain", "fountain", "bargain", "margin", "origin",
                "margina", "thesis", "basis", "crisis", "axis", "genesis", "emphasis",
                "diagnosis", "prognosis", "parenthesis", "psychosis", "osmosis",
                "metadata", "errata", "data", "beta", "delta", "theta", "media"}
    for m in pattern.finditer(text):
        word = m.group(0)
        if word in known_ok:
            continue
        stem = word[: -len(m.group(1))]
        # A real word ending in the glue string is fine; a glued pair is not. Heuristic:
        # flag when the stem is itself a plausible standalone word of 4+ chars.
        if len(stem) >= 5:
            ctx = text[max(0, m.start() - 40):m.end() + 20].replace("\n", " ")
            problems.append(f"[{label}] possible glued word {word!r} in: ...{ctx}...")
    return problems


def extract_pdf_text(path: Path) -> str:
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # noqa: N813
        except ImportError:
            return ""
    doc = pymupdf.open(path)
    return "".join(page.get_text() for page in doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tex", type=Path)
    ap.add_argument("--pdf", type=Path, default=None,
                    help="compiled PDF, checked for glued-word artifacts before submission")
    args = ap.parse_args()

    raw = args.tex.read_text(encoding="utf-8")
    src = strip_comments(raw)

    sections = {
        "references": check_refs(src),
        "citations": check_citations(src),
        "environments": check_environments(src),
        "graphics": check_graphics(src, args.tex),
        "identifiers": check_identifiers(prose_only(raw), args.tex),
        "typography (tex)": check_glued_words(prose_only(src), "tex"),
    }

    if args.pdf and args.pdf.exists():
        text = extract_pdf_text(args.pdf)
        if text:
            sections["typography (pdf)"] = check_glued_words(text, "pdf")
            leaked = [b for b in FORBIDDEN_SUBSTRINGS if b in text]
            sections["identifiers (pdf)"] = [f"forbidden string in PDF: {b}" for b in leaked]
        else:
            sections["typography (pdf)"] = ["note: install pymupdf to scan the PDF"]
    elif args.pdf:
        sections["typography (pdf)"] = [f"note: {args.pdf} not found — compile first"]

    print("=" * 68)
    print(f"Manuscript checks — {args.tex}")
    print("=" * 68)

    hard_errors = 0
    for name, problems in sections.items():
        real = [p for p in problems if not p.startswith("note:") and "[note]" not in p]
        notes = [p for p in problems if p.startswith("note:")]
        status = "OK" if not real else f"{len(real)} issue(s)"
        print(f"\n{name:<22s} {status}")
        for p in real:
            print(f"  ! {p}")
        for p in notes:
            print(f"  - {p}")
        hard_errors += len(real)

    print("\n" + "=" * 68)
    print(f"{hard_errors} issue(s) requiring attention")
    print("NOTE: this does not replace compiling the document. Compile with pdflatex or")
    print("Overleaf and re-run with --pdf before submitting.")
    return 1 if hard_errors else 0


if __name__ == "__main__":
    sys.exit(main())

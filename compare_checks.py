"""Iterate, Step 7: how well do the checks catch mistakes?

Reads an evaluation run made with --citations --entropy and counts, for each
check, how many wrong or made-up answers it caught and how many correct
answers it flagged by mistake (false alarms).

What counts as a flag:
  citation checker      - any citation unsupported or not found
  entropy (low)         - confidence "low"
  entropy (low/medium)  - confidence "low" or "medium" (a stricter alarm)
Both entropy rules (strict and loose) are reported.

    python compare_checks.py results/eval_..._full-checks.json \
        --baseline results/eval_..._baseline-regraded.json

Saves the summary as results/checks_<date>_<time>.txt.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent


def checks(r):
    """Every check's flag for one answer: name -> True if flagged."""
    return {
        "Citation checker": r["citation_flag"] == "FLAG",
        "Entropy strict (low)": r["confidence"] == "low",
        "Entropy strict (low/medium)": r["confidence"] in ("low", "medium"),
        "Entropy loose (low)": r["confidence_loose"] == "low",
        "Entropy loose (low/medium)": r["confidence_loose"] in ("low", "medium"),
        "Citations OR entropy loose (low/medium)": (
            r["citation_flag"] == "FLAG" or r["confidence_loose"] in ("low", "medium")
        ),
        "Citations OR entropy strict (low)": r["citation_flag"] == "FLAG" or r["confidence"] == "low",
    }


def rate(part, whole):
    return f"{part}/{whole}" + (f" ({part / whole:.0%})" if whole else "")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", help="results JSON from evaluate.py --citations --entropy")
    parser.add_argument("--baseline", help="baseline results JSON (no checks), for comparison")
    args = parser.parse_args()

    rows = json.loads(Path(args.run).read_text())
    bad = [r for r in rows if r["grade"] in ("wrong", "made_up")]
    good = [r for r in rows if r["grade"] == "correct"]
    n = len(rows)

    lines = [f"Run: {args.run}", ""]
    if args.baseline:
        base = json.loads(Path(args.baseline).read_text())
        made = sum(r["grade"] == "made_up" for r in base)
        right = sum(r["grade"] == "correct" for r in base)
        lines += [
            f"BASELINE (no checks): {args.baseline}",
            f"  accuracy {rate(right, len(base))}, hallucination rate {rate(made, len(base))}",
            "",
        ]
    lines += [
        "THIS RUN (new answers, graded the same way):",
        f"  correct {len(good)}, wrong {sum(r['grade'] == 'wrong' for r in rows)}, "
        f"made_up {sum(r['grade'] == 'made_up' for r in rows)}  (of {n})",
        f"  hallucination rate {rate(sum(r['grade'] == 'made_up' for r in rows), n)}",
        "",
        "HOW EACH CHECK DID",
        f"  {'check':<42}{'caught (wrong or made up)':<28}{'false alarms (correct flagged)':<32}",
    ]
    names = list(checks(rows[0]))
    for name in names:
        caught = sum(checks(r)[name] for r in bad)
        false_alarms = sum(checks(r)[name] for r in good)
        lines.append(f"  {name:<42}{rate(caught, len(bad)):<28}{rate(false_alarms, len(good)):<32}")

    missed = [r for r in bad if not checks(r)["Citation checker"] and not checks(r)["Entropy loose (low/medium)"]
              and not checks(r)["Entropy strict (low)"]]
    lines += [
        "",
        f"Wrong or made-up answers missed by BOTH checks (citations, and entropy with either rule): "
        f"{rate(len(missed), len(bad))}",
    ]
    for r in missed:
        lines.append(f"  - [{r['grade']}] {r['question']}")

    lines += ["", "PER QUESTION",
              f"  {'grade':<9}{'citations':<11}{'strict':<9}{'loose':<9}{'search':<9}question"]
    for r in rows:
        lines.append(
            f"  {r['grade']:<9}{r['citation_flag']:<11}{r['confidence']:<9}{r['confidence_loose']:<9}"
            f"{r['source_section_retrieved']:<9}{r['question']}"
        )

    text = "\n".join(lines)
    out = ROOT / "results" / f"checks_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"
    out.write_text(text + "\n")
    print(text)
    print(f"\nSaved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

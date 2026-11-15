"""Iterate, part 1: measure how accurate the assistant is.

Reads test_set.csv, which has four columns:
  question        - a question a real person might ask
  correct_answer  - the right answer, checked on ontario.ca/laws
  source_section  - where the answer is, e.g. "RTA 116" or "ESA 17; ESA 18"
                    (RTA / ESA / CPA), or "NONE" if the laws don't cover it
  type            - your own label, e.g. easy, tricky, not_covered

Each question goes through the normal assistant (answer.py, unchanged). Then
an AI judge compares the assistant's answer with correct_answer and grades it:
  correct   - gets the main point right (for not-covered questions: says it
              couldn't find it)
  wrong     - misses or gets the main point wrong, without inventing law
              (e.g. says "couldn't find this" when the answer exists)
  made_up   - states law that isn't true: a wrong rule, number, deadline or
              section, or answers a not-covered question from memory

Results go in results/, named with the date and time so runs never overwrite
each other:
  eval_<date>_<time>[_<label>].csv   one row per question (open in Excel/Numbers)
  eval_<date>_<time>[_<label>].json  everything, including the law sections used
  eval_<date>_<time>[_<label>].txt   the summary that was printed

    python evaluate.py                     # whole test set
    python evaluate.py --limit 2           # first 2 questions only (a cheap test)
    python evaluate.py --label baseline    # adds "_baseline" to the file names
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import anthropic

from answer import MissingKeyError, answer
from citations import check_citations
from search import saved_sections

ROOT = Path(__file__).parent
TEST_SET = ROOT / "test_set.csv"
RESULTS_DIR = ROOT / "results"

# The cheapest model, same one the assistant uses.
JUDGE_MODEL = "claude-haiku-5-5"

LAW_NAMES = {
    "RTA": "Residential Tenancies Act, 2006",
    "ESA": "Employment Standards Act, 2000",
    "CPA": "Consumer Protection Act, 2002",
}
GRADES = ("correct", "wrong", "made_up")

JUDGE_PROMPT = """You grade answers from an Ontario law assistant against an answer key written by a person who checked the official law.

You get the question, the answer key, the official text of the answer key's law section(s) if there are any, the official text of every section the assistant was given, and the assistant's answer.

Judge only from these texts. Do NOT use your own memory of Ontario law: it may be out of date or wrong. A claim counts as supported if the answer key or any of the provided law texts says it.

Grade the assistant's answer with exactly one label:

correct - The answer gets the main point of the answer key right. Extra true detail is fine. If the answer key says the question is not covered by the assistant's laws, "correct" means the assistant said it couldn't find it.
wrong - The answer misses or gets the main point wrong, but does not invent law. For example: it says it couldn't find the answer when the answer key has one, it answers a different question, or it misreads the law (like reading an exception as the rule).
made_up - The answer states law that isn't true: a rule, number, deadline, amount or section that contradicts the answer key or the provided law texts, or that none of the provided texts support. Also use this if the question is not covered and the assistant answers it anyway with legal rules.

If an answer is both wrong and invents law, choose made_up.

Reply in exactly this format:
GRADE: <correct, wrong or made_up>
REASON: <one or two sentences>"""


def parse_sections(text):
    """'RTA 116; ESA s. 17' -> [('Residential Tenancies Act, 2006', '116'), ...]"""
    return [
        (LAW_NAMES[law.upper()], number)
        for law, number in re.findall(r"(RTA|ESA|CPA)\s*(?:s\.)?\s*(\d+(?:\.\d+)*)", text, re.I)
    ]


def official_text(source_section):
    """The real law text of the answer key's sections, to help the judge."""
    sections = saved_sections()
    blocks = []
    for law, number in parse_sections(source_section):
        text = sections.get((law, number), "(section not found in the database)")
        blocks.append(f"{law}, s. {number}:\n{text[:8000]}")
    return "\n\n".join(blocks) or "(none - the answer key says the question isn't covered)"


def judge(client, row, assistant_answer, sections_used):
    """Ask the judge model to grade one answer. Returns (grade, reason)."""
    used = "\n\n".join(s["text"] for s in sections_used) or "(none)"
    message = (
        f"QUESTION:\n{row['question']}\n\n"
        f"ANSWER KEY:\n{row['correct_answer']}\n\n"
        f"OFFICIAL TEXT OF THE ANSWER KEY'S SECTIONS:\n{official_text(row['source_section'])}\n\n"
        f"OFFICIAL TEXT OF THE SECTIONS THE ASSISTANT WAS GIVEN:\n{used}\n\n"
        f"ASSISTANT'S ANSWER:\n{assistant_answer}"
    )
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4000,
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": message}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    grade = re.search(r"GRADE:\s*(correct|wrong|made_up)", text, re.I)
    reason = re.search(r"REASON:\s*(.+)", text, re.S)
    return (
        grade.group(1).lower() if grade else "unclear",
        reason.group(1).strip() if reason else text.strip(),
    )


def short(law, number):
    """('Residential Tenancies Act, 2006', '116') -> 'RTA 116'"""
    abbreviations = {name: abbr for abbr, name in LAW_NAMES.items()}
    return f"{abbreviations.get(law, law)} {number}"


def source_found(expected, retrieved):
    """Did search find the answer key's sections? yes / partial / NO / n/a"""
    if not expected:
        return "n/a"
    found = set(expected) & set(retrieved)
    return "yes" if found == set(expected) else "partial" if found else "NO"


def run_question(client, row, result=None, citations=False):
    """Run one test question through the assistant (unless a saved result is
    given, when re-grading), the judge, and any checks that are switched on."""
    if result is None:
        result = answer(row["question"])
    retrieved = [short(s["law"], s["section"]) for s in result["sections"]]
    expected = [short(law, n) for law, n in parse_sections(row["source_section"])]
    grade, reason = judge(client, row, result["answer"], result["sections"])
    checks = {}
    if citations:
        found, summary = check_citations(client, result["answer"], result["sections"])
        checks.update(summary)
        checks["_citations"] = found
    return {
        "question": row["question"],
        "type": row["type"],
        "correct_answer": row["correct_answer"],
        "source_section": row["source_section"],
        "assistant_answer": result["answer"],
        "search_rewrite": result["rewrite"],
        "sections_retrieved": "; ".join(retrieved),
        # Did search find the answer key's section? Tells you whether a wrong
        # answer is a search problem or an answering problem.
        "source_section_retrieved": source_found(expected, retrieved),
        "grade": grade,
        "judge_reason": reason,
        **checks,
        # Kept only in the .json file, for re-grading and later checks.
        "_sections": result["sections"],
    }


def summarize(rows):
    """Accuracy, hallucination rate and a per-question table, as text."""
    n = len(rows)
    count = {g: sum(r["grade"] == g for r in rows) for g in GRADES + ("unclear",)}
    lines = [
        f"Questions: {n}",
        f"Accuracy:           {count['correct']}/{n} = {count['correct'] / n:.0%}",
        f"Hallucination rate: {count['made_up']}/{n} = {count['made_up'] / n:.0%}  (graded made_up)",
        f"Wrong (not made up): {count['wrong']}/{n}",
    ]
    if count["unclear"]:
        lines.append(f"Judge reply unclear: {count['unclear']} (check the reasons)")
    types = sorted({r["type"] for r in rows})
    if len(types) > 1:
        lines.append("")
        lines.append("By type:")
        for t in types:
            group = [r for r in rows if r["type"] == t]
            ok = sum(r["grade"] == "correct" for r in group)
            bad = sum(r["grade"] == "made_up" for r in group)
            lines.append(f"  {t:<14} {ok}/{len(group)} correct, {bad} made up")
    if "citation_flag" in rows[0]:
        total = sum(r["citations_total"] for r in rows)
        flagged = [r for r in rows if r["citation_flag"] == "FLAG"]
        lines += [
            "",
            "Citation checker:",
            f"  citations checked: {total} "
            f"({sum(r['citations_verified'] for r in rows)} verified, "
            f"{sum(r['citations_unsupported'] for r in rows)} unsupported, "
            f"{sum(r['citations_not_found'] for r in rows)} not found)",
            f"  answers flagged: {len(flagged)}/{n}",
        ]
        for g in GRADES:
            group = [r for r in rows if r["grade"] == g]
            if group:
                hit = sum(r["citation_flag"] == "FLAG" for r in group)
                lines.append(f"    flagged among {g:<8} answers: {hit}/{len(group)}")
    lines += ["", "Per question:"]
    for i, r in enumerate(rows, 1):
        flag = f"citations: {r['citation_flag']:<4}  " if "citation_flag" in r else ""
        lines.append(
            f"  {i:>2}. [{r['grade']:<7}] search found source: {r['source_section_retrieved']:<7}  {flag}{r['question']}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    parser.add_argument("--label", default="", help="added to the result file names, e.g. baseline")
    parser.add_argument(
        "--regrade", metavar="RESULTS.json",
        help="re-judge the answers saved in an earlier run instead of asking the assistant again",
    )
    parser.add_argument("--citations", action="store_true", help="also run the citation checker")
    args = parser.parse_args()

    with TEST_SET.open() as f:
        tests = [row for row in csv.DictReader(f) if row["question"].strip()]
    if args.limit:
        tests = tests[: args.limit]

    # When re-grading, reuse the saved answers (and the sections they used).
    saved = {}
    if args.regrade:
        for r in json.loads(Path(args.regrade).read_text()):
            saved[r["question"]] = {
                "answer": r["assistant_answer"], "rewrite": r["search_rewrite"], "sections": r["_sections"],
            }
        tests = [row for row in tests if row["question"] in saved]

    client = anthropic.Anthropic()
    rows = []
    for i, row in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {row['question']}", flush=True)
        try:
            rows.append(run_question(client, row, saved.get(row["question"]), citations=args.citations))
        except MissingKeyError as e:
            sys.exit(f"Stopping: {e}")
        flag = f", citations: {rows[-1]['citation_flag']}" if args.citations else ""
        print(f"         -> {rows[-1]['grade']}{flag}", flush=True)

    # Save everything, named by date and time so nothing gets overwritten.
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = RESULTS_DIR / (f"eval_{stamp}" + (f"_{args.label}" if args.label else ""))

    columns = [k for k in rows[0] if not k.startswith("_")]
    with base.with_suffix(".csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    base.with_suffix(".json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))

    summary = summarize(rows)
    base.with_suffix(".txt").write_text(summary + "\n")
    print("\n" + summary)
    print(f"\nSaved: {base.relative_to(ROOT)}.csv / .json / .txt")


if __name__ == "__main__":
    main()

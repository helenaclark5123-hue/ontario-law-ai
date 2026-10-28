"""Run my test questions through the app and save the results for grading.

Reads questions.csv, which has three columns:
  question          - the question a real person might ask
  correct_answer    - the right answer, from ontario.ca/laws (my answer key)
  correct_sections  - where the answer is, e.g. "RTA 116" or "ESA 17; ESA 18"
                      (RTA / ESA / CPA), or "NONE" if the laws don't cover it

Writes results.csv (opens in Excel, Numbers or Google Sheets) with the app's
answer, the sections it cited and found, some automatic checks, and empty
columns for my own grading.

    python run_tests.py
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import csv
import re
from pathlib import Path

from answer import NOT_FOUND, MissingKeyError, answer
from get_laws import load_saved_laws

ROOT = Path(__file__).parent
QUESTIONS = ROOT / "questions.csv"
RESULTS = ROOT / "results.csv"

SHORT = {
    "Residential Tenancies Act, 2006": "RTA",
    "Employment Standards Act, 2000": "ESA",
    "Consumer Protection Act, 2002": "CPA",
}
CITATION = re.compile(
    "(" + "|".join(re.escape(name) for name in SHORT) + r"),?\s*s\.\s*(\d+(?:\.\d+)*)"
)


def parse_sections(text):
    """'RTA 116; ESA s. 17' -> {'RTA 116', 'ESA 17'}"""
    return {f"{law.upper()} {num}" for law, num in re.findall(r"(RTA|ESA|CPA)\s*(?:s\.)?\s*([\d.]+)", text, re.I)}


def main():
    real_sections = {
        f"{SHORT[law['name']]} {number}" for law in load_saved_laws() for number in law["sections"]
    }
    with QUESTIONS.open() as f:
        tests = [row for row in csv.DictReader(f) if row["question"].strip()]

    rows = []
    for i, test in enumerate(tests, start=1):
        print(f"[{i}/{len(tests)}] {test['question']}")
        try:
            result = answer(test["question"])
        except MissingKeyError as e:
            print(f"Stopping: {e}")
            return

        cited = [f"{SHORT[law]} {num}" for law, num in CITATION.findall(result["answer"])]
        cited = list(dict.fromkeys(cited))
        found = list(dict.fromkeys(f"{SHORT[c['law']]} {c['section']}" for c in result["sections"]))
        expected = parse_sections(test["correct_sections"])
        not_covered = test["correct_sections"].strip().upper() == "NONE"

        rows.append({
            "question": test["question"],
            "correct_answer": test["correct_answer"],
            "correct_sections": test["correct_sections"],
            "my_app_answer": result["answer"],
            "sections_cited": "; ".join(cited),
            "sections_found_by_search": "; ".join(found),
            # Automatic checks
            "said_couldnt_find": "yes" if NOT_FOUND.rstrip(".") in result["answer"] else "no",
            "cited_sections_all_exist": "yes" if all(c in real_sections for c in cited) else "NO",
            "search_found_right_section": (
                "n/a" if not_covered or not expected
                else "yes" if expected & set(found) else "NO"
            ),
            # For me to fill in
            "plain_ai_answer": "",
            "correct_plain_ai": "",
            "correct_my_app": "",
            "cited_real_section_my_app": "",
            "notes": "",
        })

    with RESULTS.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} results to {RESULTS.name}")
    print("Wrong answer + 'search_found_right_section' = NO  -> a search problem (Stage 3)")
    print("Wrong answer + 'search_found_right_section' = yes -> an answering problem (Stage 4)")


if __name__ == "__main__":
    main()

"""Iterate, part 3: a semantic entropy confidence score.

Idea: if the assistant really "knows" the answer from the law text, asking it
the same question several times gives answers that mean the same thing. If it
is unsure, the answers disagree. So:

  1. Generate 5 answers to the same question, from the same retrieved law
     sections, with random sampling at temperature 1.0. (This model only
     allows its default temperature, which is 1.0, so we leave it unset.)
  2. Group the answers into clusters of answers that mean the same thing:
     two answers go in the same cluster if an AI judge says each one entails
     the other (everything A says about the answer is implied by B, and the
     other way round). For long legal answers, "meaning" is the actual answer
     to the question: the conclusion and key legal facts (yes/no, numbers,
     deadlines, conditions), not wording, order or minor extra detail.
  3. Semantic entropy = -sum(p * ln p) over the clusters, where p is the
     share of answers in each cluster. 0 means all 5 agree; the maximum,
     ln 5 = 1.61, means all 5 disagree.

Confidence labels:
  high    - all 5 answers in one cluster (entropy 0)
  medium  - entropy up to 0.7 (e.g. a 4-1 split = 0.50, or 3-2 = 0.67)
  low     - entropy above 0.7 (e.g. 3-1-1 = 0.95, or more scattered)

Two clustering rules are scored from the same 5 samples:
  strict - each answer must entail the other (the original method). In
           testing, long answers got split just for including different
           details, even when they agreed.
  loose  - same conclusion and no contradiction: leaving a detail out is
           fine, but disagreeing on a yes/no, number, deadline or condition
           is not.

    python entropy.py "your question"     # run one question and show everything
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import math
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from answer import MODEL, SYSTEM_PROMPT, answer, format_sections

SAMPLES = 5
JUDGE_MODEL = "claude-haiku-5-5"  # the cheapest model, same as the assistant
MEDIUM_MAX = 0.7

ENTAILMENT_PROMPT = """You compare two answers that an Ontario law assistant gave to the same question.

Focus on the actual answer to the question: the conclusion and the key legal facts (yes or no, numbers, deadlines, amounts, who it applies to, main conditions and exceptions). Ignore wording, order, formatting, citation style, the disclaimer, and minor extra details that don't change the answer.

Decide two things:
A_ENTAILS_B: Does everything answer B says about the question follow from answer A? (yes/no)
B_ENTAILS_A: Does everything answer A says about the question follow from answer B? (yes/no)

Reply in exactly this format:
A_ENTAILS_B: <yes or no>
B_ENTAILS_A: <yes or no>
REASON: <one sentence>"""


SAME_CONCLUSION_PROMPT = """You compare two answers that an Ontario law assistant gave to the same question.

Decide whether they give the SAME ANSWER to the question:
- Same conclusion (for example both say yes, both say no, or both say it couldn't be found).
- No contradiction on any key legal fact: yes or no, numbers, deadlines, amounts, who it applies to, conditions and exceptions.

One answer leaving out a detail that the other includes is fine, as long as nothing contradicts. Ignore wording, order, formatting and citation style.

Reply in exactly this format:
SAME: <yes or no>
REASON: <one sentence>"""


def sample_answers(client, question, sections, n=SAMPLES):
    """Generate n answers from the same law sections, in parallel."""
    content = f"{format_sections(sections)}\n\nQuestion: {question}"

    def one(_):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},  # same settings as the assistant
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(one, range(n)))


def same_meaning(client, question, a, b):
    """True if the judge says A entails B and B entails A."""
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=2000,
        system=ENTAILMENT_PROMPT,
        messages=[{
            "role": "user",
            "content": f"QUESTION:\n{question}\n\nANSWER A:\n{a}\n\nANSWER B:\n{b}",
        }],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    ab = re.search(r"A_ENTAILS_B:\s*(yes|no)", text, re.I)
    ba = re.search(r"B_ENTAILS_A:\s*(yes|no)", text, re.I)
    reason = re.search(r"REASON:\s*(.+)", text)
    both = bool(ab and ba and ab.group(1).lower() == "yes" and ba.group(1).lower() == "yes")
    return both, reason.group(1).strip() if reason else text.strip()


def same_conclusion(client, question, a, b):
    """The loose rule: True if the judge says A and B give the same answer
    with no contradiction (omissions allowed)."""
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=2000,
        system=SAME_CONCLUSION_PROMPT,
        messages=[{
            "role": "user",
            "content": f"QUESTION:\n{question}\n\nANSWER A:\n{a}\n\nANSWER B:\n{b}",
        }],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    same = re.search(r"SAME:\s*(yes|no)", text, re.I)
    reason = re.search(r"REASON:\s*(.+)", text)
    return bool(same and same.group(1).lower() == "yes"), reason.group(1).strip() if reason else text.strip()


def cluster(client, question, answers, compare=same_meaning):
    """Put answers that mean the same thing together.

    Each new answer is compared (with the given rule) to the first answer of
    every existing cluster; it joins the first cluster it matches, or starts
    a new one. Returns (clusters as lists of answer numbers, comparison notes).
    """
    clusters, notes = [], []
    for i, ans in enumerate(answers):
        for members in clusters:
            match, reason = compare(client, question, answers[members[0]], ans)
            notes.append(f"answer {members[0] + 1} vs {i + 1}: {'SAME' if match else 'different'} - {reason}")
            if match:
                members.append(i)
                break
        else:
            clusters.append([i])
    return clusters, notes


def entropy_of(clusters, n):
    h = -sum((len(c) / n) * math.log(len(c) / n) for c in clusters)
    return max(0.0, h)  # avoid printing "-0.0" when all answers agree


def confidence_label(h, n_clusters):
    if n_clusters == 1:
        return "high"
    return "medium" if h <= MEDIUM_MAX else "low"


def score(client, question, answers):
    """Cluster the same samples with both rules and score each.

    Returns (summary columns, details per rule)."""
    summary, details = {}, {}
    for rule, compare in (("strict", same_meaning), ("loose", same_conclusion)):
        clusters, notes = cluster(client, question, answers, compare)
        h = entropy_of(clusters, len(answers))
        suffix = "" if rule == "strict" else "_loose"
        summary.update({
            f"entropy{suffix}": round(h, 3),
            f"n_clusters{suffix}": len(clusters),
            f"cluster_sizes{suffix}": "-".join(str(len(c)) for c in sorted(clusters, key=len, reverse=True)),
            f"confidence{suffix}": confidence_label(h, len(clusters)),
        })
        details[rule] = {"clusters": [[i + 1 for i in c] for c in clusters], "comparisons": notes}
    return summary, details


def semantic_entropy(client, question, sections):
    """Sample, cluster and score. Returns (summary columns, full details)."""
    answers = sample_answers(client, question, sections)
    summary, details = score(client, question, answers)
    return summary, {"samples": answers, **details}


def quick_confidence(client, question, sections):
    """The version used in the app's "How sure is this?" button: 5 samples,
    clustered with the loose rule only (fewer judge calls). Returns
    (label, entropy, cluster sizes like "4-1")."""
    answers = sample_answers(client, question, sections)
    clusters, _ = cluster(client, question, answers, same_conclusion)
    h = entropy_of(clusters, len(answers))
    sizes = "-".join(str(len(c)) for c in sorted(clusters, key=len, reverse=True))
    return confidence_label(h, len(clusters)), round(h, 2), sizes


def print_report(summary, details, show_answers=True):
    if show_answers:
        for i, a in enumerate(details["samples"], 1):
            print(f"\n--- Sample {i} ---\n{a}")
    for rule in ("strict", "loose"):
        suffix = "" if rule == "strict" else "_loose"
        print(f"\n[{rule.upper()} rule] comparisons:")
        for note in details[rule]["comparisons"]:
            print(f"  {note}")
        print("  Clusters (answer numbers):",
              "  ".join("{" + ", ".join(map(str, c)) + "}" for c in details[rule]["clusters"]))
        print(f"  Semantic entropy: {summary['entropy' + suffix]} (0 = all agree, max {math.log(SAMPLES):.2f})"
              f"  ->  confidence: {summary['confidence' + suffix].upper()}")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    if not question:
        print(__doc__)
        sys.exit()
    load_dotenv(".env")
    client = anthropic.Anthropic()
    result = answer(question)
    print(f"Q: {question}\n\nMain answer:\n{result['answer']}")
    print_report(*semantic_entropy(client, question, result["sections"]))

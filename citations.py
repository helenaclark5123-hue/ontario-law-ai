"""Iterate, part 2: check every law section an answer cites.

For each answer:
  1. Find every citation, like "(Residential Tenancies Act, 2006, s. 116(1))"
     or the short form "(s. 116(3))". A short citation belongs to the Act
     most recently named before it.
  2. Look the section up in the law database (data/). If it isn't there,
     the citation is "not_found".
  3. For sections that exist, an AI judge reads the real section text and the
     sentence(s) where the answer cites it, and decides whether the text
     supports what the answer says: "verified" or "unsupported".

An answer is flagged if any citation is unsupported or not_found.

    python citations.py --demo     # check a made-up answer with planted mistakes
    python citations.py --recheck results/eval_..._full-checks.json
                                   # re-check the saved answers of an earlier run
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import re
import sys

import anthropic
from dotenv import load_dotenv

from search import saved_sections

# The cheapest model, same one the assistant uses.
JUDGE_MODEL = "claude-haiku-5-5"
MAX_SECTION_CHARS = 6000

LAWS = [
    "Residential Tenancies Act, 2006",
    "Employment Standards Act, 2000",
    "Consumer Protection Act, 2002",
]
LAW_NAME = re.compile("|".join(re.escape(name) for name in LAWS))
# "s. 116(1)", "ss. 22-23", "section 106": group 1 is the number(s) after it.
CITATION = re.compile(
    r"\b(?:ss?\.|sections?)\s*"
    r"(\d+(?:\.\d+)*(?:\([^)\s]*\))*(?:\s*(?:,|and|to|-|–)\s*\d+(?:\.\d+)*(?:\([^)\s]*\))*)*)"
)
SECTION_NUMBER = re.compile(r"(?<![(\w.])(\d+(?:\.\d+)*)")

JUDGE_PROMPT = """You check citations in answers from an Ontario law assistant.

For each numbered citation you get the claim(s) the answer makes while citing it, the official text of the cited section, and whether the assistant was GIVEN that section when it wrote the answer. Decide whether the claim is supported:

verified - The section text says what the claim says (wording can differ).
unsupported - The section text does not say it, says something different, or says the opposite. Also use this if the claim gets a number, deadline, amount or condition wrong.

Rules:
- Judge only from the section text given. Do NOT use your own memory of Ontario law.
- If a claim also cites other sections, only judge the part this section could support; don't mark it unsupported just because part of the claim comes from another cited section.
- The assistant only sees some sections. If the claim just says the assistant doesn't have this section, couldn't find it, or can't say what it requires, and the assistant was NOT given it, that statement is true: mark it verified. Only judge the legal content of the claim.
- Long sections are shown as excerpts (the parts most related to the claim), with [...] for skipped parts.

Reply with one line per citation, in exactly this format:
[1] verified - <short reason>
[2] unsupported - <short reason>"""


def split_claims(text):
    """Split an answer into sentences/bullet points, keeping their positions."""
    units = []
    for line in re.finditer(r"[^\n]+", text):
        start = line.start()
        for piece in re.split(r"(?<=[.!?])\s+(?=[A-Z*(])", line.group(0)):
            offset = text.find(piece, start)
            units.append((offset, offset + len(piece), piece.strip(" -*")))
            start = offset + len(piece)
    return units


def extract_citations(text, default_law=None):
    """Find every cited (law, section) and the claims made with it.

    Returns a list of dicts: law, section, cited_as (as written), claims.
    """
    law_mentions = [(m.start(), m.group(0)) for m in LAW_NAME.finditer(text)]
    units = split_claims(text)
    found = {}
    for m in CITATION.finditer(text):
        before = [name for pos, name in law_mentions if pos < m.start()]
        law = before[-1] if before else default_law or "unknown law"
        claim = next((u[2] for u in units if u[0] <= m.start() < u[1]), "")
        for number in SECTION_NUMBER.findall(m.group(1)):
            entry = found.setdefault((law, number), {
                "law": law, "section": number, "cited_as": [], "claims": [],
            })
            entry["cited_as"].append(m.group(0))
            if claim and claim not in entry["claims"]:
                entry["claims"].append(claim)
    return list(found.values())


def relevant_text(text, claims):
    """The section text to show the judge.

    Short sections are shown whole. For long ones (like ESA s. 1, the
    13,000-character definitions section), the parts most similar in meaning
    to the claims are kept, in their original order, up to MAX_SECTION_CHARS.
    """
    if len(text) <= MAX_SECTION_CHARS:
        return text
    from make_chunks import split_long
    from search import embed

    parts = split_long(text)
    vectors = embed(parts + [" ".join(claims)])
    claim_vector = vectors[-1]
    similarity = [sum(a * b for a, b in zip(v, claim_vector)) for v in vectors[:-1]]
    keep, size = set(), 0
    for i in sorted(range(len(parts)), key=lambda i: similarity[i], reverse=True):
        if keep and size + len(parts[i]) > MAX_SECTION_CHARS:
            continue
        keep.add(i)
        size += len(parts[i])
    pieces, previous = [], -1
    for i in sorted(keep):
        if i != previous + 1:
            pieces.append("[...]")
        pieces.append(parts[i])
        previous = i
    if previous != len(parts) - 1:
        pieces.append("[...]")
    return "\n".join(pieces)


def judge_support(client, citations):
    """Ask the judge whether each section's text supports its claims."""
    sections = saved_sections()
    blocks = []
    for i, c in enumerate(citations, 1):
        claims = "\n".join(f"- {claim}" for claim in c["claims"])
        text = relevant_text(sections[(c["law"], c["section"])], c["claims"])
        given = "yes" if c["given"] else "NO"
        blocks.append(
            f"[{i}] {c['law']}, s. {c['section']}\n"
            f"WAS THE ASSISTANT GIVEN THIS SECTION? {given}\n"
            f"CLAIM(S) IN THE ANSWER:\n{claims}\n"
            f"OFFICIAL SECTION TEXT:\n{text}"
        )
    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=4000,
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": "\n\n".join(blocks)}],
    )
    reply = "".join(b.text for b in response.content if b.type == "text")
    for i, c in enumerate(citations, 1):
        m = re.search(rf"\[{i}\]\s*(verified|unsupported)\s*[-–:]?\s*(.*)", reply, re.I)
        c["status"] = m.group(1).lower() if m else "unclear"
        c["reason"] = m.group(2).strip() if m else "(judge didn't answer for this one)"


def check_citations(client, answer_text, sections_used=()):
    """Check every citation in an answer. Returns (citations, summary)."""
    laws_used = {s["law"] for s in sections_used}
    default_law = laws_used.pop() if len(laws_used) == 1 else None
    citations = extract_citations(answer_text, default_law)

    sections = saved_sections()
    given = {(s["law"], s["section"]) for s in sections_used}
    to_judge = []
    for c in citations:
        c["given"] = (c["law"], c["section"]) in given
        if (c["law"], c["section"]) in sections:
            to_judge.append(c)
        else:
            c["status"] = "not_found"
            c["reason"] = "this section isn't in the law database"
    if to_judge:
        judge_support(client, to_judge)

    count = {s: sum(c["status"] == s for c in citations) for s in ("verified", "unsupported", "not_found", "unclear")}
    summary = {
        "citations_total": len(citations),
        "citations_verified": count["verified"],
        "citations_unsupported": count["unsupported"],
        "citations_not_found": count["not_found"],
        "citation_flag": "FLAG" if count["unsupported"] or count["not_found"] else "ok",
        "citation_details": "\n".join(
            f"{c['status'].upper()}: {c['law']}, s. {c['section']} - {c['reason']}" for c in citations
        ),
    }
    return citations, summary


def print_report(citations, summary):
    for c in citations:
        print(f"  {c['status'].upper():<12} {c['law']}, s. {c['section']}   (cited as: {', '.join(dict.fromkeys(c['cited_as']))})")
        for claim in c["claims"]:
            print(f"               claim: {claim[:160]}")
        print(f"               why:   {c['reason']}")
    print(f"  -> {summary['citations_total']} citations: {summary['citations_verified']} verified, "
          f"{summary['citations_unsupported']} unsupported, {summary['citations_not_found']} not found  "
          f"=> {summary['citation_flag']}")


# A made-up answer with two planted mistakes, to show the checker catches them:
# s. 116 really says 90 days (not 30), and the RTA has no section 999.
DEMO_ANSWER = """Your landlord must give you at least 30 days' written notice before raising your rent (Residential Tenancies Act, 2006, s. 116(1)). Rent can only go up once every 12 months (s. 119(1)). Tenants can also get a rent rebate for any month the landlord is late with repairs (s. 999).

This is legal information, not legal advice."""


def recheck(path, match=(), label="citations-rechecked"):
    """Re-run only the citation checker on the answers saved in a results
    file. Grades, entropy scores and everything else are kept as they were,
    so the old and new citation results can be compared fairly."""
    import json
    from datetime import datetime
    from pathlib import Path

    rows = json.loads(Path(path).read_text())
    if match:
        rows = [r for r in rows if r["question"].startswith(tuple(match))]
    client = anthropic.Anthropic()
    for i, r in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {r['question']}", flush=True)
        before = r.get("citation_flag", "-")
        found, summary = check_citations(client, r["assistant_answer"], r["_sections"])
        r.update(summary)
        r["_citations"] = found
        print(f"         citations: {before} -> {r['citation_flag']}  ({r['grade']})", flush=True)
        for c in found:
            if c["status"] != "verified":
                print(f"           {c['status'].upper()}: {c['law']}, s. {c['section']} - {c['reason']}")

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = Path(path).parent / f"eval_{stamp}_{label}.json"
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"\nSaved: {out}")
    return out


if __name__ == "__main__":
    load_dotenv(".env")
    if "--demo" in sys.argv:
        print("Demo answer (planted mistakes: 30 days, and s. 999):\n")
        print(DEMO_ANSWER, "\n")
        print_report(*check_citations(anthropic.Anthropic(), DEMO_ANSWER))
    elif "--recheck" in sys.argv:
        # python citations.py --recheck results/x.json [--label NAME] [question starts...]
        args = sys.argv[sys.argv.index("--recheck") + 1:]
        label = "citations-rechecked"
        if "--label" in args:
            label = args[args.index("--label") + 1]
            args = args[:args.index("--label")] + args[args.index("--label") + 2:]
        recheck(args[0], args[1:], label)
    else:
        print(__doc__)

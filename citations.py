"""Iterate, part 2: check every law section an answer cites.

For each answer:
  1. Find every citation, like "(Residential Tenancies Act, 2006, s. 116(1))"
     or the short form "(s. 116(3))". A short citation belongs to the Act
     most recently named before it. Section numbers of other Acts (e.g.
     "Fighting Delays, Building Faster Act, 2025, s. 2(2)") are skipped.
  2. Look the section up in the law database (data/). If it isn't there,
     the citation is "not_found".
  3. For sections that exist, an AI judge reads the real section text and
     each sentence that cites it, together with that sentence's paragraph and
     heading, reasons first, then decides "verified" or "unsupported". The
     judge is asked 3 times:
       verified    - all 3 say supported
       unsupported - most say unsupported
       disputed    - most say supported, but at least one objects (a warning)

An answer is flagged if any citation is unsupported or not_found. "Disputed"
is recorded but doesn't flag: it caught more real errors in testing, but
added about 4 false alarms per run.

    python citations.py --demo     # check a made-up answer with planted mistakes
    python citations.py --recheck results/eval_..._full-checks.json
                                   # re-check the saved answers of an earlier run
    python citations.py --recheck results/x.json --model claude-sonnet-5-5
                                   # ...with a stronger (more expensive) judge
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from search import saved_sections

# The cheapest model, same one the assistant uses.
JUDGE_MODEL = "claude-haiku-5-5"
MAX_SECTION_CHARS = 6000
# How many times the judge is asked; the majority verdict wins.
VOTES = 3

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
# The name of any Act, e.g. "Fighting Delays, Building Faster Act, 2025".
OTHER_ACT = re.compile(r"((?:[A-Z][\w'’-]*,?\s+){1,8}Act(?:,\s*\d{4})?)")

JUDGE_PROMPT = """You check citations in answers from an Ontario law assistant.

For each numbered citation you get the claim(s) the answer makes while citing it, each with its CONTEXT (the paragraph and heading it appears under, so you know who "you" is and what the sentence is about), the official text of the cited section, and whether the assistant was GIVEN that section when it wrote the answer. Decide whether the claim, read in its context, is supported:

verified - The section text says what the claim says (wording can differ).
unsupported - The section text does not say it, says something different, or says the opposite. Also use this if the claim gets a number, deadline, amount or condition wrong.

Rules:
- Judge only from the section text given. Do NOT use your own memory of Ontario law.
- If a claim also cites other sections, only judge the part this section could support; don't mark it unsupported just because part of the claim comes from another cited section.
- The assistant only sees some sections. If the claim just says the assistant doesn't have this section, couldn't find it, or can't say what it requires, and the assistant was NOT given it, that statement is true: mark it verified. Only judge the legal content of the claim.
- Long sections are shown as excerpts (the parts most related to the claim), with [...] for skipped parts.

For each citation, reason FIRST, then give your verdict on its own line. Use exactly this format:
[1] REASON: <one to three sentences comparing the claim with the section text>
VERDICT: <verified or unsupported>
[2] REASON: <...>
VERDICT: <...>"""


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


def is_heading(line):
    """A markdown heading, a fully bold line, or a short line ending in ':'."""
    line = line.strip(" -")
    return (
        line.startswith("#")
        or (line.startswith("**") and line.endswith(("**", "**:", ":**")))
        or (line.endswith(":") and len(line) < 100)
    )


def context_for(text, pos, limit=700):
    """The paragraph or bullet point containing pos, with the nearest heading
    above it, so the judge knows what a sentence like "You must give 10 days'
    notice" is about (e.g. under "Can you leave earlier?")."""
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    line = text[line_start: line_end if line_end != -1 else len(text)].strip()
    heading = next((l.strip() for l in reversed(text[:line_start].split("\n")) if is_heading(l)), "")
    return (f"{heading}\n{line}" if heading and heading != line else line)[:limit]


def other_act_mentions(text):
    """Positions of Acts other than our three, e.g. 'Fighting Delays, Building
    Faster Act, 2025', so their section numbers aren't mistaken for ours."""
    generic = ("The", "This", "That", "Each", "Under", "In", "By")
    found = []
    for m in OTHER_ACT.finditer(text):
        name = m.group(1).strip()
        words = name.split()
        while words and words[0] in generic:  # "The Fighting Delays ... Act" -> keep the name
            words.pop(0)
        if LAW_NAME.search(name) or len(words) < 2:  # one of our laws, or just "the Act"
            continue
        found.append(m.start())
    return found


def extract_citations(text, default_law=None):
    """Find every cited (law, section) and the claims made with it.

    Returns a list of dicts: law, section, cited_as (as written), claims, and
    contexts (each claim's paragraph and heading). Section numbers that follow
    the name of a different Act on the same line are skipped.
    """
    law_mentions = [(m.start(), m.group(0)) for m in LAW_NAME.finditer(text)]
    others = other_act_mentions(text)
    units = split_claims(text)
    found = {}
    for m in CITATION.finditer(text):
        before = [(pos, name) for pos, name in law_mentions if pos < m.start()]
        law = before[-1][1] if before else default_law or "unknown law"
        # Skip citations that belong to another Act: its name comes after ours and
        # in the same phrase, e.g. "(Fighting Delays ... Act, 2025, Schedule 12, s. 2(2))".
        last_ours = before[-1][0] if before else -1
        if any(
            last_ours < pos < m.start() and m.start() - pos < 150
            and not re.search(r"\)|\.\s|\n", text[pos:m.start()])
            for pos in others
        ):
            continue
        claim = next((u[2] for u in units if u[0] <= m.start() < u[1]), "")
        for number in SECTION_NUMBER.findall(m.group(1)):
            entry = found.setdefault((law, number), {
                "law": law, "section": number, "cited_as": [], "claims": [], "contexts": [],
            })
            entry["cited_as"].append(m.group(0))
            if claim and claim not in entry["claims"]:
                entry["claims"].append(claim)
                entry["contexts"].append(context_for(text, m.start()))
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


def judge_support(client, citations, model=JUDGE_MODEL):
    """Ask the judge whether each section's text supports its claims."""
    sections = saved_sections()
    blocks = []
    for i, c in enumerate(citations, 1):
        contexts = c.get("contexts") or [""] * len(c["claims"])
        claims = "\n".join(
            f"- CLAIM: {claim}" + (f"\n  CONTEXT: {context}" if context and context != claim else "")
            for claim, context in zip(c["claims"], contexts)
        )
        text = relevant_text(sections[(c["law"], c["section"])], c["claims"])
        given = "yes" if c["given"] else "NO"
        blocks.append(
            f"[{i}] {c['law']}, s. {c['section']}\n"
            f"WAS THE ASSISTANT GIVEN THIS SECTION? {given}\n"
            f"CLAIM(S) IN THE ANSWER:\n{claims}\n"
            f"OFFICIAL SECTION TEXT:\n{text}"
        )
    content = "\n\n".join(blocks)

    def one_vote(_):
        response = client.messages.create(
            model=model,
            max_tokens=8000,
            output_config={"effort": "medium"},
            system=JUDGE_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        reply = "".join(b.text for b in response.content if b.type == "text")
        # Each block runs from "[i]" to the next "[i+1]"; the verdict comes last.
        votes = []
        for i in range(1, len(citations) + 1):
            block = re.search(rf"\[{i}\](.*?)(?=\[{i + 1}\]|\Z)", reply, re.S)
            body = block.group(1) if block else ""
            verdict = re.findall(r"VERDICT:\s*\**\s*(verified|unsupported)", body, re.I)
            reason = re.search(r"REASON:\s*(.*?)(?=VERDICT:|\Z)", body, re.S | re.I)
            votes.append((
                verdict[-1].lower() if verdict else "unclear",
                reason.group(1).strip() if reason else body.strip(),
            ))
        return votes

    # Ask the same judge VOTES times at once and keep the majority verdict,
    # because a single judge can read a subtle section differently each time.
    with ThreadPoolExecutor(max_workers=VOTES) as pool:
        ballots = list(pool.map(one_vote, range(VOTES)))
    for i, c in enumerate(citations):
        votes = [ballot[i] for ballot in ballots]
        counts = Counter(status for status, _ in votes if status != "unclear")
        verified, unsupported = counts["verified"], counts["unsupported"]
        # A citation only passes if every judge agrees it's supported. In testing,
        # subtle real errors (RTA s. 120, s. 83) got 2-1 votes, while false alarms
        # went 3-0 "verified" once judges saw the claim's context.
        if unsupported == 0 and verified > 0:
            c["status"] = "verified"
        elif unsupported > verified:
            c["status"] = "unsupported"
        elif unsupported:
            c["status"] = "disputed"
        else:
            c["status"] = "unclear"
        c["votes"] = f"{verified} verified / {unsupported} unsupported"
        reasons = [reason for status, reason in votes if status == c["status"] and reason]
        c["reason"] = (reasons[0] if reasons else "(judges split)") + f"  [votes: {c['votes']}]"


def check_citations(client, answer_text, sections_used=(), model=JUDGE_MODEL):
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
        judge_support(client, to_judge, model)

    count = {
        s: sum(c["status"] == s for c in citations)
        for s in ("verified", "unsupported", "disputed", "not_found", "unclear")
    }
    summary = {
        "citations_total": len(citations),
        "citations_verified": count["verified"],
        "citations_unsupported": count["unsupported"],
        "citations_disputed": count["disputed"],
        "citations_not_found": count["not_found"],
        # "disputed" is recorded but doesn't flag: in testing, single judges
        # objected at random often enough to add ~4 false alarms per run.
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


def recheck(path, match=(), label="citations-rechecked", model=JUDGE_MODEL):
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
        found, summary = check_citations(client, r["assistant_answer"], r["_sections"], model)
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
        # python citations.py --recheck results/x.json [--label NAME] [--model ID] [question starts...]
        args = sys.argv[sys.argv.index("--recheck") + 1:]
        options = {"--label": "citations-rechecked", "--model": JUDGE_MODEL}
        for flag in options:
            if flag in args:
                options[flag] = args[args.index(flag) + 1]
                args = args[:args.index(flag)] + args[args.index(flag) + 2:]
        recheck(args[0], args[1:], options["--label"], options["--model"])
    else:
        print(__doc__)

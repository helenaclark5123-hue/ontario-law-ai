"""Re-ranking: let the AI choose which law sections to read.

Search by meaning (search.py) is good at finding *roughly* related sections,
but the exact top 8 shifts with small changes in wording, so a key section
(like the stunt-driving definition for "50 km/h over") can fall just outside.

So instead of taking the top 8 by score:
  1. Gather a wider pool of candidate sections (about 30) from all the
     search queries (the person's words and the legal-terms rewrite).
  2. Show Claude Haiku the question and a short preview of each candidate,
     and ask it to pick the sections needed to answer correctly and
     completely: the main rule, key definitions, exceptions, penalties, and
     regulations that set the actual numbers.
  3. Return those sections in full (search.expand), as before.

If the AI's reply can't be read, the pool's best-scoring sections are used.
"""

import re

from search import expand, search

MODEL = "claude-haiku-5-5"
PER_QUERY = 25  # distinct sections taken from each query's results (about 40 candidates in all)
PREVIEW_CHARS = 500

RERANK_PROMPT = """You help an Ontario law assistant decide which law sections to read before answering a question.

You get the question and numbered candidate sections, each with a short preview. Choose the sections needed to answer the question correctly and completely: the main rule, the definitions it depends on, important exceptions and conditions, penalties or consequences, and any regulation that sets the actual numbers, lists or details. Prefer sections that directly answer the question over ones that are only loosely related.

Each candidate has a label like C1, C2, C3. Reply with the labels of up to {k} candidates, most important first, separated by commas, for example: C4, C1, C12. Use the C labels, not the law's section numbers. Reply with the labels only."""


def candidates(queries, per_query=PER_QUERY):
    """A pool of distinct sections from all queries, best-scoring first.

    Returns (pool, matched): pool is a list of the best-matching chunk for
    each section; matched maps each section to its matching parts' scores
    (needed to expand long sections).
    """
    best, matched = {}, {}
    for query in queries:
        taken = []
        for hit in search(query, per_query * 4):
            key = (hit["law"], hit["section"])
            parts = matched.setdefault(key, {})
            parts[hit["part"]] = max(parts.get(hit["part"], 0), hit["score"])
            if key not in best or hit["score"] > best[key]["score"]:
                best[key] = hit
            if key not in taken:
                taken.append(key)
            if len(taken) >= per_query:
                break
    pool = sorted(best.values(), key=lambda h: h["score"], reverse=True)
    return pool, matched


def rerank_retrieve(client, question, queries, k=8):
    """Return the k sections the AI judges most useful for the question."""
    pool, matched = candidates(queries)
    listing = "\n\n".join(
        f"C{i}: {hit['text'][:PREVIEW_CHARS]}" for i, hit in enumerate(pool, 1)
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        output_config={"effort": "low"},
        system=RERANK_PROMPT.format(k=k),
        messages=[{"role": "user", "content": f"QUESTION: {question}\n\nCANDIDATE SECTIONS:\n\n{listing}"}],
    )
    reply = "".join(b.text for b in response.content if b.type == "text")

    chosen = []
    # Only "C<number>" labels count, so a law section number in the reply
    # (e.g. "s. 24") can't be mistaken for candidate 24.
    for number in re.findall(r"\bC(\d+)\b", reply):
        i = int(number) - 1
        if 0 <= i < len(pool) and pool[i] not in chosen:
            chosen.append(pool[i])
        if len(chosen) == k:
            break
    # Top up from the best-scoring sections if the AI picked fewer than k.
    for hit in pool:
        if len(chosen) >= k:
            break
        if hit not in chosen:
            chosen.append(hit)
    return [expand(h, matched[(h["law"], h["section"])]) for h in chosen]

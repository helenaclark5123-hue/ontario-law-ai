"""Stage 4: Answer a question using only the retrieved Ontario law sections.

This is the RAG step: rewrite the question into legal terms, retrieve the 8
most relevant sections using both versions (Stage 3), send them to Claude with
strict rules, and return the answer plus the sections used.

    python answer.py "your question"
"""

import os
import sys

import anthropic
from dotenv import load_dotenv

from search import retrieve

load_dotenv()  # reads ANTHROPIC_API_KEY from the .env file

MODEL = "claude-haiku-5-5"
NOT_FOUND = "I couldn't find this in the laws I have."
DISCLAIMER = (
    "This is legal information, not legal advice. For advice about your "
    "situation, contact a lawyer, paralegal or community legal clinic."
)

# The exact instructions the model gets with every question.
SYSTEM_PROMPT = f"""You answer questions about Ontario law for members of the public.

You will be given numbered law sections inside <sections> tags, then a question. Follow these rules:

1. Answer ONLY using the provided law sections. Do not use anything you know about the law from memory, even if you think it is correct. If a detail (a number of days, an amount, an exception) is not in the sections, do not state it.
2. Cite the law name and section number for every claim, in the form (Residential Tenancies Act, 2006, s. 116). If a sentence makes a claim, it needs a citation.
3. If the sections do not answer the question, reply with exactly: "{NOT_FOUND}" You may add one sentence saying what kind of law or help might cover it, but do not answer the question itself. If the sections only partly answer it, answer that part and clearly say what you could not find.
4. End every reply with this note on its own line: "{DISCLAIMER}"

Write in plain language a non-lawyer can follow. Keep answers short: a direct answer first, then the key conditions or exceptions."""

# Instructions for rewriting a question before searching. The rewrite is only
# used to search; the answer still comes only from the retrieved sections.
REWRITE_PROMPT = """You turn everyday questions about Ontario law into search queries for a database of three statutes: the Residential Tenancies Act, 2006, the Employment Standards Act, 2000, and the Consumer Protection Act, 2002.

Rewrite the question using the words these statutes themselves would use. For example, "door-to-door sale" becomes "direct agreement", "damage deposit" becomes "security deposit", "fired" becomes "termination of employment", and "pay" becomes "wages".

Use legal terms only. Do not add section numbers, amounts, time periods or anything else that would answer the question, because the answer must come from the law text that the search finds.

Reply with only the rewritten query on one line. Do not answer the question or explain."""

class MissingKeyError(Exception):
    """Raised when there is no API key in the .env file."""


def format_sections(chunks):
    """Put the retrieved sections into the message, one numbered block each."""
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(
            f'<section number="{i}" law="{c["law"]}" section="{c["section"]}" url="{c["url"]}">\n'
            f"{c['text']}\n</section>"
        )
    return "<sections>\n" + "\n\n".join(blocks) + "\n</sections>"


def rewrite_question(client, question):
    """Ask Claude to restate the question in the statutes' own legal terms."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        output_config={"effort": "low"},
        system=REWRITE_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text.splitlines()[0].strip() if text else ""


def answer(question, k=8):
    """Rewrite the question, retrieve the top k sections, and ask Claude to
    answer from them only.

    Returns a dict with the answer text, the rewritten search, and the
    sections that were used.
    """
    load_dotenv(override=True)  # re-read .env, so a newly pasted key works without a restart
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise MissingKeyError("There's no API key in the .env file yet.")

    client = anthropic.Anthropic()
    rewrite = rewrite_question(client, question)
    # Search with both the person's own words and the legal-terms version.
    chunks = retrieve([question, rewrite] if rewrite else [question], k)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},  # simple Q&A: keep it quick and cheap
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"{format_sections(chunks)}\n\nQuestion: {question}",
        }],
    )

    if response.stop_reason == "refusal":
        text = f"{NOT_FOUND}\n\n{DISCLAIMER}"
    else:
        text = "".join(b.text for b in response.content if b.type == "text").strip()

    return {"question": question, "rewrite": rewrite, "answer": text, "sections": chunks}


def main():
    question = " ".join(sys.argv[1:])
    if not question:
        print(__doc__)
        return

    try:
        result = answer(question)
    except MissingKeyError:
        print("No API key yet: paste your key after ANTHROPIC_API_KEY= in the .env file and save it.")
        return
    except anthropic.AuthenticationError:
        print("API key problem: check that your key is pasted correctly in the .env file.")
        return
    except anthropic.PermissionDeniedError:
        print("Your API key isn't allowed to do this. Check your Console account and billing.")
        return
    except anthropic.BadRequestError as e:
        print(f"The request was rejected: {e.message}")
        print("If this mentions credit or billing, add credit at console.anthropic.com.")
        return
    except anthropic.APIConnectionError:
        print("Couldn't reach Anthropic. Check your internet connection.")
        return

    print(f"\nQ: {question}")
    print(f"Searched for: {result['rewrite']}\n")
    print(result["answer"])
    print("\nSections retrieved:")
    for c in result["sections"]:
        print(f"  - {c['law']}, s. {c['section']} – {c['heading']}  ({c['url']})")


if __name__ == "__main__":
    main()

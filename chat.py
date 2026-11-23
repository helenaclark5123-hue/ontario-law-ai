"""A chat version of the assistant: people describe their problem in their
own words, and can reply with more details.

Each turn:
  1. If there is earlier conversation, rewrite the newest message into one
     self-contained question ("he says his daughter is moving in" ->
     "My landlord wants to evict me because his daughter is moving in...").
  2. Search the laws exactly like answer.py: rewrite into legal terms, then
     let the AI pick the 8 most useful whole sections from a wider pool
     (rerank.py).
  3. Answer with the same strict rules as answer.py (only from the sections,
     cite everything, disclaimer), plus: if the answer depends on a fact the
     person hasn't given, explain the likely cases and ask one short
     follow-up question.

answer.py is unchanged; the evaluation still tests it directly.
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import anthropic
from dotenv import load_dotenv

from answer import MODEL, NOT_FOUND, DISCLAIMER, SYSTEM_PROMPT, MissingKeyError, format_sections, rewrite_question
from rerank import rerank_retrieve

# How many earlier messages to send with each turn (keeps costs down).
HISTORY_MESSAGES = 8

CHAT_PROMPT = SYSTEM_PROMPT + """

This is a conversation. The person may describe their situation in everyday words rather than ask a legal question. Work out which of the provided law sections apply to their situation and explain what those sections mean for them. Use the earlier messages for context, but the law sections in the newest message are the only source for legal statements.

If the answer depends on a fact the person hasn't told you (for example, the reason the landlord gave, or how long they've worked there), briefly explain what the law says for the most likely cases, then end with one short follow-up question, placed just before the disclaimer. Ask it in everyday words that someone with no legal knowledge can answer (for example "Did your landlord give you anything in writing?", not "Was the notice given under section 48?")."""

STANDALONE_PROMPT = """You help a legal search system understand a conversation about Ontario law.

Given the conversation so far and the person's newest message, write ONE self-contained question that captures the person's situation and what they want to know now, including the relevant facts from earlier messages. Write it from the person's point of view, in plain words.

Only use facts the person actually said. Do not assume or add details they didn't give (like whether they got a written notice), and don't add facts from the assistant's replies.

Reply with only the question."""


FLAGS_PROMPT = """You check messages sent to an Ontario legal information service, to decide whether to show a box pointing the person to a lawyer or to emergency help. Based only on what the person wrote, answer each with true or false:

- "danger": the person (or a child or someone else) seems to be in immediate danger or at risk of harm right now, e.g. violence at home, threats, thoughts of self-harm.
- "criminal": the person has been charged with, arrested for, or is being investigated for a criminal offence (not a traffic ticket or other provincial offence).
- "immigration": the question involves immigration, refugee claims, deportation, visas, work or study permits, or citizenship.
- "court_date": the person says they already have a court date, trial or tribunal hearing scheduled.

Reply with only JSON, like {"danger": false, "criminal": false, "immigration": false, "court_date": false}."""

FLAG_NAMES = ("danger", "criminal", "immigration", "court_date")


def check_flags(client, question):
    """Spot situations where the person should be pointed to a professional
    (or to 911). Returns a dict of True/False; all False if the check fails."""
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            output_config={"effort": "low"},
            system=FLAGS_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
        text = "".join(b.text for b in response.content if b.type == "text")
        data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        return {name: data.get(name) is True for name in FLAG_NAMES}
    except (anthropic.AnthropicError, AttributeError, ValueError):
        return {name: False for name in FLAG_NAMES}


def standalone_question(client, history, message):
    """Turn a follow-up like 'he says his daughter is moving in' into a full
    question, using the earlier conversation. First messages are used as is."""
    if not history:
        return message
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-HISTORY_MESSAGES:])
    response = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=1000,
        output_config={"effort": "low"},
        system=STANDALONE_PROMPT,
        messages=[{"role": "user", "content": f"CONVERSATION:\n{transcript}\n\nNEWEST MESSAGE:\n{message}"}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return text or message


def chat_turn(history, message, k=8):
    """Answer the newest message in a conversation.

    history is a list of {"role": "user" | "assistant", "content": text}.
    Returns a dict with the reply, the search question used, and the sections.
    """
    load_dotenv(override=True)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise MissingKeyError("There's no API key in the .env file yet.")
    client = anthropic.Anthropic()

    question = standalone_question(client, history, message)
    with ThreadPoolExecutor(max_workers=2) as pool:  # both at once, so it isn't slower
        flags = pool.submit(check_flags, client, question)
        rewrite = rewrite_question(client, question)
        flags = flags.result()
    sections = rerank_retrieve(client, question, [question, rewrite] if rewrite else [question], k)

    messages = [{"role": m["role"], "content": m["content"]} for m in history[-HISTORY_MESSAGES:]]
    messages.append({
        "role": "user",
        "content": f"{format_sections(sections)}\n\n{message}",
    })
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},
        system=CHAT_PROMPT,
        messages=messages,
    )
    if response.stop_reason == "refusal":
        text = f"{NOT_FOUND}\n\n{DISCLAIMER}"
    else:
        text = "".join(b.text for b in response.content if b.type == "text").strip()
    return {"reply": text, "question": question, "rewrite": rewrite, "sections": sections, "flags": flags}

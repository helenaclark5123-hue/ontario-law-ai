"""The chat assistant: people describe their situation and get cited answers."""

import html
import json
from datetime import datetime
from pathlib import Path

import anthropic
import streamlit as st

from answer import MissingKeyError
from chat import chat_turn
from citations import extract_citations
from search import retrieve
from summary import build_summary, make_pdf
from ui import GROUPS, LAWS, current_lookup, footer, law_dates, safe

# A narrower column reads better for a conversation.
st.markdown(
    "<style>.block-container, [data-testid='stBottomBlockContainer'] { max-width: 840px; }</style>",
    unsafe_allow_html=True,
)

# Topic groups for the welcome message, e.g. "housing", "work", "money".
TOPICS = [group.lower() for group in GROUPS]

SUGGESTIONS = [
    "My landlord is trying to kick me out",
    "Can my boss make me work 13 hours?",
    "Can I refuse a job I think is unsafe?",
    "What happens if I'm caught speeding?",
    "I hurt myself at work. Can I get paid while I recover?",
    "My landlord won't rent to me because I have kids",
]


def section_title(law, number, info):
    return f"{law}, s. {number}" + (f" — {info['heading']}" if info["heading"] else "")


def show_laws(message, lookup):
    """A "Laws used" drop-down under a reply: the full text of every section
    the reply cites, then the other sections that were searched."""
    cited = [
        (c["law"], c["section"]) for c in extract_citations(message["content"], None)
        if (c["law"], c["section"]) in lookup
    ]
    searched = [(s["law"], s["section"]) for s in message["sections"]]
    others = [s for s in dict.fromkeys(searched) if s not in cited]
    label = f"Laws used ({len(cited)})" if cited else f"Law sections found ({len(others)})"
    with st.expander(label, icon=":material/gavel:"):
        for law, number in cited:
            info = lookup[(law, number)]
            st.markdown(f'<div class="law-title">{html.escape(section_title(law, number, info))}</div>',
                        unsafe_allow_html=True)
            st.markdown(safe(info["text"]).replace("\n", "  \n"))
            st.caption(f"Official version: [{info['url']}]({info['url']}) (find section {number})")
        if others:
            st.caption("Also searched: " + "; ".join(
                f"{law.split(',')[0]} s. {n}" for law, n in others
            ))


def reply_to(message):
    """Get the assistant's reply to a new message, given the conversation so far."""
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state["messages"] if not m.get("error")
    ]
    try:
        result = chat_turn(history, message)
        return {"role": "assistant", "content": result["reply"], "sections": result["sections"],
                "searched": result["question"] if history else ""}
    except MissingKeyError:
        error = ("The AI answer isn't available yet: no API key is set "
                 "(.env on my computer, or the app's Secrets settings online).")
    except anthropic.AuthenticationError:
        error = ("The AI answer isn't available: the API key isn't working. Check it was pasted "
                 "correctly (.env on my computer, or the app's Secrets settings online).")
    except anthropic.AnthropicError as e:
        error = f"The AI answer isn't available: {e}"
    return {"role": "assistant", "content": error, "sections": retrieve([message]), "error": True}


FLAGS_FILE = Path(__file__).parent.parent / "logs" / "flags.jsonl"


def save_flag(question, message, comment):
    """Add one flagged answer to logs/flags.jsonl (one JSON record per line)."""
    FLAGS_FILE.parent.mkdir(exist_ok=True)
    record = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "searched": message.get("searched", ""),
        "answer": message["content"],
        "sections": [f"{s['law']}, s. {s['section']}" for s in message["sections"]],
        "comment": comment.strip(),
    }
    with FLAGS_FILE.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def flag_button(i, question, message):
    """A small "Flag this answer" pop-up under each reply."""
    flagged = st.session_state.setdefault("flagged", set())
    if i in flagged:
        st.caption("Thanks, this answer was flagged for review.")
        return
    with st.popover("Flag this answer", icon=":material/flag:"):
        st.caption("Think this answer is wrong or unclear? Flag it so it can be checked against the law.")
        with st.form(f"flag-{i}", border=False):
            comment = st.text_area("What looks wrong? (optional)", key=f"flag-comment-{i}")
            if st.form_submit_button("Send flag", type="primary"):
                save_flag(question, message, comment)
                flagged.add(i)
                st.rerun()


def suggest(text):
    st.session_state["pending"] = text


def new_conversation():
    st.session_state["messages"] = []


messages = st.session_state.setdefault("messages", [])
lookup = current_lookup()
collected, _ = law_dates()

# ---- Header -----------------------------------------------------------------
title, action = st.columns([4, 1.3], vertical_alignment="bottom")
with title:
    st.markdown('<div class="eyebrow">The Bridge</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="section-title">How can I help?</h2>', unsafe_allow_html=True)
    chips = "".join(f'<span class="chip">{group}</span>' for group in GROUPS)
    st.markdown(f'<div class="chips">{chips}<span class="chip">Law text from {collected}</span></div>',
                unsafe_allow_html=True)
with action:
    st.button("New conversation", icon=":material/add:", on_click=new_conversation, use_container_width=True,
              disabled=not messages)
st.write("")

# ---- Conversation -----------------------------------------------------------
if not messages and "pending" not in st.session_state:
    with st.chat_message("assistant", avatar=":material/gavel:"):
        st.markdown(
            "Hi! Tell me what's going on in your own words, and I'll find the Ontario laws that "
            "apply and explain what they say, with the exact sections. I can help with "
            + ", ".join(f"**{topic}**" for topic in TOPICS[:-1])
            + f", and **{TOPICS[-1]}**."
        )
        st.caption("Or start with one of these:")
        left, right = st.columns(2)
        for i, text in enumerate(SUGGESTIONS):
            (left if i % 2 == 0 else right).button(
                text, key=f"suggest-{i}", on_click=suggest, args=(text,), use_container_width=True,
            )

for i, message in enumerate(messages):
    with st.chat_message(message["role"], avatar=":material/gavel:" if message["role"] == "assistant" else ":material/person:"):
        if message.get("searched"):
            st.markdown(f'<div class="searched">Searched the laws for: {html.escape(message["searched"])}</div>',
                        unsafe_allow_html=True)
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(safe(message["content"]))
        if message["role"] == "user":
            st.markdown('<span class="user-msg"></span>', unsafe_allow_html=True)  # tints the bubble
        if message["role"] == "assistant":
            show_laws(message, lookup)
            if not message.get("error"):
                flag_button(i, messages[i - 1]["content"] if i else "", message)

# ---- "Get ready for a lawyer" ------------------------------------------------
if any(m["role"] == "assistant" and not m.get("error") for m in messages):
    with st.container(border=True):
        st.markdown("**Get ready for a lawyer.** Turn this conversation into a one-page summary to bring to a "
                    "lawyer, paralegal or legal clinic: what happened, the laws that apply, your options, and "
                    "questions to ask.")
        ready = st.session_state.get("lawyer_pdf")
        if ready and ready[0] == len(messages):
            st.download_button("Download summary (PDF)", ready[1], file_name="the-bridge-summary.pdf",
                               mime="application/pdf", icon=":material/download:", type="primary")
        elif st.button("Make my summary", icon=":material/description:"):
            with st.spinner("Writing your summary..."):
                try:
                    pdf = make_pdf(build_summary(messages, lookup), messages)
                    st.session_state["lawyer_pdf"] = (len(messages), pdf)
                    st.rerun()
                except anthropic.AnthropicError as e:
                    st.error(f"The summary isn't available right now: {e}")

typed = st.chat_input("Describe your situation or ask a question...")
new = typed or st.session_state.pop("pending", None)
if new:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(safe(new))
        st.markdown('<span class="user-msg"></span>', unsafe_allow_html=True)
    with st.chat_message("assistant", avatar=":material/gavel:"):
        with st.spinner("Finding the laws that apply..."):
            reply = reply_to(new)
    messages += [{"role": "user", "content": new}, reply]
    st.rerun()

footer()

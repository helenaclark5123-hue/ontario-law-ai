"""Stage 5: A simple web app for the Ontario law assistant.

    .venv/bin/streamlit run app.py
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import html
import json
import os
from datetime import datetime

import anthropic
import streamlit as st

from answer import MissingKeyError
from chat import chat_turn
from citations import extract_citations
from get_laws import load_saved_laws
from make_chunks import CHUNKS_FILE
from search import build, get_collection, retrieve
from update_laws import STATUS_FILE, update

st.set_page_config(page_title="Ontario Law Assistant", page_icon="⚖️", layout="centered")

# One icon and plain-English topic per Act, used on badges and section titles.
LAW_STYLE = {
    "Residential Tenancies Act, 2006": ("🏠", "Renting"),
    "Employment Standards Act, 2000": ("💼", "Work"),
    "Consumer Protection Act, 2002": ("🛒", "Buying things"),
}
EXAMPLES = {
    "🏠 Renting": "My landlord is trying to kick me out. What are my rights?",
    "💼 Work": "My boss wants me to work a 13-hour shift. Is that allowed?",
    "🛒 Buying": "Someone sold me something at my door yesterday and I want to cancel.",
}
WELCOME = (
    "Hi! Tell me what's going on in your own words, like *\"my landlord is trying to kick me out\"* "
    "or *\"my boss didn't pay me overtime\"*. I'll find the Ontario laws that apply and explain "
    "what they say, with the exact sections. I can help with **renting**, **work** and **buying things**."
)

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextInput input, button {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, h4, .hero-title {
    font-family: 'Source Serif 4', Georgia, serif !important;
    letter-spacing: -0.01em;
}
.block-container { padding-top: 2.5rem; max-width: 760px; }

/* Header */
.hero { border-bottom: 1px solid #E2DCCF; padding-bottom: 1.1rem; margin-bottom: 1.4rem; }
.hero p.hero-title {
    font-size: 2.4rem !important; font-weight: 700; color: #1F3A5F; margin: 0 !important; line-height: 1.15;
}
.hero p.hero-sub { color: #4A5566; font-size: 1.05rem !important; margin: .5rem 0 .9rem !important; }
.badges { display: flex; flex-wrap: wrap; gap: .45rem; }
.badge {
    background: #FFFFFF; border: 1px solid #E2DCCF; border-radius: 999px;
    padding: .25rem .75rem; font-size: .85rem; color: #1E2733; white-space: nowrap;
}
.hero p.status { color: #6B7280; font-size: .8rem !important; margin: .8rem 0 0 !important; }
.status b { color: #4A5566; font-weight: 600; }

/* Chat */
[data-testid="stChatMessage"] { background: #FFFFFF; border: 1px solid #E2DCCF; border-radius: 12px; }
.searched { color: #6B7280; font-size: .8rem; font-style: italic; margin: .2rem 0 .4rem; }
.law-title { font-weight: 600; color: #1F3A5F; margin-top: .6rem; }

/* Footer */
.footer {
    margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid #E2DCCF;
    color: #6B7280; font-size: .8rem; line-height: 1.5;
}
</style>
"""


def load_api_key():
    """Online, the key comes from Streamlit secrets; on my computer, from .env.

    Streamlit secrets are set in the app's settings on Streamlit Community
    Cloud, so the key never has to be in the code or uploaded to GitHub.
    If there are no secrets (on my computer), answer.py reads .env instead.
    """
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets file exists on my computer
        key = None
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key


@st.cache_resource(show_spinner=False)
def ensure_database():
    """Build the search database from data/chunks.json if it's missing.

    The prebuilt db/ folder is uploaded with the app, because building it
    takes several minutes. This is only a backup in case db/ is missing.
    """
    if get_collection().count() == 0:
        with st.spinner("Building the law search database (this can take several minutes)..."):
            build()


load_api_key()
ensure_database()


def nice_date(iso):
    return datetime.fromisoformat(iso).strftime("%b %-d, %Y")


def nice_time(iso):
    return datetime.fromisoformat(iso).strftime("%b %-d, %Y at %-I:%M %p")


def safe(text):
    """Stop Streamlit from treating $ signs in law text as maths formulas."""
    return text.replace("$", "\\$")


@st.cache_data
def section_lookup(version):
    """Full saved text and heading of every section, by (law, section number).

    `version` is when chunks.json last changed, so the cache refreshes
    whenever the stored laws change (an update or a fake amendment).
    """
    chunks = json.loads(CHUNKS_FILE.read_text())
    headings = {(c["law"], c["section"]): c["heading"] for c in chunks}
    lookup = {}
    for law in load_saved_laws():
        for number, text in law["sections"].items():
            lookup[(law["name"], number)] = {
                "text": text, "url": law["url"], "heading": headings.get((law["name"], number), ""),
            }
    return lookup


def read_status():
    return json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}


def section_title(law, number, info):
    icon, _ = LAW_STYLE.get(law, ("📘", ""))
    return f"{icon} {law}, s. {number}" + (f" — {info['heading']}" if info["heading"] else "")


def show_laws(message, lookup):
    """A "Laws used" drop-down under a reply: the full text of every section
    the reply cites, then the other sections that were searched."""
    cited = [
        (c["law"], c["section"]) for c in extract_citations(message["content"], None)
        if (c["law"], c["section"]) in lookup
    ]
    searched = [(s["law"], s["section"]) for s in message["sections"]]
    others = [s for s in dict.fromkeys(searched) if s not in cited]
    label = f"📚 Laws used ({len(cited)})" if cited else f"📚 Law sections found ({len(others)})"
    with st.expander(label):
        for law, number in cited:
            info = lookup[(law, number)]
            st.markdown(f'<div class="law-title">{html.escape(section_title(law, number, info))}</div>',
                        unsafe_allow_html=True)
            st.markdown(safe(info["text"]).replace("\n", "  \n"))
            st.caption(f"Official version: [{info['url']}]({info['url']}) (find section {number})")
        if others:
            st.caption("Also searched: " + "; ".join(
                f"{LAW_STYLE.get(law, ('📘',))[0]} {law.split(',')[0]} s. {n}" for law, n in others
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


def use_example(text):
    st.session_state["pending"] = text


def new_conversation():
    st.session_state["messages"] = []


st.markdown(STYLE, unsafe_allow_html=True)

# ---- Header -----------------------------------------------------------------
status = read_status()
laws = status.get("laws") or {law["name"]: law["scraped_timestamp"] for law in load_saved_laws()}
badges = "".join(
    f'<span class="badge">{LAW_STYLE[name][0]} {name}</span>' for name in laws if name in LAW_STYLE
)
checked = nice_time(status["last_checked"]) if "last_checked" in status else "never"
st.markdown(
    f"""
    <div class="hero">
      <p class="hero-title">⚖️ Ontario Law Assistant</p>
      <p class="hero-sub">Plain-language answers about renting, work and buying things in Ontario,
      taken only from the text of the law, with the exact section cited.</p>
      <div class="badges">{badges}</div>
      <p class="status"><b>Law text collected:</b> {nice_date(max(laws.values()))}
      &nbsp;·&nbsp; <b>Last checked for updates:</b> {checked}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Sidebar ----------------------------------------------------------------
with st.sidebar:
    st.button("💬  New conversation", on_click=new_conversation, use_container_width=True, type="primary")
    st.divider()
    st.markdown("### Keep the laws current")
    st.caption("Re-downloads the laws from the A2AJ dataset and updates only the sections that changed.")
    if st.button("🔄  Check for updates", use_container_width=True):
        with st.spinner("Downloading the latest laws and comparing every section..."):
            report = update()
        st.session_state["update_report"] = report
        st.cache_data.clear()
        st.rerun()

    report = st.session_state.get("update_report")
    if report:
        n = len(report["changed"]) + len(report["added"]) + len(report["removed"])
        if n == 0:
            st.success("No changes: the laws are up to date.")
        else:
            st.warning(
                f"Updated: {len(report['changed'])} changed, "
                f"{len(report['added'])} added, {len(report['removed'])} removed."
            )
            for c in report["changed"]:
                st.write(f"• Changed: {c['where']}")
            for a in report["added"]:
                st.write(f"• Added: {a}")
            for r in report["removed"]:
                st.write(f"• Removed: {r}")

    # Always show the most recent change, even if a later check found nothing new.
    if status.get("last_changes"):
        st.caption(f"**Last change found:** {nice_time(status['last_changed'])}")
        for change in status["last_changes"][:10]:
            st.caption(f"• {change}")

    st.divider()
    st.markdown("### About")
    st.caption(
        "Covers three Ontario statutes only, not regulations or case law. The law text is an "
        "unofficial copy from the A2AJ Canadian Legal Data project (Osgoode Hall Law School and "
        "Toronto Metropolitan University). Answers are written by Claude from the retrieved sections."
    )

# ---- Conversation -----------------------------------------------------------
messages = st.session_state.setdefault("messages", [])
lookup = section_lookup(CHUNKS_FILE.stat().st_mtime)

with st.chat_message("assistant", avatar="⚖️"):
    st.markdown(WELCOME)
    if not messages:
        st.caption("Try an example:")
        columns = st.columns(len(EXAMPLES))
        for column, (label, example) in zip(columns, EXAMPLES.items()):
            column.button(label, on_click=use_example, args=(example,), use_container_width=True)

for message in messages:
    with st.chat_message(message["role"], avatar="⚖️" if message["role"] == "assistant" else "🙂"):
        if message.get("searched"):
            st.markdown(f'<div class="searched">Searched the laws for: {html.escape(message["searched"])}</div>',
                        unsafe_allow_html=True)
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(safe(message["content"]))
        if message["role"] == "assistant":
            show_laws(message, lookup)

typed = st.chat_input("Describe your situation or ask a question...")
new = typed or st.session_state.pop("pending", None)
if new:
    with st.chat_message("user", avatar="🙂"):
        st.markdown(safe(new))
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("Finding the laws that apply..."):
            reply = reply_to(new)
    messages += [{"role": "user", "content": new}, reply]
    st.rerun()

# ---- Footer -----------------------------------------------------------------
st.markdown(
    """
    <div class="footer">
      <b>This is legal information, not legal advice.</b> For advice about your situation, contact a
      lawyer, paralegal or community legal clinic. Always check the official text on
      <a href="https://www.ontario.ca/laws" target="_blank">ontario.ca/laws</a>.
    </div>
    """,
    unsafe_allow_html=True,
)

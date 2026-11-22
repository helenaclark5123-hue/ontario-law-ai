"""Shared look and helpers for every page of the website."""

import json
from datetime import datetime

import streamlit as st

from get_laws import load_saved_laws
from make_chunks import CHUNKS_FILE
from update_laws import STATUS_FILE

# One icon, plain-English topic and short description per Act.
LAWS = {
    "Residential Tenancies Act, 2006": {
        "icon": "🏠", "topic": "Renting",
        "about": "Rent increases, evictions, repairs, deposits and your landlord entering your home.",
        "examples": [
            "My landlord is trying to kick me out. What are my rights?",
            "Can my landlord raise my rent whenever they want?",
        ],
    },
    "Employment Standards Act, 2000": {
        "icon": "💼", "topic": "Work",
        "about": "Hours, breaks, overtime, vacation, sick days, and being fired or laid off.",
        "examples": [
            "My boss wants me to work a 13-hour shift. Is that allowed?",
            "I got fired without warning. Do they owe me anything?",
        ],
    },
    "Consumer Protection Act, 2002": {
        "icon": "🛒", "topic": "Buying things",
        "about": "Cancelling contracts, door-to-door sales, gym memberships, estimates and refunds.",
        "examples": [
            "Someone sold me something at my door yesterday and I want to cancel.",
            "A mechanic charged me way more than his estimate. What can I do?",
        ],
    },
}

NAVY, GOLD = "#1F3A5F", "#8A6D3B"

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextInput input, button, textarea {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, h4, .serif { font-family: 'Source Serif 4', Georgia, serif !important; letter-spacing: -0.01em; }
.block-container { padding-top: 3.5rem; padding-bottom: 3rem; max-width: 1080px; }
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], #MainMenu { display: none; }

/* Small uppercase label above headings */
.eyebrow {
    text-transform: uppercase; letter-spacing: .12em; font-size: .75rem;
    font-weight: 600; color: #8A6D3B; margin-bottom: .5rem;
}
.muted { color: #5B6474; }

/* Home: hero */
.hero { padding: 2.5rem 0 1.2rem; }
.hero h1 { font-size: 3.1rem !important; line-height: 1.08; color: #1F3A5F; margin: 0 0 1rem; padding: 0; }
.hero p.lead { font-size: 1.2rem; color: #3E4757; max-width: 640px; line-height: 1.55; margin: 0; }

/* Home: trust strip */
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: #E2DCCF;
         border: 1px solid #E2DCCF; border-radius: 14px; overflow: hidden; margin: 2.2rem 0 3rem; }
.stat { background: #FFFFFF; padding: 1.1rem 1.2rem; }
.stat b { display: block; font-family: 'Source Serif 4', Georgia, serif; font-size: 1.55rem; color: #1F3A5F; }
.stat span { font-size: .85rem; color: #5B6474; }

/* Section headings */
.section-title { font-size: 1.9rem !important; color: #1F3A5F; margin: 0 0 .3rem; padding: 0; }

/* Cards (bordered containers named "card-...") */
[class*="st-key-card-"] {
    background: #FFFFFF; border-radius: 14px !important; padding: 1.3rem 1.2rem !important;
    box-shadow: 0 1px 2px rgba(30, 39, 51, .04);
}
/* Example questions inside cards look like links */
[class*="st-key-card-"] [data-testid="stBaseButton-tertiary"] {
    justify-content: flex-start; text-align: left; color: #1F3A5F; padding: .15rem 0; min-height: 0;
}
[class*="st-key-card-"] [data-testid="stBaseButton-tertiary"] p { text-align: left; font-size: .9rem; }
[class*="st-key-card-"] [data-testid="stBaseButton-tertiary"]:hover { color: #8A6D3B; text-decoration: underline; }
.card-head { font-size: 1.9rem; line-height: 1; margin-bottom: .6rem; }
.card-title { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.3rem; font-weight: 700; color: #1F3A5F; }
.card-law { font-size: .8rem; color: #8A6D3B; font-weight: 600; margin: .15rem 0 .55rem; }
.card-text { font-size: .93rem; color: #3E4757; line-height: 1.5; }

/* How-it-works steps */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem; margin-top: 1rem; }
.step { background: #FFFFFF; border: 1px solid #E2DCCF; border-radius: 14px; padding: 1.3rem; }
.step-num { width: 2rem; height: 2rem; border-radius: 50%; background: #1F3A5F; color: #FFFFFF;
            display: flex; align-items: center; justify-content: center; font-weight: 600; margin-bottom: .8rem; }
.step b { display: block; color: #1E2733; margin-bottom: .3rem; }
.step span { font-size: .92rem; color: #3E4757; line-height: 1.5; }

/* Chat */
[data-testid="stChatMessage"] { background: #FFFFFF; border: 1px solid #E2DCCF; border-radius: 14px; padding: 1rem 1.1rem; }
[data-testid="stChatMessage"]:has(.user-msg) { background: #EEF2F7; border-color: #D7E0EB; }
.searched { color: #6B7280; font-size: .8rem; font-style: italic; margin: 0 0 .5rem; }
.law-title { font-weight: 600; color: #1F3A5F; margin-top: .6rem; }
.badges { display: flex; flex-wrap: wrap; gap: .45rem; margin-top: .6rem; }
.badge { background: #FFFFFF; border: 1px solid #E2DCCF; border-radius: 999px; padding: .2rem .7rem;
         font-size: .8rem; color: #1E2733; white-space: nowrap; }

/* Footer */
.footer { margin-top: 3.5rem; padding-top: 1.2rem; border-top: 1px solid #E2DCCF;
          color: #6B7280; font-size: .82rem; line-height: 1.6; }

/* Phones */
@media (max-width: 640px) {
    .hero h1 { font-size: 2.2rem !important; }
    .hero h1 br { display: none; }
    .hero p.lead { font-size: 1.05rem; }
    .stats { grid-template-columns: repeat(2, 1fr); }
    .steps { grid-template-columns: 1fr; }
    .block-container { padding-top: 2.5rem; }
}
</style>
"""


def apply_style():
    st.markdown(STYLE, unsafe_allow_html=True)


def nice_date(iso):
    return datetime.fromisoformat(iso).strftime("%b %-d, %Y")


def nice_time(iso):
    return datetime.fromisoformat(iso).strftime("%b %-d, %Y at %-I:%M %p")


def safe(text):
    """Stop Streamlit from treating $ signs in law text as maths formulas."""
    return text.replace("$", "\\$")


def read_status():
    return json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}


def law_dates():
    """When A2AJ collected each law, and when we last checked for updates."""
    status = read_status()
    laws = status.get("laws") or {law["name"]: law["scraped_timestamp"] for law in load_saved_laws()}
    checked = nice_time(status["last_checked"]) if "last_checked" in status else "never"
    return nice_date(max(laws.values())), checked


@st.cache_data(show_spinner=False)
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


def current_lookup():
    return section_lookup(CHUNKS_FILE.stat().st_mtime)


@st.cache_data(show_spinner=False)
def _section_counts(version):
    chunks = json.loads(CHUNKS_FILE.read_text())
    sections = {(c["law"], c["section"]) for c in chunks}  # repealed/blank sections have no chunks
    counts = {}
    for law, _ in sections:
        counts[law] = counts.get(law, 0) + 1
    return counts


def section_counts():
    """Number of sections with law text in them, per Act (repealed ones excluded)."""
    return _section_counts(CHUNKS_FILE.stat().st_mtime)


def start_chat(text):
    """Open the assistant page with this message already sent."""
    st.session_state["pending"] = text
    st.switch_page("views/assistant.py")


def footer():
    st.markdown(
        """
        <div class="footer">
          <b>This is legal information, not legal advice.</b> For advice about your situation, contact a
          lawyer, paralegal or community legal clinic. Always check the official text on
          <a href="https://www.ontario.ca/laws" target="_blank">ontario.ca/laws</a>.<br>
          Law text: unofficial copy from the A2AJ Canadian Legal Data project (Osgoode Hall Law School and
          Toronto Metropolitan University). Answers are written by Claude from the retrieved sections.
        </div>
        """,
        unsafe_allow_html=True,
    )

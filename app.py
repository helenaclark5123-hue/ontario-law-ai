"""Stage 5: A simple web app for the Ontario law assistant.

    .venv/bin/streamlit run app.py
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import json
import os
import re
from datetime import datetime

import anthropic
import streamlit as st

from answer import MissingKeyError, answer
from get_laws import LAWS, load_saved_laws
from make_chunks import CHUNKS_FILE
from search import build, get_collection, search
from update_laws import STATUS_FILE, update

st.set_page_config(page_title="Ontario Law Assistant", page_icon="⚖️")


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

# Matches citations like "Residential Tenancies Act, 2006, s. 116" in an answer.
CITATION = re.compile(
    "(" + "|".join(re.escape(name) for name in LAWS) + r"),?\s*s\.\s*(\d+(?:\.\d+)*)"
)


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


def status_line():
    status = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
    laws = status.get("laws") or {law["name"]: law["scraped_timestamp"] for law in load_saved_laws()}
    names = " · ".join(laws)
    collected = nice_date(max(laws.values()))
    checked = nice_time(status["last_checked"]) if "last_checked" in status else "never"
    return names, collected, checked


def show_section(law, number, lookup, expanded=False):
    info = lookup.get((law, number))
    if not info:
        return
    title = f"{law}, s. {number}" + (f" – {info['heading']}" if info["heading"] else "")
    with st.expander(title, expanded=expanded):
        st.markdown(safe(info["text"]).replace("\n", "  \n"))
        st.caption(f"Official version: [{info['url']}]({info['url']}) (find section {number})")


# ---- Header -----------------------------------------------------------------
st.title("⚖️ Ontario Law Assistant")
names, collected, checked = status_line()
st.caption(
    f"**Laws loaded:** {names}  \n"
    f"**Law text collected by A2AJ:** {collected} · **Last checked for updates:** {checked}"
)

with st.sidebar:
    st.subheader("Keep the laws current")
    st.write("Re-downloads the laws from the A2AJ dataset and updates only the sections that changed.")
    if st.button("Check for updates", use_container_width=True):
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
    status = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
    if status.get("last_changes"):
        st.caption(f"**Last change found:** {nice_time(status['last_changed'])}")
        for change in status["last_changes"][:10]:
            st.caption(f"• {change}")
    st.caption("Full details in logs/update_log.md")

    st.divider()
    st.caption(
        "Covers only these three Ontario statutes (not regulations or case law). "
        "Law text is an unofficial copy from the A2AJ Canadian Legal Data project."
    )

# ---- Question and answer ----------------------------------------------------
with st.form("ask"):
    question = st.text_input(
        "Ask a question about renting, work, or buying things in Ontario",
        placeholder="e.g. How much notice does my landlord need to give before raising my rent?",
    )
    asked = st.form_submit_button("Ask")

if asked and question.strip():
    lookup = section_lookup(CHUNKS_FILE.stat().st_mtime)
    with st.spinner("Searching the laws and writing an answer..."):
        error = None
        try:
            result = answer(question)
            retrieved = result["sections"]
        except MissingKeyError:
            error = (
                "The AI answer isn't available yet: no API key is set "
                "(.env on my computer, or the app's Secrets settings online)."
            )
        except anthropic.AuthenticationError:
            error = (
                "The AI answer isn't available: the API key isn't working. Check it was pasted "
                "correctly (.env on my computer, or the app's Secrets settings online)."
            )
        except anthropic.AnthropicError as e:
            error = f"The AI answer isn't available: {e}"
        if error:
            result, retrieved = None, search(question)

    if result:
        st.markdown(safe(result["answer"]))
        cited = list(dict.fromkeys(CITATION.findall(result["answer"])))
        if cited:
            st.subheader("Sections cited")
            for law, number in cited:
                show_section(law, number, lookup)
    else:
        st.error(error)
        st.info("Here are the law sections the search found. The AI would answer using these.")
        cited = []

    others = [(c["law"], c["section"]) for c in retrieved]
    others = [s for s in dict.fromkeys(others) if s not in cited]
    if others:
        st.subheader("Other sections searched" if cited else "Sections found")
        for law, number in others:
            show_section(law, number, lookup)

"""The Ontario Law Assistant website: a home page, the chat assistant, and a
"How it works" page, with navigation along the top.

    .venv/bin/streamlit run app.py
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import os

import streamlit as st

from search import build, get_collection
from ui import apply_style

st.set_page_config(page_title="Ontario Law Assistant", page_icon="⚖️", layout="wide")


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
apply_style()
st.logo("static/flag-canada.png", size="large", link="https://ontario-law-ai-hairmdjbph7rmavchjbpbd.streamlit.app/")

pages = st.navigation(
    [
        st.Page("views/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("views/assistant.py", title="Ask the assistant", icon=":material/forum:", url_path="assistant"),
        st.Page("views/how_it_works.py", title="How it works", icon=":material/menu_book:",
                url_path="how-it-works"),
    ],
    position="top",
)
pages.run()

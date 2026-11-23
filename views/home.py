"""Home page: what the assistant does, the topics it covers, and how it works."""

import streamlit as st

from get_laws import REGULATIONS
from ui import GROUPS, LAWS, STATIC, number_word, footer, grid, law_dates, section_counts, start_chat

collected, _ = law_dates()
sections = sum(section_counts().values())

# ---- Hero (photo: Toronto skyline at night) ---------------------------------
st.markdown(
    f"""
    <div class="hero">
      <div class="flag-line"><img src="{STATIC}/flag-canada.png" alt="Flag of Canada">
        <span>Ontario Law Assistant</span></div>
      <h1>Know your rights in Ontario, straight from the law.</h1>
      <p class="lead">Describe your problem in your own words: your landlord or condo, your job, a purchase or a debt,
      your family, driving, discrimination, benefits, and more.
      The assistant finds the Ontario laws that apply and explains them in plain English,
      citing the exact section for every point.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")
left, right, _ = st.columns([1.3, 1, 3.2])
if left.button("Start a conversation  →", type="primary", use_container_width=True):
    st.switch_page("views/assistant.py")
if right.button("How it works", use_container_width=True):
    st.switch_page("views/how_it_works.py")

# ---- Trust strip ------------------------------------------------------------
st.markdown(
    f"""
    <div class="stats">
      <div class="stat"><b>{len(LAWS)}</b><span>Ontario laws covered</span></div>
      <div class="stat"><b>{sections:,}</b><span>sections of law searched</span></div>
      <div class="stat"><b>Every point</b><span>cites the exact section</span></div>
      <div class="stat"><b>{collected}</b><span>law text last updated</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Topics -----------------------------------------------------------------
st.markdown('<div class="eyebrow">What it can help with</div>', unsafe_allow_html=True)
st.markdown('<h2 class="section-title">Pick a topic, or just describe your situation</h2>', unsafe_allow_html=True)
st.write("")
for tab, names in zip(st.tabs(list(GROUPS)), GROUPS.values()):
    with tab:
        for column, (law, info) in grid((n, LAWS[n]) for n in names):
            with column, st.container(border=True, key=f"card-{info['topic'].lower().replace(' ', '-')}"):
                st.markdown(
                    f"""
                    <div class="card-photo" style="background-image:url('{info['photo']}')"></div>
                    <div class="card-body">
                      <div class="card-title">{info['topic']}</div>
                      <div class="card-law">{law}</div>
                      <div class="card-text">{info['about']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                for i, example in enumerate(info["examples"]):
                    if st.button(f"“{example}”  →", key=f"ex-{law}-{i}", type="tertiary"):
                        start_chat(example)

# ---- How it works -----------------------------------------------------------
st.write("")
st.write("")
st.markdown('<div class="eyebrow">How it works</div>', unsafe_allow_html=True)
st.markdown('<h2 class="section-title">Answers from the law itself, not from memory</h2>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="steps">
      <div class="step"><div class="step-num">01</div><b>Tell it what's happening</b>
        <span>Write it the way you'd tell a friend, like "my landlord is trying to kick me out".
        It asks a follow-up question if it needs more details.</span></div>
      <div class="step"><div class="step-num">02</div><b>It finds the laws that apply</b>
        <span>Your words are translated into legal terms and matched against every section of
        the {number_word(len(LAWS))} Acts and {len(REGULATIONS)} regulations, so it finds the right rules even if you don't know what they're called.</span></div>
      <div class="step"><div class="step-num">03</div><b>You get a cited answer</b>
        <span>The answer only uses the law it found, cites a section for every point, and says so
        when the law doesn't cover your question. You can read the original text of each section.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
st.write("")
_, middle, _ = st.columns([2, 1.2, 2])
if middle.button("Ask your question  →", type="primary", use_container_width=True, key="cta-bottom"):
    st.switch_page("views/assistant.py")

footer()

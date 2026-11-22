"""How it works: the laws covered, how answers are made and tested, keeping
the law current, and the limitations."""

import streamlit as st

from get_laws import load_saved_laws
from ui import LAWS, footer, nice_date, nice_time, read_status, section_counts
from update_laws import update

st.markdown("<style>.block-container { max-width: 960px; }</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">How it works</div>', unsafe_allow_html=True)
st.markdown('<h1 class="section-title" style="font-size:2.6rem !important">Built on the text of the law</h1>',
            unsafe_allow_html=True)
st.markdown(
    '<p class="muted" style="font-size:1.1rem; max-width:680px">The assistant never answers from memory. '
    "It looks up the actual sections of Ontario law, answers only from what they say, and shows "
    "you exactly where each point comes from.</p>",
    unsafe_allow_html=True,
)
st.write("")

# ---- The laws ---------------------------------------------------------------
st.markdown("### The laws it covers")
counts = section_counts()
saved = {law["name"]: law for law in load_saved_laws()}
for column, (name, info) in zip(st.columns(3, gap="medium"), LAWS.items()):
    law = saved.get(name, {})
    count = counts.get(name, 0)
    with column, st.container(border=True, key=f"card-{info['topic'].split()[0].lower()}"):
        st.markdown(
            f"""
            <div class="card-head">{info['icon']}</div>
            <div class="card-title">{info['topic']}</div>
            <div class="card-law">{name}</div>
            <div class="card-text">{info['about']}</div>
            <div class="card-text" style="margin-top:.7rem"><b>{count}</b> sections ·
            collected {nice_date(law['scraped_timestamp']) if law else '?'}</div>
            """,
            unsafe_allow_html=True,
        )
        if law:
            st.link_button("Official text on ontario.ca ↗", law["url"], use_container_width=True)
st.caption("Statutes only. Regulations (like the yearly rent increase guideline amount) and court decisions "
           "are not included.")

# ---- How an answer is made --------------------------------------------------
st.write("")
st.markdown("### How an answer is made")
st.markdown(
    """
    <div class="steps">
      <div class="step"><div class="step-num">1</div><b>Understand the question</b>
        <span>Your message, plus anything you said earlier in the conversation, is turned into a
        search question, and rewritten in the law's own words (for example, "door-to-door" becomes
        "direct agreement").</span></div>
      <div class="step"><div class="step-num">2</div><b>Find the law</b>
        <span>Both versions are matched by meaning against every section of the three Acts. The 8 best
        sections are pulled in whole, so related rules and exceptions stay together.</span></div>
      <div class="step"><div class="step-num">3</div><b>Answer only from it</b>
        <span>Claude writes the answer using only those sections, cites a section for every point, says
        "I couldn't find this" when the law doesn't cover it, and asks a follow-up if a key fact is missing.</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Testing ----------------------------------------------------------------
st.write("")
st.markdown("### How it's tested")
a, b, c = st.columns(3)
a.metric("Test questions answered correctly", "33 / 35", help="Final test run, Nov 21, 2026, graded against an answer key written from the law text.")
b.metric("Answers that made up law", "0", help="No answer stated a rule, number or section that isn't in the law.")
c.metric("Out-of-scope questions declined", "6 / 6", help="Questions about criminal, family, traffic, tax and other laws it doesn't cover.")
st.markdown(
    "Every answer in the test set is graded by an AI judge against a written answer key, and a "
    "**citation checker** confirms that each cited section exists and says what the answer claims. "
    "When the assistant got something wrong, it was because search missed a section, and the assistant "
    "said it couldn't find the rule rather than guessing. Full results are in the project's "
    "[GitHub repository](https://github.com/helenaclark5123-hue/ontario-law-ai)."
)

# ---- Keeping it current -----------------------------------------------------
st.write("")
st.markdown("### Keeping the law current")
status = read_status()
with st.container(border=True):
    info, action = st.columns([3, 1.2], vertical_alignment="center")
    with info:
        checked = nice_time(status["last_checked"]) if "last_checked" in status else "never"
        st.markdown(f"**Last checked for updates:** {checked}")
        st.caption("Checking re-downloads the three laws, compares every section, and updates only the "
                   "ones that changed.")
    with action:
        if st.button("🔄 Check for updates", use_container_width=True):
            with st.spinner("Downloading the latest laws and comparing every section..."):
                st.session_state["update_report"] = update()
            st.cache_data.clear()
            st.rerun()
    report = st.session_state.get("update_report")
    if report:
        n = len(report["changed"]) + len(report["added"]) + len(report["removed"])
        if n == 0:
            st.success("No changes: the laws are up to date.")
        else:
            st.warning(f"Updated: {len(report['changed'])} changed, {len(report['added'])} added, "
                       f"{len(report['removed'])} removed.")
            for item in [f"Changed: {c['where']}" for c in report["changed"]] + \
                        [f"Added: {a}" for a in report["added"]] + [f"Removed: {r}" for r in report["removed"]]:
                st.write(f"• {item}")

# ---- Limitations ------------------------------------------------------------
st.write("")
st.markdown("### Limitations")
st.markdown(
    """
- **Legal information, not legal advice.** It explains what the law says; it can't tell you what to do in your case.
- **Three laws only**, and only the Acts themselves, not regulations or court decisions.
- **Unofficial copy.** The text comes from the A2AJ Canadian Legal Data project and is only as current as their last update.
- **Search can miss a section**, especially when a problem is described in everyday words. Check the original text, and when it matters, ask a lawyer, paralegal or community legal clinic.
"""
)

footer()

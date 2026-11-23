"""How it works: the laws covered, how answers are made and tested, keeping
the law current, and the limitations."""

import json
from pathlib import Path

import streamlit as st

from get_laws import REGULATIONS, load_saved_laws
from ui import LAWS, STATIC, number_word, footer, grid, nice_date, nice_time, read_status, section_counts
from update_laws import update

st.markdown("<style>.block-container { max-width: 960px; }</style>", unsafe_allow_html=True)

# ---- Header (photo: Queen's Park, the Legislative Assembly of Ontario) ------
st.markdown(
    f"""
    <div class="page-hero" style="background: linear-gradient(90deg, rgba(11,20,36,.95) 0%,
         rgba(11,20,36,.78) 55%, rgba(11,20,36,.35) 100%), url('{STATIC}/queens-park.jpg') center 40% / cover;">
      <div class="eyebrow">How it works</div>
      <h1>Built on the text of the law</h1>
      <p>The assistant never answers from memory. It looks up the actual sections of Ontario law,
      answers only from what they say, and shows you exactly where each point comes from.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- The laws ---------------------------------------------------------------
st.markdown("### The laws it covers")
counts = section_counts()
saved = {law["name"]: law for law in load_saved_laws()}
for column, (name, info) in grid(LAWS.items()):
    law = saved.get(name, {})
    count = counts.get(name, 0)
    regs = [r for r in REGULATIONS if r["parent"] == name]
    reg_list = "".join(
        f'<div class="card-text" style="font-size:.82rem">{r["name"]}: {r["title"]} '
        f'({counts.get(r["name"], 0)} sections)</div>' for r in regs
    )
    with column, st.container(border=True, key=f"card-{info['topic'].lower().replace(' ', '-')}"):
        st.markdown(
            f"""
            <div class="card-photo" style="background-image:url('{info['photo']}'); height:130px"></div>
            <div class="card-body">
              <div class="card-title">{info['topic']}</div>
              <div class="card-law">{name}</div>
              <div class="card-text">{info['about']}</div>
              <div class="card-text" style="margin:.7rem 0 .8rem"><b>{count}</b> sections ·
              collected {nice_date(law['scraped_timestamp']) if law else '?'}</div>
              <div class="card-law" style="margin-top:.2rem">Regulations included</div>
              {reg_list}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if law:
            st.link_button("Official text on ontario.ca", law["url"], icon=":material/open_in_new:", use_container_width=True)
st.caption("Each Act comes with the main regulations made under it (the detailed rules, amounts and "
           "definitions). Other regulations, the yearly rent increase guideline amount, and court decisions are "
           "not included. The speed limits regulation includes its rules but not its lists of highway stretches. "
           "Divorce itself is a federal law (the Divorce Act) and isn't included; separation, support, property "
           "and parenting under Ontario law are.")

# ---- How an answer is made --------------------------------------------------
st.write("")
st.markdown("### How an answer is made")
st.markdown(
    f"""
    <div class="steps">
      <div class="step"><div class="step-num">01</div><b>Understand the question</b>
        <span>Your message, plus anything you said earlier in the conversation, is turned into a
        search question, and rewritten in the law's own words (for example, "door-to-door" becomes
        "direct agreement").</span></div>
      <div class="step"><div class="step-num">02</div><b>Find the law</b>
        <span>Both versions are matched by meaning against every section of the {number_word(len(LAWS))} Acts
        and {len(REGULATIONS)} regulations. Claude then reads short previews of about 40 matches and picks the 8
        sections that answer the question best, which are pulled in whole so related rules and exceptions
        stay together.</span></div>
      <div class="step"><div class="step-num">03</div><b>Answer only from it</b>
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
c.metric("Out-of-scope questions declined", "6 / 6", help="Questions about criminal, family, traffic, tax and other laws it didn't cover at the time.")
st.markdown(
    "These results are from the final test run on the original three laws (renting, work and buying), before "
    "workplace safety and driving were added. "
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
        st.caption(f"Checking re-downloads the {number_word(len(LAWS))} Acts and {len(REGULATIONS)} regulations, compares every section, and updates only the "
                   "ones that changed.")
    with action:
        if st.button("Check for updates", icon=":material/refresh:", use_container_width=True):
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
    f"""
- **Legal information, not legal advice.** It explains what the law says; it can't tell you what to do in your case.
- **{number_word(len(LAWS)).capitalize()} Acts and {len(REGULATIONS)} of their regulations only**, not other laws or regulations, city bylaws or court decisions.
- **Unofficial copy.** The text comes from the A2AJ Canadian Legal Data project and is only as current as their last update.
- **Search can miss a section**, especially when a problem is described in everyday words. Check the original text, and when it matters, ask a lawyer, paralegal or community legal clinic.
"""
)

# ---- Photo credits (required by the photos' Creative Commons licences) -----
st.write("")
with st.expander("Photo credits"):
    credits = json.loads((Path(__file__).parent.parent / "static" / "photo_credits.json").read_text())
    for file, c in credits.items():
        st.caption(
            f"**{c['title'].rsplit('.', 1)[0]}** by {c['artist'] or 'unknown'}, "
            f"[{c['license']}]({c['license_url'] or c['page']}), via [Wikimedia Commons]({c['page']}). Resized."
        )

footer()

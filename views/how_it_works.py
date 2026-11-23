"""How it works: why The Bridge exists, information vs advice, how answers are
made and checked, test results, keeping the law current, free legal help, and
the limitations."""

import json
from pathlib import Path

import streamlit as st

from get_laws import REGULATIONS, load_saved_laws
from help import FREE_HELP
from ui import GROUPS, LAWS, STATIC, number_word, footer, grid, nice_date, nice_time, read_status, section_counts
from update_laws import update

st.markdown("<style>.block-container { max-width: 960px; }</style>", unsafe_allow_html=True)

# ---- Header (photo: Queen's Park, the Legislative Assembly of Ontario) ------
st.markdown(
    f"""
    <div class="page-hero" style="background: linear-gradient(90deg, rgba(11,20,36,.95) 0%,
         rgba(11,20,36,.78) 55%, rgba(11,20,36,.35) 100%), url('{STATIC}/queens-park.jpg') center 40% / cover;">
      <div class="eyebrow">How it works</div>
      <h1>A bridge to your rights, built on the text of the law</h1>
      <p>The Bridge never answers from memory. It looks up the actual sections of Ontario law,
      explains only what they say, and shows you exactly where each point comes from.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Why The Bridge exists ---------------------------------------------------
st.markdown("### Why The Bridge exists")
st.markdown(
    "Many people with a legal problem never get help. Lawyers are expensive, people often don't know their rights, "
    "and the process can feel scary and lonely. So people with a bad landlord, an unpaid paycheque or a store that "
    "won't give a refund often just give up.\n\n"
    "The Bridge helps people in Ontario understand their rights in plain, warm language, grounded in the real text "
    "of the law. It doesn't replace lawyers. It helps you show up ready: knowing what the law says, what options "
    "people in your situation have, and what to ask. **You deserve justice. We help you get there.**"
)

# ---- Information, not advice ------------------------------------------------
st.write("")
st.markdown("### Information, not advice")
st.markdown(
    "The Bridge gives **legal information**: what the law says, and the options people in a situation like yours "
    "typically have. It never gives **legal advice**: it won't tell you what you should do in your case. That's "
    "because the right choice depends on details only a lawyer or legal clinic can look at properly, and because "
    "in Ontario, giving legal advice is the job of licensed lawyers and paralegals.\n\n"
    "So instead of \"you should file a complaint\", The Bridge says \"the law says...\" and \"people in this "
    "situation can...\". For serious situations (criminal charges, immigration, a court date that's already set, "
    "family and custody matters, or when it isn't sure), it shows a box pointing to a professional and free help. "
    "If someone may be in danger, it says to call 911 first."
)

# ---- The laws ---------------------------------------------------------------
st.write("")
st.markdown("### The laws it covers")
counts = section_counts()
saved = {law["name"]: law for law in load_saved_laws()}
for tab, names in zip(st.tabs(list(GROUPS)), GROUPS.values()):
    with tab:
        for column, (name, info) in grid((n, LAWS[n]) for n in names):
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

# ---- How The Bridge checks itself ------------------------------------------
st.write("")
st.markdown("### How The Bridge checks itself")
st.markdown(
    """
- **An AI judge.** A set of test questions, each with an answer key written from the law text, is run through
  The Bridge. A separate AI judge grades every answer as correct, wrong, or made up (stating law that isn't there).
- **A citation checker.** For every section an answer cites, it checks that the section exists and actually says
  what the answer claims.
- **A confidence score (semantic entropy).** The Bridge asks itself the same question 5 times, from the same law
  sections, and compares the answers by meaning. If they all agree, it's confident. If they disagree, it's
  probably guessing. You can run this yourself with the **How sure is this?** button under any answer; a low score
  shows the "talk to a professional" box.
- **You.** Every answer has a **Flag this answer** button. Flagged answers are saved with the question so they can
  be checked against the law and used to improve the search.
"""
)

# ---- Test results (numbers copied exactly from the files in results/) -------
st.write("")
st.markdown("### Test results")
st.markdown("**Latest run: November 23, 2026**, with all " + number_word(len(LAWS)) + " Acts and the new warmer tone")
a, b, c = st.columns(3)
a.metric("Test questions answered correctly", "35 / 37", help="results/eval_2026-11-23_181903_warm-tone")
b.metric("Answers graded as made-up law", "1", help="See the note below.")
c.metric("Out-of-scope questions declined", "5 / 5", help="Questions about laws The Bridge doesn't cover, "
         "such as criminal law, divorce, tax and immigration.")
st.caption(
    "The one answer graded as made up was about a landlord's son moving in. Search missed the section on "
    "compensation (Residential Tenancies Act, s. 48.1), and the answer said it couldn't find a compensation rule. "
    "We think the judge was too strict, but we report the grade as it was given. Before the tone change, the same "
    "test scored 34 / 37 with none graded made up."
)
st.markdown("**First final run: November 21, 2026**, on the original three laws (renting, work and buying)")
a, b, c = st.columns(3)
a.metric("Test questions answered correctly", "33 / 35", help="results/eval_2026-11-21_125426_final")
b.metric("Answers that made up law", "0")
c.metric("Out-of-scope questions declined", "6 / 6")
st.markdown(
    "When The Bridge gets something wrong, it's usually because search missed a section, and it says it couldn't "
    "find the rule rather than guessing. Full results are in the project's "
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

# ---- Where to get more help -------------------------------------------------
st.write("")
st.markdown("### Where to get more help")
st.markdown("Free and low-cost legal help in Ontario. Every link was checked on the organization's own website "
            "(November 2026). **If you're in immediate danger, call 911.**")
for column, (name, what, url, phone) in grid(FREE_HELP):
    with column, st.container(border=True):
        st.markdown(f"**[{name}]({url})**  \n{what}" + (f"  \nPhone: {phone}" if phone else ""))

# ---- Limitations ------------------------------------------------------------
st.write("")
st.markdown("### Limitations")
st.markdown(
    f"""
- **Legal information, not legal advice.** It explains what the law says; it can't tell you what to do in your case.
- **Translations are unofficial.** If you write in another language, the answer is translated, but the law text and citations are in English.
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

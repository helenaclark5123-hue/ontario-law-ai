"""Shared look and helpers for every page of the website."""

import json
from datetime import datetime

import streamlit as st

from get_laws import load_saved_laws
from make_chunks import CHUNKS_FILE
from update_laws import STATUS_FILE

# Photos are served from static/ (see .streamlit/config.toml); credits are in
# static/photo_credits.json and shown on the How it works page.
STATIC = "app/static"

# Plain-English topic, short description, photo and example questions per Act.
LAWS = {
    "Residential Tenancies Act, 2006": {
        "topic": "Renting",
        "photo": f"{STATIC}/renting.jpg",
        "about": "Rent increases, evictions, repairs, deposits and your landlord entering your home.",
        "examples": [
            "My landlord is trying to kick me out. What are my rights?",
            "Can my landlord raise my rent whenever they want?",
        ],
    },
    "Employment Standards Act, 2000": {
        "topic": "Work",
        "photo": f"{STATIC}/work.jpg",
        "about": "Hours, breaks, overtime, vacation, sick days, and being fired or laid off.",
        "examples": [
            "My boss wants me to work a 13-hour shift. Is that allowed?",
            "I got fired without warning. Do they owe me anything?",
        ],
    },
    "Consumer Protection Act, 2002": {
        "topic": "Buying things",
        "photo": f"{STATIC}/buying.jpg",
        "about": "Cancelling contracts, door-to-door sales, gym memberships, estimates and refunds.",
        "examples": [
            "Someone sold me something at my door yesterday and I want to cancel.",
            "A mechanic charged me way more than his estimate. What can I do?",
        ],
    },
    "Occupational Health and Safety Act": {
        "topic": "Workplace safety",
        "photo": f"{STATIC}/safety.jpg",
        "about": "Refusing unsafe work, safety training, injuries, and workplace harassment and violence.",
        "examples": [
            "Can I refuse to do a job I think is dangerous?",
            "My manager keeps harassing me at work. What does my employer have to do?",
        ],
    },
    "Highway Traffic Act": {
        "topic": "Driving",
        "photo": f"{STATIC}/driving.jpg",
        "about": "Speeding, licences and suspensions, seatbelts, phones while driving, and collisions.",
        "examples": [
            "What happens if I get caught speeding 50 km/h over the limit?",
            "Is it illegal to hold my phone while I'm stopped at a red light?",
        ],
    },
    "Human Rights Code": {
        "topic": "Human rights",
        "photo": f"{STATIC}/human-rights.jpg",
        "about": "Discrimination and harassment at work, in housing and in services, and accommodating disabilities.",
        "examples": [
            "My landlord won't rent to me because I have kids. Is that legal?",
            "My employer won't adjust my duties for my disability. What are my rights?",
        ],
    },
    "Workplace Safety and Insurance Act, 1997": {
        "topic": "Workplace injuries",
        "photo": f"{STATIC}/injured-worker.jpg",
        "about": "WSIB benefits after a workplace injury, reporting deadlines, lost wages and returning to work.",
        "examples": [
            "I hurt my back at work. Can I get paid while I recover?",
            "How long do I have to report a workplace injury?",
        ],
    },
    "Family Law Act": {
        "topic": "Family law",
        "photo": f"{STATIC}/family.jpg",
        "about": "Splitting property after separation, the family home, spousal support and child support.",
        "examples": [
            "We're separating. Do we split everything 50/50?",
            "How is child support worked out in Ontario?",
        ],
    },
    "Ontario Works Act, 1997": {
        "topic": "Ontario Works",
        "photo": f"{STATIC}/ontario-works.jpg",
        "about": "Financial and employment help for people in need: who qualifies, obligations and appeals.",
        "examples": [
            "Who can get Ontario Works?",
            "My Ontario Works was cut off. Can I appeal?",
        ],
    },
    "Ontario Disability Support Program Act, 1997": {
        "topic": "Disability support",
        "photo": f"{STATIC}/disability.jpg",
        "about": "ODSP income support for people with disabilities: who qualifies, assets and appeals.",
        "examples": [
            "How do I qualify for ODSP?",
            "Can I work part-time and still get ODSP?",
        ],
    },
    "Children's Law Reform Act": {
        "topic": "Custody and parenting",
        "photo": f"{STATIC}/custody.jpg",
        "about": "Decision-making for children, parenting time, where a child lives, and moving with a child.",
        "examples": [
            "We're separating. Who decides where the kids live?",
            "Can my ex move to another city with our child?",
        ],
    },
    "Payday Loans Act, 2008": {
        "topic": "Payday loans",
        "photo": f"{STATIC}/payday.jpg",
        "about": "The cost of borrowing, cancelling a payday loan, and what lenders can't do.",
        "examples": [
            "I took out a payday loan yesterday. Can I still cancel it?",
            "How much can a payday lender charge me?",
        ],
    },
    "Collection and Debt Settlement Services Act": {
        "topic": "Debt collectors",
        "photo": f"{STATIC}/debt.jpg",
        "about": "When and how collection agencies can contact you, and what they're not allowed to do.",
        "examples": [
            "Is a debt collector allowed to call me at work?",
            "A collection agency keeps calling me late at night. Is that allowed?",
        ],
    },
    "Condominium Act, 1998": {
        "topic": "Condos",
        "photo": f"{STATIC}/condos.jpg",
        "about": "Condo fees, the board and owners' meetings, rules, records, and disputes.",
        "examples": [
            "Can my condo board raise my fees?",
            "How do I get a copy of my condo's records?",
        ],
    },
    "Trespass to Property Act": {
        "topic": "Trespassing",
        "photo": f"{STATIC}/trespass.jpg",
        "about": "When you can be told to leave a property, signs, and fines for trespassing.",
        "examples": [
            "Can a store kick me out and ban me?",
            "What's the fine for trespassing in Ontario?",
        ],
    },
    "Liquor Licence and Control Act, 2019": {
        "topic": "Alcohol",
        "photo": f"{STATIC}/alcohol.jpg",
        "about": "The drinking age, where you can drink, and rules for selling and serving alcohol.",
        "examples": [
            "What's the legal drinking age in Ontario?",
            "Can I drink alcohol in a public park?",
        ],
    },
    "Cannabis Control Act, 2017": {
        "topic": "Cannabis",
        "photo": f"{STATIC}/cannabis.jpg",
        "about": "Age limits, where you can carry and use cannabis, and in cars.",
        "examples": [
            "How old do you have to be to buy weed in Ontario?",
            "Can I have cannabis in my car?",
        ],
    },
    'Education Act': {
        "topic": 'School',
        "photo": f"{STATIC}/school.jpg",
        "about": "Suspensions and expulsions, attending school, special education, and parents' rights.",
        "examples": [
            'My son got suspended. Can we appeal?',
            'Until what age do kids have to go to school in Ontario?',
        ],
    },
    'Health Care Consent Act, 1996': {
        "topic": 'Consent to treatment',
        "photo": f"{STATIC}/consent.jpg",
        "about": "Agreeing to or refusing treatment, capacity, and who decides for someone who can't.",
        "examples": [
            'Can a doctor treat me without my consent?',
            "Who makes medical decisions for my mom if she can't?",
        ],
    },
    'Mental Health Act': {
        "topic": 'Mental health',
        "photo": f"{STATIC}/mental-health.jpg",
        "about": "Psychiatric assessment, involuntary admission, and patients' rights to a hearing.",
        "examples": [
            'Can a hospital keep me against my will for mental health?',
            'How long can someone be held for a psychiatric assessment?',
        ],
    },
    'Personal Health Information Protection Act, 2004': {
        "topic": 'Health records',
        "photo": f"{STATIC}/health-records.jpg",
        "about": 'Getting your medical records, correcting them, and who can see your health information.',
        "examples": [
            'How do I get a copy of my medical records?',
            'Can my doctor share my health information without asking me?',
        ],
    },
    'Provincial Offences Act': {
        "topic": 'Tickets and fines',
        "photo": f"{STATIC}/tickets.jpg",
        "about": 'Fighting a ticket, deadlines to respond, trials, and paying fines.',
        "examples": [
            'I got a ticket. How do I fight it?',
            "What happens if I don't pay a ticket?",
        ],
    },
    'Courts of Justice Act': {
        "topic": 'Small claims court',
        "photo": f"{STATIC}/small-claims.jpg",
        "about": 'The courts of Ontario, small claims court and its money limit, and interest on judgments.',
        "examples": [
            'How much can I sue for in small claims court?',
            'Someone owes me $5,000. Which court do I go to?',
        ],
    },
    "Dog Owners' Liability Act": {
        "topic": 'Dog bites',
        "photo": f"{STATIC}/dogs.jpg",
        "about": 'Who is responsible when a dog bites or attacks, and court orders about dangerous dogs.',
        "examples": [
            "My neighbour's dog bit me. Is the owner responsible?",
            'What can happen to a dog that attacks someone?',
        ],
    },
    'Smoke-Free Ontario Act, 2017': {
        "topic": 'Smoking and vaping',
        "photo": f"{STATIC}/smoking.jpg",
        "about": 'The age to buy tobacco and vapes, and where smoking and vaping are banned.',
        "examples": [
            'How old do you have to be to buy a vape in Ontario?',
            'Can I smoke on a restaurant patio?',
        ],
    },
    'Child, Youth and Family Services Act, 2017': {
        "topic": 'Child protection',
        "photo": f"{STATIC}/child-protection.jpg",
        "about": "When children's aid can step in, a child's rights in care, and youth services.",
        "examples": [
            "When can children's aid take a child from their home?",
            'Do I have to report it if I think a child is being abused?',
        ],
    },
    'Fixing Long-Term Care Act, 2021': {
        "topic": 'Long-term care',
        "photo": f"{STATIC}/long-term-care.jpg",
        "about": "Residents' rights in long-term care homes, care standards, and making complaints.",
        "examples": [
            'What rights does my grandmother have in a long-term care home?',
            'How do I complain about care in a nursing home?',
        ],
    },
}

# Topic groups for the tabs on the Home and How it works pages.
GROUPS = {
    "Housing": ["Residential Tenancies Act, 2006", "Condominium Act, 1998", "Trespass to Property Act"],
    "Work": ["Employment Standards Act, 2000", "Occupational Health and Safety Act", "Workplace Safety and Insurance Act, 1997"],
    "Money": ["Consumer Protection Act, 2002", "Payday Loans Act, 2008", "Collection and Debt Settlement Services Act"],
    "Family": ["Family Law Act", "Children's Law Reform Act", "Child, Youth and Family Services Act, 2017"],
    "Health": ["Health Care Consent Act, 1996", "Mental Health Act", "Personal Health Information Protection Act, 2004",
               "Fixing Long-Term Care Act, 2021"],
    "Benefits": ["Ontario Works Act, 1997", "Ontario Disability Support Program Act, 1997"],
    "Rights and school": ["Human Rights Code", "Education Act"],
    "Driving and court": ["Highway Traffic Act", "Provincial Offences Act", "Courts of Justice Act"],
    "Everyday rules": ["Liquor Licence and Control Act, 2019", "Cannabis Control Act, 2017", "Smoke-Free Ontario Act, 2017",
                       "Dog Owners' Liability Act"],
}

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

:root {
    --navy: #0B1424; --panel: #111D33; --panel-2: #14223A; --line: #24344F;
    --text: #E6EBF2; --muted: #9AA7BA; --red: #D52B1E; --red-soft: #F2A39B;
}
html, body, [class*="css"], .stMarkdown, .stTextInput input, button, textarea {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
h1, h2, h3, h4, .serif { font-family: 'Source Serif 4', Georgia, serif !important; letter-spacing: -0.01em; color: #FFFFFF; }
.block-container { padding-top: 3.5rem; padding-bottom: 3rem; max-width: 1080px; }
[data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], #MainMenu { display: none; }
a { color: var(--red-soft) !important; }

/* Small uppercase label above headings, with a red rule */
.eyebrow {
    text-transform: uppercase; letter-spacing: .14em; font-size: .74rem; font-weight: 600;
    color: var(--red-soft); margin-bottom: .6rem; display: flex; align-items: center; gap: .6rem;
}
.eyebrow::before { content: ""; width: 28px; height: 2px; background: var(--red); display: inline-block; }
.muted { color: var(--muted); }

/* Home: photo hero */
.hero {
    position: relative; border-radius: 18px; overflow: hidden; margin: .5rem 0 0;
    padding: 4.5rem 3rem 4rem; min-height: 420px;
    background: linear-gradient(90deg, rgba(11,20,36,.96) 0%, rgba(11,20,36,.82) 45%, rgba(11,20,36,.25) 100%),
                url('app/static/hero-skyline.jpg') center 35% / cover no-repeat;
    border: 1px solid var(--line);
}
.hero h1 { font-size: 3.2rem !important; line-height: 1.07; margin: 0 0 1.1rem; padding: 0; max-width: 620px; }
.hero p.lead { font-size: 1.15rem; color: #C9D2DF; max-width: 540px; line-height: 1.6; margin: 0; }
.flag-line { display: flex; align-items: center; gap: .6rem; margin-bottom: 1.2rem; }
.flag-line img { height: 18px; border-radius: 2px; box-shadow: 0 0 0 1px rgba(255,255,255,.15); }
.flag-line span { text-transform: uppercase; letter-spacing: .14em; font-size: .74rem; font-weight: 600; color: #FFFFFF; }

/* Page header with photo (How it works) */
.page-hero {
    border-radius: 18px; overflow: hidden; padding: 3.2rem 2.6rem; margin-bottom: 2rem;
    border: 1px solid var(--line);
}
.page-hero h1 { font-size: 2.6rem !important; margin: 0 0 .6rem; padding: 0; }
.page-hero p { color: #C9D2DF; font-size: 1.08rem; max-width: 620px; margin: 0; line-height: 1.6; }

/* Trust strip */
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--line);
         border: 1px solid var(--line); border-radius: 14px; overflow: hidden; margin: 2.2rem 0 3.2rem; }
.stat { background: var(--panel); padding: 1.2rem 1.3rem; }
.stat b { display: block; font-family: 'Source Serif 4', Georgia, serif; font-size: 1.55rem; color: #FFFFFF; }
.stat span { font-size: .85rem; color: var(--muted); }

.section-title { font-size: 1.9rem !important; margin: 0 0 .3rem; padding: 0; }

/* Cards (bordered containers named "card-...") */
[class*="st-key-card-"] {
    background: var(--panel); border-color: var(--line) !important; border-radius: 16px !important;
    padding: 0 0 1.1rem !important; overflow: hidden;
}
.card-photo { height: 170px; background-size: cover; background-position: center; margin-bottom: 1rem; }
.card-body { padding: 0 1.25rem; margin-bottom: .8rem; }
.card-title { font-family: 'Source Serif 4', Georgia, serif; font-size: 1.35rem; font-weight: 700; color: #FFFFFF; }
.card-law { font-size: .78rem; color: var(--red-soft); font-weight: 600; margin: .2rem 0 .6rem; letter-spacing: .02em; }
.card-text { font-size: .93rem; color: #C3CCD9; line-height: 1.55; }
[class*="st-key-card-"] [data-testid="stElementContainer"]:has(button),
[class*="st-key-card-"] [data-testid="stElementContainer"]:has(a) { padding: 0 1.25rem; }
/* Example questions inside cards look like links */
[class*="st-key-card-"] [data-testid="stBaseButton-tertiary"] {
    justify-content: flex-start; text-align: left; color: #FFFFFF; padding: .2rem 0; min-height: 0;
}
[class*="st-key-card-"] [data-testid="stBaseButton-tertiary"] p { text-align: left; font-size: .9rem; }
[class*="st-key-card-"] [data-testid="stBaseButton-tertiary"]:hover { color: var(--red-soft); text-decoration: underline; }

/* Numbered steps */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem; margin-top: 1rem; }
.step { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 1.4rem; }
.step-num { font-family: 'Source Serif 4', Georgia, serif; font-size: 2rem; font-weight: 700; color: var(--red);
            line-height: 1; margin-bottom: .7rem; }
.step b { display: block; color: #FFFFFF; margin-bottom: .35rem; }
.step span { font-size: .92rem; color: #C3CCD9; line-height: 1.55; }

/* Chat */
/* Like Claude: the assistant writes on the page itself, your messages sit in a
   rounded bubble on the right, and there are no avatars. */
[data-testid="stChatMessage"] { background: transparent; border: 0; padding: .4rem 0; gap: 0; }
[data-testid^="stChatMessageAvatar"] { display: none; }
[data-testid="stChatMessage"]:has(.user-msg) {
    background: #1E2F4D; border-radius: 20px 20px 6px 20px; padding: .7rem 1.1rem;
    width: fit-content; max-width: 80%; margin: 1.2rem 0 .6rem auto;
}
[data-testid="stChatMessage"]:has(.user-msg) p { margin: 0; }
[data-testid="stChatMessageContent"] { line-height: 1.7; }
/* While it works: a pulsing red dot and the current step */
.thinking { display: flex; align-items: center; gap: .6rem; color: var(--muted); font-size: .92rem;
            padding: .3rem 0; animation: fade 1.6s ease-in-out infinite; }
.thinking .dot { width: .55rem; height: .55rem; border-radius: 50%; background: var(--red);
                 animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { transform: scale(.7); opacity: .5; } 50% { transform: scale(1.15); opacity: 1; } }
@keyframes fade { 0%, 100% { opacity: .75; } 50% { opacity: 1; } }
/* Don't grey out the page while an answer is being written */
[data-stale="true"], .stale-element { opacity: 1 !important; transition: none !important; }
.searched { color: var(--muted); font-size: .8rem; font-style: italic; margin: 0 0 .5rem; }
.law-title { font-weight: 600; color: #FFFFFF; margin-top: .6rem; }
.chips { display: flex; flex-wrap: wrap; gap: .45rem; margin-top: .7rem; }
.chip { border: 1px solid var(--line); border-radius: 999px; padding: .2rem .75rem;
        font-size: .8rem; color: #C3CCD9; white-space: nowrap; background: var(--panel); }

/* Footer */
.footer { margin-top: 3.5rem; padding-top: 1.3rem; border-top: 1px solid var(--line);
          color: var(--muted); font-size: .82rem; line-height: 1.65; }

/* Phones */
@media (max-width: 640px) {
    .hero { padding: 2.6rem 1.4rem 2.4rem; min-height: 0;
            background: linear-gradient(180deg, rgba(11,20,36,.7) 0%, rgba(11,20,36,.95) 70%),
                        url('app/static/hero-skyline.jpg') center / cover no-repeat; }
    .hero h1 { font-size: 2.2rem !important; }
    .hero p.lead { font-size: 1.02rem; }
    .page-hero { padding: 2.2rem 1.4rem; }
    .page-hero h1 { font-size: 2rem !important; }
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


def number_word(n):
    """10 -> "ten", for sentences like "the ten Acts"."""
    words = "zero one two three four five six seven eight nine ten eleven twelve".split()
    return words[n] if n < len(words) else str(n)


def grid(items, per_row=3):
    """Lay items out in rows of `per_row` columns; yields (column, item)."""
    items = list(items)
    for start in range(0, len(items), per_row):
        columns = st.columns(per_row, gap="medium")
        for column, item in zip(columns, items[start:start + per_row]):
            yield column, item


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
          Photos from Wikimedia Commons; credits on the How it works page.
        </div>
        """,
        unsafe_allow_html=True,
    )

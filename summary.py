""""Get ready for a lawyer": turn a conversation into a one-page PDF.

The PDF has:
  1. What happened, in the person's own words (their messages, unchanged)
  2. The laws that apply: each section cited in the answers, with a one-line
     plain-language note on what it says (written from the section's text)
  3. Options the law mentions (only ones the answers already described)
  4. Questions to ask a lawyer or legal clinic

It is legal information, not advice: the AI is told not to recommend anything.
"""

import json
import re
from datetime import date
from pathlib import Path

import anthropic
from fpdf import FPDF

from answer import DISCLAIMER, MODEL
from citations import extract_citations

FONTS = Path(__file__).parent / "fonts"
MAX_LAWS = 6  # keeps the sheet to about one page

SUMMARY_PROMPT = """You help someone in Ontario prepare to talk to a lawyer or community legal clinic about their situation. You get a conversation they had with The Bridge (a legal information assistant) and the text of the law sections it cited.

Write a short preparation sheet as JSON with these keys:
- "situation": 2 to 4 short sentences describing what happened, using only facts the person said. Write it in the first person ("My landlord..."), as the person would tell it.
- "laws": a list with one item per law section given to you, in the same order: {"ref": the ref exactly as given, "note": one short plain-language sentence (at most 20 words) saying what that section says, based only on its text}.
- "options": up to 4 short points describing options the assistant's answers said the law provides, phrased as "The law allows..." or "People in this situation can...". Only include options stated in the answers. Never say what the person should do.
- "questions": 3 to 5 short questions the person could ask a lawyer or legal clinic about their situation.

This is legal information, not legal advice: never recommend a course of action. Write in the same language the person used. Reply with only the JSON."""


def cited_sections(messages, lookup):
    """Every (law, section) cited in the assistant's replies that we have text for."""
    found = []
    for m in messages:
        if m["role"] == "assistant" and not m.get("error"):
            for c in extract_citations(m["content"], None):
                key = (c["law"], c["section"])
                if key in lookup and key not in found:
                    found.append(key)
    return found


def build_summary(messages, lookup):
    """Ask Claude to write the preparation sheet. Returns a dict."""
    sections = cited_sections(messages, lookup)[:MAX_LAWS]
    transcript = "\n\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages if not m.get("error")
    )
    law_text = "\n\n".join(
        f'<section ref="{law}, s. {number}">\n{lookup[(law, number)]["text"][:3000]}\n</section>'
        for law, number in sections
    )
    response = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=3000,
        output_config={"effort": "low"},
        system=SUMMARY_PROMPT,
        messages=[{"role": "user", "content": f"<conversation>\n{transcript}\n</conversation>\n\n"
                                              f"<sections>\n{law_text}\n</sections>"}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    match = re.search(r"\{.*\}", text, re.S)
    data = json.loads(match.group(0)) if match else {}
    notes = {item.get("ref"): item.get("note", "") for item in data.get("laws", []) if isinstance(item, dict)}
    return {
        "situation": data.get("situation", ""),
        "laws": [(f"{law}, s. {n}", lookup[(law, n)]["heading"], notes.get(f"{law}, s. {n}", ""),
                  lookup[(law, n)]["url"]) for law, n in sections],
        "options": [str(o) for o in data.get("options", [])],
        "questions": [str(q) for q in data.get("questions", [])],
    }


class SummaryPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("DejaVu", size=7.5)
        self.set_text_color(110, 110, 110)
        self.multi_cell(0, 3.6, f"{DISCLAIMER}  The Bridge · page {self.page_no()}", align="C")


def make_pdf(summary, messages):
    """Lay out the summary on A4/letter-size pages and return the PDF bytes."""
    pdf = SummaryPDF(format="Letter")
    pdf.add_font("DejaVu", "", str(FONTS / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()

    def heading(text):
        pdf.ln(2)
        pdf.set_font("DejaVu", "B", 11.5)
        pdf.set_text_color(180, 20, 30)
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(25, 25, 25)

    def para(text, size=9.5, bold=False, indent=0):
        pdf.set_font("DejaVu", "B" if bold else "", size)
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(0, size * 0.48, text, align="L", new_x="LMARGIN", new_y="NEXT")

    def bullets(items):
        for item in items:
            para(f"•  {item}", indent=2)
            pdf.ln(0.4)

    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(25, 25, 25)
    pdf.cell(0, 9, "Getting ready to talk to a lawyer", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(0, 5, f"Prepared with The Bridge on {date.today():%B %d, %Y}. Bring this to a lawyer, "
                   "paralegal or legal clinic.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(25, 25, 25)

    heading("What happened")
    if summary["situation"]:
        para(summary["situation"])
        pdf.ln(1.5)
    para("In your words:", size=9, bold=True)
    for m in messages:
        if m["role"] == "user":
            para(f"“{m['content']}”", size=9, indent=2)
            pdf.ln(0.8)

    heading("The laws that apply")
    if not summary["laws"]:
        para("The answers didn't cite any law sections.")
    for ref, title, note, url in summary["laws"]:
        para(ref + (f" ({title})" if title else ""), bold=True)
        if note:
            para(note, indent=2)
        pdf.set_text_color(90, 90, 90)
        para(f"Official text: {url}", size=7.5, indent=2)
        pdf.set_text_color(25, 25, 25)
        pdf.ln(0.8)

    if summary["options"]:
        heading("Options the law mentions")
        bullets(summary["options"])

    if summary["questions"]:
        heading("Questions to ask a lawyer or clinic")
        bullets(summary["questions"])

    pdf.ln(2)
    pdf.set_font("DejaVu", "", 8.5)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 4.2, "This sheet explains what the law says, based on an unofficial copy of Ontario law. "
                           "It is not legal advice and may be incomplete. Always check the official text on "
                           "ontario.ca/laws.")
    return bytes(pdf.output())

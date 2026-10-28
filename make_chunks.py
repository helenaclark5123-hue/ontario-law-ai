"""Stage 2: Split each saved law into chunks, one per numbered section.

Each chunk keeps the law's name, the section number, the section heading and
the source URL. Long sections are split into smaller parts at subsection
boundaries like "(3)", but every part keeps its section number.
"""

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CHUNKS_FILE = DATA_DIR / "chunks.json"

# Sections longer than this (in characters) get split into parts.
# ~1200 characters is roughly 250-300 words, which suits small embedding models.
MAX_CHARS = 1200

# A line that starts a new subsection, e.g. "(3) The notice shall..."
SUBSECTION_START = re.compile(r"^\(\d+(\.\d+)?\)")

# A line that starts a section, e.g. "116 (1) A landlord..." or a repealed
# range like "65.1-65.11 Repealed". group(1) is the section number.
SECTION_START = re.compile(r"^(\d+(?:\.\d+)*)(?:-[\d.]+)? ")

# How many sections ahead we may skip when a section has no line of its own.
LOOKAHEAD = 25


def find_headings(full_text, section_numbers):
    """Find the heading and Part for each section by reading the full text.

    In the full text, a section looks like:
        ## part vii general rules governing rent
        ### Notice of rent increase required
        116 (1) A landlord shall not increase the rent...

    We walk through the sections in order, so a line that merely starts with
    a number (like a year) isn't mistaken for a section. Some sections never
    get their own line (e.g. a repealed range "65.1-65.11 Repealed"), so we
    allow skipping a few sections ahead.
    """
    headings, parts = {}, {}
    current_part, last_heading = "", ""
    remaining = list(section_numbers)

    for line in full_text.splitlines():
        if line.startswith("## "):
            current_part = line[3:].strip()
        elif line.startswith("### "):
            last_heading = line[4:].strip()
        else:
            match = SECTION_START.match(line)
            if match and match.group(1) in remaining[:LOOKAHEAD]:
                skip_to = remaining.index(match.group(1))
                number = remaining[skip_to]
                del remaining[: skip_to + 1]
                headings[number] = last_heading
                parts[number] = current_part.title()
    return headings, parts


def is_empty(text):
    """Repealed or blank sections have no law left in them."""
    t = text.strip()
    return t == "[blank]" or (t.startswith("Repealed") and len(t) < 120)


def split_long(text):
    """Split a long section into parts of at most MAX_CHARS.

    We only cut between lines (never mid-sentence), and prefer to cut right
    before a new subsection like "(4)".
    """
    if len(text) <= MAX_CHARS:
        return [text]

    # Group lines into subsections.
    units = []
    for line in text.split("\n"):
        if SUBSECTION_START.match(line) or not units:
            units.append([line])
        else:
            units[-1].append(line)

    # A subsection that is itself too long gets broken into its lines.
    pieces = []
    for unit in units:
        joined = "\n".join(unit)
        pieces.extend(unit if len(joined) > MAX_CHARS else [joined])

    # Pack pieces together until a part would get too long.
    parts, current = [], ""
    for piece in pieces:
        if current and len(current) + 1 + len(piece) > MAX_CHARS:
            parts.append(current)
            current = piece
        else:
            current = f"{current}\n{piece}" if current else piece
    if current:
        parts.append(current)
    return parts


def chunk_law(law):
    """Turn one saved law into a list of chunks."""
    sections = law["sections"]
    headings, law_parts = find_headings(law["full_text"], list(sections))
    chunks = []

    for number, text in sections.items():
        if is_empty(text):
            continue
        heading = headings.get(number, "")
        pieces = split_long(text.strip())

        for i, piece in enumerate(pieces, start=1):
            label = f"{law['name']}, s. {number}"
            if heading:
                label += f" – {heading}"
            if len(pieces) > 1:
                label += f" (part {i} of {len(pieces)})"

            chunks.append({
                "id": f"{law['citation']} s{number} p{i}",
                "law": law["name"],
                "citation": law["citation"],
                "section": number,
                "heading": heading,
                "law_part": law_parts.get(number, ""),
                "part": i,
                "total_parts": len(pieces),
                "url": law["url"],
                # The text we search over and show the AI: a label line so the
                # chunk makes sense on its own, then the law's own words.
                "text": f"{label}\n{piece}",
                # A fingerprint of the text, so Stage 6 can spot changes.
                "hash": hashlib.sha256(piece.encode()).hexdigest()[:16],
            })
    return chunks


def main():
    all_chunks = []
    for path in sorted(DATA_DIR.glob("*.json")):
        if path == CHUNKS_FILE:
            continue
        law = json.loads(path.read_text())
        chunks = chunk_law(law)
        all_chunks.extend(chunks)

    CHUNKS_FILE.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))

    print(f"Saved {len(all_chunks)} chunks to {CHUNKS_FILE.name}\n")
    print(f"{'Law':<36}{'Sections':>9}{'Chunks':>8}{'No heading':>12}")
    for name, count in Counter(c["law"] for c in all_chunks).items():
        law_chunks = [c for c in all_chunks if c["law"] == name]
        n_sections = len({c["section"] for c in law_chunks})
        no_heading = len({c["section"] for c in law_chunks if not c["heading"]})
        print(f"{name:<36}{n_sections:>9}{count:>8}{no_heading:>12}")

    print("\n3 random chunks:")
    for c in random.sample(all_chunks, 3):
        print("=" * 70)
        print(f"[{c['id']}]  {c['law_part']}  {c['url']}")
        print("-" * 70)
        print(c["text"])
    print("=" * 70)


if __name__ == "__main__":
    main()

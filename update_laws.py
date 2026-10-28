"""Stage 6: Keep the law database up to date (the self-updating twist).

Re-downloads the laws from the A2AJ dataset, chunks them the same way as
Stage 2, and compares every chunk with what is stored in the database:
  - changed sections are re-embedded (only those, not everything)
  - new sections are added
  - deleted sections are removed
Every check is written to logs/update_log.md, and logs/last_updated.json
records when the laws were last checked (shown at the top of the app).

    python update_laws.py           # check A2AJ for changes and apply them
    python update_laws.py --local   # make the database match the files in data/
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from get_laws import fetch_laws, load_saved_laws, save_law
from make_chunks import chunk_laws, save_chunks
from search import embed, get_collection, metadata_for

ROOT = Path(__file__).parent
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "update_log.md"
STATUS_FILE = LOG_DIR / "last_updated.json"


def describe(meta):
    """'Residential Tenancies Act, 2006, s. 116 (part 1 of 2)'"""
    part = f" (part {meta['part']} of {meta['total_parts']})" if meta["total_parts"] > 1 else ""
    return f"{meta['law']}, s. {meta['section']}{part}"


def sync(laws):
    """Make the database match these laws, touching only what changed.

    Returns a report of what was added, changed and removed.
    """
    new_chunks = chunk_laws(laws)
    new = {c["id"]: c for c in new_chunks}

    collection = get_collection()
    stored = collection.get(include=["metadatas", "documents"])
    old = {
        id_: {"meta": meta, "text": doc}
        for id_, meta, doc in zip(stored["ids"], stored["metadatas"], stored["documents"])
    }

    added = [i for i in new if i not in old]
    changed = [i for i in new if i in old and old[i]["text"] != new[i]["text"]]
    removed = [i for i in old if i not in new]

    # Re-embed only the chunks that are new or different.
    to_embed = [new[i] for i in added + changed]
    for start in range(0, len(to_embed), 64):
        group = to_embed[start:start + 64]
        collection.upsert(
            ids=[c["id"] for c in group],
            documents=[c["text"] for c in group],
            embeddings=embed([c["text"] for c in group]),
            metadatas=[metadata_for(c) for c in group],
        )
    if removed:
        collection.delete(ids=removed)

    save_chunks(new_chunks)

    return {
        "added": [describe(new[i]) for i in added],
        "changed": [
            {"where": describe(new[i]), "before": old[i]["text"], "after": new[i]["text"]}
            for i in changed
        ],
        "removed": [describe(old[i]["meta"]) for i in removed],
        "total_chunks": collection.count(),
    }


def write_log(report, source, laws):
    """Add a readable entry to logs/update_log.md and update the status file."""
    LOG_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")

    n_changes = len(report["added"]) + len(report["changed"]) + len(report["removed"])
    lines = [f"## {stamp} ({source})", ""]
    for law in laws:
        lines.append(f"- {law['name']}: A2AJ copy collected {law['scraped_timestamp'][:10]}")
    lines.append("")
    if n_changes == 0:
        lines.append("No changes: the database already matches.")
    else:
        lines.append(
            f"{len(report['changed'])} changed, {len(report['added'])} added, "
            f"{len(report['removed'])} removed."
        )
        for c in report["changed"]:
            lines += ["", f"### Changed: {c['where']}", "", "Before:", "",
                      "> " + c["before"].replace("\n", "\n> "), "", "After:", "",
                      "> " + c["after"].replace("\n", "\n> ")]
        if report["added"]:
            lines += ["", "### Added", ""] + [f"- {a}" for a in report["added"]]
        if report["removed"]:
            lines += ["", "### Removed", ""] + [f"- {r}" for r in report["removed"]]
    lines += ["", f"Database now holds {report['total_chunks']} chunks.", "", ""]

    with LOG_FILE.open("a") as f:
        f.write("\n".join(lines))

    status = json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}
    status["last_checked"] = now.isoformat(timespec="seconds")
    if n_changes:
        status["last_changed"] = now.isoformat(timespec="seconds")
    status["laws"] = {law["name"]: law["scraped_timestamp"] for law in laws}
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def update(source="A2AJ"):
    """Check for changes and apply them. source is 'A2AJ' or 'local files'."""
    if source == "A2AJ":
        laws = fetch_laws()
        for law in laws:
            save_law(law)
    else:
        laws = load_saved_laws()

    report = sync(laws)
    write_log(report, source, laws)
    return report


def print_report(report):
    if not (report["added"] or report["changed"] or report["removed"]):
        print("No changes: the database already matches.")
    for c in report["changed"]:
        print(f"CHANGED  {c['where']}")
    for a in report["added"]:
        print(f"ADDED    {a}")
    for r in report["removed"]:
        print(f"REMOVED  {r}")
    print(f"Database now holds {report['total_chunks']} chunks. Log: {LOG_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    source = "local files" if "--local" in sys.argv else "A2AJ"
    print(f"Checking for changes ({source})...")
    print_report(update(source))

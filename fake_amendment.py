"""Test the self-updating feature with a fake amendment.

1. Backs up data/ to backups/<date-time>/
2. Edits section 116 of my stored Residential Tenancies Act so it says a
   landlord only needs 30 days' notice for a rent increase (the real law
   says 90), and loads that fake text into the database.
3. Then you ask the app about rent-increase notice (it should say 30 days),
   run `python update_laws.py`, and ask again (it should say 90 days).

    python fake_amendment.py
"""

import shutil
from datetime import datetime
from pathlib import Path

from get_laws import DATA_DIR, load_saved_laws, save_law
from update_laws import sync

ROOT = Path(__file__).parent
LAW = "Residential Tenancies Act, 2006"
SECTION = "116"
REAL = "at least 90 days written notice"
FAKE = "at least 30 days written notice"


def main():
    # 1. Back up the data folder.
    backup = ROOT / "backups" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    shutil.copytree(DATA_DIR, backup)
    print(f"Backed up data/ to {backup.relative_to(ROOT)}")

    # 2. Change the stored copy of the law.
    laws = load_saved_laws()
    law = next(l for l in laws if l["name"] == LAW)
    text = law["sections"][SECTION]
    if REAL not in text:
        print(f"Section {SECTION} doesn't contain '{REAL}' (already faked?). Stopping.")
        return
    law["sections"][SECTION] = text.replace(REAL, FAKE)
    law["full_text"] = law["full_text"].replace(REAL, FAKE, 1)
    save_law(law)

    # Load the fake text into the database, as if this were the stored law.
    report = sync(laws)
    print(f"Faked {LAW}, s. {SECTION}: '{REAL}' -> '{FAKE}'")
    print(f"Database updated ({len(report['changed'])} chunk changed).")
    print("\nNow ask: 'How much notice does my landlord need to give before raising my rent?'")
    print("Then run: python update_laws.py   (it should find and fix s. 116)")


if __name__ == "__main__":
    main()

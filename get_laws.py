"""Stage 1: Download Ontario laws from the A2AJ dataset and save them to data/.

The A2AJ "canadian-laws" dataset (Osgoode Hall / TMU) has one file per
jurisdiction and type. We download the Ontario statutes and regulations files,
pick out our laws and the regulations made under them, and save each one as a
JSON file.
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import json
import re
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

DATA_DIR = Path(__file__).parent / "data"

# Exact English names as they appear in the dataset.
# Note: there is also a "Consumer Protection Act, 2023", but it is a newer
# replacement that is mostly not in force yet, so we use the 2002 Act.
LAWS = [
    "Residential Tenancies Act, 2006",
    "Employment Standards Act, 2000",
    "Consumer Protection Act, 2002",
    "Occupational Health and Safety Act",
    "Highway Traffic Act",
]

# Regulations made under those Acts that fill gaps the Acts leave (detailed
# rules, amounts and definitions). "name" is the short citation the assistant
# cites; "skip_schedules" leaves out long schedules (e.g. Reg. 619's lists of
# highway stretches) that would add noise to search.
REGULATIONS = [
    {"citation": "O Reg 516/06", "title": "General", "parent": "Residential Tenancies Act, 2006"},
    {"citation": "O Reg 290/98", "title": "Business Practices Permissible to Landlords in Selecting Prospective Tenants",
     "parent": "Residential Tenancies Act, 2006"},
    {"citation": "O Reg 285/01", "title": "When Work Deemed to be Performed, Exemptions and Special Rules",
     "parent": "Employment Standards Act, 2000"},
    {"citation": "O Reg 288/01", "title": "Termination and Severance of Employment", "parent": "Employment Standards Act, 2000"},
    {"citation": "O Reg 17/05", "title": "General", "parent": "Consumer Protection Act, 2002"},
    {"citation": "O Reg 297/13", "title": "Occupational Health and Safety Awareness and Training",
     "parent": "Occupational Health and Safety Act"},
    {"citation": "RRO 1990, Reg 851", "title": "Industrial Establishments", "parent": "Occupational Health and Safety Act"},
    {"citation": "O Reg 339/94", "title": "Demerit Point System", "parent": "Highway Traffic Act"},
    {"citation": "O Reg 455/07", "title": "Races, Contests and Stunts", "parent": "Highway Traffic Act"},
    {"citation": "RRO 1990, Reg 619", "title": "Speed Limits", "parent": "Highway Traffic Act", "skip_schedules": True},
    {"citation": "O Reg 340/94", "title": "Drivers' Licences", "parent": "Highway Traffic Act"},
]


def short_name(citation):
    """'O Reg 516/06' -> 'O. Reg. 516/06'; 'RRO 1990, Reg 619' -> 'R.R.O. 1990, Reg. 619'"""
    return citation.replace("RRO", "R.R.O.").replace("O Reg", "O. Reg.").replace(", Reg ", ", Reg. ")


for regulation in REGULATIONS:
    regulation["name"] = short_name(regulation["citation"])

# Every document in the database: the Acts, then the regulations.
ALL_NAMES = LAWS + [r["name"] for r in REGULATIONS]


def download_ontario(kind="LEGISLATION"):
    """Download the Ontario LEGISLATION (Acts) or REGULATIONS file as a table."""
    path = hf_hub_download(
        "a2aj/canadian-laws",
        f"{kind}-ON/train.parquet",
        repo_type="dataset",
        force_download=True,  # always fetch the latest version
    )
    df = pd.read_parquet(path)
    return df[df["dataset"] == f"{kind}-ON"]


def public_url(api_url):
    """Turn the dataset's API link into the normal ontario.ca/laws page link.

    e.g. .../api/v2/legislation/en/doc-search/statute/06r17
      -> https://www.ontario.ca/laws/statute/06r17
    (and .../regulation/060516 -> https://www.ontario.ca/laws/regulation/060516)
    """
    kind, code = api_url.rstrip("/").split("/")[-2:]
    return f"https://www.ontario.ca/laws/{kind}/{code}"


def file_name(law_name):
    """'Residential Tenancies Act, 2006' -> 'residential_tenancies_act_2006.json',
    'O. Reg. 516/06' -> 'o_reg_516_06.json'"""
    return re.sub(r"[^a-z0-9]+", "_", law_name.lower()).strip("_") + ".json"


def law_record(row, name):
    """One law or regulation from the dataset, as a dict."""
    return {
        "name": name,
        "citation": row["citation_en"],
        "url": public_url(row["source_url_en"]),
        "source_api_url": row["source_url_en"],
        "scraped_timestamp": row["scraped_timestamp_en"].isoformat(),
        "num_sections": int(row["num_sections_en"]),
        "full_text": row["unofficial_text_en"],
        # The dataset also gives the law already split by section number,
        # e.g. {"1": "...", "2": "..."}. We'll use this in Stage 2.
        "sections": json.loads(row["unofficial_sections_en"]),
    }


def fetch_laws():
    """Download the datasets and return our Acts and regulations as a list of dicts."""
    laws = []
    acts = download_ontario("LEGISLATION")
    for name in LAWS:
        rows = acts[acts["name_en"] == name]
        if rows.empty:
            print(f"!! Could not find '{name}' in the dataset")
            continue
        laws.append(law_record(rows.iloc[0], name))

    regulations = download_ontario("REGULATIONS")
    for reg in REGULATIONS:
        rows = regulations[regulations["citation_en"] == reg["citation"]]
        if rows.empty:
            print(f"!! Could not find '{reg['citation']}' in the dataset")
            continue
        law = law_record(rows.iloc[0], reg["name"])
        law["kind"] = "regulation"
        law["title"], law["parent"] = reg["title"], reg["parent"]
        # How the regulation is labelled in search results and for the AI.
        law["display"] = f"{reg['name']} ({reg['title']}), a regulation under the {reg['parent']}"
        if reg.get("skip_schedules"):
            law["sections"] = {k: v for k, v in law["sections"].items() if not k.startswith("Schedule")}
        laws.append(law)
    return laws


def save_law(law):
    """Save one law to data/<law name>.json and return the file path."""
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / file_name(law["name"])
    out.write_text(json.dumps(law, indent=2, ensure_ascii=False))
    return out


def load_saved_laws():
    """Read back the laws currently saved in data/."""
    return [json.loads((DATA_DIR / file_name(name)).read_text()) for name in ALL_NAMES]


def main():
    for law in fetch_laws():
        out = save_law(law)

        print("=" * 70)
        print(f"{law['name']}  ({law['citation']})")
        print(f"Saved to:      {out.relative_to(Path(__file__).parent)}")
        print(f"Official page: {law['url']}")
        print(f"Collected:     {law['scraped_timestamp']}")
        print(f"Sections:      {law['num_sections']}")
        print("-" * 70)
        print(law["full_text"][:500])
        print()


if __name__ == "__main__":
    main()

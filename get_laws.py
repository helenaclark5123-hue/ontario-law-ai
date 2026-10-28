"""Stage 1: Download Ontario laws from the A2AJ dataset and save them to data/.

The A2AJ "canadian-laws" dataset (Osgoode Hall / TMU) has one file per
jurisdiction. We only download the Ontario statutes file, pick out our laws,
and save each one as a JSON file.
"""

import quiet  # noqa: F401  (must come before the AI libraries)

import json
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
]


def download_ontario_laws():
    """Download the Ontario legislation file and return it as a table."""
    path = hf_hub_download(
        "a2aj/canadian-laws",
        "LEGISLATION-ON/train.parquet",
        repo_type="dataset",
        force_download=True,  # always fetch the latest version
    )
    df = pd.read_parquet(path)
    return df[df["dataset"] == "LEGISLATION-ON"]


def public_url(api_url):
    """Turn the dataset's API link into the normal ontario.ca/laws page link.

    e.g. .../api/v2/legislation/en/doc-search/statute/06r17
      -> https://www.ontario.ca/laws/statute/06r17
    """
    return "https://www.ontario.ca/laws/statute/" + api_url.rstrip("/").split("/")[-1]


def file_name(law_name):
    """'Residential Tenancies Act, 2006' -> 'residential_tenancies_act_2006.json'"""
    return law_name.lower().replace(",", "").replace(" ", "_") + ".json"


def fetch_laws():
    """Download the dataset and return our laws as a list of dicts."""
    df = download_ontario_laws()
    laws = []
    for name in LAWS:
        rows = df[df["name_en"] == name]
        if rows.empty:
            print(f"!! Could not find '{name}' in the dataset")
            continue
        row = rows.iloc[0]
        laws.append({
            "name": row["name_en"],
            "citation": row["citation_en"],
            "url": public_url(row["source_url_en"]),
            "source_api_url": row["source_url_en"],
            "scraped_timestamp": row["scraped_timestamp_en"].isoformat(),
            "num_sections": int(row["num_sections_en"]),
            "full_text": row["unofficial_text_en"],
            # The dataset also gives the law already split by section number,
            # e.g. {"1": "...", "2": "..."}. We'll use this in Stage 2.
            "sections": json.loads(row["unofficial_sections_en"]),
        })
    return laws


def save_law(law):
    """Save one law to data/<law name>.json and return the file path."""
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / file_name(law["name"])
    out.write_text(json.dumps(law, indent=2, ensure_ascii=False))
    return out


def load_saved_laws():
    """Read back the laws currently saved in data/."""
    return [json.loads((DATA_DIR / file_name(name)).read_text()) for name in LAWS]


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

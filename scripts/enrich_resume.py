"""Resume enrichment runner.

If `data/sites_enriched.json` exists, load it and continue enriching the remaining
items. Otherwise fall back to `data/sites.json` and run a full enrichment.

This script writes progress to `data/sites_enriched.json` and saves the final
index to `data/index_enriched.pkl` when finished.
"""

import json
import pathlib
import sys
from src.fetcher import enrich_sites
from src.indexer import HeritageIndexer

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

enriched_path = DATA_DIR / "sites_enriched.json"
base_path = DATA_DIR / "sites.json"

sites = None
if enriched_path.exists():
    print("Found existing enriched file:", enriched_path)
    with open(enriched_path, "r", encoding="utf-8") as f:
        sites = json.load(f)
    print(
        "Loaded",
        len(sites),
        "records from sites_enriched.json — continuing enrichment.",
    )
elif base_path.exists():
    print("No enriched file found, loading base sites.json", base_path)
    with open(base_path, "r", encoding="utf-8") as f:
        sites = json.load(f)
    print("Loaded", len(sites), "records — starting enrichment.")
else:
    print("No source file found (sites_enriched.json or sites.json). Exiting.")
    sys.exit(1)

out_path = str(enriched_path)
sites = enrich_sites(sites, save_every=50, out_path=out_path)
print("Enrichment finished — saved to", out_path)

# build index
idx = HeritageIndexer()
idx.fit(sites)
idx.save(str(DATA_DIR / "index_enriched.pkl"))
print("Saved enriched index to data/index_enriched.pkl")

# final persist
with open(enriched_path, "w", encoding="utf-8") as f:
    json.dump(sites, f, ensure_ascii=False, indent=2)
print("Done.")

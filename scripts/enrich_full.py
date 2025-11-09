"""Full enrichment runner.

Loads normalized sites (from data/sites.json or data/sites_from_rss.json),
follows links to scrape richer metadata for all records, writes progress to
`data/sites_enriched.json`, builds a TF-IDF index and saves it to
`data/index_enriched.pkl`.

This is a long-running script for the full dataset; it saves progress
incrementally so it can be restarted.
"""

import json
import pathlib
import sys
from src.fetcher import load_sites_from_rss, enrich_sites
from src.indexer import HeritageIndexer

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Try to load previously normalized JSON
candidates = [DATA_DIR / "sites.json", DATA_DIR / "sites_from_rss.json"]
sites = None
for p in candidates:
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            sites = json.load(f)
        print("Loaded sites from", p)
        break

if sites is None:
    # If we don't have normalized sites, try to read the RSS bundled with the repo
    rss_path = ROOT / "heritage_sites" / "sites.rss"
    if rss_path.exists():
        print("No normalized JSON found, parsing RSS", rss_path)
        sites = load_sites_from_rss(
            str(rss_path),
            save_raw_to=str(DATA_DIR / "sites.rss"),
            save_json_to=str(DATA_DIR / "sites.json"),
        )
    else:
        print("No source RSS or sites JSON found. Exiting.")
        sys.exit(1)

print("Total sites to enrich:", len(sites))

# Enrich and save to data/sites_enriched.json
out_path = str(DATA_DIR / "sites_enriched.json")
sites = enrich_sites(sites, save_every=50, out_path=out_path)
print("Enrichment complete. Saved to", out_path)

# Build TF-IDF index for enriched dataset
idx = HeritageIndexer()
idx.fit(sites)
idx.save(str(DATA_DIR / "index_enriched.pkl"))
print("Saved enriched index to data/index_enriched.pkl")

# also persist the enriched sites list for later use
with open(DATA_DIR / "sites_enriched.json", "w", encoding="utf-8") as f:
    json.dump(sites, f, ensure_ascii=False, indent=2)

print("All done.")

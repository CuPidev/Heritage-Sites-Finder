"""Enrich a sample of sites by following links and build an enriched index.

Writes:
 - data/sites_enriched.json
 - data/index_enriched.pkl

Run with PYTHONPATH pointing to the project root.
"""

import os
import json
from src.fetcher import load_sites_from_rss
from src.indexer import HeritageIndexer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

print("Working dir:", os.getcwd())

sites = load_sites_from_rss(
    "heritage_sites/sites.rss",
    save_raw_to="data/sites.rss",
    save_json_to="data/sites_enriched.json",
    max_sites=200,
    follow_links=True,
)

print("Enriched sites count:", len(sites))
with open("data/sites_enriched.json", "w", encoding="utf-8") as f:
    json.dump(sites, f, ensure_ascii=False, indent=2)

idx = HeritageIndexer()
idx.fit(sites)
idx.save("data/index_enriched.pkl")
print("Saved enriched index: data/index_enriched.pkl")

# quick diagnostic search
res = idx.search("castle in asia", top_k=10)
print('\nTOP-10 for "castle in asia":')
print(json.dumps(res, ensure_ascii=False, indent=2))

# show country metadata for those hits
id_to_doc = {d["id"]: d for d in idx.docs}
meta = [
    {
        "id": r["id"],
        "name": id_to_doc.get(r["id"], {}).get("name"),
        "country": id_to_doc.get(r["id"], {}).get("country"),
    }
    for r in res
]
print("\nMETADATA:")
print(json.dumps(meta, ensure_ascii=False, indent=2))

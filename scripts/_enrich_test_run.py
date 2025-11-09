from src.fetcher import enrich_sites
import json, pathlib, sys

p = pathlib.Path("data/sites.json")
if not p.exists():
    print("no data/sites.json")
    sys.exit(0)
sites = json.load(open(p, "r", encoding="utf-8"))
small = sites[:3]
enriched = enrich_sites(small, save_every=1, out_path="data/sites_enriched_test.json")
print("enriched_count=", len(enriched))
print(
    "sample country/continent:",
    enriched[0].get("country"),
    enriched[0].get("continent"),
)

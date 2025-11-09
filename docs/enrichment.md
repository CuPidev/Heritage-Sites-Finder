# Enrichment (scraping & metadata augmentation)

The project includes scripts to enrich the normalized RSS-derived records by following each site's link and scraping additional metadata (country, coordinates, and a best-effort continent tag).

Files and scripts

-   `src/fetcher.py` — core functions:

    -   `load_sites_from_rss(rss_path, save_raw_to, save_json_to, follow_links=False, max_sites=None)` — parses a local RSS XML and optionally follows links to scrape richer metadata.
    -   `enrich_sites(sites, save_every=50, out_path='data/sites_enriched.json')` — iterates and enriches a list of site dicts in-place, saving progress incrementally.

-   `scripts/enrich_full.py` — original full-run script that reads `data/sites.json` (or the included RSS), enriches everything, and saves `data/index_enriched.pkl`.
-   `scripts/enrich_resume.py` — resume runner: if `data/sites_enriched.json` exists, it loads and continues enrichment from there; otherwise falls back to `data/sites.json`.

Progress & restartability

-   The enrichment functions write snapshots to `data/sites_enriched.json` periodically (`save_every` default 50). This allows the process to be stopped and resumed safely.
-   When enrichment completes, the script builds and saves `data/index_enriched.pkl` which the API will prefer on startup.

Notes about scraping

-   The fetcher uses BeautifulSoup + lxml to parse site pages and employs several heuristics to locate "State Party" / "Country" labels and coordinate meta tags. Scraping can fail (remote blocking, layout changes) — the code logs failures and leaves records unchanged.
-   If many records still have empty `country` fields after enrichment, consider running targeted enrichment or improving the per-site scraping heuristics for the specific pages that failed.

Quick commands

```powershell
# Resume enrichment (it will pick up data/sites_enriched.json if present)
Set-Location 'C:\Users\m41hm\Desktop\IR-Project\Heritage-Sites-Finder'
$env:PYTHONPATH='C:\Users\m41hm\Desktop\IR-Project\Heritage-Sites-Finder'
.\.venv\Scripts\python.exe scripts/enrich_resume.py
```

When finished the enriched index will be available at `data/index_enriched.pkl` and the enriched JSON at `data/sites_enriched.json`.

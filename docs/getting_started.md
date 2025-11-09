# Getting started

This page explains how to set up the project locally, install dependencies, and run the CLI and Flask API.

Prerequisites

-   Python 3.10+ (project tested on 3.10)
-   A terminal / PowerShell on Windows

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install project dependencies:

```powershell
pip install -r requirements.txt
```

3. Import data (from the provided `heritage_sites/sites.rss`) and build the index

```powershell
# from the project root (Heritage-Sites-Finder)
$env:PYTHONPATH='C:\Users\m41hm\Desktop\IR-Project\Heritage-Sites-Finder'
.\.venv\Scripts\python.exe -c "from src.fetcher import load_sites_from_rss; import json, pathlib; pathlib.Path('data').mkdir(exist_ok=True); sites=load_sites_from_rss('heritage_sites/sites.rss', save_raw_to='data/sites.rss', save_json_to='data/sites_from_rss.json'); open('data/sites.json','w',encoding='utf-8').write(json.dumps(sites,ensure_ascii=False))"

# build index
.\.venv\Scripts\python.exe -c "from src.indexer import HeritageIndexer; import json; docs=json.load(open('data/sites.json','r',encoding='utf-8')); idx=HeritageIndexer(); idx.fit(docs); idx.save('data/index.pkl'); print('BUILT_INDEX=', len(docs))"
```

4. Run the Flask API and open the frontend

```powershell
# run from project root
.\.venv\Scripts\python.exe run_api.py
```

Then open http://127.0.0.1:5000/ in your browser.

Notes

-   The app prefers an enriched index (`data/index_enriched.pkl`) if present.
-   Enrichment scripts and resumable workers exist in `scripts/` (see `enrichment.md`).

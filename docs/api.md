# API Reference

The Flask API is implemented in `src/api.py`. It serves search, rebuild and (planned) feedback endpoints. Below are the currently available endpoints and examples.

## /search

GET /search?q=<query>&k=<k>

-   q (required): search query string
-   k (optional): number of results to return (default 5)

Behavior:

-   The search endpoint runs a TF‑IDF retrieval and returns JSON results with the canonical site fields: `id`, `name`, `description`, `country`, `continent`, `latitude`, `longitude`, and `raw` metadata.
-   The API detects a trailing `in <place>` phrase (e.g. `castle in asia`) and will post-filter results by `continent` / `country` / document text when possible.

Response (example):

```json
[
    {
        "id": "668",
        "name": "Angkor",
        "description": "...",
        "country": "Cambodia",
        "continent": "Asia",
        "latitude": 13.4125,
        "longitude": 103.866667,
        "raw": { "link": "https://whc.unesco.org/en/list/668" }
    }
]
```

## /rebuild

GET or POST /rebuild

Optional params (query or JSON body):

-   `json_url`: path or URL to a JSON file of site records. If a local path is provided it will be loaded directly.
-   `use_fetcher`: boolean to call the configured fetcher to obtain fresh data from UNESCO or fallback sources.

The endpoint will rebuild the index (save to `data/index.pkl`) and return `{status: 'rebuilt', count: N}` on success.

## /feedback (planned)

A `/feedback` endpoint is planned to accept user feedback events (clicks, relevance labels). The project TODOs include adding a simple POST endpoint to persist events to `data/feedback.json` and use them for session-level re-ranking (Rocchio) or offline learning. See `docs/feedback.md` for the proposed schema.

## Static frontend

The project serves a small frontend from `web/`; open `/` to load it. A documentation page is available at `/docs.html` which serves `web/docs.html` (mirrors this docs folder).

# Heritage Sites Finder (UNESCO World Heritage IR project)

Small Information Retrieval (IR) project that fetches UNESCO World Heritage data, builds a TF-IDF index, and provides a tiny CLI to search site descriptions.

Quick start

-   create a virtual environment and activate it
-   install dependencies: pip install -r requirements.txt
-   run tests: pytest -q

CLI examples

-   Fetch & index (attempts to fetch from configured UNESCO endpoint):
    python -m src.cli fetch --out data/sites.json

-   Search an index (or JSON file):
    python -m src.cli search --json data/sites.json "ancient temple"

    Run the Flask API and frontend

    -   Start the API (from project root with venv active):
        python -m src.api

    Open http://127.0.0.1:5000/ in your browser to use the simple frontend.

Project layout

-   `src/fetcher.py` : functions to fetch UNESCO data or load fallback/sample data
-   `src/indexer.py` : TF-IDF indexing and search utilities
-   `src/cli.py` : simple CLI to fetch, index and search
-   `tests/` : unit tests (indexer)

Notes

The project uses scikit-learn's TfidfVectorizer for a compact search index. The fetcher attempts to hit UNESCO's public listing; if the endpoint changes, pass your own JSON file to the CLI.

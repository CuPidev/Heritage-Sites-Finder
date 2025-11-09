# Heritage Sites Finder — Documentation

Welcome to the documentation for Heritage Sites Finder — a small Information Retrieval (IR) project that fetches UNESCO World Heritage site data, normalizes records, builds a TF‑IDF search index, and exposes search via a Flask API and a tiny frontend.

This docs folder contains user-facing guidance and developer notes. Key pages:

-   getting_started.md — How to set up the project and run the API/CLI.
-   api.md — API endpoints and examples (/search, /rebuild, /feedback).
-   enrichment.md — How enrichment works, resume/run scripts and expected output files.
-   feedback.md — Design of the feedback system and quick how-to for testing it.
-   development.md — Notes for contributors: code layout, tests, adding features.

If you prefer to view docs in the app, open `/docs.html` in the frontend (served from `web/docs.html`).

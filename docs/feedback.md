# Feedback design

This page describes the planned feedback pipeline and a minimal JSON schema for storing user events.

Events to capture

-   Explicit relevance: user marks a result as relevant or not relevant (thumbs up/down).
-   Clicks: user clicks a result; capture position and timestamp.
-   Dwell: approximate time between click and returning to the search UI.
-   Query reformulation events.

Minimal feedback event JSON (append to `data/feedback.json` as newline-delimited JSON):

```json
{
    "event_id": "uuid-v4",
    "user_id": "anon-123",
    "session_id": "sess-abc",
    "timestamp": "2025-11-09T22:15:00Z",
    "query": "castle in asia",
    "doc_id": "668",
    "action": "relevance",
    "value": 1,
    "position": 3
}
```

Recording feedback

-   A `/feedback` POST endpoint is planned. The frontend should POST events immediately when the user clicks or labels a result.
-   Store events append-only; run a periodic job to train models or aggregate signals.

Using feedback for immediate re-ranking

-   A simple, high-impact approach is session-level Rocchio relevance feedback: keep the session's explicit positive docs and use their vectors to adjust the query vector at query time.
-   This requires `src/indexer.py` to expose document vectors and the `TfidfVectorizer` instance after `fit()`.

Offline learning

-   Periodically convert implicit/explicit events to training examples and train a learning-to-rank model (LightGBM, XGBoost or pairwise logistic regression).
-   Store resulting ranking model and use it to re-rank the top-N candidates returned by the TF‑IDF retriever.

Privacy & retention

-   Anonymize personal data where possible. Keep low-sensitivity identifiers (session_id) instead of real user identifiers.
-   Add a retention/rotation policy (e.g. purge events older than 90 days) and a size cap for the JSON file; for scale, move to SQLite or a message queue.

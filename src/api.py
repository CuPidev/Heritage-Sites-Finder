"""Flask API to serve heritage site search results."""

import os
import json
from typing import Optional, Any, Dict
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from .fetcher import fetch_unesco_list, sample_sites
from .indexer import HeritageIndexer
from .feedback import append_events


ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
SITES_JSON = os.path.join(DATA_DIR, "sites.json")
INDEX_PKL = os.path.join(DATA_DIR, "index.pkl")
ENRICHED_INDEX_PKL = os.path.join(DATA_DIR, "index_enriched.pkl")

# Results paging defaults and safety clamps
DEFAULT_K = 5
MIN_K = 1
# Allow overriding max via environment variable (useful for deployment)
try:
    MAX_K = int(os.environ.get("HSF_MAX_K", "50"))
except Exception:
    MAX_K = 50


# this is what is actually used by the runner
def create_app(static_folder: Optional[str] = None):
    if static_folder is None:
        static_folder = os.path.join(ROOT, "web")
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    CORS(app)

    indexer = HeritageIndexer()

    # try to load existing index (prefer enriched) or build from saved JSON or sample
    def _build_from_saved():
        # prefer enriched index if present
        if os.path.exists(ENRICHED_INDEX_PKL):
            try:
                indexer.load(ENRICHED_INDEX_PKL)
                return True
            except Exception:
                pass
        if os.path.exists(INDEX_PKL):
            try:
                indexer.load(INDEX_PKL)
                return True
            except Exception:
                pass
        # try load sites.json
        if os.path.exists(SITES_JSON):
            with open(SITES_JSON, "r", encoding="utf-8") as f:
                docs = json.load(f)
            indexer.fit(docs)
            indexer.save(INDEX_PKL)
            return True
        # fallback sample
        docs = sample_sites()
        indexer.fit(docs)
        indexer.save(INDEX_PKL)
        return True

    _build_from_saved()

    @app.route("/search")
    def search():
        q = request.args.get("q", "")
        # parse k safely and clamp to configured bounds to avoid excessive work
        k_raw = request.args.get("k", None)
        try:
            k = int(k_raw) if k_raw is not None else DEFAULT_K
        except (ValueError, TypeError):
            k = DEFAULT_K
        # enforce clamps
        k = max(MIN_K, min(k, MAX_K))
        if not q:
            return jsonify({"error": "missing query parameter 'q'"}), 400
        # Simple geographic parsing: detect "in <place>" and use it as a post-filter
        # e.g. "castle in asia" -> query="castle", place="asia"
        place = None
        m = None
        try:
            m = __import__("re").search(
                r"\bin\s+([A-Za-z \-]+)$", q, __import__("re").IGNORECASE
            )
        except Exception:
            m = None
        if m:
            place = m.group(1).strip()
            # remove the trailing "in <place>" from the query
            q = q[: m.start()].strip()

        try:
            results = indexer.search(q or (place or ""), top_k=max(k * 4, k))
        except RuntimeError:
            return jsonify({"error": "Index not ready"}), 500

        # If place was provided, post-filter results by continent or country match
        if place:
            place_l = place.lower()
            # simple continent match
            continents = {
                "asia",
                "europe",
                "africa",
                "oceania",
                "america",
                "north america",
                "south america",
                "americas",
            }

            def match_place(doc):
                # check explicit continent field
                cont = doc.get("continent")
                if cont and cont.lower() == place_l:
                    return True
                if cont and place_l in cont.lower():
                    return True
                # check country field
                country = doc.get("country") or ""
                if country and place_l in country.lower():
                    return True
                # fallback: check name/description text contains place
                txt = (doc.get("name", "") + " " + doc.get("description", "")).lower()
                if place_l in txt:
                    return True
                return False

            # if user asked 'in asia' or similar, try to match continent first
            if place_l in continents or place_l.endswith("asia"):
                filtered = [r for r in results if match_place(r)]
            else:
                # otherwise prefer country/name matches
                filtered = [r for r in results if match_place(r)]

            # limit to requested k
            results = filtered[:k]
        else:
            results = results[:k]

        return jsonify(results)

    @app.route("/rebuild", methods=["POST", "GET"])
    def rebuild():
        """Rebuild index. If `json_url` provided as query or json body, fetch that URL; if `use_fetcher` is true, call the configured UNESCO endpoint."""
        json_url = (
            request.args.get("json_url")
            or request.json
            and request.json.get("json_url")
        )
        use_fetcher = (
            request.args.get("use_fetcher") in ("1", "true", "True")
            or request.json
            and request.json.get("use_fetcher")
        )
        docs = None
        if json_url:
            try:
                # load local file if path provided
                if os.path.exists(json_url):
                    with open(json_url, "r", encoding="utf-8") as f:
                        docs = json.load(f)
                else:
                    docs = fetch_unesco_list(url=json_url)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        elif use_fetcher:
            try:
                docs = fetch_unesco_list()
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        if docs is not None:
            # save to sites.json
            with open(SITES_JSON, "w", encoding="utf-8") as f:
                json.dump(docs, f, ensure_ascii=False, indent=2)
            indexer.fit(docs)
            indexer.save(INDEX_PKL)
            return jsonify({"status": "rebuilt", "count": len(docs)})

        return jsonify({"status": "nothing to do"})

    @app.route("/feedback", methods=["POST"])
    def feedback():
        """Accept feedback events (single object or array) and append to data/feedback.json.

        Minimal validation is applied. Clients should send either a single JSON
        object or an array of objects. Each event should include at least
        `event_id`, `session_id`, `action` and `doc_id`.
        """
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "invalid json"}), 400

        events = payload if isinstance(payload, list) else [payload]

        valid_actions = {"relevance", "click", "dwell", "reformulation", "impression"}
        to_save = []
        errors = []
        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                errors.append({"index": i, "error": "event must be an object"})
                continue
            # basic required fields
            if not ev.get("event_id"):
                errors.append({"index": i, "error": "missing event_id"})
                continue
            if not ev.get("session_id"):
                errors.append({"index": i, "error": "missing session_id"})
                continue
            if not ev.get("doc_id"):
                errors.append({"index": i, "error": "missing doc_id"})
                continue
            action = ev.get("action")
            if not action or action not in valid_actions:
                errors.append(
                    {
                        "index": i,
                        "error": f"invalid or missing action (must be one of {sorted(valid_actions)})",
                    }
                )
                continue
            # add server timestamp if missing
            if not ev.get("timestamp"):
                import datetime

                ev["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

            to_save.append(ev)

        if errors and not to_save:
            return jsonify({"error": "validation failed", "details": errors}), 400

        try:
            count = append_events(to_save)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        # use a generic dict[Any] so static checkers allow mixed value types
        resp: Dict[str, Any] = {"saved": count}
        if errors:
            resp["partial_errors"] = errors
        return jsonify(resp), 201

    @app.route("/", defaults={"path": "index.html"})
    @app.route("/<path:path>")
    def serve_frontend(path):
        # serve static frontend files from web/
        if app.static_folder and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return ("Not Found", 404)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)

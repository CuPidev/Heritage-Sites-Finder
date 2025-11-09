"""Flask API to serve heritage site search results."""

import os
import json
from typing import Optional
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from .fetcher import fetch_unesco_list, sample_sites
from .indexer import HeritageIndexer


ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
SITES_JSON = os.path.join(DATA_DIR, "sites.json")
INDEX_PKL = os.path.join(DATA_DIR, "index.pkl")


def create_app(static_folder: Optional[str] = None):
    if static_folder is None:
        static_folder = os.path.join(ROOT, "web")
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    CORS(app)

    indexer = HeritageIndexer()

    # try to load existing index or build from saved JSON or sample
    def _build_from_saved():
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
        k = int(request.args.get("k", 5))
        if not q:
            return jsonify({"error": "missing query parameter 'q'"}), 400
        try:
            results = indexer.search(q, top_k=k)
        except RuntimeError:
            return jsonify({"error": "Index not ready"}), 500
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

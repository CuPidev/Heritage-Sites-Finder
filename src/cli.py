"""Simple CLI for fetching and searching UNESCO heritage site data."""
import argparse
import json
from typing import List

from .fetcher import fetch_unesco_list, sample_sites
from .indexer import HeritageIndexer


def cmd_fetch(args):
    out = args.out
    url = args.url
    try:
        sites = fetch_unesco_list(url=url)
        if out:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(sites, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(sites)} sites to {out}")
        else:
            print(f"Fetched {len(sites)} sites")
    except Exception as e:
        print("Fetch failed:", e)
        print("Falling back to sample data")
        sites = sample_sites()
        if out:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(sites, f, ensure_ascii=False, indent=2)
            print(f"Saved {len(sites)} sample sites to {out}")


def load_json(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # If the JSON root contains a list under a key, try to extract it
    if isinstance(data, dict):
        for key in ("sites", "rows", "data", "results", "features"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # fallback: if dict looks like list values
        for v in data.values():
            if isinstance(v, list):
                return v
        return [data]
    return data


def cmd_search(args):
    # Load docs from JSON or use sample
    if args.json:
        docs = load_json(args.json)
    else:
        docs = sample_sites()

    indexer = HeritageIndexer()
    indexer.fit(docs)
    results = indexer.search(args.query, top_k=args.k)
    for r in results:
        print(f"[{r['score']:.4f}] {r['id']} - {r['name']}")
        if args.show_description:
            print("  ", r.get("description"))


def main():
    parser = argparse.ArgumentParser("Heritage Sites Finder CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_fetch = sub.add_parser("fetch")
    p_fetch.add_argument("--out", help="Output JSON file to save sites")
    p_fetch.add_argument("--url", default="https://whc.unesco.org/en/list/json/", help="UNESCO JSON endpoint")
    p_fetch.set_defaults(func=cmd_fetch)

    p_search = sub.add_parser("search")
    p_search.add_argument("query", help="Query string")
    p_search.add_argument("--json", help="Path to JSON file containing site data")
    p_search.add_argument("-k", type=int, default=5, help="Number of results")
    p_search.add_argument("--show-description", action="store_true", help="Show matched doc descriptions")
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()
    if not hasattr(args, "func") or args.func is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()

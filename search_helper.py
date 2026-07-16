"""
Thin Tavily wrapper. Called by Claude via Bash during /search.

Usage:
  python search_helper.py "QA Engineering Manager Remote software automation job"

Outputs a JSON array of results to stdout. Each result has:
  url, title, content (snippet), raw_content (full page text, markdown),
  published_date, score (Tavily relevance)
"""

import sys
import json
import os
import argparse

from dotenv import load_dotenv, find_dotenv
from tavily import TavilyClient

load_dotenv(find_dotenv())


def search(query: str, max_results: int = 5, include_domains: list = None):
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    kwargs = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_raw_content": "markdown",
    }
    if include_domains:
        kwargs["include_domains"] = include_domains
    try:
        result = client.search(**kwargs)
        return result.get("results", [])
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+")
    parser.add_argument("--include-domains", help="Comma-separated domains to restrict search to")
    args = parser.parse_args()

    query = " ".join(args.query)
    domains = [d.strip() for d in args.include_domains.split(",")] if args.include_domains else None
    print(json.dumps(search(query, include_domains=domains)))

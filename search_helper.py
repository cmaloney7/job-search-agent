"""
Thin Tavily wrapper. Called by Claude via Bash during /search.

Usage:
  python search_helper.py "QA Engineering Manager Remote software automation job"

Outputs a JSON array of results to stdout. Each result has:
  url, title, content (snippet), published_date, score (Tavily relevance)
"""

import sys
import json
import os

from dotenv import load_dotenv, find_dotenv
from tavily import TavilyClient

load_dotenv(find_dotenv())


def search(query: str, max_results: int = 5):
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    try:
        result = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
        )
        return result.get("results", [])
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return []


if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    if not query:
        print("Usage: python search_helper.py <query>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(search(query)))

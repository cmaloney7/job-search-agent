"""
SQLite dedup store. One row per URL, keyed by SHA-256 hash of the URL.
Never re-scores a posting once seen.

CLI usage (called by Claude via Bash):
  python db.py seen <url>          -- exits 0 if seen, 1 if not
  python db.py insert '<json>'     -- inserts a record from JSON string
  python db.py all                 -- prints all records as JSON array
"""

import sqlite3
import hashlib
import json
import sys
from contextlib import contextmanager

DB_PATH = "matches.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    url_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    comp_text TEXT,
    comp_type TEXT,
    posted_date TEXT,
    summary TEXT,
    score INTEGER,
    reasoning TEXT,
    found_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'new'
);
"""


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()


def already_seen(conn, url: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM matches WHERE url_hash = ?", (url_hash(url),)
    )
    return cur.fetchone() is not None


def insert_match(conn, *, url, title=None, company=None, location=None,
                 comp_text=None, comp_type=None, posted_date=None,
                 summary=None, score=0, reasoning=None):
    conn.execute(
        """INSERT OR IGNORE INTO matches
           (url_hash, url, title, company, location, comp_text, comp_type,
            posted_date, summary, score, reasoning)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (url_hash(url), url, title, company, location, comp_text, comp_type,
         posted_date, summary, score, reasoning),
    )


def all_matches(conn, order_by: str = "score DESC, found_at DESC"):
    cur = conn.execute(f"SELECT * FROM matches ORDER BY {order_by}")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "seen":
        url = sys.argv[2]
        with get_conn() as conn:
            sys.exit(0 if already_seen(conn, url) else 1)

    elif cmd == "insert":
        data = json.loads(sys.argv[2])
        with get_conn() as conn:
            insert_match(conn, **data)

    elif cmd == "all":
        with get_conn() as conn:
            print(json.dumps(all_matches(conn), default=str))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

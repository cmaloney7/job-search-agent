"""
Local dashboard server. Serves docs/index.html and persists status
changes back to matches.db.

Usage: python3 server.py [port]   (default port: 8765)

Status changes made in the browser are POSTed to /api/status and
written to matches.db immediately. On page load the browser fetches
/api/statuses to populate dropdowns from the DB instead of localStorage.
If the server isn't running the dashboard falls back to localStorage.
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import db

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
HTML_PATH = Path("docs/index.html")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress per-request noise; errors still reach stderr

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/statuses":
            with db.get_conn() as conn:
                rows = db.all_matches(conn)
            statuses = {
                r["url"]: r["status"]
                for r in rows
                if r.get("status") and r["status"] != "new"
            }
            self.send_json(statuses)

        elif self.path in ("/", "/index.html"):
            body = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/status":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            url = data.get("url", "").strip()
            status = data.get("status", "").strip()
            if url:
                with db.get_conn() as conn:
                    db.update_status(conn, url=url, status=status)
                print(f"  status: {status or '(cleared)'!r}  {url[:80]}")
            self.send_json({"ok": True})

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Dashboard → http://localhost:{PORT}/")
    print("Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

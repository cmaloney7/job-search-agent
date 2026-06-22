"""
Renders matches.db into docs/index.html.
Called by the /render skill: python render.py

Enable GitHub Pages on the /docs folder to publish the dashboard.
"""

import html
from datetime import datetime, timezone

import db

OUTPUT_PATH = "docs/index.html"
DISPLAY_THRESHOLD = 50

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Job search agent -- dashboard</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1 {{ font-size: 20px; font-weight: 500; }}
  .meta {{ color: #666; font-size: 13px; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e5e5; vertical-align: top; }}
  th {{ color: #666; font-weight: 500; font-size: 12px; text-transform: uppercase; }}
  .score {{ font-weight: 600; }}
  .score-high {{ color: #0f6e56; }}
  .score-mid {{ color: #854f0b; }}
  a {{ color: #185fa5; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .empty {{ color: #888; padding: 40px 0; text-align: center; }}
  .summary {{ color: #555; font-size: 13px; padding: 4px 12px 12px; border-bottom: 1px solid #e5e5e5; }}
</style>
</head>
<body>
  <h1>Job search agent -- matches</h1>
  <div class="meta">Last updated {updated_at} UTC &middot; {count} matches at or above score {threshold}</div>
  {body}
</body>
</html>
"""

ROW_TEMPLATE = """<tr>
  <td class="score {score_class}">{score}</td>
  <td><a href="{url}" target="_blank">{title}</a></td>
  <td>{company}</td>
  <td>{location}</td>
  <td>{comp_text}</td>
  <td>{comp_type}</td>
  <td>{posting_age}</td>
  <td>{reasoning}</td>
  <td>{found_at}</td>
</tr>
<tr><td colspan="9" class="summary">{summary}</td></tr>"""


def score_class(score):
    return "score-high" if score >= 85 else "score-mid"


def posting_age(posted_date):
    if not posted_date:
        return "unknown"
    now = datetime.now(timezone.utc)
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(posted_date, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = now - dt
            hours = int(delta.total_seconds() // 3600)
            if hours < 24:
                return f"{hours}h ago" if hours > 0 else "today"
            return f"{delta.days}d ago"
        except ValueError:
            continue
    return "unknown"


def render():
    with db.get_conn() as conn:
        matches = [m for m in db.all_matches(conn) if (m["score"] or 0) >= DISPLAY_THRESHOLD]

    if matches:
        rows = "\n".join(
            ROW_TEMPLATE.format(
                score=m["score"],
                score_class=score_class(m["score"]),
                url=html.escape(m["url"]),
                title=html.escape(m["title"] or "Untitled"),
                company=html.escape(m["company"] or "?"),
                location=html.escape(m["location"] or "?"),
                comp_text=html.escape(m["comp_text"] or "--"),
                comp_type=html.escape(m["comp_type"] or "--"),
                posting_age=posting_age(m.get("posted_date")),
                summary=html.escape(m["summary"] or ""),
                reasoning=html.escape(m["reasoning"] or ""),
                found_at=m["found_at"],
            )
            for m in matches
        )
        body = f"""<table>
  <tr><th>Score</th><th>Title</th><th>Company</th><th>Location</th><th>Comp</th><th>Type</th><th>Age</th><th>Why</th><th>Found</th></tr>
  {rows}
</table>"""
    else:
        body = '<div class="empty">No matches yet -- check back after the next scheduled run.</div>'

    page = PAGE_TEMPLATE.format(
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        count=len(matches),
        threshold=DISPLAY_THRESHOLD,
        body=body,
    )

    with open(OUTPUT_PATH, "w") as f:
        f.write(page)

    print(f"Wrote {OUTPUT_PATH} ({len(matches)} matches shown)")


if __name__ == "__main__":
    render()

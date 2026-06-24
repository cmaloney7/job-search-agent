"""
Renders matches.db into docs/index.html.
Called by the /render skill: python render.py

Enable GitHub Pages on the /docs folder to publish the dashboard.
"""

import html
import re
from datetime import datetime, timezone

import db

OUTPUT_PATH = "docs/index.html"
CRITERIA_PATH = "criteria.md"
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
  .meta {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
  .criteria {{ background: #f7f7f7; border: 1px solid #e5e5e5; border-radius: 6px; padding: 12px 20px; margin-bottom: 28px; font-size: 13px; color: #444; }}
  .criteria > summary {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #888; cursor: pointer; user-select: none; padding: 4px 0; }}
  .criteria > summary:hover {{ color: #444; }}
  .criteria[open] > summary {{ margin-bottom: 12px; }}
  .criteria-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }}
  .criteria-section {{ }}
  .criteria-label {{ font-weight: 600; color: #333; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 6px; }}
  .criteria-section ul {{ margin: 0; padding: 0 0 0 16px; }}
  .criteria-section li {{ margin-bottom: 2px; }}
  .tag {{ display: inline-block; background: #fff; border: 1px solid #d5d5d5; border-radius: 4px; padding: 2px 7px; font-size: 12px; color: #444; margin: 2px 2px 2px 0; }}
  .tag-warn {{ border-color: #f0c0a0; background: #fdf5ef; color: #884400; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e5e5; vertical-align: top; }}
  th {{ color: #666; font-weight: 500; font-size: 12px; text-transform: uppercase; }}
  .score {{ font-weight: 600; }}
  .score-high {{ color: #0f6e56; }}
  .score-mid {{ color: #854f0b; }}
  .score-low {{ color: #999; }}
  a {{ color: #185fa5; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .empty {{ color: #888; padding: 40px 0; text-align: center; }}
  .summary {{ color: #555; font-size: 13px; padding: 4px 12px 12px; border-bottom: 1px solid #e5e5e5; }}
  details {{ margin-top: 32px; }}
  summary {{ cursor: pointer; font-size: 13px; color: #666; padding: 8px 0; user-select: none; }}
  summary:hover {{ color: #333; }}
  details table {{ margin-top: 12px; opacity: 0.8; }}
</style>
</head>
<body>
  <h1>Job search agent -- matches</h1>
  <div class="meta">Last updated {updated_at} UTC &middot; {count} matches at or above score {threshold}</div>
  {criteria_panel}
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

TABLE_HEADER = "<tr><th>Score</th><th>Title</th><th>Company</th><th>Location</th><th>Comp</th><th>Type</th><th>Age</th><th>Why</th><th>Found</th></tr>"


def load_criteria():
    try:
        with open(CRITERIA_PATH) as f:
            text = f.read()
    except FileNotFoundError:
        return {}

    def section_items(heading):
        m = re.search(rf"## {heading}\n(.*?)(?=\n## |\Z)", text, re.S)
        if not m:
            return []
        return [
            line.lstrip("- ").strip()
            for line in m.group(1).splitlines()
            if line.startswith("- ") and not line.startswith("- #")
        ]

    def section_value(heading, pattern):
        m = re.search(rf"## {heading}\n(.*?)(?=\n## |\Z)", text, re.S)
        if not m:
            return None
        hit = re.search(pattern, m.group(1))
        return hit.group(1).strip() if hit else None

    return {
        "titles": section_items("Job titles to search"),
        "locations": section_items("Locations"),
        "boards": section_items("Job boards"),
        "disqualifiers": section_items(r"Hard disqualifiers.*"),
        "comp_floor": section_value("Compensation", r"Floor:\s*(.+)"),
        "comp_target": section_value("Compensation", r"Target:\s*(.+)"),
        "score_threshold": section_value("Score threshold", r"Display on dashboard.*?:\s*(\d+)"),
        "max_age": section_value("Posting age", r"Max age:\s*(.+)"),
    }


def build_criteria_panel(c):
    if not c:
        return ""

    def tag_list(items, cls="tag"):
        return "".join(f'<span class="{cls}">{html.escape(i)}</span>' for i in items)

    def ul_list(items):
        return "<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul>"

    sections = []

    if c.get("titles"):
        sections.append(
            f'<div class="criteria-section"><div class="criteria-label">Titles searched</div>{ul_list(c["titles"])}</div>'
        )

    if c.get("locations"):
        sections.append(
            f'<div class="criteria-section"><div class="criteria-label">Locations</div>{tag_list(c["locations"])}</div>'
        )

    if c.get("boards"):
        sections.append(
            f'<div class="criteria-section"><div class="criteria-label">Job boards</div>{tag_list(c["boards"])}</div>'
        )

    comp_parts = []
    if c.get("comp_floor"):
        comp_parts.append(f"Floor: {html.escape(c['comp_floor'])}")
    if c.get("comp_target"):
        comp_parts.append(f"Target: {html.escape(c['comp_target'])}")
    if comp_parts:
        sections.append(
            f'<div class="criteria-section"><div class="criteria-label">Compensation</div>{"<br>".join(comp_parts)}</div>'
        )

    filter_parts = []
    if c.get("score_threshold"):
        filter_parts.append(f"Min score to display: {html.escape(c['score_threshold'])}")
    if c.get("max_age"):
        filter_parts.append(f"Max posting age: {html.escape(c['max_age'])}")
    if filter_parts:
        sections.append(
            f'<div class="criteria-section"><div class="criteria-label">Filters</div>{"<br>".join(filter_parts)}</div>'
        )

    if c.get("disqualifiers"):
        sections.append(
            f'<div class="criteria-section"><div class="criteria-label">Auto-disqualified if contains</div>{tag_list(c["disqualifiers"], "tag tag-warn")}</div>'
        )

    grid = '<div class="criteria-grid">' + "".join(sections) + "</div>"
    return f'<details class="criteria"><summary>Search criteria</summary>{grid}</details>'


def score_class(score):
    if score >= 85:
        return "score-high"
    if score >= DISPLAY_THRESHOLD:
        return "score-mid"
    return "score-low"


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


def render_rows(matches):
    return "\n".join(
        ROW_TEMPLATE.format(
            score=m["score"],
            score_class=score_class(m["score"] or 0),
            url=html.escape(m["url"]),
            title=html.escape(m["title"] or "Untitled"),
            company=html.escape(m["company"] or "?"),
            location=html.escape(m["location"] or "?"),
            comp_text=html.escape(m["comp_text"] or "Not listed"),
            comp_type=html.escape(m["comp_type"] or "--"),
            posting_age=posting_age(m.get("posted_date")),
            summary=html.escape(m["summary"] or ""),
            reasoning=html.escape(m["reasoning"] or ""),
            found_at=m["found_at"],
        )
        for m in matches
    )


def render():
    criteria = load_criteria()
    criteria_panel = build_criteria_panel(criteria)

    with db.get_conn() as conn:
        all_rows = db.all_matches(conn)

    above = [m for m in all_rows if (m["score"] or 0) >= DISPLAY_THRESHOLD]
    below = [m for m in all_rows if (m["score"] or 0) < DISPLAY_THRESHOLD]

    if above:
        main_table = f"""<table>
  {TABLE_HEADER}
  {render_rows(above)}
</table>"""
    else:
        main_table = '<div class="empty">No matches yet -- check back after the next scheduled run.</div>'

    if below:
        below_table = f"""<details>
  <summary>{len(below)} below-threshold result{"s" if len(below) != 1 else ""} (score &lt; {DISPLAY_THRESHOLD}) &mdash; click to expand</summary>
  <table>
    {TABLE_HEADER}
    {render_rows(below)}
  </table>
</details>"""
    else:
        below_table = ""

    body = main_table + below_table

    page = PAGE_TEMPLATE.format(
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        count=len(above),
        threshold=DISPLAY_THRESHOLD,
        criteria_panel=criteria_panel,
        body=body,
    )

    with open(OUTPUT_PATH, "w") as f:
        f.write(page)

    print(f"Wrote {OUTPUT_PATH} ({len(above)} matches shown, {len(below)} below threshold)")


if __name__ == "__main__":
    render()

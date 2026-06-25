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

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Job search agent -- dashboard</title>
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 1100px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1 {{ font-size: 20px; font-weight: 500; }}
  .meta {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
  .criteria {{ background: #f7f7f7; border: 1px solid #e5e5e5; border-radius: 6px; padding: 12px 20px; margin-bottom: 20px; font-size: 13px; color: #444; }}
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

  /* Filter bar */
  .filter-bar {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
  .filter-bar span {{ color: #666; font-size: 13px; }}
  .filter-btn {{ font-size: 12px; padding: 4px 12px; border-radius: 4px; border: 1px solid #d5d5d5; cursor: pointer; background: #fff; color: #444; }}
  .filter-btn.active {{ background: #222; color: #fff; border-color: #222; }}
  .filter-btn:hover:not(.active) {{ background: #f0f0f0; }}

  /* Sort indicators */
  th[data-col] {{ cursor: pointer; user-select: none; white-space: nowrap; }}
  th[data-col]:hover {{ color: #333; }}
  th[data-col]::after {{ content: ' ↕'; color: #ccc; font-size: 10px; }}
  th[data-col].sort-asc::after {{ content: ' ▲'; color: #444; font-size: 10px; }}
  th[data-col].sort-desc::after {{ content: ' ▼'; color: #444; font-size: 10px; }}

  /* Status select */
  .status-cell {{ width: 120px; white-space: nowrap; }}
  .status-select {{ font-size: 12px; padding: 3px 6px; border-radius: 4px; border: 1px solid #d5d5d5; color: #444; cursor: pointer; width: 100%; }}

  /* Row status colors */
  tr.job-row[data-status="applied"] td {{ background-color: #e8f5e9; }}
  tr.job-row[data-status="applied"] + tr.job-summary td {{ background-color: #e8f5e9; }}
  tr.job-row[data-status="expired"] td {{ background-color: #f5f5f5; color: #aaa; }}
  tr.job-row[data-status="expired"] + tr.job-summary td {{ background-color: #f5f5f5; color: #aaa; }}
  tr.job-row[data-status="expired"] td a {{ color: #bbb; }}
  tr.job-row[data-status="not-interested"] td {{ background-color: #fff3e0; }}
  tr.job-row[data-status="not-interested"] + tr.job-summary td {{ background-color: #fff3e0; }}
</style>
</head>
<body>
  <h1>Job search agent -- matches</h1>
  <div class="meta">Last updated {updated_at} UTC &middot; {count} matches at or above score {threshold}</div>
  {criteria_panel}
  {filter_bar}
  {body}
<!-- SCRIPT_PLACEHOLDER -->
</body>
</html>
"""

FILTER_BAR = """<div class="filter-bar">
  <span>Show:</span>
  <button class="filter-btn active" data-filter="all" onclick="setFilter(this)">All</button>
  <button class="filter-btn" data-filter="active" onclick="setFilter(this)">Active only</button>
  <button class="filter-btn" data-filter="applied" onclick="setFilter(this)">Applied</button>
  <button class="filter-btn" data-filter="expired" onclick="setFilter(this)">Expired</button>
  <button class="filter-btn" data-filter="not-interested" onclick="setFilter(this)">Not Interested</button>
</div>"""

SCRIPT = """<script>
(function () {
  var PREFIX = 'jsa:';

  async function setStatus(select) {
    var row = select.closest('tr.job-row');
    var url = row.dataset.url;
    var status = select.value;
    if (status) {
      localStorage.setItem(PREFIX + url, status);
    } else {
      localStorage.removeItem(PREFIX + url);
    }
    row.dataset.status = status;
    try {
      await fetch('/api/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, status: status })
      });
    } catch (e) {}
    applyFilter();
  }

  function setFilter(btn) {
    document.querySelectorAll('.filter-btn').forEach(function (b) {
      b.classList.remove('active');
    });
    btn.classList.add('active');
    localStorage.setItem(PREFIX + 'filter', btn.dataset.filter);
    applyFilter();
  }

  function applyFilter() {
    var active = document.querySelector('.filter-btn.active');
    var filter = active ? active.dataset.filter : 'all';
    document.querySelectorAll('tr.job-row').forEach(function (row) {
      var status = row.dataset.status || '';
      var show = true;
      if (filter === 'active') {
        show = status !== 'expired' && status !== 'not-interested';
      } else if (filter !== 'all') {
        show = status === filter;
      }
      var next = row.nextElementSibling;
      row.style.display = show ? '' : 'none';
      if (next && next.classList.contains('job-summary')) {
        next.style.display = show ? '' : 'none';
      }
    });
  }

  function parseComp(s) {
    if (!s) return -1;
    var m = s.replace(/,/g, '').match(/([0-9]+(?:\\.[0-9]+)?)\\s*(k)?/i);
    if (!m) return -1;
    var n = parseFloat(m[1]);
    if (m[2]) n *= 1000;
    return n;
  }

  function getVal(row, col) {
    switch (col) {
      case 'score': return parseInt(row.dataset.score, 10) || 0;
      case 'comp': return parseComp(row.dataset.comp);
      case 'title': return (row.dataset.title || '').toLowerCase();
      case 'company': return (row.dataset.company || '').toLowerCase();
      case 'location': return (row.dataset.location || '').toLowerCase();
      case 'type': return (row.dataset.type || '').toLowerCase();
      case 'why': return (row.dataset.why || '').toLowerCase();
      case 'found': return row.dataset.found || '';
      case 'status': return row.dataset.status || '';
      default: return '';
    }
  }

  function sortTableRows(table, col, asc) {
    var pairs = [];
    table.querySelectorAll('tr.job-row').forEach(function (row) {
      var next = row.nextElementSibling;
      pairs.push([row, next && next.classList.contains('job-summary') ? next : null]);
    });
    var numeric = col === 'score' || col === 'comp';
    pairs.sort(function (a, b) {
      var av = getVal(a[0], col);
      var bv = getVal(b[0], col);
      if (numeric) return asc ? av - bv : bv - av;
      var r = String(av).localeCompare(String(bv));
      return asc ? r : -r;
    });
    var container = table.tBodies[0] || table;
    pairs.forEach(function (pair) {
      container.appendChild(pair[0]);
      if (pair[1]) container.appendChild(pair[1]);
    });
  }

  function sortTable(th) {
    var col = th.dataset.col;
    var asc;
    if (th.classList.contains('sort-desc')) {
      asc = true;
    } else if (th.classList.contains('sort-asc')) {
      asc = false;
    } else {
      asc = col !== 'score' && col !== 'found' && col !== 'comp';
    }
    document.querySelectorAll('th[data-col]').forEach(function (h) {
      h.classList.remove('sort-asc', 'sort-desc');
      if (h.dataset.col === col) h.classList.add(asc ? 'sort-asc' : 'sort-desc');
    });
    document.querySelectorAll('table').forEach(function (table) {
      sortTableRows(table, col, asc);
    });
    localStorage.setItem(PREFIX + 'sort-col', col);
    localStorage.setItem(PREFIX + 'sort-asc', asc ? '1' : '0');
  }

  window.setStatus = setStatus;
  window.setFilter = setFilter;
  window.sortTable = sortTable;

  document.addEventListener('DOMContentLoaded', async function () {
    // Try to load statuses from the local server; fall back to localStorage.
    var dbStatuses = null;
    try {
      var resp = await fetch('/api/statuses');
      if (resp.ok) dbStatuses = await resp.json();
    } catch (e) {}

    document.querySelectorAll('tr.job-row').forEach(function (row) {
      var url = row.dataset.url;
      var status;
      if (dbStatuses !== null) {
        status = dbStatuses[url] || '';
        // First-connect migration: push any localStorage-only status to the DB.
        if (!status) {
          var lsStatus = localStorage.getItem(PREFIX + url) || '';
          if (lsStatus) {
            status = lsStatus;
            fetch('/api/status', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ url: url, status: lsStatus })
            }).catch(function () {});
          }
        }
      } else {
        status = localStorage.getItem(PREFIX + url) || '';
      }
      if (status) {
        row.dataset.status = status;
        var sel = row.querySelector('.status-select');
        if (sel) sel.value = status;
      }
    });
    var saved = localStorage.getItem(PREFIX + 'filter') || 'all';
    var btn = document.querySelector('.filter-btn[data-filter="' + saved + '"]');
    if (btn) {
      document.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
    }
    applyFilter();

    var sortCol = localStorage.getItem(PREFIX + 'sort-col');
    var sortAscVal = localStorage.getItem(PREFIX + 'sort-asc');
    if (sortCol) {
      var asc = sortAscVal === '1';
      document.querySelectorAll('th[data-col="' + sortCol + '"]').forEach(function (h) {
        h.classList.add(asc ? 'sort-asc' : 'sort-desc');
      });
      document.querySelectorAll('table').forEach(function (t) {
        sortTableRows(t, sortCol, asc);
      });
    } else {
      document.querySelectorAll('th[data-col="score"]').forEach(function (h) {
        h.classList.add('sort-desc');
      });
    }
  });
})();
</script>"""

ROW_TEMPLATE = """<tr class="job-row" data-url="{url}" data-status="" data-score="{score}" data-title="{title}" data-company="{company}" data-location="{location}" data-comp="{comp_text}" data-type="{comp_type}" data-why="{reasoning}" data-found="{found_at}">
  <td class="score {score_class}">{score}</td>
  <td><a href="{url}" target="_blank">{title}</a></td>
  <td>{company}</td>
  <td>{location}</td>
  <td>{comp_text}</td>
  <td>{comp_type}</td>
  <td>{reasoning}</td>
  <td>{found_at}</td>
  <td class="status-cell">
    <select class="status-select" onchange="setStatus(this)">
      <option value="">&#8212;</option>
      <option value="applied">Applied</option>
      <option value="expired">Expired</option>
      <option value="not-interested">Not Interested</option>
    </select>
  </td>
</tr>
<tr class="job-summary"><td colspan="9" class="summary">{summary}</td></tr>"""

TABLE_HEADER = '<tr><th data-col="score" onclick="sortTable(this)">Score</th><th data-col="title" onclick="sortTable(this)">Title</th><th data-col="company" onclick="sortTable(this)">Company</th><th data-col="location" onclick="sortTable(this)">Location</th><th data-col="comp" onclick="sortTable(this)">Comp</th><th data-col="type" onclick="sortTable(this)">Type</th><th data-col="why" onclick="sortTable(this)">Why</th><th data-col="found" onclick="sortTable(this)">Found</th><th data-col="status" onclick="sortTable(this)">Status</th></tr>'


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
        filter_bar=FILTER_BAR,
        body=body,
    )
    page = page.replace("<!-- SCRIPT_PLACEHOLDER -->", SCRIPT)

    with open(OUTPUT_PATH, "w") as f:
        f.write(page)

    print(f"Wrote {OUTPUT_PATH} ({len(above)} matches shown, {len(below)} below threshold)")


if __name__ == "__main__":
    render()

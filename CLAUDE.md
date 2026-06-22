# CLAUDE.md -- job-search-agent

Autonomous job search agent for Corey Molloy. Runs 2x/day via GitHub Actions.

---

## What this repo does

1. `/search` skill -- queries Tavily for job postings matching criteria.md,
   scores each new result against profile.md using Claude's own judgment,
   and stores results in matches.db (SQLite).

2. `/render` skill -- reads matches.db and writes docs/index.html, a static
   dashboard published via GitHub Pages.

Each URL is scored exactly once and stored permanently. The dedup store is
what makes repeated runs cheap -- new results shrink toward zero over time.

---

## Files to edit

- `criteria.md` -- tune titles, locations, signals, threshold as the search evolves
- `profile.md` -- update as experience or targets change

Do not edit `db.py`, `search_helper.py`, or `render.py` unless the data
model or rendering logic needs to change.

---

## How scoring works

Claude reads profile.md and criteria.md in full, then scores each posting
using its own reasoning. There is no separate scoring API call -- Claude IS
the scorer. Hard disqualifiers are checked first via keyword scan before
Claude evaluates the posting at all, saving tokens on obvious misses.

Score guide:
- 90+: strong fit on hard criteria AND candidate story
- 70-89: worth applying
- 50-69: marginal, show on dashboard for review
- Below 50: weak fit, stored but not shown
- 0: hard disqualifier or fails a hard filter

---

## Setup

### Dependencies
```bash
pip install -r requirements.txt
```

### Environment variables
Copy `.env.example` to `.env` and fill in:
```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

### GitHub secrets
Settings > Secrets and variables > Actions:
- ANTHROPIC_API_KEY
- TAVILY_API_KEY

### GitHub Pages
Settings > Pages > Source: Deploy from branch > Branch: main, folder: /docs

---

## Running locally

```bash
# Run the search pipeline
/search

# Render the dashboard
/render

# View the dashboard
open docs/index.html
```

---

## Cost estimate

Each run fires ~27 queries (9 titles x 3 locations). Tavily: ~1,600 API calls/month
(2 runs/day x 27 queries x 30 days). Claude scoring happens in-context -- no
separate API calls per posting. Total cost: Tavily Starter plan ($20/month) +
minimal Claude token usage for the agent loop.

---

## Interview talking points

- Claude IS the orchestrator and the scorer -- no Python managing an LLM pipeline
- Hard disqualifiers are a pre-filter that saves tokens before Claude evaluates
- Dedup means each URL is scored exactly once; cost approaches zero as the
  search space is exhausted
- Skills (slash commands) define the agent's capabilities as plain markdown --
  the procedure is readable and auditable without parsing code

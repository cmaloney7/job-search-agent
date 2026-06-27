# job-search-agent

Autonomous job search agent powered by Claude. Runs 2x/day via GitHub Actions, scores postings against a candidate profile, and publishes results to a GitHub Pages dashboard.

## How it works

1. **Search** — queries Tavily across 36 combinations of job titles and locations, returning fresh postings each run.
2. **Score** — Claude reads the full candidate profile and criteria, then scores each new posting 0–100. Hard disqualifiers are keyword-checked first to skip obvious misses.
3. **Dedup** — every URL is stored in `matches.db` after its first evaluation and never re-scored, keeping costs near zero as the search space fills.
4. **Render** — scored results are written to `docs/index.html`, a static dashboard published via GitHub Pages.

## Schedule

Runs automatically via GitHub Actions on Tuesday, Thursday, and Saturday at 5:00 AM PT (`0 12 * * 2,4,6` UTC).

After each run, a Resend email notification is sent to confirm the agent completed and link to the dashboard. You can also trigger a run manually from the Actions tab (`workflow_dispatch`).

## What it searches for

**Job titles** (9):

- QA Engineering Manager
- Manager Quality Engineering
- Senior Manager Test Engineering
- Manager Engineering QA
- Director of Quality Engineering
- Head of QA
- QA Engineer III
- Senior QA Engineer
- Staff QA Automation Engineer

**Locations** (4): Remote · Seattle WA · San Diego CA · Charleston SC

**Job boards** (9): greenhouse.io · lever.co · myworkdayjobs.com · jobs.ashbyhq.com · smartrecruiters.com · icims.com · linkedin.com · weworkremotely.com · wellfound.com

**Compensation**: $150,000 floor, up to $275,000 target. Postings clearly below the floor score 0.

## Setup

### Dependencies

Installed via `pip install -r requirements.txt`: `anthropic`, `tavily-python`, `python-dotenv`.

```bash
pip install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
RESEND_API_KEY=re_...
```

`RESEND_API_KEY` is only needed locally if you want to test the email notification step. Get a key at resend.com.

### GitHub secrets

Add to Settings → Secrets and variables → Actions:

- `ANTHROPIC_API_KEY`
- `TAVILY_API_KEY`
- `RESEND_API_KEY`

### GitHub Pages

Settings → Pages → Source: Deploy from branch → Branch: `main`, folder: `/docs`

## Running locally

```bash
# Run the search pipeline
/search

# Render the dashboard
/render

# Open the dashboard
open docs/index.html
```

## Tuning the search

| File | What to edit |
|------|-------------|
| `criteria.md` | Titles, locations, job boards, comp floor, score threshold, hard disqualifiers, signals |
| `profile.md` | Candidate experience, stack, preferences, hard stops |

Do not edit `db.py`, `search_helper.py`, or `render.py` unless the data model or rendering logic needs to change.

## Score guide

| Score | Meaning |
|-------|---------|
| 90+ | Strong fit on hard criteria and candidate story |
| 70–89 | Worth applying |
| 50–69 | Marginal, shown on dashboard for review |
| Below 50 | Weak fit, stored but not shown |
| 0 | Hard disqualifier or fails a hard filter |

## Cost

~468 Tavily API calls/month (3 runs/week × 36 queries × 4.33 weeks). Claude scoring runs in-context — no separate API calls per posting. Estimated total: Tavily Starter plan (~$20/month) + minimal Claude token usage.

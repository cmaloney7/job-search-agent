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

## What happens on each GitHub Actions run

Defined in [`.github/workflows/job-search.yml`](.github/workflows/job-search.yml):

1. Checks out the repo and installs Python dependencies plus the Claude Code CLI.
2. Runs `claude -p "Run /search ... then run /render ..."`, which executes the same `/search` and `/render` skills you'd run locally.
3. Commits any changes to `matches.db` and `docs/index.html` back to `main` (author: `job-search-agent`).
4. Runs `notify.py success`, which emails a completion notice (subject, run link, and a link to the dashboard) via Resend.
5. If any step failed, runs `notify.py failure` instead, which emails a failure notice including the last ~40 lines of output from the search step to help diagnose what went wrong. `notify.py` is the same script you can run locally to test notifications — see [Testing notifications locally](#testing-notifications-locally).

The dashboard link in the email is built at runtime from `github.repository_owner` and the repo name, so it stays correct even if you rename the repo or fork it under a different account — nothing to update by hand.

## The dashboard

`docs/index.html` is a static, self-contained page (no build step) published via GitHub Pages. It renders every scored match as a sortable table:

- **Columns**: Score, Title, Company, Location, Comp, Type, Why (Claude's reasoning for the score), Found (date), Status. Click any column header to sort.
- **Filter bar**: All / Active only / Applied / Expired / Not Interested — narrows the table to matches in that state.
- **Status dropdown**: each row has a dropdown to mark a posting as Applied, Expired, or Not Interested. Matching rows get a colored background (green/gray/orange) so your pipeline is visible at a glance.
- **Only 50+ scores are shown** — weaker matches are stored in `matches.db` but not rendered.

**Using it on GitHub Pages** (the published version, after each Actions run): open `https://<your-username>.github.io/<repo-name>/`. Status changes you make there are saved to your browser's `localStorage` only — they won't sync back to the repo or to other devices, since GitHub Pages is static.

**Using it locally with persistence**: run `python3 server.py` and open `http://localhost:8765/`. Status changes are written straight to `matches.db`, so they persist across renders and are picked up by the next `/render`.

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

**Job boards** (12): builtin.com · indeed.com · Dice.com · greenhouse.io · lever.co · myworkdayjobs.com · jobs.ashbyhq.com · smartrecruiters.com · icims.com · linkedin.com · weworkremotely.com · wellfound.com

**Compensation**: $150,000 floor, up to $275,000 target. Postings clearly below the floor score 0.

## Setup

### Prerequisites

- **Python 3.11+**
- **Node.js/npm**, to install the Claude Code CLI: `npm install -g @anthropic-ai/claude-code`. Required to run `/search` and `/render` locally — they're Claude Code skills, not standalone Python scripts.

### Dependencies

Installed via `pip3 install -r requirements.txt`: `anthropic`, `tavily-python`, `python-dotenv`.

```bash
pip3 install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
RESEND_API_KEY=re_...
DASHBOARD_EMAIL=you@example.com
RESEND_FROM_EMAIL=Job Search Agent <onboarding@resend.dev>
```

`RESEND_API_KEY`, `DASHBOARD_EMAIL`, and `RESEND_FROM_EMAIL` are only needed locally if you want to test the email notification step (see below). Get a Resend key at resend.com.

#### Testing notifications locally

`notify.py` sends the same email the GitHub Actions workflow sends, using the values above. The dashboard link it sends defaults to `http://localhost:8765/`, so start the local server first or the link in the email won't resolve:

```bash
python3 server.py &               # starts the dashboard at localhost:8765
python3 notify.py success   # sends the run-complete email
python3 notify.py failure   # sends the run-failed email (with a log tail, if found)
```

Without `DASHBOARD_URL` / `RUN_URL` set (as they are in CI), the email falls back to the local dashboard server and a "local test run" placeholder, so it's safe to run anytime without a real CI run behind it.

### GitHub secrets

The scheduled workflow runs in GitHub Actions, which has no access to your local `.env` file — each value needs to be added as a repo secret instead.

Go to your repo's **Settings → Secrets and variables → Actions → New repository secret**, and add one secret per row:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Same value as in `.env` |
| `TAVILY_API_KEY` | Same value as in `.env` |
| `RESEND_API_KEY` | Same value as in `.env` |
| `DASHBOARD_EMAIL` | The email address that should receive run notifications, e.g. `you@example.com` |
| `RESEND_FROM_EMAIL` | The sender shown on notification emails, e.g. `Job Search Agent <onboarding@resend.dev>`. Only needs to be a verified domain in your Resend account if you move off the shared sandbox sender. |

### GitHub Pages

Settings → Pages → Source: Deploy from branch → Branch: `main`, folder: `/docs`

Once enabled, your dashboard is published at `https://<your-github-username>.github.io/<repo-name>/`.

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

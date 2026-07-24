Run the autonomous job search pipeline.

## Setup

Read `criteria.md` to load: titles, locations, query suffix, score threshold,
max posting age, hard disqualifiers, positive signals, negative signals, and
job boards (include_domains). Ignore lines beginning with `#` in the job boards list.

Read `profile.md` to understand the candidate in full.

## Steps

### 1. Build queries

Combine every title with every location, appending the query suffix from
criteria.md. Example: "QA Engineering Manager Remote software automation job careers remote"

### 2. For each query

If `criteria.md` includes a job boards list, pass the active domains (non-commented lines)
as a comma-separated `--include-domains` argument:

```
python search_helper.py "<query>" --include-domains "greenhouse.io,lever.co,..."
```

If no job boards are listed, omit the flag:

```
python search_helper.py "<query>"
```

This returns a JSON array. Each item has: url, title, content (snippet),
raw_content (full page text, may be null if Tavily couldn't extract it),
published_date.

### 3. For each result

**a. Skip if already seen:**
Run: `python db.py seen "<url>"`
Exit code 0 = already in db, skip it.

**a2. Skip aggregator listing/category pages:**
For results from `linkedin.com`, `indeed.com`, `dice.com`, and `builtin.com`, check
whether the URL points to an individual job posting or a search/category page.

Individual posting indicators (keep these):
- `linkedin.com` — URL contains `/jobs/view/`
- `indeed.com` — URL contains `/viewjob`
- `dice.com` — URL contains `/job-detail/`
- `builtin.com` — URL path has at least 3 segments after `/job/` (e.g. `/job/engineer/qa/123`)

If the URL does NOT match the individual-posting pattern for that domain, record it
with score 0 and skip scoring:
```
python db.py insert '{"url":"...","title":"...","score":0,"reasoning":"Listing/category page, not an individual posting"}'
```

**b. Check hard disqualifiers:**
First, check if the job is closed or expired by scanning the title and snippet
(case-insensitive and phrase search mode) for any of these phrases:
- "no longer accepting"
- "No longer accepting applications"
- "The job that you were looking for either does not exist or is no longer open"
- "no longer available"
- "position has been filled"
- "this job is closed"
- "this job has expired"
- "job has been filled"
- "not accepting applications"
- "applications are closed"
- "this position is closed"

Then scan for hard disqualifier terms from criteria.md (case-insensitive).

If any match, record with score 0 and skip Claude scoring:
```
python db.py insert '{"url":"...","title":"...","score":0,"reasoning":"Hard disqualifier: <term>"}'
```

**c. Score the posting using your own judgment:**
Using the full candidate profile and criteria, score 0-100:
- 90+: strong fit on hard criteria AND candidate story
- 70-89: worth applying
- 50-69: marginal, surface for review
- Below 50: weak fit
- 0: hard disqualifier or fails a hard filter

Hard filters that score 0:
- Seniority clearly outside QA Engineer III through Director range
- Posted comp clearly below $150K floor
- On-site required outside Seattle WA or San Diego CA
- `published_date` is present AND older than the max posting age in criteria.md

**d. Record the result:**
Always record (even below threshold) so the URL is never re-scored.

Build a JSON object with all fields you have:

- `posted_date`: use the `published_date` field from the Tavily result verbatim
  (it is an ISO date string like "2024-01-15T00:00:00Z", or null). Do NOT
  extract date text from the snippet — if `published_date` is null, omit
  `posted_date` or set it to null.
- `comp_text`: salary/pay range if explicitly stated. Check `raw_content` first
  (it holds the full page, where comp is often shown after a "show more" expander
  that the snippet omits) and fall back to the snippet. Examples: "$180K–$220K",
  "$95/hr". If not mentioned anywhere, omit or set to null.
- `comp_type`: "FTE", "contract", or null. Infer from explicit language in
  `raw_content` or the snippet (e.g. "contractor", "hourly", "full-time",
  "W2 employee"). Do not guess when there's no explicit signal — leave null.

```
python db.py insert '{"url":"...","title":"...","company":"...","location":"...","comp_text":"$180K-$220K or null","comp_type":"FTE or contract or null","posted_date":"2024-01-15T00:00:00Z or null","summary":"2-3 sentence plain-English summary of the role","score":75,"reasoning":"one sentence under 25 words"}'
```

Print a line for matches at or above threshold:
`-> MATCH (75): Title @ Company`

### 4. Summary

Print: `Done. New matches: N | Already seen: N | Disqualified: N | Below threshold: N`

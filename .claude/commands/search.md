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

This returns a JSON array. Each item has: url, title, content (snippet), published_date.

### 3. For each result

**a. Skip if already seen:**
Run: `python db.py seen "<url>"`
Exit code 0 = already in db, skip it.

**b. Check hard disqualifiers:**
Scan the title and snippet for any term in the hard disqualifiers list (case-insensitive).
If matched, record with score 0 and skip Claude scoring:
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
- Posted comp clearly below $160K floor
- On-site required outside Seattle WA or San Diego CA

Reduce score 10-15 points if published_date is older than MAX_POSTING_AGE_DAYS.

**d. Record the result:**
Always record (even below threshold) so the URL is never re-scored.

Build a JSON object with all fields you have:
```
python db.py insert '{"url":"...","title":"...","company":"...","location":"...","comp_text":"...","comp_type":"FTE or contract or null","posted_date":"...","summary":"2-3 sentence plain-English summary of the role","score":75,"reasoning":"one sentence under 25 words"}'
```

Print a line for matches at or above threshold:
`-> MATCH (75): Title @ Company`

### 4. Summary

Print: `Done. New matches: N | Already seen: N | Disqualified: N | Below threshold: N`

# Search criteria

## Job titles to search

# Manager/Director level (greenfield QA focus)
- QA Engineering Manager
- Director of Quality Engineering

# IC level (commented out: focus on leadership track)
# - Senior QA Engineer
# - Staff QA Automation Engineer

# AI Testing/Eval (new track)
- AI Evaluation

# Niche titles (commented out: too specialized)
# - Confidence Engineer
# - SDET
# - Test Engineer

## Locations

- Remote
# - United States  (redundant with Remote)
- San Diego CA
- Charleston SC
- Honolulu, HI 

## Job boards

Restrict Tavily searches to these domains. This prevents job board category pages
(ZipRecruiter, Built In, etc.) from filling results instead of individual postings.
Remove a domain or comment it out (prefix with `#`) to stop searching it.

- greenhouse.io
- lever.co
- myworkdayjobs.com
- jobs.ashbyhq.com
- smartrecruiters.com
- icims.com
- weworkremotely.com
- wellfound.com
- remoteok.com
- toptal.com
- contra.com

## Query suffix

Append this to every title + location query: `software automation job careers remote`

## Compensation

- Floor: $150,000
- Target: up to $400,000
- Score 0 if a posted range is clearly below the floor

## Posting age

Max age: 7 days. Score 0 for postings older than this.
Show "unknown" on the dashboard if no date is available.

## Score threshold

Record results at or above: 50
Display on dashboard at or above: 50

## Hard disqualifiers -- score 0 immediately, do not evaluate further

- medical device
- fda
- iec 62304
- 510(k)
- embedded systems
- hardware-in-the-loop
- in-vehicle testing
- oracle jd edwards
- hyperion epm
- isso

## Positive signals (count in favor)

- Greenfield QA function or team build-out
- AI-native or AI-enabled testing tooling
- Regulated industry experience relevant (healthcare, finance, travel, insurance)
- People leadership or technical lead scope

## Negative signals (count against)

- Pure manual QA execution role with no automation component
- Requires on-site presence outside Charleston or San Diego with no remote option
- Comp below floor based on posted range

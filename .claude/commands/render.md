Render the job matches dashboard.

Run: `python render.py`

This reads matches.db, filters to scores at or above the display threshold (50),
and writes docs/index.html.

If the render succeeds, print the output from render.py.
If matches.db does not exist yet, say so and suggest running /search first.

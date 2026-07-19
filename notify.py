"""
Sends the run-complete / run-failed email via Resend.

Used by the GitHub Actions workflow after each scheduled run, and runnable
locally to test the notification without waiting for a scheduled run.

Usage:
    python3 notify.py success
    python3 notify.py failure [log_path]

Reads from .env locally (via python-dotenv) or from the environment in CI:
    RESEND_API_KEY    -- required
    DASHBOARD_EMAIL    -- required, notification recipient
    RESEND_FROM_EMAIL  -- optional, defaults to Resend's shared sandbox sender
    DASHBOARD_URL       -- optional, defaults to the local dashboard server
    RUN_URL             -- optional, defaults to a local-test placeholder
    RUN_NUMBER          -- optional, defaults to "local-test"
"""

import json
import os
import sys
import urllib.request

from dotenv import load_dotenv

load_dotenv()

FROM_ADDRESS = os.environ.get("RESEND_FROM_EMAIL", "Job Search Agent <onboarding@resend.dev>")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:8765/")
RUN_URL = os.environ.get("RUN_URL", "(local test run — no CI run URL)")
RUN_NUMBER = os.environ.get("RUN_NUMBER", "local-test")


def send(payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": "Bearer " + os.environ["RESEND_API_KEY"],
            "Content-Type": "application/json",
            "User-Agent": "python-resend/1.0",
        },
        method="POST",
    )
    urllib.request.urlopen(req)


def send_success() -> None:
    send({
        "from": FROM_ADDRESS,
        "to": [os.environ["DASHBOARD_EMAIL"]],
        "subject": "Job search run complete — run #" + RUN_NUMBER,
        "text": (
            "Your job search agent finished.\n\n"
            "Dashboard: " + DASHBOARD_URL + "\n\n"
            "Run details: " + RUN_URL
        ),
    })


def send_failure(log_path: str) -> None:
    try:
        with open(log_path) as f:
            tail = "".join(f.readlines()[-40:]).strip()
        if not tail:
            tail = "(step produced no output before failing)"
    except FileNotFoundError:
        tail = "(no output captured — failure likely occurred outside the search step)"

    send({
        "from": FROM_ADDRESS,
        "to": [os.environ["DASHBOARD_EMAIL"]],
        "subject": "Job search run FAILED — run #" + RUN_NUMBER,
        "text": (
            "Your job search agent run failed.\n\n"
            "Run details: " + RUN_URL + "\n\n"
            "Last output before failure:\n\n" + tail
        ),
    })


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "success":
        send_success()
    elif mode == "failure":
        default_log = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "search-output.log")
        send_failure(sys.argv[2] if len(sys.argv) > 2 else default_log)
    else:
        sys.exit("Usage: python3 notify.py <success|failure> [log_path]")

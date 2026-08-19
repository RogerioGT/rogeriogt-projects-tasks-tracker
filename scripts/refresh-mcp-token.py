#!/usr/bin/env python3
"""Refresh the Tasks Tracker MCP API token in VS Code's mcp.json files.

Checks the token embedded in the configured mcp.json files. If it has more than
REFRESH_WINDOW_DAYS left, does nothing (silent, exit 0). Otherwise it logs in,
gets a fresh token, verifies it, and rewrites it in place (formatting preserved).

Silent-on-noop makes it safe to run daily: it only emits output (and only
rewrites files) when a refresh actually happens.

Credentials come from the vibecoding profile .env:
    TASKS_TRACKER_ADMIN_EMAIL=...
    TASKS_TRACKER_ADMIN_PASSWORD=...
"""

import base64
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

API = "https://tasksmgr.rogeriogt.com"
REFRESH_WINDOW_DAYS = 7  # refresh when fewer than this many days remain

ENV_FILE = os.path.expanduser("~/.hermes/profiles/vibecoding/.env")

TARGETS = [
    os.path.expanduser("~/.config/Code/User/mcp.json"),
    os.path.expanduser("~/Documents/rogeriogt-projects-tasks-tracker/.vscode/mcp.json"),
]

# Matches `"TASKS_API_TOKEN": "<anything>"` on one line, so it rewrites both a
# hardcoded token and a `${input:...}` placeholder, preserving all other content.
TOKEN_RE = re.compile(r'("TASKS_API_TOKEN"\s*:\s*)"[^"]*"')


def load_creds() -> tuple[str, str]:
    email = password = None
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k == "TASKS_TRACKER_ADMIN_EMAIL":
                email = v
            elif k == "TASKS_TRACKER_ADMIN_PASSWORD":
                password = v
    if not email or not password:
        print("ERROR: TASKS_TRACKER_ADMIN_EMAIL/PASSWORD not set in .env", file=sys.stderr)
        sys.exit(1)
    return email, password


def token_expiry(token: str) -> int:
    """Unix timestamp the token expires, or 0 if it can't be decoded."""
    try:
        b64 = token.split(".")[0]
        pad = "=" * (-len(b64) % 4)
        payload = base64.urlsafe_b64decode(b64 + pad).decode()
        _, exp = payload.rsplit(":", 1)
        return int(exp)
    except Exception:
        return 0


def read_token(path: str) -> str | None:
    """Extract the TASKS_API_TOKEN value from a file, or None if not present."""
    try:
        text = open(path).read()
    except FileNotFoundError:
        return None
    m = re.search(r'"TASKS_API_TOKEN"\s*:\s*"([^"]*)"', text)
    if not m:
        return None
    val = m.group(1)
    return None if val.startswith("${input") else val


def login(email: str, password: str) -> str:
    req = urllib.request.Request(
        f"{API}/api/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["token"]


def verify_token(token: str) -> bool:
    req = urllib.request.Request(
        f"{API}/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError:
        return False


def rewrite_token(path: str, new_token: str) -> bool:
    if not os.path.exists(path):
        return False
    text = open(path).read()
    new_text, n = TOKEN_RE.subn(f'\\1"{new_token}"', text)
    if n == 0:
        # file exists but has no TASKS_API_TOKEN line to rewrite
        return False
    with open(path, "w") as f:
        f.write(new_text)
    return True


def main() -> int:
    force = "--force" in sys.argv

    if not force:
        # What's the soonest-expiring hardcoded token across all target files?
        now = int(time.time())
        soonest = None
        for p in TARGETS:
            tok = read_token(p)
            if not tok:
                continue
            exp = token_expiry(tok)
            if exp == 0:
                soonest = 0  # un-decodable token -> force refresh
                break
            if soonest is None or exp < soonest:
                soonest = exp

        if soonest is not None and soonest > now + REFRESH_WINDOW_DAYS * 86400:
            # plenty of life left, nothing to do (silent)
            return 0

    email, password = load_creds()
    try:
        new_token = login(email, password)
    except Exception as e:
        print(f"ERROR: login failed: {e}", file=sys.stderr)
        return 1
    if not verify_token(new_token):
        print("ERROR: new token failed verification", file=sys.stderr)
        return 1

    new_exp = token_expiry(new_token)
    updated = [p for p in TARGETS if rewrite_token(p, new_token)]

    if not updated:
        print("ERROR: no target mcp.json had a TASKS_API_TOKEN to update", file=sys.stderr)
        return 1

    exp_str = time.strftime("%Y-%m-%d", time.gmtime(new_exp)) if new_exp else "unknown"
    print(f"Tasks Tracker token refreshed in: {', '.join(updated)}")
    print(f"New token expires {exp_str} (30 days).")
    print("Action needed: restart the tasks-tracker MCP server in VS Code "
          "(Copilot Chat -> Configure Tools -> restart icon, or accept VS Code's reload prompt).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

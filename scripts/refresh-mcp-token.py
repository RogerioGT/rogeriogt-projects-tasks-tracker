#!/usr/bin/env python3
"""Refresh the Tasks Tracker MCP API token in VS Code's mcp.json files.

Checks the token embedded in the configured mcp.json files. If it has more than
REFRESH_WINDOW_DAYS left, does nothing (silent, exit 0). Otherwise it logs in,
gets a fresh token, verifies it, and rewrites it in place (formatting preserved).

Silent-on-noop makes it safe to run daily: it only emits output (and only
rewrites files) when a refresh actually happens.

Credentials come from the vibecoding profile .env:
    TASKS_TRACKER_ADMIN_EMAIL / _PASSWORD    (Rogerio's admin token)
    TASKS_TRACKER_MATI_EMAIL / _PASSWORD     (Mati's own token, refreshed over SSH)
"""

import base64
import json
import os
import re
import subprocess
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

# Hermes config.yaml — the MCP server's env block uses YAML (unquoted) values.
HERMES_CONFIG = os.path.expanduser("~/.hermes/profiles/vibecoding/config.yaml")

# Mati's machine (her own Hermes + token). Refreshed over SSH (key auth).
MATI_HOST = "mati@mati-slim"
MATI_SSH_OPTS = ["-o", "ConnectTimeout=10", "-p", "22"]
MATI_REMOTE_CONFIG = "/home/mati/.hermes/profiles/personal/config.yaml"

# Matches `"TASKS_API_TOKEN": "<anything>"` on one line, so it rewrites both a
# hardcoded token and a `${input:...}` placeholder, preserving all other content.
TOKEN_RE = re.compile(r'("TASKS_API_TOKEN"\s*:\s*)"[^"]*"')
# YAML form: `TASKS_API_TOKEN: <value>` (may be quoted or not).
TOKEN_RE_YAML = re.compile(r'(\n\s+TASKS_API_TOKEN:\s*)\S+')


def load_creds() -> dict[str, tuple[str, str]]:
    """Return {email: (email, password)} for admin and (if present) mati."""
    email = password = mati_email = mati_password = None
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
            elif k == "TASKS_TRACKER_MATI_EMAIL":
                mati_email = v
            elif k == "TASKS_TRACKER_MATI_PASSWORD":
                mati_password = v
    if not email or not password:
        print("ERROR: TASKS_TRACKER_ADMIN_EMAIL/PASSWORD not set in .env", file=sys.stderr)
        sys.exit(1)
    creds = {email: (email, password)}
    if mati_email and mati_password:
        creds[mati_email] = (mati_email, mati_password)
    return creds


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
    """Extract the TASKS_API_TOKEN value from a JSON mcp.json, or None."""
    try:
        text = open(path).read()
    except FileNotFoundError:
        return None
    m = re.search(r'"TASKS_API_TOKEN"\s*:\s*"([^"]*)"', text)
    if not m:
        return None
    val = m.group(1)
    return None if val.startswith("${input") else val


def read_token_yaml(path: str) -> str | None:
    """Extract the TASKS_API_TOKEN value from the Hermes config.yaml, or None."""
    try:
        text = open(path).read()
    except FileNotFoundError:
        return None
    m = re.search(r'\n\s+TASKS_API_TOKEN:\s*["\']?([^"\'\s]+)', text)
    if not m:
        return None
    return m.group(1)


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


def rewrite_token_yaml(path: str, new_token: str) -> bool:
    if not os.path.exists(path):
        return False
    text = open(path).read()
    new_text, n = TOKEN_RE_YAML.subn(f'\\1{new_token}', text)
    if n == 0:
        return False
    with open(path, "w") as f:
        f.write(new_text)
    return True


def read_token_remote(host: str, path: str) -> str | None:
    """Read the TASKS_API_TOKEN from a config.yaml on a remote host via SSH."""
    cmd = ["ssh", *MATI_SSH_OPTS, host,
           f"grep -m1 'TASKS_API_TOKEN:' {path} 2>/dev/null"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    m = re.search(r'TASKS_API_TOKEN:\s*["\']?([^"\'\s]+)', out)
    return m.group(1) if m else None


def rewrite_token_remote(host: str, path: str, new_token: str) -> bool:
    """Rewrite the TASKS_API_TOKEN on a remote host via SSH (sed on the remote).

    The token is base64url + '.' + ':' — no single quotes or shell metachars —
    so it's safe to single-quote inside the remote command string."""
    # ssh host "sed -i 's|...|...|' path"  (whole command passed as one string)
    remote_cmd = f"sed -i 's|^ *TASKS_API_TOKEN:.*|  TASKS_API_TOKEN: {new_token}|' {path}"
    cmd = ["ssh", *MATI_SSH_OPTS, host, remote_cmd]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return r.returncode == 0
    except Exception:
        return False


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
        # Hermes config.yaml token
        ytok = read_token_yaml(HERMES_CONFIG)
        if ytok:
            exp = token_expiry(ytok)
            if exp == 0:
                soonest = 0
            elif soonest is None or exp < soonest:
                soonest = exp
        # Mati's remote config token
        mtok = read_token_remote(MATI_HOST, MATI_REMOTE_CONFIG)
        if mtok:
            exp = token_expiry(mtok)
            if exp == 0:
                soonest = 0
            elif soonest is None or exp < soonest:
                soonest = exp

        if soonest is not None and soonest > now + REFRESH_WINDOW_DAYS * 86400:
            # plenty of life left, nothing to do (silent)
            return 0

    creds = load_creds()
    updated: list[str] = []
    messages: list[str] = []

    # --- admin token: VS Code files + my Hermes config ---
    # admin is the first entry in .env (added before mati's)
    emails = list(creds.keys())
    admin_email = emails[0]
    try:
        admin_token = login(*creds[admin_email])
        if not verify_token(admin_token):
            print("ERROR: admin token failed verification", file=sys.stderr)
            return 1
        new_exp = token_expiry(admin_token)
        admin_updated = [p for p in TARGETS if rewrite_token(p, admin_token)]
        if rewrite_token_yaml(HERMES_CONFIG, admin_token):
            admin_updated.append(HERMES_CONFIG)
        if admin_updated:
            updated += admin_updated
            exp_str = time.strftime("%Y-%m-%d", time.gmtime(new_exp)) if new_exp else "unknown"
            messages.append(f"admin token refreshed in {', '.join(admin_updated)} (expires {exp_str})")
    except Exception as e:
        print(f"ERROR: admin login failed: {e}", file=sys.stderr)
        return 1

    # --- mati's token: refresh on her machine over SSH ---
    if len(emails) > 1:
        mati_email = emails[1]
        try:
            mati_token = login(*creds[mati_email])
            if not verify_token(mati_token):
                print("ERROR: mati token failed verification", file=sys.stderr)
            elif rewrite_token_remote(MATI_HOST, MATI_REMOTE_CONFIG, mati_token):
                updated.append(f"{MATI_HOST}:{MATI_REMOTE_CONFIG}")
                m_exp = token_expiry(mati_token)
                m_str = time.strftime("%Y-%m-%d", time.gmtime(m_exp)) if m_exp else "unknown"
                messages.append(f"mati token refreshed on {MATI_HOST} (expires {m_str})")
            else:
                print(f"WARNING: could not refresh mati token on {MATI_HOST}", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: mati login failed: {e}", file=sys.stderr)

    if not updated:
        print("ERROR: no target config had a TASKS_API_TOKEN to update", file=sys.stderr)
        return 1

    for m in messages:
        print(m)
    print("Action needed: restart the tasks-tracker MCP server in VS Code / Hermes "
          "(/reload-mcp or new session); on Mati's machine restart her Hermes or "
          "run /reload-mcp in her personal profile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

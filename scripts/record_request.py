#!/usr/bin/env python3
"""Runs on GitHub Actions when a license request issue is opened.
Extracts PC code + RSA public key from the issue body and appends to
pending.txt (last entry per code wins). Commits via GITHUB_TOKEN.
"""
import os
import re
import sys
import json
import base64

def main():
    event_path = os.environ["GITHUB_EVENT_PATH"]
    with open(event_path) as fh:
        event = json.load(fh)
    issue = event.get("issue") or {}
    body = issue.get("body") or ""
    title = issue.get("title") or ""

    m = re.search(r"REQUEST\s+([0-9A-F]{8})\s+([A-Za-z0-9+/=\s]+)", body, re.IGNORECASE)
    if not m:
        print("issue does not contain a REQUEST line - ignoring")
        sys.exit(0)
    code = m.group(1).upper()
    pubkey_b64 = "".join(m.group(2).split())

    # sanity: valid base64, plausible RSA public key (DER, ~300+ bytes)
    try:
        pem = base64.b64decode(pubkey_b64)
        if len(pem) < 200:
            raise ValueError("too short")
    except Exception:
        print("invalid pubkey in issue - ignoring")
        sys.exit(0)

    line = f"{code} {pubkey_b64}"
    with open("pending.txt", "a") as fh:
        fh.write(line + "\n")
    print(f"pending registered: {code}")

    # commit via git (GITHUB_TOKEN)
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    os.system("git config user.name license-bot")
    os.system("git config user.email bot@users.noreply.github.com")
    os.system("git add pending.txt")
    os.system('git diff --cached --quiet || git commit -m "request: register ' + code + '"')
    push = f"https://x-access-token:{token}@github.com/{repo}.git"
    os.system(f"git push {push} HEAD:{os.environ.get('GITHUB_REF_NAME','main')} 2>&1 || git push")

if __name__ == "__main__":
    main()

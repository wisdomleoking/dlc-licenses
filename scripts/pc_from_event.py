#!/usr/bin/env python3
"""Prints the PC code from the workflow event issue (helper for record.yml)."""
import json
import os
import re
import sys

with open(os.environ["GITHUB_EVENT_PATH"]) as fh:
    event = json.load(fh)
body = (event.get("issue") or {}).get("body") or ""
m = re.search(r"REQUEST\s+([0-9A-F]{8})", body, re.IGNORECASE)
if m:
    print(m.group(1).upper())

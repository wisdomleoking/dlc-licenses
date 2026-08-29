#!/usr/bin/env python3
"""Runs on GitHub Actions (never on user PCs). Wraps master key K with each
newly approved PC's RSA-2048 public key (RSA-OAEP-SHA256), publishes
keygrants/<PCCODE>.b64 to the 'licenses' release, tracks grants by
CODE+PUBKEY-PREFIX so re-activation with a fresh identity re-grants.
"""
import os
import base64
import hashlib
import json
import subprocess
import urllib.request

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def api(method, path, data=None):
    """GitHub REST API via urllib - reliable asset upload/replace."""
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GH_REPO"]
    url = f"https://api.github.com/repos/{repo}/{path}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, method=method, data=body)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "dlc-grant")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        txt = r.read()
        return json.loads(txt) if txt else None


def upload_asset(pc, b64_content):
    repo = os.environ["GH_REPO"]
    token = os.environ["GH_TOKEN"]
    name = f"keygrants_{pc}.b64"

    # find release 'licenses' (create if missing)
    rel = None
    for r in api("GET", "releases"):
        if r.get("tag_name") == "licenses":
            rel = r
            break
    if rel is None:
        rel = api("POST", "releases", {"tag_name": "licenses", "name": "License grants"})

    # delete existing asset with same name, if any
    for a in rel.get("assets", []):
        if a["name"] == name:
            api("DELETE", f"releases/assets/{a['id']}")
            break

    # upload via the asset upload URL
    upload_url = rel["upload_url"].replace("{?name,label}", f"?name={name}")
    req = urllib.request.Request(upload_url, method="POST", data=b64_content.encode())
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/octet-stream")
    req.add_header("User-Agent", "dlc-grant")
    with urllib.request.urlopen(req) as r:
        json.loads(r.read())
    print(f"uploaded {name}")


def load_approved():
    return set(open("approved.txt").read().upper().split())


def load_granted():
    g = {}
    if os.path.exists("granted.txt"):
        for line in open("granted.txt"):
            parts = line.strip().split()
            if not parts:
                continue
            g[parts[0].upper()] = parts[1].upper() if len(parts) > 1 else ""
    return g


def load_pending():
    p = {}
    if os.path.exists("pending.txt"):
        for line in open("pending.txt"):
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                p[parts[0].upper()] = parts[1]
    return p


def main():
    approved = load_approved()
    granted = load_granted()
    pending = load_pending()

    todo = []
    for pc in approved:
        if pc not in pending:
            continue
        prefix = hashlib.sha256(pending[pc].encode()).hexdigest()[:16].upper()
        if pc in granted and granted[pc] == prefix:
            continue  # this exact identity already has its key
        todo.append((pc, pending[pc], prefix))

    if not todo:
        print("No newly approved PCs with pending keys. Nothing to do.")
        return

    key_k = bytes.fromhex(os.environ["MASTER_KEY"].strip())
    repo = os.environ["GH_REPO"]
    token = os.environ["GH_TOKEN"]

    done = []
    for pc, pub_b64, prefix in todo:
        pem = base64.b64decode(pub_b64)
        rsa_key = RSA.import_key(pem)
        if rsa_key.size_in_bits() < 2048:
            print(f"skip {pc}: weak key")
            continue
        wrapped = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256).encrypt(key_k)
        b64 = base64.b64encode(wrapped).decode()
        print(f"wrapped K for {pc}")
        try:
            upload_asset(pc, b64)
        except Exception as e:
            print(f"upload failed for {pc}: {e}")
            continue
        granted[pc] = prefix
        done.append(pc)

    if not done:
        print("No grants written.")
        return

    with open("granted.txt", "w") as fh:
        for pc, prefix in granted.items():
            fh.write(f"{pc} {prefix}\n")

    sh("git config user.name license-bot")
    sh("git config user.email bot@users.noreply.github.com")
    sh("git add granted.txt")
    sh('git diff --cached --quiet || git commit -m "grant: ' + ", ".join(done) + '"')
    push = f"https://x-access-token:{token}@github.com/{repo}.git"
    sh(f'git push {push} 2>&1 || git push')
    print("granted:", ", ".join(done))


if __name__ == "__main__":
    main()

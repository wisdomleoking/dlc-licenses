#!/usr/bin/env python3
"""Runs on GitHub Actions (never on user PCs). Wraps master key K with each
newly approved PC's RSA-2048 public key (RSA-OAEP-SHA256), publishes
keygrants/<PCCODE>.b64 to the 'licenses' release, marks codes granted.
"""
import os
import base64
import subprocess
import sys

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    approved = set(open("approved.txt").read().upper().split())
    granted = set()
    if os.path.exists("granted.txt"):
        granted = set(open("granted.txt").read().upper().split())

    pending = {}
    for line in open("pending.txt"):
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            pending[parts[0].upper()] = parts[1]

    todo = [pc for pc in approved if pc not in granted and pc in pending]
    if not todo:
        print("No newly approved PCs with pending keys. Nothing to do.")
        return

    key_k = bytes.fromhex(os.environ["MASTER_KEY"].strip())
    repo = os.environ["GH_REPO"]
    token = os.environ["GH_TOKEN"]

    for pc in todo:
        pem = base64.b64decode(pending[pc])
        rsa_key = RSA.import_key(pem)
        if rsa_key.size_in_bits() < 2048:
            print(f"skip {pc}: weak key")
            continue
        wrapped = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256).encrypt(key_k)
        b64 = base64.b64encode(wrapped).decode()
        print(f"wrapped K for {pc} ({len(wrapped)} bytes)")

        # ensure 'licenses' release exists, then upload/overwrite asset
        sh('gh release create licenses --title "License grants" --notes "auto" --repo ' + repo)
        sh(f'gh release delete-asset licenses "keygrants_{pc}.b64" --yes --repo {repo} || true')
        open(f"keygrants_{pc}.b64", "w").write(b64)
        sh(f'gh release upload licenses "keygrants_{pc}.b64" --clobber --repo {repo}')
        print(f"published keygrants_{pc}.b64")

    with open("granted.txt", "a") as fh:
        for pc in todo:
            fh.write(pc + "\n")

    sh("git config user.name license-bot")
    sh("git config user.email bot@users.noreply.github.com")
    sh("git add granted.txt")
    sh('git diff --cached --quiet || git commit -m "grant: ' + ", ".join(todo) + '"')
    push = f"https://x-access-token:{token}@github.com/{repo}.git"
    sh(f'git push {push} 2>&1 || git push')
    print("done:", ", ".join(todo))


if __name__ == "__main__":
    main()

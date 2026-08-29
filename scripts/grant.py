#!/usr/bin/env python3
"""Runs on GitHub Actions (never on user PCs). Wraps master key K with each
newly approved PC's RSA-2048 public key (RSA-OAEP-SHA256), publishes
keygrants/<PCCODE>.b64 to the 'licenses' release, tracks grants by
CODE+PUBKEY-PREFIX so re-activation with a fresh identity re-grants.
"""
import os
import base64
import hashlib
import subprocess

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


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
        open(f"keygrants_{pc}.b64", "w").write(b64)
        print(f"wrapped K for {pc}")

        sh(f'gh release create licenses --title "License grants" --notes "auto" --repo {repo} 2>/dev/null || true')
        sh(f'gh release delete-asset licenses "keygrants_{pc}.b64" --yes --repo {repo} 2>/dev/null || true')
        code, out = sh(f'gh release upload licenses "keygrants_{pc}.b64" --clobber --repo {repo}')
        if code != 0:
            print(f"upload failed for {pc}: {out}")
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

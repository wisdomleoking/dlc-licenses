# dlc-licenses - approval server

PRIVATE repo. The master key K lives only in repo Secrets (MODEL_KEY).

## How you approve someone (15 seconds)

You'll get a GitHub email: *"License REQUEST ABCD1234"*.
1. Open this repo on github.com -> `approved.txt` -> pencil icon to edit
2. Add the PC code on its own line (e.g. `ABCD1234`)
3. Commit the file (defaults are fine)

That's it. Within a minute GitHub wraps the key for that PC and publishes
`keygrants/ABCD1234.b64`. The user's popup picks it up automatically and
the app opens. They are never asked again (key cached encrypted on their PC).

Denying = do nothing. They stay blocked forever.

## Files

- `approved.txt` - PC codes you've approved (one per line)
- `pending.txt` - auto-filled by workflow when a kit requests (code + RSA pub)
- `granted.txt` - auto-maintained: codes already given their key
- `.github/workflows/record.yml` - turns request issues into pending entries
- `.github/workflows/grant.yml` - wraps K for newly approved codes

## Kill switch

Settings -> Secrets and variables -> Actions -> update MODEL_KEY. Old grants
become useless the moment the kit re-requests (but cached keys keep working
until the kit is reinstalled - a full revoke also requires clearing the
release assets).

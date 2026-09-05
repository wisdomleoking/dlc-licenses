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

## If an approved PC reinstalls (fresh key)

Reinstalling the kit generates a NEW RSA identity, so it files a new
request. That request is intentionally NOT auto-granted. To approve a
reinstall:

1. `pending.txt` -> pencil icon -> delete that PC code's old line -> commit
   (first key per code wins; the old line blocks the new one)
2. Tell the user to click **Cancel** on their popup and start the app again
   (START bat re-files the request with the new key)
3. Check `pending.txt` - the code now has the new key
4. Actions -> **Grant license keys** -> Run workflow (main)
5. Their popup picks the new grant up within ~10s and the app starts

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

"""Optional phone push via ntfy.sh (install the free ntfy app, subscribe to your secret topic)."""
import os, json, urllib.request
topic = os.environ.get("NTFY_TOPIC"); url = os.environ.get("APP_URL", "")
if not topic: raise SystemExit("NTFY_TOPIC not set - skipping push")
ch = json.load(open("data/changes.json")); r = ch["run"]
if r["suspect"]:
    title, body = "IAF tracker: check run", f"Only {r['collected']} bids collected - looks incomplete, nothing marked as dropped."
elif r["new"] or r["extended"] or r["dropped"]:
    top = "\n".join(f"- {b['i'][:70]} (closes {b['e'][:10]})" for b in ch["new"][:5])
    title, body = f"IAF bids: {r['new']} new", f"{r['new']} new, {r['extended']} date changes, {r['dropped']} withdrawn.\n{top}"
else:
    raise SystemExit("no changes - no push")
req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode(), method="POST",
                             headers={"Title": title, **({"Click": url} if url else {})})
urllib.request.urlopen(req, timeout=20); print("pushed")

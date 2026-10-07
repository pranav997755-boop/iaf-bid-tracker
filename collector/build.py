"""Merge today's scrape into the running state, work out what changed, write docs/data.json."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
from categorise import classify, RULES

RAW = os.environ.get("GEM_OUT", "data/raw.json")
STATE = "data/state.json"
OUTJ = "docs/data.json"
KEEP_DAYS = 45          # keep closed bids this long
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
NOW = dt.datetime.now(IST)
TODAY = NOW.date().isoformat()

def iso(s):
    return dt.datetime.strptime(s.strip(), "%d-%m-%Y %I:%M %p").strftime("%Y-%m-%dT%H:%M")

def main():
    raw = json.load(open(RAW))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"bids": {}, "runs": []}
    bids = state["bids"]
    now = NOW.strftime("%Y-%m-%dT%H:%M")
    scraped = {}
    for r in raw["rows"]:
        try: s, e = iso(r["start"]), iso(r["end"])
        except Exception: continue
        c, t = classify(r["items"])
        scraped[r["bid"]] = dict(b=r["bid"], i=r["items"], q=r["qty"], s=s, e=e, cat=c, t=t[0], d=r["doc"])

    prev_open = [b for b in bids.values() if b["st"] == "open"]
    suspect = len(prev_open) > 20 and len(scraped) < 0.6 * len(prev_open)
    new, ext, gone = [], [], []
    first_run = not bids
    for k, v in scraped.items():
        o = bids.get(k)
        if not o:
            # "new" = opened in the last 3 days; older unseen bids are added quietly so a first run
            # (or a missed day) does not flood the Today tab.
            fresh = (not first_run) and v["s"][:10] >= (NOW.date() - dt.timedelta(days=3)).isoformat()
            v.update(st="open", f=(TODAY if fresh else v["s"][:10])); bids[k] = v
            if fresh: new.append(k)
        else:
            if o["e"] != v["e"]:
                ext.append(k); o["pe"] = o["e"]
            o.update({x: v[x] for x in ("i", "q", "s", "e", "cat", "t", "d")}); o["st"] = "open"; o.pop("gone", None)
    for k, o in bids.items():
        if k in scraped or o["st"] != "open": continue
        if o["e"] < now: o["st"] = "closed"
        elif not suspect:
            o["st"] = "dropped"; o["gone"] = TODAY; gone.append(k)
    cutoff = (NOW.date() - dt.timedelta(days=KEEP_DAYS)).isoformat()
    for k in [k for k, o in bids.items() if o["st"] != "open" and o["e"][:10] < cutoff]: del bids[k]

    run = dict(date=TODAY, collected=len(scraped), new=len(new), extended=len(ext), dropped=len(gone),
               short=len(raw.get("unverified", [])), suspect=suspect)
    state["runs"] = [r for r in state["runs"] if r["date"] != TODAY][-59:] + [run]
    os.makedirs("data", exist_ok=True); os.makedirs("docs", exist_ok=True)
    json.dump(state, open(STATE, "w"), ensure_ascii=False)

    cats = sorted({o["cat"] for o in bids.values()} - {"Other / Unclassified"},
                  key=lambda c: -sum(1 for o in bids.values() if o["cat"] == c and o["st"] == "open"))
    cats.append("Other / Unclassified"); ci = {c: i for i, c in enumerate(cats)}
    rows = [dict(b=o["b"], i=o["i"], q=o["q"], s=o["s"], e=o["e"], c=ci[o["cat"]], t=o["t"], d=o["d"],
                 f=o["f"], st=o["st"], **({"pe": o["pe"]} if o.get("pe") else {})) for o in bids.values()]
    rows.sort(key=lambda r: r["e"])
    json.dump(dict(generated=now, cats=cats, rows=rows, runs=state["runs"],
                   changes=dict(date=TODAY, new=new, extended=ext, dropped=gone), suspect=suspect,
                   short=raw.get("unverified", [])),
              open(OUTJ, "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(dict(new=[scraped[k] for k in new], extended=ext, dropped=gone, run=run), open("data/changes.json", "w"))
    print(run)

if __name__ == "__main__":
    main()

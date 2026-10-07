"""Collect Ministry of Defence -> Indian Air Force bids from the GeM public portal.

Drives a real browser (Playwright) because GeM's list endpoint needs a per-session token.
Strategy (learned the hard way): GeM's offset paging returns overlapping pages when many bids
share an end time, so we search small end-date windows, crawl each more than once, union the
results, and compare against the portal's own "N records" count.
"""
import os, re, sys, json, time, datetime as dt
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = os.environ.get("GEM_BASE", "https://bidplus.gem.gov.in")
MINISTRY = os.environ.get("GEM_MINISTRY", "Ministry of Defence")
ORG = os.environ.get("GEM_ORG", "Indian Air Force")
DAYS = int(os.environ.get("GEM_DAYS", "120"))        # how far ahead to look
SPLIT_AT = int(os.environ.get("GEM_SPLIT_AT", "40"))  # windows bigger than this are split
PASSES = int(os.environ.get("GEM_PASSES", "3"))
OUT = os.environ.get("GEM_OUT", "data/raw.json")

PARSE_JS = r"""
() => [...document.querySelectorAll('div.card')].map(c => {
  const a = c.querySelector('a.bid_no_hover'); if (!a) return null;
  const txt = c.innerText.replace(/\s+/g,' ');
  let items = '';
  const ia = [...c.querySelectorAll('a[title],a[data-content]')].find(x => !x.classList.contains('bid_no_hover'));
  if (ia) items = ia.getAttribute('data-content') || ia.getAttribute('title') || ia.textContent;
  if (!items) { const m = txt.match(/Items:\s*(.*?)\s*Quantity:/i); if (m) items = m[1]; }
  const q = (txt.match(/Quantity:\s*([\d,]+)/i)||[])[1] || '0';
  const s = c.querySelector('span.start_date'), e = c.querySelector('span.end_date');
  return {bid: a.textContent.trim(), doc: (a.getAttribute('href')||'').split('/').pop(),
          items: items.trim(), qty: parseInt(q.replace(/,/g,''))||0,
          start: s ? s.textContent.trim() : '', end: e ? e.textContent.trim() : ''};
}).filter(Boolean)
"""
COUNT_JS = r"""() => { const m = document.body.innerText.match(/of\s+([\d,]+)\s+records/i); return m ? parseInt(m[1].replace(/,/g,'')) : null }"""
SIG_JS = r"""() => { const a = document.querySelector('div.card a.bid_no_hover'); return a ? a.textContent.trim() + '|' + document.querySelectorAll('div.card').length : 'none' }"""

def ddmmyyyy(d): return d.strftime("%d-%m-%Y")

class Scraper:
    def __init__(self, page):
        self.p = page
        self.rows = {}          # bid -> row
        self.unverified = []

    def open_search(self):
        self.p.goto(BASE + "/advance-search", wait_until="domcontentloaded", timeout=60000)
        self.p.wait_for_selector("#ministry", timeout=60000)
        self.p.select_option("#ministry", label=MINISTRY)
        self.p.wait_for_function("(l)=>[...document.querySelectorAll('#organization option')].some(o=>o.textContent.trim()===l)", arg=ORG, timeout=30000)
        self.p.select_option("#organization", label=ORG)

    def search(self, d_from, d_to):
        """Run a search for bids ending between two dates; return the portal's record count."""
        self.p.evaluate("location.hash='#page-1'")
        before = self.p.evaluate(SIG_JS)
        self.p.fill("#bidendFromMinistrySearch", ddmmyyyy(d_from))
        self.p.fill("#bidendToMinistrySearch", ddmmyyyy(d_to))
        self.p.click("#tab1 a:has-text('Search')")
        try:
            self.p.wait_for_function("(b)=>{const a=document.querySelector('div.card a.bid_no_hover');"
                "const s=a?a.textContent.trim()+'|'+document.querySelectorAll('div.card').length:'none';"
                "return s!==b || /\\b0\\s+records/i.test(document.body.innerText)}", arg=before, timeout=20000)
        except PWTimeout:
            pass  # same first card is legitimate when the window repeats
        time.sleep(0.4)
        return self.p.evaluate(COUNT_JS) or 0

    def crawl(self, n):
        got = {}
        pages = max(1, -(-n // 10))
        for i in range(pages):
            for r in self.p.evaluate(PARSE_JS):
                got[r["bid"]] = r
            if i == pages - 1: break
            sig = self.p.evaluate(SIG_JS)
            ok = False
            for _ in range(3):
                nxt = self.p.query_selector(".pagination2 a.page-link.next")
                if not nxt: break
                nxt.click()
                try:
                    self.p.wait_for_function("(b)=>{const a=document.querySelector('div.card a.bid_no_hover');"
                        "return a && (a.textContent.trim()+'|'+document.querySelectorAll('div.card').length)!==b}", arg=sig, timeout=12000)
                    ok = True; break
                except PWTimeout:
                    continue
            if not ok: break
            time.sleep(0.15)
        return got

    def window(self, d_from, d_to, depth=0):
        n = self.search(d_from, d_to)
        if n == 0: return
        if n > SPLIT_AT and d_from < d_to:
            mid = d_from + (d_to - d_from) // 2
            self.window(d_from, mid, depth + 1)
            self.window(mid + dt.timedelta(days=1), d_to, depth + 1)
            return
        seen = {}
        limit = PASSES if d_from < d_to else PASSES * 3   # single days get extra passes
        for k in range(limit):
            if k: self.search(d_from, d_to)
            seen.update(self.crawl(n))
            if len(seen) >= n: break
        for b, r in seen.items(): self.rows[b] = r
        if len(seen) < n and d_from < d_to:               # still short: narrow the window
            mid = d_from + (d_to - d_from) // 2
            self.window(d_from, mid, depth + 1)
            self.window(mid + dt.timedelta(days=1), d_to, depth + 1)
            return
        if len(seen) < n:
            self.unverified.append((ddmmyyyy(d_from), ddmmyyyy(d_to), n, len(seen)))
        print(f"  {ddmmyyyy(d_from)}..{ddmmyyyy(d_to)}: {len(seen)}/{n}", flush=True)

    def fill_missing_items(self):
        """Some cards list items as plain text; any still empty are looked up by bid number."""
        for b, r in list(self.rows.items()):
            if r["items"]: continue
            try:
                self.p.goto(BASE + "/all-bids", wait_until="domcontentloaded", timeout=45000)
                self.p.fill("#searchBid", b)
                self.p.keyboard.press("Enter")
                self.p.wait_for_function("(b)=>document.body.innerText.includes(b)", arg=b, timeout=15000)
                for c in self.p.evaluate(PARSE_JS):
                    if c["bid"] == b and c["items"]: r["items"] = c["items"]
            except Exception as e:
                print("  item lookup failed", b, e)

def main():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
    with sync_playwright() as pw:
        exe = os.environ.get("CHROMIUM_PATH")
        br = pw.chromium.launch(headless=True, executable_path=exe) if exe else pw.chromium.launch(headless=True)
        ctx = br.new_context(locale="en-IN", timezone_id="Asia/Calcutta",
                             user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")
        page = ctx.new_page()
        s = Scraper(page)
        s.open_search()
        s.window(today, today + dt.timedelta(days=DAYS))
        s.fill_missing_items()
        br.close()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump({"fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
               "unverified": s.unverified, "rows": list(s.rows.values())},
              open(OUT, "w"), ensure_ascii=False)
    print(f"collected {len(s.rows)} bids; windows short of portal count: {len(s.unverified)}")
    if not s.rows:
        sys.exit("no bids collected - refusing to overwrite yesterday's data")

if __name__ == "__main__":
    main()

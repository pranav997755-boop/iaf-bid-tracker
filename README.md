# IAF Bid Tracker

A phone app that tracks Government e-Marketplace (GeM) bids for **Ministry of Defence → Indian Air Force**, refreshed automatically every morning.

- **Today** tab: new bids, bids closing in 3 days, closing-date changes, withdrawn bids.
- **Radar / Categories / Bid list** tabs: the same category views as the IAF Bid Explorer, with filters and search.
- Installs to your phone's home screen and opens offline with the last data it saw.
- Optional push notification each morning when something new appears.

## How it works

```
GitHub Actions (08:00 IST daily)
  collector/scrape.py   drives a real browser on GeM's advance-search page, one small date window at a time,
                        crawling each window several times and comparing with GeM's own "N records" count
  collector/build.py    categorises (collector/categorise.py), compares with yesterday (data/state.json),
                        writes docs/data.json
  commit + push         GitHub Pages serves docs/ as the app
  collector/notify.py   optional push via ntfy.sh
```

GeM's list endpoint needs a per-session security token, so the scraper uses a browser instead of calling it directly.

## Setup (about 10 minutes)

1. Create a **public** GitHub repository and push this folder to it. Pages on a private repo needs a paid plan. The data is public GeM data.
2. Repository **Settings → Pages**: source = *Deploy from a branch*, branch `main`, folder `/docs`. Your app address is shown there, usually `https://<you>.github.io/<repo>/`.
3. **Actions** tab → *Daily IAF bid refresh* → **Run workflow** once to test. A full run can take 30–60 minutes.
4. On your phone, open the address, then **Add to Home screen** (Chrome: menu → Install app. Safari: Share → Add to Home Screen).
5. Optional push alerts: install the free **ntfy** app, subscribe to a long random topic name, then add it in the repo under *Settings → Secrets and variables → Actions* as secret `NTFY_TOPIC`. Add your app address as a *variable* named `APP_URL` so tapping the notification opens the app.

The repository already contains a starting snapshot (898 bids captured 8 Oct 2026), so the app is useful before the first run.

## If GeM blocks the cloud run

Some Indian government sites refuse traffic from overseas data centres. If the workflow fails or collects 0 bids, run the same pipeline from an Indian connection instead:

- Easiest: on an always-on computer, run `./run_local.sh` daily (cron on Mac/Linux, Task Scheduler on Windows). It does the same steps and pushes the result.
- Or register that computer as a GitHub *self-hosted runner* and change `runs-on` in `.github/workflows/daily.yml` to `self-hosted`.

The scraper refuses to overwrite yesterday's data if it collects nothing, and flags a run as "suspect" (no withdrawals recorded) if it collects under 60% of the previous count.

## Tuning

| Setting (env var) | Default | Meaning |
|---|---|---|
| `GEM_DAYS` | 120 | How many days ahead of today to collect |
| `GEM_MINISTRY` / `GEM_ORG` | Ministry of Defence / Indian Air Force | Change to track another buyer |
| `GEM_PASSES` | 3 | Crawls per date window (GeM's paging drops rows, so windows are crawled repeatedly) |
| `GEM_SPLIT_AT` | 40 | Windows with more bids than this are split in half |

Edit `collector/categorise.py` to adjust the keyword rules. After changing categories, the next run re-categorises every bid.

## Testing

`tests/run_all.sh` runs the full pipeline against a mock GeM page that reproduces the overlapping-pagination flaw, then loads the app in a phone-sized browser. It needs no internet.

## Known limits

- **Not tested against live GeM from the build environment.** The scraper's selectors came from manual runs on the live site; GeM can change its page or add a CAPTCHA, which would make runs fail until the selectors are updated. Watch the first run.
- GeM's site terms may restrict automated access. Keep the schedule at once a day.
- A few bids can be missed when many share the same closing time. The app footer says when a day came back short of GeM's own count.
- City or location is not in the listing, only in each bid document, so it isn't shown.
- Categories are keyword guesses; roughly 4% land in "Other".
- Bids are marked *new* if they opened within the last 3 days. Older bids seen for the first time are added quietly.

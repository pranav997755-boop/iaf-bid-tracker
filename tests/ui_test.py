"""Load the built app in a phone-sized browser and check every tab renders without errors."""
import sys, threading, http.server, functools, os
from playwright.sync_api import sync_playwright
os.environ.setdefault("NO_PROXY", "127.0.0.1")
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory="docs")
H.log_message = lambda *a, **k: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8766), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
errs = []; shots = sys.argv[1] if len(sys.argv) > 1 else None
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    pg = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, service_workers="block").new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "fonts" not in m.text and "ERR_" not in m.text else None)
    pg.goto("http://127.0.0.1:8766/index.html"); pg.wait_for_selector(".bc, .empty", timeout=8000)
    def snap(n):
        if shots: pg.screenshot(path=f"{shots}/{n}.png")
    snap("today")
    print("today cards:", pg.locator(".bc").count(), "kpis:", pg.locator("#view .strip .v").all_inner_texts())
    for tab, sel in (("radar", "svg.radar circle.b"), ("cats", ".cards .card"), ("list", "tbody tr")):
        pg.click(f"[data-tab={tab}]"); pg.wait_for_selector(sel, timeout=5000)
        print(tab, pg.locator(sel).count()); snap(tab)
    pg.click("#ftoggle"); snap("filters"); pg.fill("#q", "laptop"); print("search laptop ->", pg.locator("tbody tr").count())
    pg.click("[data-tab=today]"); assert pg.locator(".controls").is_hidden()
    b.close()
print("errors:", errs); sys.exit(1 if errs else 0)

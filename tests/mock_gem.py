"""Tiny fake of GeM's advance-search page (same selectors, same overlapping-pagination flaw)."""
import http.server, json, random, datetime as dt, sys, threading
random.seed(7)
WORDS = ["AMC of air conditioner","Repair and overhauling service - cars","Laptop computer","Tea set","Fire extinguisher",
 "Housekeeping manpower","Medical injection kit","Tyre for truck","Radar antenna","Concrete road works","Stationery paper"]
BIDS = []
base = dt.datetime(2026,10,9,10,0)
for i in range(137):
    end = base + dt.timedelta(days=random.randint(0,25), hours=random.choice([0,0,0,3,5]))  # many ties
    BIDS.append(dict(no=f"GEM/2026/B/{7000000+i}", doc=str(9000000+i), item=random.choice(WORDS)+f" #{i}",
                     q=random.randint(1,500), start=end-dt.timedelta(days=10), end=end, plain=(i%3==0)))
BIDS.sort(key=lambda b:b["end"])
PAGE = """<html><body>
<select id=ministry><option>--</option><option>Ministry of Defence</option></select>
<select id=organization><option>--</option></select>
<input id=bidendFromMinistrySearch><input id=bidendToMinistrySearch>
<div id=tab1><a href="#" id=go>Search</a></div>
<input id=searchBid>
<div id=count></div><div id=list></div>
<div class=pagination2><a class="page-link next" href="#">Next</a></div>
<script>
const D=__D__; let res=[], off=0;
ministry.onchange=()=>{organization.innerHTML='<option>--</option><option>Indian Air Force</option>'};
function p(s){const [d,m,y]=s.split('-');return new Date(y+'-'+m+'-'+d)}
function render(){const pg=res.slice(off,off+10).map(b=>{ // overlap flaw: ties reshuffled each request
 const t=b.plain?`<div>Items: ${b.item}</div>`:`<div>Items: <a title="${b.item}">${b.item.slice(0,12)}...</a></div>`;
 return `<div class=card><a class=bid_no_hover href="/showbidDocument/${b.doc}">${b.no}</a>${t}<div>Quantity: ${b.q}</div><span class=start_date>${b.start}</span><span class=end_date>${b.end}</span></div>`}).join('');
 list.innerHTML=pg; count.textContent=`Showing ${res.length?off+1:0} - ${Math.min(off+10,res.length)} of ${res.length} records`}
function shuffleTies(a){const g={};a.forEach(b=>(g[b.end]=g[b.end]||[]).push(b));return Object.keys(g).sort().flatMap(k=>g[k].sort(()=>Math.random()-.5))}
go.onclick=e=>{e.preventDefault();const f=p(bidendFromMinistrySearch.value),t=p(bidendToMinistrySearch.value);t.setHours(23,59);
 setTimeout(()=>{res=D.filter(b=>{const d=new Date(b.endISO);return d>=f&&d<=t});off=0;res.sort((a,b)=>a.endISO<b.endISO?-1:1);render()},150)};
document.querySelector('.next').onclick=e=>{e.preventDefault();setTimeout(()=>{res=shuffleTies(res);off+=10;render()},150)};
</script></body></html>"""
def fmt(d): return d.strftime("%d-%m-%Y %I:%M %p")
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        if self.path.startswith("/advance-search"):
            D=[dict(b, start=fmt(b["start"]), end=fmt(b["end"]), endISO=b["end"].isoformat()) for b in BIDS]
            body=PAGE.replace("__D__",json.dumps(D)).encode()
            self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()
def serve(port=8765):
    s=http.server.ThreadingHTTPServer(("127.0.0.1",port),H); threading.Thread(target=s.serve_forever,daemon=True).start(); return s
if __name__=="__main__":
    serve(); import time; time.sleep(3600)

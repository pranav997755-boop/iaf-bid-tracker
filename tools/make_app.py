"""One-off: derive docs/index.html from the explorer template (kept for reproducibility)."""
import re, sys
src = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/work/template.html'
s = open(src).read()
def rep(old, new):
    global s
    assert old in s, old[:70]
    s = s.replace(old, new, 1)

s = ('<!doctype html><html lang="en"><meta charset="utf-8">'
     '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
     '<meta name="theme-color" content="#17608c"><meta name="apple-mobile-web-app-capable" content="yes">'
     '<link rel="manifest" href="manifest.webmanifest"><link rel="icon" href="icon-192.png"><link rel="apple-touch-icon" href="icon-192.png">\n') + s
rep('<title>IAF Bid Explorer</title>', '<title>IAF Bid Tracker</title>')
rep('<button role="tab" id="t-radar" aria-selected="true" data-tab="radar">Radar</button>',
    '<button role="tab" id="t-today" aria-selected="true" data-tab="today">Today</button>\n    <button role="tab" id="t-radar" aria-selected="false" data-tab="radar">Radar</button>')
rep('<script type="application/json" id="data">__DATA__</script>\n<script>\n(function(){\n  var D = JSON.parse(document.getElementById(\'data\').textContent);',
'''<script>
(function(){
  if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(function(){});
  fetch('data.json',{cache:'no-cache'}).then(function(r){if(!r.ok)throw 0;return r.json()}).then(boot).catch(function(){
    document.getElementById('view').innerHTML='<div class="panel"><div class="empty">Could not load the bid data. Check your connection and reopen the app.</div></div>';
  });
  function boot(D){''')
rep('renderTypes();render();\n})();\n</script>', "$('ftoggle').addEventListener('click',function(){document.querySelector('.controls').classList.toggle('open')});\n  renderTypes();render();\n  }\n})();\n</script>")
rep("var ROWS = D.rows.map(function(r,i){\n    return {i:i,b:r.b,",
    "var ALL = {}; D.rows.forEach(function(r){ALL[r.b]=r});\n  var ROWS = D.rows.filter(function(r){return r.st==='open'}).map(function(r,i){\n    return {i:i,f:r.f||'',pe:r.pe||'',b:r.b,")
rep("tab:'radar'", "tab:'today'")
s = re.sub(r"\$\('dek'\)\.textContent=.*?;\n", "$('dek').textContent=nf(ROWS.length)+' open bids that close between '+fmtDay(MIN_MS)+' and '+fmtDay(MAX_MS)+', sorted into '+CATS.length+' categories. Refreshed every morning.';\n", s, count=1, flags=re.S)
s = re.sub(r"\$\('foot'\)\.textContent=.*?;\n", """$('foot').textContent='Source: GeM public bid listing (bidplus.gem.gov.in), Ministry of Defence, Indian Air Force. Last refresh '+fmtStamp(D.generated)+' IST'+(D.short&&D.short.length?'. '+D.short.length+' date window(s) came back slightly short of the portal count, so a few bids may be missing today':'')+'. Categories are keyword-based and can be wrong; open the bid on GeM to confirm. Not an official GeM product.';\n""", s, count=1, flags=re.S)

today_js = r"""
  /* ---------- today ---------- */
  function bidCard(r,extra){
    return '<div class="bc"><div class="bc-t">'+esc(clip(r.txt||'',160))+'</div><div class="bc-m"><span class="dot '+r.t+'"></span>'+esc(CATS[r.c])+
      ' · qty '+nf(r.q)+' · closes '+fmtDay(r.ms)+', '+fmtTime(r.ms)+(extra||'')+'</div>'+
      '<a href="https://bidplus.gem.gov.in/showbidDocument/'+esc(r.d)+'" target="_blank" rel="noopener">Open on GeM</a></div>';
  }
  function section(title,sub,items,empty){
    return '<div class="panel tsec"><h2>'+title+'</h2><p class="note">'+sub+'</p>'+(items.length?items.join(''):'<div class="empty small">'+empty+'</div>')+'</div>';
  }
  function renderToday(){
    var ch=D.changes||{new:[],extended:[],dropped:[]}, now=Date.now()+19800000;
    var byB={};ROWS.forEach(function(r){byB[r.b]=r});
    var newRows=ch.new.map(function(b){return byB[b]}).filter(Boolean);
    var cut=new Date(now-3*DMS).toISOString().slice(0,10);
    var recent=ROWS.filter(function(r){return r.f>=cut&&ch.new.indexOf(r.b)<0});
    var soon=ROWS.filter(function(r){var d=r.ms-now;return d>-DMS/4&&d<3*DMS}).sort(function(a,b){return a.ms-b.ms});
    var ext=ch.extended.map(function(b){return byB[b]}).filter(Boolean);
    var drop=ch.dropped.map(function(b){return ALL[b]}).filter(Boolean).map(function(o){return {txt:o.i,q:o.q,ms:Date.parse(o.e+':00Z'),c:o.c,t:o.t,d:o.d}});
    var warn=D.suspect?'<div class="warn">Today\'s collection looks incomplete, so nothing was marked as withdrawn. Showing the last known bids.</div>':'';
    var runs=(D.runs||[]).slice(-14), mx=Math.max.apply(null,runs.map(function(r){return r.collected}).concat([1]));
    var spark='<div class="spark big">'+runs.map(function(r){return '<i style="height:'+Math.max(6,100*r.collected/mx)+'%" title="'+r.date+': '+r.collected+'"></i>'}).join('')+'</div>';
    function kp(k,v,s){return '<div><div class="k">'+k+'</div><div class="v">'+v+'</div><div class="s">'+s+'</div></div>'}
    var kpi='<section class="strip" style="margin-bottom:14px">'+
      kp('New today',newRows.length,'since the previous run')+kp('Closing in 3 days',soon.length,'act on these first')+
      kp('Date changes',ext.length,'closing date moved')+kp('Withdrawn',drop.length,'no longer listed')+'</section>';
    return warn+kpi+
      section('New today','Bids that appeared since the last run.',newRows.map(function(r){return bidCard(r)}),'Nothing new today.')+
      section('Closing in the next 3 days','Soonest first.',soon.slice(0,40).map(function(r){return bidCard(r)}),'Nothing closes in the next 3 days.')+
      section('Closing date changed','Extended or moved by the buyer.',ext.map(function(r){return bidCard(r,' · was '+fmtDay(Date.parse(r.pe+':00Z')))}),'No date changes.')+
      section('Withdrawn or cancelled','Disappeared from the listing before their closing date.',drop.map(function(r){return bidCard(r)}),'None.')+
      (recent.length?section('Added in the last 3 days','Earlier arrivals you may not have seen.',recent.slice(0,30).map(function(r){return bidCard(r)}),''):'')+
      '<div class="panel"><h2>Daily runs</h2><p class="note">Bids collected per run, last '+runs.length+' days.</p>'+spark+'</div>';
  }
"""
rep("  /* ---------- render ---------- */", today_js + "\n  /* ---------- render ---------- */")
rep('<section class="controls"','<button class="btn" id="ftoggle" type="button" hidden>Filters</button>\n  <section class="controls"')
rep("v.innerHTML=st.tab==='radar'?renderRadar(rows):st.tab==='cats'?renderCats(rows):renderList(rows);",
    "document.querySelector('.controls').hidden=document.getElementById('strip').hidden=document.getElementById('ftoggle').hidden=(st.tab==='today');\n    v.innerHTML=st.tab==='today'?renderToday():st.tab==='radar'?renderRadar(rows):st.tab==='cats'?renderCats(rows):renderList(rows);")
rep("""'<td class="it" title="'+esc(r.txt)+'">'+esc(clip(r.txt,200))+""",
    """'<td class="it" title="'+esc(r.txt)+'">'+(r.f>=new Date(Date.now()+19800000-2*DMS).toISOString().slice(0,10)?'<span class="newb">NEW</span> ':'')+esc(clip(r.txt,200))+""")
css = """
.bc{border-top:1px solid var(--line-2);padding:10px 0;display:flex;flex-direction:column;gap:3px}
.bc-t{font-weight:500;overflow-wrap:anywhere}
.bc-m{color:var(--ink-3);font-size:12px;display:flex;flex-wrap:wrap;gap:4px 6px;align-items:center}
.bc a{color:var(--accent);font-size:13px;align-self:flex-start;padding:4px 0}
.tsec{margin-bottom:14px}.empty.small{padding:14px 0}
.warn{background:#fff3cd;color:#5c4400;border:1px solid #e6c85a;border-radius:6px;padding:10px 12px;margin-bottom:12px}
.newb{background:var(--accent);color:var(--accent-ink);font-family:var(--f-data);font-size:10px;padding:1px 5px;border-radius:3px;letter-spacing:.06em}
.spark.big{height:60px;margin-top:8px}
[hidden]{display:none!important}
header{order:-3}.tabs{order:-2;position:sticky;top:0;background:var(--bg);z-index:4}
#ftoggle{display:none}
@media (max-width:700px){
  body{padding-inline:12px;padding-top:calc(12px + env(safe-area-inset-top))}
  .tabs{overflow-x:auto}.tabs button{padding:10px 12px 8px;white-space:nowrap}
  .tbl-wrap table{min-width:0}.tbl-wrap thead{display:none}
  .tbl-wrap tr{display:flex;flex-wrap:wrap;gap:2px 10px;border-bottom:1px solid var(--line-2);padding:8px 0}
  .tbl-wrap td{border:0;padding:0}.tbl-wrap td.it{order:-1;width:100%;max-width:none;font-weight:500}
  .row{gap:8px}.field.grow{flex-basis:100%}
  #ftoggle{display:block;width:100%}
  .controls:not(.open){display:none}
}
</style>"""
rep("</style>", css)
open('docs/index.html', 'w').write(s)
print('index.html', len(s))

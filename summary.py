"""Self-contained, responsive walk summary pages."""
import html, json, math, sys
from pathlib import Path

def build_html(walk):
    points=walk.get("route",[]); narrations=walk.get("narrations",[])
    width,height=800,340
    if points:
        lats=[p["lat"] for p in points]; lons=[p["lon"] for p in points]
        mid=sum(lats)/len(lats); xs=[(x-min(lons))*math.cos(math.radians(mid)) for x in lons]; ys=lats
        sx=max(max(xs)-min(xs),1e-7); sy=max(max(ys)-min(ys),1e-7); scale=min((width-60)/sx,(height-60)/sy)
        xy=[(30+(x-min(xs))*scale,height-30-(y-min(ys))*scale) for x,y in zip(xs,ys)]
        path=" ".join(("M" if i==0 else "L")+"%.1f %.1f"%pt for i,pt in enumerate(xy))
        pins=[]
        for n,item in enumerate(narrations,1):
            pos=item.get("route_index",min(n-1,len(xy)-1))
            if xy: pins.append('<g><circle cx="%.1f" cy="%.1f" r="14" fill="#3157d5"/><text x="%.1f" y="%.1f" text-anchor="middle" fill="white">%d</text></g>'%(xy[pos][0],xy[pos][1],xy[pos][0],xy[pos][1]+5,n))
        dots=('<circle cx="%.1f" cy="%.1f" r="8" fill="#24a05a"/><circle cx="%.1f" cy="%.1f" r="8" fill="#d23c3c"/>'%(xy[0][0],xy[0][1],xy[-1][0],xy[-1][1])) if xy else ""
        map_svg='<svg viewBox="0 0 800 340" role="img" aria-label="Walk route"><path d="%s" fill="none" stroke="#5685d6" stroke-width="5" stroke-linecap="round"/>%s%s</svg>'%(path,dots,"".join(pins))
    else: map_svg="<p>No route points were recorded.</p>"
    timeline=[]
    for item in narrations:
        badge="model %s"%html.escape(str(item.get("model", ""))) if item.get("source")=="llm" else "template fallback"
        timeline.append('<article><small>%s · %s</small><h3>%s</h3><p>%s</p><p>%s</p><small>Guard blocks: %s</small></article>'%(html.escape(str(item.get("elapsed",""))),html.escape(str(item.get("position",""))),html.escape(str(item.get("place",""))),html.escape(str(item.get("text",""))),badge,html.escape(", ".join(item.get("rejected",[])) or "none")))
    stats=walk.get("stats",{})
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Walk summary</title><style>
:root{color-scheme:light dark;font:16px system-ui}body{margin:auto;max-width:980px;padding:1rem;background:Canvas;color:CanvasText}svg{width:100%;background:color-mix(in srgb,Canvas 92%,#5685d6);border-radius:1rem}svg text{font:14px system-ui}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.7rem}.stat,article{padding:1rem;border:1px solid #8885;border-radius:.8rem}.stat b{display:block;font-size:1.3rem}article{margin:.8rem 0}small{opacity:.75}</style><h1>Walk summary</h1>%s<section>%s</section><h2>Narration timeline</h2>%s</html>'''%(map_svg,"".join('<div class="stat"><small>%s</small><b>%s</b></div>'%(html.escape(k.replace("_"," ").title()),html.escape(str(v))) for k,v in stats.items()),"".join(timeline))

def demo():
    return {"route":[{"lat":0,"lon":0},{"lat":.001,"lon":.001},{"lat":.002,"lon":.001}],"narrations":[{"place":"Fictional Garden","text":"This is a fictional garden.","position":"about 40 metres ahead","source":"template","elapsed":"00:12","route_index":1}],"stats":{"Distance":"310 m","Time":"4 min","Pace":"12:54/km","Places":1,"Avg model latency":"0.0 s","Guard rejections":0}}

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--demo": data=demo()
    elif len(sys.argv)>1: data=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else: print("usage: summary.py --demo | walks/file.json"); raise SystemExit(2)
    out=Path("walk-summary.html"); out.write_text(build_html(data),encoding="utf-8"); print(out)

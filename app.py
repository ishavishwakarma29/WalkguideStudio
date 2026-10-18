"""Command line walking guide."""
import argparse, datetime, json, math, time, xml.etree.ElementTree as ET
from pathlib import Path
from narrator import narrate
from sources import bearing, compass, haversine, nearby
from speak import make_speaker
from summary import build_html

def interpolate_walk(text, spacing=20):
    coords=[]
    for pair in text.split(";"):
        lat,lon=map(float,pair.split(",")); coords.append((lat,lon))
    out=[]
    for a,b in zip(coords,coords[1:]):
        distance=haversine(*a,*b); steps=max(1,int(math.ceil(distance/spacing)))
        for i in range(steps):
            f=i/steps; out.append((a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f))
    if coords: out.append(coords[-1])
    return out

def _gpx(path):
    root=ET.parse(path).getroot(); out=[]
    for pt in root.iter():
        if pt.tag.endswith("trkpt") or pt.tag.endswith("rtept") or pt.tag.endswith("wpt"):
            out.append((float(pt.attrib["lat"]),float(pt.attrib["lon"])))
    return interpolate_walk(";".join("%s,%s"%p for p in out)) if len(out)>1 else out

def where(distance, direction, heading=None, bearing_to=None):
    distance=max(1,int(round(distance/10)*10))
    if heading is None or bearing_to is None: return "about %d metres %s"%(distance,direction)
    relative=(bearing_to-heading+360)%360
    if relative<35 or relative>=325: side="ahead of you"
    elif relative<145: side="on your right"
    elif relative<215: side="behind you"
    else: side="on your left"
    return "about %d metres %s"%(distance,side)

def run(args):
    cache=Path(args.cache); state=Path(args.state)
    if args.reset:
        try: state.unlink()
        except OSError: pass
    try: visited=set(json.loads(state.read_text()).get("visited",[]))
    except Exception: visited=set()
    if args.prefetch:
        if args.lat is None or args.lon is None: raise SystemExit("--prefetch requires --lat and --lon")
        from sources import cell_for
        clat,clon=cell_for(args.lat,args.lon)
        for i in range(-1,2):
            for j in range(-1,2): nearby(clat+i*.01+.005,clon+j*.01+.005,cache,args.offline,1500)
        print("Prefetch complete."); return
    if args.walk: points=interpolate_walk(args.walk)
    elif args.gpx: points=_gpx(args.gpx)
    elif args.lat is not None and args.lon is not None: points=[(args.lat,args.lon)]*3
    elif args.termux:
        points=[]
        for _ in range(3):
            try:
                import subprocess
                data=json.loads(subprocess.check_output(["termux-location","-p","gps"],timeout=10,text=True)); points.append((data["latitude"],data["longitude"]))
            except Exception: print("Location unavailable; retrying in 5 seconds."); time.sleep(5)
    else: raise SystemExit("Choose --lat/--lon, --walk, --gpx, or --termux")
    speaker=None if args.no_speak else make_speaker(args.piper_model)
    route=[]; narrations=[]; last_speak=-1e9; previous=None; heading=None; vtime=0.0
    for idx,(lat,lon) in enumerate(points):
        if args.walk or args.gpx:
            if previous:
                step=haversine(*previous,lat,lon); vtime+=step/1.4
                if step>5: heading=bearing(*previous,lat,lon)
        else: vtime=idx*args.tick
        route.append({"lat":lat,"lon":lon,"time":vtime})
        try: candidates=nearby(lat,lon,cache,args.offline,args.trigger)
        except Exception: candidates=[]
        candidates=[p for p in candidates if p.get("id") not in visited]
        if candidates and vtime-last_speak>=args.cooldown:
            def rank(p): return sum(len(str(f)) for f in p.get("facts",[]))+ (2 if p.get("source")=="wikipedia" else 0)-p["dist"]/40
            poi=max(candidates,key=rank); direction=compass(poi["bearing"])
            pos=where(poi["dist"],direction,heading,poi["bearing"])
            text,meta=narrate(poi,pos,model=args.model,host=args.ollama_host)
            print("%s — %s"%(poi["name"],text))
            if speaker:
                try: speaker(text)
                except Exception as exc: print("Speech playback unavailable: %s"%exc)
            visited.add(poi.get("id")); last_speak=vtime
            entry={"place":poi["name"],"text":text,"position":pos,"source":meta["source"],"model":args.model,"elapsed":"%02d:%02d"%(vtime//60,vtime%60),"route_index":idx,"rejected":meta["rejected"],"latency_s":meta["latency_s"]}
            narrations.append(entry)
            state.parent.mkdir(parents=True,exist_ok=True); state.write_text(json.dumps({"visited":sorted(visited)},indent=2),encoding="utf-8")
            with open(args.metrics,"a",encoding="utf-8") as f: f.write(json.dumps(entry,ensure_ascii=False)+"\n")
        previous=(lat,lon)
    distance=sum(haversine(a["lat"],a["lon"],b["lat"],b["lon"]) for a,b in zip(route,route[1:]))
    latency=[x["latency_s"] for x in narrations if x["source"]=="llm"]
    blocked=sum(len(x["rejected"]) for x in narrations)
    stats={"distance_m":round(distance),"time_s":round(vtime),"places":len(narrations),"model":sum(x["source"]=="llm" for x in narrations),"template":sum(x["source"]!="llm" for x in narrations),"guard_rejections":blocked,"mean_latency_s":round(sum(latency)/len(latency),2) if latency else 0}
    print("Summary: {places} narrations ({model} model, {template} template), {guard_rejections} guard rejections, mean model latency {mean_latency_s}s.".format(**stats))
    walk={"route":route,"narrations":narrations,"stats":stats}; folder=Path("walks"); folder.mkdir(exist_ok=True)
    stamp=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); j=folder/("walk-"+stamp+".json"); j.write_text(json.dumps(walk,indent=2),encoding="utf-8"); j.with_suffix(".html").write_text(build_html(walk),encoding="utf-8")

def main():
    p=argparse.ArgumentParser(description="Offline-first walking audio guide")
    p.add_argument("--lat",type=float); p.add_argument("--lon",type=float); p.add_argument("--walk"); p.add_argument("--gpx"); p.add_argument("--termux",action="store_true")
    p.add_argument("--model",default="gemma3:1b"); p.add_argument("--ollama-host",default="http://localhost:11434"); p.add_argument("--piper-model"); p.add_argument("--trigger",type=float,default=60); p.add_argument("--cooldown",type=float,default=15); p.add_argument("--tick",type=float,default=2); p.add_argument("--offline",action="store_true"); p.add_argument("--prefetch",action="store_true"); p.add_argument("--no-speak",action="store_true"); p.add_argument("--reset",action="store_true"); p.add_argument("--cache",default="cache"); p.add_argument("--state",default="visited.json"); p.add_argument("--metrics",default="metrics.jsonl")
    args=p.parse_args(); run(args)
if __name__=="__main__": main()

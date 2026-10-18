"""Build a self-contained offline tour folder from operator notes."""
import argparse, html, json, re, sys
from pathlib import Path
from narrator import narrate
from sources import haversine, nearby
from speak import synth
from summary import build_html

def slugify(text): return re.sub(r"-+","-",re.sub(r"[^a-z0-9]+","-",text.casefold())).strip("-") or "tour"

def sentences(text): return [s.strip() for s in re.split(r"(?<=[.!?])\s+",text.strip()) if s.strip()]

def build_tour(data, out_root="tours", model="gemma3:1b", host="http://localhost:11434", piper_model=None, enrich=True):
    stops=data.get("stops",[]); root=Path(out_root)/slugify(data.get("title","tour")); audio=root/"audio"; audio.mkdir(parents=True,exist_ok=True)
    report=[]; tour=[]; points=[]
    for i,stop in enumerate(stops,1):
        notes=sentences(stop.get("notes",""))
        facts=notes[:]
        if enrich:
            try:
                nearby_pois=nearby(stop["lat"],stop["lon"],root/"cache",False,100)
                match=next((p for p in nearby_pois if p.get("name","").casefold()==stop["name"].casefold()),None)
                if match: facts.extend(match.get("facts",[])[:3])
            except Exception: pass
        facts=facts[:8]
        system="You are a friendly tour guide. Return only 3 to 5 short spoken sentences, with no heading, bullet, markdown, or generic introduction. Start with the exact label 'Stop %d of %d.' and then narrate using only the facts. Do not add facts, names, numbers, dates, or claims beyond the supplied notes."%(i,len(stops))
        text,meta=narrate({"name":stop["name"]},"Stop %d of %d"%(i,len(stops)),facts,model,host,system,max_sentences=5)
        # Make the stop number a required grounded opening in deterministic fallback too.
        if not text.casefold().startswith(("stop %d"%i).casefold()):
            text="Stop %d of %d. "%(i,len(stops))+text
        audio_path=synth(text,audio/("stop-%02d"%i),piper_model)
        rel=Path(audio_path).relative_to(root).as_posix() if audio_path else None
        tour.append({"name":stop["name"],"lat":stop["lat"],"lon":stop["lon"],"text":text,"audio":rel,"index":i})
        report.append({"stop":stop["name"],"source":meta["source"],"latency_s":meta["latency_s"],"rejections":meta["rejected"],"audio":bool(audio_path)})
        points.append({"lat":stop["lat"],"lon":stop["lon"]})
    # Browser data closes script tags safely.
    payload=json.dumps({"title":data.get("title","Tour"),"operator":data.get("operator",""),"stops":tour},ensure_ascii=False).replace("</","<\\/")
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Tour</title><style>
:root{color-scheme:light dark;font:16px system-ui}body{margin:auto;max-width:900px;padding:1rem;background:Canvas;color:CanvasText}svg{width:100%;height:auto;max-height:380px;background:color-mix(in srgb,Canvas 92%,#5685d6);border-radius:1rem}.stop{padding:1rem;border:1px solid #8886;border-radius:1rem;margin:.8rem 0}.current{outline:3px solid #3157d5}.played{opacity:.7}button{font:inherit;padding:.7rem 1rem}audio{width:100%}</style><h1 id="title"></h1><p id="operator"></p><svg id="map" viewBox="0 0 800 360" aria-label="Tour route"></svg><label><input id="auto" type="checkbox"> Auto-play when I arrive (requires HTTPS)</label><p id="status"></p><div id="stops"></div><audio id="player" controls></audio><script type="application/json" id="tour-data">%s</script><script>
const tour=JSON.parse(document.querySelector('#tour-data').textContent), stops=tour.stops; let current=-1, played=new Set(), you=null, positions=[];
document.querySelector('#title').textContent=tour.title;document.querySelector('#operator').textContent=tour.operator;
const list=document.querySelector('#stops'), player=document.querySelector('#player'), svg=document.querySelector('#map');
function play(i){if(i<0||i>=stops.length||(!player.paused&&current!==i))return;current=i;played.add(i);render();if(stops[i].audio){player.src=stops[i].audio;player.play().catch(()=>{});}else{speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(stops[i].text));}}
player.onended=()=>{current=-1;render()};
function render(){list.innerHTML='';stops.forEach((s,i)=>{let a=document.createElement('article');a.className='stop '+(current===i?'current ':'')+(played.has(i)?'played':'');let h=document.createElement('h2');h.textContent='Stop '+s.index+': '+s.name;let p=document.createElement('p');p.textContent=s.text;let b=document.createElement('button');b.textContent='Play';b.onclick=()=>play(i);a.append(h,p,b);list.append(a)});draw()}
function draw(){svg.innerHTML='';if(!stops.length)return;let la=stops.map(s=>s.lat),lo=stops.map(s=>s.lon),minA=Math.min(...la),maxA=Math.max(...la),minO=Math.min(...lo),maxO=Math.max(...lo);positions=stops.map(s=>[50+(s.lon-minO)/(maxO-minO||1)*700,320-(s.lat-minA)/(maxA-minA||1)*280]);let path=document.createElementNS('http://www.w3.org/2000/svg','polyline');path.setAttribute('points',positions.map(x=>x.join(',')).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke','#5685d6');path.setAttribute('stroke-width','4');path.setAttribute('stroke-dasharray','10 9');svg.append(path);positions.forEach((p,i)=>{let c=document.createElementNS(svg.namespaceURI,'circle');c.setAttribute('cx',p[0]);c.setAttribute('cy',p[1]);c.setAttribute('r','15');c.setAttribute('fill',i===current?'#3157d5':played.has(i)?'#777':'#8a62c2');svg.append(c);let t=document.createElementNS(svg.namespaceURI,'text');t.setAttribute('x',p[0]);t.setAttribute('y',p[1]+5);t.setAttribute('text-anchor','middle');t.setAttribute('fill','white');t.textContent=i+1;svg.append(t)});if(you){let c=document.createElementNS(svg.namespaceURI,'circle');c.setAttribute('cx',you[0]);c.setAttribute('cy',you[1]);c.setAttribute('r','9');c.setAttribute('fill','#168cff');svg.append(c)}}
document.querySelector('#auto').onchange=e=>{if(!e.target.checked)return;if(!navigator.geolocation){e.target.checked=false;return}navigator.geolocation.watchPosition(pos=>{let lat=pos.coords.latitude,lon=pos.coords.longitude;let idx=stops.map((s,i)=>[Math.hypot((s.lat-lat)*111000,(s.lon-lon)*111000*Math.cos(lat*Math.PI/180)),i]).sort((a,b)=>a[0]-b[0])[0];you=positions[idx[1]];draw();document.querySelector('#status').textContent='Location updated';if(idx[0]<=40&&!played.has(idx[1])&&(player.paused||!player.src))play(idx[1]);},err=>document.querySelector('#status').textContent='Location unavailable: '+err.message,{enableHighAccuracy:true,maximumAge:5000});};render();
</script></html>'''.replace("%s",payload,1)
    (root/"index.html").write_text(page,encoding="utf-8")
    (root/"build_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return root

def main():
    p=argparse.ArgumentParser();p.add_argument("input");p.add_argument("--model",default="gemma3:1b");p.add_argument("--ollama-host",default="http://localhost:11434");p.add_argument("--piper-model");p.add_argument("--no-enrich",action="store_true");a=p.parse_args()
    data=json.loads(Path(a.input).read_text(encoding="utf-8"));print(build_tour(data,model=a.model,host=a.ollama_host,piper_model=a.piper_model,enrich=not a.no_enrich))
if __name__=="__main__":main()

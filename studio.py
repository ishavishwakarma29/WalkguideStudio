"""Local-first web studio for operators to create Gemma-powered offline tours."""
import argparse
import json
import re
import urllib.error
import urllib.request
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from tourpack import build_tour, slugify

ROOT = Path(__file__).resolve().parent
TOURS = ROOT / "tours"

PAGE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#f5f4ef"><title>Walkguide Studio — sellable audio tours</title><style>
:root{font:16px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#18251f;background:#f5f4ef;--green:#145b42;--mint:#dff3e7;--line:#d9dfd9;--muted:#65736b;--paper:#fffefa;--orange:#f2a65a}*{box-sizing:border-box}body{margin:0}header{display:flex;justify-content:space-between;align-items:center;padding:20px max(24px,calc((100vw - 1160px)/2));border-bottom:1px solid var(--line);background:#fbfaf6}.brand{font-weight:850;font-size:1.15rem;letter-spacing:-.04em}.brand span{color:var(--green)}.local{font-size:.82rem;color:var(--green);background:var(--mint);padding:7px 12px;border-radius:20px}.wrap{max-width:1160px;margin:auto;padding:40px 24px 72px}.hero{display:grid;grid-template-columns:1.2fr .8fr;gap:24px;align-items:end;margin-bottom:26px}.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.72rem;font-weight:800;color:var(--green)}h1{font-size:clamp(2.3rem,5vw,4.2rem);letter-spacing:-.065em;line-height:.99;margin:12px 0 18px;max-width:700px}.hero p{color:var(--muted);max-width:680px;margin:0;font-size:1.08rem}.engine{background:#183b2d;color:white;padding:20px 22px;border-radius:18px}.engine .eyebrow{color:#a9e0bf}.engine strong{display:block;font-size:1.1rem;margin:4px 0}.engine p{color:#d0dfd5;font-size:.9rem}.engine-status{display:inline-flex;align-items:center;gap:8px;background:#ffffff1a;border-radius:20px;padding:5px 10px;font-size:.78rem}.dot{width:8px;height:8px;border-radius:50%;background:#ffc568}.dot.ok{background:#7de2a1}.layout{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(280px,.6fr);gap:22px;align-items:start}.card{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:24px;box-shadow:0 8px 26px #203b2b08}.card h2{font-size:1.3rem;letter-spacing:-.035em;margin:0}.sub{color:var(--muted);font-size:.9rem;margin:5px 0 22px}.field{margin:15px 0}.field label,.stop label{display:block;font-weight:700;font-size:.83rem;margin-bottom:6px}.field input,.stop input,.stop textarea{width:100%;font:inherit;border:1px solid #cbd4cc;background:white;border-radius:9px;padding:10px 12px;color:#18251f}.field input:focus,.stop input:focus,.stop textarea:focus{outline:3px solid #bce5cc;border-color:var(--green)}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}.stop{border:1px solid var(--line);border-radius:14px;padding:16px;margin:14px 0;background:#fff}.stop-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.stop-head strong{font-size:.95rem}.remove{border:0;background:none;color:#9a4d36;cursor:pointer}.stop textarea{min-height:96px;resize:vertical}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.btn{border:0;border-radius:10px;padding:12px 17px;font:inherit;font-weight:800;cursor:pointer}.primary{background:var(--green);color:white}.primary:disabled{opacity:.45;cursor:not-allowed}.secondary{background:#e9eee9;color:#234433}.result{display:none;margin-top:18px;padding:16px;border:1px solid #acd8b9;background:#effaf2;border-radius:12px}.result.show{display:block}.result a{color:#145b42;font-weight:800;margin-right:15px}.side{position:sticky;top:18px}.side h3{margin:0 0 10px}.steps{padding:0;list-style:none;counter-reset:steps}.steps li{counter-increment:steps;display:grid;grid-template-columns:30px 1fr;gap:10px;margin:15px 0;color:#526159;font-size:.9rem}.steps li:before{content:counter(steps);width:27px;height:27px;display:grid;place-items:center;border-radius:50%;background:var(--mint);color:var(--green);font-weight:800}.notice{border-left:3px solid var(--orange);padding:9px 12px;background:#fff6e9;color:#70512d;font-size:.8rem;border-radius:0 8px 8px 0;margin-top:18px}.footer{color:var(--muted);text-align:center;font-size:.82rem;margin:28px 0}.error{color:#972f26!important}.hidden{display:none}@media(max-width:850px){.hero,.layout{grid-template-columns:1fr}.side{position:static}.hero{align-items:start}.engine{max-width:600px}}@media(max-width:520px){header{padding:14px 16px}.wrap{padding:28px 14px 48px}.card{padding:17px}.grid2{grid-template-columns:1fr}h1{font-size:2.55rem}.local{font-size:.72rem}}
</style></head><body><header><div class="brand">walk<span>guide</span> studio</div><div class="local">● Private on this computer</div></header><main class="wrap"><div class="hero"><div><div class="eyebrow">For independent tour operators</div><h1>Turn your local knowledge into a tour people can buy.</h1><p>Write the stops once. Gemma turns your notes into a grounded audio guide. Download one folder to sell, share, and use offline—without a narration API bill.</p></div><div class="engine"><div class="eyebrow">Open model engine</div><strong>Google Gemma · running locally</strong><p>Your stop notes stay on this computer. The model drafts the narration; a grounding check blocks unsupported names and numbers.</p><div class="engine-status"><span class="dot" id="dot"></span><span id="engineStatus">Checking local Gemma…</span></div></div></div><div class="layout"><section class="card"><h2>Build your first tour</h2><p class="sub">Start with the sample or replace it with your own route and stories.</p><div class="field"><label for="title">Tour name</label><input id="title" value="Bengaluru: Green Spaces & Granite" maxlength="90"></div><div class="field"><label for="operator">Your business name</label><input id="operator" value="Walkguide demo route" maxlength="90"></div><div id="stops"></div><div class="actions"><button class="btn secondary" id="add">＋ Add a stop</button><button class="btn primary" id="build" disabled>Create Gemma tour →</button></div><div class="result" id="result"></div></section><aside class="card side"><h3>How your side hustle works</h3><ol class="steps"><li><span><b>Enter your expertise.</b> Your real notes are the source of truth; no generic place facts are made up.</span></li><li><span><b>Gemma writes each stop.</b> Local open-weight inference means no per-tour API fee and your customer material stays on-device.</span></li><li><span><b>Sell the package.</b> Give customers the ZIP. They open the tour on their phone and can download it for a self-guided walk.</span></li></ol><div class="notice"><b>Bengaluru demo route:</b> These are researched real places. Pins mark approximate outdoor viewpoints, not pedestrian directions. Check local access, closures, and walking paths before recording or visiting.</div></aside></div><p class="footer">Built for operators with a few great stories and no time to hire an app team.</p></main><script>
const initial=[{name:'Cubbon Park',lat:12.97669,lon:77.59500,notes:'Cubbon Park is officially known as Sri Chamarajendra Park. It was established in 1870 by John Meade, then acting Commissioner of Mysore. Major General Richard Sankey conceived the park landscape. It was officially renamed Sri Chamarajendra Park in 1927.'},{name:'Vidhana Soudha',lat:12.979722,lon:77.590556,notes:'Vidhana Soudha houses Karnataka’s State Legislature and Secretariat. It was conceived by Kengal Hanumanthaiah, then Chief Minister of Mysore State, and completed in 1956. The Karnataka Legislature describes its architecture as Neo-Dravidian. It is built largely with Bangalore granite.'},{name:'Attara Kacheri (Karnataka High Court)',lat:12.97806,lon:77.59254,notes:'Attara Kacheri houses the High Court of Karnataka. The Bengaluru Urban district describes it as a red brick and stone building in the Graeco-Roman architectural style.'}];const list=document.querySelector('#stops');let count=0;
function addStop(data={name:'',lat:'',lon:'',notes:''}){count++;let n=count;let el=document.createElement('div');el.className='stop';el.innerHTML=`<div class="stop-head"><strong>Stop <span class="number"></span></strong><button class="remove" type="button">Remove</button></div><div class="field"><label>Name</label><input class="name" maxlength="100" required></div><div class="grid2"><div class="field"><label>Latitude</label><input class="lat" type="number" step="any" required></div><div class="field"><label>Longitude</label><input class="lon" type="number" step="any" required></div></div><div class="field"><label>Your notes (the facts Gemma can use)</label><textarea class="notes" required maxlength="5000" placeholder="What do visitors see? What story or detail do you know? Use only facts you can stand behind."></textarea></div>`;el.querySelector('.name').value=data.name;el.querySelector('.lat').value=data.lat;el.querySelector('.lon').value=data.lon;el.querySelector('.notes').value=data.notes;el.querySelector('.remove').onclick=()=>{if(list.children.length>1)el.remove();renumber()};list.append(el);renumber()}
function renumber(){[...list.children].forEach((x,i)=>x.querySelector('.number').textContent=i+1)}initial.forEach(addStop);document.querySelector('#add').onclick=()=>addStop();
async function health(){try{let r=await fetch('/health'),d=await r.json();document.querySelector('#engineStatus').textContent=d.ready?`Ready · ${d.model}`:(d.message||'Start Ollama and install Gemma');document.querySelector('#dot').classList.toggle('ok',d.ready);document.querySelector('#build').disabled=!d.ready}catch(e){document.querySelector('#engineStatus').textContent='Studio server unavailable'}}health();
document.querySelector('#build').onclick=async()=>{let btn=document.querySelector('#build'),result=document.querySelector('#result');btn.disabled=true;btn.textContent='Gemma is writing your tour…';result.className='result';let data={title:document.querySelector('#title').value.trim(),operator:document.querySelector('#operator').value.trim(),stops:[...list.children].map(x=>({name:x.querySelector('.name').value.trim(),lat:x.querySelector('.lat').value.trim()===''?null:Number(x.querySelector('.lat').value),lon:x.querySelector('.lon').value.trim()===''?null:Number(x.querySelector('.lon').value),notes:x.querySelector('.notes').value.trim()}))};try{if(!data.title||!data.operator||data.stops.some(s=>!s.name||!s.notes||!Number.isFinite(s.lat)||!Number.isFinite(s.lon)))throw Error('Fill in the tour and business names, and give every stop a name, valid coordinates, and notes.');let r=await fetch('/build',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),d=await r.json();if(!r.ok)throw Error(d.error||'Build failed');result.innerHTML=`<b>Your tour package is ready.</b><p>${d.modelStops} stops narrated by Gemma · ${d.fallbackStops} safety fallbacks · ${d.audioStops}/${d.totalStops} with audio files</p><a href="${d.preview}" target="_blank">Preview the customer tour ↗</a><a href="${d.download}">Download tour ZIP ↓</a>`;result.classList.add('show')}catch(e){result.innerHTML=`<b class="error">Tour not packaged.</b><p class="error">${e.message}</p>`;result.classList.add('show')}finally{btn.disabled=false;btn.textContent='Create Gemma tour →';health()}};
</script></body></html>'''


def gemma_status(host, model):
    try:
        request = urllib.request.Request(host.rstrip("/") + "/api/tags", headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = [item.get("name", "") for item in data.get("models", [])]
        ready = any(name == model or name.split(":")[0] == model.split(":")[0] and name.startswith("gemma") for name in models)
        return {"ready": ready, "model": model if ready else "", "message": "Gemma model not installed. Run: ollama pull %s" % model if not ready else ""}
    except Exception:
        return {"ready": False, "model": "", "message": "Start Ollama, then install Gemma with: ollama pull %s" % model}


class Handler(BaseHTTPRequestHandler):
    model = "gemma3:1b"
    host = "http://localhost:11434"
    piper_model = None

    def log_message(self, fmt, *args):
        print("[studio] " + fmt % args)

    def _json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        if parsed.path == "/health":
            self._json(200, gemma_status(self.host, self.model)); return
        match = re.fullmatch(r"/download/([a-z0-9-]+)", parsed.path)
        if match:
            folder = TOURS / match.group(1)
            if not folder.is_dir(): self._json(404, {"error": "Tour package not found"}); return
            mem = BytesIO()
            with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in folder.rglob("*"):
                    if path.is_file() and "cache" not in path.parts:
                        zf.write(path, Path(folder.name) / path.relative_to(folder))
            body = mem.getvalue()
            self.send_response(200); self.send_header("Content-Type", "application/zip"); self.send_header("Content-Disposition", 'attachment; filename="%s-tour.zip"' % match.group(1)); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        match = re.fullmatch(r"/preview/([a-z0-9-]+)", parsed.path)
        if match:
            path = (TOURS / match.group(1) / "index.html").resolve()
            if not path.is_file() or not path.is_relative_to(TOURS.resolve()): self.send_error(404); return
            body = path.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/build": self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 200000: self._json(413, {"error": "Tour form is too large"}); return
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            stops = data.get("stops", [])
            if not data.get("title", "").strip() or not data.get("operator", "").strip() or not stops:
                self._json(400, {"error": "Add a tour name, business name, and at least one stop."}); return
            for stop in stops:
                if not stop.get("name", "").strip() or not stop.get("notes", "").strip():
                    self._json(400, {"error": "Every stop needs a name and operator notes."}); return
                try: lat, lon = float(stop["lat"]), float(stop["lon"])
                except (TypeError, ValueError):
                    self._json(400, {"error": "Every stop needs valid latitude and longitude coordinates."}); return
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    self._json(400, {"error": "Stop coordinates are outside valid latitude/longitude bounds."}); return
            status = gemma_status(self.host, self.model)
            if not status["ready"]:
                self._json(503, {"error": status["message"]}); return
            folder = build_tour(data, TOURS, self.model, self.host, self.piper_model, enrich=False)
            report = json.loads((folder / "build_report.json").read_text(encoding="utf-8"))
            model_count = sum(row["source"] == "llm" for row in report)
            fallback_count = len(report) - model_count
            if model_count == 0:
                reasons = list(dict.fromkeys(reason for row in report for reason in row.get("rejections", [])))[:4]
                detail = " Guard blocks: " + "; ".join(reasons) if reasons else " Check the local model status and try again."
                self._json(502, {"error": "Gemma did not produce grounded narration for any stop, so no ZIP was offered." + detail}); return
            self._json(200, {"model": self.model, "modelStops": model_count, "fallbackStops": fallback_count, "audioStops": sum(row["audio"] for row in report), "totalStops": len(report), "preview": "/preview/" + folder.name, "download": "/download/" + folder.name})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._json(400, {"error": "Please check the tour form: %s" % exc})
        except Exception as exc:
            self._json(500, {"error": "Tour build failed safely: %s" % exc})


def main():
    parser = argparse.ArgumentParser(description="Open the local Walkguide operator studio")
    parser.add_argument("--model", default="gemma3:1b")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--piper-model")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    Handler.model, Handler.host, Handler.piper_model = args.model, args.ollama_host, args.piper_model
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = "http://127.0.0.1:%d" % args.port
    print("Walkguide Studio is local at %s" % url)
    print("Model status: %s" % gemma_status(args.ollama_host, args.model)["message"] or args.model)
    try: webbrowser.open(url)
    except Exception: pass
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStudio stopped.")
    finally: server.server_close()


if __name__ == "__main__": main()

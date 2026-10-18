"""Offline-first place discovery from OpenStreetMap and Wikipedia."""
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
WIKI = "https://en.wikipedia.org/w/api.php"


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.atan2(math.sqrt(a), math.sqrt(1-a))


def bearing(lat1, lon1, lat2, lon2):
    p1, p2, dl = map(math.radians, (lat1, lat2, lon2-lon1))
    y, x = math.sin(dl)*math.cos(p2), math.cos(p1)*math.sin(p2)-math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x))+360) % 360


def compass(deg):
    return ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][int((deg % 360 + 22.5)//45) % 8]


def cell_for(lat, lon):
    return math.floor(lat*100)/100, math.floor(lon*100)/100


def _request(url, data=None, timeout=12):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "walkguide/1.0 (offline-first audio guide)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _overpass(lat, lon, radius):
    query = '[out:json][timeout:15];(nwr(around:%s,%s,%s)[name][historic];nwr(around:%s,%s,%s)[name][tourism~"^(museum|artwork|attraction|viewpoint|gallery)$"];nwr(around:%s,%s,%s)[name][leisure~"^(park|garden|nature_reserve)$"];nwr(around:%s,%s,%s)[name][amenity=place_of_worship];nwr(around:%s,%s,%s)[name][natural~"^(peak|water|spring|wood)$"];node(around:%s,%s,%s)[name][natural=tree][species];);out center tags 80;' % tuple([radius, lat, lon]*6)
    body = urllib.parse.urlencode({"data": query}).encode()
    error = None
    for endpoint in OVERPASS:
        try:
            return _request(endpoint, body).get("elements", [])
        except Exception as exc:
            error = exc
    raise error or RuntimeError("Overpass unavailable")


def _sentences(tags):
    out = []
    kinds = {"church":"church", "chapel":"chapel", "mosque":"mosque", "temple":"temple", "synagogue":"synagogue", "cathedral":"cathedral", "place_of_worship":"place of worship", "museum":"museum", "gallery":"art gallery", "park":"park", "garden":"garden", "nature_reserve":"nature reserve", "peak":"mountain peak", "spring":"spring", "wood":"woodland", "water":"water feature", "viewpoint":"viewpoint", "attraction":"attraction", "artwork":"work of art"}
    for key in ("building", "amenity", "tourism", "leisure", "historic", "natural"):
        val = tags.get(key)
        if val in kinds:
            out.append("It is a %s." % kinds[val])
            break
    if tags.get("historic") and tags["historic"] not in ("yes", "building") and not any("historic site" in x for x in out):
        out.append("It is a historic site.")
    if tags.get("start_date"):
        date = str(tags["start_date"])
        if re.match(r"^\d{3,4}$", date): out.append("It dates from %s." % date)
    if tags.get("architect"): out.append("The architect was %s." % tags["architect"])
    if tags.get("species"): out.append("Its species is %s." % tags["species"])
    if tags.get("description"): out.append(str(tags["description"]).rstrip(". ") + ".")
    return list(dict.fromkeys(out))


def _osm(lat, lon, radius):
    found = []
    for el in _overpass(lat, lon, radius):
        tags = el.get("tags", {})
        name = tags.get("name")
        center = el.get("center", el)
        facts = _sentences(tags)
        if name and len(facts) >= 2 and "lat" in center and "lon" in center:
            found.append({"id": "osm:%s:%s" % (el.get("type"), el.get("id")), "name": name, "lat": center["lat"], "lon": center["lon"], "facts": facts, "source": "osm"})
    return found


def _wiki(lat, lon, radius):
    params = {"action":"query", "format":"json", "generator":"geosearch", "ggscoord":"%s|%s" % (lat, lon), "ggsradius": min(10000, radius), "ggslimit": 30, "prop":"extracts|coordinates", "exintro":1, "explaintext":1}
    try:
        data = _request(WIKI + "?" + urllib.parse.urlencode(params))
        pages = data.get("query", {}).get("pages", {}).values()
        result = []
        for page in pages:
            coords = page.get("coordinates", [{}])[0]
            intro = re.sub(r"\s+", " ", page.get("extract", "")).strip()
            sentences = re.split(r"(?<=[.!?])\s+", intro)
            intro = " ".join(sentences[:4])
            if intro and coords:
                result.append({"id":"wiki:%s" % page.get("pageid"), "name":page.get("title", ""), "lat":coords.get("lat"), "lon":coords.get("lon"), "facts":[intro], "source":"wikipedia"})
        return result
    except Exception:
        raise


def fetch_pois(lat, lon, radius=800):
    osm, wiki = _osm(lat, lon, radius), _wiki(lat, lon, radius)
    merged = {p["name"].casefold(): p for p in osm}
    for p in wiki:
        key = p["name"].casefold()
        if key in merged:
            p["facts"] += merged[key]["facts"][:3]
        merged[key] = p
    return list(merged.values())


def nearby(lat, lon, cache_dir="cache", offline=False, max_dist=1000):
    clat, clon = cell_for(lat, lon)
    path = Path(cache_dir) / ("%.2f_%.2f.json" % (clat, clon))
    pois = None
    if path.exists():
        try: pois = json.loads(path.read_text(encoding="utf-8"))
        except Exception: pois = None
    if pois is None and not offline:
        center = (clat + .005, clon + .005)
        try:
            # Cache only when both source lookups complete successfully.
            osm = _osm(*center, 800)
            wiki = _wiki(*center, 800)
            merged = {p["name"].casefold():p for p in osm}
            for p in wiki:
                k = p["name"].casefold()
                if k in merged: p["facts"] += merged[k]["facts"][:3]
                merged[k] = p
            pois = list(merged.values())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(pois, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            print("Place lookup unavailable; using cache if present (%s)." % exc)
            pois = []
    pois = pois or []
    for p in pois:
        p["dist"] = haversine(lat, lon, p["lat"], p["lon"])
        p["bearing"] = bearing(lat, lon, p["lat"], p["lon"])
    return sorted([p for p in pois if p["dist"] <= max_dist], key=lambda x:x["dist"])

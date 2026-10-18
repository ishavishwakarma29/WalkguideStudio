"""Grounded narration with a strict deterministic fallback."""
import json, re, time, urllib.request

def build_prompt(place, location="", facts=None, max_sentences=3):
    lines = ["Place: " + str(place.get("name", "")), "Location: " + str(location)]
    lines += ["Fact: " + str(x) for x in (facts if facts is not None else place.get("facts", []))[:8]]
    lines.append("Write no more than %d short spoken sentences. Use only the supplied information." % max_sentences)
    return "\n".join(lines)

def _sentences(text):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]

def _strip_stop_heading(text, location):
    """Remove a model-echoed stop heading; tourpack adds a grounded opening."""
    label_text = str(location).strip()
    if not re.fullmatch(r"Stop\s+\d+\s+of\s+\d+", label_text, flags=re.I):
        return text
    label = re.escape(label_text)
    separator = r"(?:\s*[:：.!?—–-]\s*|\s*[\r\n]+\s*)"
    return re.sub(r"^\s*" + label + separator, "", text, count=1, flags=re.I)

def grounding_errors(text, source_text):
    errors=[]
    source_nums=set(re.findall(r"\d+(?:[.,]\d+)*", source_text))
    for n in re.findall(r"\d+(?:[.,]\d+)*", text):
        if n not in source_nums: errors.append("invented number: " + n)
    allowed=set(re.findall(r"[A-Z][a-zA-Z'-]*", source_text)) | {"I"}
    allowed |= {"North","South","East","West","north","south","east","west","North-east","North-west","South-east","South-west"}
    for match in re.finditer(r"\b[A-Z][a-zA-Z'-]*\b", text):
        word=match.group(0)
        prefix=text[:match.start()]
        is_first=not prefix.strip() or bool(re.search(r"[.!?]\s*$", prefix))
        if not is_first and word not in allowed: errors.append("ungrounded name: " + word)
    return errors

def template(place, location="", facts=None, max_sentences=3):
    name=place.get("name", "This place")
    bits=[]
    if location and re.fullmatch(r"Stop\s+\d+\s+of\s+\d+", str(location).strip(), flags=re.I):
        bits.append(str(location).strip() + ".")
    elif location: bits.append("%s is %s." % (name, location))
    for fact in (facts if facts is not None else place.get("facts", [])):
        clean=str(fact).strip()
        if clean: bits.append(clean if clean.endswith((".","!","?")) else clean+".")
    if not bits: bits=["You are near %s." % name]
    return " ".join(bits[:max_sentences])

def narrate(place, location="", facts=None, model="gemma3:1b", host="http://localhost:11434", system_prompt=None, max_sentences=3):
    facts=list(facts if facts is not None else place.get("facts", []))[:8]
    prompt=build_prompt(place, location, facts, max_sentences)
    source="\n".join([str(place.get("name", "")), str(location)]+facts)
    rejected=[]; start=time.monotonic(); attempts=0
    if model:
        for temperature in (.4,.1):
            attempts+=1
            try:
                body={"model":model,"stream":False,"messages":[{"role":"system","content":system_prompt or "You are a concise audio guide. Use only provided facts."},{"role":"user","content":prompt}],"options":{"temperature":temperature,"num_predict":140}}
                req=urllib.request.Request(host.rstrip("/")+"/api/chat", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
                with urllib.request.urlopen(req, timeout=18) as response: out=json.loads(response.read().decode())
                text=out.get("message",{}).get("content", "")
                text=re.sub(r"```.*?```|[*_#>`]", "", text, flags=re.S).strip()
                text=_strip_stop_heading(text, location)
                text=" ".join(_sentences(text)[:max_sentences])
                errors=grounding_errors(text, source)
                if text and not errors: return text,{"source":"llm","attempts":attempts,"rejected":rejected,"latency_s":time.monotonic()-start}
                rejected.extend(errors or ["empty response"])
            except Exception as exc: rejected.append("model unavailable: %s" % exc)
    return template(place, location, facts, max_sentences),{"source":"template","attempts":attempts,"rejected":rejected,"latency_s":time.monotonic()-start}

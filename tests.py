"""Plain-assert, network-free checks for walkguide."""
import json, tempfile
from pathlib import Path
from narrator import _strip_stop_heading, grounding_errors, narrate, template
from sources import nearby
from app import interpolate_walk, where

def run():
    source="Blue Hall Location: Stop 1 of 2 It is a fictional hall."
    assert grounding_errors("Blue Hall is a fictional hall.",source)==[]
    assert grounding_errors("Blue Hall is 1890 metres away.",source)
    assert grounding_errors("Blue Hall welcomes Alice.",source)
    assert _strip_stop_heading("Stop 2 of 3: This is a fictional stop.","Stop 2 of 3")=="This is a fictional stop."
    assert _strip_stop_heading("Stop 2 of 3\nThis is a fictional stop.","Stop 2 of 3")=="This is a fictional stop."
    place={"name":"Blue Hall","facts":["It is a fictional hall."]}
    assert template(place,"about 20 metres ahead of you").startswith("Blue Hall is")
    assert template(place,"Stop 1 of 3").startswith("Stop 1 of 3. It is a fictional hall.")
    text,meta=narrate(place,"nearby",model="",max_sentences=2)
    assert meta["source"]=="template" and text
    text,meta=narrate(place,"nearby",model="walkguide-test-no-server",host="http://127.0.0.1:1",max_sentences=2)
    assert meta["source"]=="template" and meta["attempts"]==2
    points=interpolate_walk("0,0;0,0.001")
    assert len(points)>2
    assert "ahead of you" in where(42,"east",0,0)
    assert "south-east" in where(42,"south-east")
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent.parent / "work") as td:
        p=Path(td)/"0.00_0.00.json"
        p.write_text(json.dumps([{"id":"x","name":"Fictional place","lat":0.001,"lon":0.001,"facts":["It is fictional."]}]))
        got=nearby(0.001,0.001,td,offline=True,max_dist=100)
        assert len(got)==1 and got[0]["dist"]==0
        assert nearby(1,1,td,offline=True)==[]
    print("All walkguide offline assertions passed.")

if __name__=="__main__":run()

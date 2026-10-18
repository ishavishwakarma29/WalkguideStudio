"""Optional offline speech adapters. All external programs are discovered at runtime."""
import os, platform, shutil, subprocess, tempfile
from pathlib import Path

def _which(*names):
    for name in names:
        found=shutil.which(name)
        if found: return found

def make_speaker(piper_model=None):
    piper=_which("piper") if piper_model else None
    player=_which("aplay","afplay","paplay","ffplay")
    if piper and player:
        def speak(text):
            with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as f: path=f.name
            try:
                subprocess.run([piper,"--model",piper_model,"--output_file",path],input=text,text=True,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                _play(player,path)
            finally:
                try: os.unlink(path)
                except OSError: pass
        return speak
    termux=_which("termux-tts-speak")
    if termux: return lambda text: subprocess.run([termux,text],check=False)
    if platform.system()=="Darwin" and _which("say"): return lambda text: subprocess.run(["say",text],check=False)
    engine=_which("espeak-ng","espeak")
    if engine: return lambda text: subprocess.run([engine,text],check=False)
    if platform.system()=="Windows":
        ps=_which("powershell") or _which("pwsh")
        if ps: return lambda text: subprocess.run([ps,"-NoProfile","-Command","Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak([Console]::In.ReadToEnd())"],input=text,text=True,check=False)
    return None

def _play(player,path):
    cmd=[player,path]
    if Path(player).name.lower()=="ffplay": cmd=[player,"-nodisp","-autoexit",path]
    subprocess.run(cmd,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def synth(text,base_path,piper_model=None):
    base=Path(base_path); base.parent.mkdir(parents=True,exist_ok=True); wav=base.with_suffix(".wav")
    try:
        piper=_which("piper") if piper_model else None
        if piper:
            subprocess.run([piper,"--model",piper_model,"--output_file",str(wav)],input=text,text=True,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        elif platform.system()=="Darwin" and _which("say"):
            subprocess.run(["say","-o",str(wav),"--data-format=LEI16@22050",text],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else:
            engine=_which("espeak-ng","espeak")
            if not engine: return None
            subprocess.run([engine,"-w",str(wav),text],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        ffmpeg=_which("ffmpeg")
        if ffmpeg:
            mp3=base.with_suffix(".mp3")
            try:
                subprocess.run([ffmpeg,"-y","-i",str(wav),str(mp3)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                return str(mp3)
            except Exception: pass
        return str(wav) if wav.exists() else None
    except Exception:
        return None

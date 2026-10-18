# Walkguide Studio

Built during **Hacktoberfest Week 2** for the [DEV Open-Source AI Challenge: Side Hustle](https://dev.to/devteam/join-the-hacktoberfest-open-source-ai-challenge-side-hustle-2550-in-prizes-across-18-winners-55ba?bb=264692).

## Demo

[![Watch the Walkguide demo](https://img.youtube.com/vi/NbL-dx2ZQpA/hqdefault.jpg)](https://youtu.be/NbL-dx2ZQpA)

Click the thumbnail to watch the video.

Walkguide Studio helps an independent walking-tour operator turn their own stop notes into a self-guided tour package. The operator enters the route and their local knowledge once; Gemma, running on the operator's computer through Ollama, drafts a short narration for each stop. A grounding check rejects unsupported names and numbers. The result is a static tour with a route map, transcripts, optional audio, and an offline ZIP that the operator can share or sell through their existing channel.

The main product flow is built around open-weight AI: Studio requires a local Gemma model before it can create a package. There is no hosted model API in the path and no per-narration API charge. The original command line tools remain available for automation and for the separate Walk Guide product.

## Start Studio on Windows

1. Install [Ollama](https://ollama.com/download).
2. Open PowerShell in this folder and run:

   ```powershell
   ollama pull gemma3:1b
   python studio.py
   ```

3. Studio opens at `http://127.0.0.1:8765`. If the browser does not open, paste that address into it.
4. Replace the clearly fictional sample route with a real tour name, business name, stop coordinates, and facts from your own notes. Select **Create Gemma tour**.
5. Preview the tour, then download the ZIP. It contains `index.html`, any generated audio files, and a build report. Share the ZIP with customers or host its contents on a static HTTPS site. The arrival auto-play option needs HTTPS and visitor location permission; manual stop playback works without location permission.

The model runs on the same computer as Studio. Tour names, notes, and generated text are sent to that local Ollama service and are not sent to a hosted AI API by this application. A computer needs enough memory and processing power to run Gemma. Audio files are optional and require Piper with a voice model, macOS `say`, or `espeak`/`espeak-ng`.

## Honest demo checklist

- Use a real operator's notes or explicitly say the sample route is fictional.
- Show the operator form, local Gemma status, generated narration, grounding report, preview, and downloaded ZIP.
- Play a generated audio file if a TTS engine is installed; otherwise demonstrate the transcript and explain that speech synthesis is the fallback.
- Ask one independent tour operator to try creating a route. Do not claim customer demand, sales, or savings until measured.
- The current fictional sample is for demonstrating the interface only; it is not evidence about a real place or a paying user.

## Tour Pack CLI

Input JSON has `title`, `operator`, and `stops` with `name`, `lat`, `lon`, and `notes`:

```powershell
python tourpack.py operator-tour.json --model gemma3:1b --piper-model .\voice.onnx --no-enrich
```

Output is `tours/<slug>/index.html`, optional files under `audio/`, and `build_report.json`. Enrichment is best effort and can be disabled. `--model ""` uses only the deterministic template fallback; that mode is useful for offline checks but does not demonstrate the challenge's open-weight AI requirement.

## Walk Guide

```powershell
python app.py --walk "48.8584,2.2945;48.8590,2.2950" --trigger 60
python app.py --gpx route.gpx --piper-model .\voice.onnx
python app.py --termux --model gemma3:1b
python app.py --lat 48.8584 --lon 2.2945 --prefetch
```

`--lat` and `--lon` make three fixed-location ticks. Simulated walks and GPX tracks advance at a virtual 1.4 m/s; GPS mode uses device time. `--offline` reads cache only. The guide stores cache JSON, visited IDs, and `metrics.jsonl` in the current directory; completed summaries go into `walks/` as JSON and self-contained HTML. Use `--model`, `--ollama-host`, `--piper-model`, `--trigger`, `--cooldown`, `--tick`, `--offline`, `--no-speak`, or `--reset` to adjust behavior.

## Checks

```powershell
python tests.py
python tourpack.py sample_tour.json --model "" --no-enrich
```

No pip packages are required. Place data lookups use public OpenStreetMap Overpass and Wikipedia endpoints when enabled; network errors degrade to cache or templates.

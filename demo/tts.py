"""Generate the narration audio with a local neural voice (Kokoro, runs offline).

    python demo/tts.py [voice]      # default af_heart; e.g. am_michael, bf_emma, bm_george

Model files are expected in ~/.cache/kokoro (kokoro-v1.0.onnx, voices-v1.0.bin) from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
Writes demo/audio/<id>.wav and stores each duration in demo/narration.json.
"""
import json
import pathlib
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

HERE = pathlib.Path(__file__).parent
CACHE = pathlib.Path.home() / ".cache" / "kokoro"
voice = sys.argv[1] if len(sys.argv) > 1 else "af_heart"
lang = "en-gb" if voice[0] == "b" else "en-us"

kokoro = Kokoro(str(CACHE / "kokoro-v1.0.onnx"), str(CACHE / "voices-v1.0.bin"))
segs = json.loads((HERE / "narration.json").read_text())
(HERE / "audio").mkdir(exist_ok=True)
total = 0.0
for s in segs:
    samples, sr = kokoro.create(s["text"], voice=voice, speed=1.0, lang=lang)
    samples = np.concatenate([samples, np.zeros(int(sr * 0.15), dtype=samples.dtype)])
    sf.write(HERE / "audio" / f"{s['id']}.wav", samples, sr)
    s["ref_duration"] = s.get("ref_duration", s["duration"])   # timings in record.py were tuned on these
    s["duration"] = round(len(samples) / sr, 2)
    total += s["duration"]
    print(s["id"], s["duration"])
(HERE / "narration.json").write_text(json.dumps(segs, indent=1, ensure_ascii=False))
print(f"voice {voice}: total speech {total:.1f}s")

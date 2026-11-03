# Whiteboard animation — instructions for Claude

This folder turns an illustration into a whiteboard-style MP4 (lines drawn, then colored).
Cloud sessions have no GPU, so always render on CPU.

## Setup (once per session)

If `.venv/bin/python` is missing, run `./setup.sh` from this folder (installs into `.venv`,
about 7 GB, a few minutes). Check `ffmpeg -version` works. If `scripts/download_model.py`
fails, carry on with `subject_first=False`.

## Render

```bash
.venv/bin/python -c "
import numpy as np; from PIL import Image
from handdraw.settings import Settings; from handdraw.render import render_video
img = np.asarray(Image.open('INPUT.png').convert('RGBA'))
s = Settings(mode='d', duration=5, width=1080, height=1350, fps=30,
             device='cpu', encoder='cpu', subject_first=False, show_hand=False)
print(render_video(img, s)[0])"
```

- `mode`: `'d'` Detailed, `'e'` Quick. `duration` in seconds.
- `width`/`height` are the *maximum* frame size; aspect ratio is kept. Use 1080×1920 for 9:16, 1920×1080 for 16:9 (add `fit='contain'` to pad).
- `show_hand=True` shows the drawing hand. `paper_color='#f3ecdf'` changes the background.
- `subject_first=True` only if `assets/v181d/model.safetensors` exists.
- Timing: lines take `duration*0.70*0.45` s, coloring ends at `duration*0.70` s, then the picture holds.
- Copy the result in `outputs/` to a clear name (e.g. `outputs/klara-5s.mp4`).

## Sound effects, text cards, narration

```bash
# marker / brush / finish-chime sound that follows the drawing
.venv/bin/python -I tools/sfx.py outputs/VIDEO.mp4 /tmp/sfx.wav
# cut-paper text cards (+ paper-slap sound); edit a copy of tools/klara-cards.json
.venv/bin/python -I tools/labels.py outputs/VIDEO.mp4 /tmp/sfx.wav /tmp/sfx2.wav /tmp/out.mp4 tools/klara-cards.json
# no cards: just mux the sound
ffmpeg -y -i outputs/VIDEO.mp4 -i /tmp/sfx.wav -af loudnorm=I=-16:TP=-1.5 -c:v copy -c:a aac -t DURATION outputs/FINAL.mp4
```

Place cards in empty white space; look at the last frame first so they never cover the face.
Each card's `t` is when it appears; time narration lines to the same moments.

Narration: generate it with a connected voice service (ElevenLabs, Artlist, …), download the
file, then mix it over the effects with the effects ducked:

```bash
ffmpeg -y -i outputs/WITH_CARDS.mp4 -i voice.mp3 -filter_complex \
 "[0:a]volume=0.35[fx];[1:a]adelay=400|400[vo];[fx][vo]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -shortest outputs/FINAL.mp4
```

If the voice is longer than the video, re-render with a longer `duration` instead of cutting the voice.

## Delivering

- Send each finished video to the user with SendUserFile, as its own new file. Do not make an HTML page or artifact for it.
- Before sending, check a few frames (`ffmpeg ... select=...,tile=3x1`) and that audio and video lengths match.
- `outputs/` is git-ignored; don't commit videos.

# Short-clip test

Place here (gitignored, never committed):

- `test.mp4` — 5–10 second segment of the hard footage
- `reference.png` — clear reference face (no sunglasses preferred)

## Pixel baseline (local GPU)

One command: cut → FaceFusion per preset → `eval/<date>_pixel_grid.jpg` → run entry appended to `eval/notes.md`.

```bash
# Linux / macOS
export FACEFUSION_HOME=~/facefusion
python3 pipeline/baseline.py -s tests/short_clip/reference.png -t tests/short_clip/test.mp4 \
  --providers cuda --presets no_glasses identity glasses_kept
```

```powershell
# Windows (PowerShell)
$env:FACEFUSION_HOME = "C:\facefusion"     # FaceFusion 3.9.1, installed with: python install.py --onnxruntime cuda
python pipeline\baseline.py -s tests\short_clip\reference.png -t tests\short_clip\test.mp4 `
  --providers cuda --presets no_glasses identity glasses_kept
```

Add `--start 4 --seconds 6` to cut a window from longer footage, `--reference-frame N`
(window-relative) to pick the face, `--dry-run` to check the plan first.
Then fill the C1–C5 scores in the new `eval/notes.md` entry.

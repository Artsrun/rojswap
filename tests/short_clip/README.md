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

## Step 7 gate (paid Wan row on the same clip)

Same command plus `--diffusion`: FaceFusion rows run first, the Replicate call last, so a
local failure never costs money. Needs `REPLICATE_API_TOKEN` in the environment
(`setx REPLICATE_API_TOKEN "r8_..."` on Windows, then a new terminal) and `pip install replicate`.

```powershell
python pipeline\baseline.py -s tests\short_clip\reference.png -t <nightclub.mp4> `
  --start 4 --seconds 6 --reference-frame 30 --diffusion --dry-run    # prints plan + token status, spends nothing
python pipeline\baseline.py -s tests\short_clip\reference.png -t <nightclub.mp4> `
  --start 4 --seconds 6 --reference-frame 30 --providers cuda `
  --presets no_glasses identity --diffusion                          # -> eval\<date>_gate_grid.jpg
```

Wan only: `--presets --diffusion`. `--resolution 720` for the sharper (pricier) output.
Windows over 10 s are refused with `--diffusion`; cost is UNVERIFIED, check the model page first.

Add `--start 4 --seconds 6` to cut a window from longer footage, `--reference-frame N`
(window-relative) to pick the face, `--dry-run` to check the plan first.
Then fill the C1–C5 scores in the new `eval/notes.md` entry.

# Short-clip evaluation notes

## Criteria for “usable”

| # | Criterion | Pass when |
|---|-----------|-----------|
| C1 | Identity | Recognizably matches the reference on frontal frames |
| C2 | Eyes / sunglasses | Removed cleanly or eyes plausible — no black bars, no soft mush |
| C3 | Lighting | Roughly matches the red club light — no plastic sheen |
| C4 | Motion | Head and shoulders stay close to the original — no drift or freeze |
| C5 | Stability | No heavy flicker or morphing between neighbouring frames |

Gate = all five pass. Any FAIL → do not render full length.

## Make the grid

```bash
# row 1 = original, each next arg = one more row (swap results)
python3 eval/grid.py tests/short_clip/test.mp4 artifacts/swap.mp4 \
  -o eval/<date>_<path>_grid.jpg --frames 8
```

Columns sample every row at the same relative time, so rows line up even when the
model returns a different fps. The printed JSON lists the frame index per cell —
paste it into the run entry. `eval/grid_example.jpg` is a synthetic sample (testsrc2,
second row hue-shifted at 16 fps).

C5 (flicker) needs the video itself, not only the grid: also check a dense strip,
e.g. `--frames 12` on a 1 s cut.

## Run log

Copy this block per run. Score each criterion PASS / WEAK / FAIL with a frame
column as evidence. Say “meme-grade” when it is.

```
### <YYYY-MM-DD> — <path: pixel | diffusion> — <model / preset>
Input     tests/short_clip/test.mp4 (<s> s, <fps> fps, <WxH>)
Reference <character image>
Command   <exact command>
Grid      eval/<file>.jpg   indices <from grid.py JSON>
Cost/time <s per frame | $ per run>

| Criterion | Score | Evidence (column) |
|-----------|-------|-------------------|
| C1 Identity   |  |  |
| C2 Eyes       |  |  |
| C3 Lighting   |  |  |
| C4 Motion     |  |  |
| C5 Stability  |  |  |

GATE      PASS | FAIL — <one line why>
```

# Short-clip evaluation notes

## Criteria for “usable”

- Identity recognizably matches the reference on frontal frames.
- Sunglasses either removed cleanly or eyes look plausible (not black bars or soft mush).
- Lighting roughly matches the red club environment (no strong plastic sheen).
- Motion of head and shoulders stays close to the original (no major drift or freeze).
- No heavy flicker or morphing between consecutive frames.

## How to extract frames

```bash
# Example
ffmpeg -i input.mp4 -vf "select='eq(n,0)+eq(n,30)+eq(n,60)'" -vsync vfr frames/out_%02d.jpg
```

Drop comparison notes here after each run. Only proceed to full length if the short clip passes.

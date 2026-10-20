# Diffusion path — Wan 2.2 Animate Replace

## Model

| Item | Value |
|------|--------|
| Model ID | `wan-video/wan-2.2-animate-replace` |
| Host | [Replicate](https://replicate.com/wan-video/wan-2.2-animate-replace) |
| Paper | [Wan-Animate (HF)](https://huggingface.co/papers/2509.14055) |
| Mode | Replace (keeps scene, camera, lighting; swaps character) |

## Inputs

- `video` — target clip (prefer 5–8 s for hard footage)
- `character_image` — clear reference face or character
- `resolution` — `480` or `720`
- `merge_audio` — `true` (experimental)

## Cost (approx, Oct 2026)

Confirm on the model page before a paid run.

| Resolution | Per 5 s | 5 s clip |
|------------|---------|----------|
| 480p | ~$0.20 | ~$0.20 |
| 720p | ~$0.40 | ~$0.40 |

Minimum billed duration is typically 3 s.

## VRAM (local alternative)

The 14B Animate weights need a high-end GPU (24 GB+ with offload, 40 GB+ comfortable).  
For the short-clip gate, the hosted Replicate path is the practical first test.

## Prover

```bash
# Dry-run (no token, no cost)
python3 pipeline/run_diffusion.py --dry-run \
  --character tests/short_clip/reference.png \
  --video tests/short_clip/test.mp4

# Real 5 s run (requires REPLICATE_API_TOKEN)
REPLICATE_API_TOKEN=... python3 pipeline/run_diffusion.py \
  --character tests/short_clip/reference.png \
  --video tests/short_clip/test.mp4 \
  --output artifacts/swap_5s.mp4
```

Real run is required before the step can be marked PROVEN.

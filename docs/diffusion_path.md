# Diffusion path — Wan 2.2 Animate Replace

## Model

| Item | Value | Source |
|------|--------|--------|
| Model ID | `wan-video/wan-2.2-animate-replace` | [Replicate](https://replicate.com/wan-video/wan-2.2-animate-replace) |
| Weights | Wan-AI/Wan2.2-Animate-14B | Replicate model page |
| Paper | Wan-Animate | [HF 2509.14055](https://huggingface.co/papers/2509.14055) |
| Mode | Replace | Keeps scene, camera, lighting |

## Inputs (single source)

Built once in `build_input()` and printed by `--dry-run`:

- `video`
- `character_image`
- `resolution` — `"480"` or `"720"`
- `merge_audio` — `true`

## Cost

**UNVERIFIED on Replicate.** Confirm while signed in before a paid run.

- WaveSpeed public listing: ~$0.20 / $0.40 per 5 s (480p / 720p).
- One third-party Replicate integration listed ~$0.02/s (480) and ~$0.05/s (720) per output second.
- Dry-run now probes actual duration via `pipeline/chunk.py` `probe()` (ffprobe). Cost is not estimated from a hardcoded `--seconds`.

## VRAM

**UNVERIFIED.** Local 14B Animate typically needs a high-end GPU; exact offload numbers are not cited here. Hosted path is the practical first test.

## Prover

```bash
python3 pipeline/run_diffusion.py --dry-run \
  --character tests/short_clip/reference.png \
  --video tests/short_clip/test.mp4
```

Junk bytes named `.mp4` now fail (ffprobe). Real 5 s run still required before PROVEN.

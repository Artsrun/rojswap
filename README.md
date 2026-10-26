# RojSwap

Repeatable, evidence-gated pipeline for face and character replacement on hard footage.

**Roj** (рожа / ռոժ / արմատ) — face root.

## Why

Pixel-level face swaps (FaceFusion, InsightFace, etc.) fail on sunglasses, strong colored lighting, and motion. Diffusion video models can handle lighting and occlusion better but need careful evaluation and chunking. RojSwap makes both paths repeatable, short-clip gated, and GitHub-backed so the next attempt does not start from zero.

## Structure

```
rojswap/
├── .opencode/mission-loop.json   # OpenCode Lite Bridge card
├── pipeline/                     # pre-pass, chunking, runners
├── eval/                         # frame extraction + notes
├── tests/short_clip/             # 5–10 s test segment + reference
└── docs/hard_cases.md
```

## Quick start

1. Drop a 5–10 s test clip and reference photo into `tests/short_clip/`.
2. (Optional) Run glasses pre-pass.
3. Run the diffusion path on the short clip.
4. Extract frames and review.
5. Only proceed to full length if the short-clip gate passes.

## Paths

- **Pixel-level** — FaceFusion / VisoMaster style (GPU recommended).
- **Diffusion** — Wan 2.2 Animate Replace (or cloud equivalent). Primary for hard lighting/occlusion.

## Status

Starter skeleton. Short-clip evaluation not yet proven.

| Module | State |
|--------|-------|
| `pipeline/chunk.py` | Implemented — `python3 -m unittest tests.test_chunk -v` |
| `pipeline/run_pixel.py` + `presets.yaml` | Implemented — `python3 -m unittest tests.test_run_pixel -v`; real render needs FaceFusion (`FACEFUSION_HOME`) |
| `pipeline/run_diffusion.py` | Dry-run only, real run unproven |
| `eval/grid.py` | Implemented — `python3 -m unittest tests.test_grid -v`; original + swap rows, aligned columns |
| `pipeline/baseline.py` | Implemented — `python3 -m unittest tests.test_baseline -v`; one-command FaceFusion baseline → grid + notes entry |
| `pipeline/prepass_glasses.py` | Stub |

## Working together

Claude and Grok cooperate through PRs and the mission card — see [`docs/COOPERATION.md`](docs/COOPERATION.md).

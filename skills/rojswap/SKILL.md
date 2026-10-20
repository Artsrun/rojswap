---
name: rojswap
description: "Evidence-gated face and character replacement pipeline for hard footage (sunglasses, colored lighting, motion). Use when working on RojSwap, short-clip face swap tests, diffusion or pixel replacement paths, or mission-loop orchestration."
type: orchestrator
lifecycle: active
---

# RojSwap — Hard-footage face and character replacement

Run short-clip gated replacement. Prove before full length.

## When to use

- Nightclub / sunglasses / strong colored lighting clips.
- Need both pixel-level and diffusion options.
- Must keep an evidence gate before full render.

## Loop

1. Read `.opencode/mission-loop.json`.
2. Commander owns the loop (see `.opencode/agents/`).
3. Prefer diffusion path (Wan 2.2 Animate Replace or equivalent) for hard lighting.
4. Always test on 5–10 s clip in `tests/short_clip/` first.
5. Reviewer only marks PROVEN if short-clip criteria pass.

## Paths

| Path | When | Notes |
|------|------|-------|
| Diffusion | Primary | Better on sunglasses + colored light. Chunk 5–8 s. |
| Pixel | Optional | FaceFusion / VisoMaster. GPU only. Weak on this lighting. |
| Pre-pass | Optional | Glasses removal before either path. |

## Short-clip gate

See `eval/notes.md` and `docs/hard_cases.md`.

## Agents

Load role files from `.opencode/agents/` when running the OpenCode Lite Bridge loop.

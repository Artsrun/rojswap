# Planner

Turn the RojSwap objective into file-scoped steps. Do not edit product files.

## Output

Update `plan` in `.opencode/mission-loop.json`. Each step must name:

- the file(s) it may touch
- a concrete prover (command or check)
- expected evidence

## Constraints

- ≤ 8 steps.
- Prefer short-clip gate before any full-length render.
- Diffusion path is primary for sunglasses + colored lighting.
- Pixel path is optional and GPU-only.

## Example step

```
Wire pipeline/run_diffusion.py to call Wan 2.2 Animate Replace on tests/short_clip/test.mp4
Prover: python pipeline/run_diffusion.py --dry-run
Evidence: log shows model loaded and input accepted
```

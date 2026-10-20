# Hard cases

Documented failure modes for RojSwap.

## Sunglasses + strong colored lighting

- Pixel-level swaps (FaceFusion / InsightFace) leave the sunglasses or produce soft, glitchy eye regions.
- Red club lighting makes color matching and skin tone difficult.
- Motion (head turns, shoulder bounce) increases temporal flicker.

## Current recommendation

- Prefer diffusion video models (Wan 2.2 Animate Replace or equivalent) for this class of footage.
- Always gate on a 5–10 s short clip before full render.
- Optional glasses pre-pass can help both paths but is not a full solution on its own.

## Other hard conditions (future)

- Extreme profile / low face resolution
- Heavy motion blur
- Multiple overlapping faces
- Strong backlighting

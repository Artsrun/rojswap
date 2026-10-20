#!/usr/bin/env python3
"""Diffusion path — Wan 2.2 Animate Replace via Replicate.

Model: wan-video/wan-2.2-animate-replace
Docs:  https://replicate.com/wan-video/wan-2.2-animate-replace
Paper: https://huggingface.co/papers/2509.14055

Prefer 5–8 s chunks for hard footage (sunglasses, colored light).

Usage:
  python3 pipeline/run_diffusion.py --dry-run \\
    --character tests/short_clip/reference.png \\
    --video tests/short_clip/test.mp4

  REPLICATE_API_TOKEN=... python3 pipeline/run_diffusion.py \\
    --character tests/short_clip/reference.png \\
    --video tests/short_clip/test.mp4 \\
    --output artifacts/swap.mp4
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MODEL_ID = "wan-video/wan-2.2-animate-replace"
REPLICATE_URL = "https://replicate.com/wan-video/wan-2.2-animate-replace"
HF_PAPER = "https://huggingface.co/papers/2509.14055"

# Approximate hosted cost (WaveSpeed / public listings, Oct 2026).
# Confirm on the model page before a paid run.
COST_PER_5S_480P_USD = 0.20
COST_PER_5S_720P_USD = 0.40


def estimate_cost(seconds: float, resolution: str) -> float:
    rate = COST_PER_5S_720P_USD if resolution == "720" else COST_PER_5S_480P_USD
    billed = max(3.0, seconds)
    return round((billed / 5.0) * rate, 2)


def validate_inputs(character: Path, video: Path) -> None:
    if not character.is_file():
        raise FileNotFoundError(f"character image not found: {character}")
    if not video.is_file():
        raise FileNotFoundError(f"target video not found: {video}")
    if character.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"unsupported image type: {character.suffix}")
    if video.suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise ValueError(f"unsupported video type: {video.suffix}")


def dry_run(character: Path, video: Path, resolution: str, seconds: float) -> None:
    validate_inputs(character, video)
    cost = estimate_cost(seconds, resolution)
    print("=== RojSwap diffusion dry-run ===")
    print(f"model:      {MODEL_ID}")
    print(f"url:        {REPLICATE_URL}")
    print(f"paper:      {HF_PAPER}")
    print(f"character:  {character}")
    print(f"video:      {video}")
    print(f"resolution: {resolution}")
    print(f"seconds:    {seconds} (billed min 3 s)")
    print(f"est. cost:  ${cost:.2f} USD (approx, confirm on model page)")
    print("call:       replicate.run(")
    print(f"              '{MODEL_ID}',")
    print("              input={")
    print("                'video': <file>,")
    print("                'character_image': <file>,")
    print(f"                'resolution': '{resolution}',")
    print("                'merge_audio': True,")
    print("              }")
    print("            )")
    print("status:     inputs valid, dry-run OK")


def real_run(character: Path, video: Path, output: Path, resolution: str) -> None:
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not set")
    try:
        import replicate  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pip install replicate") from exc

    validate_inputs(character, video)
    with character.open("rb") as char_f, video.open("rb") as vid_f:
        result = replicate.run(
            MODEL_ID,
            input={
                "video": vid_f,
                "character_image": char_f,
                "resolution": resolution,
                "merge_audio": True,
            },
        )
    # result is usually a URL or file-like
    output.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(result, "read"):
        output.write_bytes(result.read())
    else:
        import urllib.request
        urllib.request.urlretrieve(str(result), output)
    print(f"wrote {output}")


def main() -> int:
    p = argparse.ArgumentParser(description="Wan 2.2 Animate Replace runner")
    p.add_argument("--character", required=True, type=Path, help="reference face/character image")
    p.add_argument("--video", required=True, type=Path, help="target video (prefer 5–8 s)")
    p.add_argument("--output", type=Path, default=Path("artifacts/swap.mp4"))
    p.add_argument("--resolution", choices=["480", "720"], default="480")
    p.add_argument("--seconds", type=float, default=5.0, help="clip length for cost estimate")
    p.add_argument("--dry-run", action="store_true", help="validate and print call only")
    args = p.parse_args()

    try:
        if args.dry_run:
            dry_run(args.character, args.video, args.resolution, args.seconds)
        else:
            real_run(args.character, args.video, args.output, args.resolution)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

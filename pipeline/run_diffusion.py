#!/usr/bin/env python3
"""Diffusion path — Wan 2.2 Animate Replace via Replicate.

Model: wan-video/wan-2.2-animate-replace
Docs:  https://replicate.com/wan-video/wan-2.2-animate-replace
Paper: https://huggingface.co/papers/2509.14055

Prefer 5–8 s chunks for hard footage.

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

# Script-mode import: python3 pipeline/run_diffusion.py puts pipeline/ on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chunk import probe  # noqa: E402

MODEL_ID = "wan-video/wan-2.2-animate-replace"
REPLICATE_URL = "https://replicate.com/wan-video/wan-2.2-animate-replace"
HF_PAPER = "https://huggingface.co/papers/2509.14055"

# Pricing: UNVERIFIED on Replicate (confirm while signed in).
COST_NOTES = "UNVERIFIED — confirm on Replicate while signed in"


def build_input(resolution: str) -> dict:
    """Single source of truth for the Replicate input dict."""
    return {
        "video": "<file>",
        "character_image": "<file>",
        "resolution": resolution,
        "merge_audio": True,
    }


def validate_inputs(character: Path, video: Path) -> dict:
    if not character.is_file():
        raise FileNotFoundError(f"character image not found: {character}")
    if not video.is_file():
        raise FileNotFoundError(f"target video not found: {video}")
    if character.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"unsupported image type: {character.suffix}")
    if video.suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise ValueError(f"unsupported video type: {video.suffix}")
    return probe(str(video))


def dry_run(character: Path, video: Path, resolution: str) -> None:
    info = validate_inputs(character, video)
    duration = info["duration"]
    inp = build_input(resolution)
    print("=== RojSwap diffusion dry-run ===")
    print(f"model:      {MODEL_ID}")
    print(f"url:        {REPLICATE_URL}")
    print(f"paper:      {HF_PAPER}")
    print(f"character:  {character}")
    print(f"video:      {video}")
    print(f"probed:     {info['frames']} frames, {info['fps']:.3f} fps, {duration:.2f} s, {info['size']}")
    print(f"resolution: {resolution}")
    print(f"cost:       {COST_NOTES}")
    print("input dict:")
    for k, v in inp.items():
        print(f"  {k}: {v}")
    print("call:       replicate.run(")
    print(f"              '{MODEL_ID}',")
    print("              input=<dict above with real files>")
    print("            )")
    print("status:     inputs valid (ffprobe OK), dry-run OK")


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
        inp = {**build_input(resolution), "video": vid_f, "character_image": char_f}
        result = replicate.run(MODEL_ID, input=inp)
    output.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(result, "read"):
        output.write_bytes(result.read())
    else:
        import urllib.request
        urllib.request.urlretrieve(str(result), output)
    print(f"wrote {output}")


def main() -> int:
    p = argparse.ArgumentParser(description="Wan 2.2 Animate Replace runner")
    p.add_argument("--character", required=True, type=Path)
    p.add_argument("--video", required=True, type=Path)
    p.add_argument("--output", type=Path, default=Path("artifacts/swap.mp4"))
    p.add_argument("--resolution", choices=["480", "720"], default="480")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    try:
        if args.dry_run:
            dry_run(args.character, args.video, args.resolution)
        else:
            real_run(args.character, args.video, args.output, args.resolution)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

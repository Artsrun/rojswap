#!/usr/bin/env python3
"""Pre-flight face check — sample frames, report detection rate + face px size.

No FaceFusion or heavy model required for the skeleton. Inject a detector for real use.
Refuse runs below threshold instead of wasting GPU minutes on garbage input.

Usage:
  preflight.py clip.mp4 --sample 8 --min-face-px 60 --min-detect 0.5
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Any


def sample_frames(video: str, n: int = 8) -> list[Path]:
    """Extract n evenly spaced frames to a temp dir. Returns paths."""
    info = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=nb_frames,r_frame_rate",
        "-of", "json", video
    ], text=True))
    stream = info["streams"][0]
    total = int(stream.get("nb_frames") or 0)
    if total < 1:
        raise ValueError(f"no frames in {video}")
    step = max(1, total // n)
    out_dir = Path("/tmp/rojswap_preflight")
    out_dir.mkdir(exist_ok=True)
    frames = []
    for i in range(n):
        frame_no = min(i * step, total - 1)
        out = out_dir / f"f_{i:02d}.png"
        subprocess.check_call([
            "ffmpeg", "-v", "error", "-y", "-i", video,
            "-vf", f"select=eq(n\\,{frame_no})", "-frames:v", "1", str(out)
        ])
        frames.append(out)
    return frames


def report(
    video: str,
    detector: Callable[[Path], list[dict[str, Any]]] | None = None,
    sample: int = 8,
    min_face_px: int = 60,
    min_detect_rate: float = 0.5,
) -> dict[str, Any]:
    """Run preflight. detector(frame_path) -> list of {w, h, yaw?} boxes.
    Default detector returns empty (no model). Tests inject one.
    """
    frames = sample_frames(video, sample)
    detections = []
    face_px = []
    if detector:
        for f in frames:
            boxes = detector(f) or []
            detections.append(len(boxes))
            for b in boxes:
                face_px.append(min(b.get("w", 0), b.get("h", 0)))
    rate = sum(1 for d in detections if d > 0) / max(1, len(frames))
    median_px = sorted(face_px)[len(face_px) // 2] if face_px else 0
    ok = rate >= min_detect_rate and median_px >= min_face_px
    return {
        "video": video,
        "sampled": len(frames),
        "detection_rate": round(rate, 3),
        "median_face_px": median_px,
        "min_face_px": min_face_px,
        "min_detect_rate": min_detect_rate,
        "ok": ok,
        "reason": None if ok else "low detection rate or face too small",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--sample", type=int, default=8)
    ap.add_argument("--min-face-px", type=int, default=60)
    ap.add_argument("--min-detect", type=float, default=0.5)
    a = ap.parse_args(argv)
    try:
        r = report(a.video, sample=a.sample, min_face_px=a.min_face_px, min_detect_rate=a.min_detect)
        print(json.dumps(r, indent=2))
        return 0 if r["ok"] else 2
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

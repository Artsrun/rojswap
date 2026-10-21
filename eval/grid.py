#!/usr/bin/env python3
"""Frame grid for the short-clip gate: one row per video, same relative timestamps per column.

  grid.py <original.mp4> [<swap.mp4> ...] [-o eval/grid.jpg] [--frames 8] [--cell-width 240]

Row 1 is the first video (usually the original), each next video is one more row.
Column c samples every video at the same fraction of its length, so rows line up
even when a model returns a different fps. Prints JSON: grid path + per-row frame indices.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from chunk import _run, probe  # noqa: E402


def frame_indices(total: int, n: int) -> list[int]:
    """n evenly spaced, distinct frame indices covering first..last frame."""
    if n < 1:
        raise ValueError("frames must be >= 1")
    if n > total:
        raise ValueError(f"asked for {n} frames, clip has only {total}")
    if n == 1:
        return [total // 2]
    return [round(i * (total - 1) / (n - 1)) for i in range(n)]


def cell_size(first_size: tuple[int, int], cell_width: int) -> tuple[int, int]:
    """Cell keeps the first video's aspect; even dims for yuv encoders."""
    w, h = first_size
    cw = cell_width - cell_width % 2
    return cw, max(2, round(cw * h / w / 2) * 2)


def build_grid(videos: list[str], output: str, n: int = 8, cell_width: int = 240) -> dict:
    """Render the grid with one ffmpeg call. Returns {"grid", "cell", "rows": [{video, frames, indices}]}."""
    if not videos:
        raise ValueError("need at least one video")
    infos = [probe(v) for v in videos]
    cw, ch = cell_size(infos[0]["size"], cell_width)
    rows = [{"video": v, "frames": i["frames"], "indices": frame_indices(i["frames"], n)}
            for v, i in zip(videos, infos)]

    graph = []
    for k, row in enumerate(rows):
        pick = "+".join(f"eq(n\\,{i})" for i in row["indices"])
        graph.append(
            f"[{k}:v:0]select='{pick}',"
            f"scale={cw}:{ch}:force_original_aspect_ratio=decrease,"
            f"pad={cw}:{ch}:(ow-iw)/2:(oh-ih)/2,setsar=1,tile={n}x1[r{k}]"
        )
    if len(rows) > 1:
        graph.append("".join(f"[r{k}]" for k in range(len(rows))) + f"vstack=inputs={len(rows)}[g]")
        out_label = "[g]"
    else:
        out_label = "[r0]"

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for v in videos:
        cmd += ["-i", v]
    cmd += ["-filter_complex", ";".join(graph), "-map", out_label,
            "-frames:v", "1", "-update", "1", "-q:v", "3", output]
    _run(cmd)
    return {"grid": output, "cell": [cw, ch], "rows": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+", help="original first, then swap result(s)")
    ap.add_argument("-o", "--output", default="eval/grid.jpg")
    ap.add_argument("--frames", type=int, default=8, help="columns (default 8)")
    ap.add_argument("--cell-width", type=int, default=240)
    a = ap.parse_args(argv)
    try:
        print(json.dumps(build_grid(a.videos, a.output, a.frames, a.cell_width)))
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

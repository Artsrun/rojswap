#!/usr/bin/env python3
"""One-command pixel baseline: cut window -> FaceFusion per preset -> frame grid -> notes entry.

  baseline.py -s ref.png -t tests/short_clip/test.mp4 --providers cuda
  baseline.py -s ref.png -t full.mp4 --start 4 --seconds 6 --presets no_glasses identity glasses_kept
  baseline.py ... --dry-run          # validate + print the plan, write nothing

Outputs:  <out-dir>/clip.mp4, <out-dir>/<preset>.mp4   (local, gitignored)
          eval/<date>_pixel_grid.jpg                    (row 1 = clip, then one row per preset)
          eval/notes.md                                 (run entry appended, scores left blank)
FaceFusion lookup is run_pixel's: FACEFUSION_HOME / FACEFUSION_PYTHON or --facefusion-home.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "eval"))
import run_pixel  # noqa: E402
from chunk import _run, probe  # noqa: E402
from grid import build_grid  # noqa: E402

DEFAULT_PRESETS = ["no_glasses", "identity"]


def rel(path: str) -> str:
    """Repo-relative posix path when inside the repo: notes get committed, home dirs should not."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def frame_window(info: dict, start: float, seconds: float | None) -> tuple[int, int]:
    """[start, end) frame range for a time window; whole clip when seconds is None."""
    first = round(start * info["fps"])
    last = info["frames"] if seconds is None else min(info["frames"], first + round(seconds * info["fps"]))
    if not 0 <= first < last:
        raise ValueError(f"window {start}s +{seconds}s is outside the {info['duration']:.2f}s clip")
    return first, last


def cut_clip(src: str, dst: str, first: int, last: int, has_audio: bool) -> None:
    """Frame-exact cut [first, last), re-encoded near-lossless, audio trimmed to match."""
    info = probe(src)
    vf = f"trim=start_frame={first}:end_frame={last},setpts=PTS-STARTPTS"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf,
           "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p"]
    if has_audio:
        t0, t1 = first / info["fps"], last / info["fps"]
        cmd += ["-af", f"atrim={t0:.6f}:{t1:.6f},asetpts=PTS-STARTPTS", "-c:a", "aac"]
    else:
        cmd += ["-an"]
    _run(cmd + [dst])


def pixel_args(preset: str, sources: list[str], target: str, output: str, a: argparse.Namespace,
               trim: tuple[int, int] | None = None) -> list[str]:
    argv = ["--preset", preset, "-s", *sources, "-t", target, "-o", output, "--providers", a.providers]
    if a.reference_frame is not None:
        argv += ["--reference-frame", str(a.reference_frame + (trim[0] if trim else 0))]
    if trim:
        argv += ["--trim", str(trim[0]), str(trim[1])]
    for opt in ("facefusion_home", "facefusion_python"):
        if getattr(a, opt):
            argv += ["--" + opt.replace("_", "-"), getattr(a, opt)]
    for s in a.set:
        argv += ["--set", s]
    return argv


def notes_entry(date: str, command: str, clip_info: dict, sources: list[str], grid: dict,
                runs: list[dict]) -> str:
    w, h = clip_info["size"]
    rows = "\n".join(f"Row {i + 1:<5} {rel(r['video'])}  indices {r['indices']}" for i, r in enumerate(grid["rows"]))
    timing = "\n".join(f"          {r['preset']}: {r['seconds']:.0f} s total, {r['sec_per_frame']:.2f} s/frame"
                       for r in runs)
    presets = ", ".join(r["preset"] for r in runs)
    return f"""
### {date} — pixel — FaceFusion {presets}
Input     clip {clip_info['duration']:.2f} s, {clip_info['fps']:.3f} fps, {w}x{h}, {clip_info['frames']} frames
Reference {' '.join(map(rel, sources))}
Command   {command}
Grid      {rel(grid['grid'])}
{rows}
Cost/time
{timing}

| Criterion | Score | Evidence (column) |
|-----------|-------|-------------------|
| C1 Identity   |  |  |
| C2 Eyes       |  |  |
| C3 Lighting   |  |  |
| C4 Motion     |  |  |
| C5 Stability  |  |  |

GATE      PASS | FAIL — <one line why>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-s", "--source", nargs="+", required=True, help="reference face image(s)")
    ap.add_argument("-t", "--target", required=True, help="target video (short clip or full footage)")
    ap.add_argument("--presets", nargs="+", default=DEFAULT_PRESETS)
    ap.add_argument("--start", type=float, default=0.0, help="window start, seconds")
    ap.add_argument("--seconds", type=float, help="window length; default = to the end")
    ap.add_argument("--reference-frame", type=int, help="frame inside the window where the face is clear")
    ap.add_argument("--providers", default="cuda", help="FaceFusion execution provider (default cuda)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override for every preset")
    ap.add_argument("--frames", type=int, default=8, help="grid columns")
    ap.add_argument("--out-dir", help="default artifacts/baseline/<date>")
    ap.add_argument("--grid", help="default eval/<date>_pixel_grid.jpg")
    ap.add_argument("--notes", default=str(ROOT / "eval" / "notes.md"))
    ap.add_argument("--facefusion-home")
    ap.add_argument("--facefusion-python")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    date = dt.date.today().isoformat()
    out_dir = Path(a.out_dir or ROOT / "artifacts" / "baseline" / date)
    grid_path = Path(a.grid or ROOT / "eval" / f"{date}_pixel_grid.jpg")
    try:
        unknown = set(a.presets) - run_pixel.load_presets().keys()
        if unknown:
            raise ValueError(f"unknown presets {sorted(unknown)}")
        info = probe(a.target)
        first, last = frame_window(info, a.start, a.seconds)
        n = last - first
        if a.reference_frame is not None and not 0 <= a.reference_frame < n:
            raise ValueError(f"reference frame {a.reference_frame} outside the window 0..{n - 1}")
        if a.frames > n:
            raise ValueError(f"grid wants {a.frames} frames, window has {n}")

        if a.dry_run:
            print(f"window:  frames {first}..{last} ({n} frames, {n / info['fps']:.2f} s) of {a.target}")
            for p in a.presets:
                code = run_pixel.main(pixel_args(p, a.source, a.target, str(out_dir / f"{p}.mp4"), a,
                                                 trim=(first, last)) + ["--dry-run"])
                if code:
                    return code
            print(f"grid:    {grid_path} ({1 + len(a.presets)} rows x {a.frames})")
            print(f"notes:   append to {a.notes}")
            print("status:  plan OK, nothing written")
            return 0

        out_dir.mkdir(parents=True, exist_ok=True)
        clip = out_dir / "clip.mp4"
        cut_clip(a.target, str(clip), first, last, info["has_audio"])
        clip_info = probe(str(clip))
        if clip_info["frames"] != n:
            raise RuntimeError(f"cut has {clip_info['frames']} frames, expected {n}")

        runs = []
        for p in a.presets:
            out = out_dir / f"{p}.mp4"
            t0 = time.monotonic()
            if run_pixel.main(pixel_args(p, a.source, str(clip), str(out), a)):
                raise RuntimeError(f"preset {p} failed (see run_pixel output above)")
            secs = time.monotonic() - t0
            runs.append({"preset": p, "output": str(out), "seconds": secs, "sec_per_frame": secs / n})

        grid = build_grid([str(clip), *(r["output"] for r in runs)], str(grid_path), a.frames)
        command = shlex.join(["python", "pipeline/baseline.py", *(argv if argv is not None else sys.argv[1:])])
        with open(a.notes, "a", encoding="utf-8") as f:
            f.write(notes_entry(date, command, clip_info, a.source, grid, runs))
        print(json.dumps({"clip": str(clip), "runs": runs, "grid": grid["grid"], "notes": a.notes}))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

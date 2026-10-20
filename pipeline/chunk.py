#!/usr/bin/env python3
"""Split a video into frame-exact chunks and stitch them back with the original audio.

  chunk.py split  <input.mp4> <out_dir> [--seconds 8]
  chunk.py stitch <output.mp4> <chunk.mp4>... [--audio <original.mp4>]
  chunk.py probe  <video.mp4>

Invariant: stitch(split(x)) has exactly the frames of x, in order.
Chunks are video-only; audio comes back from the original at stitch time.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

CHUNK_GLOB = "chunk_*.mp4"


def _run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({res.returncode}): {res.stderr.strip()[-800:]}")
    return res.stdout


def probe(path: str) -> dict:
    """Decoded frame count, fps, size, duration, audio presence."""
    out = json.loads(_run([
        "ffprobe", "-v", "error", "-count_frames",
        "-show_entries", "stream=codec_type,nb_read_frames,r_frame_rate,width,height:format=duration",
        "-of", "json", path,
    ]))
    video = next(s for s in out["streams"] if s["codec_type"] == "video")
    num, den = map(int, video["r_frame_rate"].split("/"))
    return {
        "frames": int(video["nb_read_frames"]),
        "fps": num / den,
        "size": (int(video["width"]), int(video["height"])),
        "duration": float(out["format"]["duration"]),
        "has_audio": any(s["codec_type"] == "audio" for s in out["streams"]),
    }


def chunk_video(input_path: str, out_dir: str, segment_seconds: float = 8.0) -> list[str]:
    """Re-encode with keyframes forced every N frames, cut on those frame numbers. Returns chunk paths in order.

    Cuts by frame number, not time: time-based cuts (-segment_time) miss boundaries on float rounding.
    """
    if segment_seconds <= 0:
        raise ValueError("segment_seconds must be > 0")
    info = probe(input_path)
    step = max(1, round(segment_seconds * info["fps"]))
    cuts = list(range(step, info["frames"], step))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob(CHUNK_GLOB):  # only our own pattern
        stale.unlink()

    cmd = [
        "ffmpeg", "-v", "error", "-y", "-i", input_path,
        "-map", "0:v:0", "-an",
        "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-force_key_frames", f"expr:eq(mod(n,{step}),0)",
        "-f", "segment", "-reset_timestamps", "1",
    ]
    # no cuts (clip shorter than one chunk): cut list past the end -> single segment
    cmd += ["-segment_frames", ",".join(map(str, cuts or [info["frames"] + 1]))]
    _run(cmd + [str(out / "chunk_%03d.mp4")])
    return sorted(str(p) for p in out.glob(CHUNK_GLOB))


def stitch_chunks(chunk_paths: list[str], output_path: str, original_audio: str | None = None) -> None:
    """Concat chunks in the given order; take audio from original_audio if given. No frames are trimmed."""
    if not chunk_paths:
        raise ValueError("no chunks to stitch")

    infos = [probe(p) for p in chunk_paths]
    sizes = {i["size"] for i in infos}
    if len(sizes) > 1:
        raise ValueError(f"chunks differ in size {sorted(sizes)}; resize them before stitching")

    n = len(chunk_paths)
    graph = "".join(f"[{i}:v:0]setpts=PTS-STARTPTS[v{i}];" for i in range(n))
    graph += "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"

    cmd = ["ffmpeg", "-v", "error", "-y"]
    for p in chunk_paths:
        cmd += ["-i", p]
    if original_audio:
        cmd += ["-i", original_audio]
    cmd += ["-filter_complex", graph, "-map", "[v]"]
    if original_audio:
        cmd += ["-map", f"{n}:a:0?", "-c:a", "copy"]
    # no -shortest: it silently drops trailing frames when audio is a hair shorter
    cmd += [
        "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
        "-r", f"{infos[0]['fps']:.6f}", "-movflags", "+faststart", output_path,
    ]
    _run(cmd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("split", help="split into chunks")
    sp.add_argument("input")
    sp.add_argument("out_dir")
    sp.add_argument("--seconds", type=float, default=8.0)

    st = sub.add_parser("stitch", help="stitch chunks back")
    st.add_argument("output")
    st.add_argument("chunks", nargs="+")
    st.add_argument("--audio", help="original video to take audio from")

    pr = sub.add_parser("probe", help="print frame count / fps / size / duration")
    pr.add_argument("video")

    a = ap.parse_args(argv)
    if a.cmd == "split":
        for p in chunk_video(a.input, a.out_dir, a.seconds):
            print(p)
    elif a.cmd == "stitch":
        stitch_chunks(a.chunks, a.output, a.audio)
        print(json.dumps(probe(a.output)))
    else:
        print(json.dumps(probe(a.video)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

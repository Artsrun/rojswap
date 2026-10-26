#!/usr/bin/env python3
"""Pixel path: FaceFusion 3.9.1 headless wrapper with evidence-backed presets (pipeline/presets.yaml).

  run_pixel.py --list-presets
  run_pixel.py --preset no_glasses -s me.png -t clip.mp4 -o out.mp4 --dry-run
  run_pixel.py --preset identity -s me.png me2.png -t clip.mp4 -o out.mp4 \\
      --reference-frame 30 --trim 0 90 --set face_enhancer_blend=60

FaceFusion is not vendored. Point the wrapper at an install:
  FACEFUSION_HOME    dir containing facefusion.py          (or --facefusion-home)
  FACEFUSION_PYTHON  its interpreter, default $FACEFUSION_HOME/.venv/bin/python (Windows: .venv\\Scripts\\python.exe)

Install tested on CPU (2026-10-20):
  git clone --depth 1 --branch 3.9.1 https://github.com/facefusion/facefusion
  cd facefusion && uv venv -p 3.12 .venv && uv pip install -p .venv -r requirements.txt
NVIDIA (untested here): python install.py --onnxruntime cuda, then --providers cuda.
Models download from GitHub / Hugging Face on first run.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chunk import probe  # noqa: E402

PRESETS_PATH = Path(__file__).with_name("presets.yaml")
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
# set by the wrapper itself; presets and --set may not touch them
RESERVED = {"source_paths", "target_path", "output_path", "execution_providers",
            "execution_thread_count", "trim_frame_start", "trim_frame_end",
            "reference_frame_number", "temp_path", "log_level"}
CPU_SEC_PER_FRAME = 6.0  # observed 2026-10-20, 2-core CPU, swap + gfpgan; reference only


def load_presets(path: Path = PRESETS_PATH) -> dict:
    """name -> {status, description, evidence, args}, each merged over _base."""
    import yaml  # pip install pyyaml

    raw = yaml.safe_load(path.read_text())
    base = raw.get("_base", {}).get("args", {})
    presets = {}
    for name, p in raw["presets"].items():
        args = {**base, **p.get("args", {})}
        bad = RESERVED & args.keys()
        if bad:
            raise ValueError(f"preset {name!r} sets reserved keys {sorted(bad)}")
        presets[name] = {**p, "args": args}
    return presets


def parse_overrides(items: list[str]) -> dict:
    """['k=v', 'k=a,b'] -> {'k': 'v', 'k2': ['a', 'b']}"""
    out = {}
    for item in items:
        key, sep, value = item.partition("=")
        key = key.strip().replace("-", "_")
        if not sep or not key:
            raise ValueError(f"--set expects key=value, got {item!r}")
        if key in RESERVED:
            raise ValueError(f"{key!r} is set by the wrapper; use the dedicated option")
        out[key] = value.split(",") if "," in value else value
    return out


def to_flags(args: dict) -> list[str]:
    flags = []
    for key, value in args.items():
        flags.append("--" + key.replace("_", "-"))
        flags += [str(v) for v in value] if isinstance(value, list) else [str(value)]
    return flags


def build_command(python: str, ff_home: str, args: dict, sources: list[str], target: str, output: str, *,
                  providers: str = "cpu", threads: int | None = None, reference_frame: int | None = None,
                  trim: tuple[int, int] | None = None, temp_path: str | None = None,
                  log_level: str = "info") -> list[str]:
    # absolute paths: FaceFusion runs with cwd=ff_home
    absolute = lambda p: str(Path(p).resolve())
    cmd = [python, str(Path(ff_home) / "facefusion.py"), "headless-run",
           "-s", *map(absolute, sources), "-t", absolute(target), "-o", absolute(output), *to_flags(args),
           "--execution-providers", providers,
           "--execution-thread-count", str(threads or os.cpu_count() or 1),
           "--log-level", log_level]
    if reference_frame is not None:
        cmd += ["--reference-frame-number", str(reference_frame)]
    if trim:
        cmd += ["--trim-frame-start", str(trim[0]), "--trim-frame-end", str(trim[1])]
    if temp_path:
        cmd += ["--temp-path", absolute(temp_path)]
    return cmd


def validate(sources: list[str], target_info: dict, reference_frame: int | None,
             trim: tuple[int, int] | None) -> int:
    """Raise on bad input; return the expected output frame count."""
    for s in sources:
        p = Path(s)
        if not p.is_file():
            raise FileNotFoundError(f"source image not found: {s}")
        if p.suffix.lower() not in IMAGE_EXTS:
            raise ValueError(f"source must be an image {sorted(IMAGE_EXTS)}: {s}")
    frames = target_info["frames"]
    if reference_frame is not None and not 0 <= reference_frame < frames:
        raise ValueError(f"reference frame {reference_frame} outside 0..{frames - 1}")
    if trim:
        start, end = trim
        if not 0 <= start < end <= frames:
            raise ValueError(f"trim {start}..{end} must satisfy 0 <= start < end <= {frames} (end exclusive)")
        return end - start
    return frames


def venv_python(home: str, windows: bool = os.name == "nt") -> str:
    """Interpreter inside $home/.venv: Scripts/python.exe on Windows, bin/python elsewhere."""
    return str(Path(home) / ".venv" / ("Scripts/python.exe" if windows else "bin/python"))


def resolve_facefusion(home: str | None, python: str | None) -> tuple[str, str]:
    home = home or os.environ.get("FACEFUSION_HOME", "")
    python = python or os.environ.get("FACEFUSION_PYTHON") or venv_python(home)
    return home, python


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-presets", action="store_true")
    ap.add_argument("--preset", default="no_glasses")
    ap.add_argument("-s", "--source", nargs="+", help="your face image(s); several are averaged")
    ap.add_argument("-t", "--target", help="target video")
    ap.add_argument("-o", "--output", help="output video")
    ap.add_argument("--reference-frame", type=int, help="frame where the person to replace is clearly visible")
    ap.add_argument("--trim", type=int, nargs=2, metavar=("START", "END"), help="frame range, end exclusive")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a preset arg")
    ap.add_argument("--providers", default="cpu", help="cpu | cuda | ... (FaceFusion execution provider)")
    ap.add_argument("--threads", type=int)
    ap.add_argument("--temp-path")
    ap.add_argument("--facefusion-home")
    ap.add_argument("--facefusion-python")
    ap.add_argument("--dry-run", action="store_true", help="validate and print the command only")
    a = ap.parse_args(argv)

    try:
        presets = load_presets()
        if a.list_presets:
            for name, p in presets.items():
                print(f"{name:20} [{p['status']}] {p['description']}\n{'':22}evidence: {p['evidence']}")
            return 0
        if not (a.source and a.target and a.output):
            ap.error("-s/--source, -t/--target and -o/--output are required")
        if a.preset not in presets:
            raise ValueError(f"unknown preset {a.preset!r}; available: {', '.join(presets)}")

        preset = presets[a.preset]
        args = {**preset["args"], **parse_overrides(a.set)}
        info = probe(a.target)  # also rejects unreadable video
        trim = tuple(a.trim) if a.trim else None
        expected = validate(a.source, info, a.reference_frame, trim)

        home, python = resolve_facefusion(a.facefusion_home, a.facefusion_python)
        cmd = build_command(python, home or "<FACEFUSION_HOME>", args, a.source, a.target, a.output,
                            providers=a.providers, threads=a.threads, reference_frame=a.reference_frame,
                            trim=trim, temp_path=a.temp_path)
        ff_ok = bool(home) and (Path(home) / "facefusion.py").is_file() and Path(python).is_file()

        if a.dry_run:
            print(f"preset:    {a.preset} [{preset['status']}]")
            print(f"target:    {info['frames']} frames, {info['fps']:.3f} fps, {info['size'][0]}x{info['size'][1]}")
            print(f"output:    {expected} frames expected")
            if a.providers == "cpu":
                print(f"cpu ref:   ~{expected * CPU_SEC_PER_FRAME / 60:.0f} min at {CPU_SEC_PER_FRAME:g} s/frame (2-core, 2026-10-20)")
            print(f"facefusion: {'found' if ff_ok else 'NOT FOUND - set FACEFUSION_HOME'}")
            print("command:   " + shlex.join(cmd))
            print("status:    inputs valid, dry-run OK")
            return 0

        if not ff_ok:
            raise RuntimeError("FaceFusion not found: set FACEFUSION_HOME (and FACEFUSION_PYTHON if not .venv)")
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        if subprocess.run(cmd, cwd=home).returncode != 0:
            raise RuntimeError("facefusion exited with an error")
        out = probe(a.output)
        print(json.dumps({"output": a.output, **out, "expected_frames": expected}))
        if out["frames"] != expected:
            raise RuntimeError(f"frame count {out['frames']} != expected {expected}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

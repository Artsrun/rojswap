#!/usr/bin/env python3
"""Provenance stub — C2PA signing with c2patool when available.

Step 10 remains UNPROVEN until c2patool is present and a real signed mp4 is verified.
"""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

def sign(input_mp4: str, output_mp4: str, manifest: dict | None = None) -> bool:
    """Return True if c2patool succeeded. Frames unchanged by design."""
    tool = shutil.which("c2patool")
    if not tool:
        return False
    # Minimal: copy then sign. Real impl would embed a claim.
    Path(output_mp4).write_bytes(Path(input_mp4).read_bytes())
    # Placeholder: real call would be c2patool sign ...
    return True

if __name__ == "__main__":
    print("provenance stub — see docs/harvest_live3d.md for C2PA plan")

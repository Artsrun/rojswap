#!/usr/bin/env python3
"""Chunk a video into short segments and stitch them back.

Skeleton only.
"""

def chunk_video(input_path: str, out_dir: str, segment_seconds: float = 8.0) -> list[str]:
    raise NotImplementedError("Use ffmpeg to split into ~8 s segments")


def stitch_chunks(chunk_paths: list[str], output_path: str, original_audio: str | None = None) -> None:
    raise NotImplementedError("Concat video chunks and restore original audio")


if __name__ == "__main__":
    print("chunk.py skeleton — implement with ffmpeg")

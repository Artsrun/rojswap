"""Prover for pipeline/chunk.py.  Run: python3 -m unittest tests.test_chunk -v

Needs ffmpeg/ffprobe on PATH. Uses a synthetic 37.2 s clip (same length/fps as the
RojSwap test footage) with a burned-in frame counter, so order errors show up as low PSNR.
"""
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import chunk  # noqa: E402

FPS, DURATION, SEG = 30, 37.2, 8.0


def make_clip(path: Path, size: str = "320x240", audio: bool = True) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={FPS}:duration={DURATION}"]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={DURATION}", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)


def psnr(a: str, b: str) -> float:
    err = subprocess.run(["ffmpeg", "-i", a, "-i", b, "-lavfi", "psnr", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"average:([\d.]+|inf)", err).group(1))


class ChunkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.src = cls.dir / "src.mp4"
        make_clip(cls.src)
        cls.src_info = chunk.probe(str(cls.src))
        cls.chunks = chunk.chunk_video(str(cls.src), str(cls.dir / "chunks"), SEG)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_split_count_and_frames(self):
        self.assertEqual(len(self.chunks), math.ceil(DURATION / SEG))
        frames = [chunk.probe(c)["frames"] for c in self.chunks]
        self.assertEqual(sum(frames), self.src_info["frames"])
        self.assertTrue(all(f == int(SEG * FPS) for f in frames[:-1]), frames)

    def test_chunks_are_video_only(self):
        self.assertFalse(any(chunk.probe(c)["has_audio"] for c in self.chunks))

    def test_stitch_roundtrip(self):
        out = self.dir / "stitched.mp4"
        chunk.stitch_chunks(self.chunks, str(out), str(self.src))
        info = chunk.probe(str(out))
        self.assertEqual(info["frames"], self.src_info["frames"])
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["fps"], FPS, places=3)
        self.assertGreater(psnr(str(out), str(self.src)), 30.0)

    def test_stitch_without_audio(self):
        out = self.dir / "stitched_silent.mp4"
        chunk.stitch_chunks(self.chunks, str(out))
        self.assertFalse(chunk.probe(str(out))["has_audio"])

    def test_resplit_clears_stale_chunks(self):
        again = chunk.chunk_video(str(self.src), str(self.dir / "chunks"), SEG)
        self.assertEqual(again, self.chunks)

    def test_stitch_rejects_size_mismatch(self):
        odd = self.dir / "odd.mp4"
        make_clip(odd, size="160x120", audio=False)
        with self.assertRaises(ValueError):
            chunk.stitch_chunks([self.chunks[0], str(odd)], str(self.dir / "bad.mp4"))

    def test_single_chunk_when_segment_longer_than_clip(self):
        one = chunk.chunk_video(str(self.src), str(self.dir / "one"), 60.0)
        self.assertEqual(len(one), 1)
        self.assertEqual(chunk.probe(one[0])["frames"], self.src_info["frames"])

    def test_rejects_bad_segment(self):
        with self.assertRaises(ValueError):
            chunk.chunk_video(str(self.src), str(self.dir / "x"), 0)


if __name__ == "__main__":
    unittest.main()

"""Prover for eval/grid.py.  Run: python3 -m unittest tests.test_grid -v

Needs ffmpeg/ffprobe on PATH. Synthetic 3 s clips whose gray level encodes time
(Y = 16 + 60 * t, limited range), so each grid cell's brightness tells which moment was sampled.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
import grid  # noqa: E402

DURATION, LUM_PER_S = 3, 60
FULL = 255 / 219  # limited -> full range on gray readback


def make_ramp(path: Path, fps: int, size: str = "64x48") -> None:
    src = f"nullsrc=s={size}:r={fps}:d={DURATION},geq=lum='16+{LUM_PER_S}*T':cb=128:cr=128"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src,
                    "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)], check=True)


def gray(path: str) -> tuple[int, int, bytes]:
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", path],
                                   capture_output=True, text=True, check=True).stdout.split(","))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    return w, h, raw


def cell_mean(img: tuple[int, int, bytes], col: int, row: int, cw: int, ch: int) -> float:
    w, _, raw = img
    xs = range(col * cw + cw // 4, col * cw + 3 * cw // 4)
    ys = range(row * ch + ch // 4, row * ch + 3 * ch // 4)
    vals = [raw[y * w + x] for y in ys for x in xs]
    return sum(vals) / len(vals)


class IndicesTest(unittest.TestCase):
    def test_spread_covers_ends(self):
        self.assertEqual(grid.frame_indices(90, 4), [0, 30, 59, 89])
        self.assertEqual(grid.frame_indices(10, 10), list(range(10)))

    def test_single_frame_is_middle(self):
        self.assertEqual(grid.frame_indices(90, 1), [45])

    def test_rejects_bad_counts(self):
        with self.assertRaises(ValueError):
            grid.frame_indices(5, 6)
        with self.assertRaises(ValueError):
            grid.frame_indices(5, 0)

    def test_cell_size_even_and_aspect(self):
        self.assertEqual(grid.cell_size((540, 960), 240), (240, 426))
        self.assertEqual(grid.cell_size((1920, 1080), 241), (240, 136))


class GridTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.orig = cls.dir / "orig.mp4"
        cls.swap = cls.dir / "swap.mp4"  # different fps, like a model output
        make_ramp(cls.orig, 30)
        make_ramp(cls.swap, 16)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_single_row(self):
        out = self.dir / "one.jpg"
        res = grid.build_grid([str(self.orig)], str(out), n=5, cell_width=64)
        w, h, _ = gray(str(out))
        self.assertEqual((w, h), (5 * 64, 48))
        self.assertEqual(res["rows"][0]["indices"], [0, 22, 44, 67, 89])

    def test_cells_sample_requested_frames(self):
        out = self.dir / "two.jpg"
        res = grid.build_grid([str(self.orig), str(self.swap)], str(out), n=6, cell_width=64)
        cw, ch = res["cell"]
        img = gray(str(out))
        self.assertEqual(img[:2], (6 * cw, 2 * ch))
        for r, (row, fps) in enumerate(zip(res["rows"], (30, 16))):
            for c, idx in enumerate(row["indices"]):
                self.assertAlmostEqual(cell_mean(img, c, r, cw, ch), LUM_PER_S * idx / fps * FULL,
                                       delta=4, msg=f"row {r} col {c} frame {idx}")

    def test_rows_line_up_across_fps(self):
        out = self.dir / "align.jpg"
        res = grid.build_grid([str(self.orig), str(self.swap)], str(out), n=4, cell_width=64)
        cw, ch = res["cell"]
        img = gray(str(out))
        for c in range(4):
            self.assertAlmostEqual(cell_mean(img, c, 0, cw, ch), cell_mean(img, c, 1, cw, ch), delta=5)

    def test_cli_json_and_errors(self):
        out = self.dir / "cli.jpg"
        script = Path(grid.__file__)
        ok = subprocess.run([sys.executable, str(script), str(self.orig), "-o", str(out), "--frames", "3"],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["grid"], str(out))
        self.assertTrue(out.exists())
        bad = subprocess.run([sys.executable, str(script), str(self.orig), "-o", str(out), "--frames", "999"],
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("only 90", bad.stderr)


if __name__ == "__main__":
    unittest.main()

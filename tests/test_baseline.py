"""Prover for pipeline/baseline.py.  Run: python3 -m unittest tests.test_baseline -v

Needs ffmpeg/ffprobe. FaceFusion is faked: a facefusion.py that hue-shifts -t into -o,
so the whole chain (cut -> run_pixel -> grid -> notes) runs without a GPU or models.
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import baseline  # noqa: E402
import run_pixel  # noqa: E402

FAKE_FF = '''import subprocess, sys
a = sys.argv
t, o = a[a.index("-t") + 1], a[a.index("-o") + 1]
with open(o + ".argv", "w") as f:
    f.write(" ".join(a))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", t, "-vf", "hue=h=90", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-an", o], check=True)
'''


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = baseline.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class WindowTest(unittest.TestCase):
    INFO = {"frames": 300, "fps": 30.0, "duration": 10.0}

    def test_window(self):
        self.assertEqual(baseline.frame_window(self.INFO, 2, 3), (60, 150))
        self.assertEqual(baseline.frame_window(self.INFO, 0, None), (0, 300))
        self.assertEqual(baseline.frame_window(self.INFO, 8, 5), (240, 300))  # clamped to end

    def test_rel_paths_inside_repo(self):
        self.assertEqual(baseline.rel(str(baseline.ROOT / "eval" / "x.jpg")), "eval/x.jpg")
        outside = str(Path(tempfile.gettempdir()) / "x.jpg")
        self.assertEqual(baseline.rel(outside), outside)

    def test_window_outside_clip(self):
        with self.assertRaises(ValueError):
            baseline.frame_window(self.INFO, 10, 2)

    def test_venv_python_per_os(self):
        self.assertTrue(run_pixel.venv_python("ff", windows=True).replace("\\", "/").endswith(
            ".venv/Scripts/python.exe"))
        self.assertTrue(run_pixel.venv_python("ff", windows=False).endswith(str(Path(".venv/bin/python"))))


class MediaCase(unittest.TestCase):
    """Shared fixtures: 4 s target with audio, reference png, fake FaceFusion."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.dir = Path(cls.tmp.name)
        cls.target = d / "target.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=180x320:rate=30:duration=4",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:a", "aac",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.target)], check=True)
        cls.ref = d / "ref.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=64x64",
                        "-frames:v", "1", str(cls.ref)], check=True)
        cls.ff = d / "ff"
        cls.ff.mkdir()
        (cls.ff / "facefusion.py").write_text(FAKE_FF)
        cls.ff_args = ["--facefusion-home", str(cls.ff), "--facefusion-python", sys.executable]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def paths(self, name):
        return ["--out-dir", str(self.dir / name), "--grid", str(self.dir / f"{name}.jpg"),
                "--notes", str(self.dir / f"{name}.md")]


class BaselineTest(MediaCase):
    def test_full_chain(self):
        code, out, err = run_cli("-s", str(self.ref), "-t", str(self.target), "--start", "1", "--seconds", "2",
                                 "--presets", "no_glasses", "identity", "--reference-frame", "10",
                                 "--frames", "4", *self.paths("full"), *self.ff_args)
        self.assertEqual(code, 0, err)
        clip = baseline.probe(str(self.dir / "full" / "clip.mp4"))
        self.assertEqual(clip["frames"], 60)
        self.assertTrue(clip["has_audio"])
        self.assertAlmostEqual(clip["duration"], 2.0, delta=0.1)
        for p in ("no_glasses", "identity"):
            self.assertEqual(baseline.probe(str(self.dir / "full" / f"{p}.mp4"))["frames"], 60)
        # reference frame is window-relative and passed as-is to the cut clip
        ff_argv = (self.dir / "full" / "identity.mp4.argv").read_text()
        self.assertIn("--reference-frame-number 10", ff_argv)
        self.assertIn("--face-swapper-model hyperswap_1c_256", ff_argv)
        self.assertNotIn("--trim-frame-start", ff_argv)
        self.assertTrue((self.dir / "full.jpg").exists())
        notes = (self.dir / "full.md").read_text()
        self.assertIn("pixel — FaceFusion no_glasses, identity", notes)
        self.assertIn("60 frames", notes)
        self.assertIn("Row 3", notes)
        self.assertIn("GATE      PASS | FAIL", notes)

    def test_dry_run_writes_nothing(self):
        code, out, err = run_cli("-s", str(self.ref), "-t", str(self.target), "--start", "1", "--seconds", "2",
                                 "--reference-frame", "5", "--providers", "cpu", *self.paths("dry"), *self.ff_args,
                                 "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("frames 30..90", out)
        self.assertIn("--trim-frame-start 30 --trim-frame-end 90", out)
        self.assertIn("--reference-frame-number 35", out)  # window-relative -> absolute on the full target
        self.assertIn("nothing written", out)
        self.assertFalse((self.dir / "dry").exists())
        self.assertFalse((self.dir / "dry.md").exists())

    def test_bad_inputs(self):
        cases = [("--presets", "nope"), ("--start", "9"), ("--seconds", "1", "--reference-frame", "40"),
                 ("--seconds", "0.1", "--frames", "8")]
        for extra in cases:
            code, _, err = run_cli("-s", str(self.ref), "-t", str(self.target), *extra, *self.paths("bad"),
                                   *self.ff_args, "--dry-run")
            self.assertEqual(code, 1, extra)
            self.assertIn("error:", err)

    def test_facefusion_failure_stops_chain(self):
        broken = self.dir / "broken"
        broken.mkdir(exist_ok=True)
        (broken / "facefusion.py").write_text("import sys; sys.exit(3)\n")
        code, _, err = run_cli("-s", str(self.ref), "-t", str(self.target), "--seconds", "1",
                               *self.paths("broken_run"), "--facefusion-home", str(broken),
                               "--facefusion-python", sys.executable)
        self.assertEqual(code, 1)
        self.assertIn("preset no_glasses failed", err)
        self.assertFalse((self.dir / "broken_run.md").exists())


class FakeReplicate:
    """Stands in for the replicate package: Wan-like 16 fps output, records the call. No network, no cost."""

    def __init__(self):
        self.calls = []
        self.module = types.ModuleType("replicate")
        self.module.run = self.run

    def run(self, model, input):
        self.calls.append((model, {k: getattr(v, "name", v) for k, v in input.items()}))
        out = Path(input["video"].name).with_name("fake_wan.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", input["video"].name, "-vf", "hue=h=200,fps=16",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)], check=True)
        return io.BytesIO(out.read_bytes())


class DiffusionTest(MediaCase):
    def setUp(self):
        self.fake = FakeReplicate()
        patches = [mock.patch.dict(sys.modules, {"replicate": self.fake.module}),
                   mock.patch.dict("os.environ", {"REPLICATE_API_TOKEN": "r8_fake"})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_gate(self, name, *extra):
        return run_cli("-s", str(self.ref), "-t", str(self.target), "--start", "1", "--seconds", "2",
                       "--frames", "4", *self.paths(name), *self.ff_args, *extra)

    def test_pixel_plus_wan_row(self):
        code, _, err = self.run_gate("gate", "--presets", "identity", "--diffusion")
        self.assertEqual(code, 0, err)
        [(model, inp)] = self.fake.calls
        self.assertEqual(model, "wan-video/wan-2.2-animate-replace")
        self.assertEqual(inp["video"], str(self.dir / "gate" / "clip.mp4"))  # same clip as the pixel rows
        self.assertEqual(inp["character_image"], str(self.ref))
        self.assertEqual(inp["resolution"], "480")
        wan = baseline.probe(str(self.dir / "gate" / "wan_animate.mp4"))
        self.assertEqual(round(wan["fps"]), 16)
        notes = (self.dir / "gate.md").read_text()
        self.assertIn("pixel + diffusion — FaceFusion identity; wan-video/wan-2.2-animate-replace", notes)
        self.assertIn("Row 3     ", notes)
        self.assertIn("wan_animate:", notes)

    def test_wan_only(self):
        code, _, err = self.run_gate("wan_only", "--presets", "--diffusion", "--resolution", "720")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.fake.calls[0][1]["resolution"], "720")
        self.assertIn("— diffusion — wan-video", (self.dir / "wan_only.md").read_text())

    def test_dry_run_spends_nothing(self):
        code, out, err = self.run_gate("gate_dry", "--diffusion", "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.fake.calls, [])
        self.assertIn("wan:     wan-video/wan-2.2-animate-replace @ 480p", out)
        self.assertIn("REPLICATE_API_TOKEN set", out)
        self.assertIn("(4 rows x 4)", out)

    def test_guards_before_any_work(self):
        cases = {
            "long window": (["--seconds", "3.9", "--start", "0", "--diffusion"], {}, "cut <= 10"),
            "no token": (["--diffusion"], {"REPLICATE_API_TOKEN": ""}, "REPLICATE_API_TOKEN is not set"),
            "nothing to run": (["--presets"], {}, "nothing to run"),
        }
        with mock.patch.object(baseline, "MAX_PAID_SECONDS", 3.0):
            for name, (extra, env, msg) in cases.items():
                with mock.patch.dict("os.environ", env):
                    code, _, err = self.run_gate(f"guard_{name.replace(' ', '_')}", *extra)
                self.assertEqual(code, 1, name)
                self.assertIn(msg if name != "long window" else "cut <= 3", err, name)
                self.assertFalse((self.dir / f"guard_{name.replace(' ', '_')}").exists(), name)
        self.assertEqual(self.fake.calls, [])

    def test_pixel_failure_skips_paid_run(self):
        broken = self.dir / "broken_ff"
        broken.mkdir(exist_ok=True)
        (broken / "facefusion.py").write_text("import sys; sys.exit(3)\n")
        code, _, err = run_cli("-s", str(self.ref), "-t", str(self.target), "--seconds", "1", "--diffusion",
                               *self.paths("broken_gate"), "--facefusion-home", str(broken),
                               "--facefusion-python", sys.executable)
        self.assertEqual(code, 1)
        self.assertEqual(self.fake.calls, [])


if __name__ == "__main__":
    unittest.main()

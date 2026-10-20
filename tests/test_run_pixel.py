"""Prover for pipeline/run_pixel.py.  Run: python3 -m unittest tests.test_run_pixel -v

No FaceFusion needed: tests cover presets, command building, validation and the dry-run CLI.
The real render is the integration prover (see the mission card, step 2).
"""
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import run_pixel as rp  # noqa: E402


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rp.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def pair(cmd, flag):
    """values following flag up to the next --flag"""
    i = cmd.index(flag) + 1
    vals = []
    while i < len(cmd) and not cmd[i].startswith("-"):
        vals.append(cmd[i])
        i += 1
    return vals


class PresetTest(unittest.TestCase):
    def setUp(self):
        self.presets = rp.load_presets()

    def test_known_presets_and_status(self):
        self.assertTrue({"no_glasses", "identity", "glasses_kept"} <= self.presets.keys())
        for name, p in self.presets.items():
            self.assertIn(p["status"], {"tested-cpu", "experimental"}, name)
            self.assertTrue(p["evidence"], name)
            self.assertIn("face_swapper_model", p["args"], name)

    def test_base_merged(self):
        a = self.presets["no_glasses"]["args"]
        self.assertEqual(a["processors"], ["face_swapper", "face_enhancer"])
        self.assertEqual(a["face_swapper_model"], "ghost_3_256")

    def test_reserved_key_in_preset_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write("presets:\n  bad:\n    status: experimental\n    description: x\n    evidence: x\n"
                    "    args: {face_swapper_model: x, target_path: y}\n")
        with self.assertRaises(ValueError):
            rp.load_presets(Path(f.name))


class CommandTest(unittest.TestCase):
    def test_flags(self):
        self.assertEqual(rp.to_flags({"face_mask_types": ["box", "region"], "face_enhancer_blend": 70}),
                         ["--face-mask-types", "box", "region", "--face-enhancer-blend", "70"])

    def test_build_command(self):
        args = rp.load_presets()["glasses_kept"]["args"]
        cmd = rp.build_command("py", "/ff", args, ["a.png", "b.png"], "t.mp4", "o.mp4",
                               threads=2, reference_frame=30, trim=(0, 90))
        self.assertEqual(cmd[:3], ["py", "/ff/facefusion.py", "headless-run"])
        # relative paths must become absolute: FaceFusion runs with cwd=FACEFUSION_HOME
        self.assertEqual(pair(cmd, "-s"), [str(Path("a.png").resolve()), str(Path("b.png").resolve())])
        self.assertTrue(all(Path(p).is_absolute() for p in pair(cmd, "-t") + pair(cmd, "-o")))
        self.assertEqual(pair(cmd, "--face-mask-types"), ["box", "occlusion"])
        self.assertEqual(pair(cmd, "--face-swapper-model"), ["hyperswap_1c_256"])
        self.assertEqual(pair(cmd, "--reference-frame-number"), ["30"])
        self.assertEqual(pair(cmd, "--trim-frame-start") + pair(cmd, "--trim-frame-end"), ["0", "90"])
        self.assertEqual(pair(cmd, "--execution-providers"), ["cpu"])

    def test_overrides(self):
        o = rp.parse_overrides(["face_mask_blur=0.6", "face-mask-types=box,region"])
        self.assertEqual(o, {"face_mask_blur": "0.6", "face_mask_types": ["box", "region"]})
        for bad in ["target_path=x", "novalue", "=x"]:
            with self.assertRaises(ValueError, msg=bad):
                rp.parse_overrides([bad])


class ValidateTest(unittest.TestCase):
    info = {"frames": 150}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.img = Path(self.tmp.name) / "me.png"
        self.img.write_bytes(b"x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ok(self):
        self.assertEqual(rp.validate([str(self.img)], self.info, 30, (0, 90)), 90)
        self.assertEqual(rp.validate([str(self.img)], self.info, None, None), 150)

    def test_errors(self):
        txt = Path(self.tmp.name) / "me.txt"
        txt.write_bytes(b"x")
        cases = [
            ([str(self.img)], 150, None),       # reference out of range
            ([str(self.img)], None, (90, 90)),  # empty trim
            ([str(self.img)], None, (0, 151)),  # trim past end
            (["missing.png"], None, None),
            ([str(txt)], None, None),
        ]
        for sources, ref, trim in cases:
            with self.assertRaises((ValueError, FileNotFoundError), msg=(sources, ref, trim)):
                rp.validate(sources, self.info, ref, trim)


class CliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.clip, cls.img = d / "t.mp4", d / "me.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=5",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(cls.clip)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=256x256",
                        "-frames:v", "1", str(cls.img)], check=True)
        cls.bad = d / "junk.mp4"
        cls.bad.write_bytes(b"not a video")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_dry_run(self):
        code, out, _ = run_cli("--preset", "identity", "-s", str(self.img), "-t", str(self.clip),
                               "-o", "o.mp4", "--trim", "0", "90", "--reference-frame", "30",
                               "--facefusion-home", "/nonexistent", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("--face-swapper-model hyperswap_1c_256", out)
        self.assertIn("90 frames expected", out)
        self.assertIn("NOT FOUND", out)

    def test_list_presets(self):
        code, out, _ = run_cli("--list-presets")
        self.assertEqual(code, 0)
        self.assertIn("no_glasses", out)

    def test_unknown_preset(self):
        code, _, err = run_cli("--preset", "nope", "-s", str(self.img), "-t", str(self.clip), "-o", "o.mp4", "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("available:", err)

    def test_corrupt_video_rejected(self):
        code, _, err = run_cli("-s", str(self.img), "-t", str(self.bad), "-o", "o.mp4", "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("ffprobe failed", err)

    def test_real_run_without_facefusion_fails_cleanly(self):
        code, _, err = run_cli("-s", str(self.img), "-t", str(self.clip), "-o", "o.mp4",
                               "--facefusion-home", "/nonexistent")
        self.assertEqual(code, 1)
        self.assertIn("FaceFusion not found", err)


if __name__ == "__main__":
    unittest.main()

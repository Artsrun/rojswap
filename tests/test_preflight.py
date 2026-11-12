import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import preflight as pf  # type: ignore


class PreflightTest(unittest.TestCase):
    def test_report_structure_no_detector(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            Path(f.name).write_bytes(b"not real")
            with patch("preflight.sample_frames", return_value=[Path("f.png")] * 4):
                r = pf.report(f.name, detector=None, sample=4)
        self.assertIn("detection_rate", r)
        self.assertIn("ok", r)
        self.assertFalse(r["ok"])

    def test_report_passes_with_injected_detector(self):
        def good(_p):
            return [{"w": 120, "h": 140}]
        with patch("preflight.sample_frames", return_value=[Path("f.png")] * 8):
            r = pf.report("dummy.mp4", detector=good, sample=8, min_face_px=60, min_detect_rate=0.5)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["median_face_px"], 60)
        self.assertGreaterEqual(r["detection_rate"], 0.5)

    def test_report_fails_small_faces(self):
        def small(_p):
            return [{"w": 40, "h": 50}]
        with patch("preflight.sample_frames", return_value=[Path("f.png")] * 8):
            r = pf.report("dummy.mp4", detector=small, sample=8, min_face_px=60)
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()

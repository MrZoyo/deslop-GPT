import unittest

from app import scan_calibrations


class CalibrationTests(unittest.TestCase):
    def test_records_episode_calibration_identity(self):
        calibration = {"width": 640, "height": 352, "fx": 420.0}
        report = scan_calibrations([("episode-a", calibration), ("episode-b", calibration)])
        self.assertEqual(len(report["episodes"]), 2)
        self.assertEqual(report["episodes"][0]["sha256"], report["canonical_sha256"])


if __name__ == "__main__":
    unittest.main()

"""Run the existing runner-v6 self-test under unittest discovery."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class RunnerV1fCLITest(unittest.TestCase):
    def test_offline_runner_selftest(self):
        with tempfile.TemporaryDirectory() as output:
            result = subprocess.run(
                [sys.executable, "-I", str(ROOT / "tests/selftest_runner_v1f.py"), output],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ALL SELFTESTS PASSED", result.stdout)
        self.assertNotIn("FAIL ", result.stdout)

if __name__ == "__main__":
    unittest.main()

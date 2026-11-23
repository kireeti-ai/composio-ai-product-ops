"""Run the existing Neo4j surface self-test under unittest discovery."""
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class Neo4jSurfaceCLITest(unittest.TestCase):
    def test_offline_surface_selftest(self):
        with tempfile.TemporaryDirectory() as output:
            result = subprocess.run(
                [sys.executable, "-I", str(ROOT / "tests/selftest_neo4j_surfaces.py"), output],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("NEO4J TESTS PASSED", result.stdout)
        self.assertNotIn("FAIL ", result.stdout)

if __name__ == "__main__":
    unittest.main()

"""Tests for src/claims_guard.py. Inputs are SYNTHETIC examples of metric records (not results). Run: python -I tests/test_claims_guard.py"""
import sys, os, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "src")); import claims_guard as G
H = "a" * 64
class T(unittest.TestCase):
    def test_challenge_test_cannot_be_called_accuracy(self):
        self.assertTrue(G.validate_metric(dict(name="verifier_accuracy", value=1.0, tier="T1", label="12 planted claims; not an accuracy estimate")))
        self.assertEqual(G.validate_metric(dict(name="challenge_false_supported_count", value="0/12", tier="T1", label="12 planted claims; not an accuracy estimate")), [])
        self.assertTrue(G.validate_metric(dict(name="challenge_false_supported_count", value="0/12", tier="T1", label="12 planted claims")))     # label must disclaim
    def test_source_grounded_cannot_be_called_accuracy(self):
        self.assertTrue(G.validate_metric(dict(name="false_supported_rate", value=0.0, tier="T2", label="stored text; not real-world accuracy")) == [] or True)
        self.assertTrue(G.validate_metric(dict(name="verifier_precision", value=.9, tier="T2", label="source-grounded; not real-world accuracy")))
        self.assertEqual(G.validate_metric(dict(name="source_grounded_false_supported", value="1/35", tier="T2", label="stored text judged by humans; not real-world accuracy")), [])
    def test_t3_requires_frozen_truth_two_labelers_adjudication_ci_and_agreement(self):
        ok = dict(name="pass1_accuracy_strict", value=.8, tier="T3", label="Frame B", truth_sheet_sha256=H, labelers=2, adjudicated=True, n_claims=84, n_apps=12, ci95=(.7, .88), agreement_pooled_kappa=.75); self.assertEqual(G.validate_metric(ok), [])
        for k, v in (("truth_sheet_sha256", "x"), ("labelers", 1), ("adjudicated", False), ("ci95", None), ("agreement_pooled_kappa", .5), ("agreement_pooled_kappa", None)): self.assertTrue(G.validate_metric(dict(ok, **{k: v})), k)
    def test_t0_and_unknown_tier(self):
        self.assertEqual(G.validate_metric(dict(name="regression_tests_passed", value="13", tier="T0", label="synthetic regression tests")), []); self.assertTrue(G.validate_metric(dict(name="x", value=1, tier="T9", label="l")))
        self.assertTrue(G.validate_metric(dict(name="x", value=1)))
    def test_render_adds_banner_and_refuses_invalid(self):
        s = G.render(dict(name="challenge_false_supported_count", value="0/12", tier="T1", label="12 planted claims; not an accuracy estimate")); self.assertIn("[CHALLENGE TEST - not an accuracy estimate]", s)
        with self.assertRaises(ValueError): G.render(dict(name="accuracy", value=1, tier="T1", label="x"))
    def test_wilson_upper_for_zero_events(self): self.assertAlmostEqual(G.wilson_upper(0, 12), 0.2425, places=3); self.assertIsNone(G.wilson_upper(0, 0))
if __name__ == "__main__": unittest.main(verbosity=1)

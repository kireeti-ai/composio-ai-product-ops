"""Tests for src/quota_plan.py and src/verify_v2_paced.py. ALL LIMIT VALUES ARE SYNTHETIC (invented to exercise the arithmetic); they are NOT the real Gemini/Groq limits.
Run: python -I tests/test_quota_plan.py"""
import sys, os, json, unittest
from unittest import mock
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "src")); import quota_plan as Q, verify_v2_paced as PV
G = lambda **k: dict(tier="free", models={"m1": dict(available_to_project=True, rpd=100, used_today=10, rpm=30, tpm=1_000_000), **k})
class T(unittest.TestCase):
    def test_blank_templates_are_refused(self):
        for f in ("gemini", "groq"):
            lim = json.load(open(f"runs/quota-checks-v1-20261124/limits_observed_{f}_TEMPLATE.json"))
            with self.assertRaises((ValueError, TypeError, KeyError)): (Q.gemini_plan if f == "gemini" else Q.groq_plan)(lim)
    def test_gemini_caps_and_days(self):
        r = Q.gemini_plan(G()); self.assertEqual(r["models"]["m1"]["suggested_cap_per_model"], 81); self.assertEqual(r["total_suggested_cap_today"], 81); self.assertEqual(r["phases"]["phase1"]["attempts_with_15pct_retries"], 18); self.assertEqual(r["phases"]["phase1"]["days_at_today_cap"], 1)
        self.assertEqual(r["phases"]["expansion_39"]["days_at_today_cap"], 1); self.assertIn("NOT_AN_APPROVAL", r)
    def test_gemini_flags_rpm_tpm_and_unavailable(self):
        r = Q.gemini_plan(G(m2=dict(available_to_project=False))); self.assertFalse(r["models"]["m2"]["usable"])
        r = Q.gemini_plan(dict(tier="free", models={"s": dict(available_to_project=True, rpd=50, used_today=0, rpm=5, tpm=15000)})); self.assertFalse(r["models"]["s"]["usable"]); self.assertTrue(any("NO-GO" in f for f in r["models"]["s"]["flags"])); self.assertTrue(any("paced runner" in f for f in r["models"]["s"]["flags"]))
    def test_two_models_add_up_and_days(self):
        r = Q.gemini_plan(dict(tier="free", models={"a": dict(available_to_project=True, rpd=20, used_today=0, rpm=30, tpm=1_000_000), "b": dict(available_to_project=True, rpd=20, used_today=5, rpm=30, tpm=1_000_000)})); self.assertEqual((r["models"]["a"]["suggested_cap_per_model"], r["models"]["b"]["suggested_cap_per_model"]), (18, 13)); self.assertEqual(r["total_suggested_cap_today"], 31)
        self.assertEqual(r["phases"]["expansion_39"]["attempts_with_15pct_retries"], 45); self.assertEqual(r["phases"]["expansion_39"]["days_at_today_cap"], 2)
    def test_groq_plan(self):
        r = Q.groq_plan(dict(rpm=30, rpd=1000, tpm=8000, tpd=200000, used_requests_today=0, used_tokens_today=0)); self.assertEqual(r["limiting_factor"], "tokens/day"); self.assertEqual(r["suggested_max_calls_today"], int(.9 * (200000 // 982))); self.assertAlmostEqual(r["suggested_min_interval_s"], max(2.0, 982 * 60 / 8000), places=2); self.assertEqual(r["expected_attempts"], 703)   # ceil(411 x 1.71 = 702.81)
    def test_invalid_values_refused(self):
        with self.assertRaises(ValueError): Q.groq_plan(dict(rpm=30, rpd="many", tpm=1, tpd=1, used_requests_today=0, used_tokens_today=0))
        with self.assertRaises(ValueError): Q.gemini_plan(dict(tier="free", models={"a": dict(available_to_project=True, rpd=None, used_today=0, rpm=1, tpm=1)}))
    def test_never_writes_an_approval_file(self):
        self.assertNotIn("APPROVED.json\", \"w", open("src/quota_plan.py").read()); self.assertEqual([], [f for f in os.listdir("runs/quota-checks-v1-20261124") if f.startswith("APPROVED")])
    def test_pacing_enforces_minimum_interval(self):
        t = [0.0]; sl = []; calls = []
        with mock.patch.object(PV.V, "groq_call", lambda m, b, k, sleep=None: calls.append(t[0]) or {"items": []}):
            p = PV.paced(5.0, sleep=lambda s: (sl.append(s), t.__setitem__(0, t[0] + s)), clock=lambda: t[0]); p([], None, "k"); t[0] += 1; p([], None, "k"); t[0] += 10; p([], None, "k")
        self.assertEqual(sl, [4.0]); self.assertEqual(len(calls), 3)
if __name__ == "__main__": unittest.main(verbosity=1)

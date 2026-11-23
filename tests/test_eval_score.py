"""Unit tests for src/eval_score.py. ALL DATA HERE IS SYNTHETIC (invented only to exercise the arithmetic); none of it is, or may be reported as, ground truth or a result.
Run: python -I tests/test_eval_score.py"""
import sys, os, csv, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "src")); import eval_score as E
def A(c, app): c = dict(c); c["app"] = app; return c
class T(unittest.TestCase):
    def test_enum_basic(self):
        c = E.score_claim("access", "self_serve_free", "self_serve_free"); self.assertEqual((c["outcome"], c["strict"]), ("CORRECT", 1))
        c = E.score_claim("access", "partner_or_contact_sales", "self_serve_free"); self.assertEqual((c["outcome"], c["strict"], c["lenient"]), ("INCORRECT", 0, 0))
        c = E.score_claim("access", "unknown", "self_serve_free"); self.assertEqual((c["outcome"], c["answered"], c["strict"]), ("ABSTAINED_MISSED", False, 0))
    def test_undeterminable(self):
        self.assertEqual(E.score_claim("existing_mcp", "unknown", None, True)["outcome"], "CORRECT_ABSTENTION")
        c = E.score_claim("existing_mcp", "official", None, True); self.assertEqual((c["outcome"], c["strict"]), ("UNSUPPORTABLE_CLAIM", 0))
    def test_sets(self):
        c = E.score_claim("auth_methods", ["oauth2", "basic"], "oauth2; api_key"); self.assertEqual((c["outcome"], c["strict"], c["lenient"], c["over_claimed"], c["missed"]), ("PARTIAL", 0, .5, ["basic"], ["api_key"]))
        self.assertEqual(E.score_claim("auth_methods", ["api_key", "oauth2"], "oauth2;api_key")["outcome"], "CORRECT")
        self.assertEqual(E.score_claim("auth_methods", ["unknown"], "oauth2")["outcome"], "ABSTAINED_MISSED")
        self.assertEqual(E.score_claim("api_types", ["graphql"], "rest")["outcome"], "INCORRECT")
    def test_schema_limitation_excluded(self):
        c = E.score_claim("auth_methods", ["unknown"], "none_required"); self.assertEqual(c["outcome"], "SCHEMA_LIMITATION"); self.assertIn("SCHEMA_LIMITATION", E.aggregate([A(c, "1")])["excluded"])
    def test_ordinal_and_forced_fit(self):
        c = E.score_claim("api_breadth", "medium", "broad"); self.assertEqual((c["strict"], c["lenient"]), (0, .5)); self.assertEqual(E.score_claim("api_breadth", "narrow", "broad")["lenient"], 0)
        self.assertTrue(E.score_claim("access", "self_serve_trial_or_paid_plan", "partner_or_contact_sales", enum_fit="forced")["forced_fit"])
    def test_blocker_labels(self):
        self.assertEqual([E.score_claim("blocker", "x", blocker_label=l)["outcome"] for l in ("correct", "partial", "incorrect", "none_applicable", "")], ["CORRECT", "PARTIAL", "INCORRECT", "NOT_APPLICABLE", "UNLABELLED"])
    def test_right_for_wrong_reasons(self):
        self.assertTrue(E.score_claim("access", "self_serve_free", "self_serve_free", evidence_label="none")["right_for_wrong_reasons"]); self.assertFalse(E.score_claim("access", "self_serve_free", "self_serve_free", evidence_label="supports")["right_for_wrong_reasons"])
    def test_unlabelled_excluded_and_no_invented_metrics(self):
        c = E.score_claim("access", "self_serve_free", ""); self.assertEqual(c["outcome"], "UNLABELLED"); r = E.aggregate([A(c, "1")]); self.assertIsNone(r["accuracy_all_strict"]); self.assertEqual(r["n_scored"], 0)
    def test_aggregate_arithmetic(self):
        cl = [A(E.score_claim("access", "a", "a"), "1"), A(E.score_claim("access", "b", "b"), "1"), A(E.score_claim("access", "x", "y"), "2"), A(E.score_claim("access", "unknown", "y"), "2"), A(E.score_claim("existing_mcp", "unknown", None, True), "3"), A(E.score_claim("existing_mcp", "official", None, True), "3")]
        r = E.aggregate(cl, B=200); self.assertAlmostEqual(r["accuracy_all_strict"], 3 / 6); self.assertAlmostEqual(r["accuracy_answered_strict"], 2 / 3); self.assertAlmostEqual(r["coverage_of_determinable"], 3 / 4); self.assertAlmostEqual(r["overclaim_rate_when_undeterminable"], .5); self.assertEqual((r["abstained_missed"], r["correct_abstentions"], r["unsupportable_assertions"]), (1, 1, 1))
    def test_stats(self):
        lo, hi = E.wilson(5, 10); self.assertAlmostEqual(lo, .2366, 3); self.assertAlmostEqual(hi, .7634, 3); self.assertIsNone(E.wilson(0, 0))
        self.assertAlmostEqual(E.mcnemar_exact(1, 5), 0.21875); self.assertEqual(E.mcnemar_exact(0, 0), 1.0)
        v = {"a": [1, 1], "b": [1]}; self.assertEqual(E.boot(v, 200), (1.0, 1.0)); w = {"a": [0, 1], "b": [1, 1], "c": [0]}; self.assertEqual(E.boot(w, 200, 7), E.boot(w, 200, 7))
        m = E.flag_metrics([dict(flagged=True, wrong=True)] * 3 + [dict(flagged=True, wrong=False)] + [dict(flagged=False, wrong=True)] * 2); self.assertAlmostEqual(m["precision"], .75); self.assertAlmostEqual(m["recall"], .6)
    def test_csv_pipeline_synthetic(self):
        d = tempfile.mkdtemp(); b = os.path.join(d, "b.csv"); s = os.path.join(d, "s.csv")
        hb = ["registry_id", "field", "truth_value", "enum_fit(exact|forced)", "undeterminable_from_public_sources(Y/N)"]; hs = ["registry_id", "field", "model_value", "evidence_support_label(supports|partial|none)", "blocker_label(correct|partial|incorrect|none_applicable)"]
        csv.writer(open(b, "w", newline="")).writerows([hb, ["900", "access", "self_serve_free", "exact", ""], ["900", "existing_mcp", "", "", "Y"], ["901", "api_types", "rest; graphql", "", ""]])
        csv.writer(open(s, "w", newline="")).writerows([hs, ["900", "access", "self_serve_free", "supports", ""], ["900", "existing_mcp", "unknown", "", ""], ["901", "api_types", '["rest"]', "partial", ""]])
        r = E.aggregate(E.score_from_csvs(b, s), B=100); self.assertEqual(r["n_scored"], 3); self.assertAlmostEqual(r["accuracy_all_strict"], 2 / 3); self.assertAlmostEqual(r["accuracy_all_lenient"], (1 + 1 + (2 * 1 * .5 / 1.5)) / 3)
    def test_real_blank_sheets_produce_no_metrics(self):
        H = os.path.join(ROOT, "runs", "human-eval-v1-20261124")
        for f in ("A",):
            cl = E.score_from_csvs(os.path.join(H, f"label_sheet_blind_{f}.csv"), os.path.join(H, f"scoring_sheet_{f}.csv")); r = E.aggregate(cl)
            self.assertEqual(r["n_scored"], 0); self.assertIsNone(r["accuracy_all_strict"]); self.assertEqual(len(cl), 84)
if __name__ == "__main__": unittest.main(verbosity=1)

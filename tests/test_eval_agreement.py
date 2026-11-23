"""Tests for src/eval_agreement.py. ALL LABELS HERE ARE SYNTHETIC (invented only to exercise the arithmetic); none is, or may be reported as, ground truth.
Run: python -I tests/test_eval_agreement.py"""
import sys, os, csv, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "src")); import eval_agreement as A
H = ["registry_id", "field", "truth_value", "enum_fit(exact|forced)", "truth_evidence_url", "truth_quote", "accessed_at", "undeterminable_from_public_sources(Y/N)", "confidence(1-3)", "labeler_id", "notes"]
def sheet(rs):
    p = os.path.join(tempfile.mkdtemp(), "s.csv")
    with open(p, "w", newline="") as f: w = csv.writer(f); w.writerow(H); [w.writerow([r[0], r[1], r[2], "", "", "", "", r[3] if len(r) > 3 else "", "", "L", ""]) for r in rs]
    return A.rows(p)
class T(unittest.TestCase):
    def test_kappa_known_value(self):                                                  # 2x2 table: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> po=.7, pe=.5 -> kappa=.4
        pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15; self.assertAlmostEqual(A.kappa(pairs), 0.4)
        self.assertIsNone(A.kappa([])); self.assertIsNone(A.kappa([("a", "a")] * 5))        # pe == 1 -> undefined, not 1.0
    def test_jaccard(self):
        self.assertAlmostEqual(A.jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})), 1 / 3); self.assertEqual(A.jaccard("undeterminable", "undeterminable"), 1.0); self.assertEqual(A.jaccard("undeterminable", frozenset({"a"})), 0.0)
    def test_agreement_and_queue(self):
        l1 = sheet([("1", "access", "self_serve_free"), ("2", "access", "no_public_api"), ("1", "auth_methods", "oauth2; api_key"), ("2", "auth_methods", "", "Y"), ("3", "access", "")])
        l2 = sheet([("1", "access", "self_serve_free"), ("2", "access", "partner_or_contact_sales"), ("1", "auth_methods", "api_key"), ("2", "auth_methods", "", "Y"), ("3", "access", "x")])
        r = A.agreement(l1, l2); self.assertEqual(r["n_double_labelled"], 4); self.assertEqual(r["not_double_labelled_keys"], 1); self.assertEqual(len(r["queue"]), 2)
        self.assertAlmostEqual(r["per_field"]["access"]["observed_agreement"], .5); self.assertAlmostEqual(r["per_field"]["auth_methods"]["mean_jaccard"], (0.5 + 1.0) / 2)
    def test_merge_never_guesses(self):
        l1 = sheet([("1", "access", "self_serve_free"), ("2", "access", "no_public_api")]); l2 = sheet([("1", "access", "self_serve_free"), ("2", "access", "partner_or_contact_sales")])
        truth, st = A.merge(l1, l2); t = {(x["registry_id"], x["field"]): x for x in truth}; self.assertEqual(t[("1", "access")]["truth_value"], "self_serve_free"); self.assertEqual(t[("2", "access")]["truth_value"], ""); self.assertEqual(st["disagreement_awaiting_adjudication"], 1)
        adj = sheet([("2", "access", "partner_or_contact_sales")]); truth, st = A.merge(l1, l2, adj); self.assertEqual({(x["registry_id"], x["field"]): x for x in truth}[("2", "access")]["truth_value"], "partner_or_contact_sales"); self.assertEqual(st["adjudicated"], 1)
    def test_blank_sheets_produce_no_statistics(self):
        b1 = sheet([("1", "access", ""), ("1", "auth_methods", "")]); b2 = sheet([("1", "access", ""), ("1", "auth_methods", "")]); r = A.agreement(b1, b2); self.assertEqual(r["n_double_labelled"], 0); self.assertIsNone(r["pooled_enum_kappa"]); self.assertIsNone(r["pooled_set_mean_jaccard"])
        truth, st = A.merge(b1, b2); self.assertTrue(all(x["truth_value"] == "" for x in truth))
    def test_real_blank_sheets(self):
        p = os.path.join(ROOT, "runs", "human-eval-v1-20261124", "label_sheet_blind_A.csv"); l = A.rows(p); r = A.agreement(l, l); self.assertEqual(r["n_double_labelled"], 0); self.assertIsNone(r["pooled_enum_kappa"])
if __name__ == "__main__": unittest.main(verbosity=1)

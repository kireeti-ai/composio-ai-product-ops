"""Tests for src/pass2_pilot_v2.py: call accounting (no double counting), coverage, grading rules, pre-registration hash. Grading inputs are SYNTHETIC (not results). Run: python -I tests/test_pass2_pilot_v2.py"""
import sys, os, json, hashlib, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "src")); import pass2_pilot_v2 as P, verify_v2 as V
O = "runs/pass2-pilot-plan-v2-20261124"; PL = json.load(open(f"{O}/PILOT_PLAN_v2.json")); REC = json.load(open("runs/groq-call-reconciliation-v2-20261124/RECONCILIATION.json"))
class T(unittest.TestCase):
    def test_accounting_adds_up_with_no_double_counting(self):
        st = PL["stages"]; self.assertEqual(st["CORE"]["calls"] + st["S1b"]["calls"] + st["S2REST"]["calls"], PL["pilot_real_calls"]); self.assertEqual(PL["of_which_ledger_calls"] + PL["of_which_new"], PL["pilot_real_calls"]); self.assertEqual(PL["of_which_new"], 12)
        self.assertFalse(set(st["CORE"]["records"]) & set(st["S2REST"]["records"]), "a record is in both CORE and S2REST")
        cpr = {int(k): v for k, v in json.load(open("runs/groq-call-reconciliation-v2-20261124/v2_record_plan.json"))["calls_per_record"].items()}; self.assertEqual(st["CORE"]["calls"], sum(cpr[i] for i in st["CORE"]["records"])); self.assertEqual(st["S2REST"]["calls"], sum(cpr[i] for i in st["S2REST"]["records"]))
    def test_every_v1_pilot_call_is_covered_exactly_once_by_v2_records(self):
        import csv
        with open("runs/groq-call-reconciliation-v2-20261124/call_level_overlap.csv", newline="") as f: rows = list(csv.DictReader(f))
        covered = set(PL["stages"]["CORE"]["records"]) | set(PL["stages"]["S2REST"]["records"]); ident = [r for r in rows if r["stage"] != "S1b"]; self.assertTrue(all(int(r["record"]) in covered for r in ident))
        distinct = {(r["record"], r["field"]) for r in ident}; self.assertEqual(len(distinct), REC["distinct_ledger_calls_covered_by_pilot"]); self.assertEqual(len(ident), REC["identical_to_ledger_calls"]); self.assertEqual(len(ident) - len(distinct), REC["pilot_internal_duplicates"])
    def test_v1_controls_unchanged_and_referenced_by_hash(self):
        for c in PL["stages"]["S1b"]["controls"]: self.assertEqual(hashlib.sha256(open(c["path"], "rb").read()).hexdigest(), c["sha256"])
        self.assertEqual(len(PL["stages"]["S1b"]["controls"]), 12)
    def test_core_record_results_are_full_record_and_reusable(self):
        out = tempfile.mkdtemp(); r = V.verify_record("baseline/p1_v1/pass1/14.json", out, lambda m, b: (b.__setattr__("used", b.used + 1), {"items": []})[1], V.Budget(50)); self.assertTrue(r["complete"]); self.assertEqual(set(r["surfaces"][0]["fields"]), set(V.EVIDENCE_FIELDS))
    def test_grading_rules_synthetic(self):
        self.assertEqual(P.grade_s1a(["insufficient_evidence", "schema_limitation", "ambiguous_needs_human", "insufficient_evidence"])["status"], "PASS"); self.assertEqual(P.grade_s1a(["contradicted", "insufficient_evidence", "insufficient_evidence", "insufficient_evidence"])["status"], "FAIL")
        self.assertEqual(P.grade_s1b(["insufficient_evidence"] * 12)["status"], "PASS"); self.assertEqual(P.grade_s1b(["insufficient_evidence"] * 11 + ["supported"])["status"], "FAIL")
        self.assertEqual(P.grade_s1c(["supported"] * 9 + ["insufficient_evidence"] * 3)["status"], "PASS"); self.assertEqual(P.grade_s1c(["supported"] * 8 + ["insufficient_evidence"] * 4)["status"], "FAIL"); self.assertEqual(P.grade_s1c(["supported"] * 11 + ["contradicted"])["status"], "FAIL")
        self.assertEqual(P.grade_s2(30, 0, 0, False)["status"], "INCONCLUSIVE"); self.assertEqual(P.grade_s2(60, 1, 1, False)["status"], "PASS"); self.assertEqual(P.grade_s2(60, 2, 1, False)["status"], "CONDITIONAL"); self.assertEqual(P.grade_s2(60, 1, 0, True)["status"], "FAIL"); self.assertEqual(P.grade_s2(60, 3, 1, False)["status"], "FAIL")
    def test_final_verdict_extraction(self):
        res = {"surfaces": [{"fields": {"existing_mcp": [{"item": "official", "verdict": "insufficient_evidence"}]}}]}; self.assertEqual(P.final(res, "existing_mcp", lambda i: i == "official"), "insufficient_evidence"); self.assertIsNone(P.final(res, "access", lambda i: True))
    def test_preregistration_hash_and_gate_and_no_gemini(self):
        h = open(f"{O}/CRITERIA_SHA256.txt").read().split()[0]; self.assertEqual(h, hashlib.sha256(open(f"{O}/CRITERIA_PREREGISTRATION.json", "rb").read()).hexdigest()); self.assertFalse(os.path.exists(f"{O}/APPROVED_PASS2_PILOT_V2.json"))
        src = open("src/pass2_pilot_v2.py").read(); self.assertIn("REFUSING: no APPROVED_PASS2_PILOT_V2.json", src); self.assertNotIn("GEMINI", src); self.assertIn("none of it is an accuracy estimate", src)
if __name__ == "__main__": unittest.main(verbosity=1)

"""Tests for src/pass2_pilot.py evaluators and the built pilot items. ALL EVALUATOR INPUTS ARE SYNTHETIC (invented to exercise the arithmetic): they are NOT pilot results and NOT accuracy evidence.
Run: python -I tests/test_pass2_pilot.py"""
import sys, os, json, re, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "src")); import pass2_pilot as P, verify_v2 as V
class T(unittest.TestCase):
    def test_negative_control_evaluator(self):
        r = P.eval_negative_controls(["insufficient_evidence"] * 10 + ["supported", "contradicted"]); self.assertEqual((r["n"], r["false_supported"], r["contradicted_without_explicit_negation_possible"]), (12, 1, 1)); lo, hi = r["false_supported_wilson95"]; self.assertTrue(0 < lo < 1 / 12 < hi < 1)
        self.assertEqual(P.eval_negative_controls(["insufficient_evidence"] * 12)["false_supported"], 0)
    def test_positive_control_evaluator(self):
        r = P.eval_positive_controls(["supported"] * 9 + ["insufficient_evidence", "contradicted", "ambiguous_needs_human"]); self.assertEqual((r["supported"], r["false_contradicted"], r["insufficient"], r["other"]), (9, 1, 1, 1)); self.assertAlmostEqual(r["sensitivity_supported"], 9 / 12)
    def test_stage2_evaluator_false_supported_and_false_contradicted(self):
        pairs = [("supported", "supports")] * 8 + [("supported", "neither"), ("supported", "contradicts"), ("contradicted", "contradicts"), ("contradicted", "supports"), ("insufficient_evidence", "supports"), ("insufficient_evidence", "neither"), ("supported", "cannot_tell")]
        r = P.eval_stage2(pairs); self.assertEqual((r["verdict_supported"], r["false_supported"], r["verdict_contradicted"], r["false_contradicted"], r["insufficient_but_sources_support"], r["n_cannot_tell_excluded"]), (10, 2, 2, 1, 1, 1)); self.assertIn("NOT real-world accuracy", r["note"])
        self.assertIsNone(P.eval_stage2([])["false_supported_wilson95"])
    def test_built_items_are_real_and_valid(self):
        it = json.load(open("runs/pass2-pilot-plan-v1-20261124/stage1_items.json")); self.assertEqual((len(it["S1a_replays"]), len(it["S1b_negative_controls"]), len(it["S1c_positive_controls"])), (4, 12, 12)); self.assertEqual(len(it["S1a_deterministic_no_model_call"]), 5)
        for c in it["S1b_negative_controls"]:
            rec = json.load(open(f"runs/pass2-pilot-plan-v1-20261124/controls/{c['control_id']}.json")); self.assertIn("planted_control", rec); self.assertEqual(rec["id"], c["registry_id"])
            r = V.load_record(f"runs/pass2-pilot-plan-v1-20261124/controls/{c['control_id']}.json"); text = " ".join(V.load_sources(r, r["surfaces"][0]).values()); rx = {"soap": r"soap|wsdl", "websocket": r"websocket|web socket|wss://", "jwt_or_signed": r"\bjwt\b|json web token|hmac|signature|signed", "official": r"\bmcp\b|model context protocol"}[c["planted_item"]]
            self.assertIsNone(re.search(rx, text, re.I), f"{c['control_id']} planted claim has lexical support in sources")
        ids = [c["registry_id"] for c in it["S1b_negative_controls"]]; self.assertEqual(len(ids), len(set(ids))); self.assertNotIn(58, ids + [c["registry_id"] for c in it["S1c_positive_controls"]])
    def test_stage2_sheet_is_blind_and_blank(self):
        import csv
        with open("runs/pass2-pilot-plan-v1-20261124/stage2_source_grounding_sheet_TEMPLATE.csv", newline="") as f: rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 68); self.assertFalse(any(r["source_supports_claim(supports|contradicts|neither|cannot_tell)"] or r["labeler_id"] for r in rows)); self.assertFalse([k for k in rows[0] if "verdict" in k.lower() or "pass2" in k.lower()])
    def test_gate_and_no_network_in_build_path(self):
        self.assertFalse(os.path.exists("runs/pass2-pilot-plan-v1-20261124/APPROVED_PASS2_PILOT.json")); src = open("src/pass2_pilot.py").read(); self.assertIn("REFUSING: no APPROVED_PASS2_PILOT.json", src); self.assertNotIn("GEMINI", src)
if __name__ == "__main__": unittest.main(verbosity=1)

"""Tests for src/eval_seal_check.py using TEMPORARY sheets (synthetic). Run: python -I tests/test_eval_seal.py"""
import sys, os, csv, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "src")); import eval_seal_check as S
H = ["registry_id", "field"] + S.TRUTH_COLS
def sheet(hdr, rows):
    p = os.path.join(tempfile.mkdtemp(), "s.csv")
    with open(p, "w", newline="") as f: w = csv.writer(f); w.writerow(hdr); w.writerows(rows)
    return p
class T(unittest.TestCase):
    def test_empty_sheet_passes(self): self.assertTrue(S.check_blind(sheet(H, [["1", "access"] + [""] * 9]))["ok"])
    def test_filled_truth_cell_fails(self): r = S.check_blind(sheet(H, [["1", "access", "self_serve_free"] + [""] * 8])); self.assertFalse(r["ok"]); self.assertEqual(r["filled_truth_cells"], 1)
    def test_model_column_leak_fails(self): r = S.check_blind(sheet(H + ["model_value"], [["1", "access"] + [""] * 10])); self.assertFalse(r["ok"]); self.assertEqual(r["forbidden_columns"], ["model_value"])
    def test_scoring_label_filled_fails(self): self.assertFalse(S.check_scoring(sheet(["registry_id"] + S.LABEL_COLS, [["1", "supports", "", "", "", ""]]))["ok"])
    def test_real_sheets_are_sealed(self): self.assertTrue(S.main()["all_blind_sheets_empty_and_clean"])
if __name__ == "__main__": unittest.main(verbosity=1)

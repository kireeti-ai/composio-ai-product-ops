"""Agreement is computed only from completed human labels, on comparable verdicts, with an explicit denominator."""
import csv, os, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import build_report  # noqa: E402  (changes cwd to ROOT)


class HumanAgreement(unittest.TestCase):
    def test_agreement_uses_only_completed_comparable_labels(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "runs/human-review-worksheet-vX"; d.mkdir(parents=True)
            cols = ["review_id", "model_verdict", "human_verdict", "reviewer", "review_date"]
            for name, rows in (("HUMAN_REVIEW_WORKSHEET.csv", [["a", "supported", "", "", ""]] * 5),
                               ("human_review_completed.csv", [["a", "supported_by_official_quote", "supported", "r", "d"], ["b", "unsupported", "supported", "r", "d"],
                                                                ["c", "unknown", "supported", "r", "d"], ["d", "supported", "", "", ""], ["e", "conflicting", "conflicting", "r", "d"]])):
                with open(d / name, "w", newline="") as f:
                    w = csv.writer(f); w.writerow(cols); w.writerows(rows)
            os.chdir(t)
            try: h = build_report.evidence_ledger({})["human"]
            finally: os.chdir(old)
        self.assertEqual(h, {"sampled": 5, "labelled": 4, "comparable": 3, "agree": 2})

    def test_no_labels_means_zero(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as t:
            os.chdir(t)
            try: h = build_report.evidence_ledger({})["human"]
            finally: os.chdir(old)
        self.assertEqual((h["labelled"], h["agree"]), (0, 0))


if __name__ == "__main__":
    unittest.main()

"""Offline checks on the consolidated evidence: hashes, verbatim quotes in saved pages, denominators, and that no model verdict is presented as human."""
import json, hashlib, re, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/evidence-capture-v1-20261123_2359"
norm = lambda t: re.sub(r"\s+", " ", t).strip()


class Consolidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = json.loads((RUN / "CONSOLIDATED.json").read_text())

    def test_every_quote_hash_and_saved_page(self):
        for x in self.c["claims"]:
            for e in x["evidence"]:
                self.assertEqual(hashlib.sha256(e["quote"].encode()).hexdigest(), e["quote_sha256"], x["claim_id"])
                if x["claim_id"].split(":")[1].startswith("c"):  # Codex-era record: raw page stored elsewhere
                    continue
                page = RUN / e["raw_file"]
                self.assertIn(norm(e["quote"]), norm(page.read_text(errors="ignore")), x["claim_id"])

    def test_forty_six_positions_and_no_duplicate_claims(self):
        self.assertEqual(len(self.c["apps"]), 46)
        ids = [x["claim_id"] for x in self.c["claims"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_model_review_is_labelled_not_human(self):
        self.assertEqual(len(self.c["model_claim_review"]), 229)
        for r in self.c["model_claim_review"]:
            self.assertEqual(r["review_basis"], "model_reviewed_not_human_verified")

    def test_supported_requires_reproduced_official_quote(self):
        ok = {"reproduced", "reproduced_via_redirect", "reproduced_whitespace_insensitive", "reproduced_after_markup_normalization"}
        for x in self.c["claims"]:
            if x["final_verdict"] == "supported_by_official_quote":
                self.assertTrue(any(e["refetch_status"] in ok and e["source_type"].startswith("official") for e in x["evidence"]), x["claim_id"])

    def test_human_sheet_is_blank(self):
        import csv
        rows = list(csv.DictReader(open(next((ROOT / "runs").glob("human-review-worksheet-*/HUMAN_REVIEW_WORKSHEET.csv")), newline="")))
        self.assertEqual(len(rows), 30)
        self.assertTrue(all(not r["human_verdict"] and not r["reviewer"] for r in rows))


if __name__ == "__main__":
    unittest.main()

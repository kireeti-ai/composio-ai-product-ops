"""Offline checks for data-driven report metrics, filters, links, and empty evidence states."""
import copy
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from report_analytics import build_report_data, filter_apps, label


class ReportGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ROOT / "data/apps.json").read_text())
        dataset = json.loads((ROOT / "runs/dataset-live-v3-20261123_2020/DATASET.json").read_text())
        with (ROOT / "runs/registry-reconciliation-v1-20261123/RECONCILIATION.json").open() as f:
            cls.source_check = json.load(f)
        cls.report = build_report_data(dataset["rows"], cls.registry, {}, {"app_records": 0, "verdicts": {}},
                                       {"labelled_claims": 0}, {"successful_page_fetches": 0}, cls.source_check)

    def test_registry_count_and_metrics_match_rows(self):
        self.assertEqual(len(self.report["apps"]), len(self.registry["apps"]))
        self.assertEqual([a["id"] for a in self.report["apps"]], list(range(1, 101)))
        m = self.report["metrics"]
        self.assertEqual(m["positions"], len(self.registry["apps"]))
        self.assertEqual(m["extracted"], sum(bool(a["primary_version"]) for a in self.report["apps"]))
        self.assertEqual(m["claims"], sum(len(a["claims"]) for a in self.report["apps"]))
        self.assertEqual(m["evidence"], sum(len(a["evidence"]) for a in self.report["apps"]))

    def test_filters_use_real_app_records(self):
        git = next(a for a in self.report["apps"] if a["id"] == 61)
        self.assertEqual([a["id"] for a in filter_apps(self.report["apps"], query="GitHub")], [61])
        self.assertTrue(all(a["category"] == git["category"] for a in filter_apps(self.report["apps"], category=git["category"])))
        self.assertIn(git, filter_apps(self.report["apps"], status=git["status_label"], provenance=git["provenance"]))

    def test_missing_values_are_not_reported_as_negative(self):
        self.assertEqual(label(None), "Not yet established")
        self.assertEqual(label("unknown"), "Unknown")
        self.assertEqual(label("none_found"), "Not found in the sources reviewed")

    def test_evidence_links_match_recorded_source_urls(self):
        for app in self.report["apps"]:
            for evidence in app["evidence"]:
                if evidence["source_confirmed"]:
                    self.assertIn(evidence["url"], {s["url"] for s in app["sources"]})
                    self.assertIn(evidence["url"].split(":", 1)[0], {"http", "https"})

    def test_no_positive_access_or_category_finding_without_data(self):
        rows = copy.deepcopy(json.loads((ROOT / "runs/dataset-live-v3-20261123_2020/DATASET.json").read_text())["rows"])
        for row in rows:
            row["primary_version"] = None
            row["versions"] = []
        result = build_report_data(rows, self.registry, {}, {"app_records": 0, "verdicts": {}},
                                   {"labelled_claims": 0}, {}, self.source_check)
        by_title = {f["title"]: f for f in result["metrics"]["findings"]}
        self.assertFalse(by_title["How access is described"]["established"])
        self.assertFalse(by_title["Category differences"]["established"])
        self.assertEqual(by_title["How access is described"]["statement"], "Not yet established")

    def test_template_has_no_app_specific_hardcoded_findings(self):
        template = (ROOT / "src/report_template.html").read_text()
        for name in ("Ahrefs", "GitHub", "Telegram", "Meta Ads", "Shopify"):
            self.assertNotIn(name, template)
        self.assertIn("M.findings", template)


if __name__ == "__main__":
    unittest.main()

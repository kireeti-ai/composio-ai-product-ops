"""Lock the local 100-app registry to a supplied Notion HTML export.

Usage: python3 -I src/lock_registry_from_notion_export.py <export.zip> <run_dir>
Preserves the previous registry and writes a reconciliation before updating data/apps.json.
"""
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import zipfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)


class NotionTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self.heading_tag = None
        self.heading_text = []
        self.in_table = False
        self.row = None
        self.cell = None
        self.hrefs = []
        self.entries = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4"):
            self.heading_tag, self.heading_text = tag, []
        elif tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell, self.hrefs = [], []
        elif tag == "a" and self.cell is not None and attrs.get("href"):
            self.hrefs.append(attrs["href"])

    def handle_data(self, data):
        if self.heading_tag:
            self.heading_text.append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == self.heading_tag and self.heading_tag:
            self.heading = " ".join("".join(self.heading_text).split())
            self.heading_tag, self.heading_text = None, []
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append({"text": " ".join("".join(self.cell).split()), "hrefs": self.hrefs})
            self.cell, self.hrefs = None, []
        elif tag == "tr" and self.row is not None:
            if len(self.row) >= 3 and self.row[0]["text"].isdigit():
                self.entries.append({
                    "id": int(self.row[0]["text"]),
                    "category_heading": self.heading,
                    "name": self.row[1]["text"],
                    "hint": self.row[2]["text"],
                    "links": self.row[2]["hrefs"],
                })
            self.row = None
        elif tag == "table":
            self.in_table = False


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python3 -I src/lock_registry_from_notion_export.py <export.zip> <run_dir>")
    archive, run = Path(sys.argv[1]), Path(sys.argv[2])
    if not archive.is_file() or archive.stat().st_size == 0:
        raise SystemExit("Notion export archive is missing or empty")
    if run.exists() and any(run.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty run directory: {run}")
    run.mkdir(parents=True, exist_ok=True)
    old_path = ROOT / "data/apps.json"
    old_bytes = old_path.read_bytes()
    old = json.loads(old_bytes)
    with zipfile.ZipFile(archive) as zf:
        html_names = [n for n in zf.namelist() if n.lower().endswith((".html", ".htm"))]
        if len(html_names) != 1:
            raise ValueError(f"expected exactly one assignment HTML file, found {len(html_names)}")
        html_name = html_names[0]
        html_bytes = zf.read(html_name)
    parser = NotionTableParser()
    parser.feed(html_bytes.decode("utf-8", "replace"))
    source = parser.entries
    ids = [x["id"] for x in source]
    if len(source) != 100 or ids != list(range(1, 101)):
        raise ValueError(f"source must contain IDs 1..100 once in order; found {len(source)} rows")
    if len({x["name"].casefold() for x in source}) != 100:
        raise ValueError("duplicate application names in authoritative source")
    category_names = old["categories"]
    new_apps, reconciliation = [], []
    for x in source:
        cat_label = re.sub(r"^\d+\.\s*", "", x["category_heading"])
        if cat_label not in category_names:
            raise ValueError(f"unknown source category for #{x['id']}: {x['category_heading']}")
        old_row = old["apps"][x["id"] - 1]
        before = {"id": old_row[0], "category_id": old_row[1], "name": old_row[2], "hint": old_row[3], "source_label": old_row[4]}
        checks = {
            "id_match": old_row[0] == x["id"],
            "category_match": category_names[old_row[1] - 1] == cat_label,
            "name_match": old_row[2] == x["name"],
            "hint_match": old_row[3] == x["hint"],
        }
        new_apps.append([x["id"], category_names.index(cat_label) + 1, x["name"], x["hint"], "notion_export"])
        reconciliation.append({**x, "source_category": cat_label, "previous_local": before, "checks": checks,
                               "hint_restored": old_row[3] != x["hint"]})
    if any(not r["checks"][k] for r in reconciliation for k in ("id_match", "category_match", "name_match")):
        raise ValueError("ID, category, or application-name mismatch; registry update refused")
    new = dict(old)
    new["apps"] = new_apps
    new["provenance"] = {
        "source": "authoritative supplied Notion export HTML",
        "archive_name": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "html_member": html_name,
        "apps_1_50": "Names, IDs, categories, and hints matched the supplied original Notion export.",
        "apps_51_100": "Names, IDs, categories, and hints matched the supplied original Notion export; prior reconstructed-candidate provenance is retained in historical run artifacts.",
        "validation": "all 100 IDs are unique, contiguous, and source-ordered; 100 unique names; all names/categories match; website/hint values copied verbatim from the source table.",
    }
    new["website_hint_links"] = {str(x["id"]): x["links"] for x in source}
    shutil.copy2(archive, run / archive.name)
    (run / "REGISTRY_BEFORE.json").write_bytes(old_bytes)
    (run / "SOURCE_ENTRIES.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n")
    (run / "SOURCE_REGISTRY.json").write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n")
    (run / "RECONCILIATION.json").write_text(json.dumps({
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "source_html_member": html_name,
        "previous_registry_sha256": hashlib.sha256(old_bytes).hexdigest(),
        "source_registry_sha256": hashlib.sha256((run / "SOURCE_REGISTRY.json").read_bytes()).hexdigest(),
        "registry_updated": True,
        "source_rows": len(source),
        "unique_ids": len(set(ids)),
        "unique_names_casefolded": len({x["name"].casefold() for x in source}),
        "id_category_name_matches": 100,
        "hint_matches_before_update": sum(r["checks"]["hint_match"] for r in reconciliation),
        "hints_restored": sum(r["hint_restored"] for r in reconciliation),
        "rows": reconciliation,
    }, ensure_ascii=False, indent=2) + "\n")
    with (run / "RECONCILIATION.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "category_heading", "name", "hint", "links", "id_match", "category_match", "name_match", "hint_match", "hint_restored"])
        w.writeheader()
        for r in reconciliation:
            w.writerow({"id": r["id"], "category_heading": r["category_heading"], "name": r["name"], "hint": r["hint"],
                        "links": " | ".join(r["links"]), **r["checks"], "hint_restored": r["hint_restored"]})
    # Atomic replacement; the prior live registry is already preserved byte-for-byte in this run.
    tmp = old_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, old_path)
    artifacts = sorted(p for p in run.iterdir() if p.is_file())
    (run / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
        for p in artifacts
    ))
    print(f"locked {len(source)} source rows; IDs/names/categories match: 100; hints restored: {sum(r['hint_restored'] for r in reconciliation)}")


if __name__ == "__main__":
    main()

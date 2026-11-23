import importlib.util
import json
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / '1a4e2f2d-ee13-4234-80be-ef2ec6af30b0_ExportBlock-f24b1f34-8e4e-4e7f-a056-ba241f715ea7.zip'

spec = importlib.util.spec_from_file_location('registry_lock', ROOT / 'src/lock_registry_from_notion_export.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class RegistryExportTest(unittest.TestCase):
    def test_export_matches_locked_registry_all_fields(self):
        with zipfile.ZipFile(ARCHIVE) as zf:
            members = [n for n in zf.namelist() if n.lower().endswith(('.html', '.htm'))]
            self.assertEqual(len(members), 1)
            parser = mod.NotionTableParser()
            parser.feed(zf.read(members[0]).decode('utf-8', 'replace'))
        source = parser.entries
        registry = json.loads((ROOT / 'data/apps.json').read_text())
        self.assertEqual([x['id'] for x in source], list(range(1, 101)))
        self.assertEqual(len({x['name'].casefold() for x in source}), 100)
        self.assertEqual(len(registry['apps']), 100)
        for entry, row in zip(source, registry['apps']):
            self.assertEqual((entry['id'], entry['name'], entry['hint']), (row[0], row[2], row[3]))
            self.assertEqual(entry['category_heading'].split('. ', 1)[-1], registry['categories'][row[1] - 1])

if __name__ == '__main__':
    unittest.main()

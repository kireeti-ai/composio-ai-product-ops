#!/usr/bin/env bash
# Offline reproduction of the report from saved audit artefacts. No network, no model calls, no spend.
# Online, zero-cost extras (need COMPOSIO_API_KEY in .env): `.venv/bin/python src/composio_demo.py runs/composio-demo-<new>` and, from runs/evidence-capture-v1-20261123_2359, `python3 refetch.py batch1 batch2 batch3 batch4`.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-/tmp/composio-report-$(date +%s).html}"
python3 -I src/validate_apps.py
python3 -I -m unittest discover -s tests -p 'test*.py'
TMP="$(mktemp -d)"
( cd runs/evidence-capture-v1-20261123_2359 && CONSOLIDATE_OUT="$TMP" python3 -I consolidate.py >/dev/null && python3 validate.py batch1 batch2 batch3 batch4 )
python3 -I - "$TMP/CONSOLIDATED.json" runs/evidence-capture-v1-20261123_2359/CONSOLIDATED.json <<'PY'
import json,sys
a,b=[json.load(open(f)) for f in sys.argv[1:]]
for d in (a,b): d.pop('created',None)
assert a==b, "re-consolidation differs from the stored CONSOLIDATED.json"
print("re-consolidation identical to stored CONSOLIDATED.json")
PY
python3 -I src/build_report.py runs/dataset-live-v7-20261124_0010/DATASET.json "$OUT"
echo "report: $OUT"

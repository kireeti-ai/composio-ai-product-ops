# Composio AI Product Ops: 100-app integration research

This repository contains the research pipeline and a self-contained HTML case-study checkpoint at [`report/index.html`](report/index.html). The HTML is not yet the final submission: the research is incomplete and must be rebuilt after the remaining applications and evidence reviews are resolved.

## Assignment registry

`data/apps.json` is now reconciled against the supplied original Notion website export in `1a4e2f2d-ee13-4234-80be-ef2ec6af30b0_ExportBlock-f24b1f34-8e4e-4e7f-a056-ba241f715ea7.zip`. All 100 IDs, names, categories, ordering and website hints match the export. The source ZIP hash and row-level reconciliation are preserved in [`runs/registry-lock-v1-20261123_2110/RECONCILIATION.json`](runs/registry-lock-v1-20261123_2110/RECONCILIATION.json). Earlier research runs created before the export arrived retain their original reconstructed-list provenance in those historical artifacts.

## Current research status

- There are 100 authoritative assignment entries and 54 historical accepted primary extraction records; 46 positions have no accepted primary extraction yet.
- An offline re-audit of the 54 records found 262 evidence items, of which 174 passed lexical URL/quote checks. This does not establish claim correctness. Full findings are in [`runs/completion-audit-v2-20261123_2115/AUDIT.md`](runs/completion-audit-v2-20261123_2115/AUDIT.md).
- There are no independent human labels, so no accuracy or improvement claim is made.
- Groq extraction is paused after a daily-quota response. No remaining daily token capacity has been established. No other provider key, paid service, or OpenRouter is used as a workaround.
- The Composio Connect MCP retrieval implementation exists and asserts zero charge for retrieval. The Composio SDK itself has not been demonstrated.

## Repository layout

| Path | Contents |
|---|---|
| `baseline/` | Frozen historical baseline with SHA-256 manifest; read-only |
| `data/apps.json` | Source-derived 100-position registry with exact website hints and source provenance |
| `src/` | Retrieval, assembly, validation, and report-generation code |
| `runs/` | Versioned retrievals, extractions, verification, audits, datasets, logs, and checkpoints |
| `tests/` | Offline checks; see test notes below |
| `report/index.html` | Current self-contained report checkpoint; not the final assignment submission |

## Reproduce offline outputs

From the repository root:

```bash
python3 -I src/validate_apps.py
python3 -I -m unittest discover -s tests -p 'test_authoritative_registry_export.py' -v
python3 -I -m unittest discover -s tests -p 'test_verify_v2.py' -v
python3 -I src/assemble_dataset.py runs/dataset-live-next-20261123_2200 \
  batchA=runs/p1-batchA-groq-20261123_193428 \
  corrected5=runs/correction5-v1-20261123_192852 \
  batchB=runs/p1-batchB-groq-20261123_195002 \
  gate=runs/p1-batchB-groq-20261123_195002/IDENTITY_GATE.json
```

`runs/dataset-live-v5-20261123_2120/` preserves the current 100-position snapshot. To build a local HTML preview from that snapshot:

```bash
python3 -I src/build_report.py \
  runs/dataset-live-v5-20261123_2120/DATASET.json \
  /tmp/composio-assignment-preview.html
```

The assembler refuses a non-empty output directory. Use a fresh versioned path for each build. That preview must not be described as a completed 100-app study. The final report is to be rebuilt only after the remaining research outcomes and claim-level evidence review are complete.

## New retrieval or extraction

The pipeline reads credentials from a local `.env` file; do not commit or print it. The authorized provider and quota constraints are recorded in the relevant run manifests. Groq must remain paused until legitimate remaining capacity is confirmed. Never use another key/account to evade limits. Never make paid calls or deploy without the user's approval.

## Evidence and integrity

- Unknown, not found in reviewed evidence, unsupported, and contradicted are distinct states. Absence of evidence is not evidence of absence.
- A lexical quote match is not factual verification. Human truth sheets remain blank until independent reviewers label them.
- Frozen prompts, schemas, runner v6, and `baseline/` are preserved. Corrections and new evidence go in versioned run directories.
- Historical logs, errors, failed retrievals, and invalid outputs remain part of the audit trail.

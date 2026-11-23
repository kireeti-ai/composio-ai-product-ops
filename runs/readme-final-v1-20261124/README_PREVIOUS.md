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

## Run it

```bash
./reproduce.sh [out.html]          # offline: validate registry, 77 tests, re-consolidate evidence, rebuild report from runs/dataset-live-v7-20261124_0010
.venv/bin/python src/composio_demo.py runs/composio-demo-<new-id>   # live Composio proof; needs COMPOSIO_API_KEY in .env; executes no paid tool
cd runs/evidence-capture-v1-20261123_2359 && python3 refetch.py batch1 batch2 batch3 batch4   # optional: re-fetch every quotation (network, free)
open runs/human-review-worksheet-v1-20261124/HUMAN_REVIEW_INTERFACE.html   # human review UI; export CSV -> save as human_review_completed.csv in that folder, then rebuild the report
```

## Composio demonstration (what actually happened)

`runs/composio-demo-v3-20261124_0045/DEMO_RESULT.json`: the installed SDK is composio 0.27.0; constructing `Composio(api_key=...)` with the stored `ck_` Connect consumer key is rejected with HTTP 401 (it is not an SDK project key). Through Composio Connect MCP, tools/list (12 tools), COMPOSIO_SEARCH_TOOLS, COMPOSIO_GET_TOOL_SCHEMAS and one remote-sandbox command succeeded. Executing `GITHUB_LIST_ORGANIZATION_REPOSITORIES` failed: no active GitHub connection (needs an interactive OAuth approval by the account owner via `COMPOSIO_MANAGE_CONNECTIONS`, not initiated). The only active toolkit (GetAnyAPI) does not expose the contract tool and its data tools are paid, so none was run. 0 app-toolkit calls succeeded. To finish: create an SDK project key (`ak_...`) or approve a GitHub connection, then re-run the demo script.

## Human verification

`runs/human-review-worksheet-v1-20261124/` holds a 30-claim stratified sample (seeded; strata sizes in the CSV) with blank human fields. Nothing has been labelled; the report shows 0 of 30 until you export a completed CSV.

## Update (2026-11-24 checkpoint)

- 46 positions without a historical extraction now have quote-level research: `runs/evidence-capture-v1-20261123_2359/` (batch1-4 captures with saved pages, independent re-fetch snapshots, claim-support audits, `CONSOLIDATED.json`, `RECONCILIATION.csv/.md`). The six Codex records (58, 59, 60, 68, 78, 80) were re-validated in `runs/codex-evidence-validation-v1-20261123_2359/` (23 of 28 quotes accepted, 5 kept unresolved).
- 332 new claims: 112 supported by an official quotation, 118 partly supported, 17 researcher judgements, 4 conflicting, 12 unresolved, 69 unknown/not verified. 411 of 424 quotations reproduced on re-fetch.
- The 229 flagged historical claims were reviewed by model reviewers (137 supported, 51 partial, 27 unsupported, 12 conflicting, 2 unverifiable): `runs/claim-review-v1-20261123_2359/`.
- `runs/dataset-live-v7-20261124_0010/DATASET.json` = v5 plus additive `manual_research` and `claim_review` fields; `report/index.html` was rebuilt from it (`python3 -I src/build_report.py runs/dataset-live-v7-20261124_0010/DATASET.json report/index.html`). ◆ rows in the matrix are the newly researched positions. Earlier versions are kept beside the dataset. Browser interaction results: `UI_TEST_RESULT.txt` there.
- Identity labels for positions previously "identity review blocked/pending" display as resolved to the registry hint (authoritative export); the original statuses remain in the dataset.
- All verdicts are model-made. No human labelling, so no accuracy figure exists. Still open: human labelling, Composio SDK demonstration, Groq quota, deployment (needs approval).

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

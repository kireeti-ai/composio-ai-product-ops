# Composio AI Product Ops take-home: 100-app integration-readiness research

Live case study: https://kireeti-ai.github.io/composio-ai-product-ops-research/ (static copy of `report/index.html`, served from the `gh-pages` branch). Source: https://github.com/kireeti-ai/composio-ai-product-ops-research. Self-contained case study file: [`report/index.html`](report/index.html) (open it in a browser; no server needed). Rebuilt from the saved audit data, never hand-edited.

## Status (read before relying on any number)

Headline findings are computed over all 100 positions (54 first-pass extractions + 46 source-quoted records, normalised to the same enums by `src/normalize_profiles.py`), each with its denominator. First-pass claims that model review found unsupported or conflicting are excluded from the findings.


| Tier | State |
|---|---|
| Registry | 100 apps, matched to the supplied Notion export (`data/apps.json`, lock record in `runs/registry-lock-v1-20261123_2110/`) |
| First-pass extractions | 54 of 100 positions (model-extracted, lexically quote-checked; a quote match is not factual verification) |
| Newly researched | 46 of 100 positions: 332 claims, 424 distinct quotations, 411 re-fetched successfully (`runs/evidence-capture-v1-20261123_2359/`) |
| Model review | 229 flagged first-pass claims and all new claims reviewed by model reviewers. **Not human verification.** |
| Human verification | 30-claim worksheet prepared, **0 labelled** (`runs/human-review-worksheet-v1-20261124/`). No accuracy figure is claimed. |
| Composio | Connect MCP infrastructure calls work (4 of 4); 1 real application-toolkit operation succeeded (GitHub, read-only); the SDK client is not authenticated (see below) |

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install composio httpx   # SDK 0.27.0 was used; other steps need only the Python 3 standard library
./reproduce.sh [out.html]       # offline: validate registry, run all tests, check evidence re-consolidation, rebuild the report
python3 -I src/build_report.py runs/dataset-live-v8-20261124_0330/DATASET.json report/index.html   # rebuild the report only
```

Credentials live in a local `.env` (git-ignored; never commit it). Variables: `COMPOSIO_API_KEY` (Composio Connect key), optional `COMPOSIO_SDK_API_KEY` (SDK project key) and `COMPOSIO_USER_ID`. Groq extraction is paused; nothing here needs it.

### Run the research agent (stages)

Each stage writes to a new `runs/<id>/` folder; credentials come from `.env`.

```bash
python3 src/retrieve_wave.py runs/<new_dir> 15,24,31        # 1. retrieve official sources via Composio MCP (free, no model call)
python3 src/run_p1.py --run <run_id>                         # 2. extract with the frozen prompt/schema; needs runs/<run_id>/APPROVED.json (per-model request cap); stops at the first quota error
python3 src/verify_v2.py --out runs/<run>/verify --records "<glob>"   # 3. independent-model verification (needs APPROVED_PASS2.json)
python3 src/assemble_dataset.py <out_dir> label=<run_dir> ...         # 4. assemble the 100-position dataset
python3 -I src/build_report.py <DATASET.json> report/index.html       # 5. build the page
```
Stage 2 is currently blocked by exhausted provider quota; this repository's 46 newly researched positions were done by quote-level capture and model review instead (see `runs/evidence-capture-v1-20261123_2359/`). A new-run guide for that path: capture pages, save them, quote verbatim, re-fetch with `refetch.py`, then `consolidate.py`.

### Composio demonstration

```bash
.venv/bin/python src/composio_demo.py runs/composio-demo-<new-id>
```
Steps are recorded honestly in `DEMO_RESULT.json`, labelled `mcp_infrastructure`, `sdk` or `app_toolkit`. Latest: `runs/composio-demo-v6-20261124_0130/` (installed SDK composio 0.27.0). Earlier runs (v1-v5) are kept, including the failed attempts made before a GitHub connection existed.
Results in v6: the SDK client is still rejected with 401 for the stored `ck_` Connect key (an SDK project key is needed, so SDK step S8 is skipped); 4 of 4 MCP infrastructure calls succeeded (tool list, search, schema retrieval, one sandbox command); 1 of 2 attempted application operations succeeded: `GITHUB_LIST_ORGANIZATION_REPOSITORIES` for the public `ComposioHQ` org returned real repositories (e.g. `ComposioHQ/pidge`) through a GitHub connection the account owner approved; the GetAnyAPI contract tool is not exposed on the instant account, and that account's data tools are paid, so none was run.
To reproduce the GitHub call you need your own approved GitHub connection (`COMPOSIO_MANAGE_CONNECTIONS` with `toolkits=["github"]` returns an OAuth link). To also exercise the SDK, put an SDK project key in `COMPOSIO_SDK_API_KEY` and a connected `COMPOSIO_USER_ID` in `.env`; S8 then calls `tools.execute(...)`.

### Human labels

Open `runs/human-review-worksheet-v1-20261124/HUMAN_REVIEW_INTERFACE.html`, label the 30 claims, click Export CSV, then:
```bash
python3 src/import_human_labels.py ~/Downloads/human_review_completed.csv
python3 -I src/build_report.py runs/dataset-live-v8-20261124_0330/DATASET.json report/index.html
```
The importer validates ids and verdicts and never overwrites earlier labels. Agreement in the report is computed only from imported labels, on model verdicts that have a comparable five-way equivalent, and is shown with its denominator.

## Layout

| Path | Contents |
|---|---|
| `data/apps.json` | source-derived 100-position registry |
| `src/` | retrieval, assembly, validation, report generation, Composio demo, label importer |
| `baseline/` | frozen historical baseline with checksums (read-only) |
| `runs/` | versioned run records: retrievals, extractions, audits, evidence capture, model reviews, datasets, demos, snapshots. Corrections go in new run folders; history is not rewritten |
| `runs/snapshot-final-v1-20261124_0100/` | read-only copies and SHA-256 manifests of the final deliverables at hand-off |
| `tests/` | 79 offline tests (`python3 -I -m unittest discover -s tests -p 'test*.py'`) |
| `report/index.html` | the case study |

## Evidence rules

Unknown, not found in reviewed evidence, unsupported, and contradicted are different states. Absence of evidence is not evidence of absence. Reproducing a quotation shows the text is still on the page, not that the claim is true. Saved page snapshots from the quote re-fetch are not published (size, and a few embed third-party public keys); `REFETCH.json` keeps their hashes.

## Known limits

No human verification yet; model verdicts are judgements; some vendor pages were not fetchable by automated tools (Otter, PitchBook, part of Consensus and Grain); Datadog's MCP page differs from the saved copy; vendor pages change over time.

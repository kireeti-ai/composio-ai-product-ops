# Composio AI Product Ops: 100-app integration research

This repository supports the report in [`report/index.html`](report/index.html). **Open the report first**: it is one self-contained file (no external scripts, fonts or images) with the findings, a searchable 100-app matrix with claim-level evidence, the engine, the verification and the proof. This README only explains how to reproduce it.

## What this is

For 100 applications: how developers authenticate, whether API access is self-serve or gated, API surface, whether an MCP server exists, and whether a Composio toolkit is buildable. Every non-unknown claim carries a source URL and a verbatim quotation; failures and gaps are kept in the audit trail, not hidden.

## Honest status

- **No accuracy is claimed.** There are 0 independent human labels. "Quote-supported" is a lexical check: a verbatim, contiguous quote exists in the cited page and mentions the item's terms. It is not proof the claim is true. `none_found` means "not found in the provided evidence", never "does not exist".
- Apps **1–50** come from the original list. Apps **51–100** are a **reconstructed candidate list from a secondary source**; membership, categories and order are unverified.
- Some positions have no extraction (identity blocked, held, excluded, retrieval gap, or extraction failure). They are listed with reasons in the report.
- The Composio **SDK was not demonstrated**; retrieval used the Composio Connect MCP endpoint (TinyFish search/fetch, zero charge asserted on every call).

## Layout

| Path | Contents |
|---|---|
| `baseline/` | Frozen V1 baseline (read-only, `SHA256SUMS.txt`) |
| `data/apps.json` | 100-position registry (id, category, name, hint, source) |
| `src/` | Pipeline code: `retrieve_wave.py`, `assemble_dataset.py`, `build_report.py`, `report_template.html`, earlier stages |
| `runs/` | Every run in its own versioned directory; nothing is overwritten (frozen plan `p1-v1f-*`, benchmarks `bench5-*`, `correction5-*`, `p1-batchA/B-*`, retrieval waves, dataset) |
| `tests/` | Offline tests (mocked providers; no network, no quota) |
| `report/index.html` | The final report |

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate
pip install httpx pydantic            # only third-party dependencies used by the pipeline
# offline regression tests (no network)
python tests/test_eval_score.py
python runs/bench5-v2-*/test_bench2.py
python runs/pilot5-v7-*/test_pilot5_v7.py
# rebuild the dataset and the report from the preserved runs (no network)
python src/assemble_dataset.py runs/dataset-final <run specs, see runs/dataset-final/BUILD_COMMAND.txt>
python src/build_report.py runs/dataset-final/DATASET.json report/index.html
```

New extraction or retrieval needs your own keys in a local `.env` (never committed): `COMPOSIO_API_KEY` (retrieval), `GROQ_API_KEY`, `GEMINI_API_KEY`. Free tiers only; the code stops at the first daily-quota error and never rotates keys or accounts.

## Integrity rules followed

- Frozen prompt/schema/baseline/runner v6 are never modified; corrections go to new versioned runs (hashes are listed in the report).
- Single-writer lock, atomic read-only checkpoints, hash-chained request log, per-provider quota tracking with a rolling token window, circuit breaker.
- Unknown, not-found and false are kept distinct; absence of evidence is never converted into evidence of absence.
- Human-evaluation sheets (`runs/human-eval-*`) are blind and empty until independent reviewers fill them.

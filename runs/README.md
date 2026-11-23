# runs/ - audit trail

One folder per run; nothing is overwritten, corrections go in new folders. Start with the groups marked **report inputs**.

| Group | Folders | What it is |
|---|---|---|
| **Report inputs** | `dataset-live-v8-*`, `evidence-capture-v1-*`, `claim-review-v1-*`, `human-review-worksheet-v1-*`, `composio-demo-v6-*`, `registry-lock-v1-*`, `correction5-v1-*` | The data the page is built from |
| Evidence checks | `codex-evidence-validation-*`, `manual-research-*` (earlier search-summary passes), `claim-audit-*`, `completion-audit-*`, `audit-raw-*` | Quote and claim audits behind the verdicts |
| First-pass extraction | `p1-*`, `bench5-*`, `pilot5-*`, `topup-*`, `retrieval-wave-*`, `official-hint-topup-*` | Retrieval and model extraction runs (provider quota is now exhausted) |
| Planning and gates | `readiness-*`, `quota-*`, `eligibility-*`, `execution-ledger-*`, `pass2-pilot-plan-*`, `human-eval-*`, `master-coverage-*` | Go/no-go checks, quota ledgers and evaluation protocols |
| Earlier dataset builds | `dataset-live-v1` ... `v7` | Superseded builds, kept for the trail |
| Composio demo history | `composio-demo-v1` ... `v5` | Earlier attempts, including the failed ones |
| Other | `security-audit-*`, `RUNS_SHA256SUMS_*` | Secret scan notes and checksum manifests |

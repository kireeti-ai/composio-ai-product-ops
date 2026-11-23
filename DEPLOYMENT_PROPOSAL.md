# Proposed deployment (NOT executed; needs approval)

1. **Repository** - new standalone public GitHub repo (name proposal: `composio-ai-product-ops-research`) created from this folder only (not the parent `notes` repo): 1,212 files, about 43.5 MB after `.gitignore` (excludes `.env`, `.venv/`, `work/`, re-fetch page snapshots, 9 files embedding third-party public keys). Last secret scan: 0 hits (exact `.env` values and common key patterns).
2. **Live case study** - the single static file `report/index.html` (630 KB, no external requests) on a free static host (Vercel hobby project, or GitHub Pages from the repo). No server code, no environment variables, no paid tier.
3. **Before publishing** - decide: include the Notion export ZIP (15 KB; needed by `test_authoritative_registry_export.py`), and whether to import human labels / a successful Composio operation first (the report currently states 0 human labels and 0 application-toolkit successes).
4. **Rollback** - repo and project can be deleted; nothing else is touched.

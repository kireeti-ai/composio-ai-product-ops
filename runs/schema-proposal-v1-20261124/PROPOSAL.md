# PROPOSAL (not applied): nested per-surface extraction schema
Status: proposal only. The frozen extraction prompt (sha256 13eaee38702b…) and schema (sha256 c5082c7feb4a…) are unchanged and remain what any approved run uses. Neo4j (registry ID 66) stays HELD until you decide.

## Why
Some apps expose distinct API surfaces with different auth, access and API types (Neo4j: Aura Management API vs Database Query API). The frozen schema has one value per field, so a single extraction would blend them.

## Shape
App-level: `one_liner`. Then `surfaces[]`; each surface carries `surface_id`, `surface_name`, optional `surface_description`, and EVERY other frozen field unchanged (auth_methods, access, access_note, api_types, api_breadth, existing_mcp, buildability, blocker, evidence) - the definitions are copied programmatically from the frozen schema, so enums are identical. A single-surface app is `surfaces:[{surface_id:"default", ...}]`: migration to and from the frozen shape is lossless (tested on all 26 baseline records).

## Two ways to use it (decision needed)
A. One extraction call returns all surfaces (needs a PROMPT addendum, below, and a source set covering every surface).
B. One call per surface with surface-labelled inputs (no schema change needed at all; app name passed as e.g. "Neo4j - Aura Management API"); results are merged into the nested record afterwards. Lower risk of blending, 2x model calls for Neo4j only.

## Prompt addendum (PROPOSED TEXT, not applied; only for option A)
"If the sources describe distinct API surfaces with different authentication, access or API types (for example a management API and a data or query API), return one entry in `surfaces` per surface and use only the sources that describe that surface. Otherwise return exactly one surface with surface_id 'default'. Never merge facts across surfaces."

## Consequences
- Verification (Pass 2): verify.py would check each surface's fields separately (the item list per surface), and report per surface.
- Analytics: report per app AND per surface; the 100-app denominator stays per app (surfaces are sub-rows).
- Composio coverage is an ANNOTATION per surface (not model output): Neo4j = Aura management covered, Cypher querying not demonstrated.
- Optional, separate from this decision: per-field evidence-state enums (explicit / inferred / partial / unknown). Not included in the schema files here.

## Files
nested_schema_gemini_dialect.json (usable as responseSchema), nested_schema_jsonschema.json, migration_test_results.json, examples/ (3 migrated COPIES of baseline records + a HAND-ASSESSED Neo4j two-surface example, not a model extraction).

"""PROPOSAL ONLY (not applied): nested per-surface extraction schema derived from the FROZEN schema, a validator, a lossless migration (+ reverse) and tests on the 26 existing baseline Pass-1 records.
Reads baseline/ (never modifies it). Writes only runs/schema-proposal-v1-20261124/. Offline; no network; no LLM."""
import os, sys, json, copy, hashlib, importlib.util, time, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
OUT = "runs/schema-proposal-v1-20261124"; os.makedirs(f"{OUT}/examples", exist_ok=True)
spec = importlib.util.spec_from_file_location("run_p1", ROOT + "/src/run_p1.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
FROZEN, PROMPT, H_SCH, H_PR = R.frozen()                                    # hash-verified against baseline/MANIFEST.json
FIELDS = [k for k in FROZEN["properties"] if k != "one_liner"]              # per-surface fields = every frozen field except the app-level one_liner
SURFACE = {"type": "OBJECT", "required": ["surface_id", "surface_name"] + [k for k in FROZEN["required"] if k != "one_liner"],
           "properties": {"surface_id": {"type": "STRING"}, "surface_name": {"type": "STRING"}, "surface_description": {"type": "STRING"}, **{k: copy.deepcopy(FROZEN["properties"][k]) for k in FIELDS}}}
NESTED = {"type": "OBJECT", "required": ["one_liner", "surfaces"], "properties": {"one_liner": copy.deepcopy(FROZEN["properties"]["one_liner"]), "surfaces": {"type": "ARRAY", "items": SURFACE}}}
def jsonschema(s):
    if isinstance(s, dict): return {k: (v.lower() if k == "type" else jsonschema(v)) for k, v in s.items()}
    if isinstance(s, list): return [jsonschema(x) for x in s]
    return s
def validate(v, s, path="$"):
    errs = []; t = s["type"]
    if t == "OBJECT":
        if not isinstance(v, dict): return [f"{path}: not an object"]
        errs += [f"{path}.{k}: required field missing" for k in s.get("required", []) if k not in v]
        for k, sub in s.get("properties", {}).items():
            if k in v: errs += validate(v[k], sub, f"{path}.{k}")
    elif t == "ARRAY":
        if not isinstance(v, list): return [f"{path}: not an array"]
        for i, x in enumerate(v): errs += validate(x, s["items"], f"{path}[{i}]")
    elif t == "STRING":
        if not isinstance(v, str): return [f"{path}: not a string"]
        if "enum" in s and v not in s["enum"]: errs.append(f"{path}: '{v}' not in enum")
    return errs
EXTRA_KEEP = ("id", "name", "category", "model", "pages_read", "meta")
def migrate(rec, surface_id="default"):
    s = {"surface_id": surface_id, "surface_name": rec["name"], **{k: copy.deepcopy(rec[k]) for k in FIELDS}}
    top = {k: copy.deepcopy(rec[k]) for k in EXTRA_KEEP if k in rec}
    unknown = {k: copy.deepcopy(v) for k, v in rec.items() if k not in FIELDS and k not in EXTRA_KEEP and k != "one_liner"}
    m = {**top, "one_liner": rec["one_liner"], "schema_version": "nested-v1-PROPOSAL", "surfaces": [s]}
    if unknown: m["_unmapped_original_keys"] = unknown
    m["migration"] = {"from": "frozen-single-surface", "from_schema_sha256": H_SCH, "reversible": True}; return m
def unmigrate(m):
    assert len(m["surfaces"]) == 1 and m["surfaces"][0]["surface_id"] == "default", "only single-surface 'default' records can be reversed losslessly"
    s = m["surfaces"][0]; rec = {k: copy.deepcopy(m[k]) for k in EXTRA_KEEP if k in m}; rec["one_liner"] = m["one_liner"]; rec.update({k: copy.deepcopy(s[k]) for k in FIELDS}); rec.update(copy.deepcopy(m.get("_unmapped_original_keys", {}))); return rec
# ---------------- tests on the 26 existing baseline records (read-only)
res = dict(frozen_schema_sha256=H_SCH, prompt_sha256_unchanged=H_PR); ok_rt = ok_fro = ok_nest = 0; fails = []
base = {}
for f in sorted(os.listdir("baseline/p1_v1/pass1"), key=lambda x: int(x[:-5])):
    rec = json.load(open(f"baseline/p1_v1/pass1/{f}")); base[rec["id"]] = rec; m = migrate(rec); back = unmigrate(m)
    e1 = validate(rec, FROZEN); e2 = validate(m, NESTED); rt = (back == rec)
    ok_fro += not e1; ok_nest += not e2; ok_rt += rt
    if e1 or e2 or not rt: fails.append(dict(id=rec["id"], frozen_errors=e1[:2], nested_errors=e2[:2], roundtrip=rt))
res.update(records_tested=len(base), valid_against_frozen=ok_fro, valid_against_nested_after_migration=ok_nest, lossless_roundtrip=ok_rt, failures=fails)
# negative tests: validator must reject bad records
bad = copy.deepcopy(migrate(base[4])); bad["surfaces"][0]["access"] = "totally_free_lunch"; del bad["surfaces"][0]["blocker"]; neg = validate(bad, NESTED)
res["negative_test_errors_detected"] = neg
# ---------------- examples (migrated COPIES; baseline untouched)
for i in (4, 22, 28):
    json.dump(migrate(base[i]), open(f"{OUT}/examples/migrated_baseline_record_{i}.json", "w"), indent=1)
nr = json.load(open("runs/topup-v1s-20261123/neo4j_record.json")); S = {s["surface"]: s for s in nr["surfaces"]}
ev = lambda s, fld: [dict(field=fld, url=e["url"], quote=e["quote"], quote_found=True, url_in_sources=True) for e in S[s]["evidence"][:1]]
neo = {"id": 66, "name": "Neo4j", "one_liner": "Graph database vendor whose product exposes (a) a REST API to manage Aura cloud instances and (b) an HTTPS Query API that executes Cypher against a database.", "schema_version": "nested-v1-PROPOSAL",
       "PROVENANCE": "HAND-ASSESSED from stored official pages - NOT a model extraction; illustrative only; Neo4j stays HELD and is not in the 28-app plan",
       "surfaces": [
        {"surface_id": "aura_management_api", "surface_name": "Aura Management API", "surface_description": "Manage Aura instances and projects", "auth_methods": ["unknown"], "access": "unknown", "access_note": "Needs an Aura account; free trial gives $150 credits; credential mechanism and tier availability not retrieved.",
         "api_types": ["rest"], "api_breadth": "unknown", "existing_mcp": "unknown", "buildability": "unknown", "blocker": "Authentication page not retrieved", "evidence": ev("aura_management_api", "api_types")},
        {"surface_id": "database_query_api", "surface_name": "Database Query API", "surface_description": "Execute Cypher over HTTPS against a database", "auth_methods": ["unknown"], "access": "unknown", "access_note": "Requires a reachable database; no developer registration; Aura availability and the Query API authorize page not retrieved.",
         "api_types": ["rest"], "api_breadth": "unknown", "existing_mcp": "unknown", "buildability": "unknown", "blocker": "Auth page and Aura availability not retrieved", "evidence": ev("database_query_api", "api_types")}],
       "annotations_not_model_output": {"composio_toolkit_coverage": {"aura_management_api": "covered (8 neo4j tools)", "database_query_api": "Cypher querying NOT demonstrated by the current Composio toolkit"}}}
res["neo4j_example_valid_against_nested"] = not validate(neo, NESTED); res["neo4j_example_errors"] = validate(neo, NESTED)
json.dump(neo, open(f"{OUT}/examples/neo4j_two_surface_example_HAND_ASSESSED.json", "w"), indent=1)
json.dump(NESTED, open(f"{OUT}/nested_schema_gemini_dialect.json", "w"), indent=1); json.dump(jsonschema(NESTED), open(f"{OUT}/nested_schema_jsonschema.json", "w"), indent=1)
json.dump(res, open(f"{OUT}/migration_test_results.json", "w"), indent=1)
open(f"{OUT}/PROPOSAL.md", "w").write(f"""# PROPOSAL (not applied): nested per-surface extraction schema
Status: proposal only. The frozen extraction prompt (sha256 {H_PR[:12]}…) and schema (sha256 {H_SCH[:12]}…) are unchanged and remain what any approved run uses. Neo4j (registry ID 66) stays HELD until you decide.

## Why
Some apps expose distinct API surfaces with different auth, access and API types (Neo4j: Aura Management API vs Database Query API). The frozen schema has one value per field, so a single extraction would blend them.

## Shape
App-level: `one_liner`. Then `surfaces[]`; each surface carries `surface_id`, `surface_name`, optional `surface_description`, and EVERY other frozen field unchanged (auth_methods, access, access_note, api_types, api_breadth, existing_mcp, buildability, blocker, evidence) - the definitions are copied programmatically from the frozen schema, so enums are identical. A single-surface app is `surfaces:[{{surface_id:"default", ...}}]`: migration to and from the frozen shape is lossless (tested on all 26 baseline records).

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
""")
for dp, dn, fn in os.walk(OUT):
    for f in fn: os.chmod(os.path.join(dp, f), 0o444)
print(json.dumps({k: res[k] for k in ("records_tested", "valid_against_frozen", "valid_against_nested_after_migration", "lossless_roundtrip", "failures", "neo4j_example_valid_against_nested")}, indent=1)); print("negative test (validator must catch):", neg)
print("per-surface fields copied from frozen:", FIELDS)

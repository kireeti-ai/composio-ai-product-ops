"""Build the single self-contained HTML report (report/index.html) from DATASET.json + preserved run artefacts. No network. Section order is fixed by the user: Findings -> Matrix -> Research Engine -> Verification -> Proof.
Usage: python src/build_report.py <DATASET.json> <out.html>"""
import os, sys, re, json, glob, csv, hashlib, time, collections, html
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
ds = json.load(open(sys.argv[1])); rows = ds["rows"]; OUT = sys.argv[2]; sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest(); esc = html.escape
NOW = time.strftime("%Y-%m-%d %H:%M IST")
def prim(r): return next((v for v in r["versions"] if v["version"] == r["primary_version"]), None)
STATE_LABEL = {"supported_lexical": "quote-supported (lexical)", "unsupported": "unsupported", "unknown": "unknown", "not_found_in_provided_evidence": "not found in provided evidence", "needs_human": "needs human"}
# ---------- compact per-app records for the matrix
apps = []
for r in rows:
    p = prim(r); f = p["fields"] if p else {}
    apps.append(dict(id=r["registry_id"], n=r["name"], c=r["category"], pr="O" if r["provenance_class"] == "original_notion" else "R", st=r["status"], ms=r["master_status"], statuses=[r[k] for k in ("identity_status", "retrieval_status", "extraction_status", "evidence_validation_status", "verification_status", "human_review_status")], pv=r["primary_version"] or "", md=(p["provider"] + " " + p["model"]) if p else "", auth=f.get("auth_methods"), acc=f.get("access"), api=f.get("api_types"), br=f.get("api_breadth"), mcp=f.get("existing_mcp"), bld=f.get("buildability"), blk=f.get("blocker", ""), one=f.get("one_liner", ""), note=f.get("access_note", ""),
                 cl=[[c["field"], c["item"], c["state"]] for c in p["claims"]] if p else [], ev=[[e["field"], e["url"], e["quote"], e["valid"], e["issues"]] for e in p["evidence"]] if p else [], ns=len(p["sources"]) if p else 0, nv=len(r["versions"]), cnt=p["claim_state_counts"] if p else {}, vers=[v["version"] for v in r["versions"]]))
ext = [a for a in apps if a["pv"]]; N = len(apps)
# ---------- aggregates (every number has a denominator)
st_counts = collections.Counter(a["ms"] if not a["pv"] else "EXTRACTED" for a in apps); ver_counts = collections.Counter(a["pv"] for a in ext)
claims = collections.Counter(c[2] for a in ext for c in a["cl"]); nclaims = sum(claims.values()); evs = [e for a in ext for e in a["ev"]]; evok = sum(e[3] for e in evs)
issues = collections.Counter(i for e in evs for i in e[4])
def dist(key, pool=None):
    pool = pool or ext; c = collections.Counter(); [c.update(a[key] if isinstance(a[key], list) else [a[key]]) for a in pool if a[key]]; return c
acc, mcp, bld, br = dist("acc"), dist("mcp"), dist("bld"), dist("br")
by_cat = collections.defaultdict(lambda: collections.Counter()); [by_cat[a["c"]].update([a["acc"]]) for a in ext if a["acc"]]
ev_claim = lambda a, f: [c for c in a["cl"] if c[0] == f]
easy = [a for a in ext if a["bld"] == "yes" and a["acc"] == "self_serve_free" and all(c[2] == "supported_lexical" for c in ev_claim(a, "access"))]
outreach = [a for a in ext if a["acc"] in ("approval_or_review_required", "partner_or_contact_sales")]
blocked = [a for a in apps if not a["pv"]]
# ---------- five-app correction comparison (preserved v1 vs corrected)
cmpf = sorted(glob.glob("runs/correction5-v1-*/reports/COMPARISON_V1_VS_CORRECTED.json"))[-1]; CMP = json.load(open(cmpf))["apps"]
# ---------- baseline Pass-2 (old verifier) summary
vc = collections.Counter(); vn = 0
for f in glob.glob("baseline/p1_v1/verify/*.json"):
    r = json.load(open(f)); vn += 1
    for fld, items in r["fields"].items():
        for it in items: vc[it["verdict"]] += 1
# ---------- Composio retrieval counts (records preserved in repo)
def fetched_counts():
    ok = bad = srch = 0
    for pat, key in (("runs/retrieval-wave-v*/raw/[0-9]*.json", "fetched"), ("runs/topup-v1*/raw/[0-9]*.json", "fetched"), ("runs/correction5-v1-*/raw/github_official_[0-9].json", None)):
        for f in glob.glob(pat):
            r = json.load(open(f))
            if key and not (isinstance(r, dict) and isinstance(r.get(key), list)): continue          # other record shapes (e.g. catalog files) are not page fetches
            if key: ok += sum(e["status"] == "ok" for e in r[key]); bad += sum(e["status"] != "ok" for e in r[key]); srch += len(r.get("searches", []))
            else: ok += r["status"] == "ok"; bad += r["status"] != "ok"
    return ok, bad, srch
fok, fbad, fsr = fetched_counts()
hashes = []
for label, p in (("Frozen v1f plan", "runs/p1-v1f-gemini-20261124/PLAN.json"), ("Frozen v1f FROZEN.json", "runs/p1-v1f-gemini-20261124/FROZEN.json"), ("Runner v6 (frozen)", "src/run_p1.py"), ("Baseline MANIFEST", "baseline/MANIFEST.json"), ("Baseline SHA256SUMS", "baseline/SHA256SUMS.txt"), ("Master coverage matrix", "runs/master-coverage-v1-20261124/MASTER_COVERAGE.csv"), ("Dataset assembler", "src/assemble_dataset.py"), ("Report builder", "src/build_report.py"), ("HTML template", "src/report_template.html"), ("Benchmark runner v1", glob.glob("runs/bench5-v1-*/bench.py")[0]), ("Benchmark runner v2", glob.glob("runs/bench5-v2-*/bench2.py")[0]), ("Dataset (this report)", sys.argv[1])):
    if os.path.exists(p): hashes.append((label, p, sha(p)))
for p in sorted(glob.glob("runs/p1-batch*-groq-*/BATCH_MANIFEST.json")): hashes.append(("Batch manifest", p, sha(p)))
hashes.append(("Frozen extraction prompt (sha256)", "baseline/MANIFEST.json", json.load(open("runs/p1-v1f-gemini-20261124/FROZEN.json"))["frozen_prompt_sha256"])); hashes.append(("Frozen extraction schema (sha256)", "baseline/MANIFEST.json", json.load(open("runs/p1-v1f-gemini-20261124/FROZEN.json"))["frozen_schema_sha256"]))
def pct(a, b): return f"{a}/{b}" + (f" ({100 * a / b:.0f}%)" if b else "")
def table(counter, denom, label):
    return "<table class=mini><tr><th>" + label + "</th><th>count</th><th>of " + str(denom) + "</th></tr>" + "".join(f"<tr><td>{esc(str(k))}</td><td>{v}</td><td>{100 * v / denom:.0f}%</td></tr>" for k, v in counter.most_common()) + "</table>"
DATA = json.dumps(apps, separators=(",", ":")).replace("</", "<\\/")
T = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_template.html")).read()
mapping = dict(NOW=NOW, N=N, NEXT=len(ext), DATA=DATA, STATUS=json.dumps(dict(st_counts)), VER=json.dumps(dict(ver_counts)),
    METRICS=json.dumps(dict(positions=N, extracted=len(ext), claims=nclaims, claim_states=dict(claims), evidence=len(evs), evidence_valid=evok, issues=dict(issues), acc=dict(acc), mcp=dict(mcp), bld=dict(bld), br=dict(br), by_cat={k: dict(v) for k, v in by_cat.items()}, easy=[[a["id"], a["n"]] for a in easy], outreach=[[a["id"], a["n"], a["acc"]] for a in outreach], blocked=[[a["id"], a["n"], a["st"] if a["st"] != a["ms"] else a["ms"]] for a in blocked])),
    CMP=json.dumps(CMP), P2=json.dumps(dict(n=vn, verdicts=dict(vc))), RETR=json.dumps(dict(ok=fok, bad=fbad, searches=fsr)), HASHES=json.dumps(hashes))
for k, v in mapping.items(): T = T.replace("{{" + k + "}}", str(v))
open(OUT, "w").write(T); print("report written", OUT, os.path.getsize(OUT) // 1024, "KB; extracted", len(ext), "of", N)

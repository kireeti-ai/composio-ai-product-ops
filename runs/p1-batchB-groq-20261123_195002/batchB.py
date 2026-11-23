"""Batch B: expansion apps (waves 3A/3B/4) with freshly retrieved official-domain evidence. Identity gate first (offline), then bundles (reduction-v2), then Groq extraction (same runner as Batch A). Frozen prompt/schema untouched.
Usage: python batchB.py gate | build | run"""
import os, sys, re, json, glob, importlib.util
from urllib.parse import urlparse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT); sys.path.insert(0, f"{ROOT}/src")
spec = importlib.util.spec_from_file_location("bench2", f"{ROOT}/runs/bench5-v2-20261123_192201/bench2.py"); X = importlib.util.module_from_spec(spec); sys.modules["bench2"] = X; spec.loader.exec_module(X); B = X.B
iso, sha, atomic = B.iso, B.sha, B.atomic; W1 = open("/tmp/wave_dir").read().strip(); W2 = open("/tmp/wave2_dir").read().strip(); MAX_OUT = 1500; TPM_CAP = 7200; BUDGETS = (12000, 9000, 7000, 5000)
D = json.load(open("data/apps.json")); REG = {a[0]: a for a in D["apps"]}; PLAN = json.load(open("runs/p1-expansion-v1-20261124/PLAN.json")); WAVE_IDS = [i for w, v in PLAN["waves"].items() if not w.startswith("3H") for i in v]
reg = lambda h: ".".join((h or "").lower().split(".")[-2:])
def label(d): return re.sub(r"[^a-z0-9]", "", d.split(".")[0])
def gate():
    out = []
    for i in WAVE_IDS:
        nm = REG[i][2]; norm = re.sub(r"[^a-z0-9]", "", nm.lower().split("(")[0]); src = W2 if os.path.exists(f"{W2}/raw/{i}.json") else W1; r = json.load(open(f"{src}/raw/{i}.json")); pages = [e for e in r["fetched"] if e["status"] == "ok" and e.get("chars", 0) >= 300]
        if i <= 50: doms = sorted({reg(urlparse(e["url"]).hostname) for e in pages}); tier = "A_hint_resolved_original_list" if len(pages) >= 3 else "D_retrieval_gap"; why = f"official hint domain from original list: {REG[i][3]}"
        else:
            cand = {reg(urlparse(h["url"]).hostname) for h in r["candidate_hits"]}; exact = sorted(d for d in cand if label(d) in (norm, norm + "hq", norm + "app", norm + "ai") and len(norm) >= 4)
            if not exact: tier, doms, why = "C_identity_review", [], "no candidate domain whose label equals the app name"
            elif len({label(d) for d in exact}) == 1 and len(exact) == 1: tier, doms, why = "B_name_resolved_candidate", exact, "exactly one domain label equals the app name (reconstructed-list app: identity NOT confirmed by the original list)"
            elif len({label(d) for d in exact}) == 1:
                cnt = sorted(((sum(reg(urlparse(h["url"]).hostname) == d for h in r["candidate_hits"]), d) for d in exact), reverse=True)
                if cnt[0][0] >= 3 * max(1, cnt[1][0]): tier, doms, why = "B_name_resolved_candidate_dominant_tld", [cnt[0][1]], f"same label on several TLDs; {cnt[0][1]} has {cnt[0][0]} search hits vs {cnt[1][0]} for the next (only the dominant domain accepted; flagged for review)"
                else: tier, doms, why = "C_identity_review", exact, f"same label on several TLDs with no dominant one ({cnt}); different companies may share a label"
            else: tier, doms, why = "C_identity_review", exact, "several differently-labelled domains match; identity ambiguous"
            pages = [e for e in pages if reg(urlparse(e["url"]).hostname) in doms]
            if tier.startswith("B") and len(pages) < 3: tier = "D_retrieval_gap"
        out.append(dict(id=i, name=nm, tier=tier, accepted_domains=doms, pages_usable=len(pages), why=why, source_run=src, provenance="original_notion" if i <= 50 else "reconstructed_candidate_UNVERIFIED"))
    atomic(f"{HERE}/IDENTITY_GATE.json", out); import collections; print(collections.Counter(o["tier"] for o in out)); [print(o["id"], o["name"], o["tier"], o["accepted_domains"], o["pages_usable"]) for o in out if not o["tier"].startswith(("A", "B"))]
def build():
    v7, v6, schema, prompt, h_sch, h_pr, _ = B.load_frozen(); os.chdir(ROOT); G = json.load(open(f"{HERE}/IDENTITY_GATE.json")); man = []; Dd = D
    for g in G:
        i = g["id"]
        if not g["tier"].startswith(("A", "B")): man.append(dict(id=i, name=g["name"], status="BLOCKED_" + g["tier"])); continue
        r = json.load(open(f"{g['source_run']}/raw/{i}.json")); doms = set(g["accepted_domains"]); pages = []; seen = set()
        if os.path.exists(f"baseline/p1_v1/raw/{i}.json"):
            for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]:
                if p["url"] not in seen and len(p["text"]) >= 300: seen.add(p["url"]); pages.append(dict(url=p["url"], text=p["text"], origin="baseline_cached"))
        for e in r["fetched"]:
            if e["status"] == "ok" and e.get("chars", 0) >= 300 and (g["id"] <= 50 or reg(urlparse(e["url"]).hostname) in doms):
                key = e["sha256"]
                if e["url"] not in seen and key not in seen: seen.add(e["url"]); seen.add(key); pages.append(dict(url=e["url"], text=e["text"][:30000], origin=f"retrieved {e.get('retrieved_at')} sha256={e['sha256'][:16]}"))
        a = REG[i]; chosen = None
        for bud in BUDGETS:
            red = X.reduce_pages_v2(pages, bud, win_budget=3000); rp = prompt.format(name=a[2], cat=Dd["categories"][a[1] - 1], hint=a[3] or "none", src="\n\n".join(f"### {p['url']}\n{p['text']}" for p in red))
            if B.est_tokens(len(rp)) + MAX_OUT <= TPM_CAP: chosen = (bud, red, rp); break
        if not chosen: man.append(dict(id=i, name=a[2], status="TOO_LARGE_FOR_GROQ_TPM")); continue
        bud, red, rp = chosen
        atomic(f"{HERE}/bundles_full/{i}.json", dict(id=i, name=a[2], pages=pages, identity=g)); atomic(f"{HERE}/bundles/{i}.json", dict(id=i, name=a[2], reduction="reduction-v2", budget_chars=bud, pages=red, prompt=rp, prompt_sha256=sha(rp), est_tokens=B.est_tokens(len(rp)), identity=g))
        man.append(dict(id=i, name=a[2], status="READY", tier=g["tier"], budget_chars=bud, est_tokens=B.est_tokens(len(rp)), pages_full=len(pages), pages_shown=len(red)))
    atomic(f"{HERE}/BATCH_MANIFEST.json", dict(created=iso(), prompt_sha256=h_pr, schema_sha256=h_sch, apps=man)); print([(m["id"], m["name"], m["status"], m.get("est_tokens")) for m in man])
def run():
    v7, v6, schema, prompt, h_sch, h_pr, _ = B.load_frozen(); os.chdir(ROOT); M = json.load(open(f"{HERE}/BATCH_MANIFEST.json")); ready = [m["id"] for m in M["apps"] if m["status"] == "READY"]; P, SH, FU = {}, {}, {}
    for i in ready: b = json.load(open(f"{HERE}/bundles/{i}.json")); P[i], SH[i] = b["prompt"], b["pages"]; FU[i] = json.load(open(f"{HERE}/bundles_full/{i}.json"))["pages"]
    lim = {c["bucket"]: dict(c["limits"], **({"tpd": 200000} if t == "groq_orgA" else {})) for t, c in X.PROVIDERS.items()}; quota = X.Quota2(f"{HERE}/quota.json", lim); breaker = X.Breaker(f"{HERE}/breaker.json"); log = X.Log(f"{HERE}/logs/requests.jsonl")
    cfg = dict(X.PROVIDERS["groq_orgA"], cap=len(ready) + 6, max_out=MAX_OUT)
    try: print("RESULT", X.run_provider2("groq_orgA", cfg, [(i, REG[i][2]) for i in ready], P, SH, FU, schema, B.adapter_call, quota, breaker, HERE, log, key=X.secret("GROQ_API_KEY")))
    except B.StopAll as e: print("STOP_ALL", e)
if __name__ == "__main__": {"gate": gate, "build": build, "run": run}[sys.argv[1]]()

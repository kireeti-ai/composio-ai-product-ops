"""Batch A: the 28 frozen v1f targets, Groq existing key (gpt-oss-120b), reduction-v2, evidence validation v2, per-app checkpoints. Frozen prompt/schema/plan untouched (read-only). Resumable: completed apps are skipped.
Usage: python batchA.py build | run | summary"""
import os, sys, json, re, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT); sys.path.insert(0, f"{ROOT}/src")
spec = importlib.util.spec_from_file_location("bench2", f"{ROOT}/runs/bench5-v2-20261123_192201/bench2.py"); X = importlib.util.module_from_spec(spec); sys.modules["bench2"] = X; spec.loader.exec_module(X); B = X.B
iso, sha, atomic = B.iso, B.sha, B.atomic; ALREADY_CORRECTED = {27, 32, 41, 53, 61}      # re-extracted in runs/correction5-v1-* with corrected bundles; not rerun here
MAX_OUT = 1500; TPM_CAP = int(8000 * 0.9); BUDGETS = (12000, 9000, 7000, 5000)
def load():
    v7, v6, schema, prompt, h_sch, h_pr, _ = B.load_frozen(); os.chdir(ROOT); plan = json.load(open("runs/p1-v1f-gemini-20261124/PLAN.json")); Dd = json.load(open("baseline/data/apps.json")); reg = {a[0]: a for a in Dd["apps"]}
    return v7, v6, schema, prompt, h_sch, h_pr, plan, Dd, reg
def build():
    v7, v6, schema, prompt, h_sch, h_pr, plan, Dd, reg = load(); ids = [i for v in plan["phases"].values() for i in v]; assert len(ids) == len(set(ids)) == 28; man = []
    for i in ids:
        a = reg[i]; full_prompt, pages, top = v7.build_prompt(v6, None, dict(id=i, name=a[2]), prompt, plan); chosen = None
        for bud in BUDGETS:
            red = X.reduce_pages_v2(pages, bud); src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in red); rp = prompt.format(name=a[2], cat=Dd["categories"][a[1] - 1], hint=a[3] or "none", src=src)
            if B.est_tokens(len(rp)) + MAX_OUT <= TPM_CAP: chosen = (bud, red, rp); break
        prov = plan["provenance"].get(str(i)) or {}
        if not chosen: man.append(dict(id=i, name=a[2], status="TOO_LARGE_FOR_GROQ_TPM")); continue
        bud, red, rp = chosen
        atomic(f"{HERE}/bundles_full/{i}.json", dict(id=i, name=a[2], pages=pages, topup_sources=top, provenance=prov, tier=plan["tiers"].get(str(i)), uncertainty=plan["uncertainty"].get(str(i)), api_surface_state=plan["api_surface"].get(str(i))))
        atomic(f"{HERE}/bundles/{i}.json", dict(id=i, name=a[2], reduction="reduction-v2", budget_chars=bud, pages=red, prompt=rp, prompt_sha256=sha(rp), est_tokens=B.est_tokens(len(rp)), full_prompt_est_tokens=B.est_tokens(len(full_prompt)), provenance=prov))
        man.append(dict(id=i, name=a[2], status="READY", budget_chars=bud, est_tokens=B.est_tokens(len(rp)), full_est_tokens=B.est_tokens(len(full_prompt)), pages_full=len(pages), pages_shown=len(red), prompt_sha256=sha(rp), provenance_class="original_notion" if i <= 50 else "reconstructed_unverified"))
    atomic(f"{HERE}/BATCH_MANIFEST.json", dict(created=iso(), prompt_sha256=h_pr, schema_sha256=h_sch, frozen_plan="runs/p1-v1f-gemini-20261124/PLAN.json", provider="groq existing key (P1 same org), openai/gpt-oss-120b", max_out=MAX_OUT, reduction="reduction-v2 (budget stepped down 12000/9000/7000/5000 chars only if the prompt would not fit the 8k TPM budget)", apps=man))
    print([(m["id"], m["name"], m["status"], m.get("budget_chars"), m.get("est_tokens")) for m in man])
def run():
    v7, v6, schema, prompt, h_sch, h_pr, plan, Dd, reg = load(); ids = [i for v in plan["phases"].values() for i in v]; ready = [i for i in ids if os.path.exists(f"{HERE}/bundles/{i}.json") and i not in ALREADY_CORRECTED]; P, SH, FU = {}, {}, {}
    for i in ready: b = json.load(open(f"{HERE}/bundles/{i}.json")); P[i], SH[i] = b["prompt"], b["pages"]; FU[i] = json.load(open(f"{HERE}/bundles_full/{i}.json"))["pages"]
    lim = {c["bucket"]: dict(c["limits"], **({"tpd": 200000} if t == "groq_orgA" else {})) for t, c in X.PROVIDERS.items()}; quota = X.Quota2(f"{HERE}/quota.json", lim); breaker = X.Breaker(f"{HERE}/breaker.json"); log = X.Log(f"{HERE}/logs/requests.jsonl")
    cfg = dict(X.PROVIDERS["groq_orgA"], cap=len(ready) + 6, max_out=MAX_OUT)       # cap = apps + 6 retries for the whole batch (hard)
    try: print("RESULT", X.run_provider2("groq_orgA", cfg, [(i, reg[i][2]) for i in ready], P, SH, FU, schema, B.adapter_call, quota, breaker, HERE, log, key=X.secret("GROQ_API_KEY")))
    except B.StopAll as e: print("STOP_ALL", e)
if __name__ == "__main__": {"build": build, "run": run}[sys.argv[1]]()

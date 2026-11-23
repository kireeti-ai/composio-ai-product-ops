"""Five-app correction run (versioned; v1/v2 benchmark outputs untouched). Stages: retrieve (free Composio TinyFish only, instant_charge asserted 0) | build (reduction-v2 bundles) | run (Groq existing key, via bench2.run_provider2) | compare.
Lexical quote validation is NOT proof of claim correctness."""
import os, sys, re, json, time, hashlib, datetime, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT); sys.path.insert(0, f"{ROOT}/src")
spec = importlib.util.spec_from_file_location("bench2", f"{ROOT}/runs/bench5-v2-20261123_192201/bench2.py"); X = importlib.util.module_from_spec(spec); sys.modules["bench2"] = X; spec.loader.exec_module(X); B = X.B
iso = B.iso; sha = B.sha; atomic = B.atomic; APPS = B.APPS; V1 = X.V1DIR
GH_URLS = ["https://github.com/github/github-mcp-server", "https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api", "https://docs.github.com/en/get-started/learning-about-github/githubs-plans", "https://docs.github.com/en/copilot/concepts/context/mcp", "https://raw.githubusercontent.com/github/github-mcp-server/main/README.md"]
OFFICIAL_HOSTS = {"github.com", "docs.github.com", "raw.githubusercontent.com"}      # github.com/github/* is GitHub's own organization repo
STALE = re.compile(r"/enterprise/\d+\.\d+")                # versioned GitHub Enterprise Server docs: excluded from the GitHub bundle (documented)
def retrieve():
    from mcp import MCP
    for l in open(".env"):
        if l.startswith("COMPOSIO_API_KEY="): os.environ["COMPOSIO_API_KEY"] = l.strip().split("=", 1)[1]
    m = MCP(); r = m.call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "fetch a URL and return its page text"}], "session": {"generate_id": True}}); sid = json.loads(r["content"][0]["text"])["data"]["session"]["id"]; out = []
    for n0, url in enumerate(GH_URLS, 1):
        pf = f"{HERE}/raw/github_official_{n0}.json"
        if os.path.exists(pf) and json.load(open(pf))["status"] == "ok": out.append(json.load(open(pf))); continue
        if os.path.exists(pf): os.replace(pf, pf.replace(".json", f"_failed_attempt_{int(time.time())}.json"))      # failed attempts are preserved, never overwritten
        e = dict(url=url, requested_at=iso())
        try:
            r = m.call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": "TINYFISH_FETCH_URLS", "arguments": {"urls": [url], "purpose": "official GitHub MCP / REST authentication / plans documentation"}}], "sync_response_to_workbench": False, "session_id": sid, "thought": "official docs for GitHub MCP and auth", "current_step": "FETCH", "current_step_metric": "1/4"})
            d = json.loads(r["content"][0]["text"]); ch = (d.get("data", {}).get("instant_charge") or d.get("instant_charge") or {}); assert float(ch.get("amount", 0) or 0) == 0, f"NONZERO CHARGE {ch}"; e["charge_usd"] = 0.0
            resp = d["data"]["results"][0]["response"]
            if not resp.get("successful"): e.update(status="error", error=str(resp)[:300])
            else:
                got = [x for x in resp["data"].get("results", []) if x.get("text")]
                if not got: e.update(status="empty", error=str(resp["data"].get("errors"))[:300])
                else: x = got[0]; t = x["text"]; e.update(status="ok", final_url=x.get("final_url"), title=x.get("title"), chars=len(t), sha256=sha(t), text=t[:60000])
        except AssertionError: raise
        except Exception as ex: e.update(status="error", error=f"{type(ex).__name__}: {str(ex)[:200]}")
        e["completed_at"] = iso(); out.append(e); atomic(pf, e); time.sleep(2)
    atomic(f"{HERE}/raw/github_official_ledger.json", [{k: v for k, v in e.items() if k != "text"} for e in out]); print([(e["url"][-45:], e["status"], e.get("chars")) for e in out])
def new_pages(i):
    full = json.load(open(f"{V1}/bundles_full/{i}.json"))["pages"]
    if i != 61: return full, []
    keep = [p for p in full if not STALE.search(p["url"])]; dropped = [p["url"] for p in full if STALE.search(p["url"])]; add = []
    for n in range(1, len(GH_URLS) + 1):
        if not os.path.exists(f"{HERE}/raw/github_official_{n}.json"): continue
        e = json.load(open(f"{HERE}/raw/github_official_{n}.json"))
        if e["status"] == "ok" and e["chars"] >= 500 and re.sub(r"^www\.", "", e["url"].split("/")[2]) in OFFICIAL_HOSTS: add.append(dict(url=e["url"], text=e["text"][:30000]))
    return keep + add, dict(dropped_stale_pages=dropped, added=[p["url"] for p in add])
def build():
    v7, v6, schema, prompt, h_sch, h_pr, _ = B.load_frozen(); os.chdir(ROOT); Dd = json.load(open("baseline/data/apps.json")); reg = {a[0]: a for a in Dd["apps"]}; man = []
    for i, name in APPS:
        pages, note = new_pages(i); red = X.reduce_pages_v2(pages); a = reg[i]; src = "\n\n".join(f"### {p['url']}\n{p['text']}" for p in red); rp = prompt.format(name=a[2], cat=Dd["categories"][a[1] - 1], hint=a[3] or "none", src=src)
        old = json.load(open(f"{V1}/bundles/{i}.json")); prov = old["provenance"]
        atomic(f"{HERE}/bundles_full/{i}.json", dict(app=name, id=i, pages=pages, change_note=note, provenance=prov)); atomic(f"{HERE}/bundles/{i}.json", dict(app=name, id=i, provenance=prov, provenance_class=old["provenance_class"], reduction="reduction-v2", pages=red, prompt=rp, prompt_sha256=sha(rp), est_tokens=B.est_tokens(len(rp)), change_note=note))
        man.append(dict(id=i, name=name, est_tokens=B.est_tokens(len(rp)), change=note or "reduction-v2 only", prompt_sha256=sha(rp)))
    atomic(f"{HERE}/BUNDLE_MANIFEST.json", dict(created=iso(), prompt_sha256=h_pr, schema_sha256=h_sch, apps=man)); print(json.dumps(man, indent=0)[:1500])
def run():
    v7, v6, schema, prompt, h_sch, h_pr, _ = B.load_frozen(); os.chdir(ROOT); P, SH, FU = {}, {}, {}
    for i, _ in APPS: b = json.load(open(f"{HERE}/bundles/{i}.json")); P[i], SH[i] = b["prompt"], b["pages"]; FU[i] = json.load(open(f"{HERE}/bundles_full/{i}.json"))["pages"]
    lim = {c["bucket"]: dict(c["limits"], **({"tpd": 200000} if t == "groq_orgA" else {})) for t, c in X.PROVIDERS.items()}; quota = X.Quota2(f"{HERE}/quota.json", lim); breaker = X.Breaker(f"{HERE}/breaker.json"); log = X.Log(f"{HERE}/logs/requests.jsonl")
    cfg = dict(X.PROVIDERS["groq_orgA"], cap=5, max_out=1500)      # v1 actual outputs were 567-915 tokens; 1500 keeps the largest bundle (GitHub) under the 8k TPM budget
    try: print(X.run_provider2("groq_orgA", cfg, APPS, P, SH, FU, schema, B.adapter_call, quota, breaker, HERE, log, key=X.secret("GROQ_API_KEY")))
    except B.StopAll as e: print("STOP_ALL", e)
if __name__ == "__main__":
    {"retrieve": retrieve, "build": build, "run": run}[sys.argv[1]]()

"""Per-pass progress/error/retry/verification stats. Usage: python src/stats.py"""
import json, collections, pathlib
W = pathlib.Path(__file__).resolve().parent.parent / "work"
def events(f):
    p = W / f
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
# ---- Pass 1 (Gemini via Composio/TinyFish)
ev = events("log.jsonl"); recs = [json.load(open(p)) for p in (W / "pass1").glob("*.json")]
c = collections.Counter(e["ev"] for e in ev)
gerr = collections.Counter(e["code"] for e in ev if e["ev"] == "gemini_err")
failed = sorted({e["id"] for e in ev if e["ev"] == "FAILED"} - {r["id"] for r in recs})
q = [e for r in recs for e in r["evidence"]]
print(f"PASS 1 (Gemini)  completed={len(recs)}/100  failed_pending_retry={failed}")
print(f"  models used: {dict(collections.Counter(r['model'] for r in recs))}")
print(f"  gemini retries/errors by code: {dict(gerr)}  exceptions={c['gemini_exc']}  composio_tool_retries={c['tf_retry']}")
print(f"  evidence quotes found verbatim in fetched page: {sum(e['quote_found'] for e in q)}/{len(q)}")
print(f"  unknown fields: auth={sum(r['auth_methods']==['unknown'] for r in recs)} access={sum(r['access']=='unknown' for r in recs)}")
# ---- Pass 2 (Groq)
ev2 = events("verify_log.jsonl"); vs = [json.load(open(p)) for p in (W / "verify").glob("*.json")]
done = [v for v in vs if v.get("complete")]; items = [i for v in done for f in v["fields"].values() for i in f]
c2 = collections.Counter(e["ev"] for e in ev2)
print(f"\nPASS 2 (Groq {done[0]['model'] if done else ''})  verified={len(done)}/{len(recs)} pass-1 records  (flags, not ground truth)")
print(f"  groq retries={c2['groq_retry']} (by code {dict(collections.Counter(e['code'] for e in ev2 if e['ev']=='groq_retry'))})  gave_up={c2['groq_gave_up']}  app_failures={c2['verify_FAILED']}")
print(f"  item verdicts: {dict(collections.Counter(i['verdict'] for i in items))}")
print(f"  needs_human={sum(i.get('needs_human', False) for i in items)} of {len(items)} items; downgraded contradictions={sum(i.get('flag')=='contradiction_without_verifiable_quote' for i in items)}")

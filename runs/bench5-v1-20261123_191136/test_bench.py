"""OFFLINE regression tests for bench.py: mocked providers, fake clock, temp dirs. No network, no quota use. Synthetic fixtures = control-logic tests, NOT evidence of extraction quality."""
import os, sys, json, shutil, tempfile, unittest, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import bench as B
v7, v6, SCH, PROMPT, H_SCH, H_PR, _ = B.load_frozen(); os.chdir(B.ROOT); P, PG, FG = B.load_bundles()
class Clock:
    def __init__(s): s.t = 1_000_000.0
    def __call__(s): return s.t
    def sleep(s, x): s.t += x
def good(i, model="m", tin=100, tout=50, **kw):
    pg = PG[i][0]; q = " ".join(pg["text"].split()[:8])
    o = dict(one_liner="x", auth_methods=["unknown"], access="unknown", access_note="", api_types=["unknown"], api_breadth="unknown", existing_mcp="unknown", buildability="unknown", blocker="none", evidence=[dict(field="access", url=pg["url"], quote=q)])
    return dict(http=200, text=json.dumps(o), tin=tin, tout=tout, model_returned=model, headers={}, latency=1.0, cost=0.0, error=None, **kw)
CFG = lambda **k: dict(B.PROVIDERS["openrouter_particle"], cap=5, **k)
class T(unittest.TestCase):
    def setUp(s): s.d = tempfile.mkdtemp(); s.c = Clock(); s.calls = []; s.log = B.Log(s.d + "/logs/r.jsonl")
    def tearDown(s): shutil.rmtree(s.d, ignore_errors=True)
    def q(s, **lim): return B.Quota(s.d + "/q.json", {"b": dict(dict(rpm=None, tpm=None, rpd=None), **lim)}, clock=s.c)
    def run_p(s, script, cfg=None, quota=None, apps=B.APPS):
        cfg = dict(cfg or CFG(), bucket="b"); script = list(script)
        def call(cf, prompt, schema, key): s.calls.append(prompt); r = script.pop(0) if script else good(61, cf["model"]); return r(len(s.calls)) if callable(r) else r
        return B.run_provider("t", cfg, apps, P, PG, FG, SCH, call, quota or s.q(), s.d, s.log, v6.check_quotes, sleep=s.c.sleep)
    # --- quota manager
    def test01_tpm_rolling_window(s):
        q = s.q(tpm=8000); q.reserve("b", 6000); s.assertEqual(q.wait_needed("b", 500), 0); s.assertAlmostEqual(q.wait_needed("b", 5000), 60, 3); s.c.t += 30; s.assertAlmostEqual(q.wait_needed("b", 5000), 30, 3); s.c.t += 31; s.assertEqual(q.wait_needed("b", 5000), 0)
    def test02_rpm(s):
        q = s.q(rpm=2); q.reserve("b", 1); s.c.t += 10; q.reserve("b", 1); s.assertAlmostEqual(q.wait_needed("b", 1), 50, 3)
    def test03_rpd_stops(s):
        q = s.q(rpd=2); q.reserve("b", 1); q.reserve("b", 1)
        with s.assertRaises(B.QuotaStop): q.wait_needed("b", 1)
    def test04_oversize_request_never_sent(s):
        q = s.q(tpm=8000)
        with s.assertRaises(B.QuotaStop): q.wait_needed("b", 7300)
        r = s.run_p([], cfg=dict(CFG(), max_out=7000), quota=q); s.assertEqual(r, "quota_stop"); s.assertEqual(s.calls, [])
    def test05_persistence(s):
        q = s.q(rpd=3); q.reserve("b", 10); q.observe("b", note="x"); q2 = s.q(rpd=3); s.assertEqual(len(q2.b("b")["req"]), 1); s.assertEqual(len(q2.b("b")["observations"]), 1)
    def test06_retry_after_blocks(s):
        q = s.q(); q.block("b", 45, "rate"); s.assertAlmostEqual(q.wait_needed("b", 1), 45, 3); q.block("b", 3600, "daily")
        with s.assertRaises(B.QuotaStop): q.wait_needed("b", 1)
    # --- runner
    def test07_cap_includes_retries_and_no_starvation(s):
        e = dict(http=503, text=None, tin=None, tout=None, model_returned=None, headers={}, latency=1, cost=0, error="busy")
        s.run_p([e]); s.assertEqual(len(s.calls), 5); s.assertEqual(len([f for f in os.listdir(s.d + "/outputs/t") if f.startswith("failed")]), 1)     # cap 5: retry would starve app 5 => none
        s.calls.clear(); shutil.rmtree(s.d + "/outputs"); s.run_p([e], cfg=CFG() | dict(cap=6)); s.assertEqual(len(s.calls), 6)                   # cap 6: one retry allowed
    def test08_model_mismatch_stops(s):
        r = s.run_p([good(27, "other/model")]); s.assertEqual(r, "model_mismatch"); s.assertEqual(len(s.calls), 1); s.assertFalse(os.path.exists(s.d + "/outputs/t/27.json"))
    def test09_payment_stops_all(s):
        with s.assertRaises(B.StopAll): s.run_p([dict(http=402, text=None, tin=None, tout=None, model_returned=None, headers={}, latency=1, cost=0, error="Payment Required")])
    def test10_daily_429_stops_provider_no_substitution(s):
        r = s.run_p([dict(http=429, text=None, tin=None, tout=None, model_returned=None, headers={}, latency=1, cost=0, error="free-models-per-day limit reached")]); s.assertEqual(r, "daily_quota"); s.assertEqual(len(s.calls), 1)
        q = s.q(); 
        with s.assertRaises(B.QuotaStop): q.wait_needed("b", 1)
    def test11_nonzero_cost_stops_all(s):
        with s.assertRaises(B.StopAll): s.run_p([dict(good(27), cost=0.01)])
    def test12_completed_apps_not_rerun(s):
        s.run_p([]); n = len(s.calls); s.assertEqual(n, 5); s.run_p([]); s.assertEqual(len(s.calls), n)
    def test13_rate_limit_retry_after_respected(s):
        e = dict(http=429, text=None, tin=None, tout=None, model_returned=None, headers={"retry-after": "30"}, latency=1, cost=0, error="rate limit per minute")
        s.run_p([e], cfg=CFG() | dict(cap=6)); s.assertEqual(len(s.calls), 6); s.assertTrue(s.c.t - 1_000_000.0 >= 30)
    def test14_ambiguous_429_no_retry(s):
        e = dict(http=429, text=None, tin=None, tout=None, model_returned=None, headers={}, latency=1, cost=0, error="Resource has been exhausted")
        s.run_p([e], cfg=CFG() | dict(cap=9)); s.assertEqual(len(s.calls), 5)
    def test15_failed_record_scrubs_secrets(s):
        k = B.secret("GROQ_API_KEY"); e = dict(http=400, text=None, tin=None, tout=None, model_returned=None, headers={}, latency=1, cost=0, error="bad request " + k)
        s.run_p([e]); blob = "".join(open(os.path.join(s.d, "outputs/t", f)).read() for f in os.listdir(s.d + "/outputs/t")); s.assertNotIn(k, blob); s.assertIn("[REDACTED]", blob)
    def test16_log_hash_chain_append_only(s):
        s.run_p([]); lines = open(s.d + "/logs/r.jsonl").read().splitlines(); prev = "0" * 64
        for ln in lines: s.assertEqual(json.loads(ln)["prev"], prev); prev = B.sha(ln)
        s.assertIn("O_APPEND", __import__("inspect").getsource(B.Log.__call__))
    # --- validation
    def test17_pydantic_unknown_vs_not_found(s):
        for v in ("unknown", "none_found"):
            o = json.loads(good(27)["text"]); o["existing_mcp"] = v; r, ob = B.validate_output(json.dumps(o), PG[27], FG[27], v6.check_quotes); s.assertTrue(r["schema_ok"]); s.assertEqual(ob["existing_mcp"], v)
        o["existing_mcp"] = "false"; r, _ = B.validate_output(json.dumps(o), PG[27], FG[27], v6.check_quotes); s.assertFalse(r["schema_ok"])
        r, _ = B.validate_output("not json", PG[27], FG[27], v6.check_quotes); s.assertFalse(r["json_ok"])
    def test18_pydantic_enums_match_frozen_schema(s):
        js = B.AppResearch.model_json_schema()["properties"]
        for k, v in SCH["properties"].items():
            if "enum" in v: s.assertEqual(set(js[k]["anyOf"][0]["enum"] if "anyOf" in js[k] else js[k]["enum"]), set(v["enum"]), k)
            if v["type"] == "ARRAY" and "enum" in v["items"]: s.assertEqual(set(B.json_schema_from_gemini(v)["items"]["enum"]), set(v["items"]["enum"]))
        s.assertEqual(set(SCH["required"]), set(B.AppResearch.model_fields))
    def test19_quote_validation_flags_fabricated(s):
        o = json.loads(good(27)["text"]); o["evidence"][0]["quote"] = "completely invented sentence zzz"; r, ob = B.validate_output(json.dumps(o), PG[27], FG[27], v6.check_quotes); s.assertEqual(r["quote_found"], 0); s.assertEqual(B.unsupported_claims(dict(ob, access="self_serve_free")), ["access"])
    # --- providers / filter / bundles
    def test20_openrouter_filter(s):
        m = lambda i, o, p=0, inp=("text",): dict(id=i, architecture=dict(output_modalities=o, input_modalities=list(inp)), pricing=dict(prompt=p, completion=p))
        r = B.or_text_models([m("a/text:free", ["text"]), m("google/lyria-3-pro-preview", ["audio"]), m("x/img:free", ["image"]), m("y/paid", ["text"], 0.1), m("z/mixed", ["text", "image"]), m("lyria-text", ["text"])]); s.assertEqual(r, ["a/text:free"])
    def test21_classify_error(s):
        c = lambda h, e: B.classify_error(dict(http=h, error=e)); s.assertEqual(c(429, "per day quota"), "daily_quota"); s.assertEqual(c(429, "tokens per minute"), "rate_limit"); s.assertEqual(c(429, "???"), "ambiguous_429"); s.assertEqual(c(402, ""), "payment_required"); s.assertEqual(c(503, ""), "server_5xx"); s.assertEqual(c(None, "Timeout"), "network_error"); s.assertEqual(c(400, "x"), "client_error")
    def test22_reduction_deterministic_and_identical_prompts(s):
        for i, _ in B.APPS:
            b = json.load(open(f"{HERE}/bundles/{i}.json")); s.assertEqual(B.reduce_pages(FG[i]), b["pages"]); s.assertEqual(B.sha(P[i]), b["prompt_sha256"]); s.assertLess(len(b["prompt"]), len(json.load(open(f"{HERE}/bundles_full/{i}.json"))["pages"][0]["text"]) * 50)
        cfgj = json.load(open(HERE + "/BENCH_CONFIG.json")); s.assertEqual((cfgj["prompt_sha256"], cfgj["schema_sha256"]), (H_PR, H_SCH))
    def test23_groq_prompts_fit_tpm_budget(s):
        g = B.PROVIDERS["groq_orgA"]
        for i, _ in B.APPS: s.assertLessEqual(B.est_tokens(len(P[i])) + g["max_out"], int(g["limits"]["tpm"] * 0.9), i)
    def test24_full_evidence_preserved(s):
        for i, _ in B.APPS: f = json.load(open(f"{HERE}/bundles_full/{i}.json")); s.assertGreaterEqual(sum(len(p["text"]) for p in f["pages"]), sum(len(p["text"]) for p in PG[i]))
    def test25_no_fallback_models_in_source(s):
        src = open(HERE + "/bench.py").read(); s.assertEqual([c["model"] for c in B.PROVIDERS.values()], ["openai/gpt-oss-120b", "particle-ai/particle-1:free", "gemini-2.5-flash", "gemini-3.6-flash"]); s.assertNotIn("APPROVED", src.replace("no APPROVED.json involved", ""))
        s.assertEqual(B.PROVIDERS["groq_orgA"]["key_env"], "GROQ_API_KEY"); s.assertNotIn("GROQ_KEY_P", json.dumps({k: v for k, v in B.PROVIDERS.items()}))
if __name__ == "__main__": unittest.main(verbosity=2)

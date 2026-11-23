"""OFFLINE regression tests for bench2 (breaker/backoff, validation v2, Gemini staging, reduction v2, P2-P4 disable, v1 preservation). Mocked providers, fake clock, temp dirs. No network, no quota."""
import os, sys, json, shutil, tempfile, unittest, hashlib, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import bench2 as X
B = X.B; v7, v6, SCH, PROMPT, H_SCH, H_PR, _ = B.load_frozen(); os.chdir(B.ROOT); P, SH, FU = X.load_v1_bundles()
class Clock:
    def __init__(s, t=1_000_000.0): s.t = t
    def __call__(s): return s.t
    def sleep(s, x): s.t += x
R = lambda **k: dict(dict(http=200, text=None, tin=None, tout=None, model_returned=None, headers={}, latency=1.0, cost=0.0, error=None), **k)
def good(i, model="m", **k):
    pg = SH[i][0]; q = " ".join(pg["text"].split()[:12]); o = dict(one_liner="x", auth_methods=["unknown"], access="unknown", access_note="", api_types=["unknown"], api_breadth="unknown", existing_mcp="unknown", buildability="unknown", blocker="none", evidence=[dict(field="access", url=pg["url"], quote=q)])
    return R(text=json.dumps(o), tin=100, tout=50, model_returned=model, **k)
E429 = R(http=429, error='{"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"temporarily rate-limited upstream","retry_after_seconds":1}}}', headers={"retry-after": "1"})
CFG = dict(B.PROVIDERS["openrouter_particle"], cap=5, min_gap_s=10, bucket="b")
class T(unittest.TestCase):
    def setUp(s): s.d = tempfile.mkdtemp(); s.c = Clock(); s.n = 0; s.log = B.Log(s.d + "/l.jsonl"); s.q = B.Quota(s.d + "/q.json", {"b": dict(rpm=None, tpm=None, rpd=50)}, clock=s.c); s.br = X.Breaker(s.d + "/b.json", clock=s.c)
    def tearDown(s): shutil.rmtree(s.d, ignore_errors=True)
    def run_p(s, script, cfg=None, apps=B.APPS):
        script = list(script)
        def call(cf, pr, sc, key): s.n += 1; r = script.pop(0) if script else good(61, cf["model"]); return r
        return X.run_provider2("t", dict(cfg or CFG), apps, P, SH, FU, SCH, call, s.q, s.br, s.d, s.log, sleep=s.c.sleep, clock=s.c)
    # ---- (1) breaker / backoff
    def test01_backoff_floor_ignores_retry_after_1s(s): s.assertEqual(X.backoff_s(1, 1), 30.0); s.assertEqual(X.backoff_s(1, 2), 60.0); s.assertEqual(X.backoff_s(500, 1), 300.0); s.assertEqual(X.retry_after_s(E429), 1.0)
    def test02_two_failures_open_breaker_not_five_calls(s):
        r = s.run_p([E429] * 5, cfg=dict(CFG, cap=9)); s.assertEqual(r, "breaker_open"); s.assertEqual(s.n, 2); s.assertGreaterEqual(s.c.t - 1_000_000.0, 30)
    def test03_open_breaker_blocks_until_cooldown_then_exactly_one_probe(s):
        s.run_p([E429] * 2, cfg=dict(CFG, cap=9)); n = s.n; r = s.run_p([good(27, CFG["model"])] * 5); s.assertEqual((r, s.n), ("breaker_open", n))      # still cooling down: no request
        s.c.t += X.COOLDOWN0 + 1; r = s.run_p([E429, good(27, CFG["model"])]); s.assertEqual(s.n, n + 1); s.assertEqual(s.br.b("b")["state"], "open"); s.assertEqual(s.br.b("b")["cooldown_s"], 1200.0)   # probe failed -> doubled
    def test04_probe_success_closes_and_resumes(s):
        s.run_p([E429] * 2, cfg=dict(CFG, cap=9)); s.c.t += X.COOLDOWN0 + 1; r = s.run_p([good(i, CFG["model"]) for i, _ in B.APPS], cfg=dict(CFG, cap=9)); s.assertEqual(r, "completed"); s.assertEqual(s.br.b("b")["state"], "closed")
    def test05_gives_up_after_max_opens(s):
        for _ in range(X.MAX_OPENS + 1): s.br.failure("b"); s.br.failure("b"); s.c.t += X.COOLDOWN_CAP + 1; s.br.gate("b")
        s.assertEqual(s.br.b("b")["state"], "gave_up"); s.assertEqual(s.br.gate("b")[0], "gave_up")
    def test06_breaker_persists_across_restart(s):
        s.br.failure("b"); s.br.failure("b"); s.assertEqual(X.Breaker(s.d + "/b.json", clock=s.c).gate("b")[0], "wait")
    def test07_success_resets_consecutive(s): s.br.failure("b"); s.br.success("b"); s.br.failure("b"); s.assertEqual(s.br.b("b")["state"], "closed")
    def test08_min_gap_between_requests(s):
        times = []
        def call(cf, pr, sc, key): times.append(s.c.t); return good(61, cf["model"])
        X.run_provider2("t", dict(CFG), B.APPS, P, SH, FU, SCH, call, s.q, s.br, s.d, s.log, sleep=s.c.sleep, clock=s.c); s.assertTrue(all(b - a >= 10 for a, b in zip(times, times[1:])), times)
    def test09_seed_or_breaker_from_v1_log(s):
        b = X.Breaker(s.d + "/seed.json", clock=s.c); X.seed_or_breaker(b); k = B.PROVIDERS["openrouter_particle"]["bucket"]; s.assertEqual((b.b(k)["state"], b.b(k)["opens"], b.b(k)["consec"]), ("open", 1, 5))
        s.assertEqual(X.Breaker(s.d + "/seed.json", clock=lambda: b.b(k)["opened_at"] + 10).gate(k)[0], "wait")
    # ---- (3) validation v2
    def vr(s, i, **ch):
        o = json.loads(good(i)["text"]); o.update(ch); return X.validate_v2(o, SH[i], FU[i])
    def ev(s, i, field, quote, url=None): return dict(field=field, url=url or SH[i][0]["url"], quote=quote)
    def test10_unknown_placeholder_rejected(s):
        v = s.vr(27, evidence=[s.ev(27, "existing_mcp", "unknown")]); s.assertIn("placeholder_or_too_short", v["evidence"][0]["issues"])
    def test11_ellipsis_and_stitched_rejected(s):
        t = SH[27][0]["text"]; words = t.split(); a, b = " ".join(words[:8]), " ".join(words[60:68]); v = s.vr(27, evidence=[s.ev(27, "access", a + " ... " + b), s.ev(27, "access", a + " " + b)])
        s.assertIn("stitched_ellipsis", v["evidence"][0]["issues"]); s.assertIn("not_contiguous_in_cited_page", v["evidence"][1]["issues"])
    def test12_quote_must_be_in_cited_page(s):
        other = SH[27][1]["text"].split(); q = " ".join(other[:12]); v = s.vr(27, evidence=[s.ev(27, "access", q, url=SH[27][0]["url"])]); s.assertIn("not_contiguous_in_cited_page", v["evidence"][0]["issues"])
    def test13_non_unknown_claim_requires_valid_supporting_quote(s):
        v = s.vr(27, auth_methods=["oauth2"], evidence=[]); s.assertEqual(v["claims"][0]["state"], "unsupported")
        t = FU[41][0]; sent = [x for x in t["text"].split("\n") if "oauth" in x.lower() and len(x) > 40][:1]
        if sent: v = X.validate_v2(dict(json.loads(good(41)["text"]), auth_methods=["oauth2"], evidence=[dict(field="auth_methods", url=t["url"], quote=sent[0][:150])]), FU[41], FU[41]); s.assertIn(v["claims"][0]["state"], ("supported_lexical", "unsupported"))
    def test14_unknown_and_not_found_stay_separate_and_absence_not_inferred(s):
        a = s.vr(27, existing_mcp="unknown")["claims"]; b = s.vr(27, existing_mcp="none_found")["claims"]; st = lambda c: [x["state"] for x in c if x["field"] == "existing_mcp"][0]
        s.assertEqual(st(a), "unknown"); s.assertEqual(st(b), "not_found_in_provided_evidence"); s.assertNotEqual(st(a), st(b))
        c = s.vr(27, existing_mcp="official", evidence=[]); s.assertEqual(st(c["claims"]), "unsupported")           # official needs an MCP quote
    def test15_mcp_official_needs_mcp_term_in_valid_quote(s):
        p = [p for p in FU[41] if "shopify mcp" in p["text"].lower()][0]; i = p["text"].lower().index("shopify mcp"); q = p["text"][i:i + 110]
        o = dict(json.loads(good(41)["text"]), existing_mcp="official", evidence=[dict(field="existing_mcp", url=p["url"], quote=q)]); v = X.validate_v2(o, FU[41], FU[41]); s.assertEqual([c["state"] for c in v["claims"] if c["field"] == "existing_mcp"], ["supported_lexical"])
    # ---- (2) Gemini staging
    def test16_gemini_refuses_before_reset(s):
        s.c.t = X.GEMINI_RESET_UTC - 3600; r = X.gemini_stage("g", dict(CFG, model="gemini-2.5-flash", cap=5), P, SH, FU, SCH, lambda *a: (_ for _ in ()).throw(AssertionError("call before reset")), s.q, s.br, s.d, s.log, "k", clock=s.c, sleep=s.c.sleep); s.assertEqual(r, "before_reset")
    def test17_capability_first_then_five_apps(s):
        s.c.t = X.GEMINI_RESET_UTC + 60; seq = []
        def call(cf, pr, sc, key): seq.append("cap" if sc is X.TINY_SCHEMA else "app"); return R(text='{"ok": true}', tin=5, tout=3, model_returned="gemini-2.5-flash") if sc is X.TINY_SCHEMA else good(61, "gemini-2.5-flash")
        r = X.gemini_stage("g", dict(CFG, model="gemini-2.5-flash", cap=5), P, SH, FU, SCH, call, s.q, s.br, s.d, s.log, "k", clock=s.c, sleep=s.c.sleep); s.assertEqual(seq, ["cap"] + ["app"] * 5); s.assertEqual(r, "completed")
    def test18_capability_failure_blocks_benchmark(s):
        s.c.t = X.GEMINI_RESET_UTC + 60; seq = []
        def call(cf, pr, sc, key): seq.append(1); return R(http=429, error="Quota exceeded per day")
        r = X.gemini_stage("g", dict(CFG, model="gemini-2.5-flash", cap=5), P, SH, FU, SCH, call, s.q, s.br, s.d, s.log, "k", clock=s.c, sleep=s.c.sleep); s.assertEqual((r, len(seq)), ("capability_failed", 1))
    # ---- (6) disabled accounts, preservation, reduction v2, TPD
    def test19_p2_p4_disabled(s):
        for n in X.DISABLED_ENV:
            with s.assertRaises(PermissionError): B.secret(n)
        s.assertEqual({c["key_env"] for c in X.PROVIDERS.values()}, {"GROQ_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_2"})
    def test20_v1_outputs_and_bundles_unchanged(s):
        rec = [l.split("  ", 1) for l in open(HERE + "/V1_SHA256_AT_V2_START.txt").read().splitlines()]; s.assertGreater(len(rec), 15)
        for h, f in rec: s.assertEqual(hashlib.sha256(open(f"{X.V1DIR}/{f}", "rb").read()).hexdigest(), h, f)
    def test21_reduction_v2_keeps_mcp_deterministic_and_fits_groq(s):
        r1 = X.reduce_pages_v2(FU[53]); s.assertEqual(r1, X.reduce_pages_v2(FU[53])); cnt = lambda pg: sum(len(X.re.findall(X.MCP, p["text"], X.re.I)) for p in pg); s.assertEqual(cnt(SH[53]), 0); s.assertGreaterEqual(cnt(r1), cnt(FU[53]))
        g = B.PROVIDERS["groq_orgA"]
        for i, _ in B.APPS: s.assertLessEqual(B.est_tokens(sum(len(p["text"]) for p in X.reduce_pages_v2(FU[i])) + 1500) + g["max_out"], int(g["limits"]["tpm"] * 0.9))
    def test22_tpd_soft_limit(s):
        q = X.Quota2(s.d + "/q2.json", {"b": dict(rpm=None, tpm=None, rpd=None, tpd=10000)}, clock=s.c); q.reserve("b", 8500)
        with s.assertRaises(B.QuotaStop): q.wait_needed("b", 1000)
    def test23_frozen_inputs_and_no_approved_file(s):
        s.assertEqual(hashlib.sha256(open(B.ROOT + "/src/run_p1.py", "rb").read()).hexdigest(), "71d0f19e74765f5942402ff5be29b4429650b5506ebbe6c668638cf234a15c14"); s.assertEqual((H_PR, H_SCH), ("13eaee38702bfb72c6d92529a50eedc26bf7eebecc46cac27a2b516cb20c58ae", "c5082c7feb4a2256d30b9b2ce051cc3360c6bdae74f509f01a0713a5b97300e9"))
        s.assertEqual(subprocess.run(["find", B.ROOT, "-name", "APPROVED*", "-not", "-path", "*/.git/*"], capture_output=True, text=True).stdout.strip(), "")
    def test24_unsent_probe_not_consumed(s):
        s.br.failure("b"); s.br.failure("b"); s.c.t += X.COOLDOWN0 + 1; s.assertEqual(s.br.gate("b")[0], "probe"); s.assertEqual(s.br.gate("b")[0], "probe"); s.br.probe_started("b"); s.assertEqual(s.br.gate("b")[0], "wait")
    def test25_log_chain_continues_across_instances(s):
        s.log(ev="a"); l2 = X.Log(s.d + "/l.jsonl"); l2(ev="b"); lines = open(s.d + "/l.jsonl").read().splitlines(); s.assertEqual(json.loads(lines[1])["prev"], B.sha(lines[0]))
    def test26_invalid_json_400_is_app_level_not_provider_stop(s):
        e = R(http=400, error='{"error":{"code":"json_validate_failed"}}'); r = s.run_p([e], cfg=dict(CFG, cap=9)); s.assertEqual(r, "completed"); s.assertEqual(s.n, 5); s.assertFalse(os.path.exists(s.d + "/outputs/t/27.json"))
        s.n = 0; s.run_p([]); s.assertEqual(s.n, 0)                  # failed app not re-sent; the other four are already checkpointed
if __name__ == "__main__": unittest.main(verbosity=2)

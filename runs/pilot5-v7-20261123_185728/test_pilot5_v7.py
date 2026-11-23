"""OFFLINE tests for runner v7. Mocked provider + deterministic fake clock. No network, no quota. Synthetic fixtures = regression tests, NOT evidence of extraction quality. Writes only to temp dirs."""
import os, sys, json, shutil, tempfile, threading, unittest, inspect
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import run_pilot5_v7 as R
OKP = dict(one_liner="x", auth_methods=["unknown"], access="unknown", access_note="", api_types=["unknown"], api_breadth="unknown", existing_mcp="unknown", buildability="unknown", blocker="none", evidence=[])
ok = lambda **k: dict(http=200, payload=dict(OKP, **k), model_version=R.MODEL)
RATE = dict(http=429, body='{"error":{"status":"RESOURCE_EXHAUSTED","details":[{"violations":[{"quotaId":"GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]}]}}')   # ASSUMED fixture format (no live 429 body has been observed)
DAILY = dict(http=429, body='{"error":{"status":"RESOURCE_EXHAUSTED","details":[{"violations":[{"quotaId":"GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}')
AMBIG = dict(http=429, body='{"error":{"status":"RESOURCE_EXHAUSTED","message":"Resource has been exhausted"}}')
S503 = dict(http=503, body="high demand")
class Clock:
    def __init__(s, t0=1_000_000.0): s.t = 0.0; s.t0 = t0; s.sleeps = []
    def mono(s): return s.t
    def wall(s): return s.t0 + s.t
    def sleep(s, x): s.sleeps.append(x); s.t += x
class Prov:                                   # scripted provider; records mono time of each call start; 1 s latency
    def __init__(s, clock, script): s.c, s.script, s.times, s.prompts = clock, list(script), [], []
    def __call__(s, prompt, schema):
        s.times.append(s.c.mono()); s.prompts.append(prompt); s.c.t += 1.0
        if not s.script: raise AssertionError("provider called more often than scripted")
        return s.script.pop(0)
class Base(unittest.TestCase):
    def setUp(s):
        s.tmp = tempfile.mkdtemp(); s.rd = s.tmp; s.out = s.tmp + "/output"; shutil.copy(HERE + "/PILOT5_MANIFEST.json", s.rd); s.clock = Clock()
    def tearDown(s): shutil.rmtree(s.tmp, ignore_errors=True)
    def approve(s, **over):
        a = dict(manifest_sha256=R.sha(open(s.rd + "/PILOT5_MANIFEST.json", "rb").read()), model=R.MODEL, max_requests=8); a.update(over); json.dump(a, open(s.rd + "/APPROVED.json", "w"))
    def go(s, script, clock=None, approve=True, **kw):
        if approve and not os.path.exists(s.rd + "/APPROVED.json"): s.approve()
        c = clock or s.clock; p = Prov(c, script); r = R.execute(s.rd, s.out, p, mono=c.mono, wall=c.wall, sleep=c.sleep, **kw); return r, p
    def ack(s, extra=None):
        d = dict(stop_sha256=R.sha(open(s.out + "/STOPPED.json", "rb").read()), reviewer="test"); d.update(extra or {}); json.dump(d, open(s.out + "/STOP_REVIEWED.json", "w"))
    def state(s): return json.load(open(s.out + "/state.json"))
    def done(s): return sorted(int(f[:-5]) for f in os.listdir(s.out + "/pass1"))
class T(Base):
    def test01_sequential_gap(s):
        r, p = s.go([ok()] * 5); s.assertEqual(r["stopped"], "completed"); s.assertTrue(all(b - a >= 13 for a, b in zip(p.times, p.times[1:])), p.times); s.assertEqual(len(p.times), 5)
    def test02_retries_paced_and_backoff(s):
        r, p = s.go([RATE, ok()] + [ok()] * 4); s.assertEqual(r["stopped"], "completed"); s.assertTrue(all(b - a >= 13 for a, b in zip(p.times, p.times[1:])), p.times); s.assertIn(30.0, s.clock.sleeps)
    def test03_concurrent_cannot_bypass(s):
        c = Clock(); pc = R.Pacer(13.0, c.mono, c.wall, c.sleep); stamps = []; lk = threading.Lock()
        def w(): t = pc.wait(); [stamps.append(t)]
        th = [threading.Thread(target=w) for _ in range(6)]; [t.start() for t in th]; [t.join() for t in th]; st = sorted(stamps); s.assertEqual(len(st), 6); s.assertTrue(all(b - a >= 13 for a, b in zip(st, st[1:])), st)
    def test03b_lock_blocks_second_writer(s):
        s.approve(); os.makedirs(s.out); open(s.out + "/.lock", "w").close(); r, p = s.go([]); s.assertEqual(r["stopped"], "refused_lock_held")
    def test04_eighth_allowed_ninth_refused_and_05_retries_share_budget(s):
        r, p = s.go([RATE, ok()] * 5); s.assertEqual(r["stopped"], "budget_exhausted"); s.assertEqual(len(p.times), 8); s.assertEqual(s.state()["attempts_total"], 8); s.assertEqual(s.done(), [27, 32, 41, 53]); s.assertEqual(s.state()["per_app"]["27"], 2)
    def test06_restart_preserves_count(s):
        s.go([RATE, ok()] * 5); s.ack(); c2 = Clock(t0=s.clock.wall() + 1000); r, p = s.go([], clock=c2); s.assertEqual(r["stopped"], "budget_exhausted"); s.assertEqual(p.times, []); s.assertEqual(s.state()["attempts_total"], 8)
    def test07_restart_preserves_pacing(s):
        bad = ok(evidence=[dict(field="access", url="https://nope.invalid", quote="zzz not in sources")]); r, p = s.go([bad]); s.assertEqual(r["stopped"], "review_app1_evidence_quote_failure")
        last = s.state()["last_request_wall"]; s.ack(); c2 = Clock(t0=last + 5); r, p2 = s.go([ok()] * 4, clock=c2); s.assertEqual(r["stopped"], "completed"); s.assertAlmostEqual(c2.sleeps[0], 8.0, places=3)   # 13 - 5 s already elapsed
        s.assertEqual(len(p2.times), 4); s.assertTrue(all("Telegram" not in x for x in p2.prompts))     # test15 too: completed app 27 not re-run
    def test07b_clock_backwards_waits_full_gap(s):
        pc = R.Pacer(13.0, lambda: 0.0, lambda: 100.0, lambda x: s.clock.sleep(x), last_wall=500.0); pc.wait(); s.assertEqual(s.clock.sleeps, [13.0])
    def test08_daily_429_stops_immediately(s):
        r, p = s.go([DAILY, ok()]); s.assertEqual(r["stopped"], "daily_quota_429"); s.assertEqual(len(p.times), 1); s.assertEqual(s.clock.sleeps, []); s.assertEqual(r["record"]["http_status"], 429); s.assertEqual(r["record"]["total_generation_attempts"], 1)
    def test09_rate_limit_bounded_backoff(s):
        r, p = s.go([RATE, RATE, RATE, ok()]); s.assertEqual(r["stopped"], "rate_limit_retries_exhausted"); s.assertEqual(len(p.times), 3); s.assertEqual([x for x in s.clock.sleeps if x >= 30], [30.0, 60.0])
    def test10_ambiguous_429_stops(s):
        r, p = s.go([AMBIG, ok()]); s.assertEqual(r["stopped"], "ambiguous_429_human_review"); s.assertEqual(len(p.times), 1)
    def test11_two_5xx_different_apps_stop(s):
        r, p = s.go([S503, S503, ok()]); s.assertEqual(r["stopped"], "two_consecutive_5xx_different_apps"); s.assertEqual(len(p.times), 2); s.assertEqual(s.done(), [])
    def test12_single_5xx_continues(s):
        r, p = s.go([S503] + [ok()] * 4); s.assertEqual(r["stopped"], "finished_with_uncheckpointed_apps"); s.assertEqual(s.done(), [32, 41, 53, 61]); s.assertEqual(s.state()["consec_5xx"], [])
    def test12b_5xx_reset_by_success(s):
        r, p = s.go([S503, ok(), S503, ok(), ok()]); s.assertNotEqual(r["stopped"], "two_consecutive_5xx_different_apps")
    def test13_unexpected_model_stops(s):
        r, p = s.go([dict(ok(), model_version="gemini-3.5-flash")]); s.assertEqual(r["stopped"], "unexpected_model_identity"); s.assertEqual(s.done(), []); s.assertTrue(os.path.exists(s.out + "/stops/rejected_27.json"))
    def test14_missing_identity_reported(s):
        r, p = s.go([dict(ok(), model_version=None)]); s.assertEqual(r["stopped"], "model_identity_unverified_review_required"); rec = json.load(open(s.out + "/pass1/27.json")); s.assertFalse(rec["meta"]["model_identity_verified"]); s.assertIsNone(rec["meta"]["returned_model_version"])
    def test14b_schema_violation_stops_not_repaired(s):
        r, p = s.go([dict(http=200, payload=dict(OKP, access="maybe"), model_version=R.MODEL)]); s.assertEqual(r["stopped"], "schema_violation"); s.assertEqual(s.done(), [])
    def test16_corrupt_checkpoint_refused(s):
        s.approve(); os.makedirs(s.out + "/pass1"); open(s.out + "/pass1/27.json", "w").write("{not json"); r, p = s.go([]); s.assertEqual(r["stopped"], "refused_corrupt_checkpoint"); s.assertEqual(p.times, [])
        os.remove(s.out + "/pass1/27.json"); open(s.out + "/pass1/32.json.tmp", "w").write("x"); r, p = s.go([]); s.assertEqual(r["stopped"], "refused_corrupt_checkpoint")
    def test16b_corrupt_state_refused(s):
        s.go([RATE, DAILY]); open(s.out + "/state.json", "w").write("garbage"); s.ack(); r, p = s.go([]); s.assertEqual(r["stopped"], "refused_corrupt_state")
    def test17_log_append_only_tamper_detected(s):
        s.go([DAILY]); lp = s.out + "/logs/activity.jsonl"; lines = open(lp).read().splitlines(); s.assertGreaterEqual(len(lines), 3)
        s.assertIn("O_APPEND", inspect.getsource(R.Store.log)); open(lp, "w").write("\n".join(lines[1:]) + "\n"); s.ack(); r, p = s.go([]); s.assertEqual(r["stopped"], "refused_corrupt_activity_log")
    def test18_no_fallback_possible(s):
        s.assertEqual(list(inspect.signature(R.make_gemini_call("k")).parameters), ["prompt", "schema"]); src = open(R.__file__).read()
        for bad in ("gemini-3", "GEMINI_API_KEY_2", "openrouter", "GROQ_API_KEY"): s.assertNotIn(bad, src.lower() if bad.islower() else src)
        m = json.load(open(s.rd + "/PILOT5_MANIFEST.json")); m["model"] = "gemini-3.5-flash"; json.dump(m, open(s.rd + "/PILOT5_MANIFEST.json", "w")); s.approve()
        with s.assertRaises(AssertionError): s.go([ok()])
    def test19_dry_run_makes_no_call(s):
        def boom(*a): raise AssertionError("generation call in dry run")
        r = R.execute(s.rd, s.out, boom, dry_run=True); s.assertEqual(r["generation_calls"], 0); s.assertEqual(len(r["apps"]), 5); s.assertFalse(os.path.exists(s.out + "/state.json"))
    def test20_refuses_without_authorization(s):
        r, p = s.go([ok()], approve=False); s.assertEqual(r["stopped"], "refused_no_authorization"); s.assertEqual(p.times, [])
        s.approve(manifest_sha256="0" * 64); r, p = s.go([ok()]); s.assertEqual(r["stopped"], "refused_authorization_mismatch"); s.approve(max_requests=9); r, p = s.go([ok()]); s.assertEqual(r["stopped"], "refused_authorization_mismatch")
        s.assertFalse(json.load(open(HERE + "/PILOT5_MANIFEST.json"))["execution_authorized"])
    def test21_unreviewed_stop_blocks_restart(s):
        s.go([DAILY]); r, p = s.go([ok()]); s.assertEqual(r["stopped"], "refused_previous_stop_not_reviewed"); s.assertEqual(p.times, [])
    def test22_inflight_after_crash_requires_review(s):
        class Crash(BaseException): pass
        def crash(prompt, schema): raise Crash()
        s.approve()
        with s.assertRaises(Crash): R.execute(s.rd, s.out, crash, mono=s.clock.mono, wall=s.clock.wall, sleep=s.clock.sleep)
        s.assertEqual(s.state()["attempts_total"], 1); s.assertIsNotNone(s.state()["in_flight"]); r, p = s.go([ok()]); s.assertEqual(r["stopped"], "refused_in_flight_request_unknown_outcome"); s.assertEqual(p.times, [])
    def test23_classify_429(s):
        for b, e in (("GenerateRequestsPerDayPerProjectPerModel", "daily_quota"), ("Quota exceeded ... per day", "daily_quota"), ("InputTokensPerMinute", "rate_limit"), ("???", "ambiguous_429"), ("", "ambiguous_429")): s.assertEqual(R.classify_429(b), e)
if __name__ == "__main__": unittest.main(verbosity=2)

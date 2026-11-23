"""Offline tests for src/verify_v2.py (fake Groq functions only; no network). Fixtures come from the REAL baseline records and the old verifier's 8 false-positive 'contradicted' verdicts.
Run: python -I tests/test_verify_v2.py"""
import sys, os, json, glob, hashlib, tempfile, importlib.util, unittest, urllib.error
from unittest import mock
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "src")); import verify_v2 as V
B = lambda i: V.jload(f"baseline/p1_v1/pass1/{i}.json"); sh = lambda p: hashlib.sha256(V.rbytes(p)).hexdigest()
def fake_all_contradicted(msgs, budget):                       # adversarial: the model insists everything is contradicted, quoting the first sentence of the first passage
    txt = msgs[0]["content"]; items = json.loads(txt.split("ITEMS: ")[1].split("\n")[0]); first = txt.split("PASSAGES:\n")[1].split("\n")[0]; q = first.split(") ", 1)[1][:70]
    budget.used += 1; return {"items": [{"item": i, "verdict": "contradicted", "passage_id": "P1", "evidence_quote": q, "reason": "model says contradicted"} for i in items]}
class T(unittest.TestCase):
    def test_four_enum_semantics_false_positives(self):                         # HubSpot #2, Attio #4, Twilio #22, Paygent #84: rest listed together with sdk_or_cli_only
        for i in (2, 4, 22, 84):
            api = B(i)["api_types"]; self.assertIn("sdk_or_cli_only", api); self.assertIn("rest", api)
            pre = V.precheck_enum_conflict("api_types", api); self.assertIn("sdk_or_cli_only", pre, f"#{i}")
    def test_known_false_positives_guardrails(self):
        # Front #14: 'beta MCP server' does not contradict 'official' (no negation)
        q = "... and a beta MCP server; authentication is via Front API tokens or Front OAuth apps depending"; v, fl = V.apply_guardrails("existing_mcp", "official", "contradicted", q, "Excerpt describes MCP as beta, not official", [q]); self.assertEqual(v, "insufficient_evidence"); self.assertIn("no_explicit_negation_in_quote", fl)
        # Amazon #49: quote about OAuth/LWA says nothing about MCP
        q = "* **Authorization method:** OAuth 2.0 through Login with Amazon (LWA)."; v, fl = V.apply_guardrails("existing_mcp", "none_found", "contradicted", q, "Excerpt lists an OAuth 2.0 method, so 'none found' is false.", [q]); self.assertEqual(v, "insufficient_evidence"); self.assertIn("quote_not_about_item", fl)
        # WhatsApp #28: 'OAuth (not 2.0)' is version wording -> human, never an automatic contradiction
        q = "Authentication uses OAuth (not 2.0)"; v, fl = V.apply_guardrails("auth_methods", "oauth2", "contradicted", q, "Excerpt explicitly says OAuth 2.0 is not used", [q]); self.assertEqual(v, "ambiguous_needs_human"); self.assertIn("oauth_version_wording", fl)
    def test_twenty_access_lexical_coincidence_blocked(self):                 # adversarial survivor found during development: 'no' in a quote unrelated to access
        q = "## Schema-per-tenant APIs There is no static API reference for Twenty."; v, fl = V.apply_guardrails("access", "self_serve_free :: API keys can be generated in any workspace", "contradicted", q, "model says contradicted", [q]); self.assertEqual(v, "insufficient_evidence"); self.assertIn("quote_not_about_item", fl)
    def test_absence_is_not_contradiction(self):                                # archived prototype verdict on WhatsApp websocket
        q = "The Graph API is a REST API over HTTP."; v, fl = V.apply_guardrails("api_types", "websocket", "contradicted", q, "Excerpt mentions REST/HTTP Graph API only; no mention of a WebSocket API.", [q]); self.assertEqual(v, "insufficient_evidence"); self.assertIn("absence_not_contradiction", fl)
    def test_sherlock_none_required_is_schema_limitation(self):
        rec = V.load_record("baseline/p1_v1/pass1/58.json"); s = rec["surfaces"][0]; calls = []
        res = V.verify_surface(rec, s, lambda m, b: calls.append(1) or {"items": []}, V.Budget(10)); item = res["fields"]["auth_methods"][0]
        self.assertEqual((item["item"], item["verdict"], item.get("suggested_value")), ("unknown", "schema_limitation", "none_required")); self.assertFalse(item["model_called"])
    def test_positive_controls_still_contradicted(self):
        q = "The API does not support GraphQL."; self.assertEqual(V.apply_guardrails("api_types", "graphql", "contradicted", q, "explicit", [q])[0], "contradicted")
        q = "OAuth 2.0 is not supported; use API keys only."; self.assertEqual(V.apply_guardrails("auth_methods", "oauth2", "contradicted", q, "explicit", [q])[0], "contradicted")
        q = "There is no official MCP server for this product."; self.assertEqual(V.apply_guardrails("existing_mcp", "official", "contradicted", q, "explicit", [q])[0], "contradicted")
    def test_supported_requires_verbatim_quote(self):
        v, fl = V.apply_guardrails("api_types", "rest", "supported", "a made-up quote", "", ["Real passage text about the REST API."]); self.assertEqual(v, "insufficient_evidence"); self.assertIn("quote_not_verbatim_in_retrieved_passages", fl)
    def test_adversarial_model_cannot_create_false_contradictions(self):
        survivors = 0
        for i in (2, 4, 14, 22, 28, 49, 84, 1, 3, 5):
            rec = V.load_record(f"baseline/p1_v1/pass1/{i}.json"); res = V.verify_surface(rec, rec["surfaces"][0], fake_all_contradicted, V.Budget(100))
            for f, L in res["fields"].items():
                for x in L:
                    if x["verdict"] == "contradicted":
                        survivors += 1; self.assertTrue(V.re.search(V.ACCESS_ANCHOR if f == "access" else V.ANCHOR.get(f, {}).get(x["item"], "."), x["evidence_quote"], V.re.I) and V.NEG.search(x["evidence_quote"]), f"#{i} {f} {x['item']}")
                    self.assertNotEqual((f, x["item"], x["verdict"]), ("api_types", "sdk_or_cli_only", "contradicted"))
        print(f"   adversarial run: {survivors} contradictions survived the guardrails (each has an item-specific quote with explicit negation)")
    def test_independent_retrieval_not_limited_to_cited_quote(self):
        pages = {"https://x/a": "The service offers a REST API for customers. " * 3 + "Setup steps follow.", "https://x/b": "Important: this product has no official MCP server, only community projects exist. Other text. " + "Filler sentence about billing. " * 8}
        ps = V.passages(pages); top = V.retrieve(V.query_terms("existing_mcp", "official"), ps, 3); self.assertTrue(any(p["url"] == "https://x/b" for p in top))
        cited_quote = "The service offers a REST API for customers."; self.assertFalse(any(V.norm(cited_quote)[:60] in V.norm(p["text"]) for p in top if p["url"] == "https://x/b"))
    def test_shapes_frozen_nested_neo4j(self):
        fr = V.load_record("baseline/p1_v1/pass1/4.json"); ne = V.load_record("runs/schema-proposal-v1-20261124/examples/migrated_baseline_record_4.json"); self.assertEqual((fr["shape"], ne["shape"]), ("frozen_single_surface", "nested"))
        items = lambda r: {(f, i) for f in V.EVIDENCE_FIELDS for i in V.items_for(r["surfaces"][0], f)}; self.assertEqual(items(fr), items(ne))
        ns = V.load_record("runs/schema-proposal-v1-20261124/examples/neo4j_two_surface_example_HAND_ASSESSED.json"); self.assertEqual([s["surface_id"] for s in ns["surfaces"]], ["aura_management_api", "database_query_api"])
    def test_isolated_neo4j_surfaces_and_writable_paths(self):
        spec = importlib.util.spec_from_file_location("rn", ROOT + "/src/run_neo4j_surfaces.py"); N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N); R = N.R
        schema, prompt, hs, hp = R.frozen(); D = V.jload("baseline/data/apps.json"); plan = V.jload("runs/p1-neo4j-optionB-20261124/PLAN.json"); tmp = tempfile.mkdtemp()
        fake = lambda m, p, s: ("ok", {"one_liner": "F", "auth_methods": ["unknown"], "access": "unknown", "access_note": "", "api_types": ["rest"], "api_breadth": "unknown", "existing_mcp": "unknown", "buildability": "unknown", "blocker": "", "evidence": []})
        N.run(plan, {"models": ["m"], "cap_per_model": {"m": 5}}, tmp, fake, schema, prompt, (hs, hp), D["categories"], sleep=lambda s: None)
        a = V.load_record(f"{tmp}/pass1/66__aura_management_api.json"); q = V.load_record(f"{tmp}/pass1/66__database_query_api.json"); sa = V.load_sources(a, a["surfaces"][0]); sq = V.load_sources(q, q["surfaces"][0])
        self.assertEqual((len(sa), len(sq)), (4, 1)); self.assertFalse(set(sa) & set(sq)); self.assertTrue(all("aura" in u for u in sa) and all("query-api" in u for u in sq))
        base_f = "baseline/p1_v1/pass1/4.json"; before = sh(base_f); out = tempfile.mkdtemp(); calls = []
        r = V.verify_record(base_f, out, lambda m, b: (calls.append(1), b.__setattr__("used", b.used + 1), {"items": []})[2], V.Budget(50)); self.assertTrue(r["complete"]); self.assertTrue(os.path.exists(f"{out}/4.json")); self.assertEqual(before, sh(base_f))
        n = len(calls); V.verify_record(base_f, out, lambda m, b: self.fail("resume must not call the model again"), V.Budget(50)); self.assertEqual(n, len(calls))
        for bad in ("baseline/x", "work/x"):
            with mock.patch.object(sys, "argv", ["v", "--out", bad, "--records", "baseline/p1_v1/pass1/4.json", "--dry-run"]):
                with self.assertRaises(AssertionError): V.main()
    def test_quota_budget_and_no_key_rotation(self):
        b = V.Budget(2); calls = []
        def fake(m, bud): calls.append(1); bud.used += 1; 
        def capped(m, bud):
            if bud.used >= bud.n: bud.stopped = "max_calls_reached"; raise V.QuotaStop("x")
            bud.used += 1; return {"items": []}
        out = tempfile.mkdtemp(); r = V.verify_record("baseline/p1_v1/pass1/1.json", out, capped, b); self.assertFalse(r["complete"]); self.assertEqual(r.get("stopped"), "max_calls_reached"); self.assertLessEqual(b.used, 2)
        err = urllib.error.HTTPError("u", 429, "rate", {"retry-after": "1"}, None); bud = V.Budget(50)
        with mock.patch.object(V.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(V.QuotaStop): V.groq_call([{"role": "user", "content": "x"}], bud, "k", sleep=lambda s: None)
        self.assertEqual((bud.used, bud.stopped), (5, "retries_exhausted"))
        src = V.rbytes("src/verify_v2.py").decode(); self.assertNotIn("GEMINI", src); self.assertNotIn("KEY_2", src); self.assertIn('startswith("GROQ_API_KEY=")', src)
    def test_cross_checks(self):
        self.assertIn("buildability_yes_but_access_is_no_public_api", V.cross_checks({"buildability": "yes", "access": "no_public_api"}, {}))
        self.assertTrue(any(c.startswith("api_breadth_broad_but_only_0") for c in V.cross_checks({"api_breadth": "broad"}, {"u": "no endpoints here"})))
if __name__ == "__main__": unittest.main(verbosity=1)

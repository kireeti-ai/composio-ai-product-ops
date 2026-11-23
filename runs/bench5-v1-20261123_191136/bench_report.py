"""Capability report + benchmark comparison/report (pure functions over files written by bench.py). No network except capability()'s public OpenRouter model list."""
import os, json, glob, time, csv, urllib.request
import bench as Bn
iso = Bn.iso
def capability(H):
    ROOT = Bn.ROOT; pr = json.load(open(sorted(glob.glob(f"{ROOT}/runs/quota-probe-v2-*/probe.json"))[-1])); models = json.load(urllib.request.urlopen(urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"user-agent": "research-agent/0.1"}), timeout=30))["data"]
    ids = Bn.or_text_models(models); ctx = {m["id"]: m.get("context_length") for m in models}
    rep = dict(created=iso(), basis="probe v2 (live 1-request generation tests, 2026-11-23) + live public OpenRouter /models list; nothing here is inferred from models.list alone",
      gemini=pr["gemini"], groq={k: dict(ok=v["ok"], context_window=v["context_window"], ratelimit={a: b for a, b in v["ratelimit_headers"].items()}) for k, v in pr["groq"].items()},
      groq_buckets="existing key + P1 share one counter (972 vs 973 remaining); P2, P3, P4 each showed a fresh counter (999) => observed separate; ownership/terms for P2-P4 must be confirmed by the user",
      openrouter=dict(free_text_models_total=len(ids), free_text_models_ctx_ge_32k=len([i for i in ids if (ctx[i] or 0) >= 32000]), selected="particle-ai/particle-1:free (generation verified)", excluded_examples=[m["id"] for m in models if m["id"] not in ids and float(m.get("pricing", {}).get("prompt", 1)) == 0][:10], key_free_limit=pr["openrouter"]["key_info"].get("free_model_daily_requests") if isinstance(pr["openrouter"]["key_info"], dict) else None, generation_tests=pr["openrouter"]["generation_tests"]),
      known_unknowns=["Groq daily TOKEN limit not exposed by headers", "Groq/OpenRouter RPM not observed (conservative assumptions used)", "Gemini remaining daily quota unknown; Key1 2.5 returned 429; 3.6 timed out on both keys"])
    Bn.atomic(f"{H}/reports/PROVIDER_CAPABILITY_REPORT.json", rep); print("capability report written")
def load_results(H):
    R = {}
    for tag in Bn.PROVIDERS:
        for i, n in Bn.APPS:
            p = f"{H}/outputs/{tag}/{i}.json"
            if os.path.exists(p): R.setdefault(tag, {})[i] = json.load(open(p))
    return R
def jac(a, b): a, b = set(a), set(b); return 1.0 if not a and not b else len(a & b) / len(a | b)
def metrics(res):
    ok = [r for r in res.values() if r["status"] == "ok"]; ev = [e for r in ok for e in r["output"]["evidence"]]; unk = lambda o: sum([o["auth_methods"] == ["unknown"], o["access"] == "unknown", o["api_types"] == ["unknown"], o["api_breadth"] == "unknown", o["existing_mcp"] == "unknown", o["buildability"] == "unknown"])
    return dict(apps_returned=len(res), schema_valid=len(ok), evidence_items=len(ev), quote_verbatim_in_shown_evidence=sum(e["quote_found"] for e in ev), url_in_sources=sum(e["url_in_sources"] for e in ev), claim_fields_without_verified_quote=sum(len(r["unsupported_claim_fields"]) for r in ok), unknown_fields_total=sum(unk(r["output"]) for r in ok),
                mean_latency_s=round(sum(r["latency_s"] for r in ok) / len(ok), 1) if ok else None, tokens_in=sum(r["tokens_in"] or 0 for r in res.values()), tokens_out=sum(r["tokens_out"] or 0 for r in res.values()), cost_usd=sum(float(r["cost_usd"]) for r in res.values()))
def report(H):
    R = load_results(H); failed = [json.load(open(p)) for p in sorted(glob.glob(f"{H}/outputs/*/failed_*.json"))]; M = {t: metrics(r) for t, r in R.items()}; q = json.load(open(f"{H}/quota.json")) if os.path.exists(f"{H}/quota.json") else {}; now = time.time()
    agree = {}; tags = list(R)
    for ai in range(len(tags)):
        for bi in range(ai + 1, len(tags)):
            a, b = tags[ai], tags[bi]; rows = []
            for i, _ in Bn.APPS:
                if i in R[a] and i in R[b] and R[a][i]["status"] == "ok" and R[b][i]["status"] == "ok":
                    x, y = R[a][i]["output"], R[b][i]["output"]; rows.append(dict(app=i, auth_methods_jaccard=round(jac(x["auth_methods"], y["auth_methods"]), 2), api_types_jaccard=round(jac(x["api_types"], y["api_types"]), 2), **{f: x[f] == y[f] for f in ("access", "api_breadth", "existing_mcp", "buildability")}))
            agree[f"{a} vs {b}"] = rows
    with open(f"{H}/reports/review_aid_side_by_side.csv", "w", newline="") as fh:     # for INDEPENDENT human labelling; no verdict column pre-filled
        w = csv.writer(fh); w.writerow(["app_id", "app", "provenance_class", "provider_tag", "model", "field", "value", "evidence_quote", "quote_verbatim_in_shown_evidence", "human_label(correct|incorrect|unsupported|cannot_tell)", "labeler"])
        for t, rs in R.items():
            for i, r in rs.items():
                if r["status"] != "ok": continue
                o = r["output"]
                for f in ("auth_methods", "access", "api_types", "api_breadth", "existing_mcp", "buildability", "blocker"):
                    qs = [e for e in o["evidence"] if e["field"] == f]; w.writerow([i, r["name"], "original_notion" if i <= 50 else "reconstructed_unverified", t, r["model_returned"] or r["model"], f, json.dumps(o[f]), " | ".join(e["quote"] for e in qs), " | ".join(str(e["quote_found"]) for e in qs), "", ""])
    qr = {k: dict(requests_last_24h=len([t for t in v["req"] if now - t < 86400]), tokens_last_60s=sum(e[1] for e in v["tok"] if now - e[0] < 60), blocked_until=Bn.iso(v["blocked_until"]) if v["blocked_until"] > now else None, blocked_reason=v["blocked_reason"] if v["blocked_until"] > now else None, observations=v["observations"][-5:]) for k, v in q.items()}
    Bn.atomic(f"{H}/reports/QUOTA_USAGE_REPORT.json", dict(created=iso(), buckets=qr, caps={t: c["cap"] for t, c in Bn.PROVIDERS.items()})); Bn.atomic(f"{H}/reports/FAILED_REQUESTS.json", failed)
    rank = sorted(M, key=lambda t: (-M[t]["schema_valid"], M[t]["claim_fields_without_verified_quote"], -(M[t]["quote_verbatim_in_shown_evidence"] / max(1, M[t]["evidence_items"])), M[t]["mean_latency_s"] or 1e9))
    S = dict(created=iso(), caveat="STRUCTURAL/automatic measures only (schema, verbatim quotes, unknown rates, latency). NO accuracy claim: there is no independent human-labelled ground truth. Use review_aid_side_by_side.csv for labelling.", metrics=M, agreement_between_providers=agree, failed_requests=len(failed), ranking_by_structural_measures=rank,
             ranking_rule="schema-valid apps (desc), claim fields lacking a verified quote (asc), verbatim-quote rate (desc), latency (asc)", not_run=[t for t in Bn.PROVIDERS if t not in R])
    Bn.atomic(f"{H}/BENCHMARK_SUMMARY.json", S)
    L = ["# Benchmark summary (5 apps; pipeline/model evaluation, NOT an accuracy claim)", "", S["caveat"], "", "| provider tag | model | apps valid/returned | verbatim quotes / evidence | claim fields w/o verified quote | unknown fields | mean latency s | tokens in/out | cost USD |", "|---|---|---|---|---|---|---|---|---|"]
    for t in rank: m = M[t]; L.append(f"| {t} | {Bn.PROVIDERS[t]['model']} | {m['schema_valid']}/{m['apps_returned']} | {m['quote_verbatim_in_shown_evidence']}/{m['evidence_items']} | {m['claim_fields_without_verified_quote']} | {m['unknown_fields_total']} | {m['mean_latency_s']} | {m['tokens_in']}/{m['tokens_out']} | {m['cost_usd']} |")
    L += ["", f"Not run / deferred: {', '.join(S['not_run']) or 'none'}", f"Failed requests recorded: {len(failed)}", "", "## Pairwise agreement (same apps, same evidence)"]
    for k, rows in agree.items(): L.append(f"- {k}: " + (", ".join(f"#{r['app']}: access={r['access']}, mcp={r['existing_mcp']}, build={r['buildability']}, auth J={r['auth_methods_jaccard']}, api J={r['api_types_jaccard']}" for r in rows) or "no comparable apps"))
    open(f"{H}/BENCHMARK_SUMMARY.md", "w").write("\n".join(L) + "\n"); print("\n".join(L))

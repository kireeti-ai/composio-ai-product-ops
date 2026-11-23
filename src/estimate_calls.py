"""Model-call estimate for completing all 100 apps. Offline. Inputs: master coverage + expansion plan + observed Groq retry ratio in baseline logs + measured verifier prompt sizes (fake model, no network).
Every assumption is labelled; hypothetical quota caps are SCENARIOS, not data. Writes runs/readiness-v2-20261124/CALL_ESTIMATE.json and .md"""
import os, sys, json, math, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); import verify_v2 as V
M = json.load(open("runs/master-coverage-v1-20261124/MASTER_COVERAGE.json")); X = json.load(open("runs/p1-expansion-v1-20261124/PLAN.json")); cnt = M["counts"]; waves = collections.Counter(a["wave"] for a in X["apps"])
v1f = cnt["PLANNED_FROZEN_V1F"]; neo = 2; w3 = waves["3A_core_ready_access_topup"] + waves["3B_partial_targeted_reretrieval"] + waves["4_no_retrieval_full_discovery"]; gated = cnt["HELD_IDENTITY_PROVISIONAL"] + cnt["EXCLUDED_IDENTITY_UNRESOLVED"] + waves["3H_provisional_identity_hold"]
mand = dict(v1f_targets=v1f, neo4j_two_surface_calls=neo, expansion_waves_3A_3B_4=w3, identity_gated_after_confirmation=gated); gem_min = sum(mand.values()); optional = dict(reextract_quarantined_or_weak_baseline_58_14=2, corrected_pass_for_20pct_of_new_records=math.ceil(.2 * gem_min))
RETRY = 1.15; MAXA = 3                                                   # ASSUMPTION: 15% transient retries; runner allows 3 attempts per model per app (6 with two models)
gem = dict(minimum=gem_min, expected_with_15pct_retries=math.ceil(gem_min * RETRY), worst_case_3_attempts=gem_min * MAXA, worst_case_both_models_6_attempts=gem_min * 6, with_optional=gem_min + sum(optional.values()))
# Groq: records to verify (surface-records) x 4 field calls (planned after shortcuts measured on baseline: 103/26)
rec_new = v1f + neo + w3 + gated; per_rec = 103 / 26; baseline_reverify = 26
logs = [json.loads(l) for l in open("baseline/p1_v1/logs/verify_log.jsonl")]; r_obs = sum(1 for e in logs if e.get("ev") == "groq_retry"); ver_done = sum(1 for e in logs if e.get("ev") == "verified")
base_calls_old = 26 * 4; retry_ratio = 1 + r_obs / base_calls_old
grq_min = math.ceil(rec_new * per_rec) + math.ceil(baseline_reverify * per_rec)
# measure real prompt sizes (fake model; no network)
sizes = []
def cap(msgs, b): sizes.append(len(msgs[0]["content"])); b.used += 1; return {"items": []}
for i in range(1, 51):
    p = f"baseline/p1_v1/pass1/{i}.json"
    if os.path.exists(p): r = V.load_record(p); V.verify_surface(r, r["surfaces"][0], cap, V.Budget(999))
avg_chars = sum(sizes) / len(sizes); tok_in = avg_chars / 4; tok_out = 150; tok_per_call = tok_in + tok_out
grq = dict(records_to_verify_new=rec_new, baseline_reverify=baseline_reverify, per_record_calls=round(per_rec, 2), minimum=grq_min, observed_retry_ratio_in_baseline_logs=round(retry_ratio, 2), expected_attempts=math.ceil(grq_min * retry_ratio), worst_case_5_attempts=grq_min * 5,
           avg_prompt_chars_measured=round(avg_chars), est_tokens_per_call=round(tok_per_call), est_total_tokens_expected=round(math.ceil(grq_min * retry_ratio) * tok_per_call))
comp_min = sum(a["est_free_composio_calls"] for a in X["apps"]) + gated * 11 - sum(a["est_free_composio_calls"] for a in X["apps"] if a["wave"].startswith("3H")) + 5
comp = dict(estimated_minimum=comp_min, with_50pct_retries=math.ceil(comp_min * 1.5), cost_usd=0.0, note="free TinyFish via Composio; instant_charge asserted 0 on every call; includes 5 Neo4j gap fetches (need approval)")
def days(calls, models, cap): return math.ceil(calls / (models * cap))
sc = {}
for c in (20, 50, 100, 250): sc[f"cap_{c}_per_model_per_day"] = {f"models_{m}": dict(min=days(gem["minimum"], m, c), expected=days(gem["expected_with_15pct_retries"], m, c), worst_3x=days(gem["worst_case_3_attempts"], m, c)) for m in (1, 2)}
tk = {f"hypothetical_{t // 1000}k_tokens_per_day": days(grq["est_total_tokens_expected"], 1, t) for t in (100_000, 250_000, 500_000, 1_000_000)}
human = dict(claims_scored=252, label_rows_two_labelers=504, calibration_rows_two_labelers=42, adjudication="only disagreements queued")
res = dict(created=time.strftime("%Y-%m-%dT%H:%M:%S%z"), apps=100, status_counts=cnt, gemini_extraction=dict(mandatory=mand, optional=optional, calls=gem), groq_verification=grq, composio_free_retrieval=comp, days_needed_gemini_by_daily_cap_scenario=sc, days_needed_groq_by_token_cap_scenario=tk, human_labelling=human,
           assumptions=["transient retry rate 15% for Gemini is an ASSUMPTION to be replaced by the first run's observed ratio", "daily caps are SCENARIOS: active Gemini/Groq limits are unverified (last observed: 20 requests/day on one Gemini model for one project)", "Groq retry ratio is OBSERVED from the baseline verify log", "one Gemini call per app (frozen prompt/schema); Neo4j = 2 calls", "apps in wave 3H and identity-gated apps need user identity confirmation first"],
           not_counted=["calls for apps whose retrieval turns out unusable (they would be dropped, lowering the count)", "any schema change (would require re-extraction)", "second labeler or adjudicator tooling"])
json.dump(res, open("runs/readiness-v2-20261124/CALL_ESTIMATE.json", "w"), indent=1)
print("Gemini extraction calls:", gem); print("mandatory breakdown:", mand); print("Groq:", grq); print("Composio free:", comp); print("Gemini days (2 models):", {k: v["models_2"] for k, v in sc.items()}); print("Gemini days (1 model):", {k: v["models_1"] for k, v in sc.items()}); print("Groq days by hypothetical token cap:", tk)

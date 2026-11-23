"""Turns the limits YOU observe (blank templates in runs/quota-checks-v1-20261124/) into per-model caps, pacing flags and days needed. Pure + offline. It REFUSES blank or invalid values (no guessing) and never writes an
APPROVED*.json file: its output is a SUGGESTION to copy into an approval you make. Safety margin 10%. Usage: python src/quota_plan.py gemini LIMITS.json | groq LIMITS.json"""
import json, math, sys
SAFETY = .9; RUNNER_PEAK_RPM = 15            # the frozen Gemini runner is sequential; ~4 s per fast call => at most ~15 requests/min
STATS = dict(avg_tokens_in=8500, max_tokens_in=17500, out_tokens=1000, groq_tokens_per_call=982)   # MEASURED prompt sizes (chars/4) of the 28 v1f calls; Groq per-call size measured on 26 baseline records
def need(v, name):
    if not isinstance(v, int) or isinstance(v, bool) or v < 0: raise ValueError(f"'{name}' must be a non-negative integer observed from the dashboard (got {v!r}); blank values are refused")
    return v
def gemini_plan(lim, calls_needed=(("phase1", 15), ("phase2", 13), ("neo4j", 2), ("expansion_39", 39), ("identity_gated_6", 6)), retry=1.15):
    if lim.get("tier") not in ("free", "paid"): raise ValueError("tier must be 'free' or 'paid'")
    out = dict(models={}, notes=[]); total_cap = 0
    for m, d in lim["models"].items():
        if not d.get("available_to_project"): out["models"][m] = dict(usable=False, reason="not available to this project (confirm in AI Studio)"); continue
        rpd, used, rpm, tpm = need(d["rpd"], f"{m}.rpd"), need(d["used_today"], f"{m}.used_today"), need(d["rpm"], f"{m}.rpm"), need(d["tpm"], f"{m}.tpm"); cap = math.floor(SAFETY * max(0, rpd - used)); total_cap += cap
        flags = []
        if rpm < RUNNER_PEAK_RPM: flags.append(f"RPM {rpm} < runner peak {RUNNER_PEAK_RPM}: the frozen runner has no pacing -> a paced runner version is needed before approval")
        if tpm < RUNNER_PEAK_RPM * STATS["avg_tokens_in"]: flags.append(f"TPM {tpm} < {RUNNER_PEAK_RPM}x{STATS['avg_tokens_in']} (avg prompt) at peak rate: risk of per-minute 429s (they are retried, each attempt counts)")
        if tpm < STATS["max_tokens_in"] + STATS["out_tokens"]: flags.append(f"TPM {tpm} cannot even fit the largest single call ({STATS['max_tokens_in'] + STATS['out_tokens']} tokens): NO-GO for this model")
        out["models"][m] = dict(usable=not any("NO-GO" in f for f in flags), suggested_cap_per_model=cap, rpd_remaining=max(0, rpd - used), flags=flags)
    out["total_suggested_cap_today"] = sum(v.get("suggested_cap_per_model", 0) for v in out["models"].values() if v.get("usable")); days = {}
    for name, n in calls_needed: days[name] = dict(min_calls=n, attempts_with_15pct_retries=math.ceil(n * retry), days_at_today_cap=(math.ceil(math.ceil(n * retry) / out["total_suggested_cap_today"]) if out["total_suggested_cap_today"] else None))
    out["phases"] = days; out["NOT_AN_APPROVAL"] = "copy caps into runs/<plan>/APPROVED.json yourself only after you approve; this tool never writes one"; return out
def groq_plan(lim, planned_calls=411, expected_ratio=1.71):   # 411 = 99 actual baseline + 300 new-record estimate + 12 planted controls (groq-call-reconciliation-v2); the old default 431 double counted
    rpm, rpd, tpm, tpd, ur, ut = (need(lim[k], k) for k in ("rpm", "rpd", "tpm", "tpd", "used_requests_today", "used_tokens_today")); tok = STATS["groq_tokens_per_call"]
    by_req = max(0, rpd - ur); by_tok = max(0, (tpd - ut)) // tok; cap = math.floor(SAFETY * min(by_req, by_tok)); interval = max(60 / rpm if rpm else 0, tok * 60 / tpm if tpm else 0)
    attempts = math.ceil(planned_calls * expected_ratio)
    return dict(suggested_max_calls_today=cap, limiting_factor=("requests/day" if by_req <= by_tok else "tokens/day"), suggested_min_interval_s=round(interval, 2), planned_calls=planned_calls, expected_attempts=attempts, days_needed=(math.ceil(attempts / cap) if cap else None), NOT_AN_APPROVAL="copy into APPROVED_PASS2*.json yourself; max_calls must count ATTEMPTS")
if __name__ == "__main__":
    kind, path = sys.argv[1], sys.argv[2]; lim = json.load(open(path)); print(json.dumps(gemini_plan(lim) if kind == "gemini" else groq_plan(lim), indent=1))

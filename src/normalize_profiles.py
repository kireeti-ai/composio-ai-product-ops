"""Normalise the 46 source-quoted records into the first-pass enums so findings can be computed over all 100 positions.
Deterministic rules + an explicit access table (judgements, listed here so they are auditable). Adds manual_research.profile; nothing else changes.
Usage: python3 src/normalize_profiles.py <in DATASET.json> <out_dir>   (refuses a non-empty out_dir)"""
import json, os, re, sys, time
S, F, G, P, U, N = "self_serve_free", "self_serve_trial_or_paid_plan", "approval_or_review_required", "partner_or_contact_sales", "unknown", "no_public_api"
# access judgement per position: first-pass enum semantics (self_serve_free = self-serve with no paid plan stated)
ACCESS = {15: F, 24: G, 31: G, 37: S, 40: S, 42: S, 45: S, 48: S, 50: U, 54: S, 55: S, 57: S, 58: N, 59: P, 60: F, 64: U, 66: S, 67: F, 68: U, 69: F, 71: S, 73: S, 74: U, 77: S,
          78: U, 79: U, 80: S, 81: S, 82: G, 83: U, 85: S, 86: S, 87: F, 88: F, 89: F, 90: U, 91: F, 92: P, 93: S, 94: F, 95: S, 96: F, 97: F, 98: N, 99: S, 100: S}
MCP = {"official": "official", "third_party": "community", "community": "community", "none_found_in_reviewed_sources": "none_found", "not_verified": "unknown"}
BUILD = {"yes": "yes", "conditional": "yes_with_caveats", "unknown": "unknown", "no": "no"}
def auth(items, app_id):
    out = set()
    for it in items:
        s = it.lower()
        if "mcp" in s or s.strip() in ("unknown", ""): continue
        if "oauth" in s and "oauth1" not in s.replace(" ", ""): out.add("oauth2")
        if "oauth1" in s: out.add("other")
        if re.search(r"bearer", s): out.add("bearer_token")
        if re.search(r"basic", s): out.add("basic")
        if re.search(r"hmac|rsa|ed25519|jwt|key_pair|keypair|signed", s): out.add("jwt_or_signed")
        if "oauth" not in s and re.search(r"api[_ ]?key|api[_ ]?token|access[_ ]?token|personal_access|key_id|client_id\+secret|secret_api|user_token|service_user|x-api|consumer key|application_password|app_id", s): out.add("api_key")
    if app_id == 98: out = {"none_required"}
    return sorted(out)
def api(items):
    out = set(); t = " ".join(items).lower()
    if re.search(r"\brest\b", t.replace("(unverified)", "")) and "rest (unverified)" not in t: out.add("rest")
    if "rest (" in t and "unverified" not in t: out.add("rest")
    for k in ("graphql", "soap", "websocket"):
        if k in t: out.add(k)
    if "cli" in t and not out and "unknown" not in t: out.add("sdk_or_cli_only")
    if "grpc" in t or "sql_api" in t or "https_cypher" in t: out.add("other")
    return sorted(out)
def build(d, out_dir):
    if os.path.isdir(out_dir) and os.listdir(out_dir): raise SystemExit("refusing non-empty out_dir")
    os.makedirs(out_dir, exist_ok=True); n = 0
    for r in d["rows"]:
        m = r.get("manual_research")
        if not m or r["primary_version"]: continue
        for c in m["claims"]: c["verdict"] = {"researcher_judgement_from_quoted_facts": "judgement_from_quoted_facts"}.get(c["verdict"], c["verdict"])
        i, s = r["registry_id"], m["summary"]; sup = {c["field"] for c in m["claims"] if c["verdict"] in ("supported_by_official_quote", "partially_supported")}   # a reproduced official quotation covers the core statement
        has = lambda *k: any(any(x in f for x in k) for f in sup)
        blocker = str(s.get("blocker") or "")
        m["profile"] = {"access": ACCESS[i], "mcp": MCP.get(s.get("mcp_status"), "unknown"), "buildability": BUILD.get(s.get("buildability"), "unknown"), "auth": auth(s.get("auth_methods", []), i), "api_types": api(s.get("api_types", [])),
                        "blocker": "none" if blocker.lower().startswith("none") and ";" not in blocker else blocker, "quoted": {"access": has("access"), "auth": has("authentication"), "mcp": has("mcp"), "api_types": has("api_types")},
                        "basis": "model-normalised from source-quoted claims; access class is a judgement (src/normalize_profiles.py)"}
        n += 1
    d["created"] = time.strftime("%Y-%m-%dT%H:%M:%S%z"); d["note"] += " | v8: adds manual_research.profile (normalised enums) for 46 positions"
    json.dump(d, open(f"{out_dir}/DATASET.json", "w"), indent=1); return n
if __name__ == "__main__": print(build(json.load(open(sys.argv[1])), sys.argv[2]), "profiles")

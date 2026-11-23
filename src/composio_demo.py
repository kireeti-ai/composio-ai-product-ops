"""Composio integration proof. Runs real calls and records every outcome (success, auth failure, unavailable) - nothing is simulated.
Usage: python3 src/composio_demo.py <out_dir>   (needs COMPOSIO_API_KEY in .env; no paid tool is executed; key is never written to output)
Steps: S1 installed SDK surface + SDK auth attempt; S2 Composio Connect MCP tools/list; S3 tool discovery; S4 schema inspection;
S5 execute GITHUB_LIST_ORGANIZATION_REPOSITORIES (expected to need a GitHub connection); S6 execute GETANYAPI_GET_API_CONTRACT (read-only price/contract lookup, not a paid run); S7 trivial Composio remote-sandbox command."""
import os, sys, json, time, warnings, importlib.metadata as md
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/src")
warnings.filterwarnings("ignore")
for ln in open(f"{ROOT}/.env"):
    if ln.startswith("COMPOSIO_API_KEY="): os.environ["COMPOSIO_API_KEY"] = ln.split("=", 1)[1].strip()
KEY = os.environ["COMPOSIO_API_KEY"]
scrub = lambda s: str(s).replace(KEY, "<key>")
out = sys.argv[1]; os.makedirs(out, exist_ok=False)
R = {"run_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "key_prefix": KEY.split("_")[0] + "_", "steps": []}
def step(name, fn, layer):
    t = time.time()
    try:
        r = fn(); ok = not (isinstance(r, dict) and r.get("successful") is False)   # tool-level failure inside a successful transport call
        res = {"step": name, "status": "ok" if ok else "tool_call_failed", "result": r}
    except Exception as e: res = {"step": name, "status": "error", "error_type": type(e).__name__, "error": scrub(e)[:600]}
    res["layer"] = layer; res["seconds"] = round(time.time() - t, 2); R["steps"].append(res); print(name, res["status"], (res.get("error") or json.dumps(res.get("result", ""))[:160])[:160])
def s1():
    import composio; from composio import Composio
    c = Composio(api_key=KEY); info = {"composio_version": md.version("composio"), "client_attrs": [a for a in dir(c) if not a.startswith("_")], "tools_methods": [a for a in dir(c.tools) if not a.startswith("_")]}
    try: c.toolkits.get(slug="github"); info["sdk_toolkits_get"] = "ok"
    except Exception as e: info["sdk_toolkits_get"] = f"{type(e).__name__}: {scrub(e)[:200]}"
    return info
step("S1_sdk_surface_and_auth", s1, "sdk")
from mcp import MCP
holder = {}
def s2():
    holder["c"] = MCP(); t = holder["c"].tools(); holder["t"] = {x["name"]: x for x in t}
    return [{"name": x["name"], "required": (x.get("inputSchema") or {}).get("required"), "params": list((x.get("inputSchema") or {}).get("properties", {}))} for x in t]
step("S2_mcp_tools_list", s2, "mcp_infrastructure")
def call(name, args): return json.loads(holder["c"].call(name, args)["content"][0]["text"])
def s3():
    d = call("COMPOSIO_SEARCH_TOOLS", {"queries": [{"use_case": "list public GitHub repositories of an organization"}], "session": {"generate_id": True}})["data"]
    holder["session"] = d.get("session", {}).get("id") if isinstance(d.get("session"), dict) else None
    return {"results": d["results"], "connection_status": [{k: v for k, v in t.items() if k in ("toolkit", "has_active_connection", "status_message")} for t in d["toolkit_connection_statuses"]]}
step("S3_search_tools", s3, "mcp_infrastructure")
def s4():
    d = call("COMPOSIO_GET_TOOL_SCHEMAS", {"tool_slugs": ["GITHUB_LIST_ORGANIZATION_REPOSITORIES", "GETANYAPI_GET_API_CONTRACT"], "session_id": holder.get("session") or "demo"})["data"]["tool_schemas"]
    return {k: {"description": v["description"][:300], "required": v["input_schema"].get("required"), "properties": list(v["input_schema"]["properties"])} for k, v in d.items()}
step("S4_get_tool_schemas", s4, "mcp_infrastructure")
def ex(slug, args): return call("COMPOSIO_MULTI_EXECUTE_TOOL", {"tools": [{"tool_slug": slug, "arguments": args}], "thought": "reproducible integration demo", "sync_response_to_workbench": False, "current_step": "DEMO", "current_step_metric": "1/1", "session_id": holder.get("session") or "demo"})
def s8():
    k = os.environ.get("COMPOSIO_SDK_API_KEY")
    if not k: raise RuntimeError("skipped: COMPOSIO_SDK_API_KEY not set (SDK project key required)")
    from composio import Composio
    r = Composio(api_key=k).tools.execute("GITHUB_LIST_ORGANIZATION_REPOSITORIES", {"org": "ComposioHQ", "per_page": 3}, user_id=os.environ.get("COMPOSIO_USER_ID", "default"))
    return {"successful": bool(r.get("successful")), "error": r.get("error"), "data": json.dumps(r.get("data"))[:1500]}
def ex_bash(): return call("COMPOSIO_REMOTE_BASH_TOOL", {"command": "python3 -c \"print(2+2)\"", "session_id": holder.get("session") or "demo"})
step("S5_execute_github_list_org_repos", lambda: ex("GITHUB_LIST_ORGANIZATION_REPOSITORIES", {"org": "ComposioHQ", "per_page": 3}), "app_toolkit")
step("S6_execute_getanyapi_get_api_contract", lambda: ex("GETANYAPI_GET_API_CONTRACT", {"sku": "hackernews.story"}), "app_toolkit")
step("S7_execute_composio_remote_bash (Composio meta-tool, not an app toolkit)", lambda: ex_bash(), "mcp_infrastructure")
step("S8_sdk_execute_github_list_org_repos", s8, "app_toolkit")
R["summary"] = {"app_toolkit_calls_succeeded": sum(1 for x in R["steps"] if x["layer"] == "app_toolkit" and x["status"] == "ok"), "app_toolkit_calls_attempted": sum(1 for x in R["steps"] if x["layer"] == "app_toolkit" and not str(x.get("error", "")).startswith("skipped")), "app_toolkit_calls_skipped": sum(1 for x in R["steps"] if str(x.get("error", "")).startswith("skipped")), "sdk_authenticated": R["steps"][0].get("result", {}).get("sdk_toolkits_get") == "ok", "mcp_infrastructure_calls_succeeded": sum(1 for x in R["steps"] if x["layer"] == "mcp_infrastructure" and x["status"] == "ok"), "mcp_infrastructure_calls_attempted": sum(1 for x in R["steps"] if x["layer"] == "mcp_infrastructure"), "note": ("" if any(x["layer"] == "app_toolkit" and x["status"] == "ok" for x in R["steps"]) else "No application-toolkit operation succeeded. GitHub needs an interactive OAuth connection (COMPOSIO_MANAGE_CONNECTIONS) that the account owner must approve; the GetAnyAPI instant account does not expose the contract tool and its other tools are paid.")}
json.dump(R, open(f"{out}/DEMO_RESULT.json", "w"), indent=1, default=str); print("saved", out)

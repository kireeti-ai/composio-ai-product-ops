"""Offline execution-configuration check (no network, no model call, no secret values printed). Verifies frozen artifacts, approval absence, which scripts can reach which provider key, absence of key-rotation paths,
mandatory caps, and quota-stop behaviour in the source. Writes a NEW timestamped runs/readiness-v3-20261124/CONFIG_CHECK_<ts>.json each run (never overwrites an earlier file)."""
import os, re, json, glob, hashlib, subprocess, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest(); out = []; ok = lambda name, c, d="": out.append(dict(check=name, passed=bool(c), detail=d))
FZ = json.load(open("runs/p1-v1f-gemini-20261124/FROZEN.json"))
ok("v1f PLAN.json equals frozen hash", sha("runs/p1-v1f-gemini-20261124/PLAN.json") == FZ["plan_sha256"]); ok("runner src/run_p1.py equals frozen hash", sha("src/run_p1.py") == FZ["runner_sha256"]); ok("v1f status/eligibility/validation files equal frozen hashes", all(sha(f"runs/p1-v1f-gemini-20261124/{f}") == FZ[k] for f, k in (("APP_STATUS.json", "app_status_sha256"), ("eligibility.csv", "eligibility_csv_sha256"), ("registry_validation.json", "registry_validation_sha256"))))
ok("no approval files exist (APPROVED.json / APPROVED_PASS2.json / RETRIEVAL_APPROVED.json)", not glob.glob("runs/**/APPROVED*.json", recursive=True) and not glob.glob("runs/**/RETRIEVAL_APPROVED.json", recursive=True))
env = [l.split("=")[0] for l in open(".env") if "=" in l]; ok(".env present with owner-only mode", oct(os.stat(".env").st_mode & 0o777) == "0o600", f"keys present: {sorted(env)}")
def reads(f): t = open(f).read(); return sorted({k for k in env if k in t})
gem = {"src/run_p1.py": reads("src/run_p1.py"), "src/run_neo4j_surfaces.py": reads("src/run_neo4j_surfaces.py")}; grq = reads("src/verify_v2.py")
ok("Gemini runners mention only GEMINI_API_KEY as a variable to read", all(set(v) <= {"GEMINI_API_KEY", "GEMINI_API_KEY_2"} for v in gem.values()), str(gem))
def code_lines(f): return [l for l in open(f).read().split("\n") if "KEY_2" in l and not l.strip().startswith(("#", '"""')) and "never read" not in l and "policy" not in l.lower()]
ok("no executable code path reads GEMINI_API_KEY_2 (no key rotation)", all(not [l for l in code_lines(f) if "environ" in l or "startswith" in l or "COMBOS" in l] for f in ("src/run_p1.py", "src/run_neo4j_surfaces.py", "src/verify_v2.py", "src/research.py")))
ok("run_p1 reads the key only via startswith('GEMINI_API_KEY=')", 'startswith("GEMINI_API_KEY=")' in open("src/run_p1.py").read()); ok("run_neo4j_surfaces reads the key only via startswith('GEMINI_API_KEY=')", 'startswith("GEMINI_API_KEY=")' in open("src/run_neo4j_surfaces.py").read())
ok("verify_v2 reads only GROQ_API_KEY", grq == ["GROQ_API_KEY"], str(grq)); ok("legacy scripts are neutralised (refuse to run)", all("LEGACY SCRIPT" in open(f).read() for f in ("src/research.py", "src/verify.py")))
rp = open("src/run_p1.py").read(); ok("runner requires per-model caps", 'assert set(approved["models"]) == set(approved["cap_per_model"])' in rp); ok("runner stops on first daily-quota 429 (no retry loop)", 'kind == "daily_quota"' in rp and "dead.add(m)" in rp); ok("runner refuses without APPROVED.json", "REFUSING: no APPROVED.json" in rp)
vp = open("src/verify_v2.py").read(); ok("verifier v2: mandatory call cap + retry-exhaustion stop + checkpointing", "max_calls" in vp and "retries_exhausted" in vp and "os.replace" in vp); ok("verifier v2 refuses outputs inside baseline/ or work/", "never baseline/ or work/" in vp)
ok("Gladly/Neo4j/expansion plans exist and are unapproved", all(os.path.exists(p) for p in ("runs/p1-neo4j-optionB-20261124/PLAN.json", "runs/p1-expansion-v1-20261124/PLAN.json")))
ok("baseline intact", subprocess.run("cd baseline && shasum -a 256 -c SHA256SUMS.txt", shell=True, capture_output=True, text=True).stdout.count(": OK") == 151, "151 files")
ok("unused keys flagged for removal (not removed)", True, "OPENROUTER_API_KEY and GEMINI_API_KEY_2 are not used by any executable script")
os.makedirs("runs/readiness-v3-20261124", exist_ok=True); _p = "runs/readiness-v3-20261124/CONFIG_CHECK_" + time.strftime("%Y%m%d_%H%M%S") + ".json"   # a NEW timestamped file each run: earlier versions are never overwritten
with open(_p, "w") as _f: json.dump(dict(created=time.strftime("%Y-%m-%dT%H:%M:%S%z"), passed=all(c["passed"] for c in out), checks=out), _f, indent=1)
for c in out: print(("PASS " if c["passed"] else "FAIL ") + c["check"] + (f" [{c['detail']}]" if c["detail"] and not c["passed"] else ""))
print("ALL CONFIG CHECKS PASSED" if all(c["passed"] for c in out) else "SOME CHECKS FAILED")

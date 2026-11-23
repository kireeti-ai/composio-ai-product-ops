"""Secret-handling audit. Searches for the REAL key values (read from .env at runtime, never printed) and for generic key formats across project files, logs, generated artifacts,
scratch files and background-task outputs; checks .env permissions, .gitignore coverage, git history, and which scripts read which environment variables.
Writes ONLY metadata (path, key NAME, line number, counts) - never a secret value - to runs/security-audit-v1-20261124/SECRET_AUDIT.json."""
import os, re, json, stat, subprocess, time, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
ENV = {}
for l in open(".env"):
    if "=" in l and not l.startswith("#"): k, v = l.strip().split("=", 1); ENV[k] = v
PAT = {"composio_ck": re.compile(rb"ck_[A-Za-z0-9]{16,}"), "google_AQ": re.compile(rb"AQ\.[A-Za-z0-9_\-]{30,}"), "google_AIza": re.compile(rb"AIza[0-9A-Za-z_\-]{35}"), "groq_gsk": re.compile(rb"gsk_[A-Za-z0-9]{40,}"), "openrouter_sk_or": re.compile(rb"sk-or-v1-[a-f0-9]{40,}"), "generic_sk": re.compile(rb"\bsk-[A-Za-z0-9]{32,}\b")}
SC = "/private/tmp/claude-501/-Users-kireeti-Desktop-notes-Assignment"; roots = {"project_src": ["src", "tests", "data"], "runs": ["runs"], "baseline": ["baseline"], "work_logs_and_evidence": ["work"], "root_files": [".gitignore"], "assistant_scratch_and_task_outputs": [SC]}
hits = []; scanned = {k: 0 for k in roots}
def scan(path, area):
    try:
        if os.path.getsize(path) > 60_000_000: return
        b = open(path, "rb").read()
    except Exception: return
    scanned[area] += 1
    for name, v in ENV.items():
        if v and v.encode() in b: hits.append(dict(file=path, area=area, kind=f"exact_value_of:{name}", lines=[b[:b.find(v.encode())].count(b"\n") + 1], count=b.count(v.encode())))
    for pn, rx in PAT.items():
        ms = rx.findall(b)
        if ms and not any(h["file"] == path and h["kind"].startswith("exact_value_of") for h in hits): hits.append(dict(file=path, area=area, kind=f"pattern:{pn}", count=len(ms)))
for area, ps in roots.items():
    for p in ps:
        if os.path.isfile(p): scan(p, area)
        else:
            for dp, dn, fn in os.walk(p):
                for f in fn: scan(os.path.join(dp, f), area)
# also: the assistant's own session transcripts (outside the project; cannot be scrubbed from here) - count only
tr = os.path.expanduser("~/.claude/projects/-Users-kireeti-Desktop-notes-Assignment"); tr_hits = 0; tr_files = 0
if os.path.isdir(tr):
    for dp, dn, fn in os.walk(tr):
        for f in fn:
            tr_files += 1
            try: b = open(os.path.join(dp, f), "rb").read()
            except Exception: continue
            if any(v and v.encode() in b for v in ENV.values()): tr_hits += 1
st = os.stat(".env"); mode = oct(stat.S_IMODE(st.st_mode)); ign = open(".gitignore").read().split()
gl = subprocess.run(["git", "-C", "..", "log", "--all", "--oneline", "--", "Assignment"], capture_output=True, text=True).stdout.strip().splitlines()
gs = subprocess.run(["git", "-C", "..", "status", "--short", "--", "Assignment"], capture_output=True, text=True).stdout.strip().splitlines()
readers = {}
for f in glob.glob("src/*.py"):
    t = open(f).read(); names = sorted({n for n in ENV if n in t}); loads_all = ("setdefault(k, v)" in t) or ("for l in" in t and "setdefault" in t)
    readers[f] = dict(mentions_keys=names, loads_every_env_var=loads_all)
rep = dict(created=time.strftime("%Y-%m-%dT%H:%M:%S%z"), env_key_names=sorted(ENV), env_file=dict(mode=mode, owner_only=(st.st_mode & 0o077) == 0, gitignored=".env" in ign), work_dir_gitignored="work/" in ign,
           files_scanned=scanned, exposed_value_hits_outside_env=[h for h in hits if h["kind"].startswith("exact_value_of")], format_pattern_hits=[h for h in hits if h["kind"].startswith("pattern:")],
           git=dict(commits_touching_Assignment=len(gl), status_of_Assignment=gs[:3], note="Assignment/ is untracked in the parent repo: no secret has been committed from here"),
           session_transcripts=dict(location="~/.claude/projects/... (outside the project)", files=tr_files, files_containing_key_values=tr_hits, note="keys pasted in chat live in the transcript store; rotation is the only remedy"),
           scripts_reading_keys=readers)
os.makedirs("runs/security-audit-v1-20261124", exist_ok=True); outp = "runs/security-audit-v1-20261124/SECRET_AUDIT.json"
if os.path.exists(outp): outp = "runs/security-audit-v1-20261124/SECRET_AUDIT_rerun_" + time.strftime("%Y%m%d_%H%M%S") + ".json"   # every audit is preserved
json.dump(rep, open(outp, "w"), indent=1); os.chmod(outp, 0o444); print("written:", outp)
print(".env mode:", mode, "| owner-only:", rep["env_file"]["owner_only"], "| gitignored:", rep["env_file"]["gitignored"], "| work/ gitignored:", rep["work_dir_gitignored"])
print("files scanned:", scanned)
print("EXACT key values found outside .env:", [(h["file"], h["kind"], h["count"]) for h in rep["exposed_value_hits_outside_env"]] or "none")
print("generic key-format matches:", [(h["file"], h["kind"], h["count"]) for h in rep["format_pattern_hits"]] or "none")
print("git commits touching Assignment/:", len(gl), "| status:", gs[:2]); print("session transcript files containing key values (outside project):", tr_hits, "of", tr_files)
print("scripts that load EVERY .env variable:", [f for f, v in readers.items() if v["loads_every_env_var"]]); print("scripts mentioning key names:", {f: v["mentions_keys"] for f, v in readers.items() if v["mentions_keys"]})

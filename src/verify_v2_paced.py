"""Versioned wrapper around src/verify_v2.py adding a MINIMUM INTERVAL between Groq calls (from "min_interval_s" in APPROVED_PASS2*.json), so the observed RPM/TPM limits can be respected. verify_v2.py is unchanged.
Usage: python src/verify_v2_paced.py --out DIR --records GLOB [--dry-run]   (same arguments as verify_v2)"""
import os, sys, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT); sys.path.insert(0, "src"); import verify_v2 as V
def paced(min_interval, sleep=time.sleep, clock=time.monotonic):
    last = [None]; orig = V.groq_call
    def call(msgs, budget, key, sleep=sleep):
        if last[0] is not None:
            wait = min_interval - (clock() - last[0])
            if wait > 0: sleep(wait)
        last[0] = clock(); return orig(msgs, budget, key, sleep=sleep)
    return call
if __name__ == "__main__":
    out = sys.argv[sys.argv.index("--out") + 1]; ap = f"{out}/APPROVED_PASS2.json"
    if os.path.exists(ap):
        mi = float(json.load(open(ap)).get("min_interval_s", 0))
        if mi: V.groq_call = paced(mi)
    V.main()

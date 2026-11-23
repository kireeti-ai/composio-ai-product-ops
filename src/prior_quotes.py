"""Code-verified quotes for the 11 'prior access evidence sufficient' apps (assistant reading of baseline pages; provisional). Also records heuristic-vs-judgment disagreements. Offline. Output: runs/topup-v1s-20261123/prior_access_quotes.json"""
import os, re, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'")).strip().lower()
Q = {27: "messaging applications on our platform free of charge", 32: "To use the Marketing API in production, you must", 33: "Vetted Product with development and standard tiers", 34: "API access is available across HighLevel subscription plans.",
     39: "each permission must first be approved through the App Review process", 41: "Some APIs also require Shopify's approval or a specific Shopify plan.", 43: "Sign up for a free BigCommerce trial store to test API calls",
     52: "Data API requests draw on your credit balance", 53: "Ahrefs API is available on eligible paid plans.", 56: "Create a free account for direct API access and higher limits", 76: "The first step is to sign up and create a trial account."}
rows = json.load(open("runs/topup-v1s-20261123/page_evidence_table.json")); out = {}
for i, q in Q.items():
    pages = {p["url"]: p["text"] for p in json.load(open(f"baseline/p1_v1/raw/{i}.json"))["pages"]}; u = next((u for u, t in pages.items() if norm(q) in norm(t)), None)
    heur = sum(1 for r in rows if r["app_id"] == i and r["retrieval_usability"] == "usable" and isinstance(r["evidence_relevance"], dict) and r["evidence_relevance"]["access"] == "direct")
    out[i] = dict(quote=q, url=u, verified=u is not None, heuristic_direct_access_pages=heur, disagreement=(u is not None and heur == 0))
json.dump(dict(provenance="assistant reading of baseline pages, provisional; quotes verified by code", apps=out, disagreements=[i for i, v in out.items() if v["disagreement"]], unverified=[i for i, v in out.items() if not v["verified"]]), open("runs/topup-v1s-20261123/prior_access_quotes.json", "w"), indent=1)
os.chmod("runs/topup-v1s-20261123/prior_access_quotes.json", 0o444)
print("verified:", sum(v["verified"] for v in out.values()), "/ 11 | unverified:", [i for i, v in out.items() if not v["verified"]], "| heuristic-vs-judgment disagreements (heuristic 0 direct pages, quote exists):", [i for i, v in out.items() if v["disagreement"]])

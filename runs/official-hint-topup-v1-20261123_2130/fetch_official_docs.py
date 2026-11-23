"""Fetch official documentation pages discovered from authoritative first-party search results; GET only."""
import hashlib,json,time,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
OUT=Path(__file__).resolve().parent; RAW=OUT/'raw'/'additional'; RAW.mkdir(parents=True,exist_ok=True)
URLS={
83:[('https://developers.binance.com/en/docs/introduction','official API documentation overview'),('https://developers.binance.com/en/docs/products/spot/rest-api','official Spot REST API'),],
86:[('https://developer.intuit.com/app/developer/qbo/docs/','official QBO API overview'),('https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0','official OAuth setup'),('https://static.developer.intuit.com/output_html/qbo/docs/learn/premium-apis.html','official premium API access'),],
91:[('https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks','official Gemini Notebook Enterprise API'),('https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/overview','official product overview')],
92:[('https://help.otter.ai/hc/en-us/articles/36130822688279-Otter-ai-Public-API','official Otter Public API'),('https://help.otter.ai/hc/en-us/articles/35287607569687-Otter-MCP-Server','official Otter MCP'),],
93:[('https://www.fathom.ai/features/api','official Fathom API product page')],
99:[('https://transcriptapi.com/docs/api/','official TranscriptAPI API docs'),('https://transcriptapi.com/docs/mcp/','official TranscriptAPI MCP docs')],
}
manifest=[]
for app,items in URLS.items():
 for n,(url,kind) in enumerate(items):
  rec={'app_id':app,'source_kind':kind,'url':url,'started_at_utc':datetime.now(timezone.utc).isoformat()}
  req=urllib.request.Request(url,headers={'User-Agent':'AssignmentResearch/1.0','Accept':'text/html,application/xhtml+xml,*/*'})
  try:
   with urllib.request.urlopen(req,timeout=25) as r:
    body=r.read(4_000_001); truncated=len(body)>4_000_000; body=body[:4_000_000]
    rec.update(status='returned',http_status=r.status,final_url=r.geturl(),content_type=r.headers.get('Content-Type'),retrieved_at_utc=datetime.now(timezone.utc).isoformat(),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),truncated_at_4mb=truncated)
    (RAW/f'{app}_{n+1}.bin').write_bytes(body)
  except Exception as e: rec.update(status='failed',error_type=type(e).__name__,error=str(e)[:300],retrieved_at_utc=datetime.now(timezone.utc).isoformat())
  manifest.append(rec);print(app,rec['status'],rec.get('http_status'),rec.get('final_url',''));time.sleep(0.5)
(OUT/'OFFICIAL_DOC_ATTEMPTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('total',len(manifest),'returned',sum(x['status']=='returned' for x in manifest),'failed',sum(x['status']=='failed' for x in manifest))

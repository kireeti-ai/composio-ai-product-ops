"""One bounded, zero-cost HTTPS GET for each ID with no cached retrieval bundle."""
import hashlib, json, re, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
D=json.load(open(ROOT/'data/apps.json'))
ids=[83,86,91,92,93,98,99]
manifest=[]
for i in ids:
    row=D['apps'][i-1]; hint=row[3]
    host=hint.split()[0].strip('()')
    if host.startswith('github.com/'):
        url='https://'+host
    else:
        url='https://'+host.rstrip('/')+'/'
    started=datetime.now(timezone.utc).isoformat()
    rec={'id':i,'name':row[2],'url':url,'source_kind':'assignment website/developer hint','started_at_utc':started}
    req=urllib.request.Request(url,headers={'User-Agent':'AssignmentResearch/1.0 (public documentation fetch)','Accept':'text/html,application/xhtml+xml,*/*'})
    try:
        with urllib.request.urlopen(req,timeout=18) as res:
            raw=res.read(2_000_001)
            if len(raw)>2_000_000:
                raw=raw[:2_000_000]; rec['truncated_local_limit']=True
            rec.update(http_status=res.status,final_url=res.geturl(),content_type=res.headers.get('Content-Type'),retrieved_at_utc=datetime.now(timezone.utc).isoformat(),byte_length=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            (OUT/'raw'/f'{i}.bin').write_bytes(raw)
            rec['fetch_status']='returned_page'
    except Exception as e:
        rec.update(fetch_status='failed',error_type=type(e).__name__,error=str(e)[:400],retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    manifest.append(rec)
    print(i,rec['fetch_status'],rec.get('http_status'),rec.get('final_url',''))
    time.sleep(1)
(OUT/'ATTEMPTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('attempts',len(manifest),'returned',sum(x['fetch_status']=='returned_page' for x in manifest),'failed',sum(x['fetch_status']=='failed' for x in manifest))

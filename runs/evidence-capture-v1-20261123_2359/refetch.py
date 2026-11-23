"""Independent re-fetch of every captured quote. usage: refetch.py batchN [...]  -> batchN/refetch/{snap_*.txt,REFETCH.json}. Never overwrites originals or prior snapshots (snapshots are content-hash named)."""
import json,hashlib,sys,os,re,html,subprocess,datetime
from concurrent.futures import ThreadPoolExecutor
def norm(t):
    t=re.sub(r'<(script|style)[^>]*>.*?</\1>',' ',t,flags=re.S|re.I); t=re.sub(r'<[^>]+>',' ',t); t=html.unescape(t)
    t=t.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"').replace('–','-').replace('—','-').replace('`','').replace('*','')
    return re.sub(r'\s+',' ',t).strip().lower()
def get(u):
    p=subprocess.run(['curl','-sL','-m','30','-A','Mozilla/5.0','-w','\n__META__%{http_code} %{url_effective}','--max-filesize','8000000',u],capture_output=True)
    b=p.stdout; i=b.rfind(b'\n__META__'); body=b[:i]; code,eff=b[i+9:].decode().split(' ',1); return body,int(code or 0),eff.strip()
for b in sys.argv[1:]:
    d=json.load(open(f'{b}/records.json')); out=f'{b}/refetch'; os.makedirs(out,exist_ok=True)
    urls=sorted({e['url'] for r in d['records'] for c in r['claims'] for e in c.get('evidence',[])})
    with ThreadPoolExecutor(2) as ex: got=dict(zip(urls,ex.map(get,urls)))
    res=[]; now=datetime.datetime.utcnow().isoformat()+'Z'
    for r in d['records']:
        for c in r['claims']:
            for e in c.get('evidence',[]):
                body,code,eff=got[e['url']]; sh=hashlib.sha256(body).hexdigest(); sn=f'{out}/snap_{sh[:16]}.txt'
                if not os.path.exists(sn): open(sn,'wb').write(body[:2000000])
                txt=norm(body.decode('utf8','ignore')); q=norm(e['quote']); found=q in txt; ws=re.sub(r'\s+','',q) in re.sub(r'\s+','',txt)
                redir=eff.rstrip('/')!=e['url'].rstrip('/')
                if code in(403,401,429) or (code==0) : st='inaccessible'
                elif code>=400: st='unavailable'
                elif found: st='reproduced_via_redirect' if redir else 'reproduced'
                elif ws: st='reproduced_whitespace_insensitive'
                elif len(body)<200: st='inaccessible'
                else: st='changed_or_not_reproduced'
                res.append(dict(app_id=r['app_id'],field=c['field'],url=e['url'],http=code,final_url=eff,refetched_at_utc=now,refetch_status=st,quote_sha256=e['quote_sha256'],original_page_sha256=e.get('page_sha256'),refetch_page_sha256=sh,page_bytes_identical=sh==e.get('page_sha256'),refetch_snapshot=sn))
    json.dump(res,open(f'{out}/REFETCH.json','w'),indent=1)
    from collections import Counter; print(b,len(res),Counter(x['refetch_status'] for x in res))

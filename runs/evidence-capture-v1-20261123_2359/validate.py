import json,hashlib,sys,os,re
from collections import Counter
def n(t): return re.sub(r'\s+',' ',t).strip()
tot=Counter(); bad=[]
for b in sys.argv[1:]:
    p=f'{b}/records.json'
    if not os.path.exists(p): print(b,'missing'); continue
    d=json.load(open(p))
    for r in d['records']:
        for c in r['claims']:
            for e in c.get('evidence',[]):
                f=f"{b}/{e['raw_file']}"; ok=os.path.exists(f)
                t=n(open(f,errors='ignore').read()) if ok else ''
                inpage=ok and n(e['quote']) in t
                hq=hashlib.sha256(e['quote'].encode()).hexdigest()==e['quote_sha256']
                hp=ok and hashlib.sha256(open(f,'rb').read()).hexdigest()==e.get('page_sha256')
                tot['evidence']+=1; tot['quote_in_page']+=inpage; tot['quote_hash_ok']+=hq; tot['page_hash_ok']+=hp
                if not(inpage and hq): bad.append((r['app_id'],c['field'],e['url'],inpage,hq))
            if c['status']=='supported_by_quote' and not c.get('evidence'): bad.append((r['app_id'],c['field'],'no evidence'))
            tot['claim_'+c['status']]+=1
print(dict(tot)); print(len(bad),'bad'); [print(x) for x in bad[:15]]

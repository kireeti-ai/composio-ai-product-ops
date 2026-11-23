"""Offline audit of the 54 accepted primary records; writes only to this run."""
import collections, hashlib, importlib.util, json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; os.chdir(ROOT)
run=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('bench2',ROOT/'runs/bench5-v2-20261123_192201/bench2.py')
B=importlib.util.module_from_spec(spec); import sys; sys.modules['bench2']=B; spec.loader.exec_module(B)
D=json.load(open(ROOT/'runs/dataset-live-v4-20261123_2040/DATASET.json'))
RUNS={'batchA':'runs/p1-batchA-groq-20261123_193428','batchB':'runs/p1-batchB-groq-20261123_195002','corrected5':'runs/correction5-v1-20261123_192852'}
rows=[]; states=collections.Counter(); issue_totals=collections.Counter(); claim_totals=collections.Counter(); per_app={}
for row in D['rows']:
    if not row.get('primary_version'): continue
    i=row['registry_id']; version=row['primary_version']
    if version=='baseline_p1_v1':
        rec=json.load(open(ROOT/f'baseline/p1_v1/pass1/{i}.json'))
        raw=json.load(open(ROOT/f'baseline/p1_v1/raw/{i}.json'))
        full=[{'url':p['url'],'text':p['text']} for p in raw['pages']]; shown=full
        obj=rec
    else:
        d=ROOT/RUNS[version]
        rec=json.load(open(d/f'outputs/groq_orgA/{i}.json')); obj=rec['output']
        full=json.load(open(d/f'bundles_full/{i}.json'))['pages']
        shown=json.load(open(d/f'bundles/{i}.json'))['pages']
    v=B.validate_v2(obj,shown,full)
    evidence=[]
    for e in v['evidence']:
        x={'field':e['field'],'url':e['url'],'issues':e['issues'],'valid_lexical':e['valid']}
        evidence.append(x)
        for issue in e['issues']: issue_totals[issue]+=1
    for c in v['claims']:
        states[c['state']]+=1; claim_totals[c['field']+':'+c['state']]+=1
    out={'id':i,'name':row['name'],'version':version,'provider': 'gemini' if version=='baseline_p1_v1' else 'groq','model':rec.get('model_returned') or rec.get('model'),'evidence_count':len(evidence),'evidence_lexically_valid':sum(e['valid_lexical'] for e in evidence),'evidence':evidence,'claim_states':v['claims'],'claim_state_counts':v['claim_state_counts'],'interpretation':'Lexical evidence validation only; no semantic or accuracy claim.'}
    rows.append(out); per_app[i]=out
assert len(rows)==54 and len({x['id'] for x in rows})==54
assert all(x['id'] in {r['registry_id'] for r in D['rows']} for x in rows)
report={'created_local':__import__('datetime').datetime.now().astimezone().isoformat(),'source_dataset':'runs/dataset-live-v4-20261123_2040/DATASET.json','registry_sha256':hashlib.sha256((ROOT/'data/apps.json').read_bytes()).hexdigest(),'accepted_records_audited':len(rows),'network_calls':0,'model_calls':0,'accuracy_claimed':False,'method':'Re-ran existing strict lexical/URL/contiguity checks against full stored source bundles (baseline raw evidence for V1); did not judge factual semantics.','claim_state_totals':dict(states),'evidence_issue_totals':dict(issue_totals),'claims_by_field_and_state':dict(claim_totals),'records':rows}
(run/'AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
lines=['# Offline audit of accepted primary records','',f"Audited {len(rows)} accepted records from the preserved v4 dataset.",'','This is a deterministic source-quote and source-URL audit only. It does not establish factual correctness or model accuracy. No network or model calls were made.','', '## Results','',f"- Evidence items: {sum(x['evidence_count'] for x in rows)}",f"- Lexically valid evidence items: {sum(x['evidence_lexically_valid'] for x in rows)}",f"- Claim states: `{json.dumps(dict(states),sort_keys=True)}`",f"- Evidence issue counts: `{json.dumps(dict(issue_totals),sort_keys=True)}`",'', '## Records with evidence issues','', '| ID | App | Version | Evidence items | Valid | Issues |','|---:|---|---|---:|---:|---|']
for x in rows:
    issues=collections.Counter(q for e in x['evidence'] for q in e['issues'])
    if issues: lines.append(f"| {x['id']} | {x['name']} | {x['version']} | {x['evidence_count']} | {x['evidence_lexically_valid']} | {', '.join(f'{k}: {v}' for k,v in sorted(issues.items()))} |")
lines+=['','## Limitations','','- A matching contiguous quotation is not proof that the quotation entails the claim.','- Source URLs were checked against saved page ledgers, not refetched in this audit.','- No independent human labels are available; accuracy remains unmeasured.','']
(run/'AUDIT.md').write_text('\n'.join(lines))
print(json.dumps({'audited':len(rows),'evidence_items':sum(x['evidence_count'] for x in rows),'valid':sum(x['evidence_lexically_valid'] for x in rows),'claim_states':dict(states),'issues':dict(issue_totals),'report':str(run/'AUDIT.md')},indent=2))

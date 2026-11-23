"""Consolidate batches 1-4 + Codex six + claim review into CONSOLIDATED.json and RECONCILIATION.{csv,md}. Deterministic; reads only saved artefacts."""
import json,csv,hashlib,collections,os
R='..'; 
prior=json.load(open(f'{R}/manual-research-consolidated-v1-20261123_2330/RESEARCH_RECORDS.json'))['records']
cv=json.load(open(f'{R}/codex-evidence-validation-v1-20261123_2359/VALIDATION_FINAL.json'))
KEY=lambda f:('auth_methods' if 'auth' in f else 'mcp_status' if 'mcp' in f else 'api_types' if ('api' in f or 'webhook' in f) else 'access' if ('access' in f or 'plan' in f or 'pric' in f or 'sandbox' in f or 'limit' in f) else 'buildability' if ('build' in f or 'block' in f) else None)
OK={'reproduced','reproduced_via_redirect','reproduced_whitespace_insensitive'}
apps={}; claims=[]
for b in ('batch1','batch2','batch3','batch4'):
    recs=json.load(open(f'{b}/records.json'))['records']
    rel={x['claim_id']:x for x in json.load(open(f'relevance_v2/output_{b}.json'))}
    rf=json.load(open(f'{b}/refetch/REFETCH.json')); rfk={(x['app_id'],x['field'],x['url'],x['quote_sha256']):x for x in rf}
    for r in recs:
        a=dict(app_id=r['app_id'],name=r['name'],batch=b,evidence_class='source_quoted_primary_capture',identity_note=r['identity_note'],summary=r['summary'],prior_record_corrections=r['prior_record_corrections'],open_questions=r['open_questions'],claim_ids=[]); apps[r['app_id']]=a
        pr=prior.get(str(r['app_id']),{})
        for ci,c in enumerate(r['claims']):
            ev=[]
            for ei,e in enumerate(c.get('evidence',[])):
                x=rfk[(r['app_id'],c['field'],e['url'],e['quote_sha256'])]; rl=rel.get(f"{r['app_id']}:{ci}",dict(verdict='none',contradicts=False,reason='no audit row',uncovered=[]))
                ev.append(dict(url=e['url'],title=e.get('title'),source_type=e['source_type'],retrieved_at_utc=e['retrieved_at_utc'],quote=e['quote'],quote_sha256=e['quote_sha256'],raw_file=f"{b}/{e['raw_file']}",page_sha256=e['page_sha256'],refetch_status=x['refetch_status'],refetch_snapshot=f"{b}/{x['refetch_snapshot']}",refetch_page_sha256=x['refetch_page_sha256'],refetch_checked_utc=x['refetched_at_utc'],relevance=rl['verdict'],contradicts=bool(rl.get('contradicts')),relevance_reason=rl['reason'],uncovered_components=rl.get('uncovered',[])))
            official=[e for e in ev if e['source_type'].startswith('official')]
            k=KEY(c['field']); cl=ev[0]['relevance'] if ev else 'none'; repro=[e for e in ev if e['refetch_status'] in OK]; offrep=[e for e in repro if e['source_type'].startswith('official')]
            st=c['status']
            if st=='conflicting' or any(e['contradicts'] for e in ev): fv='conflicting'
            elif st=='supported_by_quote':
                if not repro: fv='unresolved_not_reproduced'
                elif cl=='direct': fv='supported_by_official_quote' if offrep else 'supported_by_third_party_quote_only'
                elif cl=='partial': fv='partially_supported'
                else: fv='unresolved_quote_does_not_support_claim'
            else: fv=st  # unknown / not_verified
            if k=='buildability' and fv in('supported_by_official_quote','supported_by_third_party_quote_only','partially_supported'): fv='researcher_judgement_from_quoted_facts'
            orig=pr.get(k) if k else None
            if k=='access' and orig: orig=f"{orig} | {pr.get('access_note','')}"
            claims.append(dict(claim_id=f"{r['app_id']}:{ci}",app_id=r['app_id'],name=r['name'],field=c['field'],claim_value=c['value'],agent_status=st,final_verdict=fv,original_prior_claim=orig,note=c.get('note',''),evidence=ev,remaining_uncertainty=('; '.join(filter(None,[c.get('note','') if fv!='supported_by_official_quote' else '', ('uncovered: '+', '.join(ev[0].get('uncovered_components',[]))) if ev and ev[0].get('uncovered_components') else '', 'no evidence quote' if not ev else '', ' / '.join(sorted({e['refetch_status'] for e in ev if e['refetch_status'] not in OK}))]))) or 'none recorded'))
            a['claim_ids'].append(f"{r['app_id']}:{ci}")
# Codex six
H={58:dict(auth_methods=['unknown'],access='local open-source CLI/package (no hosted API documented in reviewed pages)',api_types=['cli'],mcp_status='not_verified',buildability='unknown',blocker='no hosted API documented'),
 59:dict(auth_methods=['api_key (x-api-key header)'],access='paid; rates quoted per committed volume',api_types=['rest (sync+async)'],mcp_status='not_verified',buildability='conditional',blocker='quote-based commercial terms'),
 60:dict(auth_methods=['api_key'],access='14-day trial with 1,000 data credits; Enterprise-only IP restrictions',api_types=['unknown'],mcp_status='official',buildability='conditional',blocker='plan limits'),
 68:dict(auth_methods=['oauth2 service account (near-match quote unresolved)','api_key (digest)'],access='account + Organization Owner to create API credentials',api_types=['rest (Atlas Administration API)'],mcp_status='not_verified',buildability='conditional',blocker='Admin API cannot read cluster data; database access uses separate DB-user credentials'),
 78:dict(auth_methods=['unknown'],access='unknown',api_types=['rest'],mcp_status='not_verified',buildability='unknown',blocker='auth/access not evidenced'),
 80:dict(auth_methods=['personal_access_token','oauth2 (quote unresolved)'],access='self-serve personal access token from Harvest ID Developers section',api_types=['rest'],mcp_status='not_verified',buildability='yes',blocker='none recorded')}
for r in cv:
    i=r['app_id']; a=apps.setdefault(i,dict(app_id=i,name=r['name'],batch='codex_v1',evidence_class='source_quoted_codex_validated',identity_note='',summary=H[i],prior_record_corrections=[],open_questions=[],claim_ids=[]))
    cid=f"{i}:c{len(a['claim_ids'])}"; fv='supported_by_official_quote' if r['final_status']=='source_quoted_supported' and r['source_type'].startswith('official') else 'unresolved_preserved'
    claims.append(dict(claim_id=cid,app_id=i,name=r['name'],field=r['field'],claim_value=r['claim'],agent_status=r['original_status'],final_verdict=fv,original_prior_claim=None,note=r.get('reason',''),evidence=[dict(url=r['url'],title=None,source_type=r['source_type'],retrieved_at_utc='2026-11-23T16:18:25Z (Codex web search); re-fetched later',quote=r['quote'],quote_sha256=hashlib.sha256(r['quote'].encode()).hexdigest(),raw_file=r['raw_file'],page_sha256=r['page_sha256'],refetch_status='reproduced' if r['quote_in_page'] else ('reproduced_after_markup_normalization' if r['validation'].startswith('exact') else 'not_reproduced_verbatim'),refetch_snapshot=r['raw_file'],refetch_page_sha256=r['page_sha256'],refetch_checked_utc='2026-11-23 validation run',relevance={'supports':'direct','weak':'partial','irrelevant':'none'}[r['relevance']],contradicts=False,relevance_reason=r.get('reason',''))],remaining_uncertainty=r.get('reason') or 'none recorded'))
    a['claim_ids'].append(cid)
# claim review (model-reviewed, 229)
rev=[];inp=[]
for k in (1,2,3): rev+=json.load(open(f'../claim-review-v1-20261123_2359/output_chunk{k}.json')); inp+=json.load(open(f'../claim-review-v1-20261123_2359/input_chunk{k}.json'))
ik={x['row_id']:x for x in inp}
review=[dict(x,app_name=ik[x['row_id']]['app_name'],review_basis='model_reviewed_not_human_verified',cited_quote=ik[x['row_id']]['quote']) for x in rev]
# Paygent kept unresolved
for x in review:
    if 'aygent' in x['app_name']: x['identity_hold']='Paygent product identity unresolved (stored bundle mixes paygent.to, withpaygent.com, gopaygent.com)'
out=dict(created=__import__('time').strftime('%Y-%m-%dT%H:%M:%S%z'),apps=apps,claims=claims,model_claim_review=review)
json.dump(out,open(os.path.join(os.environ.get('CONSOLIDATE_OUT','.'),'CONSOLIDATED.json'),'w'),indent=1)
vc=collections.Counter(c['final_verdict'] for c in claims); print(len(apps),'apps',len(claims),'claims',dict(vc))
qs={(e['url'],e['quote_sha256']) for c in claims for e in c['evidence']}; print('distinct quotes',len(qs))
print('review',collections.Counter(x['verdict'] for x in review))
with open(os.path.join(os.environ.get('CONSOLIDATE_OUT','.'),'RECONCILIATION.csv'),'w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['app_id','app','field','original_prior_claim','current_claim','final_verdict','supporting_quote','source_url','source_type','refetch_result','quote_directly_supports_claim','remaining_uncertainty'])
    for c in claims:
        if not c['evidence']: w.writerow([c['app_id'],c['name'],c['field'],c['original_prior_claim'],c['claim_value'],c['final_verdict'],'','','','','',c['remaining_uncertainty']])
        for e in c['evidence']: w.writerow([c['app_id'],c['name'],c['field'],c['original_prior_claim'],c['claim_value'],c['final_verdict'],e['quote'],e['url'],e['source_type'],e['refetch_status'],e['relevance'],c['remaining_uncertainty']])

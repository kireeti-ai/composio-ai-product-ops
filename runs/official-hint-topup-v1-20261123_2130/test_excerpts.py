import hashlib,json
from pathlib import Path
p=Path(__file__).with_name('WEB_RESEARCH_EXCERPTS.json'); d=json.loads(p.read_text())
assert [r['id'] for r in d['records']]==[83,86,91,92,93,98,99]
for r in d['records']:
 assert r['research_state'].startswith('partial')
 for c in r['claims']:
  assert c['source_url'].startswith('https://') and c['quote'] and '...' not in c['quote'] and '…' not in c['quote']
  assert c['quote_sha256']==hashlib.sha256(c['quote'].encode()).hexdigest()
print('PASS: 7 IDs, source URLs, non-placeholder quotations and quote hashes')

import json,collections
d=json.load(open('data/apps.json'));a=d['apps']
assert [x[0] for x in a]==list(range(1,101)),"ids not 1..100 in order"
c=collections.Counter(x[1] for x in a)
assert all(c[i]==10 for i in range(1,11)),c
assert len({x[2].lower() for x in a})==100,"duplicate names"
assert all(x[1]==(x[0]-1)//10+1 for x in a),"category/order mismatch"
print("OK: 100 apps, 10 categories x10, ordered; sources:",dict(collections.Counter(x[4] for x in a)))

"""Group the callcap $10458 memory delta by map plane. Usage: python vriv_planes.py vriv_cc.json"""
import json, sys, collections
d = json.load(open(sys.argv[1]))
mem = d.get("mem") or d.get("memory") or d
planes = {"alt": 0x3f86c, "colA": 0x418ad, "colB": 0x438ee, "flags": 0x4592f}
cnt = collections.Counter(); rows = collections.defaultdict(set)
for e in mem:
    a = e["addr"] if isinstance(e, dict) else e[0]
    for n, b in planes.items():
        if b <= a < b + 4096:
            cnt[n] += 1; rows[n].add((a - b) >> 6)
print(dict(cnt)); print({n: (min(r), max(r), len(r)) for n, r in rows.items()})

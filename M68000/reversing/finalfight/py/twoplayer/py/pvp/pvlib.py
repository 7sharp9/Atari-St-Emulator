"""pvlib.py: reader for the pvp.lua log: rows of {rel, p1: {...}, p2: {...}, g: {...}} with hexadecimal field values as ints."""
import os
def load(path):
    rows = []
    for ln in open(path):
        a = ln.split(' | ')
        if len(a) < 4: continue
        rel = int(a[0]); d = []
        for part in a[1:3]:
            d.append({k: int(v, 16) for k, v in (t.split('=') for t in part.split())})
        g = {k: (int(v, 16) if '/' not in v else v) for k, v in (t.split('=') for t in a[3].split())}
        rows.append(dict(rel=rel, p1=d[0], p2=d[1], g=g))
    return rows
def changes(rows, who, keys):
    prev = None; out = []
    for r in rows:
        v = tuple(r[who][k] for k in keys)
        if v != prev: out.append((r['rel'],) + v); prev = v
    return out

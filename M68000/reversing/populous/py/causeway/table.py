"""table.py - planner vs baselines on water gaps from real snapshots.  Writes table.json and table.txt (AGENT DIR).
Gap = (snapshot, component i, component j): start/goal = the cell of each component nearest its centroid."""
import os, sys, json, time
from causelib import *
from planner import *
SNAPS = ['game_start', 'late4', 'walker/snaps/front']
MINSZ = 8
def nearest_centroid(c):
    cx = sum(p[0] for p in c)/len(c); cy = sum(p[1] for p in c)/len(c)
    return min(c, key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
rows = []
for s in SNAPS:
    m = ram(os.path.join(WORK, s + '.snap')); h = heights(m); sh = shapes(m)
    comps, seen = components(h, sh); comps.sort(key=len, reverse=True)
    comps = [c for c in comps if len(c) >= MINSZ]
    for i in range(len(comps)):
        for j in range(i+1, len(comps)):
            a, b = nearest_centroid(comps[i]), nearest_centroid(comps[j])
            t = time.time()
            r = plan(h, sh, [a], [b])
            if r is None: continue
            mana, clicks, cells = r
            hp, mp, cp = replay(h, clicks)
            ok_p = connected(hp, sh, a, b)
            row = dict(snap=s, comps=(i, j), sizes=(len(comps[i]), len(comps[j])), start=a, goal=b, planner=dict(clicks=clicks, mana=mp, ok=ok_p, costs=cp, secs=round(time.time()-t, 1)))
            for name, fn in (('straight', straight_naive), ('straight_best', straight_best), ('greedy', greedy)):
                cl = fn(h, sh, a, b)
                if cl is None: row[name] = None; continue
                hh, mm, cc = replay(h, cl)
                row[name] = dict(clicks=cl, mana=mm, ok=connected(hh, sh, a, b))
            rows.append(row); print(s, row['comps'], a, b, 'planner', mp, len(clicks), 'ok', ok_p,
                  {k: (row[k] and (row[k]['mana'], len(row[k]['clicks']), row[k]['ok'])) for k in ('straight','straight_best','greedy')}, flush=True)
json.dump(rows, open(os.path.join(DATA, 'table.json'), 'w'), indent=1)

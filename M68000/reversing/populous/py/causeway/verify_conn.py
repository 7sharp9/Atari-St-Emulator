"""Is start connected to goal in the emulator's own shape map ($36e78: walkable = shape not 0/$2f/$35, 8-connected)?
ACT (after the clicks) must be connected, CTL (no raise clicks) must not."""
import os, json
from causelib import *
rows = json.load(open(os.path.join(DATA, 'table.json')))
def real_walk(shp, x, y): return 0 <= x < 64 and 0 <= y < 64 and shp[y*64+x] not in (0, 0x2f, 0x35)
def conn(shp, a, b):
    st = [a]; seen = {a}
    while st:
        c = st.pop()
        if c == b: return True
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                q = (c[0]+dx, c[1]+dy)
                if q not in seen and real_walk(shp, *q): seen.add(q); st.append(q)
    return False
for tag, snap, comps in (('g1','game_start',(1,3)),('g2','game_start',(2,5)),('g3','late4',(2,3)),('g4','late4',(1,2))):
    r = next(r for r in rows if r['snap']==snap and tuple(r['comps'])==comps)
    a, b = tuple(r['start']), tuple(r['goal'])
    if not os.path.exists(os.path.join(DATA,'snaps',tag,'final_act.snap')): print(tag, 'not gated here (run gate.py first)'); continue
    sa = shapes(ram(os.path.join(DATA,'snaps',tag,'final_act.snap'))); sc = shapes(ram(os.path.join(DATA,'snaps',tag,'final_ctl.snap')))
    print(tag, snap, comps, a, '->', b, 'ACT connected', conn(sa, a, b), 'CTL connected', conn(sc, a, b))

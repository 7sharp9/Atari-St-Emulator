"""gate_pass.py - from data/gate_nat_<T>.json and data/gate_geom.json: for every drone frame whose car centre (screen x+8, y+6) lies inside a
gate's collision box (expanded by `m` px) tabulate the gate's pos/dir at that frame, and the drone's flag/stun (crash markers) in the
frame and the 3 after.  Also each drone's passes: (entry frame, gate pos at entry, pos at exit, route that sent it)."""
from lt import *
import collections
geom = json.load(open(os.path.join(DATA, 'gate_geom.json')))
M = 4
BOX = {2: {0: (105, 142, 58, 62)}, 4: {0: (89, 126, 58, 62), 1: (121, 158, 106, 110), 2: (89, 126, 146, 150)}, 7: {0: (217, 254, 98, 102)}}   # from gate_geom.py output
for T in (2, 4, 7):
    d = json.load(open(os.path.join(DATA, 'gate_nat_%d.json' % T)))
    rows = d['rows']
    for g, (x0, x1, y0, y1) in BOX[T].items():
        inside = collections.Counter(); crashes = []; passes = []
        for s in (0, 2, 3):
            cur = None
            for i, x in enumerate(rows):
                cx, cy = x['sx'][s] + 8, x['sy'][s] + 6
                ins = x0 - M <= cx <= x1 + M and y0 - M <= cy <= y1 + M
                if ins:
                    inside[(x['gpos'][g], x['gdir'][g])] += 1
                    if cur is None: cur = [i, x['gpos'][g], x['gdir'][g], s]
                    cur_last = (i, x['gpos'][g], x['gdir'][g])
                    if any(rows[j]['flag'][s] or rows[j]['stun'][s] for j in range(i, min(i + 4, len(rows)))): crashes.append((i, s, x['gpos'][g]))
                elif cur is not None:
                    passes.append((s, cur[0], cur[1], cur[2], cur_last[0], cur_last[1], cur_last[2])); cur = None
        print('T%d gate %d box %s: drone-frames inside (gate pos,dir): %s; flag/stun frames inside: %d %s' % (T, g, (x0, x1, y0, y1), sorted(inside.items()), len(crashes), crashes[:6]))
        print('   passes (slot, entry frame, pos, dir, exit frame, pos, dir):', passes)

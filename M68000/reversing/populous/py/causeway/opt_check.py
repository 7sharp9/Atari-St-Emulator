"""Planner optimality: exhaustive subset search of sea corners inside a box vs the planner restricted to the same box."""
import os, json, time
from causelib import *
from planner import *
rows = json.load(open(os.path.join(DATA, 'table.json')))
for snap, comps in (('game_start',(3,4)), ('game_start',(2,5)), ('late4',(2,3)), ('game_start',(1,3)), ('game_start',(4,5)), ('late4',(2,4))):
    r = next(r for r in rows if r['snap']==snap and tuple(r['comps'])==comps)
    m = ram(os.path.join(WORK,snap+'.snap')); h = heights(m); sh = shapes(m)
    a, b = tuple(r['start']), tuple(r['goal'])
    cl = r['planner']['clicks']
    # start/goal far inside land: use the cells nearest the gap instead (first/last path cell of the planner) to keep the box small
    p = plan(h, sh, [a], [b]); cells = p[2]
    # first and last cells of the water stretch
    wet = [i for i, c in enumerate(cells) if not cell_walkable(h, c[0], c[1], sh)]
    a2, b2 = cells[max(wet[0]-1, 0)], cells[min(wet[-1]+1, len(cells)-1)]
    xs = [c[0] for c in cl] + [a2[0], b2[0]]; ys = [c[1] for c in cl] + [a2[1], b2[1]]
    box = (max(0, min(xs)-2), max(0, min(ys)-2), min(63, max(xs)+2), min(63, max(ys)+2))
    nsea = sum(1 for x in range(box[0], box[2]+2) for y in range(box[1], box[3]+2) if h[y*N+x] == 0)
    t = time.time()
    pr = plan(h, sh, [a2], [b2], box=box)
    ex = check_optimal(h, sh, a2, b2, box, kmax=len(pr[1]))
    print(snap, comps, 'ends', a2, b2, 'box', box, 'sea corners', nsea, 'planner(box) k', len(pr[1]), 'exhaustive k', ex[0], 'match', ex[0] == len(pr[1]), '%.0fs' % (time.time()-t), flush=True)

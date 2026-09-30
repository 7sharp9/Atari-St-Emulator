"""ab_human.py - A/B: does the human car's state change a drone's state?  Compares data/paths_idle.json (human never presses) with
data/paths_fire.json (human holds accelerate and crashes around), same snapshot, same step grid (record_paths.py).

For each drone slot the first sample where (px,py,spd,wp,stun,acc) differs between the two runs is found, together with the human
slot-1 position and its distance (world units) to that drone at that sample; before that sample the drone traces are bit-identical.
Also reports the minimum human-drone distance over the identical prefix.
"""
import json, math
from aiutil import *
a = json.load(open(os.path.join(DATA, 'paths_idle.json')))
b = json.load(open(os.path.join(DATA, 'paths_fire.json')))
n = min(len(a), len(b))
keys = ['px', 'py', 'spd', 'wp', 'stun', 'acc']
print('samples', n, 'human final pos idle/fire', (a[-1]['px'][1], a[-1]['py'][1]), (b[-1]['px'][1], b[-1]['py'][1]))
for d in (0, 2, 3):
    first = None
    for i in range(n):
        if any(a[i][k][d] != b[i][k][d] for k in keys):
            first = i
            break
    pre = range(first if first is not None else n)
    mind = min(math.hypot(b[i]['px'][1] - b[i]['px'][d], b[i]['py'][1] - b[i]['py'][d]) for i in pre)
    if first is None:
        print('drone slot %d: identical for all %d samples; min dist human-drone %.0f u' % (d, n, mind))
    else:
        i = first
        dist = math.hypot(b[i]['px'][1] - b[i]['px'][d], b[i]['py'][1] - b[i]['py'][d])
        print('drone slot %d: traces identical for the first %d samples (%d steps); human moved from (%d,%d) during that time; first difference at sample %d: human-drone distance %.0f u (1 px = 8 u); min distance in the identical prefix %.0f u; speeds there idle/fire %s/%s' % (
            d, first, first * 3000, a[0]['px'][1], a[0]['py'][1], first, dist, mind, a[i]['spd'][d], b[i]['spd'][d]))
hum_moved = sum(1 for i in range(n) if (b[i]['px'][1], b[i]['py'][1]) != (b[0]['px'][1], b[0]['py'][1]))
print('samples where the fire-run human differs from its start position:', hum_moved, 'of', n)

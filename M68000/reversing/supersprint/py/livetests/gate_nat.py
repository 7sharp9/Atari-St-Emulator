"""gate_nat.py <T> [frames] - natural gate routing on a gate track (T = 2, 4, 7 = Tracks 3, 5, 8).

Resumes agents/tracks/snaps/race_<T>.snap (paused at $beb2, inside $be40) and runs 3M steps (race live), then samples once per
frame at the entry of $df18: the gate arrays (-1814 dir, -1820 pos, -1826 timer, -1832 route, -1808 count, frame counter
-8072) and every car's wp/flag/stun/position.  A *branch event* is a frame where drone d's wp changed to n+route-ish: with p the old
wp and n = (p+2) mod count, tb[n].hd & 0x200 means the record is a gate branch for gate g = tb[n].hd & 3; the new wp is then
n + route[g] (the model).  Reports per event: gate state at the sample before and after, the route used, and the model's match.
Output data/gate_nat_<T>.json."""
from lt import *
from wptables import table, COUNT
T = int(sys.argv[1]); frames = int(sys.argv[2]) if len(sys.argv) > 2 else 2400
SN = os.path.join(sscfg.WORK, 'agents', 'tracks', 'snaps')
r = Repl2(os.path.join(SN, 'race_%d.snap' % T))
r.cmd('s 3000000')
tb = table(T); cnt = COUNT[T]
ng = r.a4w(-1808, 1)[0]
rows = []
for f in range(frames):
    out, _ = r.cmd('bp df18 400000')
    assert any('hit' in l for l in out), out[-3:]
    s = sample(r)
    s['gdir'] = r.a4w(-1814, 3); s['gpos'] = r.a4w(-1820, 3); s['gtim'] = r.a4w(-1826, 3); s['grt'] = r.a4w(-1832, 3)
    s['fc'] = r.a4w(-8072, 1)[0]
    rows.append(s)
json.dump({'T': T, 'ng': ng, 'rows': rows}, open(os.path.join(DATA, 'gate_nat_%d.json' % T), 'w'))
r.close()
print('T', T, 'gates', ng, 'frames', len(rows))

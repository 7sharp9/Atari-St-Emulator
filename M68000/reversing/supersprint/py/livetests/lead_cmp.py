"""lead_cmp.py - compare data/lead_<arm>.json against lead_ctl.json: per drone slot (0,2,3) count samples whose full state
(sx sy spd wp stun cap div qx qy hd thd acc flag) equals the control's, the first divergence with human-drone distance,
and the watch-write counts.  Also the human's rank key (laps*100000 + chk*10000 + tiles) against the best drone's at each end."""
from lt import *
import math
ctl = json.load(open(os.path.join(DATA, 'lead_ctl.json')))
keys = ['sx', 'sy', 'spd', 'wp', 'stun', 'cap', 'div', 'qx', 'qy', 'hd', 'thd', 'acc', 'flag']
def key(row, d): return row['lap'][d] * 100000 + row['chk'][d] * 10000 + row['tiles'][d]
for arm in sys.argv[1:] or ['lap', 'pos', 'fire']:
    a = json.load(open(os.path.join(DATA, 'lead_%s.json' % arm)))
    n = min(len(a['rows']), len(ctl['rows']))
    print('== arm %s vs ctl: %d samples, watch writes in run: ctl %d, arm %d; positive control seen: %s' % (arm, n, len(ctl['watch']), len(a['watch']), bool(a['poke_watch'])))
    rk = [(i, key(a['rows'][i], 1), max(key(a['rows'][i], d) for d in (0, 2, 3))) for i in (0, n // 2, n - 1)]
    print('   human key vs best-drone key at samples 0, mid, last (arm):', rk)
    ahead = sum(1 for i in range(n) if key(a['rows'][i], 1) > max(key(a['rows'][i], d) for d in (0, 2, 3)))
    print('   samples with human key > every drone key: %d of %d' % (ahead, n))
    for d in (0, 2, 3):
        same = sum(1 for i in range(n) if all(a['rows'][i][k][d] == ctl['rows'][i][k][d] for k in keys))
        first = next((i for i in range(n) if any(a['rows'][i][k][d] != ctl['rows'][i][k][d] for k in keys)), None)
        extra = ''
        if first is not None:
            hr = a['rows'][first]
            dist = math.hypot(hr['qx'][1] - hr['qx'][d], hr['qy'][1] - hr['qy'][d])
            diffk = [k for k in keys if a['rows'][first][k][d] != ctl['rows'][first][k][d]]
            extra = ' first diff sample %d (step %d), human-drone distance %.0f u (1 px = 8 u), fields %s' % (first, first * a['stride'], dist, diffk)
        print('   drone %d: %d/%d samples identical to ctl%s' % (d, same, n, extra))

"""bot_cmp.py [arm] - compare data/bot_<arm>.json (default bot) with data/bot_ctl.json frame by frame over race 1 (until the
human's lap counter reaches 4): per drone slot 0, 2, 3 the frames whose state (lead_cmp.py's fields) equals the control's, the
first divergence with the human-drone distance and bump flags, the frames the human leads on the winner's-circle rank key,
and the writers of the cap/divisor watch."""
from lt import *
import math, collections
arm = sys.argv[1] if len(sys.argv) > 1 else 'bot'
ctl = json.load(open(os.path.join(DATA, 'bot_ctl.json')))
a = json.load(open(os.path.join(DATA, 'bot_%s.json' % arm)))
keys = ['sx', 'sy', 'spd', 'wp', 'stun', 'cap', 'div', 'q38', 'q46', 'hd', 'thd', 'acc', 'flag', 'lap', 'chk', 'tiles']
def key(row, d): return row['lap'][d] * 100000 + row['chk'][d] * 10000 + row['tiles'][d]
end = next(i for i, r in enumerate(a['rows']) if r['lap'][1] >= 4)
n = end + 1
print('race 1: human lap 4 at frame %d; comparing frames 0..%d' % (end, end))
ahead = sum(1 for i in range(n) if key(a['rows'][i], 1) > max(key(a['rows'][i], d) for d in (0, 2, 3)))
first_lead = next(i for i in range(n) if key(a['rows'][i], 1) > max(key(a['rows'][i], d) for d in (0, 2, 3)))
print('human ahead of every drone on the rank key: %d of %d frames (first at frame %d)' % (ahead, n, first_lead))
print('drone laps at that frame:', [a['rows'][end]['lap'][d] for d in (0, 2, 3)])
mind = {d: min(math.hypot(a['rows'][i]['q38'][1] - a['rows'][i]['q38'][d], a['rows'][i]['q46'][1] - a['rows'][i]['q46'][d]) for i in range(n)) for d in (0, 2, 3)}
for d in (0, 2, 3):
    same = sum(1 for i in range(n) if all(a['rows'][i][k][d] == ctl['rows'][i][k][d] for k in keys))
    first = next((i for i in range(n) if any(a['rows'][i][k][d] != ctl['rows'][i][k][d] for k in keys)), None)
    extra = ''
    if first is not None:
        hr = a['rows'][first]
        dist = math.hypot(hr['q38'][1] - hr['q38'][d], hr['q46'][1] - hr['q46'][d])
        extra = ' first diff frame %d, distance %.0f u, fields %s, bump %s' % (
            first, dist, [k for k in keys if hr[k][d] != ctl['rows'][first][k][d]], hr['bump'])
    print('drone %d: %d/%d frames identical to ctl; closest approach to the human %.0f u (1 px = 8 u)%s' % (d, same, n, mind[d], extra))
for nm, x in (('ctl', ctl), (arm, a)):
    inr = [l for l in x['watch'] if int(l.split()[0][1:]) <= end]
    later = collections.Counter((l.split()[0], re.search(r'pc=\$([0-9a-f]+)', l).group(1)) for l in x['watch'] if l not in inr)
    print('cap/div watch %s: %d writes in frames 0..%d, later writes (frame, pc): %s' % (nm, len(inr), end, dict(later)))
print('positive control (REPL poke of a cap word) seen: ctl %s, %s %s' % (bool(ctl['poke_watch']), arm, bool(a['poke_watch'])))

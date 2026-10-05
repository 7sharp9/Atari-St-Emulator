"""target_check.py <log> : check the pool-2 target rule against extra_target.lua lines. Kinds 0 to 2: +144 (target index 1 or 2), +148 (record word), +150 = 180 at acquire ($280c8:
nearest live (+2 == 2) player by |dx|, player 1 only when strictly closer, ties to player 2). Kinds 3 to 6: +134 long = target record, set by $3068 at init and at throw start (same rule)."""
import sys, re, collections
P = {}
T = []
for ln in open(sys.argv[1]):
    if ln[0] == 'P':
        m = re.match(r'P (\d+) p1 (\d+) x=(\w+) y=(\w+) st=(\w+) p2 (\d+) x=(\w+) y=(\w+) st=(\w+)', ln)
        f = int(m.group(1)); P[f] = dict(u1=int(m.group(2)), x1=int(m.group(3), 16), st1=int(m.group(5)[:2], 16), u2=int(m.group(6)), x2=int(m.group(7), 16), st2=int(m.group(9)[:2], 16))
    elif ln[0] == 'T':
        d = dict(t.split('=') for t in ln.split()[2:] if '=' in t); d['f'] = int(ln.split()[1]); T.append(d)
    elif ln[0] == 'H': pass
byrec = collections.defaultdict(list)
for d in T: byrec[d['rec']].append(d)
ok = bad = skip = 0; stats = collections.Counter()
for rec, L in byrec.items():
    prev = None
    for d in L:
        k = int(d['k'])
        if k > 2: prev = d; continue
        c = int(d['c150'], 16)
        if prev and prev['f'] + 1 == d['f'] and c > int(prev['c150'], 16) and c >= 0xb0:   # acquire: +150 reloaded to 180
            p = P.get(d['f'] - 1)   # positions the code saw (the updater runs before the frame-end sample)
            x = int(d['x'], 16)
            if p and p['u1'] and p['u2']:
                live1, live2 = p['st1'] == 2, p['st2'] == 2
                d1, d2 = abs(x - p['x1']), abs(x - p['x2'])
                if live1 and live2: exp = 1 if d1 < d2 else 2
                elif live1: exp = 1
                elif live2: exp = 2
                else: exp = 0
                got = int(d['t144'], 16)
                stats[(exp, got)] += 1
                if exp == got: ok += 1
                else: bad += 1; print('MISMATCH f=%d rec=%s k=%d x=%04x d1=%d d2=%d live=%d%d exp %d got %d' % (d['f'], rec, k, x, d1, d2, live1, live2, exp, got))
            else: skip += 1
        prev = d
print('kinds 0-2 acquire events: match %d, mismatch %d, skipped (a player unused) %d' % (ok, bad, skip))
print('(expected, got):', dict(stats))

"""report.py - score table and map PNGs from results.pkl. Usage (from M68000/): uv run python reversing/powermonger/commander/bug2/report.py"""
import pickle, sys, statistics
from collections import Counter
from pathlib import Path
here = Path(__file__).resolve()
sys.path.insert(0, str(here.parent))
import follow, render, astar
from follow import DATA
d = pickle.load(open(DATA / 'pairs.pkl', 'rb'))
pairs = d['pairs']
R = pickle.load(open(DATA / 'results.pkl', 'rb'))
cnt = Counter(p['cls'] for p in pairs)
print('pairs by class (recomputed):', dict(cnt), 'total', len(pairs))
b = {i: r for i, r in R.items() if r['cls'] == 'b'}
print('b pairs scored:', len(b), ' A* verified', sum(r['astar']['verified'] for r in b.values()))

# step 2: control
print('\n== control: the game-rule tick model (astar.Map.simulate_walk, 3000 ticks) ==')
for cls in ('a-twater', 'a', 'b', 'c'):
    q = [r for r in R.values() if r['cls'] == cls]
    st = sum(1 for r in q if not r['ctl']['arrives'])
    print('%-9s n=%4d model stuck %4d  arrives %4d' % (cls, len(q), st, len(q) - st))
stuck_all = [r for r in R.values() if r['cls'] in ('a-twater', 'a', 'b')]
print('stuck pairs (census) where model says stuck: %d/%d' % (sum(1 for r in stuck_all if not r['ctl']['arrives']), len(stuck_all)))
arr = [(i, R[i]) for i in R if R[i]['cls'] == 'b' and R[i]['ctl']['arrives']]
print('206-style disagreements:', len(arr), ' ticks median', statistics.median(r['ctl']['tick'] for _, r in arr) if arr else None)
# broken-model control: water-blind sampler
mpcache = {}
def water_blind(p):
    return True
print('(broken-model control: control_water_blind.py, a probe that never sees water, gives stuck 0/%d)' % len(stuck_all))

# step 3a
print('\n== (a) component labels vs the A* triangle graph ==')
ok_pairs = [r for r in R.values()]
for name in ('lat', 'c4', 'c8'):
    agree = sum(1 for r in ok_pairs if r['reach'][name] == r['reach']['tri'])
    fp = sum(1 for r in ok_pairs if r['reach'][name] and not r['reach']['tri'])
    fn = sum(1 for r in ok_pairs if (not r['reach'][name]) and r['reach']['tri'])
    print('%-4s agree %d/%d  says reachable but A* graph unreachable %d, says unreachable but reachable %d' % (name, agree, len(ok_pairs), fp, fn))
# ground truth on the physical side: every b/c pair is reachable (verified path / straight walk), every a pair has no path in the graph
print('b pairs labelled reachable by lat/c4/c8/tri:', *[sum(r['reach'][n] for r in b.values()) for n in ('lat', 'c4', 'c8', 'tri')], 'of', len(b))
for cls in ('a', 'a-twater', 'c'):
    q = [r for r in R.values() if r['cls'] == cls]
    print('%-9s reachable by lat/c4/c8/tri:' % cls, *[sum(r['reach'][n] for r in q) for n in ('lat', 'c4', 'c8', 'tri')], 'of', len(q))

# step 3b/c
def stats(names, label, bytes_):
    solved, ratios, whys = 0, [], Counter()
    for i, r in b.items():
        cands = [r['algos'][n] for n in names]
        okc = [c for c in cands if c['ok']]
        if okc:
            solved += 1
            best = min(okc, key=lambda c: c['length'])
            ratios.append(best['length'] / r['astar']['len'])
        else:
            whys[cands[0]['why']] += 1
    ratios.sort()
    q = lambda f: ratios[min(len(ratios) - 1, int(f * len(ratios)))]
    print('%-34s solved %4d/%d  ratio median %.2f p90 %.2f worst %.2f  fail %s  state %s' % (label, solved, len(b), statistics.median(ratios), q(.9), ratios[-1], dict(whys), bytes_))
print('\n== (b)/(c) followers on the %d reachable-with-water-on-line pairs ==' % len(b))
stats(['bug2_L'], 'Bug2 left-hand', '1 flag byte + hit dist 2 B + origin 4 B (7 B; 3 B if the saved origin is reused)')
stats(['bug2_R'], 'Bug2 right-hand', 'same')
stats(['bug2_auto'], 'Bug2 hand chosen by smaller turn', 'same')
stats(['bug2_L', 'bug2_R'], 'Bug2 try both, keep shorter (oracle)', 'two runs; not a per-unit state')
stats(['kclear_L'], 'k-clear (k=4) left', '1 flag byte')
stats(['kclear_R'], 'k-clear (k=4) right', '1 flag byte')
stats(['kclear_L', 'kclear_R'], 'k-clear try both (oracle)', '')
stats(['kcd_L'], 'k-clear+closer-than-hit left', '1 flag byte + 2 B')
stats(['kcd_R'], 'k-clear+closer-than-hit right', '1 flag byte + 2 B')
stats(['kcd_L', 'kcd_R'], 'k-clear+closer try both (oracle)', '')
stats(['bug2_L_a0'], 'BROKEN control: Bug2 L, a0=0', '')
# unique to the loops
print('\nloop / cap counts per algo on b:')
for n in b[next(iter(b))]['algos']:
    print(' ', n, dict(Counter(r['algos'][n]['why'] for r in b.values())))
print('\nmedian ticks bug2_L (solved):', statistics.median(r['algos']['bug2_L']['ticks'] for r in b.values() if r['algos']['bug2_L']['ok']))
print('A* path ticks proxy: median len/speed not computed')
# per series
print('\nBug2 best-of-both by series:')
byser = {}
for i, r in b.items():
    byser.setdefault(pairs[i]['series'], []).append(r)
for s, q in byser.items():
    ok = sum(1 for r in q if r['algos']['bug2_L']['ok'] or r['algos']['bug2_R']['ok'])
    okL = sum(1 for r in q if r['algos']['bug2_L']['ok'])
    print(' %-10s n=%4d  L %4d  best-of-both %4d' % (s, len(q), okL, ok))
# the other classes
print('\nBug2 on the other classes (should arrive for c, never for a):')
for cls in ('c', 'a'):
    q = [r for r in R.values() if r['cls'] == cls]
    for n in ('bug2_L', 'bug2_R'):
        print(' ', cls, n, dict(Counter(r['algos'][n]['why'] for r in q)), 'n follow ticks>0:', sum(1 for r in q if r['algos'][n]['nfollow'] > 0))

# step 4 PNGs
def pick():
    L = [(r['algos']['bug2_L'], i) for i, r in b.items() if r['algos']['bug2_L']['ok']]
    ratio = lambda i, n: r_ratio(i, n)
def r_ratio(i, n):
    return b[i]['algos'][n]['length'] / b[i]['astar']['len']
okb = [i for i in b if b[i]['algos']['bug2_L']['ok']]
med = statistics.median(r_ratio(i, 'bug2_L') for i in okb)
typical = min(okb, key=lambda i: abs(r_ratio(i, 'bug2_L') - med) + (0 if b[i]['astar']['len'] > 1500 else 5))
worst = max(okb, key=lambda i: r_ratio(i, 'bug2_L'))
fails = [i for i in b if not b[i]['algos']['bug2_L']['ok']]
failb = [i for i in b if not b[i]['algos']['bug2_L']['ok'] and not b[i]['algos']['bug2_R']['ok']]
fail = (failb or fails or [None])[0]
trs = {}
def tr_of(p):
    if p['plane'] not in trs:
        trs[p['plane']] = follow.Terrain(astar.Map(str(follow.ROOT / 'scratchpad/pm148/arms/long' / (p['snap'] + '.snap'))))
    return trs[p['plane']]
for tag, i in (('typical', typical), ('worst', worst), ('failure', fail)):
    if i is None:
        print('no', tag); continue
    p = pairs[i]; tr = tr_of(p)
    s, t = (p['x'], p['y']), (p['tx'], p['ty'])
    for hand, nm in ((1, 'L'),):
        res, pts = follow.trace(tr, s, t, p['speed'], algo='bug2', hand=hand, a0=16, turn=16, max_ticks=min(60000, 2 * 400000))
        if len(pts) > 6000:
            pts = pts[:6000]
        fn = str(DATA / 'maps' / ('map_%s.png' % tag))
        render.render(tr, s, t, b[i]['astar']['pts'], pts, fn, '%s %s obj%d speed %d bug2_L %s ratio %s' % (tag, p['series'], p['obj'], p['speed'], res['why'], ('%.2f' % (res['length'] / b[i]['astar']['len'])) if res['ok'] else '-'))
        print(tag, p['series'], p['snap'], 'obj', p['obj'], s, t, 'bug2_L', res['why'], res['ticks'], 'A* len %.0f' % b[i]['astar']['len'], 'bug2 len %.0f' % res['length'], '->', fn)

"""hazard_seeds.py [nseeds] - hazard counts under different RNG seeds (the open item of hazard_by_R.py: its 6 variants all had the same RNG state).

Start ai_econ/data/hz_0.snap (paused at $bec0, the top of $be40's car loop; the XBIOS Random() seed is the longword at $29b8).  For each R in
RS and each of nseeds random seeds: poke R and the seed (labelled pokes), run to $c32e (after the hazard initialisers) and read
  -1792 (flashing-sign flag, $b22a)  -1776 (roving hazard flag, $b094)  -1858 (random hazard tiles, $a6c4)  -1766 (blocking tiles, $a8a0).
A second pass with the same pokes logs every call of the RNG wrapper $a666 (stop at its `unlk`, $a686) as (return address, n, result) up to
the step count of pass 1, so each decision is attributed to its own call site and reproduced from the code's rule:
  roving   : R > 3 and rand(2) != 0        [call returning to $c2f6]
  tiles    : min(3, rand(R/6 + 1))          [call returning to $a6da]
  blocking : 4 if R >= 16 and rand(20) >= 10 else 0   [call returning to $a8b8]     (-1766 is R-16 first; checked against the code's value)
Prints per R: the counts of each outcome over the seeds, the chi-square-free comparison with the expected frequency, and the match count of
live vs the rule applied to the logged call.
"""
import random, collections
from lt import *
nseeds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
RS = [0, 3, 4, 6, 12, 17, 50]
base = os.path.join(AI, 'hz_0.snap')
rnd = random.Random(20261017)
seeds = [rnd.randrange(1, 1 << 32) for _ in range(nseeds)]

def run(R, seed, steps=None):
    r = Repl2(base)
    setwords(r, {A4 - 1748: R})
    r.cmd('w 29b8 %08x' % seed)
    calls = []
    if steps is None:
        out, regs = r.cmd('bpc c32e 1 600000')
        assert regs['PC'] == 0xc32e, hex(regs['PC'])
        n = int(re.search(r'after (\d+) step', ' '.join(out)).group(1)) if any('after' in l for l in out) else None
        res = (r.a4w(-1792, 1)[0], r.a4w(-1776, 1)[0], r.a4w(-1858, 1)[0], r.a4w(-1766, 1)[0])
        r.close()
        return res, n
    used = 0
    while True:
        out, regs = r.cmd('bp a686 %d' % (steps - used + 1))
        if not any('hit' in l for l in out): break
        m = re.search(r'after (\d+) step', ' '.join(out)); used += int(m.group(1))
        if used > steps: break
        a6 = regs['A6']
        ret = struct.unpack('>I', r.mem(a6 + 4, 4))[0] & 0xffffff
        n = r.words(a6 + 8, 1)[0]
        calls.append((ret, n, regs['D0'] & 0xffff))
    r.close()
    return calls, used

tab = {}
tot = ok = 0
for R in RS:
    stats = collections.Counter()
    for sd in seeds:
        res, steps = run(R, sd)
        calls, _ = run(R, sd, steps)
        A, rov, tiles, blk = res
        byret = collections.defaultdict(list)
        for ret, n, d0 in calls: byret[ret].append((n, d0))
        c = []
        # decisions from the logged calls
        pred_rov = None
        if R > 3:
            xs = byret.get(0xc2f6, [])
            pred_rov = 1 if xs and xs[0][1] != 0 else 0
        else:
            pred_rov = 0
        xs = byret.get(0xa6da, [])
        pred_tiles = min(3, xs[0][1]) if xs else None
        pred_blk = None
        if R >= 16:
            xs = byret.get(0xa8b8, [])
            pred_blk = 4 if xs and xs[0][1] >= 10 else 0
        else:
            pred_blk = 0
        checks = [('A', A, 1 if (R + 1) % 3 == 0 else 0), ('roving', rov, pred_rov), ('tiles', tiles, pred_tiles), ('blocking', blk, pred_blk)]
        for name, live, pred in checks:
            tot += 1; ok += (live == pred)
            if live != pred: print('  MISMATCH R=%d seed=%08x %s live %s pred %s calls %s' % (R, sd, name, live, pred, calls[:6]))
        stats[('rov', rov)] += 1; stats[('tiles', tiles)] += 1; stats[('blk', blk)] += 1; stats[('A', A)] += 1
        stats['ncalls_%d' % len(calls)] += 1
    tab[R] = stats
    print('R=%2d over %d seeds: A %s | roving %s | tiles %s | blocking %s | rand calls per init %s' % (R, nseeds,
          {k[1]: v for k, v in stats.items() if k[0] == 'A'}, {k[1]: v for k, v in sorted(stats.items(), key=str) if k[0] == 'rov'},
          {k[1]: v for k, v in sorted(stats.items(), key=str) if k[0] == 'tiles'}, {k[1]: v for k, v in sorted(stats.items(), key=str) if k[0] == 'blk'},
          sorted(k for k in stats if isinstance(k, str))), flush=True)
print('live == rule-applied-to-logged-call: %d / %d' % (ok, tot))

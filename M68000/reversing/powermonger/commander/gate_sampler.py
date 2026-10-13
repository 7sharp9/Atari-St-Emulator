"""gate_sampler.py - the Python $1648e (astar.Map.sample = tools/pm_fsm_ref.terrain_sample) against the real
68000: `callcap 1648e 100 - D0=deadbeef D6=<x> D7=<y>` per point, one REPL per snapshot; the colour is the
low byte of D0 on return.

Point set per snapshot (fixed RNG seed): 300 random in-map points; for up to 250 shore cells where exactly one
triangle byte is 0 ($418ad+c or $438ee+c), both triangle centroids and 6 points hugging the diagonal
(on it and one unit either side); 40 off-map points (x >= $4000, x < 0, y < 0).

Usage (from M68000/): uv run python reversing/powermonger/commander/gate_sampler.py [snap ...]
Default snaps: scratchpad/pm142/rand1.snap, scratchpad/pm148/arms/long/X10G_k25_c40.snap.
Work files go to $CMD_WORK/sampler_gate (default scratchpad/cmd1)."""
import os
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astar  # noqa: E402

ROOT = astar.ROOT
WORK = Path(os.environ.get('CMD_WORK', ROOT / 'scratchpad' / 'cmd1')) / 'sampler_gate'
WORK.mkdir(parents=True, exist_ok=True)
DLL = ROOT / 'bin' / 'Debug' / 'net8.0' / 'M68000.dll'


def points(mp, seed):
    rnd = random.Random(seed)
    pts = []
    for _ in range(300):
        pts.append(('random', rnd.randrange(0x4000), rnd.randrange(0x8000)))
    shore = [c for c in range(64 * 128) if (mp.ram[astar.PLANE_A + c] == 0) != (mp.ram[astar.PLANE_B + c] == 0)]
    rnd.shuffle(shore)
    for c in shore[:250]:
        cy, cx = divmod(c, 64)
        bx, by = cx * 256, cy * 256
        for h in (0, 1):
            x, y = mp.node_point(2 * c + h)
            pts.append(('shore-centroid', x, y))
        t = rnd.randrange(1, 254)
        if mp.diag[c]:
            for lx, ly in ((t, 255 - t), (t, 256 - t), (t + 1, 255 - t), (t, 254 - t), (255, 1), (0, 255)):
                pts.append(('shore-diag', bx + lx, by + (ly & 0xff)))
        else:
            for lx, ly in ((t, t), (t + 1, t), (t, t + 1), (0, 0), (255, 255), (255, 254)):
                pts.append(('shore-diag', bx + lx, by + ly))
    for _ in range(40):
        k = rnd.randrange(3)
        if k == 0:
            pts.append(('off-x-hi', 0x4000 + rnd.randrange(0x3000), rnd.randrange(0x8000)))
        elif k == 1:
            pts.append(('off-x-neg', -1 - rnd.randrange(0x2000), rnd.randrange(0x8000)))
        else:
            pts.append(('off-y-neg', rnd.randrange(0x4000), -1 - rnd.randrange(0x4000)))
    return pts, len(shore)


def run(snap, tag):
    mp = astar.Map(ROOT / snap)
    pts, nshore = points(mp, 1648)
    repl = WORK / ('%s.repl' % tag)
    with open(repl, 'w') as f:
        for _k, x, y in pts:
            f.write('callcap 1648e 100 - D0=deadbeef D6=%08x D7=%08x\n' % (x & 0xffff, y & 0xffff))
        f.write('q\n')
    out = WORK / ('%s.out' % tag)
    env = dict(os.environ, ATARI_NOTRACE='1')
    with open(repl) as fi, open(out, 'w') as fo, open(WORK / ('%s.err' % tag), 'w') as fe:
        subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(snap), 'repl'], stdin=fi, stdout=fo, stderr=fe,
                       cwd=ROOT, env=env, check=False)
    got = []
    txt = open(out).read().splitlines()
    for i, line in enumerate(txt):
        if line.startswith('--- callcap $01648e'):
            assert 'returned' in line, line
            m = re.search(r'D0 \$[0-9a-f]{8}->\$(dead[0-9a-f]{4})', txt[i + 1]) if i + 1 < len(txt) else None
            got.append(int(m.group(1), 16) & 0xff if m else None)
    assert len(got) == len(pts), 'expected %d callcaps, parsed %d (see %s)' % (len(pts), len(got), out)
    by = {}
    bad = []
    for (k, x, y), g in zip(pts, got):
        p = mp.sample(x, y)
        ok = p == g
        n, okn = by.get(k, (0, 0))
        by[k] = (n + 1, okn + ok)
        if not ok:
            bad.append((k, x, y, p, g))
    tot = sum(v[1] for v in by.values())
    print('%s: %d/%d match (%d shore cells (one triangle water, one land) on this map)' % (snap, tot, len(pts), nshore))
    for k, (n, okn) in by.items():
        print('   %-15s %d/%d' % (k, okn, n))
    for b in bad[:10]:
        print('   MISMATCH', b)
    # the shore points must hit both outcomes, or the gate does not test the triangle choice
    zero = sum(1 for (k, x, y) in pts if k.startswith('shore') and mp.sample(x, y) == 0)
    print('   shore points sampling water %d, land %d' % (zero, sum(1 for p in pts if p[0].startswith('shore')) - zero))
    return tot, len(pts)


if __name__ == '__main__':
    snaps = sys.argv[1:] or ['scratchpad/pm142/rand1.snap', 'scratchpad/pm148/arms/long/X10G_k25_c40.snap']
    T = N = 0
    for s in snaps:
        t, n = run(s, Path(s).stem)
        T += t
        N += n
    print('TOTAL %d/%d' % (T, N))

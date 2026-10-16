"""gate_line.py - tools/pm_fsm_ref.terrain_sample ($1648e) against the 68000 on the points stuck_census_exact.py
actually samples: `callcap 1648e 100 - D0=deadbeef D6=<x> D7=<y>` per point, one REPL per snapshot; the colour is the
low byte of D0 on return.

Point set per snapshot (fixed RNG seed): the ghost-walk points (stuck_census_exact.ghost_points) of every man that
snapshot's census reports stuck against the previous chunk: sorted into four classes by the
model (water / land) and by the cell (half-wet: exactly one triangle byte 0), up to CAP/4 of each; plus 60 random in-map points.

Usage (from M68000/): uv run python reversing/powermonger/py/fsm/gate_line.py <chunk snap> [...]
Work files go to ${PM_WORK:-scratchpad/pm162}/water/gate."""
import os
import random
import re
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve()
sys.path.insert(0, str(here.parent))
import stuck_census_exact as sce  # noqa: E402

ROOT = sce.ROOT
WORK = ROOT / os.environ.get('PM_WORK', 'scratchpad/pm162') / 'water' / 'gate'
WORK.mkdir(parents=True, exist_ok=True)
DLL = ROOT / 'bin' / 'Debug' / 'net8.0' / 'M68000.dll'
CAP = 300
A, B = sce.astar.PLANE_A, sce.astar.PLANE_B


def stuck_men(snap):
    m = re.match(r'(.*)_c(\d+)\.snap$', str(snap))
    prevsnap = '%s_c%d.snap' % (m.group(1), int(m.group(2)) - 1)
    mp = sce.astar.Map(snap)
    cur, prev = sce.men(mp.ram), sce.men(sce.astar.Map(prevsnap).ram)
    out = []
    for i, v in cur.items():
        p = prev.get(i)
        if p and (p['tx'], p['ty']) == (v['tx'], v['ty']):
            d0 = max(abs(p['tx'] - p['x']), abs(p['ty'] - p['y']))
            d1 = max(abs(v['tx'] - v['x']), abs(v['ty'] - v['y']))
            if d1 >= d0 - 256:
                out.append(v)
    return mp, out


def points(snap):
    mp, ms = stuck_men(snap)
    rnd = random.Random(1648)
    cls = {'water-shorecell': [], 'water-wetcell': [], 'land-shorecell': [], 'land': []}
    seen = set()
    for v in ms:
        for x, y in sce.ghost_points(mp, v):
            if (x, y) in seen:
                continue
            seen.add((x, y))
            c = ((y & 0xffff) >> 8) * 64 + ((x & 0xffff) >> 8)
            half = 0 <= c < 8192 and (mp.ram[A + c] == 0) != (mp.ram[B + c] == 0)
            if mp.sample(x, y) == 0:
                cls['water-shorecell' if half else 'water-wetcell'].append((x, y))
            else:
                cls['land-shorecell' if half else 'land'].append((x, y))
    pts = []
    for k, l in cls.items():
        rnd.shuffle(l)
        pts += [(k, x, y) for x, y in l[:CAP // 4]]
    pts += [('random', rnd.randrange(0x4000), rnd.randrange(0x8000)) for _ in range(60)]
    return mp, pts, len(ms)


def run(snap):
    mp, pts, nmen = points(snap)
    tag = Path(snap).stem
    repl = WORK / (tag + '.repl')
    with open(repl, 'w') as f:
        for _k, x, y in pts:
            f.write('callcap 1648e 100 - D0=deadbeef D6=%08x D7=%08x\n' % (x & 0xffff, y & 0xffff))
        f.write('q\n')
    out = WORK / (tag + '.out')
    env = dict(os.environ, ATARI_NOTRACE='1')
    with open(repl) as fi, open(out, 'w') as fo, open(WORK / (tag + '.err'), 'w') as fe:
        subprocess.run(['dotnet', 'exec', str(DLL), 'resume', str(snap), 'repl'], stdin=fi, stdout=fo, stderr=fe,
                       cwd=ROOT, env=env, check=False)
    txt = open(out).read().splitlines()
    got = []
    for i, line in enumerate(txt):
        if line.startswith('--- callcap $01648e'):
            assert 'returned' in line, line
            m = re.search(r'D0 \$[0-9a-f]{8}->\$(dead[0-9a-f]{4})', txt[i + 1]) if i + 1 < len(txt) else None
            got.append(int(m.group(1), 16) & 0xff if m else None)
    assert len(got) == len(pts), 'expected %d callcaps, parsed %d (see %s)' % (len(pts), len(got), out)
    by, bad = {}, []
    for (k, x, y), g in zip(pts, got):
        p = mp.sample(x, y)
        n, ok = by.get(k, (0, 0))
        by[k] = (n + 1, ok + (p == g))
        if p != g:
            bad.append((k, x, y, p, g))
    tot = sum(v[1] for v in by.values())
    zero_emu = sum(1 for g in got if g == 0)
    print('%s: %d stuck men, %d/%d match; 68000 returned 0 (water) on %d' % (snap, nmen, tot, len(pts), zero_emu))
    for k, (n, ok) in by.items():
        print('   %-11s %d/%d' % (k, ok, n))
    for b in bad[:10]:
        print('   MISMATCH', b)
    return tot, len(pts)


if __name__ == '__main__':
    T = N = 0
    for s in sys.argv[1:]:
        t, n = run(s)
        T += t
        N += n
    print('TOTAL %d/%d' % (T, N))

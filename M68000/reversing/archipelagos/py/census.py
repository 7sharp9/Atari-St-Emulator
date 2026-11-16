#!/usr/bin/env python3
"""census.py: island_model.py over every island number, from the disk image and isl/ent1.snap alone (model, not live).

Per island: stamp count and shapes, land cells, 4-connected land pieces and the largest, and every RAM byte outside
the map ($3000..$12fff) that the build changes. Islands up to 100 take their block from the disk (`disk_block`);
above 100 the block is island_params.model(N) plus the range table $16166 writes at $16222..$16272 (one entry,
keyed to iteration 1: a centred square of side 3 * count - 20).

usage: uv run python reversing/archipelagos/py/census.py [N ...]       (default 1-9999; a-b and a-b/step ranges)
       uv run python reversing/archipelagos/py/census.py --summary   (the summary from the last census.json)
       uv run python reversing/archipelagos/py/census.py --edges     (how near an edge the stamps start: the range
       tables' bound and the starts drawn, disk islands and 101-164 (every parameter set); picks gate_census_live's islands)
       J=<workers> (default 10). Writes scratchpad/archipelagos/census/census.json (CELLS=1 adds each map as hex),
       then prints the summary: out-of-map changes, the edge control, distinct parameter sets above 100 and
       whether N and N+64 share one, land overlap of N vs N+64 against N vs N+1, and medians by range of N.
About 6 min for 1-9999 on 10 cores.
"""
import os, sys, json, statistics as st
from multiprocessing import Pool
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
import island_model as im, island_params as ip
from gfxview import load_ram

ROOT = im.d
OUT = os.path.join(ROOT, 'scratchpad', 'archipelagos', 'census')
RAM, _ = load_ram(os.path.join(ROOT, 'scratchpad', 'archipelagos', 'isl', 'ent1.snap'))
DISK = open(im.DISK, 'rb').read()
SPECIAL = set(range(5, 101, 5))

def ram_for(N):
    r = bytearray(RAM); r[0x1d566:0x1d568] = N.to_bytes(2, 'big')
    if N <= 100:
        r[0x1697a:0x1697a + 42] = im.disk_block(DISK, N)
    else:
        p = ip.model(N)
        for a, v in p.items(): r[a:a + 2] = (v & 0xFFFF).to_bytes(2, 'big')
        c = (p[0x1697a] * 3 - 20) & 0xFF; o = ((0xFF - c) & 0xFF) >> 1
        r[0x1698c:0x16990] = bytes([c, c, o, o])
        r[0x16990:0x16992] = (1).to_bytes(2, 'big')
        for a in (0x16996, 0x1699c, 0x169a2): r[a:a + 2] = b'\0\0'
    return r

def pieces(cells):
    seen = bytearray(65536); sizes = []
    for i in range(65536):
        if cells[i] != 4 and not seen[i]:
            st_ = [i]; seen[i] = 1; k = 0
            while st_:
                j = st_.pop(); k += 1; y, x = divmod(j, 256)
                for jj in (j + 1 if x < 255 else -1, j - 1 if x > 0 else -1, j + 256 if y < 255 else -1, j - 256 if y > 0 else -1):
                    if jj >= 0 and cells[jj] != 4 and not seen[jj]: seen[jj] = 1; st_.append(jj)
            sizes.append(k)
    return sizes

def outside(before, after):
    return [(a, before[a], after[a]) for a in range(len(before)) if not (0x3000 <= a < 0x13000) and before[a] != after[a]]

def map_of(N):
    return im.Model(ram_for(N)).run(DISK)

def one(N):
    r = ram_for(N); before = bytes(r)
    M = im.Model(r); cells = M.run(DISK)
    sizes = pieces(cells)
    return dict(N=N, special=N in SPECIAL, count=int.from_bytes(r[0x1697a:0x1697c], 'big'), shapes=M.shapes,
                land=sum(c != 4 for c in cells), pieces=len(sizes), largest=max(sizes) if sizes else 0,
                outside=outside(before, M.m), cells=cells.hex() if os.environ.get('CELLS') else None)

def edge_control():
    """Island 150's block with the range table forced to rows 0..3 and every stamp a circle: must write outside."""
    r = ram_for(150)
    r[0x1698c:0x16990] = bytes([3, 255, 0, 0])
    r[0x16980:0x16986] = (0).to_bytes(2, 'big') + (0).to_bytes(2, 'big') + (100).to_bytes(2, 'big')
    before = bytes(r); M = im.Model(r); M.run(DISK)
    o = outside(before, M.m)
    return len(o), (min(a for a, _, _ in o), max(a for a, _, _ in o)) if o else None

def land_overlap(a, b):
    A = {i for i, c in enumerate(a) if c != 4}; B = {i for i, c in enumerate(b) if c != 4}
    return len(A & B) / len(A | B)

class StartLog(im.Model):
    """The model, recording each stamp's start cell as (distance to the nearest edge, shape)."""
    def shape(self, D3, D4):
        y, x = divmod(D3, 256); self.starts.append(min(x, y, 255 - x, 255 - y)); return super().shape(D3, D4)


def edges():
    disk = [n for n in range(1, 101) if n not in SPECIAL]
    bound = []
    for N in disk:                                                # the range table's own bound, per used entry
        r = ram_for(N); tab = r[0x1698c:0x1698c + 24]; cnt = int.from_bytes(r[0x1697a:0x1697c], 'big')
        for k in range(4):
            if 1 <= int.from_bytes(tab[6 * k + 4:6 * k + 6], 'big') <= cnt:
                y0, x0 = tab[6 * k + 2], tab[6 * k + 3]
                bound.append((min(y0, x0, 255 - (y0 + tab[6 * k]), 255 - (x0 + tab[6 * k + 1])), N))
    print('range-table bound, disk islands (distance, N):', sorted(bound)[:4])
    for name, ns in (('disk', disk), ('101-164', range(101, 165))):
        rows = []
        for N in ns:
            M = StartLog(ram_for(N)); M.starts = []; M.run(DISK); rows.append((min(M.starts), N))
        print(f'stamp starts drawn, {name} (nearest-edge distance, N):', sorted(rows)[:6])
    hi = [(ip.model(N)[0x1697a], ip.model(N)[0x1697c], N) for N in range(101, 165)]
    print('above 100, most stamps (count, P_c, N):', sorted(hi, reverse=True)[:3],
          '| largest P_c:', sorted(hi, key=lambda t: (t[1], t[0]), reverse=True)[:3])


def parse(args):
    for a in args:
        if '-' in a:
            rng, _, step = a.partition('/'); lo, hi = map(int, rng.split('-'))
            yield from range(lo, hi + 1, int(step or 1))
        else: yield int(a)

def summary(rows, pool):
    proc = [r for r in rows if not r['special']]
    ow = [r for r in proc if r['outside']]
    print(f'out-of-map: {len(ow)} of {len(proc)} procedural islands change a byte outside $3000..$12fff')
    n, span = edge_control()
    print(f'  control (stamps forced to rows 0..3, circles): {n} bytes changed' + (f', ${span[0]:x}..${span[1]:x}' if span else ''))
    P = [tuple(sorted(ip.model(N).items()))[:-1] for N in range(101, 10000)]
    print(f'parameter sets over 101..9999 (build seed excluded): {len(set(P))} distinct; '
          f'N and N+64 share one: {all(P[i] == P[i + 64] for i in range(len(P) - 64))}')
    pairs = [(1000, 1064), (1000, 1128), (1000, 1192), (5000, 5064)] + [(n, n + 1) for n in range(1000, 1063)]
    need = sorted({x for p in pairs for x in p})
    cells = dict(zip(need, pool.map(map_of, need)))
    s64 = [land_overlap(cells[a], cells[b]) for a, b in pairs[:4]]
    s1 = [land_overlap(cells[a], cells[b]) for a, b in pairs[4:]]
    print('land overlap (Jaccard) N vs N+64k:', ' '.join(f'{a}/{b} {x:.3f}' for (a, b), x in zip(pairs[:4], s64)),
          f'| N vs N+1 over 1000..1062: median {st.median(s1):.3f}, max {max(s1):.3f}')
    print('medians by range (procedural islands): stamps, land cells, pieces, largest piece')
    for lo, hi in ((1, 20), (21, 40), (41, 60), (61, 80), (81, 100), (101, 1000), (1001, 3000), (3001, 6000), (6001, 9999)):
        g = [r for r in proc if lo <= r['N'] <= hi]
        if g:
            f = lambda k: st.median(r[k] for r in g)
            print(f'  {lo:>5}-{hi:<5} n={len(g):>4}  {f("count"):>5}  {f("land"):>7}  {f("pieces"):>5}  {f("largest"):>7}')
    fl = [(N, int.from_bytes(im.disk_block(DISK, N)[14:16], 'big')) for N in range(1, 101) if N not in SPECIAL]
    print('share of stamps allowed to touch ($16988), disk islands, median by 20s:',
          [st.median(v for n, v in fl if lo <= n < lo + 20) for lo in (1, 21, 41, 61, 81)],
          '| above 100: range', min(ip.model(N)[0x16988] for N in range(101, 10000)), '..',
          max(ip.model(N)[0x16988] for N in range(101, 10000)))

if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--edges']:
        edges(); sys.exit()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'census.json')
    with Pool(int(os.environ.get('J', '10'))) as p:
        if args == ['--summary']:
            rows = json.load(open(path))
        else:
            rows = sorted(p.imap_unordered(one, list(parse(args or ['1-9999'])), chunksize=4), key=lambda r: r['N'])
            json.dump(rows, open(path, 'w'))
        print(f'{len(rows)} islands, {os.path.relpath(path, ROOT)}')
        summary(rows, p)

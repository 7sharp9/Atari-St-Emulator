"""flatten.py - fewest clicks to make an NxN-cell building site flat (all (N+1)^2 corners equal T), on the proven
raise/lower model (popgen.Gen.raise_pt / lower_pt, cost 4*changes+10, terrain.md section 2).
Search: beam search over clicks (raise or lower at any corner within the site + margin 2), potential
P(T) = sum over site corners |h - T|; target T tried for 0..8; stop at P == 0.  Result is an upper bound (heuristic).
Lower bound (reversing/ideas.md): ceil(P0 / M) with M = the most site-corner height change one click makes on the
INITIAL map (max over all clicks); not rigorous (cascades can grow as the terrain steepens), reported as the ideas file states it."""
import os, sys, json, copy
from causelib import *
def site_corners(x0, y0, n): return [(x, y) for y in range(y0, y0+n+1) for x in range(x0, x0+n+1)]
def click(h, c, kind):
    g = Gen(0); g.h = list(h); g.raises = 0
    (g.raise_pt if kind == 'r' else g.lower_pt)(*c)
    return g.h, 4*g.raises + 10
def search(h0, x0, y0, n, T, width=60, depth=14, margin=2):
    sc = site_corners(x0, y0, n)
    P = lambda h: sum(abs(h[y*N+x] - T) for x, y in sc)
    cand = [(x, y) for x in range(max(0, x0-margin), min(64, x0+n+margin)+1) for y in range(max(0, y0-margin), min(64, y0+n+margin)+1)]
    beam = [(P(h0), 0, h0, [])]
    seen = {tuple(h0)}
    for d in range(depth):
        nxt = []
        for p, mana, h, seq in beam:
            if p == 0: return seq, mana
            for c in cand:
                for kind in 'rl':
                    h2, cost = click(h, c, kind)
                    if h2 == h: continue
                    t = tuple(h2)
                    if t in seen: continue
                    seen.add(t); nxt.append((P(h2), mana+cost, h2, seq + [(kind, c)]))
        if not nxt: return None
        nxt.sort(key=lambda e: (e[0], e[1])); beam = nxt[:width]
        for p, mana, h, seq in beam:
            if p == 0: return seq, mana
    return None
def lower_bound(h0, x0, y0, n, T, margin=2):
    sc = site_corners(x0, y0, n); P0 = sum(abs(h0[y*N+x] - T) for x, y in sc)
    M = 1
    for x in range(max(0, x0-margin), min(64, x0+n+margin)+1):
        for y in range(max(0, y0-margin), min(64, y0+n+margin)+1):
            for kind in 'rl':
                h2, _ = click(h0, (x, y), kind)
                M = max(M, sum(abs(h2[yy*N+xx] - h0[yy*N+xx]) for xx, yy in sc))
    return -(-P0 // M), P0, M
if __name__ == '__main__':
    snap = sys.argv[1]; x0, y0, n = map(int, sys.argv[2:5])
    m = ram(os.path.join(WORK, snap + '.snap')); h = heights(m)
    sc = site_corners(x0, y0, n)
    print('site', snap, (x0, y0), n, 'heights', [[h[y*N+x] for x in range(x0, x0+n+1)] for y in range(y0, y0+n+1)])
    best = None
    for T in range(0, 9):
        lb, P0, M = lower_bound(h, x0, y0, n, T)
        r = search(h, x0, y0, n, T)
        print(' T', T, 'P0', P0, 'M', M, 'LB', lb, 'found', r and (len(r[0]), r[1]), flush=True)
        if r and (best is None or (len(r[0]), r[1]) < (len(best[1][0]), best[1][1])): best = (T, r, lb)
    T, (seq, mana), lb = best
    hh = list(h)
    for kind, c in seq: hh, _ = click(hh, c, kind)
    flat = len({hh[y*N+x] for x, y in sc}) == 1
    print('BEST T', T, 'clicks', len(seq), 'mana', mana, 'LB at that T', lb, 'flat', flat, seq)

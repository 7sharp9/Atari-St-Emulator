"""run_all.py - score the stuck pairs: control model, component labels, A* paths, Bug2 / k-clear followers.
Usage (from M68000/): uv run python reversing/powermonger/commander/bug2/run_all.py [procs]   -> results.pkl
Input: pairs.pkl from extract_pairs.py (which re-runs classify_stuck.py's census loop)."""
import math, pickle, sys, time
from collections import deque
from multiprocessing import Pool
from pathlib import Path
here = Path(__file__).resolve()
sys.path.insert(0, str(here.parent))
import follow
from follow import DATA
from follow import astar, ROOT

ALGOS = {   # name -> kwargs for follow.run
    'bug2_L': dict(algo='bug2', hand=1), 'bug2_R': dict(algo='bug2', hand=-1), 'bug2_auto': dict(algo='bug2', hand=0),
    'kclear_L': dict(algo='kclear', hand=1, k=4), 'kclear_R': dict(algo='kclear', hand=-1, k=4),
    'kcd_L': dict(algo='kclear', hand=1, k=4, dhit=True), 'kcd_R': dict(algo='kclear', hand=-1, k=4, dhit=True),
    'bug2_L_a0': dict(algo='bug2', hand=1, a0=0),          # broken-constant control: no wall-side turn
}
A0, TURN = 16, 16


def lattice_comp(tr, step=32):
    """independent reachability: flood fill of a `step`-unit point lattice, a point is land by the exact sampler,
    4-neighbour moves between land lattice points."""
    nx, ny = 0x4000 // step, 0x8000 // step
    land = bytearray(nx * ny)
    for j in range(ny):
        y = j * step + step // 2
        for i in range(nx):
            land[j * nx + i] = tr.free(i * step + step // 2, y)
    comp = [-1] * (nx * ny)
    k = 0
    for s in range(nx * ny):
        if land[s] and comp[s] < 0:
            comp[s] = k
            dq = [s]
            while dq:
                u = dq.pop()
                ux, uy = u % nx, u // nx
                for v in ((u - 1) if ux else -1, (u + 1) if ux + 1 < nx else -1, (u - nx) if uy else -1, (u + nx) if uy + 1 < ny else -1):
                    if v >= 0 and land[v] and comp[v] < 0:
                        comp[v] = k
                        dq.append(v)
            k += 1
    return lambda x, y: (comp[(y // step) * nx + x // step] if 0 <= x < 0x4000 and 0 <= y < 0x8000 and land[(y // step) * nx + x // step] else -1)


def cell_comp(mp, conn8):
    """in-game style: a cell is land if either triangle is; label by 4- or 8-connectivity."""
    W, H = 64, 128
    cl = [bool(mp.land[2 * c] or mp.land[2 * c + 1]) for c in range(W * H)]
    lab = [-1] * (W * H)
    k = 0
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (1, -1), (-1, 1), (1, 1)] if conn8 else [])
    for s in range(W * H):
        if cl[s] and lab[s] < 0:
            lab[s] = k
            st = [s]
            while st:
                u = st.pop()
                ux, uy = u % W, u // W
                for dx, dy in nb:
                    vx, vy = ux + dx, uy + dy
                    if 0 <= vx < W and 0 <= vy < H:
                        v = vy * W + vx
                        if cl[v] and lab[v] < 0:
                            lab[v] = k
                            st.append(v)
            k += 1
    return lambda x, y: (lab[(y >> 8) * W + (x >> 8)] if 0 <= x < 0x4000 and 0 <= y < 0x8000 else -1)


def polylen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def do_plane(args):
    plane, snap, idxs, pairs = args
    t0 = time.time()
    mp = astar.Map(str(ROOT / 'scratchpad/pm148/arms/long' / (snap + '.snap')))
    tr = follow.Terrain(mp)
    lat = lattice_comp(tr)
    c4, c8 = cell_comp(mp, False), cell_comp(mp, True)
    out = {}
    for n, i in enumerate(idxs):
        p = pairs[i]
        s, t = (p['x'], p['y']), (p['tx'], p['ty'])
        r = dict(cls=p['cls'])
        # reachability verdicts: tri (A* graph), lattice flood, cell flood 4/8
        tri = mp.reachable(s, t)
        r['reach'] = dict(tri=tri,
                          lat=(lat(*s) >= 0 and lat(*s) == lat(*t)),
                          c4=(mp.sample(*t) != 0 and c4(*s) >= 0 and c4(*s) == c4(*t)),
                          c8=(mp.sample(*t) != 0 and c8(*s) >= 0 and c8(*s) == c8(*t)))
        if p['cls'] in ('b', 'c', 'a', 'a-twater'):
            arr, tick, pos, modes = mp.simulate_walk(s, t, p['speed'], 3000, chase=p['prev'] == 0x2e)
            r['ctl'] = dict(arrives=arr, tick=tick)
        if p['cls'] == 'b':
            wps, ver = mp.path(s, t, p['speed'])
            pts = [s] + wps
            r['astar'] = dict(len=polylen(pts), n=len(wps), verified=ver, pts=pts)
            r['straight'] = math.hypot(t[0] - s[0], t[1] - s[1])
            r['algos'] = {}
            for name, kw in ALGOS.items():
                kw = dict(kw)
                kw.setdefault('a0', A0)
                res = follow.run(tr, s, t, p['speed'], turn=TURN, **kw)
                r['algos'][name] = res
        elif p['cls'] in ('c', 'a'):
            kw = dict(ALGOS['bug2_L']); kw.update(a0=A0)
            r['algos'] = {'bug2_L': follow.run(tr, s, t, p['speed'], turn=TURN, **kw), 'bug2_R': follow.run(tr, s, t, p['speed'], turn=TURN, **dict(ALGOS['bug2_R'], a0=A0))}
        out[i] = r
    print('plane', plane[:6], len(idxs), 'pairs, %.0fs' % (time.time() - t0), flush=True)
    return out


if __name__ == '__main__':
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    d = pickle.load(open(DATA / 'pairs.pkl', 'rb'))
    pairs = d['pairs']
    by = {}
    for i, p in enumerate(pairs):
        if p['cls'] == 'boat':
            continue
        e = by.setdefault(p['plane'], (p['snap'], []))
        e[1].append(i)
    tasks = []
    for plane, (snap, idxs) in by.items():
        # split big planes into chunks so the pool balances
        for k in range(0, len(idxs), 250):
            tasks.append((plane, snap, idxs[k:k + 250], pairs))
    res = {}
    with Pool(procs) as pool:
        for o in pool.imap_unordered(do_plane, tasks):
            res.update(o)
    pickle.dump(res, open(DATA / 'results.pkl', 'wb'))
    print('done', len(res))

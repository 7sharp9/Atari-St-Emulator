"""Shortest route to finish a base, against the plan the generator's dig order gives for free.

    uv run python -I reversing/captive/py/mapgen/full/route.py <first mission> <last mission exclusive> [--json out]

Bases are those of finish.py: D0 = 11*mission + target, D2 = 1 for target 11, from the chained generator (gated
400/400 against the emulator). Model output only: nothing here is driven in play.

The task (assumed, not the game's whole objective): start at the entrance, stand beside a generator tile ($28/$29,
bit 7 ignored; the cell EXPLOSIVES are used on, ai.md "Finishing a base"), and walk back to the entrance. The party
is taken to carry EXPLOSIVES. Cost is cells walked; panel clicks and the blind settings of key kinds 0 and 1 (2 and
8 settings) cost nothing.

Passability is lockcensus.Grid's (open cells by $24efc's rule plus every arrow edge), with each lock's door cell D
blocked until the lock is opened. Lock i is opened by standing on its panel cell, the open cell in front of the wall
item W on the straight line from W to the approach cell P ($2584c walks P -> W), which the script checks against
W's tile side. Key kinds 2 and 3 need the code first: the party must have stood on the key cell K (the clipboard).
Kinds 0 and 1 need nothing. With --label (the second mode, always run) a lock's code is also known once its panel is
reached, because the panel prints the same label as the clipboard and the label inverts to the code (mapgen.md
"Sealed keys").

Three routes per base:
  optimal  A* over (position, locks opened, codes known, generator reached), moves between points of interest
           (entrance, panel cells, key cells, cells beside a generator) at BFS distance under the doors opened so
           far. Heuristic: the all-doors-open distance to the goal, which is a lower bound, so the result is optimal.
  plan     the dig-order plan: find the locks needed by regression (doors on the all-doors-open shortest path to the
           nearest reachable goal, then recursively the doors on the paths to each needed lock's panel and key), then
           open them in rising G0(D) and walk each leg by the shortest path under the doors open so far.
  sweep    open every openable lock in rising G0(D) (the order the census proves always works), then finish.
"""
import heapq
import json
import os
import sys
from collections import Counter, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lockcensus as LC  # noqa: E402
import chain_run as CR  # noqa: E402

NB = ((1, 0), (-1, 0), (0, 1), (0, -1))
NODE_LIMIT = 100000
CACHE_LIMIT = 20000


def record_locks_p(d0, d2):
    """lockcensus.record_locks, plus each lock's approach cell P (13222/13242 at the time of the lock)."""
    C = LC.C
    orig = C.lock_2584c
    ps = []

    def lock(S, x, y, slot):
        n0 = S.w(13626)
        orig(S, x, y, slot)
        if S.w(13626) != n0:
            ps.append((S.sw(13222), S.sw(13242)))
    C.lock_2584c = lock
    try:
        locks, m, ab, full = LC.record_locks(d0, d2)
    finally:
        C.lock_2584c = orig
    # record_locks wraps C.lock_2584c itself; our wrapper sits inside it, so both see the same successful locks
    assert len(ps) == len(locks), (d0, d2, len(ps), len(locks))
    for L, p in zip(locks, ps):
        L['P'] = p
    return locks, m, full


def sgn(v):
    return (v > 0) - (v < 0)


class Base:
    def __init__(self, d0, d2):
        self.d0, self.d2 = d0, d2
        self.locks, m, full = record_locks_p(d0, d2)
        g = LC.Grid(m)
        g.reach((0, 0), set())          # builds g.adj
        self.adj = {c: tuple(sorted(n)) for c, n in g.adj.items()}
        self.g0 = g.g0
        ex = LC.w(m, 32)
        self.ent = (ex % 64, ex // 64)
        p = int.from_bytes(m[13684:13688], 'big') - CR.FED
        self.tiles = full[p:p + 2048]
        gens = [(i % 64, i // 64) for i in range(2048) if self.tiles[i] & 0x7e == 0x28]
        self.beside = sorted({(x + dx, y + dy) for x, y in gens for dx, dy in NB if (x + dx, y + dy) in self.adj})
        self.beside_set = set(self.beside)
        self.doors = [L['D'] for L in self.locks]
        self.stand = []
        self.side_pairs = Counter()
        for L in self.locks:
            (wx, wy), (px, py) = L['W'], L['P']
            dx, dy = sgn(px - wx), sgn(py - wy)
            ok_line = (dx == 0) != (dy == 0)
            s = (wx + dx, wy + dy) if ok_line else None
            self.stand.append(s if s in self.adj else None)
            self.side_pairs[((dx, dy), self.tiles[64 * wy + wx] & 0xf3)] += 1
        self.keyed = [L['K'] is not None for L in self.locks]
        self._bfs = {}

    def bfs(self, src, opened):
        """Distances from src with every unopened lock's door blocked."""
        key = (src, opened)
        r = self._bfs.get(key)
        if r is not None:
            return r
        if len(self._bfs) > CACHE_LIMIT:
            self._bfs.clear()
        banned = {d for i, d in enumerate(self.doors) if not opened >> i & 1}
        dist = {src: 0}
        q = deque([src])
        while q:
            c = q.popleft()
            for n in self.adj.get(c, ()):
                if n not in dist and n not in banned:
                    dist[n] = dist[c] + 1
                    q.append(n)
        self._bfs[key] = dist
        return dist

    def all_open(self, src):
        return self.bfs(src, (1 << len(self.locks)) - 1)

    def can_open(self, i, known):
        return not self.keyed[i] or known >> i & 1

    # ---------- optimal ----------
    def arrive(self, pos, opened, known, label):
        """At pos: read any clipboard there, and open every lock whose panel is pos and whose code is known
        (opening only adds passability and costs no steps, so it never hurts)."""
        for j, L in enumerate(self.locks):
            if L['K'] == pos:
                known |= 1 << j
        for j, s in enumerate(self.stand):
            if s == pos and not opened >> j & 1 and (label or self.can_open(j, known)):
                opened |= 1 << j
        return opened, known & ~opened

    def optimal(self, label, allowed):
        n = len(self.locks)
        ent_d = self.all_open(self.ent)
        hb = {}

        def h(pos, blown):
            if blown:
                return ent_d.get(pos, 10 ** 6)
            r = hb.get(pos)
            if r is None:
                d = self.all_open(pos)
                r = min((d[b] + ent_d[b] for b in self.beside if b in d and b in ent_d), default=10 ** 6)
                hb[pos] = r
            return r
        o0, k0 = self.arrive(self.ent, 0, 0, label)
        start = (self.ent, o0, k0, False)
        pq = [(h(self.ent, False), 0, start)]
        labels = {}          # (pos, blown) -> [(opened, known, g)] non-dominated settled labels
        nodes = 0
        while pq:
            f, gc, st = heapq.heappop(pq)
            pos, opened, known, blown = st
            lst = labels.setdefault((pos, blown), [])
            if any(o & opened == opened and (k | o) & known == known and g <= gc for o, k, g in lst):
                continue
            lst.append((opened, known, gc))
            if blown and pos == self.ent:
                return gc, nodes
            nodes += 1
            if nodes > NODE_LIMIT:
                return None, nodes
            dist = self.bfs(pos, opened)
            targets = set()
            if blown:
                targets.add(self.ent)
            else:
                targets.update(b for b in self.beside if b in dist)
                for i in range(n):
                    if opened >> i & 1 or not allowed >> i & 1:
                        continue
                    s = self.stand[i]
                    if s in dist and (label or self.can_open(i, known)):
                        targets.add(s)
                    K = self.locks[i]['K']
                    if K is not None and not label and not known >> i & 1 and K in dist:
                        targets.add(K)
            for p2 in targets:
                if p2 not in dist or p2 == pos:
                    continue
                b2 = blown or p2 in self.beside_set
                o2, k2 = self.arrive(p2, opened, known, label)
                g2 = gc + dist[p2]
                heapq.heappush(pq, (g2 + h(p2, b2), g2, (p2, o2, k2, b2)))
        return None, nodes

    # ---------- dig-order plan and sweep ----------
    def openable(self, label):
        """Locks openable at all, by the fixpoint (delete relaxation is exact: opening only adds passability)."""
        n = len(self.locks)
        opened = known = 0
        changed = True
        while changed:
            changed = False
            reach = self.bfs(self.ent, opened)
            for i in range(n):
                K = self.locks[i]['K']
                if K is not None and K in reach and not known >> i & 1:
                    known |= 1 << i
                    changed = True
                s = self.stand[i]
                if not opened >> i & 1 and s in reach and (label or self.can_open(i, known)):
                    opened |= 1 << i
                    known |= 1 << i if label else 0
                    changed = True
        reach = self.bfs(self.ent, opened)
        finishable = any(b in reach for b in self.beside)
        return opened, finishable

    def walk(self, order, label):
        """Open the locks in `order`, each time taking the first one in that order whose key (if needed) and panel are
        reachable now (key cell first, then panel), then walk to the nearest goal and back. None if stuck."""
        pos, opened, known, cost = self.ent, 0, 0, 0
        left = list(order)
        self.walk_skips = 0
        while left:
            d = self.bfs(self.ent, opened)
            pick = None
            for k, i in enumerate(left):
                K = self.locks[i]['K']
                if (label or K is None or K in d) and self.stand[i] in d:
                    pick = k
                    break
            if pick is None:
                return None
            self.walk_skips += pick > 0
            i = left.pop(pick)
            K = self.locks[i]['K']
            if K is not None and not label and not known >> i & 1:
                cost += self.bfs(pos, opened)[K]
                pos = K
                known |= 1 << i
            cost += self.bfs(pos, opened)[self.stand[i]]
            pos = self.stand[i]
            opened |= 1 << i
        d = self.bfs(pos, opened)
        back = self.bfs(self.ent, opened)
        legs = [d[b] + back[b] for b in self.beside if b in d and b in back]
        return cost + min(legs) if legs else None

    def path(self, src, dst, mask):
        """One shortest path src -> dst (cells) with only the doors in mask passable."""
        d = self.bfs(dst, mask)
        if src not in d:
            return None
        out = [src]
        c = src
        while c != dst:
            c = min((n for n in self.adj[c] if n in d and d[n] == d[c] - 1))
            out.append(c)
        return out

    def plan(self, label):
        """Regression from the goal through the openable locks only (the fixpoint's set), then dig order."""
        mask, fin = self.openable(label)
        if not fin:
            return None, set()
        doorat = {d: i for i, d in enumerate(self.doors)}
        ent_d = self.bfs(self.ent, mask)
        g = min((b for b in self.beside if b in ent_d), key=lambda b: ent_d[b])
        need = set()
        todo = [self.path(self.ent, g, mask)]
        while todo:
            pth = todo.pop()
            assert pth is not None
            for c in pth:
                i = doorat.get(c)
                if i is None or i in need:
                    continue
                need.add(i)
                todo.append(self.path(self.ent, self.stand[i], mask))
                K = self.locks[i]['K']
                if K is not None and not label:
                    todo.append(self.path(self.ent, K, mask))
        order = sorted(need, key=lambda i: self.g0(*self.doors[i]))
        return self.walk(order, label), need

    def sweep(self, label):
        opened, _ = self.openable(label)
        order = sorted((i for i in range(len(self.locks)) if opened >> i & 1), key=lambda i: self.g0(*self.doors[i]))
        return self.walk(order, label)


def one(args):
    mi, t = args
    d0, d2 = 11 * mi + t, (1 if t == 10 else 0)
    B = Base(d0, d2)
    row = {'mission': mi + 1, 'target': t + 1, 'd0': d0, 'd2': d2, 'locks': len(B.locks),
           'keyed': sum(B.keyed), 'sealed': sum(L['K'] == L['D'] for L in B.locks if L['K']),
           'no_panel': sum(s is None for s in B.stand), 'sides': [[list(k[0]), k[1], v] for k, v in B.side_pairs.items()]}
    ent_d = B.all_open(B.ent)
    legs = [2 * ent_d[b] for b in B.beside if b in ent_d]
    row['lb'] = min(legs) if legs else None
    for label in (False, True):
        tag = 'label' if label else 'clip'
        opened, fin = B.openable(label)
        row[f'{tag}_finishable'] = fin
        row[f'{tag}_openable'] = bin(opened).count('1')
        if not fin:
            continue
        pl, need = B.plan(label)
        mask = sum(1 << i for i in need)
        opt, nodes = B.optimal(label, mask)
        row.update({f'{tag}_plan': pl, f'{tag}_need': len(need), f'{tag}_opt': opt, f'{tag}_nodes': nodes,
                    f'{tag}_plan_skips': B.walk_skips, f'{tag}_sweep': B.sweep(label)})
    return row


def main(argv):
    from multiprocessing import Pool
    lo, hi = int(argv[0]), int(argv[1])
    jobs = int(argv[argv.index('-j') + 1]) if '-j' in argv else 8
    out = argv[argv.index('--json') + 1] if '--json' in argv else None
    work = [(mi, t) for mi in range(lo, hi) for t in range(11)]
    rows = []
    with Pool(jobs, maxtasksperchild=20) as p:
        for k, r in enumerate(p.imap_unordered(one, work, chunksize=1)):
            rows.append(r)
            if k % 50 == 0:
                print(f'{k + 1}/{len(work)} bases', file=sys.stderr, flush=True)
    rows.sort(key=lambda r: r['d0'])
    if out:
        with open(out, 'w') as f:
            json.dump(rows, f, indent=0)
    c = Counter()
    sides = Counter()
    for r in rows:
        c['bases'] += 1
        c['locks'] += r['locks']
        c['locks with no panel cell'] += r['no_panel']
        c['sealed keys'] += r['sealed']
        for k0, k1, v in r['sides']:
            sides[(tuple(k0), k1)] += v
        if r['lb'] is None:
            c['bases with no generator side reachable even with every door open'] += 1
            continue
        for tag in ('clip', 'label'):
            if not r[f'{tag}_finishable']:
                c[f'{tag}: not finishable'] += 1
                continue
            c[f'{tag}: finishable'] += 1
            pl, opt, lb = r[f'{tag}_plan'], r[f'{tag}_opt'], r['lb']
            c[f'{tag}: A* node limit'] += opt is None
            c[f'{tag}: plan == lower bound (provably optimal)'] += pl == lb
            c[f'{tag}: plan == A* (needed locks only)'] += opt is not None and pl == opt
            c[f'{tag}: plan stuck'] += pl is None
            c[f'{tag}: plan left dig order at least once'] += bool(r.get(f'{tag}_plan_skips'))
            c[f'{tag}: A* > plan (would be a bug)'] += opt is not None and pl is not None and opt > pl
            c[f'{tag}: opens no lock'] += r[f'{tag}_need'] == 0
    for k, v in c.items():
        print(f'{k}: {v}')
    print('panel side check ((dx,dy) from W to the panel cell, W tile & $f3):', dict(sorted(sides.items())))
    for tag in ('clip', 'label'):
        r = [x for x in rows if x.get(f'{tag}_plan') and x.get(f'{tag}_opt')]
        if not r:
            continue
        q = lambda v: (sorted(v)[len(v) // 2], max(v))
        pl = q([x[f'{tag}_plan'] / x['lb'] for x in r])
        po = q([x[f'{tag}_plan'] / x[f'{tag}_opt'] for x in r if x[f'{tag}_opt']])
        sw = q([x[f'{tag}_sweep'] / x[f'{tag}_plan'] for x in r if x[f'{tag}_sweep']])
        nd = q([x[f'{tag}_need'] for x in r])
        print(f'{tag} ({len(r)} bases): plan/lower bound median {pl[0]:.3f} max {pl[1]:.3f}; plan/A* median {po[0]:.3f} '
              f'max {po[1]:.3f}; sweep/plan median {sw[0]:.2f} max {sw[1]:.2f}; locks needed median {nd[0]} max {nd[1]}')


if __name__ == '__main__':
    main(sys.argv[1:])

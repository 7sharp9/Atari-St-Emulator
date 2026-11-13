"""Census of $25722's locked doors and keys over chained bases (chain_run.generate, gated 400/400 against the emulator).

    uv run python -I reversing/captive/py/mapgen/full/chain_run.py locks <d2> <lo> <hi>

Per lock it records, while $25722 runs: dead end E (prize: item 25 and a group), door cell D, wall-item cell W, door
kind 13596, key kind 13598 and the key cell K (item $5c/$5d, word = the lock's code). On the base's final grids it
then measures:
  dig     G0(K) <= G0(D), G0 the dig-step number (the rule $2588a-$258b0 enforces)
  arrowK  the plane-2 arrow path K -> entrance avoids D (a walkable route to the key that never crosses the door)
  arrowE  the arrow path E -> entrance passes D
  bypass  E reachable from the entrance with D removed (4-neighbour open cells by $24efc's rule plus every arrow
          edge, so lifts and shafts count), i.e. the door does not seal the prize
  keyBFS  K reachable from the entrance with D removed
  others  other locks' doors on K's arrow path (key behind another lock), and whether that dependency graph is acyclic
"""
import os
import sys
from collections import Counter, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chain_run as CR  # noqa: E402
import cmodels as C  # noqa: E402
import models  # noqa: E402
from models import d5of  # noqa: E402

G0 = 56
G2 = 8280


def record_locks(d0, d2):
    locks = []
    cur = {}
    orig_lock, orig_app = C.lock_2584c, C.P.obj_append

    def lock(S, x, y, slot):
        n0 = S.w(13626)
        cur.clear()
        orig_lock(S, x, y, slot)
        if S.w(13626) != n0:
            locks.append({'E': (S.w(13218), S.w(13238)), 'D': (S.w(13220), S.w(13240)),
                          'W': (S.w(13224), S.w(13244)), 'door': S.w(13596), 'key': S.w(13598),
                          'K': cur.get('K'), 'code': S.w(13602)})
        elif 'K' not in cur and S.w(13598) > 1 and cur.get('site'):
            abandoned[0] += 1

    def site(S, x, y):
        r = orig_site(S, x, y)
        cur['site'] = r
        return r

    def app(S, x, y, d0b, d3w, keep=False):
        if d0b in (0x5c, 0x5d):
            cur['K'] = (x, y)
        return orig_app(S, x, y, d0b, d3w, keep)

    orig_site = C.site_25a3e
    abandoned = [0]
    C.lock_2584c, C.site_25a3e, C.P.obj_append = lock, site, app
    try:
        m, full, _ = CR.generate(d0, d2)
    finally:
        C.lock_2584c, C.site_25a3e, C.P.obj_append = orig_lock, orig_site, orig_app
    return locks, m, abandoned[0], full


def w(m, o):
    return (m[o] << 8) | m[o + 1]


class Grid:
    def __init__(self, m):
        self.m = m
        self.S = models.State(bytearray(m), bytearray(0x1d9e8 - 0x1bd3e))

    def g0(self, x, y):
        return w(self.m, G0 + 2 * (64 * y + x))

    def is_open(self, x, y):
        return 0 <= x < 64 and 0 <= y < 32 and models.blocked(self.S, x, y)[0] == 0

    def arrow(self, x, y):
        return models.step_flow(self.S, x, y)

    def arrow_path(self, x, y, limit=5000):
        out = [(x, y)]
        for _ in range(limit):
            x, y = self.arrow(x, y)
            if not (0 <= x < 64 and 0 <= y < 32):
                return out, True
            out.append((x, y))
        return out, False

    def edges(self, x, y):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if self.is_open(x + dx, y + dy):
                yield x + dx, y + dy
        a = self.arrow(x, y)
        if 0 <= a[0] < 64 and 0 <= a[1] < 32:
            yield a

    def reach(self, start, banned):
        if not hasattr(self, 'adj'):
            self.adj = self._adj()
        adj = self.adj
        seen = {start}
        q = deque([start])
        while q:
            c = q.popleft()
            for n in adj.get(c, ()):
                if n not in seen and n not in banned:
                    seen.add(n)
                    q.append(n)
        return seen

    def _adj(self):
        adj = {}
        for y in range(32):
            for x in range(64):
                if self.is_open(x, y):
                    for c in self.edges(x, y):
                        adj.setdefault((x, y), set()).add(c)
                        adj.setdefault(c, set()).add((x, y))
        return adj


def main(args):
    d2, lo, hi = int(args[0]), int(args[1]), int(args[2])
    c = Counter()
    kinds = Counter()
    gaps = []
    for d0 in range(lo, hi):
        locks, m, ab, full = record_locks(d0, d2)
        c['bases'] += 1
        c['abandoned (no key cell in 11 tries)'] += ab
        # cross-check against the base's own lock list 13720 (10 bytes per lock) and count 13270
        q = int.from_bytes(m[13720:13724], 'big') - CR.FED
        lst = [(full[q + 10 * i + 6], full[q + 10 * i + 7]) for i in range(w(m, 13270))]
        c['lock list 13720 == recorded doors'] += lst == [L['D'] for L in locks]
        if not locks:
            continue
        g = Grid(m)
        ex = w(m, 32)
        ent = (ex % 64, ex // 64)
        doors = {L['D']: i for i, L in enumerate(locks)}
        dep = {}
        for i, L in enumerate(locks):
            c['locks'] += 1
            kinds[(L['door'], L['key'])] += 1
            D, E, K = L['D'], L['E'], L['K']
            pe, oute = g.arrow_path(*E)
            c['arrowE passes D'] += D in pe
            reach = g.reach(ent, {D})
            c['bypass: E reachable without D'] += E in reach
            if K is None:
                c['no key object (key kind 0/1)'] += 1
                continue
            c['with key'] += 1
            c['dig: G0(K) <= G0(D)'] += g.g0(*K) <= g.g0(*D)
            c['key on the door cell itself'] += K == D
            c['dig: G0(K) <= G0(E)'] += g.g0(*K) <= g.g0(*E)
            gaps.append(g.g0(*D) - g.g0(*K))
            pk, outk = g.arrow_path(*K)
            c['arrowK reaches entrance'] += outk
            c['arrowK avoids D'] += D not in pk
            c['keyBFS: K reachable without D'] += K in reach
            others = [doors[p] for p in pk if p in doors and doors[p] != i]
            c['key behind another lock door (arrow path)'] += bool(others)
            if not outk:
                print(f'  d0={d0} lock {i}: arrow path from K={K} does not leave the grid in 5000 steps; tail {pk[-4:]}')
            for j in others:
                c['  ... dependency with G0(D_other) < G0(D_this)'] += g.g0(*locks[j]['D']) < g.g0(*D)
                c['  ... that door made earlier' if j < i else '  ... that door made later'] += 1
                c['  ... that door keyed (key kind 2/3)' if locks[j]['K'] else '  ... that door keyless'] += 1
            ka = g.reach(ent, set())
            c['K reachable at all'] += K in ka
            dep[i] = set(others)
        # cycle check on the key-behind-door dependency graph
        state = {}

        def cyc(v):
            state[v] = 1
            for u in dep.get(v, ()):
                if state.get(u) == 1 or (state.get(u) is None and cyc(u)):
                    return True
            state[v] = 2
            return False
        c['bases with a dependency cycle'] += any(cyc(v) for v in dep if v not in state)
    for k_, v in c.items():
        print(f'{k_}: {v}')
    print('(door kind 13596, key kind 13598):', dict(sorted(kinds.items())))
    if gaps:
        gaps.sort()
        print('G0(D) - G0(K): min', gaps[0], 'median', gaps[len(gaps) // 2], 'max', gaps[-1])

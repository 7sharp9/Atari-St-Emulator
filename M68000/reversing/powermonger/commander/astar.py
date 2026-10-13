"""astar.py - land reachability and waypoint paths for the PowerMonger commander (README step 2).

Model (addresses are the game's; see ai.md "Spatial primitives" and the movement-mode table):

- Terrain sample `$1648e` (exact, reused from tools/pm_fsm_ref.terrain_sample, gated by gate_sampler.py):
  cell index = ((Y & $ff00) | ((X >> 6) & $ff)) >> 2 (X wraps mod $4000; a negative Y reads past the plane),
  flag byte `$4592f+c` bit 7 picks the diagonal, the in-cell low bytes pick the triangle:
    bit 7 set   : (x + y) carries (x+y >= 256) -> byte $438ee+c ("B"), else $418ad+c ("A")
    bit 7 clear : x > y (unsigned)             -> byte $438ee+c ("B"), else $418ad+c ("A")
  colour 0 = water / blocked.
- Step `$164bc` (exact, pm_fsm_ref.step_toward): count = major // speed, minor step = minor // count,
  dwell 18 := count >> 1, "reached" <=> dwell == 0.
- Straight leg = mode `$10` (`$14f58`..`$14fd4`) + mode `$12` (`$14ff8`) + epilogue `$161c4`, read from code:
  $10 re-plans with $164bc; reached -> snap onto the target ($14fdc), then $161c4 vetoes a water target
  (mode $00, no write); else it probes the `dwell` points P + k*step (k = 1..dwell, `dbeq` on $1648e, no
  map-bound test) and any water point sends the man to mode $4a; otherwise $12 walks exactly those points
  (each clamped and re-sampled by $161c4) and $10 re-plans from the last one. A Boat carrier (byte 33 == $0a)
  skips the probe.
- Detour = modes `$4a` (`$1597a`) and `$48` (`$158da`), read from code, only in simulate_walk():
  $4a: lead with word 28 == 0 keeps its target, heading &= $fc, sweep word 40 := 8, mode $48;
  $48: step := $12d56 rotate of (0, -speed) by the heading; probe min(dwell, $100)+1 points (exits on x<0,
  y<0, x>=$4000); open -> mode $12 (walk `dwell` steps on that heading, then $10 re-plans); blocked ->
  heading += sweep, sweep -> -(sweep+4) / -sweep+4, at sweep $80: dwell -= 8 and restart via $4a
  (or, dwell < 0, keep mode $48 with the heading reversed: every later probe counts as open).

Not modelled (inferred irrelevant to terrain, or out of scope): the group hand-off at $14fa2 (a group lead
whose group is in state 8 halves its dwell, and at dwell <= $12 jumps to $1518a); followers ($4a copies the
lead's position into the target when word 28 != 0); a moving chase target (prev mode $2e is modelled against
a target standing still: depth-3 probe, contact at reached); collisions.

Graph: triangle level (two triangles per cell, the exact regions $1648e distinguishes), 4-neighbour edge
adjacency across cell sides plus the shared diagonal inside a cell. A cell-level graph would call a shore
cell with one wet triangle either all land or all water, and $1648e does not.

CLI:  astar.py <snap> x0 y0 x1 y1 [--cells] [--speed N]
      world units by default (a cell is 256); --cells takes cell coordinates and uses cell centres.
"""
import heapq
import math
import struct
import sys
from pathlib import Path


def _root():
    import os
    if os.environ.get('M68000_ROOT'):
        return Path(os.environ['M68000_ROOT'])
    here = Path(__file__).resolve()
    return next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())


ROOT = _root()
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap  # noqa: E402
import pm_fsm_ref as ref  # noqa: E402

PLANE_B = 0x438ee            # 0(A4) in $1648e
PLANE_A = 0x438ee - 8257     # -8257(A4) = $418ad
FLAGS = 0x438ee + 8257       # 8257(A4) = $4592f
W, H = 64, 128

s8, s16 = ref.s8, ref.s16


class Map:
    """A RAM image plus the triangle graph of its terrain."""

    def __init__(self, ram):
        if isinstance(ram, (str, Path)):
            ram = ram_from_snap(str(ram))
        self.ram = bytes(ram)
        self.m = ref.Mem(self.ram)
        ref.init_tables(self.ram)
        self._build()

    # ------------------------------------------------------------ $1648e
    def sample(self, x, y):
        return ref.terrain_sample(self.m, x & 0xffff, y & 0xffff)

    # ------------------------------------------------------------ triangle graph
    # node id = (cy*64 + cx)*2 + h, h = 0 for plane A ($418ad), 1 for plane B ($438ee)
    def _build(self):
        r = self.ram
        n = W * H * 2
        self.land = bytearray(n)
        self.diag = bytearray(W * H)
        for c in range(W * H):
            self.diag[c] = r[FLAGS + c] >> 7
            self.land[2 * c] = r[PLANE_A + c] != 0
            self.land[2 * c + 1] = r[PLANE_B + c] != 0
        # sides each triangle touches: T, B(ottom), L, R
        # diag 0 (bit 7 clear, B = x > y): B touches T,R ; A touches L,Bo
        # diag 1 (bit 7 set,  B = x+y >= 256): B touches R,Bo ; A touches T,L
        self.adj = [[] for _ in range(n)]
        side = {0: {'T': 1, 'R': 1, 'L': 0, 'D': 0}, 1: {'T': 0, 'L': 0, 'R': 1, 'D': 1}}
        for cy in range(H):
            for cx in range(W):
                c = cy * W + cx
                d = self.diag[c]
                a, b = 2 * c, 2 * c + 1
                if self.land[a] and self.land[b]:
                    self.adj[a].append(b)
                    self.adj[b].append(a)
                if cx + 1 < W:
                    c2 = c + 1
                    u = 2 * c + side[d]['R']
                    v = 2 * c2 + side[self.diag[c2]]['L']
                    if self.land[u] and self.land[v]:
                        self.adj[u].append(v)
                        self.adj[v].append(u)
                if cy + 1 < H:
                    c2 = c + W
                    u = 2 * c + side[d]['D']
                    v = 2 * c2 + side[self.diag[c2]]['T']
                    if self.land[u] and self.land[v]:
                        self.adj[u].append(v)
                        self.adj[v].append(u)
        # components
        self.comp = [-1] * n
        k = 0
        for s in range(n):
            if self.land[s] and self.comp[s] < 0:
                st = [s]
                self.comp[s] = k
                while st:
                    u = st.pop()
                    for v in self.adj[u]:
                        if self.comp[v] < 0:
                            self.comp[v] = k
                            st.append(v)
                k += 1
        self.ncomp = k

    def node(self, x, y):
        """triangle node a world point lies in (the same choice $1648e makes), None off the plane."""
        x &= 0xffff
        y &= 0xffff
        if x >= 0x4000 or y >= 0x8000:
            return None
        c = (y >> 8) * W + (x >> 8)
        lx, ly = x & 0xff, y & 0xff
        if self.diag[c]:
            h = 1 if lx + ly > 0xff else 0
        else:
            h = 1 if lx > ly else 0
        return 2 * c + h

    @staticmethod
    def centroid(nd):
        c, h = divmod(nd, 2)
        cy, cx = divmod(c, W)
        return cx, cy, h

    def node_point(self, nd):
        c, h = divmod(nd, 2)
        cy, cx = divmod(c, W)
        if self.diag[c]:
            lx, ly = (170, 170) if h else (85, 85)
        else:
            lx, ly = (170, 85) if h else (85, 170)
        return cx * 256 + lx, cy * 256 + ly

    def component(self, x, y):
        nd = self.node(x, y)
        return None if nd is None or not self.land[nd] else self.comp[nd]

    def cell_components(self):
        """64 x 128 list of lists: the component of a cell's land triangle(s), -1 for an all-water cell
        (both land triangles of one cell share the diagonal, so they always share a component)."""
        out = []
        for cy in range(H):
            row = []
            for cx in range(W):
                c = cy * W + cx
                row.append(self.comp[2 * c + 1] if self.land[2 * c + 1] else self.comp[2 * c])
            out.append(row)
        return out

    def reachable(self, start, target):
        a = self.component(*start)
        return a is not None and a == self.component(*target)

    # ------------------------------------------------------------ the walker
    def _step(self, x, y, tx, ty, speed):
        """$164bc on a scratch record; returns (sx, sy, dwell, heading)."""
        A1 = 0xfff00                      # scratch record past every structure the sampler reads
        self.m.wb(A1 + 16, speed)
        _c, dwell, _r = ref.step_toward(self.m, tx & 0xffff, ty & 0xffff, x & 0xffff, y & 0xffff, A1)
        return s8(self.m.bu(A1 + 12)), s8(self.m.bu(A1 + 13)), dwell, self.m.bu(A1 + 17)

    def leg(self, start, target, speed=32, boat=False, max_replans=64, chase=False):
        """mode $10/$12 straight leg from start to target. Returns (ok, points, why): ok when the walker
        reaches the target without entering mode $4a and the snapped target is land; points = every
        position it stands on (and, on failure, the probe point that blocked). chase=True: prev mode $2e
        (probe and walk depth 3, $14f3e; contact when $164bc says reached, $15302)."""
        x, y = start
        tx, ty = target
        pts = []
        for _ in range(max_replans if not chase else 4096):
            sx, sy, dwell, _h = self._step(x, y, tx, ty, speed)
            if chase and dwell == 0:                             # $15302 contact (engage)
                return True, pts, None
            if chase:
                dwell = 3                                        # $14f3e move.w #$3,D2 ; move.w D2,18(A1)
            if dwell == 0:                                       # $14fdc snap, then $161c4 veto
                if self.sample(tx, ty) == 0:
                    return False, pts, ('target-water', (tx, ty))
                pts.append((tx, ty))
                return True, pts, None
            if not boat:
                px, py = x, y
                for _k in range(dwell):                          # dbeq probe
                    px, py = (px + sx) & 0xffff, (py + sy) & 0xffff
                    if self.sample(px, py) == 0:
                        return False, pts, ('probe-water', (s16(px), s16(py)))
            for _k in range(dwell):                              # $12 walk, $161c4 per step
                nx, ny = ref._clamp((x + sx) & 0xffff, (y + sy) & 0xffff)
                if self.sample(nx, ny) == 0:
                    return False, pts, ('step-water', (nx, ny))
                x, y = nx, ny
                pts.append((x, y))
        return False, pts, ('replan-cap', (x, y))

    def walkable(self, start, target, speed=32, boat=False):
        return self.leg(start, target, speed, boat)[0]

    def simulate_walk(self, start, target, speed=32, ticks=2000, heading=0, chase=False):
        """tick-by-tick model of a lead (word 28 == 0, no Boat, no group hand-off) in modes
        $10/$12/$4a/$48. Returns (arrived, tick, (x, y), modes visited). chase=True models prev mode $2e
        against a target standing still: probe/walk depth 3 ($14f3e), contact at dwell 0 ($15302)."""
        x, y = start
        tx, ty = target
        mode, dwell, sweep, sx, sy = 0x10, 0, 0, 0, 0
        seen = set()
        for t in range(ticks):
            seen.add(mode)
            if mode == 0x10:
                sx, sy, dwell, heading = self._step(x, y, tx, ty, speed)
                if chase and dwell == 0:
                    return True, t, (x, y), seen                 # $15302 contact
                if chase:
                    dwell = 3
                if dwell == 0:
                    if self.sample(tx, ty) == 0:
                        return False, t, (x, y), seen | {0}
                    return True, t, (tx, ty), seen
                px, py, blocked = x, y, False
                for _k in range(dwell):
                    px, py = (px + sx) & 0xffff, (py + sy) & 0xffff
                    if self.sample(px, py) == 0:
                        blocked = True
                        break
                if blocked:
                    mode = 0x4a
                    continue
                mode = 0x12                                      # falls into the $14ff8 body this tick
            if mode == 0x12:
                nx, ny = ref._clamp((x + sx) & 0xffff, (y + sy) & 0xffff)
                dwell = s16(dwell - 1)
                if dwell <= 0:
                    mode = 0x10
                if self.sample(nx, ny) == 0:
                    return False, t, (x, y), seen | {0}          # $161c4 veto -> mode $00
                x, y = nx, ny
                continue
            if mode == 0x4a:
                sweep = 8
                heading &= 0xfc
                mode = 0x48
                continue
            if mode == 0x48:
                d0, d1 = ref.rotate(self.m, 0, (-speed) & 0xffff, heading)
                d3, d4 = s16(d0), s16(d1)
                sx, sy = s8(d0), s8(d1)
                d2 = dwell if dwell < 0x100 else 0x100
                px, py = x, y
                while True:
                    px = s16(px + d3)
                    if px < 0:
                        break
                    py = s16(py + d4)
                    if py < 0:
                        break
                    if px >= 0x4000:
                        break
                    if self.sample(px, py) == 0:
                        break
                    d2 = s16(d2 - 1)
                    if d2 == -1:
                        break
                if d2 < 0:
                    mode = 0x12
                    continue
                heading = (heading + sweep) & 0xff
                if s8(sweep) >= 0:
                    sweep = -(sweep + 4)
                elif sweep == 0x80:
                    dwell = s16(dwell - 8)
                    if dwell >= 0:
                        mode = 0x4a
                        heading = (heading + 0x80) & 0xff
                else:
                    sweep = -sweep + 4
                continue
        return False, ticks, (x, y), seen

    # ------------------------------------------------------------ A*
    def astar(self, start, target):
        """triangle path (list of node ids) from start to target over land, or None."""
        s, g = self.node(*start), self.node(*target)
        if s is None or g is None or not self.land[s] or not self.land[g] or self.comp[s] != self.comp[g]:
            return None
        gx, gy = self.node_point(g)
        h = lambda n: math.hypot(self.node_point(n)[0] - gx, self.node_point(n)[1] - gy)
        dist = {s: 0.0}
        prev = {}
        pq = [(h(s), s)]
        while pq:
            _f, u = heapq.heappop(pq)
            if u == g:
                break
            ux, uy = self.node_point(u)
            for v in self.adj[u]:
                vx, vy = self.node_point(v)
                nd = dist[u] + math.hypot(vx - ux, vy - uy)
                if nd < dist.get(v, 1e18):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd + h(v), v))
        path = [g]
        while path[-1] != s:
            path.append(prev[path[-1]])
        return path[::-1]

    def path(self, start, target, speed=32, max_fail=24):
        """waypoints [(x, y), ...] ending at target, each leg walkable from the previous point (start first
        excluded). Returns (waypoints, verified). Candidates are the A* triangles' centroids; greedy
        string-pull keeps the farthest walkable candidate, giving up a scan after max_fail misses."""
        if self.walkable(start, target, speed):
            return [tuple(target)], True
        tri = self.astar(start, target)
        if tri is None:
            return None, False
        cand = [self.node_point(n) for n in tri[1:-1]] + [tuple(target)]
        out, cur, i = [], tuple(start), -1
        while True:
            if self.walkable(cur, target, speed):
                out.append(tuple(target))
                return out, True
            best, miss = None, 0
            for j in range(i + 1, len(cand)):
                if self.walkable(cur, cand[j], speed):
                    best, miss = j, 0
                else:
                    miss += 1
                    if miss > max_fail and best is not None:
                        break
            if best is None:
                return out + cand[i + 1:], False
            out.append(cand[best])
            cur, i = cand[best], best
            if best == len(cand) - 1:
                return out, True


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    speed = 32
    if '--speed' in argv:
        speed = int(argv[argv.index('--speed') + 1])
        args.remove(str(speed))
    snap, x0, y0, x1, y1 = args[0], *map(int, args[1:5])
    if '--cells' in argv:
        x0, y0, x1, y1 = x0 * 256 + 128, y0 * 256 + 128, x1 * 256 + 128, y1 * 256 + 128
    mp = Map(snap)
    a, b = mp.component(x0, y0), mp.component(x1, y1)
    print('start (%d,%d) cell (%d,%d) colour %d component %s' % (x0, y0, x0 >> 8, y0 >> 8, mp.sample(x0, y0), a))
    print('target (%d,%d) cell (%d,%d) colour %d component %s' % (x1, y1, x1 >> 8, y1 >> 8, mp.sample(x1, y1), b))
    ok, _pts, why = mp.leg((x0, y0), (x1, y1), speed)
    print('straight leg at speed %d: %s' % (speed, 'walkable' if ok else 'blocked %s' % (why,)))
    if not mp.reachable((x0, y0), (x1, y1)):
        print('unreachable over land')
        return 1
    wps, ver = mp.path((x0, y0), (x1, y1), speed)
    print('path (%s, %d legs):' % ('verified' if ver else 'UNVERIFIED', len(wps)))
    for (x, y) in wps:
        print('  (%d,%d) cell (%d,%d)' % (x, y, x >> 8, y >> 8))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

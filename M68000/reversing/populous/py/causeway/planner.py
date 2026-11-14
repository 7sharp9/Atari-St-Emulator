"""planner.py - cheapest causeway across water on the proven raise model.

Facts used (reversing/populous/terrain.md section 2, popgen.Gen):
  raise_pt on a corner of height 0 changes exactly that corner (no neighbour is lower than 0, so the
  difference test h - nb > 1 never fires): one click costs 4*1+10 = 14 mana, independent of the map.
  A cell is walkable ($18198: shape != 0) iff one of its four corners is > 0 ($c0ee), rock $2f / swamp $35 excepted.
  Raising a corner that is already > 0 can never make a sea cell walkable, only adds cascades and cost.
So for a gap the candidate clicks are sea-corner raises at 14 mana each, and the problem is the
minimum number of corner raises that connects start to goal in 8-connected cell steps.

Search state (Dijkstra, cost = mana): (cell, mask) where mask = the raised corners inside the 4x4 corner window
(cx-1..cx+2, cy-1..cy+2) of the current cell.  Every corner of a cell reachable in one step lies in that window,
and a corner is shared only by cells that are mutually adjacent, so forgetting corners that leave the window
loses nothing for a shortest path (any path that re-used a corner later can be shortcut).  Result: optimal for the
click set "raise a sea corner"; checked against exhaustive subset search in check_optimal().
Every click's cost is recomputed with popgen.Gen.raise_pt on the evolving map (replay()).
"""
import heapq, math
from causelib import *

COST = 14

def _widx(cx, cy, x, y): return (y - (cy-1))*4 + (x - (cx-1))

def water_to_goal(h, shape, goals, box=None):
    """Minimum number of non-walkable cells entered on any 8-connected path to a goal (0-1 BFS, backward).
    The cost of entering cell c is [c is water]; the goal's own cell is entered last, so it counts as well."""
    from collections import deque
    INF = 10**9; dist = {}
    dq = deque()
    for g in goals:
        dist[g] = 0; dq.append(g)
    def wcost(c): return 0 if cell_walkable(h, c[0], c[1], shape) else 1
    while dq:
        c = dq.popleft(); d = dist[c]
        if d > dist.get(c, INF): continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = (c[0]+dx, c[1]+dy)
                if not (dx or dy) or not (0 <= p[0] < 64 and 0 <= p[1] < 64): continue
                if box and not (box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]): continue
                if shape is not None and shape[p[1]*64+p[0]] in (0x2f, 0x35): continue
                nd = d + wcost(c)   # moving p -> c enters c
                if nd < dist.get(p, INF):
                    dist[p] = nd
                    (dq.appendleft if wcost(c) == 0 else dq.append)(p)
    return dist

def plan(h, shape, starts, goals, box=None, maxcost=None):
    """starts/goals: iterables of cells (x,y).  Returns (mana, [corner clicks in order], [cell path]) or None.
    Clicks are the corners raised, in the order the path needs them."""
    goals = set(goals)
    walk = {}
    def land(c):
        v = walk.get(c)
        if v is None:
            v = walk[c] = cell_walkable(h, c[0], c[1], shape)
        return v
    def ok_cell(c):
        if not (0 <= c[0] < 64 and 0 <= c[1] < 64): return False
        if box and not (box[0] <= c[0] <= box[2] and box[1] <= c[1] <= box[3]): return False
        return shape is None or shape[c[1]*64+c[0]] not in (0x2f, 0x35)
    pq = []; best = {}; par = {}
    wd = water_to_goal(h, shape, goals, box)
    # admissible: each raise serves at most 2 cells of a shortcut-free path, so >= ceil(w/2) raises remain;
    # the goal cell itself is a goal (never entered by a raise unless water), counted by the backward pass
    def hh(c, mask=0):
        w = wd.get(c)
        return 10**9 if w is None else COST * max(0, (w + 1) // 2 - bin(mask).count('1'))
    for s in starts:
        st = (s, 0); best[st] = 0; heapq.heappush(pq, (hh(s, 0), 0, s, 0)); par[st] = None
    while pq:
        f, d, c, mask = heapq.heappop(pq)
        if best.get((c, mask), 1e18) < d: continue
        if c in goals:
            # rebuild
            cells = []; clicks = []; st = (c, mask)
            while st is not None:
                cells.append(st[0]); pr = par[st]
                if pr is not None and pr[1] is not None: clicks.append(pr[1])
                st = pr[0] if pr else None
            return d, clicks[::-1], cells[::-1]
        cx, cy = c
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not dx and not dy: continue
                n = (cx+dx, cy+dy)
                if not ok_cell(n): continue
                # raised corners of n present in the mask?
                have = False
                for k in corners_of(*n):
                    if mask >> _widx(cx, cy, *k) & 1: have = True; break
                opts = []
                if land(n) or have:
                    opts.append((0, None, mask))
                else:
                    for k in corners_of(*n):
                        opts.append((COST, k, mask | 1 << _widx(cx, cy, *k)))
                for add, click, m2 in opts:
                    # remap mask into the window of n
                    nm = 0
                    for bit in range(16):
                        if m2 >> bit & 1:
                            x = cx - 1 + (bit & 3); y = cy - 1 + (bit >> 2)
                            if n[0]-1 <= x <= n[0]+2 and n[1]-1 <= y <= n[1]+2:
                                nm |= 1 << _widx(n[0], n[1], x, y)
                    nd = d + add
                    if maxcost is not None and nd > maxcost: continue
                    if hh(n) >= 10**9: continue
                    if nd < best.get((n, nm), 1e18):
                        best[(n, nm)] = nd; par[(n, nm)] = ((c, mask), click)
                        heapq.heappush(pq, (nd + hh(n, nm), nd, n, nm))
    return None

def replay(h0, clicks):
    """Apply raise clicks through the proven model; return (final h, total mana, per-click costs)."""
    g = Gen(0); g.h = list(h0); costs = []
    for (x, y) in clicks:
        g.raises = 0; g.raise_pt(x, y); costs.append(4*g.raises + 10)
    return g.h, sum(costs), costs

def connected(h, shape, a, b):
    comps, seen = components(h, shape)
    return a in seen and b in seen and seen[a] == seen[b]

# ---- baselines ----
def bresenham(a, b):
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1-x0), abs(y1-y0); sx = 1 if x1 > x0 else -1; sy = 1 if y1 > y0 else -1
    err = dx - dy; out = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        e2 = 2*err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 < dx: err += dx; y0 += sy
        out.append((x0, y0))
    return out

def straight_naive(h, shape, a, b):
    """Straight line of cells; for each cell not yet walkable raise its own (x,y) corner."""
    hh = list(h); clicks = []
    if any(shape[c[1]*64+c[0]] in (0x2f, 0x35) for c in bresenham(a, b)): return None   # line blocked by rock/swamp
    for c in bresenham(a, b):
        if not cell_walkable(hh, c[0], c[1], shape):
            clicks.append(c); g = Gen(0); g.h = hh; g.raise_pt(*c)
    return clicks

def straight_best(h, shape, a, b):
    """Same straight line of cells, corners chosen optimally (min raises) by the planner restricted to the line."""
    line = bresenham(a, b)
    # DP over line cells with the planner on a path constrained to the line: reuse plan with a custom ok-set
    S = set(line)
    box = None
    hh = list(h)
    import itertools
    # exact: minimum hitting set of corners over the water cells of the line (each line cell must be land or hit)
    water = [c for c in line if not cell_walkable(hh, c[0], c[1], shape)]
    if any(shape[c[1]*64+c[0]] in (0x2f, 0x35) for c in line): return None
    best = None
    # greedy interval cover is exact on a path, but do DP for safety: cells in order, choose corners
    from functools import lru_cache
    cand = []
    for c in water: cand.append(corners_of(*c))
    @lru_cache(None)
    def f(i, chosen):
        if i == len(water): return (0, ())
        c = water[i]; cs = corners_of(*c)
        if any(k in chosen for k in cs): return f(i+1, chosen)
        bestv = None
        for k in cs:
            nxt = tuple(x for x in chosen if abs(x[0]-c[0]) <= 3 and abs(x[1]-c[1]) <= 3) + (k,)
            v, rest = f(i+1, nxt)
            if bestv is None or v+1 < bestv[0]: bestv = (v+1, (k,)+rest)
        return bestv
    return list(f(0, ())[1])

def greedy(h, shape, a, b, cap=300):
    """Greedy nearest cell: from the current cell take the 8-neighbour closest (Euclid) to the goal, raise the
    corner of it nearest the goal if it is water.  Fails (None) on a blocked or looping walk."""
    hh = list(h); clicks = []; cur = a; seen = {a}
    for _ in range(cap):
        if cur == b: return clicks
        cands = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (cur[0]+dx, cur[1]+dy)
                if (dx or dy) and 0 <= n[0] < 64 and 0 <= n[1] < 64 and n not in seen and shape[n[1]*64+n[0]] not in (0x2f, 0x35):
                    cands.append((math.hypot(n[0]-b[0], n[1]-b[1]), not cell_walkable(hh, n[0], n[1], shape), n))
        if not cands: return None
        cands.sort(); _, wat, n = cands[0]
        if wat:
            k = min(corners_of(*n), key=lambda k: (math.hypot(k[0]-b[0]-0.5, k[1]-b[1]-0.5), k))
            clicks.append(k); g = Gen(0); g.h = hh; g.raise_pt(*k)
        seen.add(n); cur = n
    return None

def check_optimal(h, shape, a, b, box, kmax):
    """Exhaustive: smallest k with some k-subset of sea corners in box that connects a to b."""
    import itertools
    x0, y0, x1, y1 = box
    cs = [(x, y) for x in range(x0, x1+2) for y in range(y0, y1+2) if h[y*N+x] == 0]
    for k in range(0, kmax+1):
        for sub in itertools.combinations(cs, k):
            hh = list(h)
            for (x, y) in sub: hh[y*N+x] = 1
            if connected_box(hh, shape, a, b, box): return k, sub
    return None

def connected_box(hh, shape, a, b, box):
    st = [a]; seen = {a}
    while st:
        c = st.pop()
        if c == b: return True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (c[0]+dx, c[1]+dy)
                if n in seen or not (box[0] <= n[0] <= box[2] and box[1] <= n[1] <= box[3]): continue
                if cell_walkable(hh, n[0], n[1], shape): seen.add(n); st.append(n)
    return False

"""follow.py - cheap alternatives to A* for a PowerMonger lead, modelled on the game's own movement primitives.

Straight mode = the game's mode $10/$12 leg (astar.Map._step = $164bc, probe `dwell` points, walk them).
On a blocked probe (the game's mode $4a) the follower here replaces the $48 fan by one of:
  bug2   Bug2 wall following: remember the hit distance, follow the coast (hand L or R), leave when the S->T line
         is crossed closer than the hit and the way to the target is clear.
  kclear follow the coast, leave as soon as the straight line to the target is clear for K cells (optionally also
         closer than the hit: dhit=True).
Wall following = per tick, scan headings from the wall side (+A0 from the current heading) round through ahead to
the far side, take the first heading whose one-step point is land. Headings are multiples of TURN (256 = 360 deg).
Every tick is one step of length `speed` along the game's own rotate vector (ref.rotate, as mode $48 uses).
"""
import math
import sys
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'reversing/powermonger/commander'))
DATA = ROOT / 'scratchpad' / 'pm_bug2'          # untracked data: pairs.pkl, results.pkl, live/, maps/
(DATA / 'maps').mkdir(parents=True, exist_ok=True)
import astar  # noqa: E402
ref = astar.ref
W = 64


class Terrain:
    """fast exact in-plane sampler over an astar.Map's triangle arrays; off-plane points count as blocked."""

    def __init__(self, mp):
        self.mp = mp
        self.land = mp.land
        self.diag = mp.diag
        self._vec = {}

    def free(self, x, y):
        if x < 0 or y < 0 or x >= 0x4000 or y >= 0x8000:
            return False
        c = (y >> 8) * W + (x >> 8)
        lx, ly = x & 255, y & 255
        if self.diag[c]:
            h = 1 if lx + ly > 255 else 0
        else:
            h = 1 if lx > ly else 0
        return self.land[2 * c + h] != 0

    def vecs(self, speed, turn):
        k = (speed, turn)
        v = self._vec.get(k)
        if v is None:
            v = {}
            for h in range(0, 256, turn):
                d0, d1 = ref.rotate(self.mp.m, 0, (-speed) & 0xffff, h)
                v[h] = (ref.s16(d0), ref.s16(d1))
            self._vec[k] = v
        return v


def _cross(sx, sy, tx, ty, px, py):
    return (tx - sx) * (py - sy) - (ty - sy) * (px - sx)


def run(tr, start, target, speed, algo='bug2', hand=-1, turn=16, a0=64, k=4, dhit=False, max_ticks=400000,
        loop_detect=True, _rec=None, needclear=True, _ev=None):
    """returns dict(ok, ticks, length, why, end, nfollow). hand: +1/-1 = which side the wall is kept on (the sign of
    the heading increment toward the wall); 0 = pick per hit by the smaller first turn."""
    mp = tr.mp
    x, y = start
    tx, ty = target
    sx0, sy0 = start
    vec = tr.vecs(speed, turn)
    free = tr.free
    t = 0
    length = 0.0
    mode = 'S'
    h = 0
    dh = 0.0
    prevcross = 0
    seen = set()
    nfollow = 0
    reach2 = 2 * speed
    hit_hand = hand
    why = None
    while t < max_ticks:
        if mode == 'S':
            stx, sty, dwell, hd = mp._step(x, y, tx, ty, speed)
            if dwell == 0:
                if free(tx, ty):
                    length += math.hypot(tx - x, ty - y)
                    if _rec is not None:
                        _rec.append((tx, ty))
                    return dict(ok=True, ticks=t + 1, length=length, why='arrived', end=(tx, ty), nfollow=nfollow)
                return dict(ok=False, ticks=t, length=length, why='target-water', end=(x, y), nfollow=nfollow)
            px, py = x, y
            blocked = False
            nfree = 0
            for _ in range(dwell):
                px += stx
                py += sty
                if not free(px, py):
                    blocked = True
                    break
                nfree += 1
            if not blocked:
                length += math.hypot(stx * dwell, sty * dwell)
                x += stx * dwell
                y += sty * dwell
                if _rec is not None:
                    _rec.append((x, y))
                t += dwell
                continue
            # hit: walk up to the last land step before the water (the game's $48 would pivot where it stands, up to
            # `dwell` steps short of it; a wall follower has to be at the wall), then enter wall following
            if nfree:
                length += math.hypot(stx * nfree, sty * nfree)
                x += stx * nfree
                y += sty * nfree
                t += nfree
                if _rec is not None:
                    _rec.append((x, y))
            dh = math.hypot(tx - x, ty - y)
            h0 = hd & ~(turn - 1)
            if hand == 0:
                # smaller first turn away from the wall on the left (+) or the right (-)
                best = None
                for w in (1, -1):
                    for kk in range(0, 256 // turn):
                        c = (h0 - w * kk * turn) & 255
                        if free(x + vec[c][0], y + vec[c][1]):
                            if best is None or kk < best[0]:
                                best = (kk, w)
                            break
                hit_hand = best[1] if best else 1
            else:
                hit_hand = hand
            w = hit_hand
            h = None
            for kk in range(0, 256 // turn):
                c = (h0 - w * kk * turn) & 255
                if free(x + vec[c][0], y + vec[c][1]):
                    h = c
                    break
            if h is None:
                return dict(ok=False, ticks=t, length=length, why='trapped-at-hit', end=(x, y), nfollow=nfollow)
            if _ev is not None:
                _ev.append(('hit', t, x, y, round(dh)))
            mode = 'F'
            prevcross = _cross(sx0, sy0, tx, ty, x, y)
            if algo == 'bug2' and prevcross == 0:
                prevcross = 1
            continue
        # follow mode: one tick
        w = hit_hand
        moved = False
        for kk in range(a0 // turn, -(192 // turn) - 1, -1):
            c = (h + w * kk * turn) & 255
            nx, ny = x + vec[c][0], y + vec[c][1]
            if free(nx, ny):
                length += math.hypot(nx - x, ny - y)
                x, y, h = nx, ny, c
                moved = True
                if _rec is not None:
                    _rec.append((x, y))
                break
        t += 1
        nfollow += 1
        if not moved:
            return dict(ok=False, ticks=t, length=length, why='trapped', end=(x, y), nfollow=nfollow)
        if max(abs(tx - x), abs(ty - y)) < reach2:
            mode = 'S'
            continue
        d = math.hypot(tx - x, ty - y)
        if algo == 'bug2':
            cr = _cross(sx0, sy0, tx, ty, x, y)
            crossed = (cr == 0) or ((cr > 0) != (prevcross > 0))
            prevcross = cr if cr != 0 else prevcross
            if crossed and d < dh - 1e-9 and (not needclear or _clear(free, x, y, tx, ty, speed, 2)):
                mode = 'S'
                if _ev is not None:
                    _ev.append(('leave', t, x, y, round(d), round(dh)))
                dh = d
        else:
            ok = _clear(free, x, y, tx, ty, speed, k)
            if ok and (not dhit or d < dh - 1e-9):
                mode = 'S'
                dh = min(dh, d)
        if loop_detect and mode == 'F':
            key = (x, y, h, round(dh) if algo == 'bug2' or dhit else 0, prevcross > 0)
            if key in seen:
                return dict(ok=False, ticks=t, length=length, why='loop', end=(x, y), nfollow=nfollow)
            seen.add(key)
    return dict(ok=False, ticks=t, length=length, why='cap', end=(x, y), nfollow=nfollow)


def _clear(free, x, y, tx, ty, speed, kcells):
    """the straight line to the target is land for the next `kcells` cells (or to the target)."""
    dx, dy = tx - x, ty - y
    d = math.hypot(dx, dy)
    if d == 0:
        return True
    n = int(min(d, kcells * 256) // speed)
    ux, uy = dx / d * speed, dy / d * speed
    for i in range(1, n + 1):
        if not free(int(x + ux * i), int(y + uy * i)):
            return False
    return True


def trace(tr, start, target, speed, **kw):
    """the run() path as a list of points (re-runs with a recorder)."""
    import types
    pts = [start]
    orig = tr.free
    # record by wrapping run's position through max_ticks sampling is wasteful; instead replicate with a hook
    kw = dict(kw)
    kw['_rec'] = pts
    return run(tr, start, target, speed, **kw), pts

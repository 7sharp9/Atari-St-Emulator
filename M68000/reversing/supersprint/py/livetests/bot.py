"""bot.py - a steering bot for the human car (slot 1, joystick 0) that follows the game's own racing line.

The path is the drone line of `$eaea` for car index 1 (waypoint table at -4084(A4), count -4076(A4), the same wp advance and
0x100/0x200/0x400 control bits as ai_econ/drone_model.eaea), as a closed polyline of record starts in Q units (1 px = 8).
Each frame the bot projects the car onto the polyline, takes the point `look` units further along, picks the heading of the
16 direction vectors closest to that point and sends one joystick packet `fe <bits>`: right (0x08) raises the heading by one,
left (0x04) lowers it (live from lead_base.snap: right held 36 frames took the heading 12 -> 2, left 11 -> 5), fire (0x80) accelerates. Fire is released while the heading is 3 or more
steps off at speed > lift.

    from bot import Bot
    b = Bot(r)             # r: a Repl2 at a live race; reads the table once
    pkt = b.step(row)      # row: lt.sample(r) of this frame; returns the packet byte
"""
import math
from lt import *

QX, QY = -3738, -3746          # Q accumulators x, y (drone_model.place writes record x to -3738)


class Bot:
    def __init__(s, r, look=480, lift=70, car=1):
        s.look, s.lift = look, lift
        tbl = struct.unpack('>I', r.mem(A4 - 4084, 4))[0]
        cnt = r.words(A4 - 4076, 1)[0]
        raw = r.mem(tbl, cnt * 8)
        rec = [struct.unpack('>4h', raw[8 * i:8 * i + 8]) for i in range(cnt)]
        route = r.words(A4 - 1832, 4)
        s.dx = r.words(A4 - 4118, 16)
        s.dy = r.words(A4 - 4150, 16)
        # walk the line from wp 0 as $eaea does until it returns to a visited wp
        wp, seen, pts = 0, [], []
        while wp not in seen:
            seen.append(wp)
            x, y, ln, hd = rec[wp]
            pts.append((x, y))
            wp = (wp + 2) % cnt
            h = rec[wp][3]
            if h == 0x100:
                wp += 3 if (car & 1) == 0 else 2
            elif h & 0x200:
                wp += route[h & 3]
            elif h & 0x400:
                wp += h & 0xff
        s.wps = seen
        s.pts = pts
        n = len(pts)
        s.seg = []                                  # (ax, ay, ux, uy, length, cumulative start)
        cum = 0.0
        for i in range(n):
            ax, ay = pts[i]; bx, by = pts[(i + 1) % n]
            L = math.hypot(bx - ax, by - ay) or 1.0
            s.seg.append((ax, ay, (bx - ax) / L, (by - ay) / L, L, cum))
            cum += L
        s.total = cum
        s.k = None

    def project(s, x, y):
        """index of the nearest segment (searched near the last one once locked) and the arc length of the projection"""
        n = len(s.seg)
        cand = range(n) if s.k is None else [(s.k + d) % n for d in range(-1, 4)]
        best = None
        for i in cand:
            ax, ay, ux, uy, L, c = s.seg[i]
            t = max(0.0, min(L, (x - ax) * ux + (y - ay) * uy))
            d = math.hypot(ax + ux * t - x, ay + uy * t - y)
            if best is None or d < best[0]:
                best = (d, i, c + t)
        s.k = best[1]
        return best

    def point(s, arc):
        arc %= s.total
        for ax, ay, ux, uy, L, c in s.seg:
            if c <= arc < c + L:
                return ax + ux * (arc - c), ay + uy * (arc - c)
        return s.seg[0][0], s.seg[0][1]

    def step(s, row, car=1):
        x, y = row['q38'][car], row['q46'][car]
        d, i, arc = s.project(x, y)
        tx, ty = s.point(arc + s.look)
        vx, vy = tx - x, ty - y
        h = max(range(16), key=lambda k: (s.dx[k] * vx + s.dy[k] * vy) / math.hypot(s.dx[k], s.dy[k]))
        diff = (h - row['hd'][car] + 8) % 16 - 8
        pkt = 0x80
        if diff > 0: pkt |= 0x08
        elif diff < 0: pkt |= 0x04
        if abs(diff) >= 3 and row['spd'][car] > s.lift:
            pkt &= ~0x80
        s.last = (d, i, arc, h, diff)
        return pkt

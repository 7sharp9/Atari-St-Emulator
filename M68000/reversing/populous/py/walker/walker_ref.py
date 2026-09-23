"""walker_ref.py - Python reconstruction of the Populous (Atari ST) walker direction choice.

Transcribed from scratchpad/pop/pop_ad58.asm (runtime addresses). Each function takes a mutable
RAM image `m` (bytearray, absolute addresses), applies exactly the writes the 68000 routine makes,
and returns its D0.w.

    check_18198(m, cell, off)     $18198  step test: 0 land, 1 off-map/wrap, 2 rock $2f, 3 water
    land_value_18206(m, side, cell) $18206 settlement land value (+ writes $3b002, $37eb6)
    scan_f2f4(m, e, idx)          $f2f4   settle/gather/fight direction scan
    nearest_enemy_fe00(m, e)      $fe00   knight target (writes e+14)
    magnet_f6b2(m, e, idx)        $f6b2   magnet / leader / knight walker
    choose(m, e, idx)             the dispatch at $ef4c..$ef92 (mode 0, knight or armageddon -> $f6b2)
"""
import os, sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from ai_ref import rb, sb, rw, sw, rl, wb, ww, s16, rng, rec, sidest

ENT, ESZ = 0x3b278, 0x16
TERR = 0x36e78          # terrain class per cell
OVL = 0x3c522           # building overlay per cell
OCC = 0x37fd4           # occupancy (entity idx+1) per cell
VIS = 0x38fd8           # walker visit count per cell (word)
RING = 0x22b4e          # 17 cell offsets: 0, ring 1 (N E S W NE SE SW NW), ring 2
DIRS = 0x225a4          # 8 step offsets N NE E SE S SW W NW
HEAD = 0x225c8          # heading table, indexed (sx+1)*3+sy (base already folded -1)
OPP = 0x22ae2           # opposite direction index
ARMA = 0x3d524          # armageddon
OPTS = 0x219b2          # game options
QSEL = 0x3c4c6          # query-panel entity idx+1
COUNT = 0x3c4e2         # entity high-water count
NONE = 999
INFO = {}                # branch taken by the last call (coverage reporting only)


def ring(m, k): return sw(m, RING + 2 * k)
def dirw(m, k): return sw(m, DIRS + 2 * s16(k))
def sgn(v): return (v > 0) - (v < 0)


def check_18198(m, cell, off):
    cell, off = s16(cell), s16(off)
    if off == 0: return 0
    c = s16(cell + off)
    if c < 0 or c >= 0x1000: return 1
    dx = off & 0x3f
    if dx > 3: dx = s16(dx | 0xffc0)
    x = (cell & 0x3f) + dx
    if x < 0 or x > 0x3f: return 1
    t = rb(m, TERR + c)
    if t == 0: return 3
    if t == 0x2f: return 2
    return 0


def land_value_18206(m, side, cell):
    mine = (side + 0x1f) & 0xff
    cell = s16(cell)
    v = 0
    ww(m, 0x3b002, 0)
    ww(m, 0x37eb6, 0)
    for k in range(17):
        off = ring(m, k)
        r = check_18198(m, cell, off)
        if r:
            if r == 2: v = s16(v - 15)
            continue
        c = s16(cell + off)
        t = rb(m, TERR + c)
        flat = False
        if t == mine: flat = True
        elif t == 0x0f: ww(m, 0x37eb6, 1); flat = True
        elif k == 0: return 0
        if flat:
            if v == 0: v = 50
            v = s16(v + 15)
        d1 = sb(m, OVL + c)
        if k < 9 and rb(m, OVL + cell) == 0x2a and 0x29 <= d1 <= 0x2c:
            ww(m, 0x3b002, rw(m, 0x3b002) + 1)
            continue
        if k != 0 and 0x20 < d1 <= 0x2c:
            return 0
    if v < 35: v = 0
    if v == 0x131: v = 0xbea
    return v


def scan_f2f4(m, e, idx, trace=None, ideal=False):
    """returns the chosen step offset (a $22b4e entry) or 999.
    ideal=True: counterfactual scan of dir 0 once and all 8 neighbours from r (NOT the real code;
    used to measure what the rotation quirk changes)."""
    side = rb(m, e + 1)
    rng_ = rb(m, e + 2)
    last = sw(m, e + 10)
    best = [5] * 5          # -22(A6).. nearest distance per category
    res = [0] * 5           # -32(A6).. offset per category (uninitialised in the real code: stack junk)
    minv = 0x270f
    d6 = -1
    for k in range(9):
        if d6 == 0 and k == 1:
            d6 = (rng(m) & 7) + 1
        else:
            d6 += 1
        if d6 == 9: d6 = 1 if ideal else 0
        off = ring(m, d6)
        cell = sw(m, e + 8)
        d7 = 0
        while d7 != rng_:
            if check_18198(m, cell, off): break
            cell = s16(cell + off)
            if trace is not None: trace.append((k, d6, d7, cell))
            done = False
            if rb(m, TERR + cell) == 0x0f and d7 < best[0]:
                if d6 == 0:
                    if land_value_18206(m, side, cell):
                        best[0] = d7; res[0] = 0; done = True
                else:
                    blocked = False
                    for d5 in range(9, 17):
                        o2 = ring(m, d5)
                        if check_18198(m, cell, o2) == 0:
                            ov = rb(m, OVL + s16(cell + o2))
                            if 0x20 < ov <= 0x2c:           # word compare of the zero-extended byte
                                blocked = True; break
                    if not blocked:
                        best[0] = d7; res[0] = off; done = True
            if not done and d6 != 0:
                o = rb(m, OCC + cell)
                cat = None
                if o != 0 and (o - 1) != s16(idx):
                    p = ENT + (o - 1) * ESZ
                    if rb(m, p) & 8 and d7 < best[1]: cat = 1
                    elif rb(m, p + 1) != side and d7 < best[2]: cat = 2
                    elif rb(m, p) & 2 and d7 < best[3]: cat = 3
                if cat is not None:
                    best[cat] = d7; res[cat] = off
                elif off != last:
                    vv = rw(m, VIS + cell * 2)
                    if vv < minv or (vv == minv and d7 < best[4]):
                        minv = vv; best[4] = d7; res[4] = off
            d7 += 1
    md = rw(m, sidest(side) + 4)
    INFO.clear(); INFO['mode'] = md; INFO['best'] = list(best)
    if md == 3 and best[2] != 5: INFO['cat'] = 'fight2'; return res[2]
    if md == 2 and best[3] != 5: INFO['cat'] = 'gather3'; return res[3]
    for i in range(5):
        if best[i] != 5: INFO['cat'] = 'c%d' % i; return res[i]
    INFO['cat'] = 'none'
    return NONE


def nearest_enemy_fe00(m, e):
    x0, y0 = rw(m, e + 8) & 0x3f, s16(rw(m, e + 8)) >> 6
    best = 0x270f
    struct_l(m, e + 14, e)
    for i in range(s16(rw(m, COUNT))):
        p = ENT + i * ESZ
        if rb(m, p + 1) == rb(m, e + 1): continue
        if sw(m, p + 4) <= 0: continue
        if rb(m, p) & 0x80: continue
        dx = (rw(m, p + 8) & 0x3f) - x0
        dy = (s16(rw(m, p + 8)) >> 6) - y0
        d = s16(abs(s16(dx)) + abs(s16(dy)))
        if d < best:
            best = d
            struct_l(m, e + 14, p)


def struct_l(m, a, v):
    ww(m, a, v >> 16); ww(m, a + 2, v)


def heading(m, e, tcell):
    cell = sw(m, e + 8)
    sx = sgn(s16((tcell & 0x3f) - (cell & 0x3f)))
    sy = sgn(s16((s16(tcell) >> 6) - (cell >> 6)))
    return sw(m, HEAD + 2 * ((sx + 1) * 3 + sy))


def post_raise(m, side, cell):
    r = rec(side)
    wb(m, r, 1); wb(m, r + 1, cell & 0x3f); wb(m, r + 2, s16(cell) >> 6); ww(m, r + 8, 1)


def magnet_f6b2(m, e, idx):
    side = rb(m, e + 1)
    st = sidest(side)
    knight = rl(m, e + 14)
    INFO.clear()
    if knight:
        INFO['who'] = 'knight'
        t = knight
        if (rw(m, e + 8) == rw(m, t + 8) or sw(m, t + 4) <= 0 or rb(m, t + 1) == side
                or rb(m, t) & 0x80):
            nearest_enemy_fe00(m, e); INFO['who'] = 'knight-reacq'
        tcell = rw(m, rl(m, e + 14) + 8)
    elif rw(m, st) == 0:
        INFO['who'] = 'noleader'
        if rw(m, st + 2) == rw(m, e + 8):
            INFO['who'] = 'becomes-leader'
            ww(m, st, idx + 1)
            if rw(m, QSEL) == 0: ww(m, QSEL, idx + 1)
            wb(m, e + 1, side)
        tcell = rw(m, st + 2)
    elif s16(rw(m, st) - 1) == s16(idx):
        INFO['who'] = 'leader'
        tcell = rw(m, st + 2)
    else:
        INFO['who'] = 'follower'
        tcell = rw(m, ENT + s16(rw(m, st) - 1) * ESZ + 8)
    h = heading(m, e, tcell)
    cell = sw(m, e + 8)
    dh = dirw(m, h)
    r = check_18198(m, cell, dh)
    if r == 0 and (rl(m, e + 14) == 0 or rb(m, TERR + s16(cell + dh)) != 0x35):
        INFO['how'] = 'direct'; wb(m, e + 21, dh); return s16(sb(m, e + 21))
    if r == 2 and rw(m, ARMA):
        INFO['how'] = 'rock-arma'; wb(m, e + 21, dh); return s16(sb(m, e + 21))
    arma = rw(m, ARMA)
    if (rw(m, rec(side) + 6) == 1 or arma) and (not (rw(m, OPTS) & 4) or arma):
        if r == 3:
            post_raise(m, side, cell); INFO['post'] = 'raise-own'
        elif rb(m, TERR + s16(cell + dh)) == 0x35 and not (rw(m, OPTS) & 8) and not arma:
            post_raise(m, side, s16(cell + dh)); INFO['post'] = 'raise-swamp'
    d7 = s16(h - 1)
    n = 0
    while n < 8:
        if d7 < 0: d7 = 7
        if d7 > 7: d7 = 0
        o = dirw(m, d7)
        if (check_18198(m, cell, o) == 0 and o != sb(m, e + 21)
                and (rl(m, e + 14) == 0 or rb(m, TERR + s16(cell + o)) != 0x35)):
            wb(m, e + 21, dirw(m, sw(m, OPP + 2 * d7)))
            INFO['how'] = 'fallback%d' % n
            return o
        d7 += 1; n += 1
    wb(m, e + 21, dirw(m, sw(m, OPP + 2 * d7)))
    INFO['how'] = 'none'
    return NONE


def uses_f6b2(m, e):
    side = rb(m, e + 1)
    return rw(m, sidest(side) + 4) == 0 or rl(m, e + 14) != 0 or rw(m, ARMA) != 0


def choose(m, e, idx):
    return magnet_f6b2(m, e, idx) if uses_f6b2(m, e) else scan_f2f4(m, e, idx)

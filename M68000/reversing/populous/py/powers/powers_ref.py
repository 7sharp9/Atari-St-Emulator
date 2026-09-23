"""powers_ref.py - Python reconstructions of the Populous power routines, transcribed from the
disassembly (scratchpad/pop/pop_ad58.asm), operating in place on a full RAM image (bytearray).

  flood        $11f6a(side)            earthquake   $12350(side, x, y)   (pre / post split at $12470)
  volcano      $1263c(side, x, y)      swamp        $12a14(side, x, y)
  knight       $12ba0(side)            armageddon   $12d26(side)
  knight_find_target $fe00(e)          walker_merge $feca(i, j)
  combat_resolve $108b8(w, l)          (knight-winner raze path + walker-loser path)

Helpers transcribed as well: rand $16702, raise_point $bf60, lower_point $d262,
derive_cells $c0ee, set_magnet_cell $129d6, entity_kill $10068, entity_anim_advance $101a0
(settlement case only), cell_step_check $18198, land_value $18206.
Screen-side calls ($c27a minimap redraw, $2065a Setscreen, $14364/$16ed8 shake frames,
$16cf0/$16d20 pointer hide/show in TEXT, $b15a sound wait) write nothing in DATA/BSS and are
not modelled.
"""
import struct

HGT, ALT, SHAPE, FEAT, OCC, VISIT = 0x34be4, 0x33be4, 0x36e78, 0x3c522, 0x37fd4, 0x38fd8
SIDE, ENT, ESZ, GOD, GSZ = 0x3b226, 0x3b278, 0x16, 0x21e0c, 0x2e
SEED, PAINT, PAUSE, ARMA, HUMAN = 0x3d52e, 0x3b276, 0x3b274, 0x3d524, 0x3affe
SCORE, SOUND, NENT, QUERY, FRAME = 0x36cea, 0x36d02, 0x3c4e2, 0x3c4c6, 0x3c4c8
BOX = (0x36ce8, 0x3b006, 0x3d522, 0x37eb8)          # min x, max x, min y, max y
POINTS = 0x37f8a
VIEWOFF = 0x2287a
COST = {'floor': 0x21984, 'eq': 0x21990, 'swamp': 0x21994, 'knight': 0x21998, 'volcano': 0x2199c,
        'flood': 0x219a0, 'arma': 0x219a4}
FOOT = 0x22b4e
COV = {}


def cov(k):
    COV[k] = COV.get(k, 0) + 1


def s16(v): v &= 0xffff; return v - 0x10000 if v & 0x8000 else v
def s32(v): v &= 0xffffffff; return v - 0x100000000 if v & 0x80000000 else v
def rb(m, a): return m[a & 0xffffff]
def rw(m, a): return struct.unpack_from('>h', m, a & 0xffffff)[0]
def ruw(m, a): return struct.unpack_from('>H', m, a & 0xffffff)[0]
def rl(m, a): return struct.unpack_from('>i', m, a & 0xffffff)[0]
def wb(m, a, v): m[a & 0xffffff] = v & 0xff
def ww(m, a, v): struct.pack_into('>H', m, a & 0xffffff, v & 0xffff)
def wl(m, a, v): struct.pack_into('>I', m, a & 0xffffff, v & 0xffffffff)


def rand(m):
    s = ((ruw(m, SEED) * 0x24a1) + 0x24df) & 0x7fff
    ww(m, SEED, s)
    return s


def rmod(n):
    """68000 divs remainder for a non-negative rand() value: plain modulo."""
    return lambda m: rand(m) % n


def ent(i): return ENT + ESZ * i
def mana_a(side): return SIDE + 16 * side + 12


def gate(m, side, cost, bit, arma_check=True):
    """The common power gate. Returns True if the power proceeds; subtracts the cost."""
    if rw(m, PAINT):
        return True
    c = rl(m, COST[cost])
    if rl(m, mana_a(side)) < c:
        return False
    if arma_check and rw(m, ARMA):
        return False
    if rw(m, PAUSE):
        return False
    if not (rw(m, GOD + GSZ * side + 14) & bit):
        return False
    wl(m, mana_a(side), rl(m, mana_a(side)) - c)
    return True


def score(m, side, n):
    if side == rw(m, HUMAN):
        wl(m, SCORE, rl(m, SCORE) + n)


# ---------------------------------------------------------------- terrain primitives
def _grow_box(m, x, y):
    if x < rw(m, BOX[0]): ww(m, BOX[0], x)
    if x > rw(m, BOX[1]): ww(m, BOX[1], x)
    if y < rw(m, BOX[2]): ww(m, BOX[2], y)
    if y > rw(m, BOX[3]): ww(m, BOX[3], y)


NB = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))   # E SE S SW W NW N NE


def raise_point(m, x, y):
    """$bf60. Neighbour comparisons read raw memory (row wrap / outside the array)."""
    if x > 64 or x < 0 or y > 64 or y < 0:
        return 0
    a = HGT + 2 * s16(x + 65 * y)
    if rw(m, a) >= 8:
        return rw(m, a)
    ww(m, POINTS, rw(m, POINTS) + 1)
    ww(m, a, rw(m, a) + 1)
    for dx, dy in NB:
        if s16(rw(m, a) - rw(m, a + 2 * (dx + 65 * dy))) > 1:
            raise_point(m, x + dx, y + dy)
    _grow_box(m, x, y)
    return rw(m, a)


def lower_point(m, x, y):
    """$d262, mirror of $bf60."""
    if x > 64 or x < 0 or y > 64 or y < 0:
        return 0
    a = HGT + 2 * s16(x + 65 * y)
    if rw(m, a) == 0:
        return 0
    ww(m, POINTS, rw(m, POINTS) + 1)
    ww(m, a, rw(m, a) - 1)
    for dx, dy in NB:
        if s16(rw(m, a + 2 * (dx + 65 * dy)) - rw(m, a)) > 1:
            lower_point(m, x + dx, y + dy)
    _grow_box(m, x, y)
    return rw(m, a)


def derive_cells(m, x0, y0, x1, y1):
    """$c0ee: x0..x1 outer, y0..y1 inner, all signed-word loops."""
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            c = s16(x + (y << 6))
            a = HGT + 2 * s16(x + 65 * y)
            h0, h1, h3, h2 = rw(m, a), rw(m, a + 2), rw(m, a + 130), rw(m, a + 132)
            s = s16(h0 + h1 + h3 + h2) >> 2
            bits = (h0 > s) | (h1 > s) << 1 | (h2 > s) << 2 | (h3 > s) << 3
            if rb(m, SHAPE + c) == 0x2f and (bits or s):
                d5 = rb(m, SHAPE + c)
            else:
                wb(m, SHAPE + c, bits); d5 = bits
            if s and not d5:
                s -= 1; d5 = 0xf
            if s == 0 and d5 != 0xf and d5:
                d5 += 0x10
            wb(m, ALT + c, s)
            if rb(m, SHAPE + c) != 0x2f:
                wb(m, SHAPE + c, d5)
            else:
                d5 = 0x2f
            if d5 == 0:
                wb(m, FEAT + c, 0)
            ww(m, VISIT + 2 * c, 0)


def _clamp_box_derive(m):
    if rw(m, BOX[0]) < 1: ww(m, BOX[0], 1)
    if rw(m, BOX[1]) > 63: ww(m, BOX[1], 63)
    if rw(m, BOX[2]) < 1: ww(m, BOX[2], 1)
    if rw(m, BOX[3]) > 63: ww(m, BOX[3], 63)
    derive_cells(m, rw(m, BOX[0]) - 1, rw(m, BOX[2]) - 1, rw(m, BOX[1]), rw(m, BOX[3]))


# ---------------------------------------------------------------- the powers
def flood(m, side):
    """$11f6a"""
    if not gate(m, side, 'flood', 0x80):
        return
    score(m, side, 0xfa)
    for i in range(0x1081):
        a = HGT + 2 * i
        if rw(m, a) > 0:
            ww(m, a, rw(m, a) - 1)
    derive_cells(m, 0, 0, 63, 63)
    ww(m, SOUND, 0x4a)


def earthquake_pre(m, side, x, y):
    """$12350 up to the shake loop: gate, dirty box, sound, score. False if the gate refuses."""
    if not gate(m, side, 'eq', 0x08):
        return False
    ww(m, BOX[0], x); ww(m, BOX[1], x); ww(m, BOX[2], y); ww(m, BOX[3], y)
    wl(m, VIEWOFF, rl(m, VIEWOFF) - 0xa0)      # screen shake offset; net 0 after the 20 frames
    ww(m, SOUND, 0x4c)
    score(m, side, 0x19)
    return True


def earthquake_post(m, side, x, y):
    """$12470..$12638: 2 passes over corners (x..x+8) outer, (y..y+8) inner."""
    wl(m, VIEWOFF, rl(m, VIEWOFF) + 0xa0)
    for _ in range(2):
        for cx in range(x, x + 9):
            for cy in range(y, y + 9):
                if rw(m, HGT + 2 * s16(cx + 65 * cy)) == 0:
                    continue
                r = rand(m) % 5
                if r == 1:
                    raise_point(m, cx, cy)
                elif r in (2, 3, 4):
                    lower_point(m, cx, cy)
    _clamp_box_derive(m)


def earthquake_shake_net(m):
    """what the 20 shake frames do to DATA/BSS: $2287a -= $a0, then +/-$1e0 alternately (net 0)."""
    pass


def earthquake(m, side, x, y):
    if earthquake_pre(m, side, x, y):
        earthquake_post(m, side, x, y)


def volcano(m, side, x, y):
    """$1263c"""
    if not gate(m, side, 'volcano', 0x40):
        return
    score(m, side, 0x64)
    ww(m, BOX[0], x); ww(m, BOX[1], x); ww(m, BOX[2], y); ww(m, BOX[3], y)
    ww(m, SOUND, 0x4b)
    for a in range(5):
        for i in range(a, 9 - a):
            for j in range(a, 9 - a):
                r = rand(m) % 5
                if r in (1, 2, 4):
                    raise_point(m, x + i, y + j)
    # both locals read $3b226 (side 0's leader): the quirk under test
    ld = rw(m, SIDE)
    lc0 = rw(m, ent(ld - 1) + 8) if ld else 0
    lc1 = lc0
    for cx in range(x, x + 8):
        for cy in range(y, y + 8):
            if not (0 <= cx < 64 and 0 <= cy < 64):
                continue
            c = cx + (cy << 6)
            if rand(m) % 5:
                continue
            if c == lc0 or c == lc1 or c == rw(m, SIDE + 2) or c == rw(m, SIDE + 16 + 2):
                cov('volcano_rock_skipped_protected')
                continue
            l1 = rw(m, SIDE + 16)
            if l1 and c == rw(m, ent(l1 - 1) + 8):
                cov('volcano_rock_on_side1_leader_cell')
            wb(m, SHAPE + c, 0x2f)
            wb(m, FEAT + c, 0)
    _clamp_box_derive(m)
    ww(m, SOUND, 0x4b)


def swamp(m, side, x, y):
    """$12a14: 30 tries, no redraw."""
    if not gate(m, side, 'swamp', 0x10):
        return
    score(m, side, 0x32)
    for _ in range(30):
        cx = s16(x + rand(m) % 7 - 3)
        cy = s16(y + rand(m) % 7 - 3)
        if not (0 <= cx < 64 and 0 <= cy < 64):
            continue
        c = cx + (cy << 6)
        if rb(m, SHAPE + c) in (0x0f, 0x1f, 0x20, 0x42) and rb(m, OCC + c) == 0:
            wb(m, SHAPE + c, 0x35)


def set_magnet_cell(m, side, cell):
    """$129d6"""
    if rw(m, PAUSE):
        return
    ww(m, SIDE + 16 * side + 2, cell)
    ww(m, 0x3c4ca if side == 0 else 0x3d526, cell)


def knight_find_target(m, e):
    """$fe00(e): nearest live (str > 0), non-ruin enemy by |dx|+|dy|, first wins ties; self if none."""
    best = 9999
    cx, cy = rw(m, e + 8) & 0x3f, rw(m, e + 8) >> 6
    wl(m, e + 14, e)
    for k in range(rw(m, NENT)):
        o = ent(k)
        if rb(m, o + 1) == rb(m, e + 1) or rw(m, o + 4) <= 0 or rb(m, o) & 0x80:
            continue
        d = s16(abs(s16((rw(m, o + 8) & 0x3f) - cx)) + abs(s16((rw(m, o + 8) >> 6) - cy)))
        if d < best:
            best = d
            wl(m, e + 14, o)
        elif d == best:
            cov('fe00_tie_first_kept')
    cov('fe00_self' if rl(m, e + 14) == e else 'fe00_target')


def knight(m, side):
    """$12ba0"""
    if rw(m, SIDE + 16 * side) == 0:
        return
    if not gate(m, side, 'knight', 0x20):
        return
    score(m, side, 0x96)
    e = ent(rw(m, SIDE + 16 * side) - 1)
    wb(m, e + 20, 1)
    knight_find_target(m, e)
    set_magnet_cell(m, side, rw(m, e + 8))
    ww(m, SIDE + 16 * side, 0)
    ww(m, SOUND, 0x45)


def armageddon(m, side):
    """$12d26: no armageddon check; paint mode skips the score too."""
    if not rw(m, PAINT):
        c = rl(m, COST['arma'])
        if rl(m, mana_a(side)) < c or rw(m, PAUSE) or not (rw(m, GOD + GSZ * side + 14) & 0x100):
            return
        wl(m, mana_a(side), rl(m, mana_a(side)) - c)
        score(m, side, 0x1388)
    for k in range(rw(m, NENT)):
        wl(m, ent(k) + 14, 0)
    ww(m, SOUND, 0x49)
    ww(m, ARMA, 1)


# ---------------------------------------------------------------- knight rules in the people code
def walker_merge(m, i, j):
    """$feca(i, j): walker i merges into entity j."""
    src, dst = ent(i), ent(j)
    ld = rw(m, SIDE + 16 * rb(m, src + 1)) - 1
    if rl(m, src + 14):
        if rb(m, dst) == 1:
            cov('merge_knight_into_settlement_refused')
            return                                   # a knight never merges into a settlement
        cov('merge_knight_pointer_moved')
        wl(m, dst + 14, rl(m, src + 14))
    t = rw(m, src + 4) + rw(m, dst + 4)
    ww(m, dst + 4, 32000 if t > 32000 else t)
    if i == ld:
        ww(m, SIDE + 16 * rb(m, src + 1), j + 1)
    if i == rw(m, QUERY) - 1:
        ww(m, QUERY, j + 1)
    if j > i:
        pa = SIDE + 16 * rb(m, src + 1) + 8
        wl(m, pa, rl(m, pa) - rw(m, src + 4))
    if rb(m, src + 3) > rb(m, dst + 3):
        wb(m, dst + 3, rb(m, src + 3))
    ww(m, src + 4, 0)
    wb(m, dst, rb(m, dst) & 0x9f)
    ww(m, dst + 12, 0)


def cell_step_check(m, cell, off):
    """$18198"""
    if off == 0:
        return 0
    c = s16(cell + off)
    if c < 0 or c >= 0x1000:
        return 1
    dx = off & 0x3f
    if dx > 3:
        dx = s16(dx | 0xffc0)
    x = (cell & 0x3f) + dx
    if x < 0 or x >= 0x40:
        return 1
    t = rb(m, SHAPE + c)
    return 3 if t == 0 else 2 if t == 0x2f else 0


def land_value(m, side, cell):
    """$18206: also clears/counts $3b002 (castle wall pieces) and sets $37eb6 when a $0f cell is seen."""
    mine = (side + 0x1f) & 0xff
    v = 0
    ww(m, 0x3b002, 0); ww(m, 0x37eb6, 0)
    for k in range(17):
        off = rw(m, FOOT + 2 * k)
        r = cell_step_check(m, cell, off)
        if r:
            if r == 2:
                v -= 15
            continue
        c = s16(cell + off)
        t = rb(m, SHAPE + c)
        if t == mine or t == 0x0f:
            if t != mine:
                ww(m, 0x37eb6, 1)
            if v == 0:
                v = 50
            v += 15
        elif k == 0:
            return 0
        d1 = rb(m, FEAT + c); d1 = d1 - 256 if d1 > 127 else d1
        if k < 9 and rb(m, FEAT + cell) == 0x2a and 0x29 <= d1 <= 0x2c:
            ww(m, 0x3b002, rw(m, 0x3b002) + 1)
            continue
        if k != 0 and 0x20 < d1 <= 0x2c:
            return 0
    if v < 35:
        v = 0
    if v == 305:
        v = 3050
    return v


def anim_settlement(m, e):
    """$101a0 for flags == 1 with str != 0: sprite from the land value."""
    if rw(m, e + 4) == 0:
        return
    v = land_value(m, rb(m, e + 1), rw(m, e + 8))
    ww(m, e + 12, 0x2a if v >= 0xbea else s16(v * 10) // 0x131 + 0x20)


def entity_kill(m, e, idx):
    """$10068, for a non-fighting, non-settlement entity (the only case the raze test reaches)."""
    ww(m, e + 4, 0)
    if rb(m, e) == 8:                                # the attacker dies: its opponent stops fighting
        o = ent(ruw(m, e + 6))
        wb(m, o, rb(m, o) & 0xf7)
    assert not (rb(m, e) & 1), 'settlement kill ($10366 release) not modelled'
    cell = rw(m, e + 8)
    if idx == rb(m, OCC + cell) - 1:
        wb(m, OCC + cell, 0)
    c2 = s16(cell - rw(m, e + 10))
    if idx == rb(m, OCC + c2) - 1:
        wb(m, OCC + c2, 0)
    sd = rb(m, e + 1)
    if idx == rw(m, SIDE + 16 * sd) - 1:
        ww(m, SIDE + 16 * sd, 0)
        set_magnet_cell(m, sd, cell)
    if idx == rw(m, QUERY) - 1:
        ww(m, QUERY, 0)


def combat_resolve(m, wi, li):
    """$108b8(winner, loser) for: any winner vs a walker loser, and a KNIGHT winner (str != 0) vs a
    settlement loser (the raze). The non-knight take-over path ($10366/$18206) is not modelled."""
    W, L = ent(wi), ent(li)
    ww(m, 0x3c514 + 2 * rb(m, W + 1), rw(m, 0x3c514 + 2 * rb(m, W + 1)) + 1)
    if not (rb(m, L) & 1):
        wb(m, W, 1 if rb(m, W) & 1 else 2)
        cov('resolve_walker_loser')
        if rl(m, L + 14):
            e = rw(m, 0x3c4ea)
        elif li == rw(m, SIDE + 16 * rb(m, L + 1)) - 1:
            e = rw(m, 0x3c4ec)
        else:
            e = rw(m, 0x3c4e8)
    else:
        wb(m, L, 1)
        anim_settlement(m, L)
        lv = s16(rw(m, L + 12) - 0x20)
        e = 100 if lv < 0 or lv > 10 else rw(m, 0x3c4fe + 2 * lv)
        assert rl(m, W + 14) != 0 and rw(m, W + 4) != 0, 'take-over path not modelled'
        wb(m, L, 0x80); ww(m, L + 4, 1); ww(m, L + 6, 40)
        wb(m, W, 2)
        lc = rw(m, L + 8)
        col = rb(m, L + 1) + 0x1f
        cov('raze_castle' if rb(m, FEAT + lc) == 0x2a else 'raze_town')
        if rb(m, FEAT + lc) == 0x2a:
            for k in range(25):
                c = s16(rw(m, FOOT + 2 * k) + lc)
                if 0 < k < 9 and 0x28 < rb(m, FEAT + c) < 0x2d:
                    wb(m, FEAT + c, rb(m, FEAT + c) + 0x15)
                if rb(m, SHAPE + c) == col:
                    wb(m, SHAPE + c, 0x42)
        else:
            for k in range(17):
                off = rw(m, FOOT + 2 * k)
                if cell_step_check(m, lc, off) == 0:
                    c = s16(off + lc)
                    if rb(m, SHAPE + c) == col:
                        wb(m, SHAPE + c, 0x42)
        if 0x1f < rb(m, FEAT + lc) < 0x2b:
            wb(m, FEAT + lc, rb(m, FEAT + lc) + 0x15)
        if li == rb(m, OCC + lc) - 1:
            wb(m, OCC + lc, 0)
    wc = rw(m, W + 8)
    if li == rb(m, OCC + wc) - 1 or rb(m, OCC + wc) == 0:
        wb(m, OCC + wc, wi + 1)
    if rb(m, W + 20):
        g = GOD + GSZ * rb(m, W + 1)
        ww(m, g + 30, rw(m, W + 8)); ww(m, g + 28, 2)
        wb(m, W + 20, rb(m, W + 20) - 1)
    if rb(m, L + 20):
        ww(m, GOD + GSZ * rb(m, L + 1) + 28, 0)
    ww(m, W + 10, 0)
    wb(m, W, rb(m, W) | 4)
    ww(m, W + 12, 0x55)
    ma = mana_a(rb(m, W + 1)); wl(m, ma, rl(m, ma) + e)
    ml = mana_a(rb(m, L + 1)); wl(m, ml, rl(m, ml) - e)
    if rl(m, ml) < rl(m, COST['floor']):
        wl(m, ml, rl(m, COST['floor']))
    if li == rw(m, QUERY) - 1:
        ww(m, QUERY, wi + 1)
    if rw(m, L + 4) <= 0:
        entity_kill(m, L, li)

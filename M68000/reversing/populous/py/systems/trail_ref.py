"""trail_ref.py - Python model of the trail effects (entity slots $d1/$d2).

  spawn_13372(m, typ, edge, a6)  $13372: put a trail entity in the first slot with str == 0
  tick_12f84(m)                  $12f84: per-frame animation and the 8-frame step
  kill_10068(m, e, idx)          $10068 entity_kill, walker victims only (settlement release
                                 $10366 and the leader path $129d6 raise NotModelled)

m is a bytearray of RAM (absolute addresses). The step table $21e7c holds one 12-byte record per
type: +0 step offset, +2 (low byte) lower frame bound, +4 (low byte) upper frame bound, +6/+8/+10
the three cell offsets marked around the entity after each step.
"""
import struct

ENT, ESZ = 0x3b278, 0x16
TBL = 0x21e7c
CLASS, FEAT, OCC = 0x36e78, 0x3c522, 0x37fd4
SIDE = 0x3b226
GOD = 0x21e0c
SEED = 0x3d52e
FRAME = 0x3c4c8
KEY_B4, KEY_58 = 0x3c4b4, 0x21d58


class NotModelled(Exception):
    pass


def rw(m, a): return struct.unpack_from('>H', m, a)[0]
def rsw(m, a): return struct.unpack_from('>h', m, a)[0]
def rl(m, a): return struct.unpack_from('>I', m, a)[0]
def ww(m, a, v): struct.pack_into('>H', m, a, v & 0xffff)
def s16(v): v &= 0xffff; return v - 0x10000 if v & 0x8000 else v
def s8(v): v &= 0xff; return v - 0x100 if v & 0x80 else v


def rand(m):
    s = (rw(m, SEED) * 0x24a1 + 0x24df) & 0x7fff
    ww(m, SEED, s)
    return s


def tbl(m, typ, k):
    """word k (0..5) of the type's record; typ is the signed entity byte +20."""
    return rsw(m, TBL + typ * 12 + 2 * k)


def step_check(m, cell, off):
    """$18198 cell_step_check: 1 off the map (or across the x edge), 2 rock $2f, 3 water, else 0."""
    off = s16(off); cell = s16(cell)
    if off == 0:
        return 0
    c = s16(cell + off)
    if c < 0 or c >= 0x1000:
        return 1
    dx = off & 0x3f
    if dx > 3:
        dx = s16(dx | 0xffc0)
    if s16(dx + (cell & 0x3f)) < 0 or s16(dx + (cell & 0x3f)) > 0x3f:
        return 1
    v = m[CLASS + c]
    return 3 if v == 0 else 2 if v == 0x2f else 0


def kill_10068(m, e, idx):
    side = m[e + 1]
    ww(m, e + 4, 0)
    if m[e] == 8:
        o = ENT + rw(m, e + 6) * ESZ
        m[o] &= 0xf7
    if m[e] & 1:
        raise NotModelled('settlement victim ($10366)')
    cell = rsw(m, e + 8)
    if m[OCC + cell] - 1 == idx:
        m[OCC + cell] = 0
    c2 = s16(cell - rsw(m, e + 10))
    if m[OCC + c2] - 1 == idx:
        m[OCC + c2] = 0
    if rw(m, SIDE + 16 * side) - 1 == idx:
        raise NotModelled('leader victim ($129d6)')
    if rw(m, 0x3c4c6) - 1 == idx:
        ww(m, 0x3c4c6, 0)


def tick_12f84(m, plots=None):
    """one call of $12f84 over slots $d1, $d2. plots collects the $166b2 minimap calls."""
    for slot in (0xd1, 0xd2):
        e = ENT + slot * ESZ
        if rw(m, e + 4) == 0:
            continue
        ww(m, e + 12, rw(m, e + 12) + 1)
        d = s8(m[e + 21])
        t6 = (rw(m, e + 6) + d) & 0xffff
        ww(m, e + 6, t6)
        if t6 >= m[e + 2] or t6 <= m[e + 3]:          # unsigned word compares
            d = -d
            m[e + 21] = d & 0xff
        if s16(rw(m, e + 12)) <= 7:
            continue
        ww(m, e + 12, 0)
        cell = rsw(m, e + 8)
        if m[OCC + cell] - 1 == slot:
            m[OCC + cell] = 0
        typ = s8(m[e + 20])
        if rw(m, e + 10) == 0:
            ww(m, e + 10, tbl(m, typ, 0))
        if step_check(m, cell, rw(m, e + 10)) == 1:
            ww(m, e + 4, 0)
            continue
        cell = s16(cell + rsw(m, e + 10))
        ww(m, e + 8, cell)
        for i in range(3):
            so = tbl(m, typ, 3 + i)
            if step_check(m, cell, so) == 1:
                continue
            c = s16(cell + so)
            v = m[CLASS + c]
            if typ == 0:
                if v != 0 and v != 0x10:
                    m[FEAT + c] = 0x32 + i
            elif typ == 1:
                if v in (0x0f, 0x1f, 0x20, 0x42):
                    m[CLASS + c] = 0x35
            else:
                if v != 0 and v != 0x10:
                    m[CLASS + c] = (0x2f + i) & 0xff
                    if plots is not None:
                        plots.append((c, m[0x21ea0 + m[CLASS + c]]))
            if m[OCC + c]:
                idx = m[OCC + c] - 1
                kill_10068(m, ENT + idx * ESZ, idx)
        m[OCC + cell] = slot + 1


def spawn_13372(m, typ, edge, a6):
    """$13372(typ, edge). a6 = the routine's frame pointer (entry SP - 4): the mismatch branch
    writes through the uninitialised local at -14(A6)."""
    typ, edge = s16(typ), s16(edge)
    if typ > 2:
        return None
    hum = rsw(m, 0x3affe)
    p_h = GOD + hum * 0x2e + 6
    p_o = GOD + (1 if hum == 0 else 0) * 0x2e + 6
    for slot in (0xd1, 0xd2):
        e = ENT + slot * ESZ
        if rw(m, e + 4) != 0:
            continue
        ww(m, e + 4, 1)
        m[e] = 2
        if edge == 0:
            r = rand(m) % 125
            ww(m, e + 8, (r >> 1) + 0xfc0)
        elif edge == 1:
            if rand(m) & 1:
                ww(m, e + 8, (((20 + rand(m) % 43) << 6) + 0x3f))
            else:
                ww(m, e + 8, (((20 + rand(m) % 43) << 6) + 0xfc0))
        elif edge == 2:
            if rand(m) & 1:
                ww(m, e + 8, (rand(m) % 43) << 6)
            else:
                ww(m, e + 8, rand(m) % 43)
        m[OCC + rsw(m, e + 8)] = slot + 1
        ww(m, e + 10, tbl(m, typ, 0))
        m[e + 2] = tbl(m, typ, 2) & 0xff
        m[e + 3] = tbl(m, typ, 1) & 0xff
        m[e + 21] = 1
        ww(m, e + 6, m[e + 3])
        m[e + 20] = typ & 0xff
        if rl(m, KEY_B4) != (rl(m, KEY_58) + 0x12312378) & 0xffffffff:
            wild = rl(m, a6 - 14) & 0xffffff
            ww(m, wild, 1)
            ww(m, p_o, 1)
            ww(m, p_h, 1)
            ww(m, FRAME, rw(m, FRAME) - 1)
        return slot
    return None

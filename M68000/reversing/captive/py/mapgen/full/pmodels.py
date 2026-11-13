"""Python models of fed_MapGen's creature-group writer and the placement stages that call it.

Transcribed from the code (runtime addresses, module at $1f7b0, A6 = $20376). Builds on the gated stage models in
reversing/captive/py/mapgen/stages/models.py (State, RNG, grid helpers). `K` holds constants a broken-model control
perturbs.
"""
import os
import sys


def _root():
    d = os.environ.get('M68000_ROOT') or os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
        p = os.path.dirname(d)
        if p == d:
            sys.exit('repo root (tools/rdis.py) not found')
        d = p
    return d


R = _root()
sys.path.insert(0, os.path.join(R, 'reversing', 'captive', 'py', 'mapgen', 'stages'))
import models as base  # noqa: E402
from models import code, d5of, rcell, sx, State  # noqa: E402,F401
from common import G0, G1  # noqa: E402

K = base.K


def k(name, default):
    return K.get(name, default)


def cb(addr):
    ram, b = code()
    return ram[addr - b]


def cwu(addr):
    return (cb(addr) << 8) | cb(addr + 1)


def ror16(v, n):
    v &= 0xffff
    n %= 16
    return ((v >> n) | (v << (16 - n))) & 0xffff


def rol16(v, n):
    return ror16(v, 16 - (n % 16))


TYPES = 0x26040          # creature type table, 64 x 8 bytes
SLOTS = {1: 0x2603e, 2: 0x2603c, 4: 0x26038, 5: 0x26033}   # member slot lists by the type's max count
SLOT9 = 0x2602a          # 9-slot list, used for 9 and every other max count


def rng2(S):
    """$245ce: second generator, word 13656(A6) = x * $5e5 + $29; returns ror.w #3."""
    x = (S.w(13656) * 0x5e5 + 0x29) & 0xffff
    S.setw(13656, x)
    return ror16(x, 3)


def type_ok(S, i, d7):
    a = TYPES + 8 * i
    b0 = cb(a)
    if (b0 & 0xf0) != d7 or not (b0 & 0x0f):
        return False
    w6 = cwu(a + 6)
    if (w6 & 0x1f) > S.w(12408):          # minimum base number (unsigned word compare)
        return False
    n = (w6 >> 5) & 7
    if n and not (S.b[13749] >> ((n - 1) & 7)) & 1:   # creature sheet loaded for this base
        return False
    return True


def group_write(S, x, y, d7, start=None):
    """$25e10 (and $25e08 when start is given: start index into 13746, class $80).

    Returns -1 (list full) or 0. Writes one group record at the end of the list 13716(A6)."""
    if start is not None:
        S.setw(13746, start)
        d7 = 0x80
    S.b[13590], S.b[13591] = x & 0xff, y & 0xff
    d0 = rng2(S)
    cur = 13746 if d7 else 13744
    d6 = (S.w(cur) + 1) & 0x3f
    d0 = ror16(d0, 5)
    while True:
        S.setw(cur, d6)
        S.b[13594] = d6
        if type_ok(S, d6, d7):
            break
        d6 = (d6 + 1) & 0x3f
    a4 = TYPES + 8 * d6
    d3 = cb(a4) & 0x0f
    # $25fda: slot list, and a random member count (D0 ror 4) & $1f + 1 capped by the type's maximum
    if d3 == 1:
        a5 = SLOTS[1]
    else:
        a5 = SLOTS.get(d3, SLOT9)
        d4 = (ror16(d0, 4) & 0x1f) + 1
        if d3 > d4:
            d3 = d4
    size = ((d3 + 1) * 8) & 0xffff
    hdr = S.fptr(13716)
    free = (S.f[hdr + 2] << 8) | S.f[hdr + 3]
    if size > free:
        return -1
    free -= size
    S.f[hdr + 2], S.f[hdr + 3] = free >> 8, free & 0xff
    # $25fca: walk the records to the terminator
    p = hdr + 4
    while True:
        ln = (S.f[p + 2] << 8) | S.f[p + 3]
        if ln & 0x8000:
            break
        p += ln
    f = S.f
    f[p], f[p + 1] = S.b[13590], S.b[13591]
    f[p + 2], f[p + 3] = size >> 8, size & 0xff
    f[p + 4] = 0
    attach = bool(S.w(13666))
    if not attach and S.w(13274):
        S.setw(13274, S.w(13274) - 1)
        S.setw(13668, 0x0062)
        S.setw(13670, 0)
        lo = S.w(13274) & 0xff
        S.b[13670] = ((lo >> 3) | (lo << 5)) & 0xff   # ror.b #3
        attach = True
    if attach:
        idx = S.w(13650)
        q = S.fptr(13728) + 4 * idx
        f[q:q + 4] = S.b[13668:13672]
        f[p + 4] = (S.b[13651] | 0x80) & 0xff
        S.setw(13650, idx + 1)
    w6 = cwu(a4 + 6)
    f[p + 5] = S.b[13664] | (0x40 if w6 & 0x100 else 0)
    t = d0 & 0xf
    f[p + 6] = t
    f[p + 7] = ((t >> 1) + cb(a4 + 4)) & 0xff
    # hit-point factor from the base number
    lvl = S.w(12408)
    if lvl & 0x8000:
        fac = 0x7f
    else:
        fac = lvl + 1
        if fac > 0x7f:
            fac = 0x7f
    fac = (fac * 3 - 2 + S.w(54)) & 0xffff
    hp_base = cwu(a4 + 2)
    q = p + 8
    for m in range(d3):
        f[q] = S.b[13594]
        f[q + 1] = cb(a5 + m)
        d0 = rol16(d0, 3)
        d4 = hp_base * fac                         # mulu
        d4 += ((d4 & 0xffff) * d0) >> 16
        d2 = lvl
        if d2 > 0x10:
            d2 >>= 1
        d2 >>= 1
        d2 = (d2 * d0) >> 16
        d4 += d2
        if d4 > k('hp_cap', 0xffdc):
            d4 -= d2 >> 1
            if d4 > 0xffdc:
                d4 = 0xffdc
        f[q + 2], f[q + 3] = (d4 >> 8) & 0xff, d4 & 0xff
        d0 = ror16(d0, 5)
        v = (d0 & 3) + cb(a4 + 1)
        v &= 0xff
        if v > 0xfd:
            v = 0xfd
        f[q + 4] = v
        d0 = ror16(d0, 3)
        f[q + 5] = ((d0 & 3) + cb(a4 + 5) + k('skill_add', 0)) & 0xff
        f[q + 6] = f[q + 7] = 0
        q += 8
    f[q:q + 4] = bytes.fromhex('88828881')
    S.setw(13616, S.w(13616) + 1)
    return 0


D88_FEATS = (0x07, 0x0f, 0x0c, 0x1f, 0x33, 0x09, 0x11, 0x14)


def s_25d88(S):
    """$25d88: 300 random cells; a cell whose feature is one of D88_FEATS (class 0) or $23 (class 4) and whose G0 is
    above $a gets a group (not hostile, no object), and its feature byte gets bit 7. Stops when the list is full."""
    for _ in range(k('d88_tries', 0x12b) + 1):
        x, y, _ = rcell(S)
        d5 = d5of(x, y)
        d4 = S.feat(d5)
        if not d4:
            continue
        if S.g0(d5) <= 0xa:
            continue
        if d4 in D88_FEATS:
            d7 = 0
        elif d4 == 0x23:
            d7 = 0x40
        else:
            continue
        S.setw(54, 0)
        S.b[13664] &= ~0x10 & 0xff
        S.setw(13666, 0)
        if group_write(S, x, y, d7) < 0:
            return
        S.b[G1 + d5 + 1] |= 0x80


def fw(S, o):
    return (S.f[o] << 8) | S.f[o + 1]


def setfw(S, o, v):
    S.f[o], S.f[o + 1] = (v >> 8) & 0xff, v & 0xff


def obj_append(S, x, y, d0b, d3w, keep=False):
    """$26682 (keep=False clears the flag word 13674 first) / $26686: add the 4-byte item
    (type d0b, word d3w, flags) to the object list 13724(A6) at cell (x, y). A second item on a cell is inserted at
    the front of that cell's record, moving the rest of the list up by 4 (to 4 bytes past the list's $800)."""
    if not keep:
        S.setw(13674, 0)
    S.b[13590], S.b[13591] = x & 0xff, y & 0xff
    S.b[13592] = d0b & 0xff
    S.b[13594] = d3w & 0xff
    S.b[13593] = (d3w >> 8) & 0xff
    hdr = S.fptr(13724)
    if fw(S, hdr + 2) <= 8:
        return
    r = rng2(S)
    d0 = 0 if S.w(13674) else r
    S.b[13595] = (ror16(d0, 5) & 3) | 0x80
    pos = S.w(13590)
    p = hdr + 4
    while True:
        if fw(S, p) == pos:
            end = hdr + 0x800
            S.f[p + 4:end + 4] = S.f[p:end]
            setfw(S, p + 2, fw(S, p + 2) + 4)
            S.f[p + 4:p + 8] = S.b[13592:13596]
            setfw(S, hdr + 2, fw(S, hdr + 2) - 4)
            return
        ln = fw(S, p + 2)
        if ln & 0x8000:
            break
        p += ln
    setfw(S, p, pos)
    setfw(S, p + 2, 8)
    S.f[p + 4:p + 8] = S.b[13592:13596]
    S.f[p + 8:p + 12] = bytes.fromhex('88828881')
    setfw(S, hdr + 2, fw(S, hdr + 2) - 8)


def rock_side(S, x, y):
    """$25632: the first of N (D3 0), S (2), W (1), E (3) neighbours that is in the grid with G1 word 0 and G0 0.
    Returns (x, y, d3) or None."""
    for dx, dy, d3 in ((0, -1, 0), (0, 1, 2), (-1, 0, 1), (1, 0, 3)):
        nx, ny = (x + dx) & 0xffff, (y + dy) & 0xffff
        if nx > 0x3f or ny > 0x1f:
            continue
        d5 = d5of(nx, ny)
        if S.g1w(d5) == 0 and S.g0(d5) == 0:
            return nx, ny, d3
    return None


def obj_desc_26722(S):
    """$26722: 13668 = min(hi(seed * (min(D0, 22) + 1)) + $36, $4c); 13670 = (seed & $3f) | (seed & $e0) << 8."""
    d0 = min(S.w(12408), 0x16) + 1
    seed = S.w(12404)
    t = (((seed * d0) >> 16) + 0x36) & 0xffff
    if t > 0x4c:
        t = 0x4c
    S.setw(13668, t)
    S.setw(13670, (seed & 0x3f) | (((seed & 0xe0) << 8) & 0xffff))


def wall_object(S, x, y, d3):
    """Feature $22 with parameter 2 * d3 (the side it faces) and G0 $ffc3 on rock cell (x, y)."""
    d5 = d5of(x, y)
    S.b[G1 + d5] = (2 * d3) & 0xff
    S.b[G1 + d5 + 1] = 0x22
    S.setg0(d5, 0xffc3)


def pick_deadend(S):
    """$2567e as stages/models.pick_deadend, also returning the slot offset D0."""
    d6 = 0xff
    d0 = S.rng() & 0x1fe
    while True:
        while S.w(12440 + d0) == 0:
            d0 = (d0 + 2) & 0x1fe
            d6 -= 1
            if d6 < 0:
                return None
        x, y = S.b[12440 + d0], S.b[12440 + d0 + 1]
        if S.feat(d5of(x, y)) == 0x7f:
            return x, y, d0
        S.setw(12440 + d0, 0)


def guard_25454(S, x0, y0, slot):
    """$25454: a dead end whose arrow chain runs through two plain corridor cells P1, P2 gets a hostile group;
    a rock cell beside P2 gets wall object $22 with an item from $26722; (wall cell, P1) goes to list 13732."""
    S.setw(13212, slot)
    S.setw(13214, x0)
    S.setw(13216, y0)
    p1 = base.step_flow(S, x0, y0)
    n, _ = base.nblocked(S, *p1)
    if n != 2 or not base.ok_2664e(S, *p1):
        return
    p2 = base.step_flow(S, *p1)
    n, _ = base.nblocked(S, *p2)
    if n < 1 or not base.ok_2664e(S, *p2):
        return
    w = rock_side(S, *p2)
    if w is None:
        return
    wx, wy, d3 = w
    wall_object(S, wx, wy, d3)
    S.setw(13218, wx)
    S.setw(13238, wy)
    obj_desc_26722(S)
    S.b[13674] = 0xff                     # st 13674(A6)
    obj_append(S, wx, wy, S.b[13669], S.w(13670), keep=True)
    S.setw(54, k('guard_hpadd', 2))
    S.b[13664] |= 0x10
    S.setw(13666, 0)
    if group_write(S, x0, y0, 0) < 0:
        return
    d5 = d5of(x0, y0)
    S.b[G1 + d5 + 1] |= 0x80
    p1 = base.step_flow(S, x0, y0)
    q = S.fptr(13732) + 4 * S.w(13266)
    S.f[q:q + 4] = bytes([S.b[13219], S.b[13239], p1[0] & 0xff, p1[1] & 0xff])
    S.setg1w(d5of(*p1), 0)
    S.setw(13266, S.w(13266) + 1)


def s_2543a(S):
    """$2543a: up to 101 guarded dead ends ($25454), until the dead-end list is exhausted or 32 are listed."""
    for _ in range(101):
        d = pick_deadend(S)
        if d is None:
            return
        guard_25454(S, *d)
        if S.w(13266) > 0x1f:
            return


def plain_door(S, x, y, d0, count=True):
    """$242b0 (count) / $242b4: G1 word $0015, parameter byte = D0."""
    if count:
        S.setw(13618, S.w(13618) + 1)
    d5 = d5of(x, y)
    S.setg1w(d5, 0x15)
    S.b[G1 + d5] = d0 & 0xff


def coded_door(S, x, y, d0, d5code, check=True):
    """$242d6 (check: only while 13628 != 0) / $242d0: a door plus a coded-door list entry; code hi(D5 * 24)."""
    d3 = S.w(13628)
    if check and d3 == 0:
        return
    plain_door(S, x, y, d0, count=False)
    S.setw(13628, d3 - 1)
    q = S.fptr(13708) + 4 * ((7 - d3) & 0xffff)
    S.f[q], S.f[q + 1] = x & 0xff, y & 0xff
    code = (((d5code & 0xffff) * 0x18) >> 16) << 4
    S.f[q + 2], S.f[q + 3] = (code >> 8) & 0xff, code & 0xff


FACE_SIDE = 0x24490      # open-side mask of the structure's wall face, by the rock side found by $25632


def structure_24306(S, x, y, d0):
    """$24306: kind-3 door. Returns True when built (Z = 1), False on any failed condition (D0 = -1)."""
    if S.w(13640) > 0x63:
        return False
    hdr = S.fptr(13716)
    if fw(S, hdr + 2) <= 0x14 or S.w(13638) > 7:
        return False
    S.setw(13218, x)
    S.setw(13238, y)
    S.setw(13224, d0)
    s1 = base.step_flow(S, x, y)
    S.setw(13226, s1[0])
    S.setw(13246, s1[1])
    if s1[1] < 0 or base.blocked(S, *s1)[0] or not base.ok_2664e(S, *s1):
        return False
    w = rock_side(S, *s1)
    if w is None:
        s2 = base.step_flow(S, *s1)
        S.setw(13226, s2[0])
        S.setw(13246, s2[1])
        if s2[1] < 0 or base.blocked(S, *s2)[0] or not base.ok_2664e(S, *s2):
            return False
        w = rock_side(S, *s2)
        if w is None:
            return False
    wx, wy, d3 = w
    S.setw(13220, wx)
    S.setw(13240, wy)
    S.setw(13244, d3)
    d7 = (S.w(12404) & 0xf) + k('struct_walk', 3)
    c = base.step_flow(S, x, y)
    if c[1] < 0:
        return False
    while True:
        c = base.step_flow(S, *c)
        if c[1] < 0:
            return False
        if base.blocked(S, *c)[0]:
            continue
        d7 -= 1
        if d7 < 0:
            break
    if not base.ok_2664e(S, *c):
        return False
    gx, gy = c
    S.setw(13222, gx)
    S.setw(13242, gy)
    d5 = d5of(x, y)
    S.b[G1 + d5] = S.b[13225]
    S.b[G1 + d5 + 1] = 0x15
    d5w = d5of(wx, wy)
    S.setg0(d5w, 0xffc3)
    n = S.w(13638)
    S.setw(13668, 0x0065)
    S.setw(13670, 0)
    S.b[13671] = n & 0xff
    # $26398: wall face, picture 1, tagged with the structure number
    S.b[G1 + d5w] = cb(FACE_SIDE + d3)
    S.b[G1 + d5w + 1] = 0x2c
    q = S.fptr(13704) + 4 * S.w(13640)
    S.f[q:q + 4] = bytes([wx & 0xff, wy & 0xff, 1, n & 0xff])
    S.setw(13640, S.w(13640) + 1)
    S.setw(54, 0)
    S.b[13664] &= 0xef
    S.b[13666] = 0xff
    group_write(S, gx, gy, None, start=k('struct_start', 5))
    S.b[G1 + d5of(gx, gy) + 1] |= 0x80
    S.b[G1 + d5of(S.sw(13226), S.sw(13246)) + 1] = 0x0f
    q = S.fptr(13740) + 4 * n
    S.f[q:q + 4] = bytes([S.b[13221], S.b[13241], S.b[13219], S.b[13239]])
    S.setw(13638, n + 1)
    return True


def place_door(S, x, y, d0, d5code):
    """$24298: dispatch on the door kind's low 3 bits. Returns Z (True = a door was handled)."""
    kd = d0 & 7
    if kd == 2:
        coded_door(S, x, y, d0, d5code)
        return True
    if kd == 3:
        return structure_24306(S, x, y, d0)
    if kd == 4:
        coded_door(S, x, y, d0, d5code, check=False)
        return True
    plain_door(S, x, y, d0)
    return True


DOOR_KINDS = 0x24228


def s_2419a(S):
    """$2419a: doors. Pass 1: a plain door on each cell of the 25-word list 13712(A6). Pass 2: 300 random starts,
    each walking up to 17 arrow steps to the first corridor cell (feature 7) walled on both sides with no door beside
    it; the kind comes from the byte table $24228 (+8 when walled N and S)."""
    lst = S.fptr(13712)
    for i in range(25):
        q = lst + 2 * i
        if S.f[q] & 0x80:
            continue
        x, y = S.f[q], S.f[q + 1]
        d5 = d5of(x, y)
        d4 = S.b[G1 + d5 + 3]
        d0 = 1 if 0x19 < d4 <= 0x1d else 9
        place_door(S, x, y, d0, d5)
    for _ in range(0x12c):
        d0 = ror16(S.rng(), 1)
        x, y = d0 & 0x3f, ror16(d0, 6) & 0x1f
        for _ in range(17):
            m = base.mask5(S, x, y)
            if m & 4:
                break
            if m == 0xa or m == 0x11:
                d4 = 8 if m == 0x11 else 0
                d5 = d5of(x, y)
                ft = S.b[G1 + d5 + 1]
                if ft < 7 or ft >= 0x87:
                    break
                if ft == 7:
                    a1 = G1 + d5
                    if 0x15 in (S.b[a1 + 3], S.b[a1 - 1], S.b[a1 - 127], S.b[a1 + 129]):
                        break
                    r = S.rng()
                    kd = (cb(DOOR_KINDS + (ror16(r, 5) & 7)) + d4) & 0xffff
                    if S.w(12408) == 0:
                        if kd & 7:
                            kd = (kd & 0xf8) | 5
                        plain_door(S, x, y, kd)
                        break
                    if place_door(S, x, y, kd, r):
                        break
                    # a failed kind 3 leaves D1, D2 at the door cell ($24494) or untouched ($2449e)
            elif m < 0x11:
                break
            x, y = base.step_flow(S, x, y)
            if y < 0:
                break


MODELS = {0x25d88: s_25d88, 0x2543a: s_2543a, 0x2419a: s_2419a}

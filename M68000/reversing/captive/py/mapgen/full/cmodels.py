"""Python models of the fed_MapGen stages left unported after the placement pass, plus the encoder $23936.

Transcribed from the code (runtime addresses, module at $1f7b0, A6 = $20376). Builds on the gated stage models in
reversing/captive/py/mapgen/stages/models.py and this directory's pmodels.py (the group writer and the placement stages).
Each model takes a State (module block + federation block $1bd3e..$1d9e8) as it stood before the stage.
`K` holds constants a broken-model control perturbs.

  $25722  mg_PlaceLocks       locked door + key + guarded prize behind it (calls $2584c, $25a3e, $25a00)
  $25c1e  mg_PlaceTerminals   features $12 / $13 on dead ends, class-$80 carriers of item $64 ($25c74, $2695e)
  $2676c  mg_PlaceVault       D2 = 1: coded door before the dead end farthest from the entrance, hostile group
  $25414  mg_PlaceSwitchDoors $25526: dead end, a corridor cell 8..15 arrows on gets $0f, wall object $22
  $26478 / $264ac / $264c8    wall-object items $19 (up to 21), $5f (one), $61 (up to 6) via $264f4
  $268f8  mg_PlaceBase0Note   D0 = 0: items $1b and $66 at (30, 1)
  $23936  mg_Encode           tile layer and plane 2
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pmodels as P  # noqa: E402  (puts reversing/.../stages on the path)
import models as base  # noqa: E402
from models import d5of, rcell, State  # noqa: E402,F401
from common import G0, G1, G2  # noqa: E402

K = base.K
cb, cwu, ror16, rol16 = P.cb, P.cwu, P.ror16, P.rol16


def k(name, default):
    return K.get(name, default)


def cw(addr):
    return base.cw(addr)


def is_lift_step(S, x, y):
    return S.g2(d5of(x, y)) in (4, 5)


# ------------------------------------------------------------------ $25722 locks

LOCK_LIMIT = 0x2570c      # word table by min(D0, 9): bytes of lock list allowed (10 per lock)
KEY_MASK = 0x25a36        # word masks by key kind: 1, 7, $ff, $ffff
LOCK_KIND = 0x25bfe       # 32 bytes: door kind (bits 0-1, +1) and key kind (bits 2-3)
SITE_OK = (6, 0x37, 4, 5, 0x35, 0x36, 9, 0x0e, 0x7f)


def count_23(S, x, y):
    """$25ba0: rock neighbours (G0 = 0) carrying feature $23 (room pass-2 paint), W E N S."""
    n = 0
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        d0, z = base.blocked(S, x + dx, y + dy)
        if not z and S.feat(d5of(x + dx, y + dy)) == 0x23:
            n += 1
    return n


def site_25a3e(S, x, y):
    """$25a3e: from a dead end walk back 1..16 arrows to a plain corridor cell (the door), then 1..8 more without a
    lift to an open cell with a blocked side (P), then straight on to the first rock cell (W, the wall item).
    Returns True (Z = 0) when every condition holds; leaves 13218.. set as the code does."""
    S.setw(13218, x)
    S.setw(13238, y)
    d6 = S.rng() & 0xf
    for _ in range(d6 + 1):
        x, y = base.step_flow(S, x, y)
    n, z = base.nblocked(S, x, y)
    if z:
        return False
    if S.feat(d5of(x, y)) != 7:
        return False
    d4 = count_23(S, x, y)
    if d4 == 0:
        d7 = 7
        d6 = base.mask5(S, x, y)
        if d6 & 4:
            return False
        if d6 == 0xa:
            d4 = 6
            S.setw(13600, 6)
        elif d6 == 0x11:
            d4 = 14
            S.setw(13600, 14)
        else:
            d4, d7 = 14, 6
    elif d4 == 1:
        d7 = 6
    else:
        d7 = 4
    dd = min(S.w(12408), 31) + 1
    v = cb(LOCK_KIND + (((S.w(12404) * dd) >> 16) & 0x1f))
    d0 = ((v & 3) - 1) & 0xffff
    d4 = (v >> 2) & 3
    if not (d7 >> (d0 & 31)) & 1:
        return False
    S.setw(13596, d0)
    S.setw(13598, d4)
    S.setw(13220, x)
    S.setw(13240, y)
    d6 = S.rng() & 7
    for _ in range(d6 + 1):
        lift = is_lift_step(S, x, y)
        x, y = base.step_flow(S, x, y)
        if lift:
            return False
    n, _ = base.nblocked(S, x, y)
    if n == 0:
        return False
    S.setw(13222, x)
    S.setw(13242, y)
    d = S.g2(d5of(x, y))
    if d in (4, 5):
        base.step_flow(S, x, y)
        return False
    x, y = base.step_flow(S, x, y)
    d0 = (2 * d) & 0xffff
    d7 = (S.w(12404) >> 8) & 3
    if d7 != 2:
        d0 = (d0 + 2 * d7) & k('lock_dirmask', 3)
    S.setw(13260, d0)
    while True:
        if (x & 0xffff) > 0x3f or (y & 0xffff) > 0x1f:
            return False
        g = S.g0(d5of(x, y))
        if g & 0x8000:
            return False
        if g == 0:
            break
        d7 = (d7 - 1) & 0xffff
        if d7 == 0xffff:
            return False
        S.setw(13222, x)
        S.setw(13242, y)
        x = base.sx(x + cw(0x25404 + d0))
        y = base.sx(y + cw(0x2540c + d0))
    if S.g1w(d5of(x, y)) != 0:
        return False
    S.setw(13224, x)
    S.setw(13244, y)
    px, py = S.sw(13222), S.sw(13242)
    if base.ok_2664e(S, px, py):
        return True
    return S.feat(d5of(px, py)) in SITE_OK


def mask_25a00(S):
    """$25a00: reduce the lock code 13602 to the key kind's mask, rotating right 3 until a masked bit is set."""
    d0 = S.w(13598) & 3
    if d0 == 0:
        S.b[13603] = 0xff
    m = cwu(KEY_MASK + 2 * d0)
    while True:
        v = S.w(13602) & m
        if v:
            S.setw(13602, v)
            return
        S.setw(13602, ror16(S.w(13602), 3))


def lock_2584c(S, x, y, slot):
    S.setw(13212, slot)
    if not site_25a3e(S, x, y):
        return
    d0 = S.w(12404) or 0x4285
    S.setw(13602, rol16(d0, 7))
    mask_25a00(S)
    dx, dy = S.w(13220), S.w(13240)
    d7 = (S.g0(d5of(dx, dy)) + k('key_slack', 1)) & 0xffff
    # the key: a random plain cell dug no later than the door (2 <= G0 <= G0(door)); 11 tries
    for _ in range(11):
        if S.w(13598) <= 1:
            break
        while True:
            kx, ky, _ = rcell(S)
            d5 = d5of(kx, ky)
            if base.ok_2664e(S, kx, ky):
                break
            if S.sw(G0 + d5) >= 1:
                kx = None
                break
        if kx is None:
            continue
        g = S.g0(d5)
        if g & 0x8000 or g <= 1 or g >= d7:
            continue
        S.setfeat(d5, 0x29 if S.feat(d5) == 0x14 else 0x28)
        P.obj_append(S, kx, ky, 0x5c if S.w(13598) == 2 else 0x5d, S.w(13602))
        break
    else:
        if k('keep_keyless', False):
            pass
        else:
            return          # $258b8: no key cell in 11 tries abandons the lock (dead end stays listed)
    S.setw(12440 + slot, 0)
    ex, ey = S.w(13218), S.w(13238)
    d5 = d5of(ex, ey)
    S.setfeat(d5, 0x34 if S.feat(d5) == 0x33 else 0x0d)
    P.obj_append(S, ex, ey, 25, (S.w(12404) & 0x3ff) + 0x80)
    S.setw(54, 0)
    S.b[13664] &= 0xef
    S.setw(13666, 0)
    if P.group_write(S, ex, ey, 0) >= 0:
        S.b[G1 + d5 + 1] |= 0x80
    d5 = d5of(dx, dy)
    kd = S.w(13596)
    if kd == 0:
        S.b[G1 + d5] = S.b[13601]
        S.setfeat(d5, 0x15)
    elif kd == 1:
        S.setfeat(d5, 0)
    else:
        S.setfeat(d5, 0x27)
    px, py = S.sw(13222), S.sw(13242)
    if base.ok_2664e(S, px, py) or S.feat(d5of(px, py)) == 0x7f:
        S.setfeat(d5of(px, py), 0x0c)
    wx, wy = S.w(13224), S.w(13244)
    d5 = d5of(wx, wy)
    S.setfeat(d5, 0x22)
    S.b[G1 + d5] = S.b[13261]
    S.setg0(d5, 0xffc3)
    q = S.fptr(13720) + S.w(13626)
    b = S.b[13599] | ((S.w(13596) << 2) & 0xc)
    if S.w(12404) > 0x7000:
        b |= 0x10
    S.f[q:q + 10] = bytes([S.b[13225], S.b[13245], S.b[13602], S.b[13603], 0, 0, S.b[13221], S.b[13241],
                           b & 0xff, 0x20])
    S.setw(13626, S.w(13626) + 10)
    S.setw(13270, S.w(13270) + 1)


def s_25722(S):
    S.setw(13270, 0)
    d7 = S.w(12408)
    if d7 == 0:
        return
    S.setw(13604, cwu(LOCK_LIMIT + 2 * min(d7, 9)))
    for _ in range(0x1e1):
        d = P.pick_deadend(S)
        if d is None:
            return
        lock_2584c(S, *d)
        if S.w(13604) <= S.w(13626):
            return


# ------------------------------------------------------------------ $25c1e terminals

def note_2695e(S, x, y):
    """$2695e: base 0 only: feature $0d and item $66 (MESSAGE FROM RATT) with word 2 at (x, y)."""
    if S.w(12408):
        return
    S.setfeat(d5of(x, y), 0x0d)
    P.obj_append(S, x, y, 0x66, 2)


def term_25c74(S, d0, d4, lst):
    d7 = d0
    guard = 0
    while True:
        d = P.pick_deadend(S)
        if d is None:
            return
        x, y, _ = d
        d5 = d5of(x, y)
        px, py = base.step_flow(S, x, y)
        if base.ok_2664e(S, px, py):
            S.setfeat(d5of(px, py), 0x0f)
            if S.w(13672):
                S.setw(13668, 0x0064)
                S.setw(13670, 0)
                S.b[13671] = S.b[13751]
                S.setw(54, 0)
                S.b[13664] &= 0xef
                S.b[13666] = 0xff
                P.group_write(S, px, py, None, start=k('term_start', 7))
                note_2695e(S, px, py)
                S.b[G1 + d5of(px, py) + 1] |= 0x80
                S.setw(13750, S.w(13750) + 1)
        elif S.w(13672):
            guard += 1
            if guard > 100000:
                raise RuntimeError('$25c74 retry loop')
            continue
        S.setfeat(d5, d4)
        S.setg0(d5, 0xfffb)
        S.f[lst], S.f[lst + 1] = x & 0xff, y & 0xff
        lst += 2
        d7 = (d7 - 1) & 0xffff
        if d7 == 0xffff:
            return


def s_25c1e(S):
    d0 = ((S.rng() * 7) >> 16) + 1
    if d0 <= 4:
        d0 = 4
    S.setw(13672, 0)
    term_25c74(S, d0, 0x12, S.fptr(13696))
    d0 = S.rng() & 1
    S.b[13672] = 0xff
    S.setw(13750, 0)
    term_25c74(S, d0, 0x13, S.fptr(13700))
    a = S.fptr(13700)
    if not S.f[a + 2] & 0x80:
        S.f[a:a + 4] = S.f[a + 2:a + 4] + S.f[a:a + 2]


# ------------------------------------------------------------------ $2676c (D2 = 1)

def walled_2683a(S, x, y):
    m = base.mask5(S, x, y)
    return not (m & 4) and m in (0xa, 0x11)


def s_2676c(S):
    S.setw(13608, 0)
    for i in range(256):
        o = 12440 + 2 * i
        if not S.w(o):
            continue
        x, y = S.b[o], S.b[o + 1]
        S.setw(13218, x)
        S.setw(13238, y)
        c = base.step_flow(S, x, y)
        if not walled_2683a(S, *c):
            continue
        S.setw(13222, 0)
        while True:
            c = base.step_flow(S, *c)
            if (c[1] & 0xffff) == 0xffff:
                break
            S.setw(13222, S.w(13222) + 1)
            if S.w(13222) & 0x8000:
                break
        if S.w(13608) > S.w(13222):
            continue
        S.setw(13608, S.w(13222))
        S.setw(13610, S.w(13218))
        S.setw(13612, S.w(13238))
    if not S.w(13608):
        return
    x, y = S.w(13610), S.w(13612)
    dx, dy = base.step_flow(S, x, y)
    m = base.mask5(S, dx, dy)
    d4 = 8 if (not m & 4 and m != 0xa and m == 0x11) else 0
    P.place_door(S, dx, dy, k('vault_kind', 4) + d4, S.w(12404))
    S.setw(54, 0)
    S.b[13664] |= 0x10
    S.setw(13666, 0)
    P.group_write(S, x, y, None, start=30)
    d5 = d5of(x, y)
    S.b[G1 + d5 + 1] |= 0x80
    S.setg0(d5, 0xffea)


# ------------------------------------------------------------------ $25414

def sw_25526(S, x, y):
    S.setw(13218, x)
    S.setw(13238, y)
    d7 = (S.w(12404) & 7) + k('sw_walk', 8)
    pc = 'walk'
    while True:
        if pc == 'walk':
            x, y = base.step_flow(S, x, y)
            if not base.ok_2664e(S, x, y):
                if S.feat(d5of(x, y)) in (6, 0x37, 4, 5, 0x35, 0x36):
                    d7 += 1
                else:
                    return
            d7 = (d7 - 1) & 0xffff
            if d7 != 0xffff:
                continue
            pc = 'a'
        S.setw(13220, x)
        S.setw(13240, y)
        x, y = base.step_flow(S, x, y)
        gw = S.g1w(d5of(x, y))
        if gw in (0x1f, 0x33, 0x11):
            d7 = (d7 + 1) & 0xffff
            pc = 'walk'
            continue
        if gw != 7:
            return
        break
    S.setw(13222, x)
    S.setw(13242, y)
    w = P.rock_side(S, S.w(13218), S.w(13238))
    if w is None:
        return
    wx, wy, d3 = w
    S.setw(13218, wx)
    S.setw(13238, wy)
    P.wall_object(S, wx, wy, d3)
    S.setg1w(d5of(S.w(13222), S.w(13242)), 0x0f)
    S.setg1w(d5of(S.w(13220), S.w(13240)), 0x25)
    q = S.fptr(13736) + 6 * S.w(13268)
    S.f[q:q + 6] = bytes([S.b[13221], S.b[13241], S.b[13223], S.b[13243], S.b[13219], S.b[13239]])
    S.setw(13268, S.w(13268) + 1)


def s_25414(S):
    if not S.w(12408):
        return
    for _ in range(0x65):
        d = P.pick_deadend(S)
        if d is None:
            return
        sw_25526(S, d[0], d[1])
        if S.w(13268) > 0xf:
            return


# ------------------------------------------------------------------ wall-object items

def wall_item_264f4(S):
    """$264f4: a random plain/room cell ($2663e) gets the item 13668 on a rock neighbour as a new $22 wall object
    (parameter 2 * side, G0 unchanged); a cell already holding a $22 wall object gets the item itself.
    True (Z = 1) when placed."""
    x, y, z = base.pick_2663e(S)
    if not z:
        if S.feat(d5of(x, y)) != 0x22:
            return False
    else:
        w = P.rock_side(S, x, y)
        if w is None:
            return False
        x, y, d3 = w
        d5 = d5of(x, y)
        S.b[G1 + d5] = (2 * d3) & 0xff
        S.b[G1 + d5 + 1] = 0x22
    S.b[13674] = 0xff
    P.obj_append(S, x, y, S.b[13669], S.w(13670), keep=True)
    return True


def s_26478(S):
    d4 = 0
    for _ in range(0x8d):
        S.setw(13670, (S.w(12404) & 0xff) + 0x40)
        S.setw(13668, 0x19)
        if wall_item_264f4(S):
            d4 += 1
            if d4 > k('n19', 0x14):
                break
    S.setw(13614, d4)


def s_264ac(S):
    if not S.w(12408):
        return
    for _ in range(101):
        S.setw(13668, k('item5f', 0x5f))
        S.setw(13670, 0)
        if wall_item_264f4(S):
            return


def s_264c8(S):
    if not S.w(12408):
        return
    d4 = 0
    for _ in range(21):
        S.setw(13668, k('item61', 0x61))
        S.setw(13670, 0)
        if wall_item_264f4(S):
            d4 += 1
            if d4 > 5:
                return


def s_268f8(S):
    if S.w(12408):
        return
    x, y = 0x1e, 1
    d5 = d5of(x, y)
    S.setfeat(d5, 0x34 if S.feat(d5) == 0x33 else 0x0d)
    S.setw(13674, 0)
    saved = S.w(13656)
    P.obj_append(S, x, y, 27, 0)
    S.setw(13656, saved)
    P.obj_append(S, x, y, 0x66, k('note_word', 0))


# ------------------------------------------------------------------ encoder $23936

TILE = {0x16: 27, 0x34: 97, 0x33: 96, 0x1f: 32, 0x11: 32, 0x7f: 32, 0x0f: 32, 0x21: 42, 0x14: 30, 0x23: 38,
        0x27: 38, 0x12: 44, 0x13: 46, 0x0e: 26, 0x00: 0, 0x10: 32, 0x0d: 33, 0x32: 62, 0x30: 60, 0x31: 61,
        0x0c: 32, 0x28: 33, 0x29: 31, 0x2a: 35, 0x2b: 55, 0x18: 0, 0x24: 34, 0x26: 28, 0x25: 54, 0x1a: 54,
        0x1b: 54, 0x1c: 54, 0x1d: 54, 0x2e: 51, 0x2f: 48, 0x04: 52, 0x35: 52, 0x06: 50, 0x37: 50, 0x05: 49,
        0x36: 49, 0x08: 38}


def tile_2397e(g0, feat, param):
    """$2397e: (tile, 13594 word)."""
    hi = 0
    if feat == 0x20:
        return 0xa0, 0
    if feat & 0x80:
        hi = 0x80
        feat &= 0x7f
    if feat == 0x1e:
        t = 0x18
    elif feat == 0x09:
        t = 0x28
    elif feat == 0x22:
        t = 0x10 + ((param >> 1) & 3)
    elif g0 == 0xffff:
        t = 0
    elif feat == 0x2c:
        t = param
    elif g0 in (0, 0xfffd):
        t = 0
    elif feat == 0x15:
        t = (param + 0x40) & 0xff
    else:
        t = TILE.get(feat, k('tile_default', 32))
    return (t | hi) & 0xff, hi << 8


def encode(S, outa, outb):
    """$23936 into bytearrays outa (tiles) and outb (plane 2), each 2048; leaves 13594 as the code does."""
    last = None
    for i in range(2048):
        d5 = 2 * i
        g0 = S.g0(d5)
        t, last = tile_2397e(g0, S.b[G1 + d5 + 1], S.b[G1 + d5])
        outa[i] = t
        b = S.b[G2 + d5]
        if g0 not in (0, 0xffff):
            b = (b | (b << 3)) & 0xff
        outb[i] = b
    S.setw(13594, last)


MODELS = {0x25722: s_25722, 0x25c1e: s_25c1e, 0x2676c: s_2676c, 0x25414: s_25414, 0x26478: s_26478,
          0x264ac: s_264ac, 0x264c8: s_264c8, 0x268f8: s_268f8}

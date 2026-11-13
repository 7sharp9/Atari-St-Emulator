"""Python models of fed_MapGen's post-dig stages, transcribed from the code (addresses are runtime, module at $1f7b0).

Each model takes S (a State over the module's variable block, A6 = $20376, and federation's table block) as it stood
before the stage and changes it in place. gate.py compares the result with the emulator's state after the stage.
Every model keeps the code's quirks (byte-offset drift, reads past a list's end), because the gate compares bytes.
`K` holds the constants a broken-model control perturbs.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FED, G0, G1, G2, R  # noqa: E402

K = {}


def k(name, default):
    return K.get(name, default)


_CODE = None


def code():
    """The module's code bytes ($1f7b0..) from mg_ret.snap, for tables read with a data-dependent index."""
    global _CODE
    if _CODE is None:
        sys.path.insert(0, os.path.join(R, 'tools'))
        from gfxview import load_ram
        ram, base = load_ram(os.path.join(R, 'scratchpad', 'captive', 'mg_ret.snap'))
        _CODE = (ram, base)
    return _CODE


def cw(addr):
    ram, base = code()
    v = (ram[addr - base] << 8) | ram[addr - base + 1]
    return v - 0x10000 if v & 0x8000 else v


def sx(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


MA6 = 0x20376


class Mem:
    """The module block, with reads outside it falling back to mg_ret.snap's RAM (the module's own code lies on
    both sides of the variable block). A write outside it raises: the gate then reports the case."""

    def __init__(self, b):
        self.a = b

    def __len__(self):
        return len(self.a)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return bytes(self[j] for j in range(*i.indices(1 << 24))) if i.stop > len(self.a) or (i.start or 0) < 0 \
                else self.a[i]
        if 0 <= i < len(self.a):
            return self.a[i]
        ram, base = code()
        return ram[MA6 + i - base]

    def __setitem__(self, i, v):
        if not 0 <= i < len(self.a):
            raise IndexError(f'write outside the module block at A6{i:+d}')
        self.a[i] = v


class State:
    def __init__(self, mod, fed):
        self.b = Mem(mod)
        self.f = fed
        self.c = {}   # scratch registers a stage leaves behind

    # module variables
    def w(self, o):
        return (self.b[o] << 8) | self.b[o + 1]

    def sw(self, o):
        return sx(self.w(o))

    def setw(self, o, v):
        v &= 0xffff
        self.b[o], self.b[o + 1] = v >> 8, v & 0xff

    def l(self, o):
        return int.from_bytes(self.b[o:o + 4], 'big')

    def inc(self, o, d=1):
        self.setw(o, self.w(o) + d)

    # federation memory through an output pointer
    def fptr(self, slot):
        return self.l(slot) - FED

    # RNG $23b96: seed 12404 = seed * $5e5 + $29; returns (ror.w #4) ^ $800
    def rng(self):
        x = (self.w(12404) * 0x5e5 + 0x29) & 0xffff
        self.setw(12404, x)
        return (((x >> 4) | (x << 12)) & 0xffff) ^ 0x800

    # grids by D5 = 2 * (64 y + x), a sign-extended word offset like 0(A0,D5.w)
    def g0(self, d5):
        return self.w(G0 + d5)

    def setg0(self, d5, v):
        self.setw(G0 + d5, v)

    def feat(self, d5):
        return self.b[G1 + d5 + 1]

    def setfeat(self, d5, v):
        self.b[G1 + d5 + 1] = v & 0xff

    def g1w(self, d5):
        return self.w(G1 + d5)

    def setg1w(self, d5, v):
        self.setw(G1 + d5, v)

    def g2(self, d5):
        return self.b[G2 + d5]


def d5of(x, y):
    """$24d7e: D5 = ((y << 6) + x) * 2 as a signed word."""
    return sx((((y << 6) + x) * 2))


def blocked(S, x, y):
    """$24efc: (D0, Z). D0 = 1 unless open; Z = 0 only for rock (G0 = 0). Open: G0 in 1..$ffce."""
    if not (0 <= x <= 0x3f and 0 <= y <= 0x1f):   # unsigned compares on the words
        return 1, True
    v = S.g0(d5of(x, y))
    if v == 0:
        return 1, False
    if v > 0xffce:
        return 1, True
    return 0, True


def wrap(v):
    return sx(v)


def nblocked(S, x, y):
    """$24e7e: count of blocked 4-neighbours (W, E, N, S) of an open cell; (count, Z). Centre not open: (0, Z=1)."""
    d0, _ = blocked(S, x, y)
    if d0:
        return 0, True
    n = 0
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        n += blocked(S, x + dx, y + dy)[0]
    return n, False


def mask5(S, x, y):
    """$24ebc: D6 bits set where blocked: 4 = S, 3 = E, 2 = centre, 1 = W, 0 = N."""
    d6 = 0
    for dx, dy in ((0, 1), (1, 0), (0, 0), (-1, 0), (0, -1)):
        d6 = (d6 << 1) | (1 if blocked(S, x + dx, y + dy)[0] else 0)
    return d6


def floor_of(S, x, y):
    """$2511e: the floor of the block holding (x, y), module byte (y >> 3) * 4 + (x >> 4) (word arithmetic)."""
    d5 = ((((y & 0x18) << 3) + x) & 0xffff) >> 4
    return S.b[d5]


def lift_up(S, x, y):
    """$2511e + $2514c: partner on the floor above."""
    kk = floor_of(S, x, y) + 1
    o = 2 * (kk - 2)
    return wrap(x + S.sw(16 + o)), wrap(y + S.sw(24 + o))


def lift_down(S, x, y):
    """$2511e + $25136: partner on the floor below."""
    kk = floor_of(S, x, y)
    o = 2 * (kk - 2)
    return wrap(x - S.sw(16 + o)), wrap(y - S.sw(24 + o))


def step_flow(S, x, y):
    """$253a6: one step along the cell's plane-2 arrow (G2 byte 0); 4 / 5 ride the lift up / down."""
    d = S.g2(d5of(x, y))
    if d == 4:
        return lift_up(S, x, y)
    if d == 5:
        return lift_down(S, x, y)
    return wrap(x + cw(0x25404 + 2 * d)), wrap(y + cw(0x2540c + 2 * d))


def rcell(S, ror_n=6):
    """$244a2: D0 = rng; x = D0 & $3f, y = (D0 ror 6) & $1f."""
    d0 = S.rng()
    return d0 & 0x3f, ((d0 >> 6) | (d0 << 10)) & 0x1f, d0


def cell_of(d0):
    """$244a6 on a given D0."""
    return d0 & 0x3f, ((d0 >> 6) | (d0 << 10)) & 0x1f


def ror16(v, n):
    v &= 0xffff
    return ((v >> n) | (v << (16 - n))) & 0xffff


# ---------------------------------------------------------------- stages

DEADEND_SKIP = (0x06, 0x37, 0x1c, 0x1d, 0x1a, 0x1b, 0x05, 0x04, 0x36, 0x35, 0x0f, 0x21, 0x18)


def s_25198(S):
    """List dead ends: open cells with exactly 3 blocked neighbours, scanned y = 31..0, x = 63..0, except the
    entrance (row 0, x = 32(A6)) and lift / special features; at most 254, as (x, y) bytes at 12440 (count 12438);
    each gets feature $7f."""
    for i in range(512):
        S.b[12440 + i] = 0
    S.setw(12438, 0)
    d7 = 0xfe
    p = 12440
    for y in range(31, -1, -1):
        for x in range(63, -1, -1):
            if d7 == 0:
                continue
            n, _ = nblocked(S, x, y)
            if n != k('deadend_n', 3):
                continue
            d5 = d5of(x, y)
            if y == 0 and x == S.w(32):
                continue
            if S.feat(d5) in DEADEND_SKIP:
                continue
            S.b[p], S.b[p + 1] = x, y
            p += 2
            S.inc(12438)
            S.setfeat(d5, 0x7f)
            d7 -= 1


def s_2533a(S):
    """Prune dead ends: threshold T = D0 * 2048 for D0 <= 31, else $ffff (never). For each of the 256 list slots,
    draw r; when r > T and the slot is used, step once along the cell's arrow; unless that parent cell has 2 or 3
    blocked neighbours (a corridor or another dead end), the dead end is filled with rock (G0 = 0, G1 = 0)."""
    d0 = S.w(12408)
    t = 0xffff if d0 > 0x1f else ror16(d0, 5) & 0xf800
    S.setw(13282, t)
    p = 12440
    for _ in range(256):
        r = S.rng()
        if r > t and S.w(p) != 0:
            x, y = S.b[p], S.b[p + 1]
            px, py = step_flow(S, x, y)
            n, _ = nblocked(S, px, py)
            if n not in k('prune_keep', (3, 2)):
                d5 = d5of(x, y)
                S.setg0(d5, 0)
                S.setg1w(d5, 0)
        p += 2


def s_25162(S):
    """Shuffle the 256-slot dead-end list with 513 random swaps; the RNG seed is restored afterwards."""
    seed = S.w(12404)
    for _ in range(k('shuffle_n', 0x201)):
        d1 = S.rng() & 0x1fe
        d0 = S.rng() & 0x1fe
        a, b = 12440 + d0, 12440 + d1
        va, vb = S.w(a), S.w(b)
        S.setw(a, vb)
        S.setw(b, va)
    S.setw(12404, seed)


def pick_deadend(S):
    """$2567e: a random used dead-end slot whose cell still has feature $7f; stale slots are cleared on the way.
    Returns (x, y) or None (Z = 0) when 256 probes find nothing."""
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
            return x, y
        S.setw(12440 + d0, 0)


def special_25300(S, x, y):
    if not (0 <= x <= 0x3f and 0 <= y <= 0x1f):
        return False
    return S.feat(d5of(x, y)) in (0x35, 0x36, 0x37, 0x33, 0x1f)


def patch3(S, x, y, val):
    """$25292: a 3x3 patch of feature `val` from (x, y), growing +x unless (x+1, y) is a room / lift cell
    ($25300 features $35 $36 $37 $33 $1f), and +y likewise for (x, y+1); lift features keep theirs."""
    d3 = 1 if special_25300(S, x + 1, y) else -1
    d4 = 1 if special_25300(S, x, y + 1) else -1
    yy = y
    for _ in range(3):
        xx = x
        for _ in range(3):
            d5 = d5of(xx, yy)
            if S.feat(d5) not in (0x35, 0x36, 0x37, 0x04, 0x05, 0x06):
                S.setfeat(d5, val)
            xx += d3
        yy += d4


def s_25240(S):
    """Feature-9 patch: the first room-list entry (12952, 64 x (x, y, floor, kind)) whose kind has both bit fields
    0-2 and 3-5 non-zero gets a 3x3 patch of feature 9; with none, one random dead end gets feature 9."""
    for i in range(64):
        e = 12952 + 4 * i
        d0 = S.w(e + 2)
        if (d0 & 7) and (d0 & 0x38):
            patch3(S, S.b[e], S.b[e + 1], k('patch_val', 9))
            return
    while True:
        c = pick_deadend(S)
        if c:
            S.setfeat(d5of(*c), k('patch_val', 9))
            return


def s_24d64(S, d5, d6):
    """Replace every G0 word equal to D5 by D6."""
    for i in range(2048):
        if S.w(G0 + 2 * i) == d5 & 0xffff:
            S.setw(G0 + 2 * i, d6 ^ k('repl_xor', 0))


def s_24128(S):
    """Feature $16 markers on corridor cells: D0 = 0 places none; else min(D0, 10 -> 20) + 1 tries. Each starts at a
    random cell, steps once along its arrow (twice when x + y is then odd), then walks the arrows two steps at a
    time up to 19 times until an open cell of feature 7; that cell gets $16 unless a door ($15) is beside it."""
    d7 = S.w(12408)
    if d7 == 0:
        return
    d7 = d7 if d7 <= 10 else 0x14
    for _ in range(d7 + 1):
        x, y = cell_of(ror16(S.rng(), 4))
        x, y = step_flow(S, x, y)
        if (x + y) & 1:
            x, y = step_flow(S, x, y)
        for _ in range(19):
            d5 = d5of(x, y)
            if S.feat(d5) == 7:
                n, z = nblocked(S, x, y)
                if not z:
                    d5 = d5of(x, y)
                    if not any(S.b[G1 + d5 + o] == 0x15 for o in (3, -1, -127, 129)):
                        S.inc(13642)
                        S.setfeat(d5, k('mark16', 0x16))
                    break
            x, y = step_flow(S, x, y)
            x, y = step_flow(S, x, y)


def s_240c2(S):
    """Feature $1e on thin rock walls: (D0 <= 20 ? 4 D0 : 80) + 1 tries; each from a random cell, up to 5 cells
    rightwards (x wraps), takes the first rock cell open on both sides N/S or both sides E/W with no feature."""
    d7 = S.w(12408)
    d7 = d7 * 4 if d7 <= 0x14 else 0x50
    for _ in range(d7 + 1):
        x, y = cell_of(ror16(S.rng(), 4))
        for _ in range(5):
            d6 = mask5(S, x, y)
            ok = False
            if d6 & 4:
                if (d6 & 0x11) == 0 or (d6 & 0x0a) == 0:
                    ok = True
            if ok:
                d5 = d5of(x, y)
                S.inc(13644)
                if not (S.g0(d5) & 0x8000) and S.feat(d5) == 0:
                    S.setfeat(d5, k('thin', 0x1e))
                    break
            x = (x + 1) & 0x3f


def count_2640a(S, d7):
    """$2640a: compress D7 (D6 += 8, D7 = (D7 - 8) / 2 while D7 > 7; D7 += D6), then halve it while an LCG run
    from the base seed sets bit 5 without a carry."""
    d6 = 0
    if d7 > 7:
        while True:
            d6 += 8
            d7 = ((d7 - 8) & 0xffff) >> 1
            if d7 <= 7:
                break
        d7 = (d7 + d6) & 0xffff
    v = S.w(12408)
    while True:
        p = (v & 0xffff) * 0x5e5
        lo = (p & 0xffff) + 0x29
        c = lo > 0xffff
        v = (p & 0xffff0000) | (lo & 0xffff)
        if c or not (v & 0x20):
            return d7
        d7 >>= 1


def ok_2664e(S, x, y):
    """$2664e: Z = 1 for an open cell (G0 >= 1 signed) whose feature is 7, $1f, $33, $14 or $11."""
    d5 = d5of(x, y)
    if S.sw(G0 + d5) < 1:
        return False
    return S.feat(d5) in (7, 0x1f, 0x33, 0x14, 0x11)


def pick_2663e(S):
    x, y, _ = rcell(S)
    if ok_2664e(S, x, y):
        return x, y, True
    return x, y, S.feat(d5of(x, y)) == 0x28


def s_26438(S):
    """Objects $24 ($2a on a $28 cell): for D0 > 5, count_2640a(D0) + 11 tries at plain open cells, at most 11."""
    d7 = S.w(12408)
    if d7 <= 5:
        return
    d7 = (count_2640a(S, d7) + 10) & 0xffff
    for _ in range(sx(d7) + 1):
        x, y, z = pick_2663e(S)
        if z:
            d5 = d5of(x, y)
            S.setfeat(d5, 0x2a if S.feat(d5) == 0x28 else k('obj24', 0x24))
            S.inc(13634)
            if S.w(13634) > 10:
                return


def s_265cc(S):
    """Objects $25 ($2b on a $28 cell): for D0 > 1, 2 (count_2640a(D0) + 10) + 1 tries, no cap."""
    d7 = S.w(12408)
    if d7 <= 1:
        return
    d7 = ((count_2640a(S, d7) + 10) * 2) & 0xffff
    for _ in range(sx(d7) + 1):
        x, y, z = pick_2663e(S)
        if z:
            d5 = d5of(x, y)
            S.setfeat(d5, 0x2b if S.feat(d5) == 0x28 else k('obj25', 0x25))
            S.inc(13636)


def s_26606(S):
    """Objects $26: for D0 > 2, D0 + 11 tries at open cells of feature $1f, $33, $14 or $11; at most 8."""
    d7 = S.w(12408)
    if d7 <= 2:
        return
    for _ in range(d7 + 10 + 1):
        x, y, _ = rcell(S)
        if ok_2664e(S, x, y):
            d5 = d5of(x, y)
            if S.feat(d5) != 7:
                S.setfeat(d5, k('obj26', 0x26))
                S.inc(13632)
                if S.w(13632) > 7:
                    return


def s_26532(S):
    """Feature $32: for D0 > 5, min(D0 - 5, 60) / 2 + 1 random cells with a non-zero G1 word; a plain corridor
    cell (G1 word = 7) becomes $0032."""
    d7 = S.w(12408)
    if d7 <= 5:
        return
    d7 = min(d7 - 5, 60) >> 1
    for _ in range(d7 + 1):
        while True:
            x, y, _ = rcell(S)
            d5 = d5of(x, y)
            if S.g1w(d5) != 0:
                break
        if S.g1w(d5) == 7:
            S.setg1w(d5, k('obj32', 0x32))
            S.inc(13622)


def s_26570(S):
    """Feature $30/$31: for D0 > 3, min(D0 - 3, 40) / 2 + 1 random cells with a non-zero G1 word; a room cell
    ($1f or $33) gets $30 + (draw & 1), a plain corridor cell open on all four sides gets $30."""
    d7 = S.w(12408)
    if d7 <= 3:
        return
    d7 = min(d7 - 3, 40) >> 1
    for _ in range(d7 + 1):
        while True:
            x, y, d0 = rcell(S)
            d5 = d5of(x, y)
            if S.g1w(d5) != 0:
                break
        f = S.feat(d5)
        if f in (0x1f, 0x33):
            S.setg1w(d5, (d0 & 1) + k('obj30', 0x30))
            S.inc(13620)
        elif S.g1w(d5) == 7 and mask5(S, x, y) == 0:
            S.setg1w(d5, k('obj30', 0x30))
            S.inc(13620)


def wall_26298(S, x, y):
    """$26298: a rock cell none of whose open neighbours has feature $15, $1e, $12 or $13; returns the count of
    its non-open neighbours (feature $23 counts as non-open), or None to reject."""
    _, z = blocked(S, x, y)
    if z:
        return None
    n = 0
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        d0, z = blocked(S, x + dx, y + dy)
        if not z:
            n += d0
            continue
        if d0:
            n += d0
            continue
        f = S.feat(d5of(x + dx, y + dy))
        if f == 0x23:
            n += 1
            continue
        if f in (0x15, 0x1e, 0x12, 0x13):
            return None
    return n


def s_2630c(S):
    """Decorated wall faces: up to 100 rounds of up to 101 draws; a draw takes a featureless rock cell beside at least
    one corridor (wall_26298) and gives it feature $2c with parameter = mask of its open sides (N 1, E 2, S 4, W 8)
    and a picture number (draw >> 8) mod 6, 1 -> 2, recorded with the cell at fed list 13704 (x, y, picture, 0),
    count 13640; stops after 100 faces."""
    lst = S.fptr(13704)
    for _ in range(100):
        for _ in range(101):
            x, y, d0 = rcell(S)
            S.setw(13284, d0)
            n = wall_26298(S, x, y)
            if n is None or n == 4:
                continue
            d5 = d5of(x, y)
            if S.g1w(d5) != 0:
                continue
            d6 = mask5(S, x, y)
            d4 = 0
            if not d6 & 0x10:
                d4 |= 4
            if not d6 & 0x08:
                d4 |= 2
            if not d6 & 0x02:
                d4 |= 8
            if not d6 & 0x01:
                d4 |= 1
            pic = S.w(13284) >> 8
            while pic > 5:
                pic -= k('pic_mod', 6)
            if pic == 1:
                pic = 2
            S.b[G1 + d5] = d4
            S.setfeat(d5, 0x2c)
            o = lst + 4 * S.sw(13640)
            S.f[o], S.f[o + 1], S.f[o + 2], S.f[o + 3] = x, y, pic & 0xff, 0
            S.inc(13640)
            break
        if S.w(13640) > 0x63:
            return


def s_26854(S):
    """Lift-end pairs $2e / $2f: min(D0, 40) + 1 tries; from a random cell scan the row rightwards to x = 63 (the
    loop re-enters at $26866, so D5 is recomputed and the `addq.w #1,D5` is dead) for a lift feature 4 / $35 (up)
    or 5 / $36 (down); when the partner on the next floor is the matching end, the up end gets $2e and the down end
    $2f (count 13648 up, 13646 down). One pair at most per try."""
    d7 = min(S.w(12408), 0x28)
    for _ in range(d7 + 1):
        x, y, _ = rcell(S)
        while True:
            d5 = d5of(x, y)
            f = S.b[G1 + d5 + 1]
            if f in (4, 0x35):
                px, py = lift_up(S, x, y)
                p5 = d5of(px, py)
                if S.feat(p5) in (0x36, 5):
                    S.setfeat(p5, 0x2f)
                    S.b[G1 + d5 + 1] = k('lift_up_end', 0x2e)
                    S.inc(13646, -1)
                    S.inc(13648)
                break
            if f in (5, 0x36):
                px, py = lift_down(S, x, y)
                p5 = d5of(px, py)
                if S.feat(p5) in (0x35, 4):
                    S.setfeat(p5, 0x2e)
                    S.b[G1 + d5 + 1] = 0x2f
                    S.inc(13646, -1)
                    S.inc(13648)
                break
            x += 1
            if x > 0x3f:
                break


def pick_room(S):
    """$256be: a random used slot of the room list 12952 (index rng & $fc, then forward, 33 probes); (x, y, index)."""
    d6 = 32
    d0 = S.rng() & 0xfc
    while S.w(12952 + d0) == 0:
        d0 = (d0 + 4) & 0xfc
        d6 -= 1
        if d6 < 0:
            return None
    return S.b[12952 + d0], S.b[12952 + d0 + 1], d0


def mv(x, y, d):
    """$253c2: one step in the doubled direction D0 (0 N, 2 W, 4 S, 6 E) through the table at $25404."""
    return wrap(x + cw(0x25404 + d)), wrap(y + cw(0x2540c + d))


ROOM = (0x1f, 0x33)


def s_256f0(S):
    """Room doorways: 61 random rooms; from the room's cell walk (w + h + 2) steps down the arrows ((kind & 7) +
    (kind >> 3 & 7) + 2), then two cells back against the last arrow. If that cell is open and not room floor,
    nothing. Otherwise step one cell back along the arrow: if a side cell (left or right of the arrow) is blocked,
    this cell is room floor and the cell its arrow leads to is room floor too, the cell gets feature $21 and
    G0 $ffec, and the next one feature $0e (count 13272)."""
    S.setw(13272, 0)
    for _ in range(k('rooms_n', 61)):
        r = pick_room(S)
        if r is None:
            continue
        x, y, d0 = r
        S.setw(13212, d0)
        kind = S.b[12952 + d0 + 3]
        n = (kind & 7) + ((kind & 0x38) >> 3) + 1
        for _ in range(n + 1):
            x, y = step_flow(S, x, y)
        d = ((2 * S.g2(d5of(x, y))) ^ 4) & 0xffff
        x, y = mv(x, y, d)
        x, y = mv(x, y, d)
        if not blocked(S, x, y)[0] and S.feat(d5of(x, y)) not in ROOM:
            continue
        d ^= 4
        x, y = mv(x, y, d)
        if not blocked(S, *mv(x, y, (d + 2) & 6))[0] and not blocked(S, *mv(x, y, (d - 2) & 6))[0]:
            continue
        d5 = d5of(x, y)
        if S.feat(d5) not in ROOM:
            continue
        px, py = step_flow(S, x, y)
        p5 = d5of(px, py)
        if S.feat(p5) in ROOM:
            S.setfeat(p5, 0x0e)
            S.setfeat(d5, k('doorway', 0x21))
            S.setg0(d5, 0xffec)
            S.inc(13272)


MODELS = {
    0x25198: s_25198, 0x2533a: s_2533a, 0x25162: s_25162, 0x25240: s_25240,
    0x24128: s_24128, 0x240c2: s_240c2, 0x26438: s_26438, 0x265cc: s_265cc, 0x26606: s_26606,
    0x256f0: s_256f0, 0x26532: s_26532, 0x26570: s_26570, 0x2630c: s_2630c, 0x26854: s_26854,
}
# $24d64 runs twice with different registers (D5, D6) set by $23bb0 just before the call
MODELS_BY_STOP = {0x23d0a: lambda S: s_24d64(S, 0xffc3, 0), 0x23d36: lambda S: s_24d64(S, 0xffc4, 0xfff6)}

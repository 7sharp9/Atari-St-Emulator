"""141st, area `build`: from-disassembly models of the world-build routines (`$13b9a` calls them in this order:
`$10d1e` -> `$ffa6` (terrain, `maps_ref`) -> `$2266`/`$ac20` -> `$1073c`/`$10058` -> `$4672` -> `$2984` -> `$238c` -> `$2906`).

Imports `tools/pm_fsm_ref.py` for what already exists (`Mem`, `rng_12c9a`, `call_16808`, `s8`/`s16`).  Each model takes a
`Mem` and mutates it exactly like the real routine mutates RAM; the gate (`gate_build.py`) diffs the two over all RAM.

    $10d1e  make_world   the land's parameter block ($58146..$58150), site stream ($58152), per-side blocks ($580c6..)
    $111e2  rand_site    a random (x, y) byte pair appended to the site stream
    $4672   setup_forests  ten forest clusters: operation records $57f68, trees $4d252, markers $4c5f4
    $4788   place_tree   one tree (probability 1/D3) in cell D2, linked into the cell's bucket chain
"""
import sys
import os
from pathlib import Path

ROOT = Path(os.environ.get("M68000_ROOT") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
from pm_fsm_ref import Mem, rng_12c9a, call_16808, OBJ

W = 0xffff


def sx(v):
    """sign-extend a word"""
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


# ============================================================ $10d1e
SIDE_STATE = 0x5801c          # 5 slots x 6 bytes (side n at +6*(n-1)); byte 4 = the command state
STREAM = 0x58152              # site stream: 4-byte records (x, y, kind 1..4, size 1..5), terminated by size 0
AREA = 0x111ca                # 4 words: total site size per kind; 0x111d2.. the 5-word size table; 0x111e0 total
SIZETAB = AREA + 8
TOTAL = 0x111e0
SIDEBLK = 0x580a6             # 32-byte per-side blocks; the scratch block for the AI sides is built at $580a6, copied to $580c6+
MAKE_WORLD_TRACE = []


def rand_site(m, A0):
    """$111e2: append x = rnd % $2f + 8, y = rnd % $70 + 8 to the stream at A0; return (A0', D2 = x<<8 | y)."""
    x = rng_12c9a(m) % 0x2f + 8
    m.wb(A0, x)
    y = rng_12c9a(m) % 0x70 + 8
    m.wb(A0 + 1, y)
    return A0 + 2, (x << 8) | y


def _ffa6_rng(m):
    """$ffa6 (the terrain blobs, `maps_ref`/`gate_maps.py`): reseeds the RNG from word[$58146] and draws twice per
    blob (D7 = word[$58148] + 1 blobs, `dbf`); `$10410` (the smoothing) draws none.  Only the RNG state matters to
    $10d1e: its terrain writes are outside the model (the gate masks the planes)."""
    m.wl(P.RNG_SEED, m.wu(0x58146))
    for _ in range(m.wu(0x58148) + 1):
        rng_12c9a(m)
        rng_12c9a(m)


def make_world(m):
    """$10d1e: reseed from $580a0, roll the land parameters, the site stream and the sides' start blocks."""
    T = MAKE_WORLD_TRACE
    m.wl(P.RNG_SEED, m.lu(0x580a0))
    m.ww(0x58146, rng_12c9a(m))
    d0 = (rng_12c9a(m) & 0x7fff) + 0x1500
    if m.wu(0x5809c):
        d0 = m.wu(0x5809c)
    m.ww(0x58148, d0)
    d1, d2 = 2, 0
    if sx(d0) < 0x2000:                       # cmp.w #$2000,D0 ; bge
        d1, d2 = 0xa, 3
        T.append("small")
    m.ww(0x5814a, (rng_12c9a(m) & 7) + d1)
    m.ww(0x5814c, rng_12c9a(m) & 0x3f)
    m.ww(0x5814e, rng_12c9a(m) & 0x7f)
    m.ww(0x58150, (rng_12c9a(m) & 3) + 2 + d1)
    _ffa6_rng(m)
    d0 = rng_12c9a(m)
    if m.wu(0x5809c) == 0:
        n = d0 % 10 + 8                       # D1: number of sites - 1 (dbf)
    else:
        n = d0 % 10 + 4
    m.ww(TOTAL, 0)
    m.wl(AREA, 0)
    m.wl(AREA + 4, 0)
    A0 = STREAM
    d2 = d3 = 0
    d1 = n
    while True:                                # $10dfe .. dbf D1
        A0, d2 = rand_site(m, A0)
        d4 = (rng_12c9a(m) & 3) + 1
        m.wb(A0, d4)
        A0 += 1
        d0 = rng_12c9a(m) % 5 + 1
        m.wb(A0, d0)
        A0 += 1
        d0 = m.wu(SIZETAB + 2 * d0)
        m.ww(TOTAL, m.wu(TOTAL) + d0)
        d4 = (d4 - 1) * 2
        m.ww(AREA + d4, m.wu(AREA + d4) + d0)
        d3 = d2
        if d1 == 0:
            break
        d1 -= 1
    m.wl(A0, 0)
    # the sides: d4 := 1 if some side's state is 6 or 8; d5 := the last side whose state is neither
    d4 = d5 = 0
    for side in range(1, 5):
        st = m.bu(SIDE_STATE + 6 * (side - 1) + 4)
        if st in (6, 8):
            d4 = 1
        else:
            d5 = side
    if d4:                                     # $10e7c
        if d5 == 0:
            T.append("B-none")
            return
        T.append("B")
        A0 = _side_stream_B(m, A0, d3, d5)
        return
    if m.wu(0x5809c) == 0:
        T.append("A")
        _campaign_A(m, A0, d3)
    else:
        T.append("C")
        _random_C(m, A0, d3)


def _side_stream_B(m, A0, d3, d5):
    """$10e82..$10fb8: a side in state 6/8 exists and another does not: a fresh assessment block, those sides' sites go
    to side D5 (the last side not in 6/8), and every non-zero side gets a start site and its block copy."""
    d0 = rng_12c9a(m)
    m.ww(0x580a6, (d0 & 7) + 0xf)
    m.ww(0x580a8, (d0 & 0xf) - 7 + 0x29)
    m.ww(0x580aa, (d0 & 0x1f) + 0x40)
    m.ww(0x580ae, (d0 & 3) + 0xa)
    m.ww(0x580b0, (d0 & 0x1f) + 0xc)
    m.ww(0x580b2, 7)
    m.ww(0x580b4, 2)
    if d0 & 3:
        m.ww(0x580b4, d0 & 3)
    A1, A3 = SIDE_STATE, 0x580c6
    for d1 in range(1, 5):
        st = m.bu(A1 + 4)
        if st != 0:
            if st in (6, 8):
                A2 = STREAM
                while True:                    # $10f28
                    A2 += 2
                    d6 = m.bu(A2)
                    d4 = m.bu(A2 + 1)
                    A2 += 2
                    if d4 == 0:
                        break
                    if d4 >= 6:
                        continue
                    if d6 == d1:
                        m.wb(A2 - 2, d5)
                        MAKE_WORLD_TRACE.append("B:reassign")
            A0, d2 = rand_site(m, A0)
            m.wb(A0, d1)
            m.wb(A0 + 1, 0x10)
            A0 += 2
            if d3:
                m.ww(A0, d3)
                m.ww(A0 + 2, 0x11)
                m.ww(A0 + 4, d2)
                m.ww(A0 + 6, 0x63)
                A0 += 8
            m.wl(A0, 0)
            for off, src in ((0, 0x580a6), (2, 0x580a8), (4, 0x580aa), (8, 0x580ae), (10, 0x580b0), (12, 0x580b2), (14, 0x580b4)):
                m.ww(A3 + off, m.wu(src))
            m.wl(A3 + 16, 0)
            m.wl(A3 + 20, 0)
        A3 += 32
        A1 += 6
    return A0


def _campaign_A(m, A0, d3):
    """$10fc6..$1110a (no side in 6/8, `$5809c` == 0): the four sides' blocks at $580c6 (+32 each) from one draw each,
    and the site stream rebalanced so each side holds about a quarter of the area, plus a start group for a side.
    Quirk (code read, gate-checked): the state tested at $110d0 is `4(A3)` of side 1's slot every iteration, the
    computed `D1 = D4*3` is never used."""
    A1 = 0x580c6
    for d4 in (0, 2, 4, 6):
        d0 = rng_12c9a(m)
        d1 = d0 & 7
        m.ww(A1 + 0, 0xa + d1)
        d1 = (d1 << 4) & W
        m.ww(A1 + 4, (0xfa - d1) & W)
        d0 >>= 1
        d1 = d0 & 0x1f
        m.ww(A1 + 2, 0x1c + d1)
        d0 >>= 1
        d1 = (d0 + 0x1f) & W
        m.ww(A1 + 8, (8 + d1) & W)
        d0 >>= 1
        d1 = d0 & 7
        m.ww(A1 + 10, 0xa + d1)
        d0 >>= 1
        d1 = d0 & 0xff
        m.ww(A1 + 24, 0x190)
        m.ww(A1 + 24, d1)
        m.ww(A1 + 12, 7)
        m.ww(A1 + 14, 2)
        while True:                            # $1104c
            d0 = m.wu(TOTAL) >> 2
            if sx(d0) <= sx(m.wu(AREA + d4)):
                break
            d0 = 0
            d5 = 0
            for d1 in (0, 2, 4, 6):            # $11062: d5 := index of the largest (last on a tie), start 0
                if not sx(d0) > sx(m.wu(AREA + d1)):
                    d0 = m.wu(AREA + d1)
                    d5 = d1
            d6 = (d5 >> 1) + 1
            A3 = STREAM
            while True:
                d0 = m.bu(A3 + 3)
                if d0 == 0:
                    break                      # -> $110be, out of the rebalance loop
                if d0 < 6 and m.bu(A3 + 2) == d6:
                    d1 = (d4 >> 1) + 1
                    m.wb(A3 + 2, d1)
                    d1 = m.wu(AREA + 8 + 2 * d0)
                    m.ww(AREA + d5, m.wu(AREA + d5) - d1)
                    m.ww(AREA + d4, m.wu(AREA + d4) + d1)
                    MAKE_WORLD_TRACE.append("A:rebalance")
                    d0 = -1                    # bra $1104c: test again
                    break
                A3 += 4
            if d0 == 0:
                break
        d0 = rng_12c9a(m)
        if m.bu(SIDE_STATE + 4) != 0 or (d0 & 2):
            MAKE_WORLD_TRACE.append("A:start" + ("(state)" if m.bu(SIDE_STATE + 4) != 0 else "(bit1)"))
            A0, d2 = rand_site(m, A0)
            m.wb(A0, (d4 >> 1) + 1)
            m.wb(A0 + 1, 0x10)
            m.ww(A0 + 2, d3)
            m.ww(A0 + 4, 0x11)
            m.ww(A0 + 6, d2)
            m.ww(A0 + 8, 0x63)
            A0 += 10
        A1 += 32


def _random_C(m, A0, d3):
    """$1110e..$111c4 (random land, no side in 6/8, `$5809c` != 0): the local side's start site, then up to four more sides'
    sites (a repeated draw of the same side adds none), each side's block from one draw."""
    A0, d2 = rand_site(m, A0)
    m.wb(A0, m.bu(0x57fff))
    if m.bu(0x57fff) == 0:
        m.wb(A0, 1)
    m.wb(A0 + 1, 0x10)
    A0 += 2
    if d3:
        m.ww(A0, d3)
        m.ww(A0 + 2, 0x11)
        m.ww(A0 + 4, d2)
        m.ww(A0 + 6, 0x63)
        A0 += 8
    d4 = 0
    d4 |= 1 << (m.wu(0x57ffe) & 31)
    A1 = 0x580c6
    for d1 in range(1, 5):
        d5 = (rng_12c9a(m) & 3) + 1
        if (d4 >> d5) & 1:
            MAKE_WORLD_TRACE.append("C:dup")
        if not (d4 >> d5) & 1:
            d4 |= 1 << d5
            A0, d2 = rand_site(m, A0)
            m.wb(A0, d5)
            m.wb(A0 + 1, 0x10)
            m.ww(A0 + 2, d3)
            m.ww(A0 + 4, 0x11)
            m.ww(A0 + 6, d2)
            m.ww(A0 + 8, 0x63)
            A0 += 10
        m.ww(A1 + 0, 0xa)
        m.ww(A1 + 2, 0x1e)
        d0 = (rng_12c9a(m) & 0xff) + 0x40
        m.ww(A1 + 4, d0)
        m.ww(A1 + 8, 0xa)
        m.ww(A1 + 10, (d0 & 7) + 7)
        m.ww(A1 + 12, 7)
        m.ww(A1 + 14, 2)
        A1 += 32
    m.wl(A0, 0)


# ============================================================ $4672 / $4788
HERD_OPS, HERD_TREES, HERD_MARKERS = 0x57f68, 0x4d252, 0x4c5f4
OPS_LEN, MARK_NEXT, TREE_NEXT = 0x57fb8, 0x4ccd4, 0x4e512
CLUSTER = 0x488c                  # words: (dx, dy*64, divisor) triples, terminated by $7000
FOREST_TRACE = []


class Regs:
    pass


def place_tree(m, d2, d3, r):
    """$4788: r holds A4 (op record), A5 (the previous tree of this op), A6 (the cluster centre cell), D7.
    Returns D0 (0 refused, 1 accepted); D2 is the cell asked for."""
    T = FOREST_TRACE
    if sx(d2) >= 0x2000:                       # cmp.w #$2000,D2 ; bge
        T.append("t:range")
        return 0
    d0 = m.wu(P.BUCKETS + 2 * d2)
    while d0:                                  # $479c: every record already in the cell must be a tree
        A0 = (OBJ + sx(d0)) & 0xfffff
        if m.bu(A0 + 6) != 4:
            T.append("t:occupied")
            return 0
        d0 = m.wu(A0)
    A0 = 0x438ee + d2
    if m.bs(A0 - 8257) < 0x1f:
        T.append("t:planeA")
        return 0
    if not m.bs(A0) >= 0x1f:
        T.append("t:planeB")
        return 0
    d7 = 0 if m.wu(0x5809c) else 1
    d3 &= 0xff                                  # ext.w D3 (byte -> word)
    if d3 & 0x80:
        d3 |= 0xff00
    if d3 == 0:
        T.append("t:probe")
        return 1
    while True:                                # $47e8 .. dbf D7
        d0 = rng_12c9a(m)
        rem = d0 % d3 if d3 else d0
        if rem == 0:
            d0 = m.wu(TREE_NEXT)
            if d0 == 0x12c0:
                T.append("t:full")
                return 1
            m.ww(r.A4 + 2, m.wu(r.A4 + 2) + 1)
            A0 = HERD_TREES + d0
            m.ww(TREE_NEXT, m.wu(TREE_NEXT) + 0xc)
            d0 = rng_12c9a(m) & 0xf
            if d0 > 3:
                d0 = r.A6 & 3
            d0 = (d0 + 0xe) & 0xff
            m.wb(A0 + 6, 4)
            m.wb(A0 + 7, d0)
            m.ww(A0 + 10, d2)
            d0 = A0 - HERD_TREES
            if m.wu(r.A4 + 4):
                m.ww(r.A5 + 8, d0)
                T.append("t:next")
            else:
                m.ww(r.A4 + 4, d0)
                if r.A4 != HERD_OPS:
                    m.wb(A0 + 7, m.bu(A0 + 7) | 0x80)
                T.append("t:first")
            r.A5 = A0
            call_16808(m, d2, (A0 - OBJ) & W)
        else:
            T.append("t:skip")
        if d7 == 0:
            break
        d7 -= 1
    return 1


def setup_forests(m):
    """$4672: ten attempts (A2 = 0..9) to start a forest: up to 21 random cells until `$4788(cell, 0)` accepts, then an
    operation record, 6..13 map markers, and the `$488c` cluster of trees around the centre cell."""
    T = FOREST_TRACE
    r = Regs()
    r.A4 = r.A5 = r.A6 = 0
    r.A5 = 0
    m.ww(MARK_NEXT, 0x16)
    m.ww(TREE_NEXT, 0xc)
    for a2 in range(10):
        got = 0
        for _ in range(21):
            d2 = rng_12c9a(m) % 0x2000
            if place_tree(m, d2, 0, r):
                got = 1
                break
        if not got:
            T.append("f:none")
            continue
        d0 = m.wu(OPS_LEN)
        if d0 == 0x50:
            T.append("f:oplimit")
            if m.wu(r.A4 + 2):
                m.ww(OPS_LEN, m.wu(OPS_LEN) + 8)
            continue
        r.A4 = HERD_OPS + d0
        m.ww(r.A4, d2)
        d5 = d2
        d6 = 0
        if d0 != 0:
            d5 = (d5 & 7) + 5
            for _ in range(d5 + 1):            # dbf
                d0 = m.wu(MARK_NEXT)
                if d0 == 0x6e0:
                    T.append("f:markfull")
                    break
                m.ww(MARK_NEXT, d0 + 0x16)
                A1 = HERD_MARKERS + d0
                m.ww(A1 + 20, d6)
                m.wb(A1 + 5, 1)
                d6 = d0
                m.wb(A1 + 8, d2 & 0x3f)
                m.wb(A1 + 9, 0x80)
                m.ww(A1 + 10, (((d2 & 0x1fc0) << 2) + 0x80) & W)
                m.wb(A1 + 6, 0x16)
                m.wb(A1 + 16, 0x40)
                m.wb(A1 + 15, 0)
            m.ww(r.A4 + 6, d6)                 # $4730 (the first record, D0 == 0, jumps past it to $4734)
        r.A6 = sx(d2) & 0xffffffff
        A1 = CLUSTER
        while True:                            # $473c
            d0, d1, d3 = m.wu(A1), m.wu(A1 + 2), m.wu(A1 + 4)
            A1 += 6
            if d0 == 0x7000:
                break
            x = ((r.A6 & 0x3f) + d0) & W
            if sx(x) < 0 or sx(x) >= 0x40:
                continue
            y = (r.A6 + d0 + d1) & W
            if sx(y) < 0:
                continue
            place_tree(m, y, d3, r)
        if m.wu(r.A4 + 2):
            m.ww(OPS_LEN, m.wu(OPS_LEN) + 8)
            T.append("f:op")


# ============================================================ $2eac, $1b2a, $1cc4, $238c, $2906
sys.path.insert(0, str(ROOT / "reversing/powermonger/py/maps"))
import maps_ref as MR

LORDS, LORDS_END_W = 0x4e514, 0x4f914            # 32-byte lord records; word $4f914 = $20 * placements made
SETTL, SETTL_END_W = 0x4f916, 0x51536            # 18-byte settlement records; word $51536 = $12 * placements made
GROUP = 0x51538                                   # 8 sides x $13c
TOWN_TRACE = []


def _adda(base, w):
    return (base + sx(w)) & 0xfffff


def place_town(m, d1, d2, d3, d4):
    """$2eac `_set_town`: a lord of side D1 and kind D4 (1..6) at cell (D2, D3), and his layout's buildings.
    Returns (ok, A0): A0 is the lord slot (the caller `$238c` uses it without testing ok)."""
    T = TOWN_TRACE
    A0 = LORDS
    while m.bu(A0 + 5) != 0:
        A0 += 0x20
        if A0 >= 0x4f914:
            T.append("town:nolord")
            return 0, A0
    m.ww(LORDS_END_W, m.wu(LORDS_END_W) + 0x20)
    d3 = ((d3 << 6) + d2) & W                       # lsl.w #6,D3 ; add.w D2,D3
    A1 = (0x438ee + sx(d3)) & 0xfffff
    s = (m.bu(A1 - 16514) + m.bu(A1 - 16513) + m.bu(A1 - 16450) + m.bu(A1 - 16449)) & 0xff
    if s == 0:
        T.append("town:sea")
        return 0, A0
    m.wb(A0 + 0, d1)
    m.wb(A0 + 1, d4)
    d0 = (d1 & 0xff) * 0x20
    m.ww(A0 + 14, m.wu(0x580a6 + d0 + 24))
    m.ww(A0 + 6, (((1 << (d1 & 63)) & W) + 0x14) & W)
    m.ww(A0 + 4, d3)
    A2 = 0x3078 + m.wu(0x3078 + ((d4 * 2) & W))
    A5 = 0
    while True:                                     # $2f3c
        d0 = m.bu(A2)
        if d0 == 0x9d:
            T.append("town:done")
            return 1, A0
        dx = d0 - 256 if d0 & 0x80 else d0
        d1c = ((d3 & 0x3f) + dx) & W
        if sx(d1c) >= 0x40:
            A2 += 3
            continue
        d1c = (d3 + dx) & W
        dy = m.bu(A2 + 1)
        dy = dy - 256 if dy & 0x80 else dy
        d1c = (d1c + ((dy << 6) & W)) & W
        if sx(d1c) >= 0x2000:
            A2 += 3
            continue
        A3 = (0x438ee + sx(d1c)) & 0xfffff
        s = (m.bu(A3 - 16514) + m.bu(A3 - 16513) + m.bu(A3 - 16450) + m.bu(A3 - 16449)) & 0xff
        if s == 0:
            T.append("town:bsea")
            A2 += 3
            continue
        blocked = False
        if m.bu(A0 + 1) != 6:
            d0 = m.wu(P.BUCKETS + 2 * sx(d1c))                 # add.w D0,D0 ; 0(A4,D0.w)
            while d0:
                A4 = _adda(OBJ, d0)
                if m.bu(A4 + 6) in (0x10, 2):
                    blocked = True
                    break
                d0 = m.wu(A4)
        if blocked:
            T.append("town:occupied")
            A2 += 3
            continue
        A4 = SETTL + 0x12
        while m.bu(A4 + 5) != 0:
            A4 += 0x12
            if A4 >= 0x51536:
                T.append("town:nosettl")
                return 0, A0
        m.ww(SETTL_END_W, m.wu(SETTL_END_W) + 0x12)
        m.wb(A3 + 8257, m.bu(A3 + 8257) | 2)
        for o in (8258, 8321, 8322):
            m.wb(A3 + o, m.bu(A3 + o) | 2)
        d0 = A4 - SETTL
        if m.wu(A0 + 2) == 0:
            m.ww(A0 + 2, d0)
        else:
            m.ww(A5 + 8, d0)
        A5 = A4
        m.wb(A4 + 5, m.bu(A0 + 0))
        m.wb(A4 + 6, 2)
        d0 = m.bu(A2 + 2)
        m.wb(A4 + 7, d0)
        if d0 == 7:
            m.wb(A4 + 6, 0x10)
        m.ww(A4 + 12, d1c)
        m.ww(A4 + 14, A0 - LORDS)
        call_16808(m, sx(d1c), (A4 - OBJ) & W)      # the real code indexes the bucket table with a sign-extended word
        T.append("town:placed")
        A2 += 3


def add_ranker(m, A0, A1):
    """$1b2a `_add_ranker`: man A1 joins the group of the lead A0 (pushed at the head of the roster).  True if done.
    A man of another side joins only if his home settlement is owned by the lead's side; he then changes side."""
    d2 = m.bu(A0 + 5)
    if d2 != m.bu(A1 + 5):
        A3 = _adda(SETTL, m.wu(A1 + 34))
        if m.bu(A3 + 5) != d2:
            return False
        m.wb(A1 + 5, d2)
    A3 = _adda(GROUP, m.wu(A0 + 42))
    m.ww(A3 - 24, m.wu(A3 - 24) + 1)
    m.ww(A1 + 26, m.wu(A3 - 36))
    m.ww(A3 - 36, (A1 - OBJ) & W)
    m.ww(A1 + 28, (A0 - OBJ) & W)
    m.wb(A1 + 7, m.bu(A1 + 7) | 0x40)
    return True


def derank(m, d2):
    """$1cc4 `_derank`: D2 = the group's offset (`$51538` + D2 is the roster block).  Dismiss `count >> (posture - 2)` men,
    each time the one with the lowest (byte 44 + byte 33) as a signed byte (the last of equals), via $1b8c."""
    P.call_37c2(m, d2)
    A2 = _adda(GROUP, d2)
    A0 = _adda(OBJ, m.wu(A2 - 12))
    cnt = m.wu(A2 - 24)
    sh = P.call_30fe(m, A0) & 63                    # lsr.w D0,D2: count mod 64
    cnt = (cnt >> sh) if sh < 16 else 0
    if cnt == 0:
        return
    A1 = A0                                          # movea.l A0,A1: kept across the dismissals (no reset per man)
    while True:
        d0 = m.wu(A2 - 36)
        d3 = 0x7f
        while True:
            A3 = _adda(OBJ, d0)
            d0 = (m.bu(A3 + 44) + m.bu(A3 + 33)) & 0xff
            if not (P.s8(d3) < P.s8(d0)):           # cmp.b D0,D3 ; blt
                d3 = d0
                A1 = A3
            d0 = m.wu(A3 + 26)
            if d0 == 0:
                break
        P.call_1b8c(m, A0, A1, 0)
        cnt = (cnt - 1) & W
        if cnt == 0:
            break
    P.call_1d70(m, A2)


def setup_water(m):
    """$2906 `_setup_w...`: for each lord with an owner, `word[lord + 22]` := the byte offset into $57f68 of the nearest forest
    operation (max(|dx|, |dy|) over the lord's cell, first of equals; 0 if none)."""
    for A0 in range(LORDS, 0x4f914, 0x20):
        if m.bu(A0) == 0:
            continue
        cell = m.wu(A0 + 4)
        d6, d7 = cell & 0x3f, cell >> 6
        d2 = 0x7fff
        d5 = 0
        for A5 in range(HERD_OPS, 0x57fb8, 8):
            d1 = m.wu(A5)
            if d1 == 0:
                continue
            d0 = abs((d1 & 0x3f) - d6)
            d1 = abs((d1 >> 6) - d7)
            if not d0 > d1:
                d0, d1 = d1, d0
            if not sx(d2) <= sx(d0):                # cmp.w D0,D2 ; ble
                d5 = A5
                d2 = d0
        if d5:
            d5 -= HERD_OPS
        m.ww(A0 + 22, d5)


KINGS_TRACE = []


def setup_kings(m):
    """$238c `_setup_k...`: one start group per side block of $51538 whose word 100 holds a start cell."""
    T = KINGS_TRACE
    A3, A2, d5 = GROUP, 0x580a6, 0
    while True:
        d0 = m.wu(A3 + 100)
        if d0 != 0:
            _one_side(m, A3, A2, d5, d0, T)
        d5 += 1
        A2 += 0x20
        A3 += 0x13c
        if not A3 < 0x51b64:
            break
    P.call_187d8(m)


def _one_side(m, A3, A2, d5, d0, T):
    m.ww(A3 + 100, 0)
    d6 = (((d0 & 0x3f) << 8) + 0x80) & W
    d7 = (((d0 & 0x1fc0) << 2) + 0x80) & W
    d3 = d0 >> 6
    d2 = d0 & 0x3f
    ok, A0 = place_town(m, d5, d2, d3, 6)
    MR.town_gr_10638(m.r, d2, d3, 6)
    A1 = P.call_2e1e(m, d5, d6, d7)
    if A1 == 0:
        T.append("k:noman")
        return
    m.wb(A1 + 14, 0x15)
    m.wb(A1 + 7, m.bu(A1 + 7) | 0x10)
    m.wb(A1 + 45, 0x5f)
    m.wb(A1 + 31, 0x4c)
    m.ww(A1 + 34, m.wu(A0 + 2))
    A6 = _adda(SETTL, m.wu(A0 + 2))
    m.ww(A6 + 10, (A1 - OBJ) & W)
    m.ww(A1 + 42, (A3 - GROUP + 0x4c) & W)
    m.ww(A3 + 64, (A1 - OBJ) & W)
    m.ww(A3 + 28, d5)
    m.ww(A3 + 112, m.wu(A2 + 4))
    m.ww(A3 + 148, m.wu(A2 + 12))
    m.wb(A1 + 33, m.bu(A2 + 20))
    m.wb(A1 + 44, m.bu(A2 + 21))
    m.wb(A2 + 6, m.bu(A2 + 6) | (1 << (d5 & 7)))
    m.wb(A1 + 44, 6)
    m.ww(A3 + 124, 0)
    m.ww(A3 + 136, 3)
    A5 = 0x58016 + d5 * 6
    if m.bu(A5 + 4) == 0:
        m.wb(A5 + 4, 4)
        m.wb(A5, d5)
    ai = m.bu(A5 + 4) == 4
    if ai:
        m.ww(A3 + 112, 0x5fff)
        m.wb(A1 + 33, 0xa)
        m.ww(A3 + 208, m.wu(A2 + 10))
        T.append("k:ai")
    else:
        T.append("k:human")
    if d5 == m.wu(0x57ffe):
        m.ww(0x57fd2, (m.wu(0x57ffe) * 0x13c + 0x4c) & W)
        T.append("k:local")
    A0 = A1
    d1 = m.wu(A2 + 10)
    if d1 != 0:
        d1 -= 1
        while True:
            A1 = P.call_2e1e(m, d5, d6, d7)
            if A1 != 0:
                m.ww(A1 + 34, (A6 - SETTL) & W)
                d0 = (A1 - OBJ) & W
                m.ww(A1 + 24, m.wu(A6 + 10))
                m.ww(A6 + 10, d0)
                m.wb(A1 + 33, m.bu(A2 + 22))
                m.wb(A1 + 44, m.bu(A2 + 23))
                if ai:
                    m.wb(A1 + 33, 0xa)
                add_ranker(m, A0, A1)
                m.wb(A1 + 45, 0x5a)
            if d1 == 0:
                break
            d1 -= 1
        P.call_1d70(m, A3)
    d0 = (d5 * 0x13c + 0x4c) & W
    m.ww(0x58042 + d5 * 2, d0)
    # the side's other lords' leaders become groups of their own ($25d6)
    A6 = LORDS
    while True:
        d0 = m.bu(A6)
        if d0 != 0 and d0 == m.bu(A3 + 29):
            d0 = m.wu(A6 + 2)
            d0 = m.wu(SETTL + sx(d0) + 10)
            while d0 != 0:
                A1 = _adda(OBJ, d0)
                if (m.bu(A1 + 7) & 0x10) and d0 != m.wu(A3 + 64):
                    r = P.call_25d6(m, A1, 0)
                    if r.endswith("new"):
                        T.append("k:captain")
                        if ai:
                            gnew = _adda(GROUP, m.wu(A1 + 42))
                            m.ww(gnew + 36, 0x5fff)
                            m.wb(A1 + 33, 0xa)
                            m.ww(gnew + 132, m.wu(A2 + 10))
                    else:
                        T.append("k:capfull")
                d0 = m.wu(A1 + 24)
        A6 += 0x20
        if A6 == 0x4f914:
            break


def build_towns(m):
    """$1073c: clear the entity table $51b66..$57f66, then place every queued town site (`$ac20` queued `{owner, x, y, kind}`
    words at $4b9f2, terminated by a zero owner word) with `$2eac` and level its ground with `$10638`."""
    for a in range(OBJ, 0x57f66, 2):
        m.ww(a, 0)
    A1 = 0x4b9f2
    while m.wu(A1):
        d1, d2, d3, d4 = (m.wu(A1 + 2 * i) for i in range(4))     # movem.w sign-extends; every value here is < $8000
        A1 += 8
        place_town(m, d1, d2, d3, d4)
        MR.town_gr_10638(m.r, d2, d3, d4)

"""Python model of `$1abaa` (`_seasons`), read from the body `$1abaa..$1ad9a` and its callees.

    call_1abaa(ram) -> (events, branches)

`ram` is a bytearray of the full 1 MB RAM (the pre-call state) and is updated in place to the post-call
state.  Inlined callees: `$1ab90` (rate/phase reset), `$12c9a` + `$12d36` (the 32-bit LCG `$2df84`),
`$1a856` (the rain/snow overlay blit), and the sample-player state writes of `$1ba3e` -> `$1b9d0` ->
`$1b978` -> `$1ae36`.  The four sound calls are also returned as events (id, ignored second argument,
sample index, sequence pointer); no audio is modelled.  Stack scratch (pushed arguments, movem saves)
is not modelled.

Reads: `$1aba0`/`$1ab9e` (entry gate), `[$ff9e]` (pattern table base), `$1aba2[$57fd0]` (season source
offset), `$57fec`, `$57fd0`, `$57ff6`, `$4bb42`, `$4bb44`, `$4bb4a`, `$1ad9c[$57fd0]` (spell type),
`$4e512` (tree array byte length), `$4d252` records, `$2df84`, `$58054`, `[$2df7c]` (offscreen page),
`$1aac8` (overlay phase), `$1a8a4`/`$1a9c8` (overlay tables), `$2c99c`, `$2c9a0`, `$2c993`.
"""
import struct


class Spin(Exception):
    """`$1ae40` spins on byte `$2c993` != 0 (cleared only by an interrupt)."""


class DivZero(Exception):
    pass


def rw(m, a):
    return (m[a] << 8) | m[a + 1]


def ww(m, a, v):
    m[a] = (v >> 8) & 0xff
    m[a + 1] = v & 0xff


def rl(m, a):
    return struct.unpack_from(">I", m, a)[0]


def wl(m, a, v):
    struct.pack_into(">I", m, a, v & 0xffffffff)


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def rng_12c9a(m):
    """$12c9a: s = [$2df84] or $bc614e if 0; s *= $bb40e62d (low 32, $12d36); return (s >> 8) & $7fff."""
    s = rl(m, 0x2df84) or 0xbc614e
    s = (s * 0xbb40e62d) & 0xffffffff
    wl(m, 0x2df84, s)
    return (s >> 8) & 0x7fff


def sound_1ba3e(m, ev, site, sid, arg2):
    """$1ba3e(id, arg2): $1b9d0(max(id-1, 0), $80); arg2 is never read."""
    n = s16(sid - 1)
    if n < 0:
        n = 0
    e = {"site": site, "id": sid, "arg2": arg2, "n": n, "seq": None}
    if n < s16(rw(m, 0x2c99c)):                    # $1ba08: cmp.w $2c99c ; bge -> no play
        seq = rl(m, 0x2c9a0 + 4 * n)
        m[0x2c992] = 0                              # $1b978
        wl(m, 0x1af3a, 0x1b7fa)                     # $1ae36
        if m[0x2c993]:
            raise Spin(site)
        ww(m, 0x2c996, 0)
        wl(m, 0x2cba2, seq)
        m[0x2c994] = 0                              # flags $80 & $20 == 0
        m[0x2c992] = 1
        e["seq"] = seq
    ev.append(e)


def draw_1a856(m, typ, br):
    """$1a856 with D0 = 16 groups, D2 = 4 (32-byte left margin), D1 = $c2 rows, D7 = type."""
    a = (rl(m, 0x2df7c) + 960 + 4 * 8) & 0xffffff
    d3 = (m[0x1aac8] + 0x40) & 0xff
    m[0x1aac8] = d3
    snow = typ == 2
    tab = 0x1a9c8 if snow else 0x1a8a4
    br["snow_draw" if snow else "rain_draw"] += 1
    for _row in range(0xc2):
        d4 = rl(m, tab + d3)
        d3 = (d3 - 4) & 0xff
        for g in range(16):
            w = d4 & 0xffff
            for p in range(4):
                v = rw(m, a)
                if snow and p & 1:
                    v &= ~w & 0xffff
                else:
                    v |= w
                ww(m, a, v)
                a += 2
            d4 = ((d4 << 16) | (d4 >> 16)) & 0xffffffff
        a += (20 - 16) * 8


def weather_1ad2a(m, br):
    d7 = rw(m, 0x4bb42)
    if d7:
        draw_1a856(m, d7, br)
        v = rw(m, 0x4bb44)
        r = (v - 1) & 0xffff
        ww(m, 0x4bb44, r)
        nflag, vflag = bool(r & 0x8000), v == 0x8000
        if nflag != vflag:                          # bge not taken
            ww(m, 0x4bb42, 0)
            br["spell_end"] += 1
        return
    if s16(rw(m, 0x4bb44)) < 0:
        br["spent"] += 1
        return
    d0 = (rw(m, 0x4bb4a) + rw(m, 0x57fec)) & 0xffff
    if d0 & 0xa0 != 0xa0:
        return
    t = rw(m, (0x1ad9c + s16(rw(m, 0x57fd0))) & 0xffffff)
    ww(m, 0x4bb42, t)
    br["start_test"] += 1
    if t:
        ww(m, 0x4bb44, (d0 & 0x3f) + 0x20)
        br["spell_start"] += 1


def wrap_1ac3c(m, ev, br):
    br["wrap"] += 1
    ww(m, 0x57ff6, 0)
    ww(m, 0x1ab9e, 0x100)                           # $1ab90(#$100)
    ww(m, 0x1aba0, 0)
    ww(m, 0x57fec, 0)
    ww(m, 0x4bb42, 0)
    ww(m, 0x4bb44, 0)
    fd0 = (rw(m, 0x57fd0) + 2) & 6
    ww(m, 0x57fd0, fd0)
    q = rw(m, 0x4e512) // 12                        # divu #$c: D1.w = record count
    r = rng_12c9a(m)
    if q == 0:
        raise DivZero("$1ac88")
    rem = r % q                                     # divu D1,D0 ; swap: D0.w = remainder
    a0 = 0x4d252 + s16(rem * 12)                    # mulu #$c ; adda.w (sign-extended)
    br["tree_pick"] += 1
    if m[a0 + 7] == 0x0d:
        m[a0 + 7] = ((rw(m, a0 + 10) & 3) + 0x0e) & 0xff
        br["tree_regrow"] += 1
    snd = rw(m, 0x58054)
    sound_1ba3e(m, ev, 0x1acc8, 0, snd | 0x8000)
    snd = rw(m, 0x58054) ^ 5
    ww(m, 0x58054, snd)
    sound_1ba3e(m, ev, 0x1acec, (fd0 >> 1) + 1, snd | 0xa0)
    sound_1ba3e(m, ev, 0x1ad06, 0, rw(m, 0x58054) | 0x2000)
    sound_1ba3e(m, ev, 0x1ad20, 0xa, rw(m, 0x58054) | 0x8000)


def call_1abaa(m):
    import collections
    br = collections.Counter()
    ev = []
    d1 = m[0x1aba0]
    ww(m, 0x1aba0, (rw(m, 0x1aba0) + rw(m, 0x1ab9e)) & 0xffff)
    if m[0x1aba0] == d1:
        br["gate_return"] += 1
        return ev, br
    a1 = rl(m, 0xff9e) & 0xffffff
    a0 = a1 + 3712
    ww(m, 0x57fec, (rw(m, 0x57fec) + 1) & 0xffff)
    a1 = (a1 + s16(rw(m, (0x1aba2 + s16(rw(m, 0x57fd0))) & 0xffffff))) & 0xffffff
    for _ in range(16):
        x = ((rw(m, 0x57ff6) * 0x24a1) + 0x24df) & 0x1fff
        if x == 0:
            wrap_1ac3c(m, ev, br)
            break
        ww(m, 0x57ff6, x)
        d2 = x >> 4
        if d2 >= 0x120:
            br["pix_skip"] += 1
            continue
        off = d2 * 8
        mask = (0x10001 << (x & 15)) & 0xffffffff
        for o in (0, 4):
            s = rl(m, a1 + off + o)
            d = rl(m, a0 + off + o)
            wl(m, a0 + off + o, (d & ~mask) | (s & mask))
        br["pix_copy"] += 1
    weather_1ad2a(m, br)
    return ev, br

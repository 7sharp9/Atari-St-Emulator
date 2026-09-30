"""drone_model.py - Python reconstruction of Super Sprint's per-car drone update, `$eaea` (+ `$f2dc`/`$f32e`
reached test and `$f3c2` waypoint placement), differential-tested against `callcap` by drone_diff.py.

All state is A4-relative word arrays indexed car*2 (4 slots).  Offsets (proven by the diff test):
  stun -3810   speed -3730   cap -3874   div -3882   hd -3706   thd(target heading) -3714   wp -3802
  turn acc -3866   flags -3826   pos X/Y (x8 fixed point) -3738/-3746   mirrors -3786/-3794
  screen X/Y -3690/-3698   vel target -4010/-4018   vel smoothed -3994/-4002   drift -3978/-3986
  path-distance acc -4026/-4034   crossing-plane target X/Y -3962/-3970
  dirX -4118[16]  dirY -4150[16]  waypoint table ptr -4084 (long)  slot count -4076  branch table -1832[k]
Waypoint record (8 bytes = 4 words): X, Y, d (segment length in units of the heading's direction vector), h
(low nibble = heading; 0x100/0x200/0x400 bits = fork/branch/jump pseudo-records).
"""
import struct

A4 = 0x1EB44


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def trunc_div(a, b):
    """68000 DIVS quotient: truncation toward zero"""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


class Mem:
    """sparse byte memory + overlay of writes; words big-endian, signed accessors"""
    def __init__(s, base):
        s.base = dict(base)
        s.w = {}

    def b(s, a):
        return s.w[a] if a in s.w else s.base[a]

    def rw(s, a):
        return s16((s.b(a) << 8) | s.b(a + 1))

    def rl(s, a):
        return (s.b(a) << 24) | (s.b(a + 1) << 16) | (s.b(a + 2) << 8) | s.b(a + 3)

    def ww(s, a, v):
        v &= 0xFFFF
        s.w[a] = v >> 8
        s.w[a + 1] = v & 0xFF

    def delta(s):
        return {a: (s.base[a], v) for a, v in s.w.items() if s.base[a] != v}


def arr(off, car):
    return A4 + off + 2 * car


def record(m, wp):
    p = m.rl(A4 - 4084) + s16(wp * 8)
    return [m.rw(p), m.rw(p + 2), m.rw(p + 4), m.rw(p + 6)]


def dirx(m, h):
    return m.rw(A4 - 4118 + 2 * (h & 0xFFFF))


def diry(m, h):
    return m.rw(A4 - 4150 + 2 * (h & 0xFFFF))


def reached(m, car):
    """$f2dc: 2 when the car has crossed the plane at the end of its current segment, else 0"""
    thd = m.rw(arr(-3714, car))
    q = ((thd + 2) & 0xF) >> 2
    px, py = m.rw(arr(-3738, car)), m.rw(arr(-3746, car))
    tx, ty = m.rw(arr(-3962, car)), m.rw(arr(-3970, car))
    if q == 0:
        ok = not (py > ty)
    elif q == 1:
        ok = not (px < tx)
    elif q == 2:
        ok = not (py < ty)
    else:
        ok = not (px > tx)
    return 2 if ok else 0


def place(m, car, wp):
    """$f3c2: snap the car to waypoint record `wp` and compute the crossing plane of that segment"""
    rec = record(m, wp)
    m.ww(arr(-3738, car), rec[0])
    m.ww(arr(-3746, car), rec[1])
    h = rec[3] & 0xF
    m.ww(arr(-3714, car), h)
    m.ww(arr(-3978, car), 0)
    m.ww(arr(-3986, car), 0)
    d = rec[2]
    m.ww(arr(-3962, car), m.rw(arr(-3738, car)) + s16(d * dirx(m, h)))
    m.ww(arr(-3970, car), m.rw(arr(-3746, car)) + s16(d * diry(m, h)))
    m.ww(arr(-4026, car), 0)
    m.ww(arr(-4034, car), 0)


def eaea(m, car, trace=None):
    """$eaea(car).  Mutates m (a Mem); `trace` (list) collects branch events for coverage counting."""
    ev = trace.append if trace is not None else (lambda x: None)
    stun = m.rw(arr(-3810, car))
    if stun > 0:
        ev('stun')
        stun -= 1
        m.ww(arr(-3810, car), stun)
        if stun < 0:
            m.ww(arr(-3810, car), 0)
        # $eb32: direct velocity from speed and target heading, LP-filtered, drift bookkeeping, then $f054
        spd = m.rw(arr(-3730, car))
        thd = m.rw(arr(-3714, car))
        m.ww(arr(-4010, car), spd * dirx(m, thd))
        m.ww(arr(-4018, car), spd * diry(m, thd))
        m.ww(arr(-3994, car), trunc_div(s16(m.rw(arr(-3994, car)) + m.rw(arr(-4010, car))), 2))
        m.ww(arr(-4002, car), trunc_div(s16(m.rw(arr(-4002, car)) + m.rw(arr(-4018, car))), 2))
        m.ww(arr(-3978, car), m.rw(arr(-3978, car)) - m.rw(arr(-3994, car)))
        m.ww(arr(-3986, car), m.rw(arr(-3986, car)) - m.rw(arr(-4002, car)))
    else:
        wp = m.rw(arr(-3802, car))
        rec = record(m, wp)
        m.ww(arr(-3714, car), rec[3] & 0xF)
        r = reached(m, car)
        if m.rw(arr(-3730, car)) < m.rw(arr(-3874, car)):
            m.ww(arr(-3730, car), m.rw(arr(-3730, car)) + 2)
        if r == 2:
            ev('reach')
            cnt = m.rw(A4 - 4076)
            wp = trunc_div(m.rw(arr(-3802, car)) + 2, cnt)
            wp = (m.rw(arr(-3802, car)) + 2) - cnt * wp      # remainder (dividend >= 0 in practice)
            m.ww(arr(-3802, car), wp)
            rec = record(m, wp)
            thd = rec[3]
            m.ww(arr(-3714, car), thd)
            if thd == 0x100:
                ev('fork_even' if (car & 1) == 0 else 'fork_odd')
                wp += 3 if (car & 1) == 0 else 2
                m.ww(arr(-3802, car), wp)
            elif thd & 0x200:
                ev('branch')
                idx = thd & 3
                wp += m.rw(A4 - 1832 + 2 * idx)
                m.ww(arr(-3802, car), wp)
            elif thd & 0x400:
                ev('jump')
                wp += thd & 0xFF
                m.ww(arr(-3802, car), wp)
            place(m, car, m.rw(arr(-3802, car)))
        # $ee16: heading follows the target unless a spin-out (turn accumulator) is running
        acc = m.rw(arr(-3866, car))
        if acc > 0 and (m.rw(arr(-3826, car)) & 0x400) == 0:
            ev('spin')
            acc -= 1
            m.ww(arr(-3866, car), acc)
            if acc & 1:
                hd = (m.rw(arr(-3706, car)) + 1) & 0xF
                m.ww(arr(-3706, car), hd)
                if hd == m.rw(arr(-3714, car)):
                    ev('spin_done')
                    m.ww(arr(-3866, car), 0)
                    m.ww(arr(-3826, car), m.rw(arr(-3826, car)) & 0xFFCF)
            else:
                m.ww(arr(-3866, car), acc + 2)
        else:
            m.ww(arr(-3866, car), 0)
            m.ww(arr(-3706, car), m.rw(arr(-3714, car)))
        # $ef14: drift decays 1/20 per frame into the velocity target
        thd = m.rw(arr(-3714, car))
        spd = m.rw(arr(-3730, car))
        a = trunc_div(m.rw(arr(-3978, car)), 20)
        b = trunc_div(m.rw(arr(-3986, car)), 20)
        m.ww(arr(-4010, car), spd * dirx(m, thd) + a)
        m.ww(arr(-4018, car), spd * diry(m, thd) + b)
        m.ww(arr(-3978, car), m.rw(arr(-3978, car)) - a)
        m.ww(arr(-3986, car), m.rw(arr(-3986, car)) - b)
        m.ww(arr(-3994, car), trunc_div(s16(m.rw(arr(-3994, car)) + m.rw(arr(-4010, car))), 2))
        m.ww(arr(-4002, car), trunc_div(s16(m.rw(arr(-4002, car)) + m.rw(arr(-4018, car))), 2))
    # $f054: integrate
    div = m.rw(arr(-3882, car))
    vx, vy = m.rw(arr(-3994, car)), m.rw(arr(-4002, car))
    m.ww(arr(-3738, car), m.rw(arr(-3738, car)) + trunc_div(vx, div))
    m.ww(arr(-3746, car), m.rw(arr(-3746, car)) + trunc_div(vy, div))
    m.ww(arr(-3786, car), m.rw(arr(-3738, car)))
    m.ww(arr(-3794, car), m.rw(arr(-3746, car)))
    m.ww(arr(-3690, car), trunc_div(m.rw(arr(-3738, car)), 8))
    m.ww(arr(-3698, car), trunc_div(m.rw(arr(-3746, car)), 8))
    m.ww(arr(-4026, car), m.rw(arr(-4026, car)) + trunc_div(vx, div))
    m.ww(arr(-4034, car), m.rw(arr(-4034, car)) + trunc_div(vy, div))

"""ssport.py - literal Python transcription of the Super Sprint per-car physics routines.

Every routine works on a `Mem` (a bytearray copy of the 1 MB RAM image, big-endian, 68000 semantics) with A4 = 0x1eb44,
so the result can be diffed byte-for-byte against the emulator (callcap / stepping).  Routines and their addresses:

  b798  surface_sample(car)      track-surface (cell) map sampler, lap-sector/checkpoint/pickup logic, surface effects
  bda4  obstacle_test(car)       footprint x per-heading mask test against the collision window, returns 4-bit code
  14a4a car_window(car)          the sprite blitter's by-product: builds the 12-long collision window at -3682(A4)
  e8e6  carcar()                 car-to-car proximity flags
  e84c  depth_sort()             draw-order sort
  b3fc  crash_start(car)         off-screen / lethal-wall response (flag=2, stun timer)
  e5d6  car_reset(car)           respawn at the last safe position
  d4fa  human_step(car)          joystick car control + integration
  eaea  drone_step(car)          drone car control (waypoint follower) + integration
  df18  frame()                  the per-frame physics loop
Sound/effect-spawning calls (thunks 480/222 sound triggers, $b6f8 dust/skid slots, wrench-pickup effects) are NOT ported;
they are listed in EFFECT_RANGES and excluded from the diffs.
"""
import struct

A4 = 0x1eb44
A5 = 0xa304


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def u16(v):
    return v & 0xffff


class Mem:
    def __init__(s, ram):
        s.b = bytearray(ram)

    def rb(s, a): return s.b[a]
    def wb(s, a, v): s.b[a] = v & 0xff
    def rw(s, a): return (s.b[a] << 8) | s.b[a + 1]
    def rws(s, a): return s16(s.rw(a))
    def ww(s, a, v):
        v &= 0xffff
        s.b[a] = v >> 8
        s.b[a + 1] = v & 0xff
    def rl(s, a): return struct.unpack_from('>I', s.b, a)[0]
    def wl(s, a, v): struct.pack_into('>I', s.b, a, v & 0xffffffff)
    # A4-relative word globals
    def g(s, off): return s.rws(A4 + off)
    def gu(s, off): return s.rw(A4 + off)
    def sg(s, off, v): s.ww(A4 + off, v)
    def gl(s, off): return s.rl(A4 + off)
    # per-car word arrays: off(A4)[car]
    def a(s, off, car): return s.rws(A4 + off + 2 * car)
    def au(s, off, car): return s.rw(A4 + off + 2 * car)
    def sa(s, off, car, v): s.ww(A4 + off + 2 * car, v)
    # byte access to the low/high byte of a per-car word (68k: byte 0 = high byte, byte 1 = low byte)
    def ab(s, off, car, k): return s.rb(A4 + off + 2 * car + k)
    def sab(s, off, car, k, v): s.wb(A4 + off + 2 * car + k, v)


# named per-car arrays (offset from A4)
X, Y, HEAD, TGT = -3690, -3698, -3706, -3714
TURNCNT = -3722          # human steering repeat counter
SPD = -3730
QX, QY = -3738, -3746    # fixed-point (1/8 px) committed position
PX, PY = -3786, -3794    # previous-frame / candidate position
SAFEH, SAFEX, SAFEY = -3770, -3754, -3762   # last safe heading/position
FLAG = -3778             # 0 normal, 1 out of bounds, 2 crashed/removed
WP = -3802
STUN = -3810
BUMP = -3818             # car-car bump cooldown
F1, F2 = -3826, -3834    # state flag words
GATE = -3842             # checkpoint-line counter
SECTOR = -3850           # lap sector progress
LAPPOS = -3858           # human steering table position
TURN = -3866             # heading-turn / spin counter
CAP = -3874
DIV = -3882
MINSPD = -3890
MAXSPD = -3898
LAPS = -3906
ISDRONE = -3914
WRENCH = -3954
WPX, WPY = -3962, -3970
AX, AY = -3978, -3986    # slide accumulators
VX, VY = -3994, -4002    # velocity
VTX, VTY = -4010, -4018  # target velocity
RX, RY = -4026, -4034    # displacement since last waypoint
ORDER = -4042
DIRX, DIRY = -4118, -4150
PROBE = -4566
MASKS = -4406
CODEMAP = -4438
WIN = -3682


def surface_sample(m, car):
    """$b798.  Returns None (the routine has no return value); mutates flags, counters, speed, heading, the map, -4086."""
    d0 = car * 2
    x = m.rw(A4 + X + d0)
    y = m.rw(A4 + Y + d0)
    h = m.rw(A4 + HEAD + d0)
    pr = A4 + PROBE + ((h << 3) & 0xffff)
    d1 = u16(x + m.rw(pr))
    d2 = u16(y + m.rw(pr + 2))
    d4 = u16(x + m.rw(pr + 4))
    d5 = u16(y + m.rw(pr + 6))
    d1 >>= 3
    d4 >>= 3
    d2 &= 0xfff8
    d5 &= 0xfff8
    d1 = u16(d1 + d2)
    d4 = u16(d4 + d5)
    d2 = u16(d2 << 2)
    d5 = u16(d5 << 2)
    d1 = u16(d1 + d2)
    d4 = u16(d4 + d5)
    base = m.rl(A4 - 1910)

    def idx(v):   # 0(A0,D1.w): word index sign-extended
        return s16(v)
    c1 = m.rb(base + idx(d1))
    c2 = m.rb(base + idx(d4))
    d1 &= ~1
    d4 &= ~1
    d7 = d4
    f1 = A4 + F1 + d0          # A1 (word address of flags1[car]); byte0 = high byte
    f2 = A4 + F2 + d0          # A2
    ret = _surface_body(m, car, d0, c1, c2, d1, d7, f1, f2, base)
    return ret


def _bit(m, addr, n):
    return (m.rb(addr) >> n) & 1


def _bset(m, addr, n):
    m.wb(addr, m.rb(addr) | (1 << n))


def _bclr(m, addr, n):
    m.wb(addr, m.rb(addr) & ~(1 << n))


def _surface_body(m, car, d0, c1, c2, d1, d7, f1, f2, base):
    d4 = 0
    d6 = (c1 | c2) & 0xff
    if d6 & 0x80:                                   # b810: bpl not taken
        if _bit(m, f1, 2):                          # F1 & 0x0400 -> b840
            pass
        elif _bit(m, f2 + 1, 7):                    # F2 & 0x0080
            pass
        else:
            _bset(m, f2 + 1, 7)
            g = A4 + GATE + d0
            m.ww(g, m.rw(g) + 1)
    else:
        _bclr(m, f2 + 1, 7)                         # b83a
    d6 &= 0x7f                                      # b840
    if d6 == 0:
        m.ww(f2, m.rw(f2) & 0x80)                   # b848: F2 &= 0x80, then jmp bd22
        return _tail(m, car, d0, f1, 0)
    d2c = c1 & 0x7f                                 # b852: bclr #7,D2 / D5
    d5c = c2 & 0x7f
    d6 = d2c
    d2 = d7                                         # index of cell 2 (bit 0 cleared)
    for it in (0, 1):                               # moveq #1,D3 ; dbf D3
        if d6 != 0:
            r = _cell(m, car, d0, d6, d1, f1, f2, base)
            if r == 'EXIT':                         # jmp bd22
                break
            if r is not None:
                d4 = r
        d6 = d5c                                    # bd1a
        d1 = d2
    return _tail(m, car, d0, f1, d4)


COV = {}          # (kind, payload) -> times executed; filled by the tests to show branch coverage


def _cell(m, car, d0, d6, d1, f1, f2, base):
    """one iteration body of b798 for cell byte d6 (bit 7 stripped, nonzero).
    Returns a new D4 value, 'EXIT' (jump straight to bd22) or None (D4 untouched, next iteration)."""
    d7 = d6 & 3
    d1s = s16(d1)
    COV[(d7, d6 >> 2)] = COV.get((d7, d6 >> 2), 0) + 1
    if d7 != 0:
        if _bit(m, f1, 2):           # b87a: btst #2,0(A1,D0) -> bd1a
            return None
        if d7 == 3:
            return _kind3(m, car, d0, d6, f1)
        if d7 == 2:
            return _kind2(m, car, d0, d6, f2)
        return _kind1(m, car, d0, d6, d1s, base)
    p = (d6 >> 2) & 0x3f                             # b89c: lsr.b #2,D6
    h = m.rw(A4 + HEAD + d0)
    spd = A4 + SPD + d0
    if p == 1:
        if _bit(m, f2, 7):
            return None
        _bset(m, f2, 7)
        m.ww(f1, m.rw(f1) | 0x8001)
        return None
    if p == 2:
        if _bit(m, f2, 1):
            return None
        _bset(m, f2, 1)
        m.ww(f2, m.rw(f2) & 0xcffe)
        m.ww(f1, m.rw(f1) & 0xc9be)
        return None
    if p in (4, 8):
        _bclr(m, f2, 3)
        _bclr(m, f1, 3)
        if _bit(m, f2, 2):
            return None
        if _bit(m, f1, 2):                           # bac2
            _bset(m, f2, 3)
            _bset(m, f1, 3)
            return None
        if not _bit(m, f1 + 1, 0):
            return None
        if p == 4 and not (h & 8):
            return None
        if p == 8 and (h & 8):
            return None
        _bset(m, f2, 2)
        _bset(m, f1, 2)
        m.ww(A4 + LAPPOS + d0, 0 if p == 4 else 8)
        m.ww(A4 + TURN + d0, 0)
        if s16(m.rw(spd)) <= 0xf:
            m.ww(spd, 0xf)
        return 'EXIT'
    if p == 9:
        _bclr(m, f2, 3)
        _bclr(m, f1, 3)
        if _bit(m, f2, 2) or _bit(m, f1, 2):
            return None
        if h != 0xc:
            return None
        _bset(m, f2, 2)
        m.ww(f1, m.rw(f1) | 0x0401)
        m.ww(A4 + LAPPOS + d0, 0x10)
        m.ww(A4 + TURN + d0, 0)
        return 'EXIT'
    if p == 6:
        if _bit(m, f2 + 1, 6):
            return None
        _bset(m, f2 + 1, 6)
        m.ww(f1, m.rw(f1) | 0x40)
        if h == 0xc:                                   # ($ba70 / $ba94 compare blocks for 11 and 5 are unreachable)
            m.ww(A4 + HEAD + d0, 0xd)
        elif h == 4:
            m.ww(A4 + HEAD + d0, 3)
        return None
    if p == 3:
        if _bit(m, f2, 3) or not _bit(m, f1, 2):
            return None
        _bset(m, f2, 3)
        _bset(m, f1, 3)
        return None
    if p == 5:
        if _bit(m, f2, 4):
            return None
        _bset(m, f2, 4)
        _bset(m, f1, 4)
        return None
    if p == 7:
        if _bit(m, f2, 5):
            return None
        _bset(m, f2, 5)
        _bset(m, f1, 5)
        return None
    return None


def _kind1(m, car, d0, d6, d1s, base):
    p = (d6 >> 2) & 0x3f
    f1 = A4 + F1 + d0
    f2 = A4 + F2 + d0
    spd = A4 + SPD + d0
    if p in (1, 2):
        bit = 4 if p == 1 else 5
        if _bit(m, f2 + 1, bit) or _bit(m, f1 + 1, bit):
            return None
        _bset(m, f2 + 1, bit)
        _bset(m, f1 + 1, bit)
        if p == 2:
            m.ww(spd, s16(m.rw(spd)) >> 1)           # asr.w (mem)
        if s16(m.rw(spd)) <= 0xa:
            m.ww(spd, 0xa)
        m.ww(A4 + TURN + d0, 0x20)
        return 3 if p == 1 else 2
    if p == 0:
        if _bit(m, f2 + 1, 3):
            return None
        _bset(m, f2 + 1, 3)
        m.ww(spd, s16(m.rw(spd)) >> 1)
        return 2
    if p == 3:
        if m.gu(-1856) != 0:
            return None
        m.ww(A4 + WRENCH + d0, m.rw(A4 + WRENCH + d0) + 1)
        m.sg(-1856, (d0 >> 1) + 1)
        m.ww(base + d1s, m.rw(base + d1s) & 0x8080)
        return None
    if p == 4:
        if m.gu(-1846) != 0:
            return None
        m.sg(-1846, (d0 >> 1) + 1)
        m.ww(base + d1s, m.rw(base + d1s) & 0x8080)
        return None
    if 5 <= p <= 8:
        m.sg(-1774 + 2 * (p - 5), 2)
        m.ww(spd, 0)
        m.ww(base + d1s, m.rw(base + d1s) & 0x8080)
        return 4
    return None


def _kind2(m, car, d0, d6, f2):
    p = (d6 >> 2) & 0x3f
    if _bit(m, f2, 0):
        return None
    _bset(m, f2, 0)
    sec = A4 + SECTOR + d0
    d7 = u16(m.rw(sec) + 1)
    p &= 7
    if d7 != p:
        return None
    if p == 4:
        laps = A4 + LAPS + d0
        d7 = (d0 << 2) & 0xffff
        m.ww(laps, m.rw(laps) & 3)
        d7 = u16(d7 + m.rw(laps))
        d7 = u16(d7 + m.rw(laps))
        m.ww(laps, m.rw(laps) + 1)
        m.ww(A4 - 3946 + d7, m.gu(-8072))
        d7 = 0
    m.ww(sec, d7)
    m.ww(A4 + GATE + d0, 0)
    return None


def _kind3(m, car, d0, d6, f1):
    lowf1 = _bit(m, f1 + 1, 0)
    if d6 & 4:
        if not lowf1:
            return None
        m.sg(-4086, (d6 >> 3) & 0xf)
        return 1
    if d6 & 8:
        return 1
    if not lowf1:
        return None
    m.sg(-4086, 0x80)
    return 1


def _tail(m, car, d0, f1, d4):
    if _bit(m, f1 + 1, 0) and d4 == 0:              # bd22
        m.sg(-4086, 0xff)
    # d4 in (2,3,4): sound triggers ($a608/$a62c) and, for 4, the $b6f8 effect: not ported
    return d4


def ror32(v, n):
    n &= 31
    v &= 0xffffffff
    return ((v >> n) | (v << (32 - n))) & 0xffffffff if n else v


def car_window(m, car):
    """$14a4a: sprite blit; the part that matters for physics is the collision window at -3682(A4):
    12 longs = (opaque sprite pixels) AND (collision plane 1), rotated to the car's x&15, unless the car is airborne (F1&0x400)."""
    d0 = car * 2
    f1 = m.rw(A4 + F1 + d0)
    mode = (0x80 if f1 & 0x400 else 0) | (f1 & 1)
    # clear the window
    for i in range(12):
        m.wl(A4 + WIN + 4 * i, 0)
    a1 = m.rl(A4 - 94)
    a2 = m.rl(A4 - 3602)
    x = m.rw(A4 + X + d0)
    y = m.rw(A4 + Y + d0)
    d3 = ((d0 << 3) + m.rw(A4 + HEAD + d0)) & 0xffff
    if m.rw(A4 + ISDRONE + d0) != 0:
        d3 += 0x40
    a2 += (d3 << 8) & 0xffff
    d0b = ((x & 0xfff0) >> 1)
    d2 = ((y * 5) & 0xffff)
    d2 = (d2 << 5) & 0xffff
    d0b = (d0b + d2) & 0xffff
    a1 += d0b >> 2
    sh = x & 0xf
    out = []
    for row in range(12):
        d3_, d4_, d5_, d6_ = (m.rl(a2 + 4 * k) for k in range(4))
        a2 += 16
        d3_, d4_, d5_, d6_ = (ror32(v, sh) for v in (d3_, d4_, d5_, d6_))
        d2m = ((~d6_) | d3_ | d4_ | d5_) & 0xffffffff
        if not (mode & 0x80):
            w = d2m & m.rl(a1 + 8000)
            m.wl(A4 + WIN + 4 * row, w)
        a1 += 40
    return None


def obstacle_test(m, car):
    """$bda4: returns the 4-bit blocked code (bit0 = row off1 hit, bit1 = row off2 hit, bit2 = left-column mask hit, bit3 = right-column mask hit)."""
    d2 = (car << 1) & 7
    x = m.rw(A4 + X + d2)
    d4 = x & 0xf
    h = m.rw(A4 + HEAD + d2) & 0xf
    ent = A4 + MASKS + (h << 4)
    off1, off2, m1, m2 = (m.rl(ent + 4 * k) for k in range(4))
    win = A4 + WIN
    d1 = 0
    if m.rl(win + off1) != 0:
        d1 |= 1
    n = (off2 - off1) >> 2
    if m.rl(win + off2) != 0:
        d1 |= 2
    m1s = m1 >> d4
    m2s = m2 >> d4
    a0 = win + off1
    for _ in range(n):
        w = m.rl(a0)
        if m1s & w:
            d1 |= 4
        if m2s & w:
            d1 |= 8
        a0 += 4
    return d1


# ---------------------------------------------------------------------------------------------------------------------
# helpers with 68000 signed-division semantics (divs: quotient truncated toward zero, low word stored)

def divs(a, b):
    """68000 DIVS.W: 32-bit signed dividend / 16-bit signed divisor, quotient truncated toward zero (16-bit result)."""
    a = a if -0x80000000 <= a < 0x80000000 else ((a + 0x80000000) & 0xffffffff) - 0x80000000
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


def divs_rem(a, b):
    q = divs(a, b)
    return a - q * b


def depth_sort(m):
    """$e84c: order[0..3] = cars ascending by (y + 0xff if F1&1)."""
    ys = []
    for c in range(4):
        y = m.a(Y, c)
        if m.au(F1, c) & 1:
            y = s16(y + 0xff)
        ys.append((y, c))
    # bubble sort exactly like the asm (compare adjacent, swap when D1 < D0)
    v = [list(t) for t in ys]
    while True:
        sw = False
        for i in range(3):
            if v[i + 1][0] < v[i][0]:
                v[i], v[i + 1] = v[i + 1], v[i]
                sw = True
        if not sw:
            break
    for i in range(4):
        m.sa(ORDER, i, v[i][1])


def _pair(m, i, j):
    f = lambda c: m.au(F1, c)
    if f(i) & 0x440 or f(j) & 0x440:
        return
    if abs(m.a(X, i) - m.a(X, j)) > 7:
        return
    if abs(m.a(Y, i) - m.a(Y, j)) > 7:
        return
    if (f(j) & 1) != (f(i) & 1):
        return
    hi, hj = m.a(HEAD, i), m.a(HEAD, j)
    if hi == hj:
        return
    d = abs(hj - hi)
    if 5 <= d <= 11:
        if d < 7 or d > 9:
            return
        if m.a(SPD, i) < 0x3c or m.a(SPD, j) < 0x3c:
            return
        if m.a(TURN, i) == 0:
            m.sa(TURN, i, 0x20)
        if m.a(TURN, j) == 0:
            m.sa(TURN, j, 0x20)
        return
    m.sa(F1, j, m.au(F1, j) | ((i << 2) | 2))
    m.sa(F1, i, m.au(F1, i) | ((j << 2) | 2))


def carcar(m):
    """$e8e6"""
    for c in range(4):
        m.sa(F1, c, m.au(F1, c) & 0xfff1)
    for (i, j) in ((0, 1), (0, 2), (0, 3), (1, 3), (2, 3), (2, 1)):
        _pair(m, i, j)


def crash_start(m, car):
    """$b3fc: car removed from play (flag 2); stun timer = frames until the pickup animation finishes; starts the
    -1896.. 'pickup vehicle' animation state when idle."""
    if m.a(FLAG, car) == 2:
        return
    m.sa(FLAG, car, 2)
    m.sa(TURN, car, 0)
    c2 = 1
    c4 = 1
    d6 = m.a(SAFEX, car) >> 3
    if d6 < 0xa0:
        d6 = 0x140 - d6
        c2 = 0
    d8 = m.a(SAFEY, car) >> 3
    if d8 < 0x64:
        d8 = 0xc8 - d8
        c4 = 0
    if (d6 >> 1) > d8:
        c4 = 2 + c2
    else:
        d6 = d8 << 1
    m.sa(STUN, car, d6 >> 2)
    if m.g(-1896) != 0:
        return
    m.sg(-1902, 3 if m.au(ISDRONE, car) else car)
    m.sg(-1898, c4)
    m.sg(-1896, -1)
    m.sg(-1894, 0)
    if m.g(-1898) & 2:
        v = (m.a(SAFEY, car) >> 3) - 8
        if v < 0:
            v = 0
        elif v > 0xae:
            v = 0xae
        m.sg(-1892, v)
        m.sg(-1890, 0x13f if m.g(-1898) == 2 else 0xffd9)
        m.sg(-1900, 0x58)
    else:
        v = (m.a(SAFEX, car) >> 3) - 8
        if v < 0:
            v = 0
        elif v > 0x120:
            v = 0x120
        m.sg(-1890, v & 0xfff0)
        m.sg(-1892, 0xc7 if m.g(-1898) == 0 else 0xffdd)
        m.sg(-1900, 0x74)


def car_reset(m, car):
    """$e5d6"""
    m.sa(SPD, car, 0)
    m.sa(F1, car, m.au(F1, car) & 0x3180)
    m.sa(HEAD, car, m.a(SAFEH, car))
    v = m.a(SAFEX, car)
    m.sa(PX, car, v)
    m.sa(QX, car, v)
    m.sa(X, car, divs(v, 8))
    v = m.a(SAFEY, car)
    m.sa(PY, car, v)
    m.sa(QY, car, v)
    m.sa(Y, car, divs(v, 8))
    for off in (FLAG, BUMP, STUN, TURN, LAPPOS, VTY, VTX, VY, VX):
        m.sa(off, car, 0)


def _integrate(m, car):
    d = m.a(DIV, car)
    m.sa(QX, car, m.a(QX, car) + divs(m.a(VX, car), d))
    m.sa(QY, car, m.a(QY, car) + divs(m.a(VY, car), d))
    m.sa(X, car, divs(m.a(QX, car), 8))
    m.sa(Y, car, divs(m.a(QY, car), 8))


def _blend(m, car):
    m.sa(VX, car, divs(m.a(VTX, car) + m.a(VX, car), 2))
    m.sa(VY, car, divs(m.a(VTY, car) + m.a(VY, car), 2))


def human_step(m, car, inp):
    """$d4fa with the joystick byte supplied (the game reads it via $105a0(-4810(A4)[car]))."""
    inp &= 0xff
    if m.a(STUN, car) != 0:
        m.sa(STUN, car, m.a(STUN, car) - 1)
        inp = 0
    spd = lambda: m.a(SPD, car)
    if m.au(F1, car) & 0x400:                                       # airborne / scripted flight
        m.sa(SPD, car, spd() + 1)
        if spd() > m.a(MAXSPD, car):
            m.sa(SPD, car, m.a(MAXSPD, car))
        if m.a(TURN, car) == 0:
            h = (m.a(HEAD, car) + m.g(-8392 + 2 * m.a(LAPPOS, car))) & 15
            m.sa(HEAD, car, h)
            m.sa(TGT, car, h)
        if (m.a(LAPPOS, car) & 7) > 2:
            inp = 0
        else:
            inp &= 0x80
        m.sa(TURN, car, m.a(TURN, car) + 1)
        if m.a(TURN, car) == m.g(-8346 + 2 * m.a(LAPPOS, car)):
            m.sa(TURN, car, 0)
            m.sa(LAPPOS, car, m.a(LAPPOS, car) + 1)
            if m.g(-8346 + 2 * m.a(LAPPOS, car)) == 0:
                if m.au(F1, car) & 0x800:
                    pass                                              # $b6f8 landing effect + sound: not ported
                else:
                    m.sa(FLAG, car, 1)
                m.sa(F1, car, m.au(F1, car) & 0xf3ff)
    elif m.a(TURN, car) > 0:                                        # spin-out
        m.sa(TURN, car, m.a(TURN, car) - 1)
        m.sa(SPD, car, spd() + 1)
        if spd() < 10:
            m.sa(SPD, car, 10)
        inp = 0
        if m.a(TURN, car) == 0:
            m.sa(F1, car, m.au(F1, car) & 0xffcf)
        elif m.a(TURN, car) & 1:
            m.sa(HEAD, car, (m.a(HEAD, car) + 1) & 15)
    f1 = m.au(F1, car)
    if f1 & 0x1400:
        ph = 0x80
    elif f1 & 0x40:
        ph = 0
    else:
        ph = 1
    d = m.a(DIV, car)
    if spd() < m.a(MINSPD, car):
        thr = 5 - divs(spd(), d)
    else:
        thr = 5 + divs(spd(), d) - 2
    if m.au(F1, car) & 0x2000:
        thr -= 1
    if thr < 1:
        thr = 1
    fire = (inp & 0x80) == 0x80
    if (inp & 8) == 8:
        if m.a(TURNCNT, car) >= thr and spd() >= 0:
            m.sa(TGT, car, m.a(HEAD, car))
            m.sa(HEAD, car, (m.a(HEAD, car) + 1) & 15)
            m.sa(TURNCNT, car, 0)
            if fire:
                m.sa(SPD, car, spd() - thr)
        else:
            m.sa(TURNCNT, car, m.a(TURNCNT, car) + 1)
    elif (inp & 4) == 4:
        if m.a(TURNCNT, car) <= 0 and spd() >= 0:
            m.sa(TGT, car, m.a(HEAD, car))
            m.sa(HEAD, car, (m.a(HEAD, car) + 15) & 15)
            m.sa(TURNCNT, car, thr)
            if fire:
                m.sa(SPD, car, spd() - thr)
        else:
            m.sa(TURNCNT, car, m.a(TURNCNT, car) - 1)
    elif m.a(TURN, car) == 0 and ph < 2 and (m.a(HEAD, car) & 1) == ph and spd() < divs(d * 11, 4):
        if m.a(TURNCNT, car) <= divs(thr, 2):
            m.sa(TURNCNT, car, m.a(TURNCNT, car) - 1)
            if m.a(TURNCNT, car) <= 0:
                m.sa(TURNCNT, car, thr)
                m.sa(HEAD, car, (m.a(HEAD, car) + 15) & 15)
        else:
            m.sa(TURNCNT, car, m.a(TURNCNT, car) + 1)
            if m.a(TURNCNT, car) >= thr:
                m.sa(TURNCNT, car, 0)
                m.sa(HEAD, car, (m.a(HEAD, car) + 1) & 15)
    if fire:
        if spd() < m.a(CAP, car):
            m.sa(SPD, car, spd() + 2)
        else:
            m.sa(SPD, car, m.a(CAP, car))
        h = m.a(HEAD, car)
        m.sa(VTX, car, spd() * m.g(DIRX + 2 * h))
        m.sa(VTY, car, spd() * m.g(DIRY + 2 * h))
        m.sa(TGT, car, h)
    else:
        if spd() > 0:
            fr = m.gu(-8478)
            sel1 = m.g(-4070 + 8 * car)
            if m.g(-8476 + sel1 * 14 + 2 * fr) == 0:
                m.sa(SPD, car, spd() - 1)
            sel2 = m.g(-4074 + 8 * car)
            if m.g(-8476 + sel2 * 14 + 2 * fr) != 0:
                m.sa(SPD, car, spd() - 1)
            if spd() < 0:
                m.sa(SPD, car, 0)
        t = m.a(TGT, car)
        m.sa(VTX, car, spd() * m.g(DIRX + 2 * t))
        m.sa(VTY, car, spd() * m.g(DIRY + 2 * t))
    m.sa(PX, car, m.a(QX, car))
    m.sa(PY, car, m.a(QY, car))
    _blend(m, car)
    _integrate(m, car)


def waypoint_load(m, car, wp):
    """$f3c2: snap the car onto waypoint wp and set the plane it must cross next."""
    tbl = m.gl(-4084)
    rec = tbl + wp * 8
    m.sa(QX, car, m.rws(rec))
    m.sa(QY, car, m.rws(rec + 2))
    t = m.rw(rec + 6) & 0xf
    m.sa(TGT, car, t)
    m.sa(AX, car, 0)
    m.sa(AY, car, 0)
    hint = m.rws(rec + 4)
    m.sa(WPX, car, m.a(QX, car) + s16(hint * m.g(DIRX + 2 * t)))
    m.sa(WPY, car, m.a(QY, car) + s16(hint * m.g(DIRY + 2 * t)))
    m.sa(RX, car, 0)
    m.sa(RY, car, 0)


def reached(m, car):
    """$f2dc: 2 if the car has crossed the waypoint plane, else 0."""
    q = ((m.a(TGT, car) + 2) & 15) >> 2
    qx, qy = m.a(QX, car), m.a(QY, car)
    wx, wy = m.a(WPX, car), m.a(WPY, car)
    if q == 0:
        ok = not (qy > wy)
    elif q == 1:
        ok = not (qx < wx)
    elif q == 2:
        ok = not (qy < wy)
    else:
        ok = not (qx > wx)
    return 2 if ok else 0


def drone_step(m, car):
    """$eaea"""
    if m.a(STUN, car) > 0:
        m.sa(STUN, car, m.a(STUN, car) - 1)
        if m.a(STUN, car) < 0:
            m.sa(STUN, car, 0)
        t = m.a(TGT, car)
        s = m.a(SPD, car)
        m.sa(VTX, car, s * m.g(DIRX + 2 * t))
        m.sa(VTY, car, s * m.g(DIRY + 2 * t))
        m.sa(VX, car, divs(m.a(VX, car) + m.a(VTX, car), 2))
        m.sa(VY, car, divs(m.a(VY, car) + m.a(VTY, car), 2))
        m.sa(AX, car, m.a(AX, car) - m.a(VX, car))
        m.sa(AY, car, m.a(AY, car) - m.a(VY, car))
    else:
        tbl = m.gl(-4084)
        wp = m.a(WP, car)
        m.sa(TGT, car, m.rw(tbl + wp * 8 + 6) & 0xf)
        r = reached(m, car)
        if m.a(SPD, car) < m.a(CAP, car):
            m.sa(SPD, car, m.a(SPD, car) + 2)
        if r == 2:
            cnt = m.g(-4076)
            wp = divs_rem(wp + 2, cnt)
            m.sa(WP, car, wp)
            t = m.rw(tbl + wp * 8 + 6)
            m.sa(TGT, car, t)
            if t == 0x100:
                m.sa(WP, car, wp + (2 if car & 1 else 3))
            elif t & 0x200:
                m.sa(WP, car, wp + m.g(-1832 + 2 * (t & 3)))
            elif t & 0x400:
                m.sa(WP, car, wp + (t & 0xff))
            waypoint_load(m, car, m.a(WP, car))
        if m.a(TURN, car) > 0 and not (m.au(F1, car) & 0x400):
            m.sa(TURN, car, m.a(TURN, car) - 1)
            if m.a(TURN, car) & 1:
                m.sa(HEAD, car, (m.a(HEAD, car) + 1) & 15)
                if m.a(HEAD, car) == m.a(TGT, car):
                    m.sa(TURN, car, 0)
                    m.sa(F1, car, m.au(F1, car) & 0xffcf)
            else:
                m.sa(TURN, car, m.a(TURN, car) + 2)
        else:
            m.sa(TURN, car, 0)
            m.sa(HEAD, car, m.a(TGT, car))
        axd = divs(m.a(AX, car), 20)
        ayd = divs(m.a(AY, car), 20)
        t = m.a(TGT, car)
        s = m.a(SPD, car)
        m.sa(VTX, car, s * m.g(DIRX + 2 * t) + axd)
        m.sa(VTY, car, s * m.g(DIRY + 2 * t) + ayd)
        m.sa(AX, car, m.a(AX, car) - axd)
        m.sa(AY, car, m.a(AY, car) - ayd)
        _blend(m, car)
    # f054
    d = m.a(DIV, car)
    dx = divs(m.a(VX, car), d)
    m.sa(QX, car, m.a(QX, car) + dx)
    dy = divs(m.a(VY, car), d)
    m.sa(QY, car, m.a(QY, car) + dy)
    m.sa(PX, car, m.a(QX, car))
    m.sa(PY, car, m.a(QY, car))
    m.sa(X, car, divs(m.a(QX, car), 8))
    m.sa(Y, car, divs(m.a(QY, car), 8))
    m.sa(RX, car, m.a(RX, car) + divs(m.a(VX, car), d))
    m.sa(RY, car, m.a(RY, car) + divs(m.a(VY, car), d))


def hazard_touch(m):
    """$ea56 (only when -1776(A4) != 0): a car touching the roaming hazard object at (-1780, -1782+12) is set spinning."""
    for car in range(4):
        if m.au(F1, car) & 0x440:
            continue
        if abs(m.a(X, car) - m.g(-1780)) > 7:
            continue
        if abs(m.a(Y, car) - (m.g(-1782) + 0xc)) > 8:
            continue
        if m.a(TURN, car) != 0:
            continue
        m.sa(TURN, car, 0x1c)
        m.sa(F1, car, m.au(F1, car) | 0x10)
        if m.g(-8068) != 0:
            # the sound trigger ($ea32 -> $1271c) clobbers A0 (and D0/D1), which $ea86 reuses for the next car's X[]:
            # with sound on the later cars read garbage and (in practice) never match, so the roaming hazard spins at most one car per frame
            break


def render_step(m, car):
    """$149b8 (the physics-relevant part): crashed cars count their stun down and respawn; live cars build the collision window."""
    if m.a(FLAG, car) != 0:
        m.sa(STUN, car, m.a(STUN, car) - 1)
        if m.a(STUN, car) == 0:
            car_reset(m, car)
        else:
            t = m.a(TURN, car)
            if t < 0x67:
                m.sa(TURN, car, m.a(TURN, car) + 1)
    if m.a(FLAG, car) == 0:
        car_window(m, car)


def frame(m):
    """$df18: one frame of the car physics loop (control routines d4fa/eaea have already run)."""
    fr = (m.gu(-8478) + 1) & 0xffff
    m.sg(-8478, 0 if fr == 7 else fr)
    if m.g(-1776) != 0:
        hazard_touch(m)
    carcar(m)
    depth_sort(m)
    for i in range(4):
        car = m.au(ORDER, i)
        x, y = m.a(X, car), m.a(Y, car)
        if x <= 1 or x >= 0x12e or y <= 1 or y >= 0xba:
            m.sa(FLAG, car, 1)
        if m.a(FLAG, car) == 1:
            m.sa(QX, car, m.a(PX, car))
            m.sa(X, car, divs(m.a(PX, car), 8))
            m.sa(QY, car, m.a(PY, car))
            m.sa(Y, car, divs(m.a(PY, car), 8))
            crash_start(m, car)
        render_step(m, car)
        if m.a(FLAG, car) == 0:
            code = obstacle_test(m, car)
            m.sg(-4086, m.g(CODEMAP + 2 * code))
            surface_sample(m, car)
        v = m.g(-4086)
        crash = False
        if v == 0x80:
            crash = True
        elif v == ((m.a(HEAD, car) + 8) & 15) and m.a(SPD, car) == m.a(CAP, car):
            crash = True
        elif m.a(FLAG, car) == 1:
            crash = True
        if crash:
            crash_start(m, car)
        else:
            if v != 0xff and m.a(STUN, car) == 0 and m.a(FLAG, car) == 0:
                m.sa(QX, car, m.a(PX, car))
                m.sa(QY, car, m.a(PY, car))
                m.sa(TGT, car, v & 15)
                t = 10 + m.a(SPD, car)
                m.sa(VX, car, 2 * t * m.g(DIRX + 2 * v))
                m.sa(VY, car, 2 * t * m.g(DIRY + 2 * v))
                m.sa(SPD, car, divs(m.a(SPD, car), 4) + divs(m.a(DIV, car), 2))
                m.sa(STUN, car, 5 if m.au(ISDRONE, car) else 10)
                # $b6f8 effect + sound: not ported
            elif m.a(STUN, car) == 0 and (m.au(F1, car) & 0x41) == 0 and m.a(FLAG, car) == 0:
                m.sa(SAFEH, car, m.a(HEAD, car))
                m.sa(SAFEX, car, m.a(QX, car))
                m.sa(SAFEY, car, m.a(QY, car))
            elif m.au(ISDRONE, car) != 0:
                m.sa(SAFEH, car, m.a(HEAD, car))
                m.sa(SAFEX, car, m.a(QX, car))
                m.sa(SAFEY, car, m.a(QY, car))
        # e3c0
        if m.a(BUMP, car) > 0:
            m.sa(BUMP, car, m.a(BUMP, car) - 1)
        if m.a(BUMP, car) == 0 and (m.au(F1, car) & 2) and m.a(FLAG, car) == 0:
            m.sa(F1, car, m.au(F1, car) & 0xfffd)
            o = (m.a(F1, car) >> 2) & 3
            v = m.a(HEAD, o)
            m.sg(-4086, v)
            m.sa(BUMP, car, 0x19)
            m.sa(TGT, car, v)
            d = m.a(DIV, car)
            m.sa(VX, car, divs(11 * d * m.g(DIRX + 2 * v), 2))
            m.sa(VY, car, divs(11 * d * m.g(DIRY + 2 * v), 2))
            m.sa(AX, car, m.a(AX, car) - m.a(VX, car))
            m.sa(AY, car, m.a(AY, car) - m.a(VY, car))
            m.sa(SPD, car, divs(m.a(SPD, car) * 3, 4))
            m.sa(QX, car, m.a(PX, car))
            m.sa(QY, car, m.a(PY, car))
    m.sg(-4086, 0xff)


def read_input(m, car):
    """$105a0(-4810(A4)[car]): the joystick byte for input channel n (0 keyboard synth, 2 joystick 0, 3 joystick 1)."""
    ch = m.a(-4810, car)
    if ch == 0:
        kt = A4 - 4802
        b = lambda o: m.rb(kt + o)
        left = ((b(30) | b(44) | b(38)) & 1) << 2
        right = ((b(32) | b(45) | b(40)) & 1) << 3
        d0 = left | right
        if (b(42) | b(54) | b(56)) & 1:
            d0 |= 0x80
        return d0
    if ch == 2:
        return m.rb(A4 - 4804)
    if ch == 3:
        return m.rb(A4 - 4803)
    return 0


def control_phase(m):
    """the per-car control step of the race loop ($c7e0..$c844): cars with FLAG==0 run $d4fa (human, -3914==0) or $eaea (drone)."""
    for car in range(4):
        if m.a(FLAG, car) == 0:
            if m.au(ISDRONE, car) == 0:
                human_step(m, car, read_input(m, car))
            else:
                drone_step(m, car)


def next_boundary(m):
    """advance a df18-entry state to the next df18-entry state: df18 (this frame), the page flip's frame counter (-8072 += 1),
    then the next frame's control phase."""
    frame(m)
    m.sg(-8072, m.gu(-8072) + 1)
    control_phase(m)

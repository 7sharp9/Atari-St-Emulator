"""Python reconstructions of the Starglider flight code, one function per routine, each written from the 68000 body
(addresses in the docstrings). They work on `Mem`, a sparse big-endian RAM image, and mutate it as the routine does;
the gates compare the result with the emulator's memory after a real `call` of the routine."""

def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v

def s8(v):
    v &= 0xff
    return v - 0x100 if v & 0x80 else v


class Mem:
    """Regions {base: bytearray}; every access is big-endian and lands in one region."""
    def __init__(self, regions):
        self.r = {b: bytearray(d) for b, d in regions.items()}

    def _reg(self, a, n):
        for b, d in self.r.items():
            if b <= a and a + n <= b + len(d):
                return d, a - b
        raise KeyError(f'${a:x} outside the model image')

    def u8(self, a):
        d, o = self._reg(a, 1); return d[o]

    def w(self, a):                # unsigned word
        d, o = self._reg(a, 2); return (d[o] << 8) | d[o + 1]

    def sw(self, a):
        return s16(self.w(a))

    def l(self, a):
        d, o = self._reg(a, 4); return int.from_bytes(d[o:o + 4], 'big')

    def set8(self, a, v):
        d, o = self._reg(a, 1); d[o] = v & 0xff

    def setw(self, a, v):
        d, o = self._reg(a, 2); d[o] = (v >> 8) & 0xff; d[o + 1] = v & 0xff

    def setl(self, a, v):
        d, o = self._reg(a, 4); d[o:o + 4] = (v & 0xffffffff).to_bytes(4, 'big')

    def blob(self):
        return {b: bytes(d) for b, d in self.r.items()}


G = 0x5bf00
SX, SY, SD = 0xc3ce, 0xc3d0, 0xc3d4      # stick x, stick y, throttle accumulators (the ISR and $d29a write them)


def mulhi(a, b):
    """`muls b,Da ; asl.l #1,Da ; swap Da` taken as the low word of the result: the high word of 2*a*b (wrapping 32 bits)."""
    p = (s16(a) * s16(b)) & 0xffffffff
    p = (p << 1) & 0xffffffff
    return (p >> 16) & 0xffff


def sincos(m, ang, sin_slot, cos_slot):
    """The idiom `andi #$fff ; asl #1 ; word at 108(A6)+i -> sin, 112(A6)+i -> cos`."""
    i = ((ang & 0xfff) << 1)
    return m.w(m.l(G + 108) + i), m.w(m.l(G + 112) + i)


def flight_step(m):
    """$12340: one frame of the craft's motion and stick-to-attitude mapping (called once per main-loop pass from
    $caa4). Returns the list of calls it would make ('f320', 'ac9c') when the missile-camera timer expires."""
    calls = []
    A = lambda o: G + o
    # -- position += speed * (sin, cos)(heading)
    spd = m.w(A(542))
    sn, cs = sincos(m, m.w(A(316)), 108, 112)
    m.setw(A(462), sn); m.setw(A(464), cs)
    d4 = mulhi(spd, sn); d5 = mulhi(spd, cs)
    m.setw(A(320), d4); m.setw(A(324), d5)
    if not m.u8(A(712)):
        m.setw(A(302), m.w(A(302)) + d4)
        m.setw(A(306), m.w(A(306)) + d5)
    # -- stick x: clamp to +-$1f0, bank = -(stick_x >> 4)
    d0 = m.sw(SX)
    if d0 > 0x1f0:
        m.setw(SX, 0x1f0)
    elif d0 < -0x1f0:
        m.setw(SX, 0xfe10)
    m.setw(A(318), -(m.sw(SX) >> 4))
    # -- stick y: clamp to +-$140; dead zone +-$30; climb rate = -(stick_y >> 4)
    d0 = m.sw(SY)
    if d0 > 0x140:
        m.setw(SY, 0x140)
    elif d0 < -0x140:
        m.setw(SY, 0xfec0)
    d0 = m.sw(SY)
    if -0x30 <= d0 <= 0x30:
        d0 = 0
    m.setw(A(570), -(d0 >> 4))
    if not m.u8(A(712)):
        # -- throttle accumulator: clamp to [-$1df, 0]; docked/launch override; speed = -throttle
        d0 = m.sw(SD)
        if d0 <= -0x1df:
            m.setw(SD, 0xfe21)
        elif d0 > 0:
            m.setw(SD, 0)
        if m.u8(A(714)):
            m.setw(SD, 0 if m.w(A(658)) == 0x1e else 0xfff6)
        m.setw(A(542), -m.sw(SD))
        if not m.u8(A(714)):
            m.setw(A(316), m.w(A(316)) - m.w(A(318)))
            m.setw(A(304), m.w(A(304)) + m.w(A(570)))
        # -- bank offset (640) is added to the roll word and decays by 2
        m.setw(A(318), m.w(A(318)) + m.w(A(640)))
        v = m.sw(A(640))
        if v != 0:
            m.setw(A(640), v - 2 if v > 0 else v + 2)
        # -- altitude limits: y in [$f8f8, $ffec]; touching either shoves the stick back by 8
        d0 = m.sw(A(304))
        if d0 >= -0x14:
            m.setw(A(304), 0xffec); m.setw(SY, m.w(SY) + 8)
        elif d0 < -0x708:
            m.setw(SY, m.w(SY) - 8); m.setw(A(304), 0xf8f8)
        m.setw(A(314), m.sw(SY) >> 1)
    if m.u8(A(712)):
        # -- missile camera ($124c4): a chase camera that follows the missile's heading
        if (m.w(A(628)) - m.w(A(634))) & 0x8000:      # `cmp.w 634(A6),D0 ; bpl` tests N only, not N xor V
            m.setw(A(628), m.w(A(628)) + 0x10)
        else:
            d0 = m.w(A(318))
            m.setw(A(626), m.w(A(626)) - d0)
            m.setw(A(628), d0); m.setw(A(634), d0)
            m.setw(A(624), m.sw(SY) >> 1)
            sn, cs = sincos(m, m.w(A(626)), 108, 112)
            m.setw(A(462), sn); m.setw(A(464), cs)
            m.setw(A(618), m.w(A(618)) + mulhi(0x190, sn))
            m.setw(A(622), m.w(A(622)) + mulhi(0x190, cs))
            new = (m.w(A(620)) + m.w(A(570))) & 0xffff
            if new & 0x8000:
                m.setw(A(620), new)
        m.setw(A(630), m.w(A(630)) - 1)
        if m.w(A(630)) == 0:
            m.set8(A(712), 0); m.set8(A(713), 0)
            calls += ['f320', 'ac9c']
            return calls
    # -- cross-hair ($12548): follows the stick unless locked (705)
    if m.u8(A(705)):
        m.setw(A(586), 0); m.setw(A(584), 0)
        m.setw(A(580), m.w(A(516))); m.setw(A(582), m.w(A(518)))
    elif m.u8(A(700)) == 0:
        d6 = m.sw(SX) >> 1
        m.setw(A(584), d6); m.setw(A(580), d6 + m.w(A(516)))
        d7 = (-m.sw(SY)) >> 2
        m.setw(A(586), d7); m.setw(A(582), d7 + m.w(A(518)))
    else:
        d6 = m.sw(SX) >> 2
        m.setw(A(584), d6); m.setw(A(580), d6 + m.w(A(516)))
        d7 = (-m.sw(SY)) >> 3
        m.setw(A(586), d7); m.setw(A(582), d7 + m.w(A(518)))
    return calls


def rng_f21e(m):
    """$f21e: the game's pseudo-random generator; the state is the long at 100(A6), mixed with the stick-x accumulator
    and the long at 92(A6). Returns D0.w (the high word of the new state)."""
    st = m.l(G + 100)
    d0 = (st << 1) & 0xffffffff
    carry = (st >> 31) & 1
    if carry or d0 == 0:                        # not 'bhi'
        d0 ^= 0x1d872b41
    d0 = (d0 & 0xffff0000) | ((d0 + m.w(SX)) & 0xffff)       # add.w: no carry into the high word
    d0 = (d0 + m.l(G + 92)) & 0xffffffff
    m.setl(G + 100, d0)
    return (d0 >> 16) & 0xffff


def controls(m, calls=None):
    """$d29a minus its letter-key commands (it first reads and clears the last-key byte at $c3de; the test calls it
    with $c3de = 0): the held-key flags at $c34e + scancode drive the three stick accumulators, one step per pass."""
    A = lambda o: G + o
    f = lambda sc: m.u8(0xc34e + sc)
    k = {n: m.u8(A(n)) for n in (728, 729, 730, 731, 732, 733)}
    def add(a, d):
        m.setw(a, m.w(a) + d)
    # accelerate has priority over decelerate; both read the Space / '/' keys, then the user-defined key
    mode = None
    if f(57):
        mode = 'acc'
    elif f(53) or f(k[733]):
        mode = 'dec'
    elif f(k[732]):
        mode = 'acc'
    if mode == 'acc':
        if m.w(A(658)) == 0x1e:                   # launch from the silo ($d3c6)
            m.setw(A(658), m.w(A(658)) - 1)
            m.set8(A(714), 0)
            m.setw(SD, 0xfec0)
            rng_f21e(m); rng_f21e(m)
            m.setw(A(304), 0xffd0)                # 304(A6) = -48; x moves 2000 units off the silo ($d3de)
            m.setw(A(302), m.w(A(302)) + 0x7d0)
            return 'launch'
        add(SD, -0x10)
    elif mode == 'dec':
        add(SD, 0x10)
    if f(75) or f(45) or f(k[728]):
        add(SX, -0x20)
    if f(77) or f(46) or f(k[729]):
        add(SX, 0x20)
    if f(72) or f(39) or f(k[730]):
        add(SY, -0x20)
    if f(80) or f(52) or f(k[731]):
        add(SY, 0x20)
    return mode


def isr(m, vec, b):
    """$b7be and its four continuation handlers (vector $118 is re-pointed after each byte): the IKBD byte `b` taken
    from the ACIA. Returns the new vector. Writes key flags, $c3de, the stick accumulators and the button bytes."""
    if vec == 0xb7be:
        if b < 0xf8:
            if b & 0x80 == 0:
                m.set8(0xc34e + b, 1); m.set8(0xc3de, b)
            else:
                m.set8(0xc34e + (b & 0x7f), 0)
            return vec
        if b & 2:
            m.set8(0xc3d6, 0xff); m.set8(0xc3d8, 0xff)
        else:
            m.set8(0xc3d6, 0)
        return 0xb8a2 if b & 1 else 0xb834
    if vec == 0xb834:
        m.setw(SX, m.w(SX) + s8(b)); return 0xb860
    if vec == 0xb860:
        m.setw(SY, m.w(SY) + s8(b)); return 0xb7be
    if vec == 0xb8a2:
        m.setw(SX, m.w(SX) + s8(b)); return 0xb8cc
    if vec == 0xb8cc:
        m.setw(SD, m.w(SD) + s8(b)); return 0xb7be
    raise ValueError(hex(vec))

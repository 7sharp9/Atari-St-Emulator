"""Black Tiger actor AI, transcribed from COMMAND.PRG ($c470..$1f274) and gated against callcap.

Every function is a literal transcription of one routine (address in the docstring); none of
them sees callcap output.  `Mem` wraps a RAM image; a routine mutates it and `Mem.diff()` gives
the changed bytes, which `gate_*.py` compares with the callcap `mem` list.

Actor record (16 bytes, table $1f010 = hero, $1f020.. = actors, 180 records):
  +0 type byte (0 free, $ff hero), +1 state, +2 anim frame, +3 facing (0 = right, 1 = left),
  +4 x.w, +6 y.w, +8 hit points, +9 stun/cooldown, +12/+13 deferred state / cooldown,
  +14 base state to return to.
"""
import struct
from collections import Counter

COV = Counter()          # branch coverage of the corpus (label -> hits)


def cov(k): COV[k] += 1

HERO = 0x1F010
ACTORS = 0x1F020
NACT = 180
BANKS = 0x1EEA2          # long: pointer to the per-type frame-bank offset table
SEED = 0x3195C
PTAB = 0x317B8           # enemy-projectile table: 30 records x 14 bytes
PFLAG = 0x317B6
AIST = 0x1EEAE           # word: actor state after the last AI step
SCROLLX, SCROLLY = 0x1EFEC, 0x1EFEE
MAPW = 0x201C8
MAPBASE = 0x201CC
TILECLS = 0x25FCC
WRAPW = 0x1EFFE          # word: level width in pixels (MAPW*16)


class Mem:
    def __init__(self, ram):
        self.r = bytearray(ram)
        self.orig = bytes(ram)

    def b(self, a): return self.r[a]
    def sb(self, a): v = self.r[a]; return v - 256 if v > 127 else v
    def w(self, a): return (self.r[a] << 8) | self.r[a + 1]
    def sw(self, a): v = self.w(a); return v - 65536 if v > 32767 else v
    def l(self, a): return struct.unpack_from(">I", self.r, a)[0]
    def sb_(self, a, v): self.r[a] = v & 0xFF
    def sw_(self, a, v): self.r[a] = (v >> 8) & 0xFF; self.r[a + 1] = v & 0xFF
    def sl_(self, a, v): struct.pack_into(">I", self.r, a, v & 0xFFFFFFFF)

    def diff(self, lo=0, hi=0x100000):
        return {a: self.r[a] for a in range(lo, hi) if self.r[a] != self.orig[a]}


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def u16(v): return v & 0xFFFF


# ---------------------------------------------------------------- $fe1c random generator
def rng(m, n):
    """$fe1c(n) (wrapper $cb6a): seed' = (seed^2*$c2 + seed*$6eb + $3619) mod 2^16 computed
    with word adds after 16x16 mulu; result = seed' mod n (divu remainder)."""
    s = m.w(SEED)
    d0 = (s * s) & 0xFFFFFFFF            # mulu s,D0
    d0 = (d0 & 0xFFFF) * 0xC2            # mulu #$c2,D0 uses the low word of D0
    d1 = s * 0x6EB
    d0 = u16(u16(d0) + u16(d1))
    d0 = u16(d0 + 0x3619)
    m.sw_(SEED, d0)
    return d0 % (n & 0xFFFF)


# ---------------------------------------------------------------- $ec7c tile class
def tile_class(m, x, y):
    """$ec7c: returns (D1 class byte, D0 tile word).  x wraps modulo the level width ($1effe)."""
    wrap = m.w(WRAPW)
    x = s16(x)
    if x < 0:
        x = u16(x + wrap)
    elif x >= wrap:                       # cmp.w D0,D2 / blt: signed word compare
        x = u16(x - wrap)
    d0 = ((u16(y) >> 4) * m.w(MAPW)) & 0xFFFFFFFF      # mulu $201c8,D0
    d0 = u16(d0 + (u16(x) >> 4))                      # add.w D1,D0
    off = s16(d0 << 1)                                # lsl.w #1 then 0(A0,D0.w): sign-extended index
    tile = m.w(MAPBASE + off)
    return m.b(TILECLS + (tile & 0x3FF)), tile


# ---------------------------------------------------------------- $db1c sqrt-like loop
def db1c(d0w):
    """$db1c: Newton iteration, returns D0.w = result+1 (D0 is ext.l of the input word)."""
    d0 = s16(d0w) & 0xFFFFFFFF
    d3, d1 = 8, 2
    while True:
        d2 = u16(u16(d3) + u16(d1)) >> 1
        d3 = d2
        d3 = u16(d3 - d1)
        if d3 & 0x8000:
            d3 = u16(-d3)
        if s16(d3) <= 1:
            break
        d1 = d2
        # divu D1,D3 with D3 = D0 (long)
        q = d0 // d1
        d3 = q & 0xFFFF if q <= 0xFFFF else d0 & 0xFFFF
    return u16(d1 + 1)


def divs_trunc(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


# ---------------------------------------------------------------- $df74 aim vector
def df74(m, A3):
    """$df74: returns (D1 velocity long, D2 position long, D3) for a shot from actor A3 at the hero."""
    hx, hy = m.sw(0x1F014), m.sw(0x1F016)
    ax, ay = m.sw(A3 + 4), m.sw(A3 + 6)
    d2 = s16(hx - ax)
    d3 = s16(hy - ay)
    d0 = (u16(d2) * u16(d2)) & 0xFFFFFFFF          # mulu D0,D0
    d1 = (u16(d3) * u16(d3)) & 0xFFFFFFFF
    d0lo = u16(u16(d0) + u16(d1))                  # add.w D1,D0
    d0lo >>= 7                                     # lsr.w #7,D0
    r = db1c(d0lo)                                 # D0.w (upper word from ext.l: not used by divs)
    qx = divs_trunc(d2, s16(r))
    qy = divs_trunc(d3, s16(r))
    d1v = (u16(qx) << 16) | u16(qy)
    d2v = (u16(ax) << 16) | u16(ay - 0x10)
    return d1v, d2v, 2


def free_pslot(m):
    """$10e56: first projectile record whose word (A0) has bit 15 clear... returns address or None.
    (tst.w (A0) / bmi: the FREE records are the NEGATIVE ones)."""
    a = PTAB
    for _ in range(30):
        if m.w(a) & 0x8000:
            return a
        a += 14
    return None


def spawn_p(m, d1, d2, d3, d4):
    """$10e0c: spawn an enemy projectile; D4 type (negative: ignored), D3 lifetime word (long sign = flip)."""
    if d4 & 0x8000:
        return
    a = free_pslot(m)
    if a is None:
        return
    m.sw_(a, d4)
    if d3 & 0x80000000:
        m.sw_(a, m.w(a) | 0x2000)
    m.sl_(a + 2, d2)
    m.sl_(a + 6, d1)
    m.sw_(a + 10, 0)
    m.sw_(a + 12, d3)
    if u16(d3) == 0:
        p_set_timer(m, a)


def p_set_timer(m, a):
    """$10e70: 12(A0) := $1116c[type] | $8000 when the table word is nonzero."""
    t = m.w(a) & 0xFF
    v = m.w(0x1116C + 2 * t)
    if v:
        m.sw_(a + 12, v | 0x8000)


# ---------------------------------------------------------------- the AI step, $dbde
HANDLER = {1: 'dc92', 2: 'dcd6', 3: 'dcd6', 4: 'dcd6', 5: 'dce4', 6: 'dce8', 7: 'ddb8', 8: 'ddb8',
           9: 'de2e', 10: 'de2e', 11: 'de2e', 12: 'de04', 13: 'ddd4', 14: 'dc92', 15: 'dd7c',
           16: 'dd46', 17: 'dd7c', 18: 'de04', 19: 'dcd6'}


class AI:
    def __init__(self, m, A3):
        self.m, self.A3 = m, A3
        self.D0 = None

    # shared helpers ------------------------------------------------------------------
    def bank(self, off):
        """movea.l $1eea2,A0 / adda.l 0(A0,D0.w),A0"""
        m = self.m
        p = m.l(BANKS)
        return (p + m.l(p + s16(off))) & 0xFFFFFFFF

    def db84(self, off):
        """$db84: returns True when the caller should carry on (D0 bit 31 set)."""
        m, A3 = self.m, self.A3
        if m.b(A3 + 1) != 6:
            return True
        d1 = s16(m.sw(0x1F014) - m.sw(A3 + 4))
        d1 = abs(d1) if d1 < 0 else d1
        if d1 > 0x40:
            m.sb_(A3 + 2, 0)
            cov('db84_far_x')
            return False
        if m.b(A3) == 0xD:
            d1 = s16(m.sw(0x1F016) - m.sw(A3 + 6))
            d1 = abs(d1) if d1 < 0 else d1
            if d1 > 0x40:
                m.sb_(A3 + 2, 0)
                return False
        m.sb_(A3 + 1, 7)
        cov('db84_wake')
        return True

    def db50(self):
        """$db50: floor probe at the actor's own position; True = standing (class 1)."""
        m, A3 = self.m, self.A3
        cls, _ = tile_class(m, m.sw(A3 + 4), m.sw(A3 + 6))
        if cls == 1:
            m.sw_(A3 + 6, m.w(A3 + 6) & 0xFFF0)
            cov('db50_stand')
            return True
        cov('db50_fall')
        m.sb_(A3 + 1, 5)
        m.sb_(A3 + 2, 0)
        return False

    def dfbc(self):
        """$dfbc: random heading nibble into +13 (bit3 right, bit2 left, bit1 down, bit0 up)."""
        m, A3 = self.m, self.A3
        d4 = 0
        if rng(m, 100) >= 0x32:
            d4 = 8
            if s16(m.sw(A3 + 4) - m.sw(0x1F014)) >= 0:
                d4 = 4
        if rng(m, 100) >= 0x32:
            d4 = 2
            if s16(m.sw(A3 + 6) - m.sw(0x1F016)) >= 0:
                d4 = 1
        m.sb_(A3 + 13, d4)

    def dab0(self):
        """$dab0: face the hero (+3: 0 hero to the right, 1 hero to the left within 400 px)."""
        m, A3 = self.m, self.A3
        d3 = s16(m.sw(A3 + 4) - m.sw(0x1F014))
        if d3 < 0:
            m.sb_(A3 + 3, 0)
        elif d3 < 0x190:
            m.sb_(A3 + 3, 1)
        if m.b(A3) == 0xB:
            m.sb_(A3 + 3, m.b(A3 + 3) ^ 1)

    def df12(self):
        m, A3 = self.m, self.A3
        d1, d2, d3 = df74(m, A3)
        spawn_p(m, d1, d2, d3, 0)

    def de32(self, off):
        """$de32: approach / face / attack decision shared by most types."""
        m, A3 = self.m, self.A3
        a0 = self.bank(off)
        dx = s16(m.sw(0x1F014) - m.sw(A3 + 4))
        if dx < 0:
            dx = s16(-dx)
        d0 = s16(dx - m.sw(a0 + 12))
        reach = m.sw(a0 + 10)
        if d0 > reach:                                   # dea2: too far, walk toward the hero
            cov('de32_far')
            m.sb_(A3 + 1, 1)
            return self.defc()
        d0 = s16(d0 + m.sw(a0 + 12) + m.sw(a0 + 12))
        if d0 < reach:                                   # dec0
            cov('de32_dec0')
            if d0 > 0x28:                                # ded6
                cov('de32_ded6')
                x4 = u16(m.sw(A3 + 4)) >> 4
                if s16(x4) > 3:
                    cov('de32_ded6_taken')
                    m.sb_(A3 + 1, 2)
                    m.sb_(A3 + 2, 0)
                    m.sb_(A3 + 9, 6)
                    return self.defc()
        return self.de68()

    def de68(self):
        m, A3 = self.m, self.A3
        if m.b(A3 + 1) == 3:
            return self.defc()
        cov('de68_attack')
        m.sb_(A3 + 1, 3)
        m.sb_(A3 + 2, 0)
        if m.b(A3) == 0x11:
            if rng(m, 100) >= 0x32:
                m.sb_(A3 + 1, 8)
                cov('de68_type17_state8')
        return self.defc()

    def defc(self):
        self.dab0()

    # handlers ------------------------------------------------------------------------
    def run(self):
        m, A3 = self.m, self.A3
        if m.b(A3 + 9) != 0:
            cov('cooldown')
            return False
        if m.b(HERO) == 0:
            return False
        st = m.b(A3 + 1)
        if st != 0 and st != 6:
            return False
        typ = m.b(A3)
        off = (typ - 1) * 4
        if m.b(A3 + 12) != 0:
            cov('deferred_state')
            m.sb_(A3 + 1, m.b(A3 + 12))
            m.sb_(A3 + 9, m.b(A3 + 13))
            m.sb_(A3 + 12, 0)
            m.sb_(A3 + 13, 0)
        else:
            self.dispatch(typ, off)
        m.sw_(AIST, m.b(A3 + 1))
        return True

    def dispatch(self, typ, off):
        m, A3 = self.m, self.A3
        h = HANDLER[typ]
        if h == 'dc92':
            if not self.db84(off):
                return
            d1 = rng(m, 100)
            if d1 <= 0x1E:
                if not self.db50():
                    return
                return self.de32(off)
            cov('dc92_turn')
            m.sb_(A3 + 3, d1 & 1)
            m.sb_(A3 + 1, 2)
            m.sb_(A3 + 2, 0)
        elif h == 'dcd6':
            if not self.db50():
                return
            return self.de32(off)
        elif h == 'dce4':
            return self.de32(off)
        elif h == 'dce8':
            if not self.db84(off):
                return
            if m.b(A3 + 1) == 3:
                return
            a0 = self.bank(off)
            d0 = s16(m.sw(0x1F014) - m.sw(A3 + 4))
            if d0 < 0:
                d0 = s16(-d0)
            if d0 > m.sw(a0 + 10):
                return
            cov('dce8_fire')
            self.df12()
            m.sb_(A3 + 1, 3)
            m.sb_(A3 + 2, 0)
            m.sb_(A3 + 12, 1)
            m.sb_(A3 + 13, rng(m, 8) + 8)
        elif h == 'ddb8':
            if m.b(A3 + 1) != 6:
                return self.de32(off)
            if not self.db84(off):
                return
            m.sb_(A3 + 3, 0)
        elif h == 'de2e':
            return
        elif h in ('ddd4', 'de04'):
            if m.b(A3 + 1) != 6:
                self.dfbc()
                return self.de32(off)
            if not self.db84(off):
                return
            m.sb_(A3 + 3, 0)
            m.sb_(A3 + 19, 1)
            m.sb_(A3 + 17, 7)
            cov('ddd4_wake_sibling')
        elif h == 'dd7c':
            if not self.db84(off):
                return
            if not self.db50():
                return
            if rng(m, 100) >= 0x14:
                return self.de32(off)
            cov('dd7c_state2')
            m.sb_(A3 + 1, 2)
            m.sb_(A3 + 2, 0)
        elif h == 'dd46':
            m.sb_(A3 + 1, 0)
            a0 = self.bank(off)
            d0 = s16(m.sw(0x1F014) - m.sw(A3 + 4))
            if d0 < 0:
                d0 = s16(-d0)
                m.sb_(A3 + 1, 3)
            if d0 > m.sw(a0 + 10):
                return
            m.sb_(A3 + 1, 1)
            cov('dd46_near')
        else:
            raise ValueError(h)


def dbde(m, A3):
    """Run $dbde(A3) on `m`; returns the final D0 (type byte as a long) or None on an early return."""
    ai = AI(m, A3)
    typ = m.b(A3)
    ok = ai.run()
    return typ if ok else None


# ---------------------------------------------------------------- the level spawner, $cd58
MOBJ = 0x1FB60           # map objects: 164 records x 10 bytes
EE96 = 0x1EE96           # next free actor record


def cd58(m):
    """$cd58: scan the level map once and build the object tables.

    map word = (code << 10) | tile.  code 0: nothing; 1..$27: map object (10-byte record in $1fb60:
    +0 code.w, +2 x*16+8, +4 y*16+16, +6/+7 cleared); $28..$3c: actor of type code-$27 (16-byte record
    from $1f030, state 6 = dormant, hp from $171f4[type]; type $d is doubled, $f tripled);
    $3f/$3e/$3d: hero start ($1eff2/4), second point ($1eff6/8), boss spawn point ($1effa/c).
    The scan also strips the code bits from the map in place."""
    m.sl_(EE96, 0x1F030)
    for i in range(0xA4):
        m.sw_(MOBJ + 10 * i, 0)
    a0 = MOBJ
    a1 = MAPBASE
    mw, mh = m.w(MAPW), m.w(0x201CA)
    y = 0
    while True:
        x = 0
        while True:
            v = m.w(a1)
            m.sw_(a1, v & 0x3FF)
            a1 += 2
            code = v >> 10
            if code != 0:
                if code < 0x28:
                    m.sw_(a0, code)
                    m.sw_(a0 + 2, x * 16 + 8)
                    m.sw_(a0 + 4, y * 16 + 16)
                    m.sb_(a0 + 6, 0)
                    m.sb_(a0 + 7, 0)
                    a0 += 10
                elif code == 0x3F:
                    m.sw_(0x1EFF2, x * 16); m.sw_(0x1EFF4, y * 16 + 16)
                elif code == 0x3E:
                    m.sw_(0x1EFF6, x * 16); m.sw_(0x1EFF8, y * 16 + 16)
                elif code == 0x3D:
                    m.sw_(0x1EFFA, x * 16); m.sw_(0x1EFFC, y * 16 + 16)
                else:
                    a2 = m.l(EE96)
                    typ = (code - 0x27) & 0xFF
                    m.sb_(a2, typ)
                    m.sw_(a2 + 4, x * 16 + 8)
                    m.sw_(a2 + 6, y * 16 + 16)
                    m.sb_(a2 + 8, m.b(0x171F4 + typ))
                    m.sb_(a2 + 12, 0)
                    m.sb_(a2 + 13, 0)
                    m.sb_(a2 + 1, 6)
                    copies = 1 if typ == 0xD else (2 if typ == 0xF else 0)
                    for k in range(copies):
                        m.r[a2 + 16:a2 + 32] = m.r[a2:a2 + 16]
                        a2 += 16
                    a2 += 16
                    m.sl_(EE96, a2)
            x += 1
            if x == mw:
                break
        y += 1
        if y == mh:
            break


# ---------------------------------------------------------------- actor allocation, $d65a / $d678
def d65a(m, typ, d2, a6):
    """$d65a: first free actor record (type byte 0) in $1f030.. (179 records); initialise it as
    type `typ` at (x=d2>>16, y=d2.w) in state 6 and return it (A6).  A6 is left unchanged when the
    table is full (the callers then write through the stale A6)."""
    a = 0x1F030
    for _ in range(0xB3):
        if m.b(a) == 0:
            m.sb_(a, typ)
            m.sw_(a + 6, d2 & 0xFFFF)
            m.sw_(a + 4, (d2 >> 16) & 0xFFFF)
            m.sb_(a + 2, 0)
            m.sb_(a + 1, 6)
            m.sb_(a + 12, 0)
            m.sb_(a + 9, 0)
            m.sb_(a + 13, 0)
            m.sb_(a + 8, m.b(0x171F4 + typ))
            return a
        a += 0x10
    return a6


def spawn_e(m, d1, d2, d3, d4):
    """$10b28: effect/shot table E ($31612, 30 x 14 bytes; bit 15 of the first word = free).
    A timer word from $18608[type] is installed when D3.w == 0 ($10aee)."""
    a = None
    q = 0x31612
    for _ in range(30):
        if m.w(q) & 0x8000:
            a = q
            break
        q += 14
    if a is None:
        return
    m.sw_(a, d4)
    if d3 & 0x80000000:
        m.sw_(a, m.w(a) | 0x2000)
    m.sl_(a + 2, d2)
    m.sl_(a + 6, d1)
    m.sw_(a + 10, 0)
    m.sw_(a + 12, d3)
    if u16(d3) == 0:
        t = m.w(0x18608 + 2 * (m.w(a) & 0xFF))
        if t:
            m.sw_(a + 12, t | 0x8000)


def c972(m, a6):
    """$c972: ambient spawner, once per frame ($c900 list).  Returns the final A6."""
    if m.w(0x1EEB8) != 0:
        return a6
    if m.w(0x17840) != 0:
        if rng(m, 1000) <= 7:
            d0 = rng(m, 80) - 0x28
            d2x = u16(d0 + m.sw(0x1F014))
            d2 = (d2x << 16) | m.w(0x1F016)
            d0 = rng(m, 50)
            d2 = (d2 & 0xFFFF0000) | u16((d2 & 0xFFFF) - d0 - 0x28)
            d1 = rng(m, 100)
            typ = 10 if d1 <= 0x19 else 9
            a6 = d65a(m, typ, d2, a6)
            m.sb_(a6 + 1, 7)
            m.sb_(a6 + 12, 3)
        else:
            return a6
    if m.w(0x17842) != 0:
        if rng(m, 1000) > 0x14:
            return a6
        k = m.b(0x1F011)
        if k != 0 and k != 1:
            return a6
        d0 = rng(m, 0x118) - 0x8C
        d2x = u16(d0 + m.sw(0x1F014))
        d2 = (d2x << 16) | m.w(0x1F016)
        a6 = d65a(m, 2, d2, a6)
        m.sb_(a6 + 1, 7)
    return a6


def ca48(m):
    """$ca48: the boss (record $1f020, type >= $12) fires at random while the boss flag $1eeb8 is set."""
    if m.w(0x1EEB8) == 0:
        return
    a0 = 0x1F020
    t = m.b(a0)
    if t == 0 or t < 0x12:
        return
    if rng(m, 1000) > 0x0A:
        return
    d1 = 0xF if s16(m.sw(0x1F014) - m.sw(a0 + 4)) >= 0 else 0xFFF1
    d1 = (u16(d1) << 16) | 4
    d2 = (m.w(a0 + 4) << 16) | u16(m.sw(a0 + 6) - 0x28)
    spawn_e(m, d1, d2, 0, 0xC)


# ---------------------------------------------------------------- attack events, $e7e2 / $d40a / $df26
def d40a(m, d2, d4):
    """$d40a: four P shots of type D4 in a row (x step +-$20 away from/toward the hero, lifetimes 5,10,15,20)."""
    d2 = (d2 & 0xFFFF0000) | u16((d2 & 0xFFFF) - 8)
    x = (d2 >> 16) & 0xFFFF
    d0 = u16(x - m.w(0x1F014))
    step = 0x20 if d0 & 0x8000 else 0xFFE0           # bmi after sub.w
    d0l = (step << 16) & 0xFFFFFFFF
    for k in range(4):
        spawn_p(m, 0, d2, 5 * (k + 1), d4)
        d2 = (d2 + d0l) & 0xFFFFFFFF


def df26(m, A3):
    """$df26: two aimed shots with a +-2 px/frame spread from 48 px in front of the actor, 16 px up."""
    x0, y0 = m.w(A3 + 4), m.w(A3 + 6)
    m.sw_(A3 + 4, u16(x0 - 0x30))
    if m.b(A3 + 3) == 0:
        m.sw_(A3 + 4, u16(m.w(A3 + 4) + 0x60))
    m.sw_(A3 + 6, u16(y0 - 0x10))
    d1, d2, d3 = df74(m, A3)
    spawn_p(m, (d1 + 0x20000) & 0xFFFFFFFF, d2, d3, 0)
    spawn_p(m, (d1 - 0x20000) & 0xFFFFFFFF, d2, d3, 0)
    m.sw_(A3 + 6, y0)
    m.sw_(A3 + 4, x0)


def e7e2(m, A3):
    """$e7e2: the per-type attack that fires on the animation's event frame."""
    t = m.b(A3)
    if t == 0x11:
        d2 = (m.w(A3 + 4) << 16) | u16(m.sw(A3 + 6) - 0x18)
        if m.b(A3 + 1) == 8:
            d2 = (d2 & 0xFFFF0000) | u16((d2 & 0xFFFF) + 5)
        d3 = m.b(A3 + 3)
        if d3 == 0:
            d3 = 0x8000
            d2 = (d2 + 0x400000) & 0xFFFFFFFF
        d3 = (d3 << 16) & 0xFFFFFFFF
        spawn_p(m, 0, d2, d3, 4)
    elif t in (9, 10):
        d4 = 3 if t == 9 else 7
        d0 = rng(m, 0x40) - 0x20
        d2 = (u16(d0 + m.sw(0x1F014)) << 16) | u16(m.sw(0x1F016) - 0x10)
        d40a(m, d2, d4)
    elif t == 0xC:
        AI(m, A3).df12()
    elif t == 0x12:
        if m.b(A3 + 1) != 4:
            df26(m, A3)
            m.sb_(A3 + 1, 1)
            m.sb_(A3 + 9, 8)
            m.sb_(A3 + 2, 0)
    elif t == 0x13:
        AI(m, A3).df12()

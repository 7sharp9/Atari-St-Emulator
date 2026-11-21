"""Python model of the Starglider per-object update pass $125e0 (and the helpers it calls: the two random
generators $f21e / $f23e and the bearing routine $12f1c).  Written from the disassembly (sg.asm), then compared
with the live routine by objpass_gate.py.  Everything is on a objlib.Mem; A6 = $5bf00.

Record layout (stride $40, pool at 4762(A6), count 472(A6)):
  0 w type (0 = free)   2 b flags (bit 7 = indestructible)   4/6/8 w world x/y/z   10 w pitch angle   12 w heading
  14 w roll   16 w speed   20 w timer   22 w y-velocity/timer   24 w timer reload   28/30/32 vx/-/vz (w)
  34 b in view   35 b active (listed in the near list)   36 b exploding   38 w explosion tick   40/42/44 w player-relative
  x/y/z   46 b laser-immune   48 w hit points   (see objects.md)
Branch labels visited are collected in VISITED for the gate's coverage line."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from objlib import A6, Mem

M16 = 0xffff
def s16(v): v &= M16; return v - 0x10000 if v & 0x8000 else v
def s32(v): v &= 0xffffffff; return v - (1 << 32) if v & 0x80000000 else v

class Flags:
    """flags of cmp/sub on words: N Z V C"""
    def __init__(s, d, k):
        d &= M16; k &= M16; r = (d - k) & M16
        s.N = r >> 15; s.Z = int(r == 0); s.V = ((d ^ k) & (d ^ r)) >> 15 & 1; s.C = int(d < k)
    pl = property(lambda s: not s.N); mi = property(lambda s: bool(s.N))
    ge = property(lambda s: s.N == s.V); lt = property(lambda s: s.N != s.V)
    gt = property(lambda s: (not s.Z) and s.N == s.V); le = property(lambda s: bool(s.Z) or s.N != s.V)
    eq = property(lambda s: bool(s.Z)); ne = property(lambda s: not s.Z)

def cmpw(d, k): return Flags(d, k)

def divs(D1, w):
    """divs.w: D1 (32 bit) / w (16 bit signed).  Returns (newD1, overflow).  w == 0 is a trap in the real CPU."""
    dd = s32(D1); dv = s16(w)
    assert dv != 0, 'divs by zero'
    q = abs(dd) // abs(dv)
    if (dd < 0) != (dv < 0): q = -q
    r = dd - q * dv
    if q < -32768 or q > 32767: return D1 & 0xffffffff, True
    return ((r & M16) << 16) | (q & M16), False

class Sim:
    def __init__(self, m, d0=0, break_model=False):
        self.m = m; self.d0 = d0 & 0xffffffff; self.visited = set(); self.brk = break_model
    # ---- globals
    def g(self, off): return self.m.rws(A6 + off)
    def gu(self, off): return self.m.rw(A6 + off)
    def setg(self, off, v): self.m.ww(A6 + off, v)
    def v(self, l): self.visited.add(l)
    # ---- RNG ($f21e, $f23e)
    def f21e(self):
        m = self.m
        S = m.rl(A6 + 100)
        t = (S << 1) & 0xffffffff
        if (S >> 31) & 1 or t == 0:
            t ^= 0x1d872b41 ^ (1 if self.brk else 0)
        t = (t & 0xffff0000) | (((t & 0xffff) + m.rw(0xc3ce)) & 0xffff)
        t = (t + m.rl(A6 + 92)) & 0xffffffff
        m.wl(A6 + 100, t)
        self.d0 = ((t & 0xffff) << 16) | (t >> 16)      # swap D0
        return t >> 16
    def f23e(self):
        m = self.m
        b = [m.rb(A6 + 92 + i) for i in range(6)]
        s = (b[0] << 8 | b[1]) + ((self.d0 + m.rw(0xc3ce)) & M16)
        X = 1 if s > M16 else 0
        b[0] = (s >> 8) & 0xff; b[1] = s & 0xff
        out = []
        for _ in range(2):
            d = b[0]
            t = d + b[4] + X; X = t >> 8; d = t & 0xff
            t = d + b[5] + X; X = t >> 8; d = t & 0xff
            b[0] = d; b[5] = b[4]; b[4] = b[3]; b[3] = b[2]; b[2] = b[1]; b[1] = b[0]
            out.append(d)
        for i in range(6): m.wb(A6 + 92 + i, b[i])
        m.wb(A6 + 538, out[0]); m.wb(A6 + 539, out[1])
        self.d0 = (self.d0 & 0xffff0000) | (out[0] << 8 | out[1])
        return out[0] << 8 | out[1]
    # ---- bearing from the object to the player ($12f1c): returns D1.w (also the angle, 0..$fff, 4096 per turn)
    def bearing(self, o):
        m = self.m
        D0 = s16(m.rw(o + 4) - m.rw(A6 + 302)); D1 = s16(m.rw(o + 8) - m.rw(A6 + 306))
        D5 = 0xc00
        if D0 < 0: D5 = (D5 - 0x800) & M16
        D2 = abs(D0) if D0 != -32768 else -32768; D3 = abs(D1) if D1 != -32768 else -32768
        D2 &= M16; D3 &= M16
        fl = cmpw(D3, D2)               # cmp.w D2,D3 ; blt -> second table
        if not fl.lt:
            A1 = 0x1e0f4; Dl = D1; big = (0x400, 0xfc00)
        else:
            A1 = 0x1e4f6; Dl = D1 << 8; big = (0x200, 0xfe00)
        Dl &= 0xffffffff
        nd, ovf = divs(Dl, D0 & M16)
        if self.brk: nd = nd ^ 1
        lo = nd & M16
        if cmpw(lo, 0xff).pl: R = big[0]
        elif cmpw(lo, 0xff01).pl:
            idx = ((lo + 0xff) & 0x1ff) * 2
            R = m.rw(A1 + idx)
        else: R = big[1]
        D5 = (D5 - R) & M16
        return (-D5) & M16
    # ---- sin / cos at an angle ($1e8f8 / $1f0f8 tables via 108(A6)/112(A6))
    def sincos(self, ang):
        idx = ((ang & 0xfff) << 1)
        s, c = self.m.rws(self.m.rl(A6 + 108) + idx), self.m.rws(self.m.rl(A6 + 112) + idx)
        self.m.ww(A6 + 462, s); self.m.ww(A6 + 464, c)           # the routine leaves them in 462/464(A6)
        return s, c
    def vel_from_heading(self, o):
        """$128d2 and the tails of $128b6/$1285e: 28(A0) = -(speed*sin), 32(A0) = speed*cos (both >>15 with the x2)"""
        m = self.m
        s, c = self.sincos(m.rw(o + 12))
        sp = m.rws(o + 16)
        d4 = (sp * s) * 2; d4 = s16(((d4 & 0xffffffff) >> 16)); m.ww(o + 28, -d4); m.ww(o + 30, 0)
        d4 = (sp * c) * 2; d4 = s16(((d4 & 0xffffffff) >> 16)); m.ww(o + 32, d4)
    def move(self, o):
        m = self.m
        m.ww(o + 4, m.rw(o + 4) + m.rw(o + 28)); m.ww(o + 8, m.rw(o + 8) + m.rw(o + 32))
    def turn_to(self, o, D1):
        """$128be: heading += (bearing - heading) >> 4 (no wrap handling), then velocity from the new heading"""
        m = self.m
        D0 = m.rw(o + 12) & 0xfff; m.ww(o + 12, D0)
        D1 = (D1 - D0) & M16
        m.ww(o + 12, m.rw(o + 12) + (s16(D1) >> 4))
        self.v('turn'); self.vel_from_heading(o)
    # ---- the pass
    def run(self):
        m = self.m
        n = self.g(472)
        if n == 0: return
        o = A6 + 4762
        for _ in range(n):
            if m.rb(o + 36) == 0:
                t = m.rw(o)
                if t != 0:
                    self.v('t%d' % t); self.handler(o, t)
            else:
                if m.rw(o + 38) == 0x1f:
                    self.v('freed')
                    m.wb(o + 36, 0); m.ww(o + 38, 0); m.ww(o, 0)
                    self.setg(604, self.gu(604) + 1)
                    A1 = m.rl(A6 + 156); m.wl(A1, o); m.wl(A6 + 156, A1 + 4)
                else:
                    m.ww(o + 38, m.rw(o + 38) + 1)
            m.wb(A6 + 726, 0)
            o += 0x40
    def handler(self, o, t):
        H = {1: 'fighter', 10: 'fighter', 13: 'fighter', 15: 'fighter', 16: 'fighter', 18: 'fighter', 21: 'fighter',
             27: 'fighter', 32: 'fighter', 2: 'mine', 14: 'mine', 33: 'mine', 6: 'silo', 7: 'flyer', 8: 'flyer', 19: 'flyer',
             9: 'tank', 20: 'juno', 26: 'pylauncher', 23: 'trilauncher', 3: 'type3', 11: 'refuel', 12: 'missile',
             24: 'missile', 25: 'homing'}.get(t)
        if H is None: return              # 4 5 17 22 31 ... : no code
        getattr(self, 'h_' + H)(o)
    # ---- handlers
    def h_silo(self, o):
        m = self.m
        m.ww(o + 12, m.rw(o + 12) + 0x10)
        m.ww(o + 22, m.rw(o + 22) - 1)
        if not (m.rw(o + 22) & 0x8000): self.v('silo.tick'); return
        m.ww(o + 22, 0x7d0); m.wb(o + 20, 0xff); self.v('silo.reload')
    def h_mine(self, o):
        m = self.m
        close = False
        if m.rb(o + 34) != 0:
            if not cmpw(m.rw(o + 44), 0xf800).mi:
                if cmpw(m.rw(o + 44), 0x800).mi: close = True
        if close: self.mine_close(o)
        self.v('mine.move')
        m.ww(o + 12, m.rw(o + 12) + 0xffc0)
        d0 = m.rw(o + 22); self.d0 = (self.d0 & 0xffff0000) | d0
        m.ww(o + 6, m.rw(o + 6) + d0)
        if m.rw(o + 20) != 0:
            m.ww(o + 20, m.rw(o + 20) - 1)
            if m.rw(o + 20) != 0: return
            if m.rw(o) == 2: self.mine_reload(o); return
            m.ww(o + 10, m.rw(o + 10) + 0x40); return
        d0 = m.rw(o + 10) & 0x7ff; self.d0 = (self.d0 & 0xffff0000) | d0
        if d0 == 0: self.mine_reload(o); return
        m.ww(o + 10, m.rw(o + 10) + 0x40)
    def mine_reload(self, o):
        m = self.m; self.v('mine.reload')
        m.ww(o + 20, m.rw(o + 24)); m.ww(o + 22, -s16(m.rw(o + 22)))
    def mine_close(self, o):
        """$126b4: the proximity trigger.  Registers are saved and restored around the effects (movem), so D0 at
        return is the entry D0."""
        m = self.m; d0_save = self.d0
        self.v('mine.close')
        if self.g(664) != 0 or m.rb(A6 + 714) != 0: self.v('mine.skip'); return
        if cmpw(m.rw(o + 44), 0x600).pl:
            self.v('mine.near'); return                 # only the "MINE" message is drawn
        m.wb(o + 36, 0xff); m.ww(o + 38, 0)
        self.v('mine.explode')
        if m.rb(A6 + 712) != 0:
            self.setg(630, 0x10); self.setg(636, 0)
        else:
            self.v('mine.hit')
            w = self.f23e() & 0x3e
            w = (w - 0x20) & M16
            self.setg(640, self.gu(640) + w)
            d = self.gu(608) - 0x3a98
            if d < 0: d = 0
            self.setg(608, d)
            self.setg(578, 0x333)
        self.d0 = d0_save
    def h_fighter(self, o):
        m = self.m; t = m.rw(o)
        if m.rb(A6 + 711): self.v('fi.move'); self.move(o)
        dx = s16(m.rw(o + 4) - m.rw(A6 + 302))
        near = False; far = False
        if cmpw(dx, 0x3e8).pl: far = True
        elif cmpw(dx, 0xfc18).pl: near = True
        else:
            dz = s16(m.rw(o + 8) - m.rw(A6 + 306))
            if cmpw(dz, 0x3e8).pl: far = True
            elif cmpw(dz, 0xfc18).mi: far = True
            else: near = True
        if near:
            if t == 0x1b:
                D1 = self.f21e() & 0x3f
                if D1 == 0: return self.shoot(o)
                D1 &= 0x1f; D1 &= 3
                if D1 != 0: self.v('fi.27.turn'); return self.turn_to(o, self.bearing(o) & 0xfff)
                m.wb(A6 + 726, 0xff); self.v('fi.27.aim')
            else:
                D1 = self.f21e() & 0x7f
                if D1 == 0: return self.shoot(o)
                D1 &= 7
                if D1 != 0: self.v('fi.turn'); return self.turn_to(o, self.bearing(o) & 0xfff)
                self.v('fi.aim')
            return self.fire_if_aligned(o, self.bearing(o) & 0xfff)
        D1 = self.f21e() & 0x7f
        if D1 == 0: return self.shoot(o)
        D1 &= 0x1f
        if D1 == 0: self.v('fi.far.turn'); return self.turn_to(o, self.bearing(o) & 0xfff)
        D1 &= 0xf
        if D1 == 0: self.v('fi.far.aim'); return self.fire_if_aligned(o, self.bearing(o) & 0xfff)
        self.v('fi.far.idle')
    def h_flyer(self, o):
        m = self.m
        if not m.rb(A6 + 711): return
        self.move(o)
        d0 = self.f21e() & 0x3f
        if d0 != 0:
            d0 &= 0xf
            if d0 == 0: self.v('fl.shoot'); self.shoot(o)
            else: self.v('fl.idle')
            return
        self.v('fl.wander')
        d0 = (self.f21e() & 0x1f) - 0x10
        m.ww(o + 12, m.rw(o + 12) + d0)
        self.vel_from_heading(o)
    def h_missile(self, o):
        m = self.m
        self.move(o)
        d0 = s16(m.rw(A6 + 304) - m.rw(o + 6)) >> 3
        m.ww(o + 6, m.rw(o + 6) + d0)
        m.ww(o + 14, m.rw(o + 14) + 0x40)
        m.ww(o + 20, m.rw(o + 20) - 1)
        if s16(m.rw(o + 20)) <= 0: self.v('mis.die'); self.missile_die(o)
        else: self.v('mis.fly')
    def missile_die(self, o):
        m = self.m
        if m.rb(o + 36) == 0: m.wb(o + 36, 0xff); m.ww(o + 38, 0)
    def h_homing(self, o):
        m = self.m
        self.move(o)
        d0 = s16(m.rw(A6 + 304) - m.rw(o + 6)) >> 2
        m.ww(o + 6, m.rw(o + 6) + d0)
        m.ww(o + 14, m.rw(o + 14) + 0x40)
        m.ww(o + 20, m.rw(o + 20) - 1)
        if s16(m.rw(o + 20)) <= 0: self.v('hom.die'); return self.missile_die(o)
        if cmpw(m.rw(o + 6), 0xf95c).mi: self.v('hom.low'); return self.missile_die(o)
        D1 = self.bearing(o); D1 = ((D1 - 0x800) & 0xfff)
        m.ww(o + 12, D1); self.v('hom.steer'); self.vel_from_heading(o)
    def h_tank(self, o):
        m = self.m
        if not m.rb(A6 + 711): return
        dx = s16(m.rw(o + 4) - m.rw(A6 + 302)); far = False; near = False
        if cmpw(dx, 0x3e8).pl: far = True
        elif cmpw(dx, 0xfc18).pl: near = True
        else:
            dz = s16(m.rw(o + 8) - m.rw(A6 + 306))
            if cmpw(dz, 0x3e8).pl: far = True
            elif cmpw(dz, 0xfc18).mi: far = True
            else: near = True
        if near:
            d0 = self.f21e() & 0x7f
            if d0 == 0: m.wb(A6 + 726, 0xff)
            d0 &= 3
            if d0 == 0: self.v('tank.aim'); return self.fire_if_aligned(o, self.bearing(o) & 0xfff)
            self.v('tank.turn'); return self.turn_to(o, self.bearing(o) & 0xfff)
        if m.rw(o + 22) == 0:
            m.ww(o + 12, m.rw(o + 12) + 0x20)
            if (m.rw(o + 12) & 0x3ff) == 0: m.ww(o + 22, 0x64)
            self.v('tank.patrol'); return self.vel_from_heading(o)
        self.move(o)
        m.ww(o + 22, m.rw(o + 22) - 1)
        d0 = self.f21e() & 0xf
        if d0 == 0: self.v('tank.far.aim'); return self.fire_if_aligned(o, self.bearing(o) & 0xfff)
        self.v('tank.far.walk')
    def h_juno(self, o):
        m = self.m
        if m.rb(o + 35) == 0: return
        d0 = self.f21e() & 7
        if d0 == 0: self.v('juno.fire'); return self.fire(o)
        D1 = (self.bearing(o) - 0x800) & 0xfff
        D0 = m.rw(o + 12) & 0xfff
        D1 = (D1 - D0) & M16
        D0 = (D0 + (s16(D1) >> 4)) & M16
        m.ww(o + 12, D0); self.v('juno.track')
    def h_pylauncher(self, o):
        m = self.m
        if m.rb(o + 35) == 0: return
        if self.g(662) == 1: return
        m.ww(o + 12, m.rw(o + 12) + 0xffc0)
        d0 = self.f21e() & 0xf
        if d0 != 0: self.v('pyl.spin'); return
        m.wb(A6 + 726, 0xff); self.v('pyl.fire'); self.fire(o)
    def h_trilauncher(self, o):
        m = self.m
        if m.rb(o + 35) == 0: return
        m.ww(o + 12, m.rw(o + 12) + 0xffa0)
        if self.g(632) == 0: return
        D1 = (self.bearing(o) - 0x800) & 0xfff
        self.v('tri.aim'); self.fire_if_aligned(o, D1)
    def h_type3(self, o):
        if self.m.rb(o + 34) == 0: return
        d0 = self.f21e() & 0x1f
        if d0 == 0: self.v('t3.shoot'); self.shoot(o)
    def h_refuel(self, o):
        if self.g(662) < 3: return
        d0 = self.f21e() & 0x7ff
        if d0 == 0: self.v('t11.vanish'); self.m.ww(o, 0)
    # ---- weapons
    def shoot(self, o):
        """$129a4: the object fires a laser at the player; shield 608(A6) drains by the type's damage"""
        m = self.m
        if m.rb(o + 34) == 0 or m.rb(A6 + 714) or m.rb(A6 + 712): return
        t = m.rw(o); self.d0 = t * 2
        self.v('shoot')
        if self.g(662) == 1:
            d = self.gu(608) - 0x64
            if d < 0: d = 0
        else:
            d = self.gu(608) - m.rw(0x159ea + 2 * t)
            if d < 0: d = 0
        self.setg(608, d)
        D3 = m.rw(o + 44)
        if D3 == 0: return
        # laser bolt: $12a2a draws one random draw (length 96..223) before $10192 renders it (video only)
        self.f21e()
        self.setg(520, 1); self.setg(578, 0x20)
        m.wl(A6 + 196, m.rl(A6 + 196) + 1)
    def fire_if_aligned(self, o, D1):
        m = self.m
        D0 = m.rw(o + 12) & 0xfff
        D1 = (D1 - D0) & M16
        if cmpw(D1, 0).mi: D1 = -s16(D1) & M16
        if cmpw(D1, 0x50).pl: return
        self.fire(o)
    def fire(self, o):
        """$12a7e: take a spare record from the free list and launch a missile (type 24 neutron or 25 homing)"""
        m = self.m
        if self.gu(604) == 0 or m.rb(o + 35) == 0 or m.rb(A6 + 714) or m.rb(A6 + 711) == 0: return
        A1 = m.rl(A6 + 156) - 4; A2 = m.rl(A1); m.wl(A6 + 156, A1); self.setg(604, self.gu(604) - 1)
        t = m.rw(o); D2 = m.rw(0x15a9e + 2 * t)
        self.v('fire')
        lvl = self.g(662)
        if m.rb(A6 + 726) and lvl != 1: m.ww(A2, 0x19); self.v('fire.homing')
        else: m.ww(A2, 0x18)
        m.wb(A2 + 2, 1)
        m.ww(A2 + 4, m.rw(o + 4)); m.ww(A2 + 6, (D2 + m.rw(o + 6)) & M16); m.ww(A2 + 8, m.rw(o + 8))
        m.ww(A2 + 10, m.rw(o + 10))
        D1 = m.rw(o + 12)
        if m.rw(0x12ee0 + 2 * t) != 0: D1 = (D1 - 0x800) & M16
        m.ww(A2 + 12, D1 & 0xfff); m.ww(A2 + 14, m.rw(o + 14))
        m.ww(A2 + 16, m.rw(0x12b80 + 2 * lvl)); m.ww(A2 + 20, m.rw(0x12be2 + 2 * lvl)); m.ww(A2 + 48, 0)
        s, c = self.sincos(m.rw(A2 + 12))
        sp = m.rws(A2 + 16)
        d4 = (sp * s) * 2; d4 = s16((d4 & 0xffffffff) >> 16); m.ww(A2 + 28, -d4)
        d4 = (sp * c) * 2; d4 = s16((d4 & 0xffffffff) >> 16); m.ww(A2 + 32, d4); m.ww(A2 + 30, 0)

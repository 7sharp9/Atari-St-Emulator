"""Python port of fed_MapGen's digger $244b6 (called from $23cb0) and its gate against the emulator.

    uv run python -I <this dir>/dig.py gate <capture.bin> [...] [--break carve2|roomsize|pillar]
    uv run python -I <this dir>/dig.py tree <capture.bin> [...]      # tree census of the carved bases

The port is a register-level transcription of the decrypted module (runtime addresses, module at $1f7b0, variables at
A6 = $20376; A0 = G0 = 56(A6), A3 = G1 = 4168(A6) as set at $23c98/$23c9c). It takes the whole module variable block
read at $23cb0 (dig_capture.py) and runs the digger on it; the gate compares the whole block read at $23cb4 (G0, G1,
G2, the room list 12952(A6), the RNG words 12404/13656(A6), every other variable) and D1-D7 at the return.

Routines transcribed (one method each, named for the address):
  $244b6 main     turtle loop, 10 random-turn retries, then batches of 100 random cells ($2452a-$245cc)
  $24872 step     random word in 12426(A6): low 3 bits 0/1 turn left/right; 2/3 lift up/down when the word > $ccb0
                  and D4 > 4; else word <= $7ad structure, <= $8f48 room, else move forward
  $24902/$248f0   lift: far end through the floor-pair offset 16/24(A6), must be on that floor's block and fully
                  isolated (4 uncarved neighbours)
  $249da room     ((s & 7) + 2) x (((s >> 3) & 7) + 2) cells, s = (word ror 6) & $3f (& $1b if word > $3ff7)
  $24c5c          structure: fence ($24d2c) then a 50-step blob walk ($24cd4) of feature $11/$14
  $24d96          pre-placed structure triggers from 13360(A6) (set by $245e2)
  $24e8c count    uncarved neighbours of a rock cell (0 if the cell is not rock); $24efc open; $24f3c carve
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

G0, G1 = 56, 4168
PAT = bytes.fromhex('0000000000000000002209045108452200240012004900240004002000040020'
                    '002a002a002a002a0022140014224100000e0070000e00700004004400040044'
                    '6100fc58')  # $24c1c, then the first code bytes at $24c5c (read as the 9th row of a 9-row room)
DX = {0: 0, 2: 1, 4: 0, 6: 0xffff}     # $248c4 / $24c0c
DY = {0: 0xffff, 2: 0, 4: 1, 6: 0}     # $248cc / $24c14
RESTART_FEATS = (0x1f, 0x35, 0x36, 0x04, 0x05, 0x33, 0x11)  # $24552-$24588
BREAK = None


def ror(v, n):
    n &= 15
    v &= 0xffff
    return ((v >> n) | (v << (16 - n))) & 0xffff


def rol(v, n):
    return ror(v, 16 - (n & 15))


def sx(v):
    return v - 0x10000 if v & 0x8000 else v


class Dig:
    def __init__(self, block):
        self.m = bytearray(block)
        self.d0 = self.d1 = self.d2 = self.d3 = self.d4 = self.d5 = self.d6 = self.d7 = 0
        self.tag = {}   # cell index -> (routine that carved it last, instance): for the tree census only
        self.ninst = 0
        self.bid = None

    # memory
    def W(self, o):
        return (self.m[o] << 8) | self.m[o + 1]

    def SW(self, o, v):
        v &= 0xffff
        self.m[o] = v >> 8
        self.m[o + 1] = v & 0xff

    # $23b96, $245ce
    def rng(self):
        x = (self.W(12404) * 0x5e5 + 0x29) & 0xffff
        self.SW(12404, x)
        self.d0 = ror(x, 4) ^ 0x800
        return self.d0

    def rng2(self):
        x = (self.W(13656) * 0x5e5 + 0x29) & 0xffff
        self.SW(13656, x)
        self.d0 = ror(x, 3)
        return self.d0

    def idx(self):  # $24d7e
        self.d5 = (((self.d2 << 6) + self.d1) * 2) & 0xffff
        assert self.d5 < 4096, (self.d1, self.d2)

    def open(self):  # $24efc: (D0, Z)
        if self.d1 > 63 or self.d2 > 31:
            self.d0 = 1
            return 1, True
        self.idx()
        v = self.W(G0 + self.d5)
        if v == 0:
            self.d0 = 1
            return 1, False
        if v > 0xffce:
            self.d0 = 1
            return 1, True
        self.d0 = 0
        return 0, True

    def nbrs(self):  # $24e94
        self.d1 = (self.d1 - 1) & 0xffff
        self.d6 += self.open()[0]
        self.d1 = (self.d1 + 2) & 0xffff
        self.d6 += self.open()[0]
        self.d1 = (self.d1 - 1) & 0xffff
        self.d2 = (self.d2 - 1) & 0xffff
        self.d6 += self.open()[0]
        self.d2 = (self.d2 + 2) & 0xffff
        self.d6 += self.open()[0]
        self.d2 = (self.d2 - 1) & 0xffff
        self.d0 = 0xffff

    def count(self):  # $24e8c
        self.d6 = 0
        _, z = self.open()
        if z:
            return
        self.nbrs()

    def inst(self):
        self.ninst += 1
        return self.ninst

    def carve(self, tag=('corr', None)):  # $24f3c
        self.idx()
        self.tag[self.d5 >> 1] = tag
        self.SW(G0 + self.d5, self.d4)
        self.d4 = (self.d4 + 1) & 0xffff

    def restore(self):  # $24d88
        self.d1, self.d2, self.d3 = self.W(48), self.W(50), self.W(52)

    def save(self):
        self.SW(48, self.d1)
        self.SW(50, self.d2)
        self.SW(52, self.d3)

    def blk(self):
        self.d5 = ((((self.d2 & 0x18) << 3) + self.d1) & 0xffff) >> 4

    def floor_of(self):  # $2511e
        self.blk()
        self.d3 = self.m[self.d5]

    def down(self):  # $25136
        self.d5 = ((self.d3 - 2) * 2) & 0xffff
        self.d3 = (self.d3 - 1) & 0xffff
        self.d1 = (self.d1 - self.W(16 + self.d5)) & 0xffff
        self.d2 = (self.d2 - self.W(24 + self.d5)) & 0xffff

    def up(self):  # $2514c
        self.d3 = (self.d3 + 1) & 0xffff
        self.d5 = ((self.d3 - 2) * 2) & 0xffff
        self.d1 = (self.d1 + self.W(16 + self.d5)) & 0xffff
        self.d2 = (self.d2 + self.W(24 + self.d5)) & 0xffff

    def fwd(self):  # $248b6
        self.d1 = (self.d1 + DX[self.d5]) & 0xffff
        self.d2 = (self.d2 + DY[self.d5]) & 0xffff
        self.SW(12424, self.d5)

    def step2(self):  # $24bfa
        self.d5 = (self.d5 + self.W(12424)) & 6
        self.d1 = (self.d1 + DX[self.d5]) & 0xffff
        self.d2 = (self.d2 + DY[self.d5]) & 0xffff

    def side(self):  # $24bf6
        self.d5 = self.W(12428)
        self.step2()

    # $24872
    def step(self):
        self.d5 = self.W(12424)
        self.save()
        self.d6 = self.W(12426)
        self.d0 &= 7
        if self.d0 == 0:
            self.d5 = (self.d5 - 2) & 6
            return self.fwd()
        if self.d0 == 1:
            self.d5 = (self.d5 + 2) & 6
            return self.fwd()
        self.d0 -= 1
        if self.d6 > 0xccb0 and self.d4 > 4:
            self.d0 -= 1
            if self.d0 == 0:
                return self.lift(True)
            self.d0 -= 1
            if self.d0 == 0:
                return self.lift(False)
        if self.d6 <= 0x7ad:
            return self.structure()
        if self.d6 <= 0x8f48:
            return self.room()
        self.fwd()

    def lift_fail(self):  # $248e6
        self.restore()
        self.d5 = self.W(12424)
        self.fwd()

    def lift(self, goup):  # $24902 / $248f0
        if goup:
            if sx(self.d3) >= sx(self.W(46)):
                return self.fwd()
            self.SW(12420, 4)
            self.up()
        else:
            if sx(self.d3) <= 1:
                return self.fwd()
            self.SW(12420, 5)
            self.down()
        if self.d1 > 63 or self.d2 > 31:
            return self.lift_fail()
        self.SW(12414, self.W(12414) + 1)
        self.SW(12416, self.W(12416) - 1)
        self.blk()
        if self.m[self.d5] != (self.d3 & 0xff):
            return self.lift_fail()
        self.count()
        if self.d6 != 4:
            return self.lift_fail()
        self.carve(('lift', None))
        d0 = 5 if (self.W(12420) & 0xff) == 4 else 4
        if self.m[G1 + self.d5 + 1] in (0x1f, 0x33):
            d0 += 0x31
        self.SW(G1 + self.d5, d0)
        far = (self.d1, self.d2, self.d3)
        self.restore()
        self.idx()
        d0 = self.W(G1 + self.d5)
        self.d0 = d0
        if d0 == 4 or d0 == 5:
            self.SW(12420, 6)
        elif d0 & 0xff in (0x35, 0x36):
            self.SW(12420, 0x37)
        elif d0 & 0xff in (0x1f, 0x33):
            self.SW(12420, self.W(12420) + 0x31)
        self.SW(G1 + self.d5, self.W(12420))
        self.d1, self.d2, self.d3 = far
        self.SW(13646, self.W(13646) + 1)
        self.trig()
        self.d5 = 0xffff

    def dbf(self, r):
        v = (getattr(self, r) - 1) & 0xffff
        setattr(self, r, v)
        return v != 0xffff

    # $249da
    def room(self):
        self.SW(13654, 0)
        word = self.W(12426)
        self.SW(12428, 6 if word & 0x10 else 2)
        d0 = ror(word, 6) & 0x3f
        if word > 0x3ff7:
            d0 &= 0x1b
        self.SW(13652, 0)
        d6 = rol(word, 2)
        if d6 > self.W(13660):
            self.SW(13652, 0x20)
        self.m[12436] = d0
        self.m[12437] = 0x1f
        if d6 & 0x80 and self.W(12408) > 4 and d0 & 0x24:
            self.m[12437] = 0x33
        d6 = ror(d0, 3) & 7
        a4 = 0
        d0 &= 7
        if d0 and d6:
            a4 += word & 0x38
        if BREAK == 'roomsize':
            d0 = max(d0 - 1, 0)
        self.d0, self.d6 = d0 + 1, d6 + 1
        self.SW(12430, self.d0)
        self.SW(12432, self.d6)
        self.SW(12434, self.W(13584))
        sa = (self.d1, self.d2, self.d3, self.d7)
        self.d5 = 0
        self.step2()
        self.d7 = self.W(12432)
        while True:  # check pass, $24a88
            sb = (self.d1, self.d2, self.d3, self.d7)
            self.d7 = self.W(12430)
            while True:
                self.count()
                if self.W(12434):
                    self.d6 = (self.d6 - 1) & 0xffff
                if self.d6 != 3:  # $24bde: abandon, move forward
                    self.d1, self.d2, self.d3, self.d7 = sa
                    self.d5 = self.W(12424)
                    return self.fwd()
                self.SW(12434, self.W(12434) + 1)
                self.side()
                if not self.dbf('d7'):
                    break
            self.d1, self.d2, self.d3, self.d7 = sb
            self.d5 = 0
            self.step2()
            if not self.dbf('d7'):
                break
        self.d1, self.d2, self.d3, self.d7 = sa
        self.d5 = 0
        self.step2()
        saved7 = self.d7
        rid = self.inst()
        self.d5 = self.W(12432)
        while True:  # carve pass, $24b06
            self.SW(13262, self.d5)
            sc = (self.d1, self.d2, self.d3, self.d4, self.d7)
            self.d7 = self.W(12430)
            b = PAT[a4]
            a4 += 1
            self.SW(13264, (b << 8) | b)
            while True:
                pillar = False
                if self.d7 != 0 and self.W(13262) != 0:
                    v = self.W(13264)
                    self.SW(13264, rol(v, 1))
                    pillar = bool(v & 0x8000) and BREAK != 'pillar'
                if pillar:
                    self.d4 = (self.d4 + 8) & 0xffff
                    self.idx()
                    self.SW(G1 + self.d5, self.W(13652))
                else:
                    self.carve(('room', rid))
                    self.d4 = (self.d4 + 1) & 0xffff
                    self.SW(G1 + self.d5, self.W(12436))
                    self.SW(13210, self.d2)
                    self.SW(13212, self.d1)
                self.side()
                if not self.dbf('d7'):
                    break
            self.d1, self.d2, self.d3, self.d4, self.d7 = sc
            self.d4 = (self.d4 + 8) & 0xffff
            self.d5 = 0
            self.step2()
            self.d5 = self.W(13262)
            if not self.dbf('d5'):
                break
        self.d4 = (self.d4 + 0x48) & 0xffff
        self.d2 = self.W(13210)
        self.d1 = self.W(13212)
        self.d7 = self.W(13208)
        if self.d7:
            self.d7 -= 1
            self.SW(13208, self.d7)
            o = 12952 + 4 * self.d7
            self.m[o] = self.d1 & 0xff
            self.m[o + 1] = self.d2 & 0xff
            self.m[o + 2] = self.d3 & 0xff
            self.m[o + 3] = self.m[12436]
        self.step2()
        self.trig()
        self.d7 = saved7

    # $24c5c
    def structure(self):
        self.fwd()
        self.count()
        if self.d6 != 3:
            return self.trig()
        self.SW(13658, 0x11)
        r = self.rng()
        if rol(r, 8) <= 0x2710 and self.W(12408) != 0:
            self.SW(13658, 0x14)
        self.fence()
        bid = self.inst()
        outer_bid, self.bid = self.bid, bid
        self.restore()
        self.idx()
        here = self.d5
        old = self.W(G0 + here)
        self.SW(G0 + here, 0xfffe)
        sp = (self.d1, self.d2, self.d3)
        self.d5 = self.W(12424)
        self.fwd()
        self.carve(('blob', bid))
        self.SW(G1 + self.d5, self.W(13658))
        self.blob()
        self.bid = outer_bid
        self.d1, self.d2, self.d3 = sp
        self.idx()
        self.SW(G0 + self.d5, old)
        for i in range(2048):  # $24d60
            if self.W(G0 + 2 * i) == 0xfffe:
                self.SW(G0 + 2 * i, 0)
        self.d6 = 0
        self.d0 = 0xffff
        self.d5 = 0
        self.trig()

    def fence(self):  # $24d2c
        s = (self.d1, self.d2, self.d3, self.d4)
        for x in range(63, -1, -1):
            for y in range(31, -1, -1):
                self.d1, self.d2 = x, y
                self.count()
                if self.d6 != 0 and self.d6 != 4:
                    self.idx()
                    if self.W(G0 + self.d5) == 0:
                        self.SW(G0 + self.d5, 0xfffe)
        self.d1, self.d2, self.d3, self.d4 = s

    def blob(self):  # $24cd4
        s7 = self.d7
        self.d7 = 49
        draw = True
        while True:
            if draw:
                self.rng()
            self.d5 = self.W(12424)  # $2484e
            self.save()
            self.d0 &= 3
            if self.d0 == 0:
                self.d5 = (self.d5 - 2) & 6
            elif self.d0 == 1:
                self.d5 = (self.d5 + 2) & 6
            self.fwd()
            bad = self.d1 > 63 or self.d2 > 31
            if not bad:
                self.idx()
                v = self.W(G0 + self.d5)
                bad = v > 0xfffc
            if bad:
                self.restore()
                self.d0 = ror(self.rng(), 5) & 1
                draw = False
                if not self.dbf('d7'):
                    break
                continue
            if v == 0:
                self.carve(('blob', self.bid))
                self.SW(G1 + self.d5, self.W(13658))
                self.trig()
            draw = True
            if not self.dbf('d7'):
                break
        self.d7 = s7
        self.d5 = 0

    # $24d96
    def trig(self):
        sv = (self.d0, self.d1, self.d2, self.d3, self.d5, self.d6, self.d7)
        self.m[13286] = 0xff
        for g in range(5):
            self.group(13360 + 10 * g)
        self.d0, self.d1, self.d2, self.d3, self.d5, self.d6, self.d7 = sv
        if self.W(13286) & 0x8000:
            return
        self.d1 = self.W(13286)
        self.d2 = self.W(13288)
        self.floor_of()
        self.d7 = 10
        self.d5 = 0xffff

    def group(self, base):  # $24dda
        self.m[13570:13574] = (0x20376 + base).to_bytes(4, 'big')  # move.l A2,13570(A6)
        for e in range(5):
            p = base + 2 * e
            if self.W(p) & 0x8000:
                continue
            self.d1, self.d2 = self.m[p], self.m[p + 1]
            self.d6 = 0
            self.nbrs()
            if self.d6 != 2:
                continue
            tid = self.inst()
            self.carve(('trig', tid))
            self.SW(G1 + self.d5, 0x0f)
            self.SW(p, 0xffff)
            self.d1, self.d2 = self.m[p + 100], self.m[p + 101]
            self.carve(('trig', tid))
            self.d1, self.d2 = self.m[p + 50], self.m[p + 51]
            self.carve(('trig', tid))
            self.SW(G1 + self.d5, 0x1d)
            for e2 in range(5):
                q = base + 2 * e2
                if self.W(q) & 0x8000:
                    continue
                self.d1, self.d2 = self.m[q], self.m[q + 1]
                self.d6 = 0
                self.nbrs()
                if self.d6 == 3:
                    self.carve(('trig', tid))
                    self.SW(13286, self.d1)
                    self.SW(13288, self.d2)
                    self.SW(G1 + self.d5, 0x0f)
                self.SW(q, 0xffff)
            return

    def randcell(self):  # $244a2
        r = self.rng()
        self.d1 = r & 63
        self.d2 = ror(r, 6) & 31

    # $244b6
    def run(self):
        want = 2 if BREAK == 'carve2' else 3
        self.SW(13584, 0)
        self.SW(13656, 0)
        self.d1 = self.W(32)
        self.d2 = 0
        self.d3 = self.W(34)
        self.d4 = 1
        self.SW(12414, 300)
        self.SW(12416, 900)
        self.d5 = 0 if self.m[13276] & 1 else 2
        self.SW(12424, self.d5)
        self.carve(('entry', None))
        self.SW(G1 + self.d5, 0x0f)
        st = 'carve'
        while True:
            if st == 'carve':  # $244f0
                self.carve(('corr', None))
                st = 'new'
            if st == 'new':  # $244f4
                self.d7 = 9
                self.SW(12426, self.rng())
                st = 'try'
            if st == 'try':  # $244fe
                if self.d4 > 0x3000:
                    return 'd4'
                self.step()
                if self.d5 == 0xffff:
                    st = 'new'
                    continue
                self.count()
                if self.d6 == want:
                    st = 'carve'
                    continue
                self.restore()
                self.d0 = self.rng() & 3
                if self.dbf('d7'):
                    continue
                st = 'restart'
            if st == 'restart':  # $2452a
                self.d7 = 99
                st = 'r2'
            if st == 'r2':  # $2452e
                self.randcell()
                if self.d4 > 0x3000:
                    return 'd4'
                if self.rng2() > 0xa200:
                    d0, _ = self.open()
                    if d0 == 0:
                        if self.W(12416) & 0x8000:
                            return 'lifts'
                        if self.m[G1 + self.d5 + 1] in RESTART_FEATS:  # $2458a: a lift from a carved cell
                            self.d0 = 3 if self.m[12427] & 0x10 else 2
                            self.floor_of()
                            self.m[12426] = 0xff
                            self.d7 = 0
                            self.SW(12414, self.W(12414) - 1)
                            st = 'try'
                            continue
                self.count()  # $245a8
                if self.d6 == want:
                    self.floor_of()
                    self.SW(12414, self.W(12414) - 1)
                    if self.W(12414) & 0x8000:
                        return 'restarts'
                    st = 'carve'
                    continue
                if self.dbf('d7'):
                    continue
                self.SW(12414, self.W(12414) - 1)
                if self.W(12414) & 0x8000:
                    return 'restarts'
                st = 'restart'


REGIONS = [('g0', G0, 4096), ('g1', G1, 4096), ('g2', 8280, 4096), ('rooms', 12952, 256), ('rng', 12404, 2)]


def region_of(off):
    for n, a, k in REGIONS:
        if a <= off < a + k:
            return n
    return f'var{off}'


def load(paths):
    from dig_capture import records
    for p in paths:
        yield from records(p)


def gate(paths):
    ok = 0
    n = 0
    cats = {}
    ends = {}
    for seed, d2, steps, regs, pre, post in load(paths):
        n += 1
        d = Dig(pre)
        try:
            end = d.run()
        except Exception as e:  # a port bug must show as a category, not stop the census
            cats.setdefault(f'exception {type(e).__name__}', []).append(seed)
            continue
        mine = [d.d1, d.d2, d.d3, d.d4, d.d5, d.d6, d.d7]
        emu = [r & 0xffff for r in regs[1:8]]
        diff = [i for i in range(len(post)) if d.m[i] != post[i]]
        if not diff and mine == emu:
            ok += 1
            ends[end] = ends.get(end, 0) + 1
            continue
        if diff:
            key = 'first diff in ' + region_of(diff[0])
        else:
            key = 'registers ' + ','.join(f'd{i + 1}' for i in range(7) if mine[i] != emu[i])
        cats.setdefault(key, []).append(seed)
    lab = f' (broken: {BREAK})' if BREAK else ''
    print(f'match {ok}/{n}{lab}: whole module block A6..A6+$35bc (G0, G1, G2, room list, RNG words) and D1-D7 '
          f'at the return from $244b6')
    print('  matched runs by what ended the dig (D4 > $3000, restart budget 12414(A6), lift budget 12416(A6)):', ends)
    for k, v in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        print(f'  {k}: {len(v)} seeds, first {v[:8]}')


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--break' in args:
        i = args.index('--break')
        BREAK = args[i + 1]
        del args[i:i + 2]
    if args[0] == 'gate':
        gate(args[1:])
    elif args[0] == 'tree':
        from tree import census
        census(list(load(args[1:])))

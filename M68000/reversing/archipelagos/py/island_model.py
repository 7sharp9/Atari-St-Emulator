#!/usr/bin/env python3
"""island_model.py: model of Archipelagos' island builder $15a20 (procedural path, $15a82..$15b8e).

Input: the 21-word parameter block at $1697a (+ the state words $16a32/34/36 and the 8-word neighbour
offset table at $16a42), read from a snapshot taken at the $15a20 entry. Output: the 64K byte map at $3000
(index = y*256 + x). The model works on a copy of the whole 1 MB RAM because the circle/rectangle shapes
index with sign-extended 16-bit offsets that can leave the 64K array.

usage: uv run python reversing/archipelagos/py/island_model.py <entry.snap> <exit.snap>
       (snapshots from py/capture_islands.sh, under scratchpad/archipelagos/)   -> prints matching cells / 65536.
Environment: BUG=1 adds 1 to the RNG step (the broken-model control); PARAMS="hex words" overrides the block;
PNG=<path> writes the model's map as a grey PNG.
"""
import os, sys
d = os.path.abspath(os.path.dirname(__file__))
while not os.path.exists(os.path.join(d, 'tools', 'rdis.py')):
    d = os.path.dirname(d)
sys.path.insert(0, os.path.join(d, 'tools'))

BASE = 0x3000
def s16(x): x &= 0xFFFF; return x - 0x10000 if x & 0x8000 else x
def s8(x): x &= 0xFF; return x - 0x100 if x & 0x80 else x

class Model:
    def __init__(self, ram, bug=0):
        self.m = bytearray(ram)
        self.bug = bug
        w = lambda a: self.m[a] << 8 | self.m[a + 1]
        self.P = {a: w(a) for a in range(0x1697a, 0x169a4, 2)}
        self.tab = bytes(self.m[0x1698c:0x1698c + 24])           # four 6-byte entries
        self.W32, self.W34, self.W36 = w(0x16a32), w(0x16a34), w(0x16a36)
        self.offs = [s16(w(0x16a42 + 2 * i)) for i in range(8)]
        self.N = w(0x1d566)
        self.s = self.P[0x1698a]                                  # $15a96: seed := $1698a
        self.dir_prev = 1                                         # $16a3a := 1 at $15a8e
        self.dir_now = 0
        self.flag = 0                                             # $16a30
        self.D3 = 0
        # special-island table at $16a58: (word key, 4 bytes) up to a 0 key
        a = 0x16a58; self.special = []
        while w(a): self.special.append(w(a)); a += 6
        self.shapes = {'walk':0,'wander':0,'circle':0,'rect':0}
        self.q = []                                               # ring queue at $1e0fe
    # --- helpers
    def rnd(self):                                                # $16622
        self.s = (5 * self.s + 1 + self.bug) & 0xFFFF
        return self.s
    def sc(self, m):                                              # $16050 on the seed
        return ((self.s & 0xFF) * (m & 0xFF)) // 255
    def nb(self, idx):                                            # $15fe6: any of 8 neighbours has bit 7
        a = BASE + idx
        for o in (1, -1, -257, -256, -255, 255, 256, 257):
            if self.m[a + o] & 0x80: return 1
        return 0
    def mark_all(self):                                           # $15c9a / $15d76: non-4 cells |= $80
        for i in range(BASE, BASE + 0x10000):
            if self.m[i] != 4: self.m[i] |= 0x80
    # --- main
    def run(self):
        assert self.N not in self.special, 'island N is in the special table $16a58 (not procedural)'
        for i in range(BASE, BASE + 0x10000): self.m[i] = 4
        P = self.P
        D1 = P[0x1697a]
        while True:
            D7 = (P[0x1697a] - D1 + 1) & 0xFFFF                   # $16062
            for k in range(4):
                if int.from_bytes(self.tab[6*k+4:6*k+6], 'big') == D7:
                    self.W34 = self.tab[6*k]; self.W32 = self.tab[6*k+1]
                    self.W36 = int.from_bytes(self.tab[6*k+2:6*k+4], 'big'); break
            self.rnd(); d3lo = self.sc(self.W32 & 0xFF) & 0xFF
            self.rnd(); d2 = ((self.sc(self.W34 & 0xFF) & 0xFF) << 8) | d3lo
            d2 = (d2 + self.W36) & 0xFFFF; D3 = d2
            self.rnd(); D4lo = self.sc(P[0x1697e]) & 0xFF
            self.rnd(); D4 = ((self.sc(P[0x1697c]) & 0xFF) << 8) | D4lo
            self.shape(D3, D4)
            D1 = (D1 - 1) & 0xFFFF
            if D1 == 0: break
        self.final_pass()
        return bytes(self.m[BASE:BASE + 0x10000])
    def shape(self, D3, D4):                                      # $15b90
        P = self.P
        self.flag = 0
        self.rnd()
        if s16(self.sc(100)) >= s16(P[0x16988]) : pass
        else: self.flag = 1
        self.rnd(); r = self.sc(100)
        if r < P[0x16980]: self.shapes['walk'] += 1; self.walk(D3, D4)
        elif r < P[0x16982]: self.shapes['wander'] += 1; self.wander(D3, D4)
        elif r < P[0x16984]: self.shapes['circle'] += 1; self.circle(D3, D4)
        else: self.shapes['rect'] += 1; self.rect(D3, D4)
    def walk(self, D3, D4):                                       # $15c00
        m = self.m
        if m[BASE + D3] & 0x80 or self.nb(D3): return
        D7 = 0
        while True:
            saved = D3
            D7 &= 0xFF00
            while (D4 & 0xFF) != (D7 & 0xFF):
                r = self.rnd()
                if r < 0x4000: D3 = (D3 & 0xFF00) | ((D3 + 1) & 0xFF)
                elif r < 0x8000: D3 = (D3 & 0xFF00) | ((D3 - 1) & 0xFF)
                elif r < 0xC000: D3 = (D3 + 0x100) & 0xFFFF
                else: D3 = (D3 - 0x100) & 0xFFFF
                if self.flag != 1 and self.nb(D3): break
                m[BASE + D3] = 6
                D7 = (D7 & 0xFF00) | (((D7 & 0xFF) + 1) & 0xFF)
            D3 = saved
            D7 = (D7 + 0x100) & 0xFFFF
            if (D7 & 0xFF00) == (D4 & 0xFF00): break
        self.mark_all()
    def wander(self, D3, D4):                                     # $15cb8
        m = self.m
        if m[BASE + D3] & 0x80 or self.nb(D3): return
        D5 = D4 >> 8
        D4 = (D4 & 0xFF00) | (((D4 & 0xFF) + D5) & 0xFF)
        D4 = (((D4 & 0xFF) << 3) + 0x12C) & 0xFFFF
        D7 = 0
        while D4 != D7:
            r = self.rnd()
            if r < 0x4000: dd = 1
            elif r < 0x8000: dd = 0xFFFF
            elif r < 0xC000: dd = 0x100
            else: dd = 0xFF00
            if dd == self.dir_prev: continue
            self.dir_prev = dd
            D3 = (D3 + dd) & 0xFFFF
            if self.flag == 1 or not self.nb(D3): m[BASE + D3] = 6
            D7 += 1
        self.mark_all()
    def setbit(self, addr, bit): self.m[addr] |= bit
    def circle(self, D3, D4):                                     # $15d94
        D3 = (D3 - 0x8000) & 0xFFFF
        cen = 0xB000 + s16(D3)
        D4 = (D4 & 0xFF) >> 2
        D5 = D4; D4 = (D4 >> 1); D4 = (D4 + D5) & 0xFF
        if not (s16(D4) > 3): D4 = 4
        if not (s16(D4) < 0x19): D4 = 25
        D5 = (3 - 2 * D4) & 0xFFFF; D7 = 0
        while True:
            if s16(D7) > s16(D4): break
            if s16(D5) > 0:
                D6 = D5; D5 = ((D7 - D4) * 4 + 10 + D6) & 0xFFFF; D7 += 1; D4 -= 1
            else:
                D6 = D5; D5 = (D7 * 4 + 6 + D6) & 0xFFFF; D7 += 1
            d = (((D4 << 8) | (D7 & 0xFF)) - 0x101) & 0xFFFF
            def hit(): self.m[(cen + s16(d)) & 0xFFFFF] |= 0x40
            hit(); d = ~d & 0xFFFF; hit(); d ^= 0xFF; hit(); d = ~d & 0xFFFF; hit()
            d = ((d << 8) | (d >> 8)) & 0xFFFF; hit(); d = ~d & 0xFFFF; hit(); d ^= 0xFF; hit(); d = ~d & 0xFFFF; hit()
        self.fill(D3, cen)
    def rect(self, D3, D4):                                       # $15eee
        D5 = (D4 >> 8) & 0xFF
        def asrb(x, n): return (x & 0xFF00) | ((s8(x) >> n) & 0xFF)
        D6 = D5; D5 = asrb(D5, 2); D6 = D5 & 0xFF  # D6.b := D5.b after first shift
        D6 = D5 & 0xFF; D5 = asrb(D5, 1); D5 = (D5 & 0xFF00) | ((D5 + D6) & 0xFF)
        D6 = D4 & 0xFF; D4 = asrb(D4, 1); D6 = D4 & 0xFF
        D4 = asrb(D4, 1); D4 = (D4 & 0xFF00) | ((D4 + D6) & 0xFF)
        if not (s8(D5) > 4): D5 = (D5 & 0xFF00) | 5
        if not (s8(D4) > 4): D4 = (D4 & 0xFF00) | 5
        D3 = (D3 - 0x8000) & 0xFFFF
        cen = 0xB000 + s16(D3)
        D6 = D3; D4 &= 0xFF; D5 &= 0xFF; D2 = D4; D0 = D5
        D5 = asrb(D5, 1); D4 = asrb(D4, 1)
        D5 = (((D5 << 8) & 0xFFFF) | (D4 & 0xFF))
        D6 = (D6 - D5) & 0xFFFF
        A3 = 0xB000 + s16(D6)
        o = lambda a, off: self.m.__setitem__((a + s16(off)) & 0xFFFFF, self.m[(a + s16(off)) & 0xFFFFF] | 0x40)
        for i in range(D2 - 1, -1, -1): o(A3, i)
        D5 = 0
        for _ in range(D0): o(A3, D5); D5 = (D5 + 0x100) & 0xFFFF
        A3 += s16(D5)
        for i in range(D2 - 1, -1, -1): o(A3, i)
        D5 = 0; A3 += s16(D2); n = D0 - 1
        for _ in range((n & 0xFFFF) + 1): o(A3, D5); D5 = (D5 - 0x100) & 0xFFFF
        self.fill(D3, cen)
    def fill(self, D3, cen):                                      # $15e3a
        m = self.m
        m[cen] |= 0x20
        q = [D3]; A1 = 0xB000
        while q:
            D0 = q.pop(0)
            D7 = 0; A2 = A1 + s16(D0)
            for D2 in range(8, 0, -1):
                D5 = self.offs[8 - D2]
                a = A2 + D5
                if not (m[a] & 0x20) and not (m[a] & 0x40) and D2 > 4:
                    m[a] |= 0x20; q.append((D0 + D5) & 0xFFFF)
                if m[a] & 0x80: D7 = 1
            if D7 != 1: m[A2] |= 6
        for i in range(BASE, BASE + 0x10000): m[i] &= 0x1F
        for i in range(BASE, BASE + 0x10000):
            if m[i] != 4: m[i] |= 0x80
    def final_pass(self):                                         # $15b16
        m = self.m; a = BASE; D7 = 6
        for row in range(256):
            for col in range(256):
                v = m[a] & 7
                if v == 6:
                    if any((m[a + o] & 7) == 4 for o in (1, -1, 256, -256)): v = 5
                    else: v = D7
                m[a] = v; a += 1; D7 ^= 1
            D7 ^= 1

if __name__ == '__main__':
    from gfxview import load_ram
    bug = int(os.environ.get('BUG', '0'))
    ent, ex = sys.argv[1], sys.argv[2]
    ram, _ = load_ram(ent); live, _ = load_ram(ex)
    ram = bytearray(ram)
    for i, v in enumerate(os.environ.get('PARAMS', '').split()):   # the labelled poke, applied to the block
        ram[0x1697a + 2 * i: 0x1697c + 2 * i] = int(v, 16).to_bytes(2, 'big')
    M = Model(ram, bug); out = M.run()
    from collections import Counter
    print('shapes called', M.shapes, 'cells', dict(Counter(out)))
    if os.environ.get('PNG'):
        from PIL import Image
        Image.frombytes('L', (256, 256), bytes(min(255, (c - 4) * 60) for c in out)).save(os.environ['PNG'])
    ref = bytes(live[BASE:BASE + 0x10000])
    ok = sum(a == b for a, b in zip(out, ref))
    print(f'{os.path.basename(ent)}: {ok}/65536 cells match' + (f' (BUG={bug})' if bug else ''))

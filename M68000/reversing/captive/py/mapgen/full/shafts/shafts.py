"""Python port of fed_MapGen's shaft layout $245e2, room reservations $263c2, the reservation clear $24d78 and the
second room pass $263fa, and their gates against the emulator.

    uv run python -I reversing/captive/py/mapgen/full/shafts/shafts.py gate <capture.bin> [...] [--break <name>]
    uv run python -I reversing/captive/py/mapgen/full/shafts/shafts.py chain <capture.bin> [...]      # D0 alone -> state after $263fa
    uv run python -I reversing/captive/py/mapgen/full/shafts/shafts.py stats <capture.bin> [...]      # shaft / reservation census

Runtime addresses, module at $1f7b0, variables at A6 = $20376, A0 = G0 = 56(A6), A3 = G1 = 4168(A6).
The port extends the digger port (../../digger/dig.py, class Dig): the room builder $249da there handles mode 0 only;
here it takes the mode word 13584(A6) as the code does (0 = digger room, 1 = reservation, 2 = second pass).

Routines:
  $245e2 shafts    clear the three shaft lists 13360/13410/13460(A6) to $ffff, run $24606, copy the 25 words at
                   13460(A6) (the $18 cells) to the federation table at the pointer 13712(A6)
  $24606 groups    G = min(D0/2 - 1, 4) + 1 groups (none when D0 <= 1); for each, random cells until one is rock on
                   a base floor and $2465e accepts a chain that is not exactly one entry long
  $2465e chain     dry run: from the cell, an entry ($24754) on this floor, then the same cell translated by the
                   floor pair's lift offset ($2514c) on the next floor, while that cell is on the next floor's block
                   and rock; up to 6 entries. Two or more: place them (the same $24754 with 13574(A6) set) and list
                   them; one: reject; none: accept an empty group
  $24754 entry     three cells in a row pointing to the block's centre (x & 15 <= 7: east): $1c (G0 2), $18 (G0 1),
                   door $0f (G0 $ffff), the first two walled above and below and the $1c cell behind ($24718)
  $263c2 reserve   mode 1; for D0 = 0 one room, for D0 with bit 1 set count_2640a(~D0) + 1 rooms, else none; each
                   at a random cell with the LCG state as the step word, written as G0 = $fffd (no feature)
  $24d78 unreserve G0 $fffd -> 0 (via $24d64)
  $263fa pass 2    mode 2; count_2640a(D0) + 1 rooms over the carved base, written as feature $23, G0 $ffc4 on
                   cells with no G1 word, only where the rectangle is in the grid, holds no wall/door/reserved cell
                   and overlaps at least one carved cell
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'digger'))  # dig.py
import dig  # noqa: E402
from dig import Dig, G0, G1, PAT, ror, rol, sx  # noqa: E402

BREAK = None


class Gen(Dig):
    # ---- $245e2 and callees
    def shafts(self):
        for i in range(75):
            self.SW(13360 + 2 * i, 0xffff)
        self.groups()
        fed = bytes(self.m[13460:13510])
        return fed

    def ok_2482e(self):  # $2482e: Z set (False) unless D3 <= floors, in the grid and rock
        if sx(self.d3) > sx(self.W(46)):
            self.d0 = 0
            return False
        if self.d1 > 63 or self.d2 > 31:
            self.d0 = 0
            return False
        self.idx()
        _, z = self.open()
        return not z

    def groups(self):  # $24606
        a2 = 13360
        d7 = self.W(12408)
        if d7 <= 1:
            return
        d7 = (d7 >> 1) - 1
        if d7 > 4:
            d7 = 4
        while True:
            while True:
                self.randcell()
                self.floor_of()
                if not self.ok_2482e():
                    continue
                self.idx()
                if self.W(G0 + self.d5):
                    continue
                self.chain(a2)
                if self.W(13290) == 1:
                    continue
                break
            a2 += 10
            d7 -= 1
            if d7 < 0:
                break
        self.d7 = 0xffff

    def wall(self):  # $24718: True = ok
        if self.d1 > 63 or self.d2 > 31:
            self.d0 = 0
            return True
        if self.d2 == 0:
            self.d0 = 0xffff
            return False
        self.idx()
        if self.W(G1 + self.d5):
            return False
        v = self.W(G0 + self.d5)
        if v == 0xffff:
            return True
        if v:
            return False
        if self.W(13574) == 0:
            return True
        self.SW(G0 + self.d5, 0xffff)
        self.d0 = 0
        return True

    def entry(self):  # $24754: True = ok
        place = self.W(13574) != 0
        dr = self.W(13578)
        if self.d2 == 0:
            return self.fail()
        self.idx()
        if self.W(G0 + self.d5):
            return self.fail()
        if place:
            self.SW(G1 + self.d5, 0x1c)
            self.SW(G0 + self.d5, 2)
        moves = [(-dr, 0), (dr, -1), (dr, 0), (0, 2), (-dr, 0)]
        for dx, dy in moves:
            self.d1 = (self.d1 + dx) & 0xffff
            self.d2 = (self.d2 + dy) & 0xffff
            if not self.wall():
                return self.fail()
        self.d2 = (self.d2 - 1) & 0xffff
        self.d1 = (self.d1 + dr) & 0xffff
        if self.d1 > 63:
            return self.fail()
        self.idx()
        if self.W(G0 + self.d5):
            return self.fail()
        self.SW(13292, self.d1)
        self.SW(13294, self.d2)
        if place:
            self.SW(G1 + self.d5, 0x18)
            self.SW(G0 + self.d5, 1)
        self.d1 = (self.d1 + dr) & 0xffff
        if self.d1 > 63:
            return self.fail()
        self.idx()
        if self.W(G0 + self.d5):
            return self.fail()
        if place and BREAK != 'nodoor':
            self.SW(G1 + self.d5, 0x0f)
            self.SW(G0 + self.d5, 0xffff)
        self.d0 = 0
        return True

    def fail(self):
        self.d0 = 0xffff
        return False

    def up_check(self):  # $2480a: True (Z clear) = carry on up
        if sx(self.d3) >= sx(self.W(46)):
            self.d6 = 0
            return False
        self.up()
        self.blk()  # $249c4: cmp.b block byte, D3
        if self.m[self.d5] != (self.d3 & 0xff):
            self.d6 = 0
            return False
        self.d6 = 1
        return self.ok_2482e()

    def chain(self, a2):  # $2465e
        self.SW(13290, 0)
        self.SW(13578, 1)
        if (self.d1 & 15) > 7:
            self.SW(13578, 0xffff)
        if BREAK == 'dir':
            self.SW(13578, (-sx(self.W(13578))) & 0xffff)
        for i in range(60):
            self.m[13510 + i] = 0xff
        a4 = 13510
        self.SW(13574, 0)
        while True:
            if self.W(13290) > 5:
                break
            self.SW(a4, self.d1)
            self.SW(a4 + 2, self.d2)
            a4 += 4
            if not self.entry():
                break
            self.SW(13290, self.W(13290) + 1)
            self.SW(a4, self.d1)
            self.SW(a4 + 2, self.d2)
            self.m[a4 + 4:a4 + 8] = self.m[13292:13296]
            a4 += 8
            self.d1 = self.W(a4 - 12)
            self.d2 = self.W(a4 - 10)
            if not self.up_check():
                break
        if sx(self.W(13290)) <= 1:
            self.d0 = 0
            return
        a4 = 13510
        d7 = self.W(13290)
        self.SW(13290, 0)
        d7 -= 1
        self.m[13574] = 0xff
        while True:
            self.d1 = self.W(a4)
            if self.d1 & 0x8000:
                break
            self.d2 = self.W(a4 + 2)
            self.m[a2 + 50] = self.d1 & 0xff
            self.m[a2 + 51] = self.d2 & 0xff
            self.m[a2 + 100] = self.m[a4 + 9]
            self.m[a2 + 101] = self.m[a4 + 11]
            self.m[a2] = self.m[a4 + 5]
            self.m[a2 + 1] = self.m[a4 + 7]
            a2 += 2
            self.entry()
            a4 += 12
            d7 -= 1
            if d7 < 0:
                break
        self.d7 = 0xffff
        self.d0 = 0

    # ---- $263c2 / $263fa
    def count_2640a(self, d7):
        d6 = 0
        if d7 > 7:
            while True:
                d6 += 8
                d7 = ((d7 - 8) & 0xffff) >> 1
                if d7 <= 7:
                    break
            d7 = (d7 + d6) & 0xffff
        v = self.W(12408)
        while True:
            p = (v & 0xffff) * 0x5e5
            lo = (p & 0xffff) + 0x29
            c = lo > 0xffff
            v = (p & 0xffff0000) | (lo & 0xffff)
            if c or not (v & 0x20):
                self.d6 = v & 0xffffffff
                return d7
            d7 >>= 1

    def rooms_loop(self, d7):  # $263da
        saved = self.W(12404)
        while True:
            self.randcell()
            self.SW(12426, self.W(12404))
            self.d7 = d7
            self.room()
            d7 = (d7 - 1) & 0xffff
            if d7 == 0xffff:
                break
        self.d7 = d7
        self.SW(12404, saved)

    def reserve(self):  # $263c2
        self.SW(13584, 1)
        d7 = self.W(12408)
        if d7:
            if not d7 & 2:
                self.d7 = d7
                return
            d7 = self.count_2640a((~d7) & 0xffff)
        if BREAK == 'nores':
            return
        self.rooms_loop(d7)

    def unreserve(self):  # $24d78 -> $24d64 with D5 = $fffd, D6 = 0
        for i in range(2048):
            if self.W(G0 + 2 * i) == 0xfffd:
                self.SW(G0 + 2 * i, 0)
        self.d5, self.d6, self.d0 = 0xfffd, 0, 0xffff

    def pass2(self):  # $263fa
        self.SW(13584, 2)
        d7 = self.count_2640a(self.W(12408))
        self.rooms_loop(d7)

    # ---- $249da with the mode word
    def room(self):
        mode = self.W(13584)
        if mode == 0:
            return Dig.room(self)
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
        self.SW(12434, mode)
        sa = (self.d1, self.d2, self.d3, self.d7)

        def abandon():
            self.d1, self.d2, self.d3, self.d7 = sa
            self.d5 = self.W(12424)
            return self.fwd()

        self.d5 = 0
        self.step2()
        self.d7 = self.W(12432)
        while True:  # check pass $24a88
            sb = (self.d1, self.d2, self.d3, self.d7)
            self.d7 = self.W(12430)
            while True:
                if mode == 1:
                    if self.d2 == 0:
                        return abandon()
                    self.count()
                    if self.W(12434):
                        self.d6 = (self.d6 - 1) & 0xffff
                    if self.d6 != 3:
                        return abandon()
                else:
                    d0v, z = self.open()
                    if z:
                        if d0v:
                            return abandon()
                        self.SW(13654, self.W(13654) + 1)
                self.SW(12434, self.W(12434) + 1)
                self.side()
                if not self.dbf('d7'):
                    break
            self.d1, self.d2, self.d3, self.d7 = sb
            self.d5 = 0
            self.step2()
            if not self.dbf('d7'):
                break
        if mode > 1 and self.W(13654) == 0 and BREAK != 'nooverlap':
            return abandon()
        self.d1, self.d2, self.d3, self.d7 = sa
        self.d5 = 0
        self.step2()
        saved7 = self.d7
        self.d5 = self.W(12432)
        while True:  # carve pass $24b06
            self.SW(13262, self.d5)
            sc = (self.d1, self.d2, self.d3, self.d4, self.d7)
            self.d7 = self.W(12430)
            b = PAT[a4]
            a4 += 1
            self.SW(13264, (b << 8) | b)
            while True:
                self.idx()
                if mode == 1:
                    self.SW(G0 + self.d5, 0xfffd)
                    self.SW(13210, self.d2)
                    self.SW(13212, self.d1)
                elif self.W(G1 + self.d5) == 0:
                    self.SW(G1 + self.d5, 0x23)
                    self.SW(G0 + self.d5, 0xffc4)
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
        self.d7 = saved7


# ---------------------------------------------------------------- gates
def load(paths):
    from capture import records
    for p in paths:
        yield from records(p)


def diff(a, b):
    return [i for i in range(len(b)) if a[i] != b[i]]


def regs_of(g):
    return [g.d1, g.d2, g.d3, g.d4, g.d5, g.d6, g.d7]


def gate(paths):
    res = {'245e2': [0, 0, []], '263c2': [0, 0, []], '263fa': [0, 0, []]}
    acted = {'245e2': 0, '263c2': 0, '263fa': 0}
    fedok = 0
    for rec in load(paths):
        st = rec['st']
        # $245e2: from the state at $23ca4 to $23ca8 (block + the 50 federation bytes)
        g = Gen(st[0x23ca4][1])
        fed = g.shafts()
        d = diff(g.m, st[0x23ca8][1])
        r = res['245e2']
        r[1] += 1
        if not d and fed == rec['fed']:
            r[0] += 1
        elif len(r[2]) < 8:
            r[2].append((rec['d2'], rec['seed'], d[:6], fed == rec['fed']))
        fedok += fed == rec['fed']
        acted['245e2'] += st[0x23ca4][1] != st[0x23ca8][1]
        acted['263c2'] += st[0x23ca8][1][:12404] + st[0x23ca8][1][12406:] != st[0x23cb0][1][:12404] + st[0x23cb0][1][12406:]
        acted['263fa'] += st[0x23ccc][1] != st[0x23cd0][1]
        # $263c2: from $23ca8 with the RNG word restored ($23ca8: move.w (A7)+,12404(A6)) to $23cb0
        pre = bytearray(st[0x23ca8][1])
        pre[12404:12406] = st[0x23ca4][1][12404:12406]
        g = Gen(pre)
        g.d1, g.d2, g.d3, g.d4, g.d5, g.d6, g.d7 = [v & 0xffff for v in st[0x23ca8][0][1:8]]
        g.reserve()
        d = diff(g.m, st[0x23cb0][1])
        r = res['263c2']
        r[1] += 1
        if not d:
            r[0] += 1
        elif len(r[2]) < 8:
            r[2].append((rec['d2'], rec['seed'], d[:6]))
        # $263fa: $23ccc -> $23cd0
        g = Gen(st[0x23ccc][1])
        g.d1, g.d2, g.d3, g.d4, g.d5, g.d6, g.d7 = [v & 0xffff for v in st[0x23ccc][0][1:8]]
        g.pass2()
        d = diff(g.m, st[0x23cd0][1])
        r = res['263fa']
        r[1] += 1
        if not d:
            r[0] += 1
        elif len(r[2]) < 8:
            r[2].append((rec['d2'], rec['seed'], d[:6]))
    lab = f' (broken: {BREAK})' if BREAK else ''
    print(f'$245e2 shafts: match {res["245e2"][0]}/{res["245e2"][1]}{lab} (module block at $23ca8 and the 50 bytes '
          f'at 13712(A6)); federation bytes alone {fedok}')
    print(f'$263c2 reserve: match {res["263c2"][0]}/{res["263c2"][1]}{lab} (module block at $23cb0)')
    print(f'$263fa pass 2: match {res["263fa"][0]}/{res["263fa"][1]}{lab} (module block at $23cd0)')
    print('  cases where the emulator changed the block (RNG word aside for $263c2):', acted)
    for k, v in res.items():
        for b in v[2][:4]:
            print('  miss', k, b)


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--break' in args:
        i = args.index('--break')
        BREAK = args[i + 1]
        dig.BREAK = BREAK if BREAK in ('roomsize',) else None
        del args[i:i + 2]
        import shafts as _self  # chain.py imports this file as `shafts`: give that copy the same control
        _self.BREAK = BREAK
    if args[0] == 'gate':
        gate(args[1:])
    elif args[0] == 'chain':
        from chain import chain
        chain(list(load(args[1:])))
    elif args[0] == 'stats':
        from stats import stats
        stats(list(load(args[1:])))

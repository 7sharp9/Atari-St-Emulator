"""Populous II computer god `ai_run_sides` $25652 as an executable model.

A literal port of the routine and its stages, working on a byte image of RAM (the model reads every constant
table out of that image, so nothing is transcribed):

  $25652 ai_run_sides          both side records ($470fe, $47238, stride $13a), command records ($473b0, +10)
  $256d6 ai_flush_mailbox      queued entity command, queued power, walker-obstacle post
  $25770 ai_level_settlement   command 2/4 on a neighbour cell of the settlement named by +46
  $259ba ai_release_settlement command 4 on the strongest own settlement
  $25a32 ai_cast_power         plan-list draw, kind dispatch (tables $25a8c, $25b00), helper $25b72
  $25bf4 ai_magnet_and_mode    command 8 / $10 / mode byte, helper $25db4

`run(ram, d4, d5)` returns {addr: new_byte} for every byte the routine changes, plus a log of what each stage did.
D4/D5 (low bytes) are the entry registers: the kind-4 power post uses them stale ($25b44 -> $25b5e).
"""

SIDE1 = 0x470FE
SIDE_STRIDE = 0x13A
SIDE_END = 0x47372
CMD1 = 0x473B0
ENT = 0x3FF1A
CELLS = 0x3979E
TICK = 0x3979A
SEED = 0x47382


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


class God:
    def __init__(self, ram, d4=0, d5=0, control=None):
        self.control = control or ()  # broken-model controls: names of deliberate one-constant changes
        self.ram = bytearray(ram)
        self.orig = bytes(ram)
        self.d4 = d4 & 0xFF  # low bytes only are ever read from stale values
        self.d5 = d5 & 0xFF
        self.log = []
        self.paths = []

    # memory
    def rb(self, a): return self.ram[a]
    def rw(self, a): return (self.ram[a] << 8) | self.ram[a + 1]
    def rl(self, a): return (self.rw(a) << 16) | self.rw(a + 2)
    def wb(self, a, v): self.ram[a] = v & 0xFF
    def ww(self, a, v): self.ram[a] = (v >> 8) & 0xFF; self.ram[a + 1] = v & 0xFF
    def wl(self, a, v): self.ww(a, (v >> 16) & 0xFFFF); self.ww(a + 2, v & 0xFFFF)

    def p(self, name):
        self.paths.append(name)

    def ent(self, off):  # adda.w D0,A0 on $3ff1a: the word is sign-extended
        return ENT + s16(off & 0xFFFF)

    def rand(self):
        seed = self.rl(SEED)
        if seed == 0:
            seed = 0xBC614E
        seed = (seed * 0xBB40E62D) & 0xFFFFFFFF
        self.wl(SEED, seed)
        return (seed >> 8) & 0x7FFF

    def cell(self, D1):  # D1 = y<<8 | x; the 4-byte cell record address
        return CELLS + ((D1 & 0xFF00) | ((D1 << 2) & 0xFF))

    def corner_h(self, off):  # altitude, +1 when bit 0 of $36b7a[shape]
        h = self.rb(off) & 7
        if self.rb(0x36B7A + self.rb(off + 1)) & 1:
            h += 1
        return h

    def post(self, A5, cmd, x, y):
        self.wb(A5 + 1, cmd); self.wb(A5 + 2, x); self.wb(A5 + 3, y)

    # ------------------------------------------------------------------
    def run(self):
        A1, A5 = SIDE1, CMD1
        while True:
            ctl = self.rw(A1 + 26)
            do_cascade = False
            if ctl == 0x12:
                do_cascade = True
            elif ctl == 4:
                self.ww(A1 + 76, self.rw(A1 + 76) - 1)
                self.flush(A1, A5)
                if not s16(self.rw(A1 + 76)) > 0:
                    self.ww(A1 + 76, self.rw(A1 + 104) + (1 if "reload" in self.control else 0))
                    if self.rb(A5 + 1) == 0:
                        do_cascade = True
            if do_cascade:
                self.cascade(A1, A5)
            A5 += 10
            A1 += SIDE_STRIDE
            if A1 >= SIDE_END:
                break
        return {a: self.ram[a] for a in range(len(self.ram)) if self.ram[a] != self.orig[a]}

    def cascade(self, A1, A5):
        for name, fn in (("level", self.level), ("release", self.release), ("power", self.power),
                         ("magnet", self.magnet)):
            if name == "power" and self.rw(A1 + 26) == 0x12:
                return
            posted = fn(A1, A5)
            self.log.append((A1, name, bool(posted)))
            if posted:
                return

    # $256d6 --------------------------------------------------------
    def flush(self, A1, A5):
        d0 = self.rw(A1 + 54)
        if d0 and not s16(self.rw(A1 + 76)) > 0:
            A0 = self.ent(d0)
            self.p('flush_entity_cmd')
            self.wb(A5 + 1, 2); self.wb(A5 + 2, self.rb(A0 + 6)); self.wb(A5 + 3, self.rb(A0 + 8))
            return 1
        d1 = self.rw(A1 + 56)
        if d1:
            d0 = self.rw(0x30F48 + s16(d1))
            if d1 == 0x32:
                d0 = 0x48
            d0 = self.rw(0x310D0 + d0) * 4
            if s32(d0) >= s32(self.rl(A1)):
                self.p('flush_queued_power_dropped')
                self.ww(A1 + 56, 0); self.ww(A1 + 58, 0)
                return 0
            self.p('flush_queued_power_post')
            self.wb(A5 + 1, d1)
            self.ww(A5 + 2, self.rw(A1 + 58))
            return 1
        if self.rw(A1 + 50):
            self.p('flush_walker_mailbox')
            self.wb(A5 + 1, 2); self.wb(A5 + 2, self.rb(A1 + 53)); self.wb(A5 + 3, self.rb(A1 + 52))
            return 1
        return 0

    # $25770 --------------------------------------------------------
    def level(self, A1, A5):
        d0 = self.rw(A1 + 46)
        if d0 == 0:
            return 0
        self.ww(A1 + 44, self.rw(A1 + 44) - 1)
        if s16(self.rw(A1 + 44)) > 0:
            return 0
        self.ww(A1 + 44, self.rw(0x30730))
        A0 = self.ent(d0)
        d0 = self.rw(0x310D0) * 4 + 2
        if d0 > s32(self.rl(A1)):
            return 0
        D1 = (self.rw(A0 + 8) & 0xFF00) | self.rb(A0 + 6)
        A4 = 0x30732
        c = self.cell(D1)
        D5 = self.corner_h(c)
        D2 = D5
        self.d4 = (D1 << 2) & 0xFF  # D4 = D1, then add.b twice
        self.d5 = D5
        while True:
            D4 = self.rw(A4); A4 += 2
            self.d4 = D4 & 0xFF
            if D4 == 0xFF9D:
                self.p('level_exhausted_sync19')
                self.wb(A0 + 19, self.rb(A0 + 1))
                return 0
            D4 = (D4 + D1) & 0xFFFF
            self.d4 = D4 & 0xFF
            if D4 & 0xC0C0:
                continue
            D4 = (D4 & 0xFF00) | ((D4 << 2) & 0xFF)
            self.d4 = D4 & 0xFF
            node = self.rw(CELLS + D4 + 2)
            skip = False
            while node:
                A6 = self.ent(node)
                if self.rb(A6) != 4 and self.rb(A1 + 25) == self.rb(A6 + 12):
                    skip = True
                    break
                node = self.rw(A6 + 2)
            if skip:
                continue
            D5 = self.corner_h(CELLS + D4)
            self.d5 = D5
            code = self.rb(CELLS + D4 + 1)
            d0 = self.rw(0x3697A + 2 * code)
            if d0 & 0x20:
                self.p('level_raise_flag20')
                D5 = 2
            else:
                if d0 & 0x390:
                    r = self.rand() & 0xF
                    raise_ = r <= 3
                    self.p('level_rand_raise' if raise_ else 'level_rand_pass')
                else:
                    raise_ = False
                if not raise_:
                    if D5 == D2:
                        continue
                    D5 = 4 if D5 > D2 else 2
                    self.p('level_lower' if D5 == 4 else 'level_raise_lower_nb')
                    if "swap" in self.control:
                        D5 = 6 - D5
                else:
                    D5 = 2
            self.d5 = D5
            self.post(A5, D5, (D4 & 0xFF) >> 2, D4 >> 8)
            return 1

    # $259ba --------------------------------------------------------
    def release(self, A1, A5):
        if self.rw(A1 + 28) == 0:
            return 0
        self.ww(A1 + 48, self.rw(A1 + 48) - 1)
        if s16(self.rw(A1 + 48)) > 0:
            return 0
        self.ww(A1 + 48, self.rw(0x30698))
        if self.rw(0x310D0) * 4 > s32(self.rl(A1)):
            return 0
        A0 = self.ent(self.rw(A1 + 30))
        d0 = (self.rw(0x3069A) + (self.rw(0x3069C) if self.rw(A1 + 12) == 0x10 else 0)) & 0xFFFF
        thr = self.rw(0x36D0E + s16(d0)) + (50 if "thr" in self.control else 0)
        if thr >= s32(self.rl(A0 + 26)):
            return 0
        self.p('release_post')
        self.post(A5, 4, self.rb(A0 + 6), self.rb(A0 + 8))
        return 1

    # $25a32 --------------------------------------------------------
    def power(self, A1, A5):
        self.p('power_entered')
        if s32(self.rl(TICK)) < 0xFA:
            return 0
        A4 = 0x47238 if self.rw(A1 + 24) == 1 else SIDE1
        if self.rw(A4 + 28) == 0:
            self.p('power_enemy_has_no_settlement')
            return 0
        D2 = self.rw(A1 + 38)
        if D2 == 0:
            r = self.rand()
            div = self.rw(A1 + 148)
            D2 = (r % div) if div else 0  # a zero divisor would trap; never seen
            D2 = (D2 * 2) & 0xFFFF
            if D2 == 0:
                self.p('power_slot0_none')
                return 0
            D2 = (D2 * 2) & 0xFFFF
        A2 = A1 + s16(D2)
        D1 = self.rw(A2 + 152)
        D3 = self.rw(A2 + 154)
        if D3 == 0x0A:  # table $25a8c entry 5 -> $25a98: gated by the leader's strength and the tick
            D7 = (self.rw(A1 + 106) << 6) & 0xFFFFFFFF
            if s32(D7) < s32(self.rl(TICK)) or not s32(self.rl(A1 + 4)) > s32(self.rl(A4 + 4)):
                self.p('power_kinda_gate_closed')
                self.ww(A1 + 38, 0)
                return 0
        elif D3 not in (0, 2, 4, 6, 8):
            raise ValueError("kind %x outside table $25a8c" % D3)
        cost = self.rw(0x310D0 + self.rw(0x30F48 + D1)) * 4
        if not cost < s32(self.rl(A1)):
            self.p('power_mana_short')
            self.ww(A1 + 38, D2)
            return 0
        self.ww(A1 + 38, 0)
        A0 = self.ent(self.rw(A4 + 30))
        self.p('power_kind%x' % D3)
        if D3 in (0, 0x0A):
            self.post(A5, D1 & 0xFF, self.rb(A0 + 6), self.rb(A0 + 8))
            return 1
        if D3 == 2:
            self.ww(A1 + 56, D1)
            self.wb(A1 + 58, self.rb(A0 + 6)); self.wb(A1 + 59, self.rb(A0 + 8))
            return 0
        if D3 in (4, 6):
            found = self.nearest_land(A0, (3 if 'radius' in self.control else 2) if D3 == 4 else 6)
            if found is None:
                return 0
            self.post(A5, D1 & 0xFF, found[0], found[1])
            return 1
        # D3 == 8: the leader's strength; D4/D5 are whatever the registers held (stale)
        d0 = self.rw(A1 + 8)
        if d0 == 0 or s32(self.rl(ENT + s16(d0) + 26)) < 0x1000:
            self.p('power_k8_leader_weak')
            return 0
        self.post(A5, D1 & 0xFF, self.d4, self.d5)
        return 1

    def nearest_land(self, A0, D7):  # $25b72, literal: D5 and D6 are set once, before the first direction
        D4 = (self.rw(A0 + 8) & 0xFF00) | self.rb(A0 + 6)
        D2, D3 = 0x7FFF, 0
        D6 = D7
        D5 = D4
        A3 = 0x30724
        while True:
            D5 = (D5 + s16(self.rw(A3))) & 0xFFFF
            nxt = False
            if D5 & 0xC0C0:
                nxt = True
            else:
                off = (D5 & 0xFF00) | ((D5 << 2) & 0xFF)
                code = self.rb(CELLS + off + 1)
                if self.rb(0x3697A + 2 * code + 1) & 8:
                    D6 = (D6 - 1) & 0xFFFF
                    if D6 == 0:
                        D4 = (D4 - D5) & 0xFFFF
                        if D4 & 0x8000:
                            D4 = (-D4) & 0xFFFF
                        if not s16(D2) < s16(D4):
                            D2, D3 = D4, D5
                        nxt = True
                else:
                    D6 = D7
            if nxt:
                A3 += 2
                if 'quirk' in self.control:
                    D6 = D7; D5 = D4
                if A3 >= 0x3072C:
                    break
        if D3 == 0:
            return None
        return (D3 & 0xFF, D3 >> 8)

    # $25bf4 --------------------------------------------------------
    def magnet(self, A1, A5):
        A4 = 0x47238 if self.rw(A1 + 24) == 1 else SIDE1
        self.p('magnet_entered')
        lim = self.rw(0x30722)
        mode_change = False
        if not s16(lim) < s16(self.rw(A1 + 36)):  # own settlements <= limit: only leaves mode $10
            if self.rw(A1 + 12) != 0x10:
                self.p('magnet_few_settlements_not_mode10')
                return 0
            mode_change = True
        else:
            d0 = self.rw(A1 + 8)
            if d0 == 0:
                self.p('magnet_no_leader')
                self.reset38(A1)
                if self.rw(A1 + 12) != 0x10:
                    self.ww(A1 + 40, self.rw(0x3072C)); self.wb(A5 + 1, 0x10)
                return self.tail(A1, A5)
            self.p('magnet_leader')
            A0 = self.ent(d0)
            A2 = self.ent(self.rw(A1 + 34))
            A3 = self.ent(self.rw(A1 + 10))
            D3 = 0x1000
            go_post = True
            if not D3 > s32(self.rl(A0 + 26)):
                D1 = self.rw(A1 + 150)
                double = True
                if D1 != 0:
                    d0 = self.rand()
                    d0 = ((d0 % D1) + self.rw(A1 + 148)) & 0xFFFF
                    d0 = (d0 * 4) & 0xFFFF
                    d1 = self.rw(A1 + 38)
                    if d1 == 0 or not s16(d1 >> 2) >= s16(self.rw(A1 + 148)):
                        self.ww(A1 + 38, d0)
                    else:
                        double = False  # bge $25c8a skips the second strength test
                if double:
                    D3 += D3
                if not (double and D3 > s32(self.rl(A0 + 26))):
                    if self.rw(A4 + 32) == 0:
                        return 0
                    A2 = self.ent(self.rw(A4 + 34))
            if self.rb(A3 + 6) != self.rb(A2 + 6) or self.rb(A3 + 8) != self.rb(A2 + 8):
                self.p('magnet_move_cmd8')
                self.post(A5, 8, self.rb(A2 + 6), self.rb(A2 + 8))
                return 1
            if self.rw(A1 + 12) == 0x10:
                self.ww(A1 + 40, self.rw(A1 + 40) - 1)
                if s16(self.rw(A1 + 40)) > 0:
                    return self.tail(A1, A5)
                d1 = (self.rw(A0 + 8) & 0xFF00) | self.rb(A0 + 6)
                code = self.rb(CELLS + ((d1 & 0xFF00) | ((d1 << 2) & 0xFF)) + 1)
                if self.rb(0x3697A + 2 * code + 1) & 1:
                    return self.tail(A1, A5)
                mode_change = True
            else:
                self.ww(A1 + 40, self.rw(A1 + 40) - 1)
                if s16(self.rw(A1 + 40)) > 0:
                    return 0
                self.ww(A1 + 40, self.rw(0x3072C)); self.wb(A5 + 1, 0x10)
                return self.tail(A1, A5)
        if mode_change:
            self.ww(A1 + 40, self.rw(0x3072E))
            self.p('magnet_mode_byte')
            self.wb(A5 + 1, self.rb(0x25DC8 + (self.rb(A1 + 7) & 3)))
            return 1
        return 0

    def reset38(self, A1):  # $25db4
        d0 = self.rw(A1 + 38)
        if d0 and s16(d0 >> 2) >= s16(self.rw(A1 + 148)):
            self.ww(A1 + 38, 0)

    def tail(self, A1, A5):  # $25d3c..$25d88: raise the magnet's own cell when it is sloped / water
        A3 = self.ent(self.rw(A1 + 10))
        d1 = (self.rw(A3 + 8) & 0xFF00) | self.rb(A3 + 6)
        code = self.rb(CELLS + ((d1 & 0xFF00) | ((d1 << 2) & 0xFF)) + 1)
        if self.rw(0x3697A + 2 * code) & 0x790:
            self.p('magnet_tail_raise')
            self.wb(A5 + 1, 2); self.wb(A5 + 2, self.rb(A3 + 6)); self.wb(A5 + 3, self.rb(A3 + 8))
            self.ww(A1 + 40, 0)
        return 1 if self.rb(A5 + 1) else 0

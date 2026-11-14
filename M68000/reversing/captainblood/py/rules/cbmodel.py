"""Python model of Captain Blood's alien rule interpreter (French build, Zuul #40 image, runtime addresses).

Routines modelled, with the name each earned from its own body:
  $e43c  read_header     D0 = type (header & $e0), D5 = payload length (header & $1f), Z = header is $ff
  $e432  skip_record     A5 += 2 + length, then read_header
  $e44e  next_bit        element bit index D4 counts down 7..0, A4 (stream B) moves 3 bytes per 8 elements
  $e7dc  coin            XBIOS Random >> 16 compared with a threshold (carry = random above $8000)
  $e6a2  match           does the player's token list ($e3f2) satisfy the plain rule at A5
  $e7ae  advance         skip the rule at A5 and advance the stream B bit position by its element count
  $e58a  condition       test the condition record(s) at A5 (state bits, or the clock) and skip them
  $e628  action          set / clear state bits named by the payload of a $40 record
  $e67c  run_actions     loop over consecutive $40 records
  $e22e  compose         copy the matched rule's tokens (those whose stream B mask 1 bit is clear) to $e412
  $e45a  reply_engine    the scan: random roll, actions, plain/condition records, retry loop

The model is handed only a RAM image (bytearray, 1 MB) and, for a sub-routine, its entry registers. It never sees
the emulator's output. The one thing it does not model is the screen job `$de74` that `$e56c` queues (the gate
patches that call out of the emulator: see gate.py).
"""
V = 0xe3d4            # variable block (A6 in the engine)
STATE = 0x61c10       # state bit array
TOK = 0xe3f2          # player's token list, 0 terminated
OUT = 0xe412          # composed reply tokens, 0 terminated
CLOCK = 0xcb32        # game clock word
SEED = 0x29b8         # TOS 1.00 Random seed


class Model:
    # constants a broken-model control can change (the gate runs the true values)
    COIN = 0x8000      # $e6ca: coin threshold
    ROLL = 0xf000      # $e45e: state-bit-7 roll threshold
    CLKDIV = 100       # $e5a8: clock divisor
    RETRY = 7          # $e572/$e56e: retry counter reload
    REQ = 0            # stream B mask byte holding the 'required' bit ($e75e)
    IGN = 2            # stream B mask byte holding the 'not looked for' bit ($e706)
    CMASK = 1          # stream B mask byte holding the compose-skip bit ($e24e)

    def __init__(self, ram):
        self.r = bytearray(ram)
        self.d0 = self.d4 = self.d5 = 0
        self.a4 = self.a5 = 0
        self.rand_calls = 0
        self.guard = 0
        self.cov = set()

    def t(self, name): self.cov.add(name)

    # ---- memory
    def b(self, a): return self.r[a]
    def sb(self, a, v): self.r[a] = v & 0xff
    def w(self, a): return self.r[a] << 8 | self.r[a + 1]
    def sw(self, a, v): self.r[a] = (v >> 8) & 0xff; self.r[a + 1] = v & 0xff
    def l(self, a): return self.w(a) << 16 | self.w(a + 2)
    def sl(self, a, v): self.sw(a, v >> 16); self.sw(a + 2, v)

    # ---- XBIOS Random (TOS 1.00): seed = seed * 3141592621 + 1; returns seed >> 8 (24 bits)
    def rand(self):
        self.rand_calls += 1
        s = (self.l(SEED) * 3141592621 + 1) & 0xffffffff
        self.sl(SEED, s)
        return s >> 8

    def coin(self, d0=0x8000):
        """$e7dc: carry set when the 16-bit random value exceeds D0."""
        r16 = self.rand() >> 8
        return r16 > d0

    # ---- record walking
    def read_header(self):                       # $e43c
        h = self.b(self.a5)
        self.d5 = h & 0x1f
        self.d0 = h & 0xe0
        return h == 0xff                         # Z

    def skip_record(self):                       # $e432
        self.a5 += (self.b(self.a5) & 0x1f) + 2
        return self.read_header()

    def next_bit(self):                          # $e44e
        self.d4 -= 1
        if self.d4 < 0:
            self.d4 = 7
            self.a4 += 3

    def advance(self):                           # $e7ae: skip a plain rule, advance stream B bit position
        n = self.b(self.a5) & 0x1f
        self.a5 += 2
        a0 = self.a5
        self.a5 += n
        while True:
            t = self.b(a0); a0 += 1
            if t <= 3:
                a0 += 2; n -= 2
            self.next_bit()
            n -= 1
            if n == 0:
                break
            if (n & 0xffff) == 0xffff or n < 0:
                raise RuntimeError('advance ran past the record')
        # D0 = 0 on exit
        self.d0 = (self.d0 & ~0xffff)

    # ---- $e6a2
    def match(self):
        F20 = V + 20
        flag = self.b(self.a5 + 1)
        self.sb(V + 22, flag)
        if flag & 0x80 and not flag & 1:         # already used and not repeatable
            self.t('match.used_not_repeatable')
            return self._m_fail()
        a0 = TOK
        a1 = self.a5 + 2
        if flag & 8:                             # coin flip rule
            if self.coin(self.COIN):
                self.t('match.coin_fail')
                return self._m_fail()
            self.t('match.coin_pass')
        if flag & 4:                             # exact sentence
            self.t('match.exact')
            d5 = self.d5
            while True:
                x = self.b(a0); y = self.b(a1); a0 += 1; a1 += 1
                if x != y:
                    self.d5 = d5
                    return self._m_fail()
                if x <= 3:
                    for _ in range(2):
                        p = self.b(a0); q = self.b(a1); a0 += 1; a1 += 1
                        if p != q:
                            self.d5 = d5
                            return self._m_fail()
                    d5 -= 2
                d5 -= 1
                if d5 == 0:
                    break
                if d5 < 0:
                    raise RuntimeError('exact matcher overran')
            self.d5 = d5
            if self.b(a0) != 0:
                return self._m_fail()
            self.t('match.exact_ok')
            self.sb(F20, self.b(F20) | 0x80)
            return self.advance()
        if flag & 2:                             # always
            self.t('match.always')
            self.sb(F20, self.b(F20) | 0x80)
            return self.advance()
        # masked, order-free: every element whose mask-0 bit is set must be in the player's sentence;
        # elements whose mask-2 bit is set are not looked for; at least one element must be found
        self.t('match.masked')
        a3 = self.a4
        d3 = self.d4
        d5 = self.d5
        while True:
            self.sb(F20, self.b(F20) & ~1)
            d1 = self.b(a1); a1 += 1
            d2 = None
            if d1 > 3:
                pass
            else:
                d2 = self.b(a1) << 8 | self.b(a1 + 1); a1 += 2
                d5 -= 2
            if not (self.b(a3 + self.IGN) >> d3) & 1:   # mask 2 clear: look for it
                p = TOK
                while True:
                    d0 = self.b(p); p += 1
                    if d0 == 0:
                        break
                    if d0 > 3:
                        if d1 == d0:
                            self.sb(F20, self.b(F20) | 0x81)
                    else:
                        p += 2
                        if d1 == d0 and d2 == (self.b(p - 2) << 8 | self.b(p - 1)):
                            self.sb(F20, self.b(F20) | 0x81)
                found = self.b(F20) & 1
                self.sb(F20, self.b(F20) & ~1)
                if not found:
                    if (self.b(a3 + self.REQ) >> d3) & 1:   # mask 0: required
                        self.t('match.masked_required_missing')
                        self.d5 = d5
                        return self._m_fail()
                    self.t('match.masked_optional_missing')
                else:
                    self.t('match.masked_found')
            else:
                self.t('match.masked_ignored')
            d3 -= 1
            if d3 < 0:
                d3 = 7
                a3 += 3
            d5 -= 1
            if d5 == 0:
                break
            if d5 < 0:
                raise RuntimeError('masked matcher overran')
        self.d5 = d5
        self.t('match.masked_done_found' if self.b(F20) & 0x80 else 'match.masked_done_nothing')
        return self.advance()

    def _m_fail(self):                           # $e7a8
        F20 = V + 20
        self.sb(F20, self.b(F20) & 0x7f)
        return self.advance()

    # ---- $e58a
    def _state_ok(self, w):
        neg = bool(w & 0x8000)
        k = (-w) & 0xffff if neg else w
        byte = self.b(STATE + (k >> 3))
        if neg:
            byte ^= 0xff
        return bool((byte >> (k & 7)) & 1)

    def condition(self):
        F20, F21 = V + 20, V + 21
        while True:
            typ = self.d0 & 0xff
            a0 = self.a5 + 2
            word = self.w(a0); a0 += 2
            d5 = self.d5
            if typ == 0x80:
                ok = self._state_ok(word)
            else:
                clk = (self.w(CLOCK) // self.CLKDIV) & 0xffff
                ok = (word <= clk) if typ == 0xa0 else (word > clk)
            holds = False
            while True:
                if not ok:
                    break
                d5 -= 2
                if d5 == 0:
                    holds = True
                    break
                word = self.w(a0); a0 += 2
                ok = self._state_ok(word)
            self.d5 = d5
            if not holds:                        # $e5f2: condition false, skip the whole chain of conditions
                self.t('cond.false.' + hex(typ))
                self.sb(F21, self.b(F21) | 0x80)
                while True:
                    self.sb(F20, self.b(F20) | self.b(self.a5 + 1))
                    if self.skip_record():
                        return
                    if not self.d0 & 0x80:
                        return
            self.t('cond.holds.' + hex(typ))
            self.sb(F20, self.b(F20) | self.b(self.a5 + 1))   # $e610: holds, look at the next record
            if self.skip_record():
                return
            if self.d0 & 0x80:
                self.t('cond.chain')
                continue
            return

    # ---- $e628 / $e67c
    def run_actions_from_e628(self):
        return self.run_actions(first=True)

    def run_actions(self, first=False):
        """returns Z (True only through the empty-payload action). first=True enters at $e628 (header already read)."""
        while True:
            if first:
                self.d0 = 0x40
                first = False
            else:
                self.read_header()
            if self.d0 != 0x40:
                return False
            f = self.b(self.a5 + 1)
            self.sb(self.a5 + 1, f | 0x80)
            if f & 0x80 and f & 1:               # used already and bit 0: skip it
                self.t('action.skip_used')
                self.a5 += 2 + self.d5
                continue
            self.t('action.apply_used' if f & 0x80 else 'action.apply')
            if self.d5 == 0:
                self.t('action.empty')
                self.sb(V + 21, self.b(V + 21) | 0x80)
                self.sb(V + 28, self.b(V + 28) | 0x80)
                self.d0 = 0
                return True
            a0 = self.a5 + 2
            d5 = self.d5
            while True:
                w = self.w(a0); a0 += 2
                neg = bool(w & 0x8000)
                k = (-w) & 0xffff if neg else w
                idx = STATE + (k >> 3)
                if neg:
                    self.t('action.clear')
                    self.sb(idx, self.b(idx) & ~(1 << (k & 7)))
                else:
                    self.t('action.set')
                    self.sb(idx, self.b(idx) | (1 << (k & 7)))
                d5 -= 2
                if d5 == 0:
                    break
                if d5 < 0:
                    raise RuntimeError('action overran')
            self.d5 = d5
            self.a5 = a0

    # ---- $e22e
    def compose(self):
        a1 = self.l(V + 8)
        self.sb(a1 + 1, self.b(a1 + 1) | 0x80)
        a1 += 2
        a4 = self.l(V + 12)
        d1 = self.w(V + 16)
        d4 = self.w(V + 18)
        a0 = OUT
        while True:
            d0 = self.b(a1); a1 += 1
            masked = (self.b(a4 + self.CMASK) >> d4) & 1
            if masked:
                self.t('compose.masked')
                if d0 <= 3:
                    a1 += 2; d1 -= 2
            else:
                self.sb(a0, d0); a0 += 1
                if d0 <= 3:
                    self.sb(a0, self.b(a1)); self.sb(a0 + 1, self.b(a1 + 1)); a0 += 2; a1 += 2
                    d1 -= 2
            d4 -= 1
            if d4 < 0:
                d4 = 7; a4 += 3
            d1 -= 1
            if d1 == 0:
                break
            if d1 < 0:
                raise RuntimeError('compose overran')
        self.sb(a0, 0)

    # ---- $e45a
    def reply_engine(self):
        F20, F21 = V + 20, V + 21
        while True:                                  # $e45a, re-entered by "beq $e45a"
            d0 = self.rand() & 0xffff
            if d0 >= self.ROLL:
                self.t('engine.roll_sets_bit')
                self.sb(STATE, self.b(STATE) | 0x80)
                self.sw(0x7dd36, self.w(0x7dd36) | 0x100)
            self.sw(V + 20, 0)
            self.sw(V + 24, 0)
            self.a5 = self.l(V)
            self.a4 = self.l(V + 4)
            self.d4 = 7
            self.sw(V + 18, 7)
            self.run_actions()                       # $e490
            st = 'e494'
            rescan = False
            while True:
                if st == 'e494':
                    self.sw(V + 20, 0)
                    if self.read_header():
                        st = 'e554'; continue
                    if self.d0 & 0x80:
                        st = 'e4fa'; continue
                    if self.d0 == 0x40:
                        self.t('engine.skip_top_action')
                        self.a5 += 2 + self.d5
                        continue
                    self.sl(V + 8, self.a5); self.sl(V + 12, self.a4)
                    self.sw(V + 16, self.d5); self.sw(V + 18, self.d4)
                    self.match()
                    if not self.b(F20) & 0x80:
                        continue
                    self.run_actions()               # $e4d0
                    self.sl(0xe3c2, self.d4); self.sl(0xe3c6, self.d5)       # movem.l D4,D5,A4,A5
                    self.sl(0xe3ca, self.a4); self.sl(0xe3ce, self.a5)
                    self.compose()
                    if self.b(OUT) == 0:
                        self.t('engine.empty_reply')
                        continue
                    self.t('engine.reply')
                    self.sw(V + 24, self.w(V + 24) + 1)
                    self.sb(0xe3f0, self.b(0xe3f0) | 1)
                    return
                if st == 'e4fa':
                    self.sw(V + 20, 0)
                    self.condition()
                    if self.b(F21) & 0x80:
                        self.t('engine.cond_false')
                        st = 'e516'; continue
                    self.t('engine.cond_holds')
                    z = self.run_actions()
                    if z: self.t('engine.empty_action_ends')
                    st = 'e56c' if z else 'e494'
                    continue
                if st == 'e516':
                    if self.b(F20) & 0x80:
                        self.t('engine.cond_flag_stops')
                        st = 'e554'; continue
                    st = 'e51e'
                if st == 'e51e':
                    nxt = None
                    while True:
                        if self.read_header():
                            nxt = 'e554'; break
                        if self.d0 == 0:
                            self.advance(); continue
                        if not self.d0 & 0x80:
                            self.skip_record(); continue
                        self.t('engine.skip_over_cond')
                        if not self.b(F20) & 0x40:
                            nxt = 'e4fa'; break
                        if self.b(self.a5 + 1) & 0x20:
                            nxt = 'e4fa'; break
                        self.skip_record()
                    st = nxt
                    continue
                if st == 'e554':
                    c = (self.w(V + 26) - 1) & 0xffff
                    self.sw(V + 26, c)
                    if c & 0x8000:
                        st = 'e566'
                    elif self.w(V + 24) == 0:
                        self.t('engine.rescan')
                        rescan = True
                        break
                    else:
                        st = 'e566'
                    continue
                if st == 'e566':
                    self.sb(V + 28, self.b(V + 28) & ~1)
                    st = 'e56c'
                if st == 'e56c':
                    self.t('engine.end_clear')
                    self.sb(OUT, 0)
                    self.sw(V + 26, self.RETRY)
                    self.sl(0xdc34, 0); self.sl(0xdc38, 0)
                    return                           # (bsr $de74 not modelled)
            if rescan:
                self.guard += 1
                if self.guard > 50:
                    raise RuntimeError('rescan loop')
                continue

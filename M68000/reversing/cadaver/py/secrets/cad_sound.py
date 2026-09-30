"""Cadaver's 3-voice YM2149 sound engine, transcribed from the 68000 (no emulator needed to run it).

Source routines (all addresses are runtime absolute):
  $0158f8 PlaySound(D0=sound id)        5-byte request table at $01616c (62 entries)
  $015aec / $015ae0 StopSound(D0=id)    remove a queued (bit 7) sound, re-pick the best remaining
  $015b3e RepickQueued, $015aaa StartSet(D0=set id; 3 voice actions from the 3-byte table $0167aa)
  $015a7e StartEntry (A1 -> kind byte; installs actions on voices 0..n-1)
  $015bf4 InstallAction(D0=action id, D1=voice)   script pointer table $0163aa (256 longs)
  $015c70 per-VBL tick (3 voices x script interpreter + software envelopes + noise ring), then
  $015e5e flush of shadow registers R0..R10 to the PSG ($ff8800/$ff8802), once per VBL.
State lives in RAM: voice blocks $0162d0/$016306/$01633c (54 bytes each), shared block $016380
(A6), noise ring $016372, pending list $0162a2, busy mask $0162cc, round-robin $0162cd, current
priority $0162ce, flags 2496(A5)/2488(A5) with A5 = $018152.

Usage as a library:  s = Sound(ram_bytearray); s.play(2); frames = [s.tick() for _ in range(300)]
  -> each frame is the 11 bytes written to PSG registers 0..10 that VBL.
"""
import struct
A5 = 0x18152
A6 = 0x16380
BLK = (0x162d0, 0x16306, 0x1633c)
NOTE_TAB = 0x160ac
PTR_TAB = 0x163aa
REQ_TAB = 0x1616c
SET_TAB = 0x167aa
PRESET_TAB = 0x16fe5       # opcode $87: 12-byte records
NOISE_PRESET_TAB = 0x1729d  # opcode $89: 6-byte records
MIXMASK = (0x09, 0x12, 0x24)  # $016058: per-voice mixer bits (tone | noise)

class Sound:
    def __init__(self, ram):
        self.m = bytearray(ram)
    # memory helpers
    def rb(self, a): return self.m[a]
    def rw(self, a): return (self.m[a] << 8) | self.m[a + 1]
    def rl(self, a): return struct.unpack_from('>I', self.m, a)[0]
    def wb(self, a, v): self.m[a] = v & 0xff
    def ww(self, a, v): self.m[a] = (v >> 8) & 0xff; self.m[a + 1] = v & 0xff
    def wl(self, a, v): struct.pack_into('>I', self.m, a, v & 0xffffffff)
    # ---- $015bf4 InstallAction
    def install(self, action, voice):
        self.wb(0x162cc, self.rb(0x162cc) & ~(1 << voice))
        d4 = voice + 4
        self.wb(0x162cc, self.rb(0x162cc) & ~(1 << d4))
        a4 = BLK[voice]
        a2 = self.rl(PTR_TAB + 4 * action)
        self.wl(a4, a2); self.wl(a4 + 4, a2)
        if a2 != 0:
            self.wb(0x162cc, self.rb(0x162cc) | (1 << voice))
            nxt = self.rl(PTR_TAB + 4 * action + 4)
            if self.rb(nxt - 1) == 0x82:
                self.wb(0x162cc, self.rb(0x162cc) | (1 << d4))
        for i in range(8, 54): self.wb(a4 + i, 0)
        if self.rb(0x162cc) == 0: self.wb(0x162ce, 0)
    # ---- $015a7e StartEntry  (A1 = address of the kind byte)
    def start_entry(self, a1):
        n = self.rb(a1); a1 += 1
        for v in range(n):
            self.install(self.rb(a1), v); a1 += 1
    # ---- $015aaa StartSet
    def start_set(self, d0):
        a0 = SET_TAB + 3 * d0
        for v in range(3): self.install(self.rb(a0 + v), v)
    # ---- $0158f8 PlaySound
    def play(self, sid):
        self.wb(0x158f6, sid)
        e = REQ_TAB + 5 * sid
        prio = self.rb(e); kind = self.rb(e + 1)
        if prio < 0x80 and kind in (1, 2):
            busy = self.rb(0x162cc)
            d0 = (busy | (busy >> 4)) & 0xff
            rr = self.rb(0x162cd)
            if kind == 1:
                if busy == 0:
                    v = (rr + 1) % 3
                    self.wb(0x162cd, v); self.install(self.rb(e + 2), v); return
                v = rr; found = None
                for _ in range(3):
                    v = (v + 1) % 3
                    if not (d0 >> v) & 1: found = v; break
                if found is not None:
                    self.wb(0x162cd, found); self.install(self.rb(e + 2), found); return
                # all busy: fall into the priority path below
            else:
                first = None; found2 = None
                if busy == 0:
                    v = rr
                    for k in range(2):
                        v = (v + 1) % 3
                        self.wb(0x162cd, v); self.install(self.rb(e + 2 + k), v)
                    return
                v = rr
                for _ in range(3):
                    v = (v + 1) % 3
                    was = (d0 >> v) & 1; d0 |= 1 << v
                    if not was:
                        if first is None: first = v
                        else: found2 = v; break
                if found2 is not None:
                    self.wb(0x162cd, first); self.install(self.rb(e + 2), first)
                    self.wb(0x162cd, found2); self.install(self.rb(e + 3), found2)
                    return
        # $015a02
        d1 = prio & 0x7f; a1 = e + 1
        if prio & 0x80:
            cnt = self.rw(0x162a2); self.ww(0x162a2, cnt + 1)
            a0 = 0x162a4
            while True:
                w = self.rw(a0); a0 += 2
                if w == 0: break
            self.wb(a0 - 2, sid); self.wb(a0 - 1, d1)
            if d1 > self.rb(0x162ce):          # cmp.b ; ble
                self.wb(0x162ce, d1)
                self.wb(A5 + 2496, self.rb(A5 + 2496) & ~4)
                self.start_entry(a1)
            return
        if d1 == 0 or (d1 != 1 and d1 > self.rb(0x162ce)):
            self.wb(0x162ce, d1)
            self.wb(A5 + 2496, self.rb(A5 + 2496) | 4)
            self.start_entry(a1)
    # ---- $015aec StopSound  (queued sounds only)
    def stop(self, sid, flag2488=False):
        if flag2488: self.wb(A5 + 2488, 1)
        cnt = self.rw(0x162a2); a0 = 0x162a4
        if cnt:
            cnt -= 1
            while True:
                w = self.rw(a0); a0 += 2
                if w != 0:
                    if self.rb(a0 - 2) == sid:
                        self.ww(a0 - 2, 0); self.ww(0x162a2, self.rw(0x162a2) - 1); break
                    if cnt == 0: break
                    cnt -= 1
        if not self.rb(A5 + 2496) & 4: self.repick()
        self.wb(A5 + 2488, 0)
    # ---- $015b3e RepickQueued
    def repick(self):
        d2 = 0; d0 = 0; a0 = 0x162a4
        cnt = self.rw(0x162a2)
        if cnt == 0:
            self.wb(0x162ce, 0); self.wb(A5 + 2496, self.rb(A5 + 2496) & ~4)
            if self.rb(A5 + 2488): self.start_set(21)
            return
        d1 = (cnt - 1) & 0xff
        while True:
            while self.rw(a0) == 0: a0 += 2
            if d2 < self.rb(a0 + 1) or False:   # cmp.b 1(A0),D2 ; bge skip  (skip if D2 >= prio)
                d2 = self.rb(a0 + 1); d0 = self.rb(a0)
            a0 += 2
            if d1 == 0: break
            d1 -= 1
        self.wb(0x162ce, d2); self.wb(A5 + 2496, self.rb(A5 + 2496) & ~4)
        self.start_set(d0)
    # ---- $015c70 per-VBL tick; returns the 11 PSG register values flushed this VBL
    def mix(self, voice, d0):
        mask = MIXMASK[voice]
        d0 = ~(d0 & mask) & 0xff
        r7 = self.rb(A6 + 25) | mask
        self.wb(A6 + 25, r7 & d0)
    def reload_amp(self, a4):   # $016076
        self.wb(a4 + 26, self.rb(a4 + 42)); self.wb(a4 + 27, self.rb(a4 + 43))
        self.wb(a4 + 28, self.rb(a4 + 34)); self.wb(a4 + 29, self.rb(a4 + 35))
    def reload_pitch(self, a4):  # $01605c
        self.wb(a4 + 30, self.rb(a4 + 44)); self.wb(a4 + 31, self.rb(a4 + 45))
        self.wb(a4 + 32, self.rb(a4 + 36)); self.wb(a4 + 33, self.rb(a4 + 37))
    def reload_noise(self):      # $016090
        b = 0x16372
        self.wb(b, self.rb(b + 8)); self.wb(b + 1, self.rb(b + 9))
        self.wb(b + 2, self.rb(b + 4)); self.wb(b + 3, self.rb(b + 5))
    def tick(self):
        rb, wb, rw, ww, rl, wl = self.rb, self.wb, self.rw, self.ww, self.rl, self.wl
        self.ww(A6 + 12, 0)
        vol_ptr = 0x1639a; tone = A6 + 18
        for v in range(3):
            a4 = BLK[v]
            go_output = False
            if rw(a4 + 8) == 0:
                self.mix(v, 0)
                a2 = rl(a4 + 4)
                if a2 == 0:
                    go_output = True
                else:
                    a2 = self._run_script(a4, v, a2)   # returns None when it fell to 15d2c path with state committed
            if not go_output:
                # $015d2c
                ww(a4 + 8, (rw(a4 + 8) - 1) & 0xffff)
                # amplitude modulator
                d2 = 0
                for k in range(2):
                    a1 = a4 + k
                    if rb(a1 + 26) != 0: wb(a1 + 26, rb(a1 + 26) - 1); d2 += 1; break
                    if rb(a1 + 28) != 0:
                        wb(a1 + 28, rb(a1 + 28) - 1); wb(a4 + 50, rb(a4 + 50) + rb(a1 + 38))
                        wb(a1 + 26, rb(a1 + 42)); d2 += 1; break
                if d2 == 0:
                    wb(a4 + 50, 0)
                    if rb(a4 + 51) & 1: self.reload_amp(a4)
                # pitch modulator
                d2 = 0
                for k in range(2):
                    a1 = a4 + k
                    if rb(a1 + 30) != 0: wb(a1 + 30, rb(a1 + 30) - 1); d2 += 1; break
                    if rb(a1 + 32) != 0:
                        wb(a1 + 32, rb(a1 + 32) - 1)
                        d0 = rb(a1 + 40); d0 = d0 - 256 if d0 & 0x80 else d0
                        ww(a4 + 14, (rw(a4 + 14) + d0) & 0xffff)
                        wb(a1 + 30, rb(a1 + 44)); d2 += 1; break
                if d2 == 0 and (rb(a4 + 51) & 2): self.reload_pitch(a4)
            # output stage $015dc2
            wb(vol_ptr, (rb(a4 + 25) + rb(a4 + 50)) & 0xf)
            d0 = (rw(a4 + 12) + rw(a4 + 14)) & 0xfff
            d0 *= 2
            if d0 >= 0x1000: d0 >>= 1
            wb(tone, d0 & 0xff); wb(tone + 1, (d0 >> 8) & 0xff)
            tone += 2; vol_ptr += 1
            ww(A6 + 12, v + 1)
        # noise ring
        b = 0x16372; d2 = 0
        for k in range(2):
            a1 = b + k
            if rb(a1) != 0: wb(a1, rb(a1) - 1); d2 += 1; break
            if rb(a1 + 2) != 0:
                wb(a1 + 2, rb(a1 + 2) - 1); wb(b + 12, rb(b + 12) + rb(a1 + 6))
                wb(a1, rb(a1 + 8)); d2 += 1; break
        if d2 == 0 and (rb(b + 10) & 4): self.reload_noise()
        wb(A6 + 18 + 6, (rb(b + 11) + rb(b + 12)) & 0x1f)
        # flush (R7 gets bit 6 forced in the shadow itself)
        out = []
        for r in range(11):
            if r == 7: wb(A6 + 18 + 7, rb(A6 + 18 + 7) | 0x40)
            out.append(rb(A6 + 18 + r))
        return out
    def housekeeping(self):
        """Main-loop tail at $007414-$00741e: if 2496(A5) bit 2 (a non-queued priority sound is playing) is set and
        every voice is idle ($0162cc == 0) call RepickQueued ($015b3e).  Runs once per main-loop pass (~1 per VBL)."""
        if (self.rb(A5 + 2496) & 4) and self.rb(0x162cc) == 0: self.repick()
    def _run_script(self, a4, v, a2):
        rb, wb, rw, ww, rl, wl = self.rb, self.wb, self.rw, self.ww, self.rl, self.wl
        while True:
            op = rb(a2); a2 += 1
            if op < 0x80:
                # literal note
                d0 = (op + rb(a4 + 52)) & 0xff
                ww(a4 + 12, rw(NOTE_TAB + 2 * d0))
                return self._note_tail(a4, v, a2)
            k = op - 0x80
            if k == 0: wb(a4 + 25, rb(a2)); a2 += 1
            elif k == 1:
                d0 = rb(a2); a2 += 1; wb(a4 + 24, (d0 << v) & 0xff)
            elif k == 2: a2 = rl(a4); wl(a4 + 4, a2)
            elif k == 3:
                d0 = rb(a2); a2 += 1; ww(a4 + 10, (d0 * rw(A6 + 14)) & 0xffff)
            elif k == 4:
                return self._yield(a4, a2)
            elif k == 5:
                d0 = (rb(a2) * 4) & 0xffff; a2 += 1
                if d0 == 0: raise ZeroDivisionError('$85 tempo 0')
                ww(A6 + 14, 0xbb8 // d0)
            elif k == 6:
                n = rb(a2); a2 += 1; d1 = (n - 1) & 0xffff; d2 = 0
                for _ in range(d1 + 1):
                    d2 = (d2 + rb(a2) * rw(A6 + 14)) & 0xffff; a2 += 1
                ww(a4 + 10, d2)
            elif k == 7:
                wb(a4 + 51, rb(a4 + 51) & 0xfc)
                d0 = rb(a2); a2 += 1
                src = PRESET_TAB + 12 * d0
                for i in range(12): wb(a4 + 34 + i, rb(src + i))
                for o in (26, 27, 30, 31, 32, 50): wb(a4 + o, 0)
                ww(a4 + 14, 0)
            elif k == 8:
                d0 = rb(a2) & 0x1f; wb(0x1637d, d0); self.reload_noise()
                neg = rb(a2) & 0x80; a2 += 1
                if neg: continue
                return self._note_common(a4, v, a2)
            elif k == 9:
                wb(0x1637c, rb(0x1637c) & ~4)
                d0 = rb(a2); a2 += 1
                src = NOISE_PRESET_TAB + 6 * d0
                ww(0x16372, 0)
                for i in range(6): wb(0x16376 + i, rb(src + i))
                wb(0x1637e, 0)
            elif k == 10:
                d0 = rb(a2); a2 += 1; wb(a4 + 51, rb(a4 + 51) | d0); wb(0x1637c, rb(0x1637c) | d0)
            elif k == 11:
                # $015f18: install action 0 on this voice, reload cursor, countdown = 1, then literal tail
                self.install(0, v)
                a2 = rl(a4 + 4); ww(a4 + 8, 1)
                return self._note_common(a4, v, a2)
            elif k == 12:
                d0 = rb(a2); a2 += 1; wl(a4 + 16, a2); a2 = rl(PTR_TAB + 4 * d0)
            elif k == 13: a2 = rl(a4 + 16)
            elif k == 14:
                d0 = rb(a2); a2 += 1
                wb(a4 + 52, 0 if d0 == 0 else rb(a4 + 52) + d0)
            elif k == 15:
                d0 = rb(a2); a2 += 1
                if d0 != 0: wb(a4 + 53, d0); wl(a4 + 20, a2)
            elif k == 16:
                if rl(a4 + 20) != 0:
                    a2 = rl(a4 + 20); wb(a4 + 53, rb(a4 + 53) - 1)
                    if rb(a4 + 53) == 0: wl(a4 + 20, 0)
            else:
                raise ValueError('opcode $%02x' % op)
    def _note_tail(self, a4, v, a2):
        return self._note_common(a4, v, a2)
    def _note_common(self, a4, v, a2):
        # $015d0a: mixer bits from 24(A4), reload envelopes, clear bend, then yield
        self.mix(v, self.rb(a4 + 24))
        self.reload_amp(a4); self.wb(a4 + 50, 0); self.reload_pitch(a4); self.ww(a4 + 14, 0)
        return self._yield(a4, a2)
    def _yield(self, a4, a2):
        self.wl(a4 + 4, a2); self.ww(a4 + 8, self.rw(a4 + 10))
        return None

def disasm_script(s, ptr, limit=400):
    """Static listing of one action script until $82/$8b/null or limit; returns list of (addr, text)."""
    out = []; a = ptr
    names = {0x80: 'VOL', 0x81: 'MIX', 0x82: 'RESTART', 0x83: 'DUR', 0x84: 'YIELD', 0x85: 'TEMPO', 0x86: 'DURSUM', 0x87: 'ENV', 0x88: 'NOISE', 0x89: 'NENV', 0x8a: 'LOOPFLAGS', 0x8b: 'IDLE', 0x8c: 'STAGE', 0x8d: 'CALL', 0x8e: 'TRANSPOSE', 0x8f: 'LOOP', 0x90: 'ENDLOOP'}
    nargs = {0x80: 1, 0x81: 1, 0x82: 0, 0x83: 1, 0x84: 0, 0x85: 1, 0x87: 1, 0x88: 1, 0x89: 1, 0x8a: 1, 0x8b: 0, 0x8c: 1, 0x8d: 0, 0x8e: 1, 0x8f: 1, 0x90: 0}
    for _ in range(limit):
        op = s.rb(a); st = a; a += 1
        if op < 0x80: out.append((st, 'NOTE %02x' % op)); continue
        if op == 0x86:
            n = s.rb(a); args = [s.rb(a + 1 + i) for i in range(n)]; a += 1 + n
            out.append((st, 'DURSUM n=%d %s' % (n, ' '.join('%02x' % x for x in args)))); continue
        na = nargs.get(op)
        if na is None: out.append((st, '??%02x' % op)); break
        args = [s.rb(a + i) for i in range(na)]; a += na
        out.append((st, '%s %s' % (names[op], ' '.join('%02x' % x for x in args))))
        if op in (0x82, 0x8b): break
    return out

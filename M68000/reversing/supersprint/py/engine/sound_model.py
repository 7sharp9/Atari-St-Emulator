"""Python transcription of Super Sprint's 3-voice YM2149 sound driver (Timer-D ISR $13254, sequencer $134a2, envelope $1330e,
pitch modulators $13364/$133ce/$13438) plus the data parsers for the instrument table and the script block.

Data (SUPER.DAT tail, file offsets from 198966): +0 336 B (-134(A4), overwritten at load by A4 data), +336 1248 B (-138(A4), same),
+1584 2100 B instruments (35 x 60 B) -> copied to -70(A4); +3684 10000 B scripts -> copied to -54(A4).
Instrument (30 big-endian words): w0 pitch step, w1 base period, w2 step counter reload, w3 pitch-update interval (ISR ticks),
w4 initial level, w5,w6,w7 envelope segment lengths (sequencer steps), w8 start segment (0), w9 loop flag, w10,w11,w12 per-step level
deltas of the 3 segments, w13 pitch mode (0 square warble, 1 triangle glide), w14 mixer noise-disable (8 = tone only, 0 = tone+noise),
w15 unused here (1/31), w16 priority level.
Script: words; op 0..2 = note-on (arg instrument no.; logical channel 0 uses op as the PSG channel, channels 1/2 always play on their
own PSG channel); op 3..5 = set period (arg); op 6 = wait (arg sequencer steps); op >= 7 = end.
"""
import struct

TICK_DIV = 9            # the sequencer/envelope run every 9th ISR tick
ISR_HZ = 2457600 / 50 / 205


class Driver:
    def __init__(self, instruments, scripts, master=16):
        self.I = [list(struct.unpack_from('>30h', instruments, i * 60)) for i in range(35)]
        self.S = scripts
        self.master = master
        self.div = 8
        self.mirror7 = 0xF8
        self.status = [-1, -1, -1]; self.ptr = [0, 0, 0]; self.delay = [0, 0, 0]
        self.level = [0, 0, 0]
        self.cur = [self.I[0]] * 3
        self.state = [list(self.I[0][:15]) + [0] * 0 for _ in range(3)]
        for k in range(3):
            self.state[k] = list(self.I[0][:15])
        self.w = []                 # (reg, value) writes of the current tick

    def _psg(self, reg, val):
        self.w.append((reg, val & 0xFF))

    def trigger(self, ch, script_off):
        self.status[ch] = 0; self.ptr[ch] = script_off; self.delay[ch] = 0

    def word(self, off):
        return struct.unpack_from('>h', self.S, off)[0]

    # ---- sequencer ($134a2) ----
    def seq_step(self):
        for k in range(3):
            if self.status[k] != 0:
                continue
            if self.delay[k] != 0:
                self.delay[k] -= 1
                continue
            p = self.ptr[k]
            while True:
                op = self.word(p); p += 2
                if op < 3:
                    hw = op if k == 0 else k
                    inst = self.word(p); p += 2
                    I = self.I[inst]
                    self.level[hw] = I[16]
                    self.cur[hw] = I
                    S = self.state[hw]
                    S[0] = I[0]; S[1] = I[1]; S[2] = I[2]; S[3] = I[3]; S[4] = I[4]; S[5] = I[5]; S[6] = I[6]; S[7] = I[7]; S[8] = I[8]
                    S[10] = S[3]
                    m = (self.mirror7 & ~(8 << hw)) & 0xFFFF
                    m |= (I[14] << hw) & 0xFFFF
                    self._psg(7, m)
                    self.mirror7 = m
                elif op < 6:
                    hw = op - 3 if k == 0 else k
                    S = self.state[hw]; I = self.cur[hw]
                    S[1] = self.word(p); p += 2
                    S[0] = I[0]; S[3] = I[3]; S[4] = I[4]; S[5] = I[5]; S[6] = I[6]; S[7] = I[7]; S[8] = I[8]; S[2] = I[2]
                    S[10] = S[3]
                elif op == 6:
                    self.delay[k] = self.word(p); p += 2
                    break
                else:
                    self.status[k] -= 1
                    break
            self.ptr[k] = p

    # ---- envelope ($1330e) ----
    def envelope(self, hw):
        S = self.state[hw]; I = self.cur[hw]
        seg = S[8]
        if seg >= 6:
            if I[9] == 0:
                return 0
            S[4] = I[4]; S[5] = I[5]; S[6] = I[6]; S[7] = I[7]; S[8] = I[8]
            seg = S[8]
        # $1331a: decrement the segment counter at word 5+seg/2
        idx = 5 + seg // 2
        S[idx] = (S[idx] - 1)
        if S[idx] < 0:
            seg += 2; S[8] = seg
        # delta word at byte offset 20+seg (seg==6 reads w13, the pitch-mode flag, as in the original)
        delta = I[10 + seg // 2]
        lvl = (S[4] + delta)
        lvl = ((lvl + 0x8000) & 0xFFFF) - 0x8000
        S[4] = lvl
        prod = (lvl * self.master) & 0xFFFFFFFF
        return ((prod & 0xFFFF) >> 8) & 0xFF

    def vol_update(self):
        for hw in range(3):
            self._psg(8 + hw, self.envelope(hw))
        # $13308 has no rts: after the channel-C volume write the code falls straight into the envelope routine ($1330e) again with
        # channel C's pointers, so PSG channel C's envelope advances TWICE per sequencer step (result discarded, state advanced).
        self.envelope(2)

    # ---- pitch ($13364/$133ce/$13438) ----
    def pitch(self, hw):
        S = self.state[hw]; I = self.cur[hw]
        S[3] = S[10]
        d = S[0]
        if I[13] != 0:
            d = (d + S[1]); d = ((d + 0x8000) & 0xFFFF) - 0x8000
            S[1] = d
            self._psg(2 * hw, d & 0xFF); self._psg(2 * hw + 1, (d & 0xFFFF) >> 8)
            S[2] -= 1
            if S[2] < 0:
                S[2] = 3
                S[0] = -S[0]
        else:
            d = (d + S[1]); d = ((d + 0x8000) & 0xFFFF) - 0x8000
            S[0] = -S[0]
            self._psg(2 * hw, d & 0xFF); self._psg(2 * hw + 1, (d & 0xFFFF) >> 8)

    # ---- one Timer-D ISR invocation ----
    def tick(self):
        self.w = []
        self.div -= 1
        if self.div < 0:
            self.div = 8
            self.seq_step()
            self.vol_update()
        for hw in range(3):
            self.state[hw][3] -= 1
            if self.state[hw][3] < 0:
                self.pitch(hw)
        return self.w

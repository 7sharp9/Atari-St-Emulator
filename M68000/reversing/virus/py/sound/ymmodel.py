"""Model of Virus's sound engine (Sound_Trigger $17932, Sound_Tick $179f6, Sound_ChannelStep $17a1c).
Channel record = 13 words: 0 ticks left, 1 family, 2 priority, 3 chain, 4 volume (8.8), 5 volume slide,
6 mode (bit0 tone, bit1 noise), 7 period (8.8), 8 period slide, 9 tone fine reg, 10 volume reg,
11 tone-disable mixer bit, 12 noise-disable mixer bit."""
import struct

def s16(x):
    x &= 0xffff
    return x - 0x10000 if x & 0x8000 else x

def load_records(path):
    b = open(path, 'rb').read()
    return [list(struct.unpack_from('>9h', b, 18 * i)) for i in range(len(b) // 18)]

CH_INIT = [(0, 8, 0, 3), (2, 9, 1, 4), (4, 10, 2, 5)]

class Sound:
    def __init__(self, recs, flaw=None):
        self.recs = recs
        self.flaw = flaw
        self.ch = [[0] * 9 + list(c) for c in CH_INIT]
        self.mix = 0          # byte at $17b92 after Sound_Init (the high byte of the word $003f)
        self.nmax = 0
        self.atten = 0
        self.w = None

    def state(self):
        return [list(c) for c in self.ch], self.mix, self.nmax

    def trigger(self, i, atten=None, attenuated=False, d1=0):
        """Sound_Trigger (attenuation cleared) or Sound_TriggerAttenuated (D1 = distance)."""
        if attenuated:
            self.atten = s16(-(s16(d1 - 0x2000))) >> 2
        else:
            self.atten = 0
        rec = self.recs[i]
        fam = (rec[1] & 0xff)
        fam = fam - 256 if fam & 0x80 else fam          # ext.w of the low byte
        ch = self.ch
        for c in ch:
            if fam == s16(c[1]):
                if rec[3] >= 0:
                    self._load(c, rec)
                elif (rec[3] >> 8) & 0x40:
                    pass
                else:
                    c[4] = s16(rec[4] + self.atten)
                return
        for c in ch:
            if c[0] == 0:
                self._load(c, rec); return
        pa, pb, pc = (c[2] for c in ch)
        if pa > pb:
            if pb > pc: tgt = 2
            else: tgt = 1
        else:
            tgt = 2 if pa > pc else 0
        if (ch[tgt][2] >= rec[2]) if self.flaw == 'prio_ge' else (ch[tgt][2] > rec[2]):
            return
        self._load(ch[tgt], rec)

    def _load(self, c, rec):
        c[0:9] = rec
        c[4] = s16(rec[4] + self.atten)

    def tick(self):
        self.w = []
        self.nmax = 0
        for c in self.ch:
            self.step(c)
        return self.w

    def wr(self, r, v):
        self.w.append((r, v & 0xff))

    def step(self, c):
        while True:
            d0 = c[0]
            if d0 == 0:
                return
            d1, d2, d3, d4, d5, a2, a3, a4, a5 = c[4:13]
            d0 = (d0 - 1) & 0xffff
            if d0 == 0:
                d6 = c[3]
                if d6 == 0:
                    break_kill = True
                else:
                    rec = self.recs[((d6 << 2) & 0xffff) >> 2]
                    c[0:4] = rec[0:4]
                    c[5:9] = rec[5:9]
                    continue
                self.kill(c); return
            d1 = s16(d1 + d2)
            if d1 < 0:
                self.kill(c); return
            if d1 >= 0x1000:
                d1 = 0xfff
            self.wr(a3, d1 >> 8)
            if d3 & 1:
                self.mix = (self.mix & ~(1 << a4)) | (1 << a5)
                self.wr(7, self.mix)
                d4 = s16(d4 + d5)
                self.wr(a2, (d4 & 0xffff) >> 8)
                if d3 & 2:
                    self.mix &= ~(1 << a5)
                    self.wr(7, self.mix)
                    if d1 >= self.nmax or self.flaw == 'nonmax':
                        self.nmax = d1
                        self.wr(6, ((d4 & 0xffff) >> 8) >> (2 if self.flaw == 'shift2' else 3))
            else:
                self.mix = (self.mix | (1 << a4)) & ~(1 << a5)
                self.wr(7, self.mix)
                if d1 >= self.nmax or self.flaw == 'nonmax':
                    self.nmax = d1
                    d4 = s16(d4 + d5)
                    self.wr(6, ((d4 & 0xffff) >> 8) >> (2 if self.flaw == 'shift2' else 3))
            c[0] = d0
            c[4:9] = [d1, d2, d3, d4, d5]
            return

    def kill(self, c):
        c[0] = 0; c[1] = 0
        self.wr(c[10], 0)

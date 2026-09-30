"""Sound engine 1 ($1c840 and the VBL step $1c9b2 -> $1d1d0): three effect voices driven by 13-byte effect records at $1d430.
Python re-implementation of $1c840 (type-1 path), $1d0f2 (voice setup), $1d298 (voice step), $1d34c (pitch sweep),
the four envelope handlers ($1d2d0/$1d2f4/$1d318/$1d328) and the YM register writer ($1d1d0).  State comes from live RAM so no history is modelled."""
import struct

VOICE = [0x1d0a4, 0x1d0be, 0x1d0d8]      # 26-byte voice structs
MIXER = 0x1d0a2
REC = 0x1d430                              # 13-byte effect records
ENTRY = 0x1cabe                            # 8-byte sound entries (word type, word record index, long unused)

def s8(v): return v - 256 if v & 0x80 else v

class Voice:
    def __init__(self, ram, base):
        b = ram[base:base + 26]
        self.mask_on = (b[0], b[1])          # 0(A6), 1(A6): AND-masks that enable tone / noise in the mixer
        self.mask_off = b[2]                 # 2(A6): bits that disable this voice in the mixer
        self.period = struct.unpack('>H', b[4:6])[0]
        self.level = b[6]
        self.dur = struct.unpack('>H', b[8:10])[0]
        self.delay = b[10]; self.cnt = b[11]
        self.off = struct.unpack('>H', b[12:14])[0]
        self.step = struct.unpack('>H', b[14:16])[0]
        self.state = None                    # envelope handler (attack/decay/sustain/release) or None (idle)
        self.rec = None
        self.flags = b[24]

class Engine:
    def __init__(self, ram):
        self.ram = ram
        self.mixer = ram[MIXER]
        self.v = [Voice(ram, a) for a in VOICE]
        self.rr = ram[0x1cc79] & 3           # round-robin counter, bits 4-6 = locked voices
        self.lock = ram[0x1cc79] >> 4
        self.regw = []                       # register writes emitted outside the per-VBL writer (hardware envelope setup)
        self.d1 = 0

    def record(self, i): return self.ram[REC + 13 * i:REC + 13 * i + 13]

    def start(self, snd, param=0):
        """$1c840 for a type-1 entry (all 53 entries of this disk are type 1).  Returns the voice used."""
        e = self.ram[ENTRY + 8 * snd:ENTRY + 8 * snd + 8]
        typ, idx, unused = struct.unpack('>HHI', e)
        w3 = e[6] << 8 | e[7]
        assert typ == 1
        if w3 == 0:
            d6 = self.rr
            d1 = 0 if d6 + 1 == 3 else d6 + 1
            self.rr = d1
            while (self.lock >> d6) & 1:     # locked voice: try the next ($1c8e2 loops with the advanced counter)
                d6 = self.rr; d1 = 0 if d6 + 1 == 3 else d6 + 1; self.rr = d1
        else:
            raise NotImplementedError('entry with word3 != 0 (entry 0)')
        self.setup(d6, self.record(idx))
        return d6

    def setup(self, n, rec):                 # $1d0f2
        v = self.v[n]; v.rec = rec
        v.period = rec[10] | rec[11] << 8
        v.dur = rec[12]
        v.delay = rec[5]
        c = rec[6] & 0x7f
        v.cnt = (c >> 1) + (c & 1)
        v.step = rec[8] << 8 | rec[7]
        v.off = 0
        d0 = self.mixer | v.mask_off
        v.flags = rec[9]
        if v.flags & 1: d0 &= v.mask_on[0]
        if v.flags & 2: d0 &= v.mask_on[1]
        self.mixer = d0
        if v.flags & 4:                       # hardware envelope: regs 13, 11, 12 and level $ff
            self.regw += [(13, rec[0]), (11, rec[4]), (12, 0)]
            v.level = 0xff
            v.state = 'hw'
        else:
            v.state = 'attack'
        v.active = True

    # ---- per VBL ($1d1d0) ----
    def vbl(self):
        for v in self.v: self.step_voice(v)
        out = list(self.regw); self.regw = []
        out.append((7, self.mixer))
        d1 = self.d1
        for n, v in enumerate(self.v):
            d0 = (v.period + v.off) & 0xffff
            if v.flags & 2: d1 = d0 & 0xff
            out += [(2 * n, d0 & 0xff), (2 * n + 1, d0 >> 8)]
        self.d1 = d1
        out.append((6, (d1 >> 3) & 0xff))
        for n, v in enumerate(self.v):
            out.append((8 + n, (v.level >> 3) & 0xff))
        return out

    def step_voice(self, v):                 # $1d298
        if (self.mixer & v.mask_off) == v.mask_off: return
        rec = v.rec
        if v.dur != 0 and v.dur != 0xffff: v.dur -= 1
        self.sweep(v, rec)
        if v.flags & 4:
            if v.dur == 0: self.off_voice(v)
            return
        st = v.state
        if st == 'attack':
            v.level = (v.level + s8(rec[0])) & 0xff
            if v.level & 0x80 or s8(rec[4]) <= s8(v.level):     # bmi, or cmp: ceiling - level <= 0 -> clamp
                v.level = rec[4]; v.state = 'decay'
        elif st == 'decay':
            v.level = (v.level + s8(rec[1])) & 0xff
            if v.level & 0x80 or not (s8(rec[2]) < s8(v.level)):
                v.level = rec[2]; v.state = 'sustain'
        elif st == 'sustain':
            if v.dur == 0: v.state = 'release'
        elif st == 'release':
            v.level = (v.level + s8(rec[3])) & 0xff
            if v.level & 0x80: self.off_voice(v)

    def off_voice(self, v):                  # $1d332
        v.level = 0; self.mixer |= v.mask_off; v.state = None; v.active = False

    def sweep(self, v, rec):                 # $1d34c
        d0 = v.delay
        if d0 != 0:
            if d0 == 0xff: return
            v.delay -= 1
            if v.delay != 0: return
        v.off = (v.off + v.step) & 0xffff
        v.cnt = (v.cnt - 1) & 0xff
        if v.cnt != 0: return
        d0 = rec[6]
        if d0 == 0: return
        if not d0 & 0x80:
            v.cnt = d0; v.step = (-v.step) & 0xffff
        else:
            v.delay = 0xff

"""Decode, list and render the sound scripts nothing in the game starts (offline: the Timer-D tracker model, no emulator).

usage: tune.py            -> out/<name>.regs.txt, .notes.txt, .wav for the unreferenced entries (Q = script 906 in full) and a summary
The model is the proved sound_model.Driver (engine/proof_sound.py 7200/7200); `Driver.vol_update` reproduces the missing-rts bug at $13308
(channel C envelope advanced twice per step). `FixedDriver` removes that second advance, to measure the bug's audible effect."""
import sys, os, struct, wave, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
import numpy as np
import proof_sound as PS            # builds INS/SCR from SUPER.DAT and the model's initial state from the race snapshot
from sound_model import Driver, ISR_HZ

SR = 44100
SCRIPT = PS.SCR
W = lambda p: struct.unpack_from('>h', SCRIPT, p)[0]


class FixedDriver(Driver):
    """as Driver but without the second channel-C envelope advance (what the author presumably meant)"""
    def vol_update(self):
        for hw in range(3):
            self._psg(8 + hw, self.envelope(hw))


class NoteDriver(Driver):
    """records (step, script pointer before, after, logical channel) at every sequencer run that executed ops"""
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.steps = 0; self.ev = []
    def seq_step(self):
        before = list(self.ptr); st = list(self.status)
        super().seq_step()
        for k in range(3):
            if st[k] == 0 and self.ptr[k] != before[k] or (st[k] == 0 and self.status[k] != 0):
                self.ev.append((self.steps, k, before[k], self.ptr[k]))
        self.steps += 1


def make(cls, entries, master=16, noise=5):
    d = PS.init_model(); d.__class__ = cls
    if cls is NoteDriver: d.steps = 0; d.ev = []
    d.master = master; d.mirror7 = 0xF8
    for ch, off in entries:
        d.status[ch] = 0; d.ptr[ch] = off; d.delay[ch] = 0
    return d


def run(cls, entries, max_s=75.0, quiet_s=2.0, ticks=None):
    """run until every logical channel has ended and no PSG volume register has changed for quiet_s seconds (a channel the entry does not own
    keeps whatever level the snapshot left in it, so 'all volumes 0' is not usable); returns (driver, [(tick, writes)], nticks = last volume change + 30)"""
    d = make(cls, entries)
    log = []; vol = [None] * 3; last = 0
    n = ticks or int(max_s * ISR_HZ)
    for t in range(n):
        w = d.tick()
        if w: log.append((t, w))
        for r, v in w:
            if 8 <= r <= 10 and vol[r - 8] != v: vol[r - 8] = v; last = t
        if not ticks and all(s != 0 for s in d.status) and t - last > quiet_s * ISR_HZ: return d, log, last + 30
    return d, log, n


NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def note_name(period):
    if period <= 0: return '-', 0.0
    f =125000.0 / period       # YM2149 on the ST: 2 MHz master / 16 / period
    m = 69 + 12 * math.log2(f / 440.0)
    r = round(m)
    return '%s%d %+dc' % (NOTES[r % 12], r // 12 - 1, round((m - r) * 100)), f


def list_notes(entry_offs, nticks_hint=None):
    """note listing of a script run: one line per op, with time (s), PSG channel, instrument, period, frequency, nearest note"""
    d = make(NoteDriver, entry_offs)
    lines = []; maxt = int(80 * ISR_HZ)
    for t in range(maxt):
        d.tick()
        if all(s != 0 for s in d.status): break
    first = d.div  # unused
    # step n runs on ISR tick t0 + 9n; the model's first sequencer run is at tick index (div0+1) with div0 from the snapshot
    div0 = PS.init_model().div
    t0 = div0         # tick index (0-based) of sequencer run 0: div counts down from div0 to -1 -> run on tick number div0 (0-based)
    cur = {}
    for step, k, a, b in d.ev:
        p = a; time_s = (t0 + 9 * step) / ISR_HZ
        while p < b:
            op = W(p); p += 2
            if op < 3:
                hw = op if k == 0 else k; inst = W(p); p += 2; I = d.I[inst]; cur[hw] = I
                nn, f = note_name(I[1])
                lines.append('%7.3f s  step %4d  L%d  NOTE-ON  psg %s  inst %2d  base period %5d (%7.1f Hz  %s)  init level %d  tone-only %s' %
                             (time_s, step, k, 'ABC'[hw], inst, I[1], f, nn, I[4], I[14] == 8))
            elif op < 6:
                hw = op - 3 if k == 0 else k; per = W(p); p += 2
                nn, f = note_name(per)
                lines.append('%7.3f s  step %4d  L%d  PERIOD   psg %s  period %5d (%7.1f Hz  %s)' % (time_s, step, k, 'ABC'[hw], per, f, nn))
            elif op == 6:
                a2 = W(p); p += 2
                lines.append('%7.3f s  step %4d  L%d  WAIT %d steps (%.3f s)' % (time_s, step, k, a2, (a2 + 1) * 9 / ISR_HZ))
            else:
                lines.append('%7.3f s  step %4d  L%d  END' % (time_s, step, k))
                p += 0
    return lines


# ---- vectorised YM2149 approximation of the register log -> PCM ----
def _lfsr_table():
    # 17-bit LFSR with taps 0 and 3 as in render_wav (period 131071)
    lf = 1; out = np.empty(131071, np.uint8)
    for i in range(131071):
        bit = (lf ^ (lf >> 3)) & 1
        lf = (lf >> 1) | (bit << 16)
        out[i] = lf & 1
    return out
_NOISE = None


def render(log, nticks, path, noise_p0=5):
    global _NOISE
    if _NOISE is None: _NOISE = _lfsr_table()
    spt = SR / ISR_HZ
    n = int(nticks * spt) + 1
    # per-tick register file -> per-sample arrays
    regs = np.zeros((nticks + 1, 16), np.int32); regs[:, 6] = noise_p0; regs[:, 7] = 0xF8
    cur = regs[0].copy(); li = 0
    for t in range(nticks + 1):
        while li < len(log) and log[li][0] <= t:
            for r, v in log[li][1]: cur[r & 15] = v
            li += 1
        regs[t] = cur
    idx = np.minimum((np.arange(n) / spt).astype(np.int64), nticks)
    R = regs[idx]
    lut = np.array([0] + [2 ** ((i - 15) / 2.0) * 0.5 for i in range(1, 16)])      # ~3 dB per step, as engine/sound_render.py
    npd = np.maximum(1, R[:, 6] & 31)
    nph = np.cumsum((125000.0 / npd) / SR)
    nval = _NOISE[(nph.astype(np.int64)) % 131071]
    x = np.zeros(n)
    for ch in range(3):
        per = np.maximum(1, ((R[:, 2 * ch + 1] & 15) << 8) | R[:, 2 * ch])
        ph = np.cumsum((125000.0 / per) / SR) % 1.0
        tone = (ph < 0.5).astype(np.int32)
        te = ((R[:, 7] >> ch) & 1) == 0
        ne = ((R[:, 7] >> (3 + ch)) & 1) == 0
        o = np.where(te, tone, 1) & np.where(ne, nval, 1)
        a = R[:, 8 + ch]
        amp = np.where((a & 16) != 0, 0.35, lut[a & 15])
        x += (o - 0.5) * 2 * amp
    pcm = (np.clip(x / 3.0, -1, 1) * 30000).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return pcm


ENTRIES = {   # name: (trigger routine, [(logical channel, script offset)], noise period the trigger leaves in PSG reg 6)
    'Q_906_59s_tune':   ('$12d64', [(0, 906)], 5),
    'J_chord_194_208_222': ('$129bc', [(0, 194), (1, 208), (2, 222)], 5),
    'M_ch1_322':        ('$12ac2', [(1, 322)], 5),
}

if __name__ == '__main__':
    only = sys.argv[1:]
    for name, (trig, ents, nz) in ENTRIES.items():
        if only and name not in only: continue
        d, log, nt = run(Driver, ents)
        vols = [(t, v) for t, ws in log for r, v in ws if 8 <= r <= 10 and v]
        audible = vols[-1][0] / ISR_HZ if vols else 0
        with open(os.path.join(OUT, name + '.regs.txt'), 'w') as f:
            f.write('# %s %s entries %s; tick (1/%.3f s): reg=value\n' % (name, trig, ents, ISR_HZ))
            for t, ws in log: f.write('%d: %s\n' % (t, ' '.join('%d=%d' % w for w in ws)))
        with open(os.path.join(OUT, name + '.notes.txt'), 'w') as f:
            f.write('# %s (trigger %s) script entries %s, noise period %d; times are from the sequencer model (step = 9 ISR ticks = %.1f ms)\n' %
                    (name, trig, ents, nz, 9000 / ISR_HZ))
            f.write('\n'.join(list_notes(ents)) + '\n')
        render(log, nt, os.path.join(OUT, name + '.wav'), nz)
        big = sum(1 for t, ws in log for r, v in ws if 8 <= r <= 10 and v > 15)
        print('%-22s %s ticks run %d, audible to %.2f s, tick-with-write %d, writes %d, volume writes >15 (env mode): %d'
              % (name, trig, nt, audible, len(log), sum(len(w) for _, w in log), big))

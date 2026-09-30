"""Run sound_model.Driver for every effect/tune, write the register-write logs and a WAV render (approximate YM2149 synthesis), and
print the effect table (script offset, length, duration, ...).  Output: agents/engine/sound/."""
import sys, os, struct, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from sound_model import Driver, ISR_HZ
import proof_sound as PS

SND = os.path.join(OUT, 'sound'); os.makedirs(SND, exist_ok=True)
SR = 22050
EFFECTS = [  # (name, trigger routine, arg, [(logical ch, script off)])
    ('A_2voice_at0', '$12522', 0, [(0, 0), (1, 0)]), ('B_2voice_at316', '$125e6', 0, [(0, 316), (1, 316)]),
    ('C_at28', '$126ae', 0, [(0, 28)]), ('D_at166', '$1271c', 0, [(0, 166)]), ('E_at88', '$1278a', 0, [(0, 88)]),
    ('F_at180', '$127f8', 0, [(0, 180)]), ('G_at302', '$12866', 0, [(0, 302)]), ('H_at14', '$128e0', 0, [(0, 14)]),
    ('I_at74', '$1294e', 0, [(0, 74)]), ('J_3voice_at194_208_222', '$129bc', 0, [(0, 194), (1, 208), (2, 222)]),
    ('K_at242', '$12a56', 0, [(0, 242)]), ('L_at272', '$12a8c', 0, [(0, 272)]), ('M_ch1_at322', '$12ac2', 0, [(1, 322)]),
    ('N_at336_title_rev', '$12b00', 0, [(0, 336)]), ('O_at236_silence', '$12b32', 0, [(0, 236)]),
    ('P0_at3398', '$12c10', 0, [(0, 3398)]), ('P1_at4488', '$12c10', 1, [(0, 4488)]), ('P2_at5302', '$12c10', 2, [(0, 5302)]),
    ('P3_at5916', '$12c10', 3, [(0, 5916)]), ('P4_at6794', '$12c10', 4, [(0, 6794)]), ('Q_at906', '$12d64', 0, [(0, 906)]),
    ('R_at7780', '$12da8', 0, [(0, 7780)]), ('S_at2580', '$12dec', 0, [(0, 2580)]), ('T_at316', '$12e30', 0, [(0, 316)]),
]


def simulate(offs, max_s=75):
    d = PS.init_model(); d.master = 16; d.mirror7 = 0xF8
    for ch, off in offs:
        d.status[ch] = 0; d.ptr[ch] = off; d.delay[ch] = 0
    log = []
    quiet = 0
    for t in range(int(max_s * ISR_HZ)):
        w = d.tick()
        if w: log.append((t, w))
        if all(s != 0 for s in d.status) and t % 9 == 8:
            # silent once every channel's volume register reads 0 on the last update
            vols = [v for ti, ws in log[-3:] for r, v in ws if r in (8, 9, 10)]
            quiet += 1
            if quiet > 12: break
    return d, log


def render_wav(log, path, ticks_total, noise_p0=0x1F):
    regs = [0] * 16; regs[6] = noise_p0; regs[7] = 0xF8
    n_samples = int((ticks_total + 10) / ISR_HZ * SR)
    out = np.zeros(n_samples, dtype=np.float32)
    lut = [0] + [2 ** ((i - 15) / 2.0) * 0.5 for i in range(1, 16)]        # ~3 dB per step
    ph = [0.0, 0.0, 0.0]; nph = 0.0; lfsr = 1; nval = 1
    li = 0
    spt = SR / ISR_HZ
    for s in range(n_samples):
        t = s / spt
        while li < len(log) and log[li][0] <= t:
            for r, v in log[li][1]:
                regs[r & 15] = v
            li += 1
        x = 0.0
        np_ = max(1, regs[6] & 31)
        nph += (125000.0 / np_) / SR
        while nph >= 1.0:
            nph -= 1.0
            bit = (lfsr ^ (lfsr >> 3)) & 1
            lfsr = (lfsr >> 1) | (bit << 16)
            nval = lfsr & 1
        for ch in range(3):
            per = ((regs[2 * ch + 1] & 15) << 8) | regs[2 * ch]
            per = max(per, 1)
            ph[ch] = (ph[ch] + (125000.0 / per) / SR) % 1.0
            tone = 1 if ph[ch] < 0.5 else 0
            te = not (regs[7] >> ch) & 1
            ne = not (regs[7] >> (3 + ch)) & 1
            o = (tone if te else 1) & (nval if ne else 1)
            a = regs[8 + ch]
            amp = lut[a & 15] if not (a & 16) else 0.35
            x += (o - 0.5) * 2 * amp
        out[s] = x / 3.0
    pcm = (np.clip(out, -1, 1) * 30000).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == '__main__':
    do_wav = '--nowav' not in sys.argv
    rows = []
    for name, trig, arg, offs in EFFECTS:
        d, log = simulate(offs)
        last = log[-1][0] if log else 0
        # sound length = last tick at which any volume register was non-zero
        nz = [t for t, ws in log if any(r in (8, 9, 10) and v != 0 for r, v in ws)]
        dur = (nz[-1] if nz else 0) / ISR_HZ
        with open(os.path.join(SND, name + '.regs.txt'), 'w') as f:
            f.write('# tick (1/%.2f s) : reg=value ...\n' % ISR_HZ)
            for t, ws in log: f.write('%d: %s\n' % (t, ' '.join('%d=%d' % w for w in ws)))
        if do_wav:
            # tunes are cut to their first 20 s in the WAV (the .regs.txt log is complete)
            render_wav(log, os.path.join(SND, name + '.wav'), min((nz[-1] if nz else 0) + 240, int(20 * ISR_HZ)))
        rows.append((name, trig, arg, offs, dur, len(log), sum(len(w) for _, w in log)))
        print('%-26s %-7s arg %d  audible %.2f s  ticks-with-writes %d  reg writes %d' % (name, trig, arg, dur, len(log), rows[-1][-1]))

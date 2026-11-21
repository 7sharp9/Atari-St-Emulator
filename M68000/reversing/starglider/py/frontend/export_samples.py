"""Export the five digitised sounds as WAV. The $c684 Timer A handler reads one byte b of the sample (self-modifying
pointer at $c68c), indexes three 256-byte tables at $c6d6/$c7d6/$c8d6 with it and writes the three values to YM volume
registers 8/9/10 (a 3-channel volume DAC). The loader at $df0c adds $80 to every sample byte first (signed -> index).
Rate = 2457600 / prescale(TACR=4 -> 50) / TADR: 9830.4 Hz (title, TADR 5), 6144 Hz (effects, TADR 8).
Amplitude per byte = sum of three YM volume levels (approximate 2149 DAC levels); a check prints how monotone the
table is. usage: export_samples.py -> WORK/frontend/snd_*.wav"""
import os, sys, wave, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fe_repl, sgcommon
LV = [0, .0100, .0145, .0211, .0307, .0455, .0645, .1073, .1263, .2050, .2922, .3728, .4925, .6353, .8055, 1.0]
SND = [('title', 0x2A340, 0x2BC00, 5), ('fx_23940', 0x23940, 0x1B80, 8), ('fx_254c0', 0x254C0, 0x1D00, 8),
       ('fx_271c0', 0x271C0, 0x1680, 8), ('fx_28840', 0x28840, 0x1B00, 8)]
r = sgcommon.load_ram(sgcommon.SNAP_GAME1)   # game1 is past the title: sample at $2a340 already played once but bytes unchanged
t = [list(r[b:b + 256]) for b in (0xC6D6, 0xC7D6, 0xC8D6)]
amp = [sum(LV[t[c][i] & 15] for c in range(3)) for i in range(256)]
inc = sum(1 for i in range(255) if amp[i + 1] >= amp[i])
print('table monotone steps: %d/255; amp[0]=%.3f amp[255]=%.3f' % (inc, amp[0], amp[255]))
for name, a, n, tadr in SND:
    rate = 2457600 // 50 / tadr
    data = bytes(int(amp[(b + 0x80) & 0xFF] / max(amp) * 255) for b in r[a:a + n])
    # the loader flipped the sign bit already in RAM, so the stored byte IS the index; no second flip
    data = bytes(int(amp[b] / max(amp) * 255) for b in r[a:a + n])
    p = sgcommon.work('frontend', 'snd_%s.wav' % name)
    w = wave.open(p, 'wb'); w.setnchannels(1); w.setsampwidth(1); w.setframerate(int(rate)); w.writeframes(data); w.close()
    print(p, n, 'bytes', '%.1f Hz' % rate, '%.2f s' % (n / rate))

"""Numeric sanity check of the rendered WAVs (nobody can listen here).
For each wav/snd*.wav: frame count vs predicted ticks, sample rate vs Timer A rate, duration,
min/max, peak as a fraction of full scale, clipped samples, DC offset (mean), RMS, and, for ids 1..8,
an exact comparison with a render built from the LIVE PSG triples captured by verify_psg.py
(run/verify_id<N>.out): the WAV must equal centre(level(live A,B,C)).
Prints a table and `ALL OK` / the failures.  Run `python btsnd.py wav` and `python verify_psg.py` first.
"""
import os
import struct
import wave

from btsnd import OUT, centre, level_source, load_tables, stream, ym_level
from verify_psg import ticks_from_log

vt, rates = load_tables()
bad = []
print("level source:", level_source())
print("%-34s %6s %7s %7s %6s %7s %7s %6s %7s %s" % ("file", "frames", "rate", "dur_s", "min", "max", "clip", "dc", "rms", "live-eq"))
names = ["snd%d.wav" % i for i in range(9)] + ["snd0_as_played_t0_overwrite.wav"]
for n in names:
    p = os.path.join(OUT, "wav", n)
    w = wave.open(p)
    fr, hz, sw, ch = w.getnframes(), w.getframerate(), w.getsampwidth(), w.getnchannels()
    pcm = struct.unpack("<%dh" % fr, w.readframes(fr))
    sid = 0 if n.startswith("snd0") else int(n[3])
    ticks = len(stream(sid)[0])
    rate = rates[1 if sid == 0 else 0][2]
    mn, mx = min(pcm), max(pcm)
    clip = sum(1 for x in pcm if x <= -32768 or x >= 32767)
    dc = sum(pcm) / fr
    rms = (sum(x * x for x in pcm) / fr) ** 0.5
    live = "-"
    if 1 <= sid <= 8 and n == "snd%d.wav" % sid:
        err = open(os.path.join(OUT, "run", "verify_id%d.out" % sid)).read()
        trip = [(t[1], t[2], t[3]) for t in ticks_from_log(err)]
        exp = centre([ym_level(*t) for t in trip])
        live = "exact" if list(pcm) == exp else "DIFF"
        if live != "exact":
            bad.append((n, "live render differs"))
    ok = (sw == 2 and ch == 1 and fr == ticks and hz == int(round(rate)) and clip == 0 and abs(dc) < 1.0)
    if not ok:
        bad.append((n, "format/length/clip/dc"))
    print("%-34s %6d %7d %7.3f %6d %7d %7d %6.2f %7.1f %s" % (n, fr, hz, fr / hz, mn, mx, clip, dc, rms, live))
print("ALL OK" if not bad else "FAIL %s" % bad)

"""Demo renders of the instruments no script uses (17, 26, 27, 28) and a census of instrument usage. Each is played on PSG A at period 400
(the instruments have base period 0, so they only make sense with a period op) for 60 steps (2.25 s) with a synthetic one-note script.
INFERRED: nothing in the game plays these; the audio is what the proved driver would produce."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
from tune import *
import numpy as np, wave

def synth(inst, per, wait=60):
    words = [0, inst, 3, per, 6, wait, 255, 0]
    return struct.pack('>%dh' % len(words), *words)

chunks = []
for inst in (17, 26, 27, 28):
    d = make(Driver, [(0, 0)]); d.S = synth(inst, 400)
    log = []
    n = int(2.6 * ISR_HZ)
    for t in range(n):
        w = d.tick()
        if w: log.append((t, w))
    p = os.path.join(OUT, '_i%d.wav' % inst)
    render(log, n, p, 5)
    with wave.open(p) as w: chunks.append(np.frombuffer(w.readframes(w.getnframes()), '<i2'))
    os.remove(p)
    vols = [v for t, ws in log for r, v in ws if r == 8]
    print('instrument %2d on PSG A, period 400: volume register path (first 12 writes) %s ... max %d final %d' % (inst, vols[:12], max(vols), vols[-1]))
pcm = np.concatenate([np.concatenate([c, np.zeros(SR // 2, '<i2')]) for c in chunks])
with wave.open(os.path.join(OUT, 'unused_instruments_17_26_27_28.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
# usage census
import proof_sound as PS
from tune import W
used = {}
STARTS = {0: 'A', 14: 'H', 28: 'C', 74: 'I', 88: 'E', 166: 'D', 180: 'F', 194: 'J', 208: 'J', 222: 'J', 236: 'O', 242: 'K', 272: 'L', 302: 'G', 316: 'B/T', 322: 'M',
          336: 'N', 906: 'Q', 2580: 'S', 3398: 'P0', 4488: 'P1', 5302: 'P2', 5916: 'P3', 6794: 'P4', 7780: 'R'}
for off, tr in STARTS.items():
    p = off
    while True:
        op = W(p); p += 2
        if op < 7:
            a = W(p); p += 2
            if op < 3: used.setdefault(a, set()).add(tr)
        else: break
print('instrument -> starters:')
for i in range(35): print('  %2d %s' % (i, sorted(used.get(i, [])) or 'NONE'))

"""hitbox_gate.py <reclog>: check the player-attack-versus-enemy hit test ($f82e/$f8ba) against a recorded fight.
   reclog region 0 = player record $80100 (128 bytes), region 1 = pool A ($81000, 16 x $40). For every frame and every live pool A record in a state that
   runs the test (state not 1, 2, 4, 5; byte 0 bit 3 clear; +17 bit 5 clear) with the player's attack flag (+28) set, predict the hit from the boxes:
     attack box  = player +72..78 (R, L, B, T), body box = $6b000[type][state] words (R, L, B, T) + (x, y) of the enemy,
     hit iff Ra >= Lb and La < Rb and Ba >= Tb and Ta < Bb   (transcription of the cmp/bmi/bpl chain at $f8ca..$f8ea); the record's state must also be a testable one at the end of the previous frame
   and compare with the observed hit byte: the enemy's +6 bit 7 set at the end of the same frame."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
rows = []
for ln in open(sys.argv[1]):
    p = ln.split(); rows.append((int(p[0]), bytes.fromhex(p[1]), bytes.fromhex(p[2])))
def s16(v): return v - 65536 if v >= 32768 else v
def body(t, st, x, y):
    a = l(0x6b000 + 4 * t); b2 = l(a + 4 * st)
    return [(s16(w(b2 + 2 * i)) + (x if i < 2 else y)) for i in range(4)]
tp = fn = fp = tn = 0; bad = []
prevA = None
for f, P, A in rows:
    pA, prevA = prevA, A
    if P[28] == 0: continue
    atk = [s16(struct.unpack(">H", P[72 + 2 * i:74 + 2 * i])[0]) for i in range(4)]
    for i in range(16):
        r = A[i * 0x40:(i + 1) * 0x40]
        if r[0] & 0x80 == 0 or r[0] & 8 or r[3] in (0, 1, 2, 4, 5) or r[17] & 0x20: continue
        if pA is not None and (pA[i * 0x40] & 0x80 == 0 or pA[i * 0x40 + 3] in (0, 1, 2, 4, 5)): continue  # the state used by the test is the one the record had when the frame began (a state change later in the frame is not seen by the test)
        x = struct.unpack(">H", r[8:10])[0]; y = struct.unpack(">H", r[12:14])[0]
        try: bb = [s16(v & 0xffff) for v in body(r[2], r[3], x, y)]
        except Exception: continue
        pred = atk[0] >= bb[1] and atk[1] < bb[0] and atk[2] >= bb[3] and atk[3] < bb[2]
        obs = r[6] & 0x80 != 0
        if pred and obs: tp += 1
        elif pred and not obs: fp += 1; bad.append((f, i, "pred only", atk, bb, r[3]))
        elif obs and not pred: fn += 1; bad.append((f, i, "obs only", atk, bb, r[3]))
        else: tn += 1
print("frames x enemies tested: %d  hit predicted and observed: %d  predicted only: %d  observed only: %d  neither: %d" % (tp + fp + fn + tn, tp, fp, fn, tn))
for b in bad[:12]: print(b)

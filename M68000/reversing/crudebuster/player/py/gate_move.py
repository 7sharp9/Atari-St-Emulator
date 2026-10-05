"""gate_move.py <moves1 reclog>: walking speed, jump physics and the jab chain, checked frame by frame against the run of lua/plans/moves1.lua
   (region 0 = P1 record $80100; god-mode pokes on health and the blink timer; inputs are set after the end of frame N and read by the game at frame N+1)."""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(__file__))
from romlib import *
rows = {}
for ln in open(sys.argv[1]):
    p = ln.split(); rows[int(p[0])] = bytes.fromhex(p[1])
X = lambda f: struct.unpack(">I", rows[f][8:12])[0]; Y = lambda f: struct.unpack(">I", rows[f][12:16])[0]
d32 = lambda a, b_: ((b_ - a + 2 ** 31) % 2 ** 32 - 2 ** 31) / 65536
tot_ok = tot = 0
def report(name, ok, n):
    global tot_ok, tot
    tot_ok += ok; tot += n
    print("%-58s %3d of %3d  %s" % (name, ok, n, "PASS" if ok == n else "FAIL"))
# walking: held direction windows of the plan (set at 1720, 1800, ...; 40 frames each; skip the first 3 frames)
for name, lo, exp in (("walk right: dx=+1.0 per frame", 1724, (1.0, 0)), ("walk left: dx=-1.0", 1804, (-1.0, 0)), ("walk right+up: dx=+1.0", 2044, (1.0, 0)), ("walk left+up: dx=-1.0", 2204, (-1.0, 0)),
                      ("up / down (level 1 street has one lane): no motion", 1884, (0, 0)), ("right+down: no motion", 2124, (0, 0)), ("left+down: no motion", 2284, (0, 0))):
    ok = sum(1 for f in range(lo, lo + 34) if (d32(X(f), X(f + 1)), d32(Y(f), Y(f + 1))) == exp)
    report(name, ok, 34)
ok = sum(1 for f in range(1884, 1918) if (d32(Y(f), Y(f + 1))) == 0) + sum(1 for f in range(1964, 1998) if d32(Y(f), Y(f + 1)) == 0)
report("up and down held 80 frames: y never changes (one lane)", ok, 68)
# neutral jump (b2 set at 1120): frames where +5 == 3: y = y44 - (tab[+52] * 0x30 >> 8)
tab = [w(0xeab0 + 2 * i) for i in range(0x81)]
fr = [f for f in range(1115, 1160) if rows[f][5] == 3]
air = [f for f in fr if rows[f][24] == 5 and rows[f - 1][24] == 5]          # frames whose y was computed from the previous frame's phase
ok = 0
for f in air:
    ph = rows[f - 1][52]; g = struct.unpack(">H", rows[f][44:46])[0]
    ok += struct.unpack(">H", rows[f][12:14])[0] == g - ((tab[ph] * 0x30) >> 8)
report("neutral jump: y = ground - (sin[+52 of previous frame]*$30 >> 8)", ok, len(air))
report("neutral jump: sub-action 3 lasts 33 frames, phase +52 runs 0..$80 in steps of 4", int(len(fr) == 33 and rows[fr[-1]][52] == 0x80), 1)
peak = max(struct.unpack(">H", rows[f][44:46])[0] - struct.unpack(">H", rows[f][12:14])[0] for f in fr)
report("neutral jump peak height 48 px", int(peak == 48), 1)
# jump forward (right+b2 set at 1220): dx per frame while in the air
fr = [f for f in range(1218, 1260) if rows[f][5] == 3 and rows[f][24] == 6]
dxs = collections.Counter(round(d32(X(f), X(f + 1)), 4) for f in fr[1:-1])
report("jump forward: dx = +1.75 per airborne frame", dxs.get(1.75, 0), len(fr) - 2)
# jab chain (plan: taps at 980,987,994,1001,1008,1015,1022 ...): +29 grows 2 -> 4 -> 7, +28 set at animation frames 1, 3, 6
fr = [f for f in range(980, 1030) if rows[f][5] == 2]
a28 = sorted(set(rows[f][21] for f in fr if rows[f][28]))
report("jab chain 3 taps: attack flag at animation frames [1, 3, 6]", int(a28 == [1, 3, 6]), 1)
report("jab chain: +29 (animation length) reaches 7", int(max(rows[f][29] for f in fr) == 7), 1)
report("jab chain: 6 ticks per animation frame, 7 frames = 42 frames", int(len(fr) == 42), 1)
print("total %d of %d" % (tot_ok, tot))

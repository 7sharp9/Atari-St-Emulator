"""gate_2p.py <twop1 dir> <twop2 dir> <twop3 dir>: two-player facts from lua/reclog.lua runs (regions: 0 = $80100, 1 = $80180).
   twop1: P2 joins with its start button after P1 started: credit-1, record initialised next frame (health $38, spare lives 2), placed on P1, blinks 320 frames.
   twop2: P1 grabs P2 (b3, partner in front) and throws it: P2 goes to action $b, flies 4 px/frame, takes 4 damage on landing.
   twop3: P1's jab chain overlapping P2 does nothing (no friendly fire)."""
import sys, struct
def load(d):
    rows = {}
    for ln in open(d + "/reclog.txt"):
        p = ln.split(); rows[int(p[0])] = [bytes.fromhex(x) for x in p[1:]]
    return rows
ok = n = 0
def chk(name, cond, detail=""):
    global ok, n
    n += 1; ok += bool(cond); print("%-80s %s %s" % (name, "PASS" if cond else "FAIL", detail))
r = load(sys.argv[1])
chk("before the press P2 record is empty (+0 = 0), after it P2 +0 = $80 then init ($88/$c8), health $38, spare lives 2", r[960][1][0] == 0 and r[962][1][19] == 0x38 and r[962][1][20] == 2 and r[962][1][0] & 0xc8 == 0xc8,
    "P2 +0 %02x -> %02x, hp %02x lives %d" % (r[960][1][0], r[962][1][0], r[962][1][19], r[962][1][20]))
chk("P2 appears on top of P1 (same x, y word)", r[970][1][8:10] == r[970][0][8:10] and r[970][1][12:14] == r[970][0][12:14])
blink = [f for f in range(962, 1400) if r[f][1][0] & 0x10]
chk("P2 blinks (+0 bit 4 toggling) for 320 frames after joining", 318 <= (blink[-1] - 962) <= 322, "blink frames %d..%d" % (blink[0], blink[-1]))
r = load(sys.argv[2])
g = [f for f in range(1340, 1500) if r[f][1][4] == 0xb][0]
chk("P1 grab (+5=1) takes P2: P2 action $b, +1 = $20, P2 +58 = $10; P1 +26 = $c0, +58 = $88", r[g][1][1] == 0x20 and r[g][1][58] == 0x10 and r[g + 5][0][26] == 0xc0 and r[g + 5][0][58] == 0x88, "frame %d" % g)
fl = [f for f in range(g, g + 200) if r[f][1][4] == 0xb and r[f][1][1] & 0x90 == 0x90]   # flying: +1 = $b0 (bits 7 and 4)
dx = [struct.unpack(">H", r[f + 1][1][8:10])[0] - struct.unpack(">H", r[f][1][8:10])[0] for f in fl[1:-1]]
chk("thrown partner flies at +4 px per frame (%d frames)" % len(dx), len(dx) >= 15 and all(d == 4 for d in dx), "dx set %s" % sorted(set(dx)))
hp = [(f, r[f][1][19]) for f in range(g, g + 200) if r[f][1][19] != r[g][1][19]]
chk("landing costs the partner 4 health ($38 -> $34)", hp and hp[0][1] == 0x34, str(hp[:2]))
r = load(sys.argv[3])
atk = [f for f in range(1340, 1420) if r[f][0][28]]
chk("P1 attack flag set for %d frames with the box over P2" % len(atk), len(atk) >= 6)
chg = [f for f in range(1340, 1420) if r[f][1][19] != 0x38 or r[f][1][4] != 8 or r[f][1][1] != 0]
chk("P2 health, action and busy flags unchanged during P1's chain", not chg, "changed at %s" % chg[:3])
print("%d of %d" % (ok, n))

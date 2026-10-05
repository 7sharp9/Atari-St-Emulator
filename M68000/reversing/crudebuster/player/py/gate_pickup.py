"""gate_pickup.py <grab2 dir>: pick up and throw the garbage can (pool B type $0a) of level 1 from the saved state l1_wall (lua/plans/grab2.lua).
   regions: 0 = P1 record, 1 = pool B record 0 ($81400).
   pickup: during pose +27=4 at animation frame +21=1 the pickup box ($e758[action][facing]) overlaps the prop's box: P1 +26 = $c0, +58 bit 7, +92 = pointer to the prop, prop byte 0 gets bit 3 (carried);
   throw (b3 while carrying): +5 = 4, prop released with +17 = $c0, flies +4 px/frame at 24 px above the player until it leaves the screen."""
import sys, struct
rows = {}
for ln in open(sys.argv[1] + "/reclog.txt"):
    p = ln.split(); rows[int(p[0])] = [bytes.fromhex(x) for x in p[1:]]
ok = n = 0
def chk(name, cond, detail=""):
    global ok, n
    n += 1; ok += bool(cond); print("%-84s %s %s" % (name, "PASS" if cond else "FAIL", detail))
fr = sorted(rows)
g = [f for f in fr if rows[f][0][27] == 4 and rows[f][0][21] == 1][0]
chk("grab animation: +5=1, +27=4; the box test runs at animation frame +21=1 (first at frame %d)" % g, rows[g][0][5] == 1)
h = [f for f in fr if f > g and rows[f][0][26] == 0xc0][0]
chk("one frame later P1 +26 = $c0, +58 = $80, +92 = $00081400 (the can), +27 = 8", h == g + 1 and rows[h][0][58] == 0x80 and rows[h][0][92:96] == bytes.fromhex("00081400") and rows[h][0][27] == 8, "frame %d" % h)
chk("the can (byte 0) gets bit 3 set while carried", rows[h + 2][1][0] & 8 != 0, "byte0 %02x" % rows[h + 2][1][0])
t = [f for f in fr if f > h and rows[f][0][5] == 4][0]
rel = [f for f in fr if f > t and rows[f][0][26] == 0][0]
chk("b3 while carrying: +5=4 (throw), +26 cleared %d frames later" % (rel - t), rel - t <= 2, "press seen frame %d, released frame %d" % (t, rel))
fl = [f for f in fr if f >= rel and rows[f][1][0] & 0x80 and rows[f][1][17] & 0x40]
dx = [struct.unpack(">H", rows[f + 1][1][8:10])[0] - struct.unpack(">H", rows[f][1][8:10])[0] for f in fl[:-1]]
chk("thrown can flies at +4 px per frame (%d frames), at y = player y - 24" % len(dx), len(dx) > 30 and set(dx) == {4} and struct.unpack(">H", rows[fl[3]][1][12:14])[0] == struct.unpack(">H", rows[fl[3]][0][12:14])[0] - 24)
print("%d of %d" % (ok, n))

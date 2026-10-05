"""poolcensus.py <work RAM dump ($ff0000 at offset 0)> : census of the object pools by byte-18 tag (sizes from the layout read in the saved state):
 array $ff8568 (60 x $c0): idx0-1 players (tag 0), 2-14 tag 2, 15-20 tag 6, 21-28 tag 4, 29-58 tag 8, 59 tag $10; then tag $a x16 at $ffb2e8,
 tag $12 x10 at $ffbee8, tag $14 x10 at $ffc668.  'live' = byte 0 non-zero.  Character names: from the HUD name text (see report)."""
import sys, collections
d = open(sys.argv[1], "rb").read()
def b(a): return d[a - 0xff0000]
def w(a): o = a - 0xff0000; return int.from_bytes(d[o:o + 2], "big")
def l(a): o = a - 0xff0000; return int.from_bytes(d[o:o + 4], "big")
NAMES = {0x23f8c: "BRED", 0x24f2a: "DUG", 0x25ed0: "JAKE", 0x37be0: "HOLLY WOOD", 0x2bf94: "AXL(inferred)", 0x12be4: "CODY"}
pools = [("players", 0xff8568, 2), ("2", 0xff86e8, 13), ("6", 0xff90a8, 6), ("4", 0xff9528, 8), ("8", 0xff9b28, 30), ("10", 0xffb1a8, 1),
         ("a", 0xffb2e8, 16), ("12", 0xffbee8, 10), ("14", 0xffc668, 10)]
for name, base, n in pools:
    live = [i for i in range(n) if b(base + i * 0xc0) != 0]
    tags = collections.Counter(b(base + i * 0xc0 + 18) for i in range(n))
    print("pool %-7s %06x n=%2d tag(s)=%s live(b0!=0)=%d" % (name, base, n, ",".join("%02x" % t for t in tags), len(live)))
    for i in live:
        a = base + i * 0xc0
        p92 = l(a + 92) & 0xffffff
        print("   rec %2d %06x b0=%02x b1=%02x cls(2)=%02x state(3)=%02x b19=%02x w20=%04x x=%04x y=%04x hp=%04x/max %04x p92=%06x %s" % (
            i, a, b(a), b(a + 1), b(a + 2), b(a + 3), b(a + 19), w(a + 20), w(a + 6), w(a + 10), w(a + 24), w(a + 28), p92, NAMES.get(p92, "")))

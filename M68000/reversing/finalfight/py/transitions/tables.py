"""tables.py: decode every per-stage / per-area table read by the area and stage transition code (all addresses from the ROM listing).
usage: tables.py            prints all sections
Sections: stage order and TIME ($54f8/$553a, $51ec/$5210), area counts ($54b4), camera ($626c0 start, $626fa limits, $6268e modes, $6272a, $62a34 kind-$22 pairs),
player state 8 handlers ($dc08), state 10 ($f44e walk targets, $e9c2 variants, $eda0 sub 4 routines), area start state ($a414), player spawn offsets ($9d76),
stage-script segment continuations ($5cb6, from py/ai_kind45/script.py parse())."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rom import *

def per_area(base, size, fmt, label, nstage=10, wordtab=True):
    print(label)
    for s in range(nstage):
        a0 = base + rw(base + 2 * s)
        print("  stage %d @%06x" % (s, a0), ["  ".join(fmt(a0 + size * a)) for a in range(NAREAS[s])])

def main():
    print("== stage order ($54f8: 193(A5) += 1; 190(A5) = byte[$553a + 2*193]; 290(A5) = byte[$553b + 2*193])")
    print("  193:", " ".join("%d:(stage %d, bonus %d)" % (i, rb(0x553a + 2 * i), rb(0x553b + 2 * i)) for i in range(10)))
    print("== areas per stage ($54b4, byte table $54c0):", NAREAS)
    print("== TIME BCD per stage*4+area ($51ec, byte table $5210); a 60-frame second in a bonus stage ($52b6), 480 frames in a normal one ($5238, $1e0)")
    for s in range(8): print("  stage %d: %s" % (s, " ".join("%02x" % rb(0x5210 + 4 * s + a) for a in range(4))))
    per_area(0x62940, 8, lambda e: ["x=%04x y=%04x x2=%04x y2=%04x" % (rw(e), rw(e + 2), rw(e + 4), rw(e + 6))],
             "== area start camera ($626c0, table $62940): 1042(A5) x, 1046(A5) y, 1170(A5) x2, 1174(A5) y2")
    per_area(0x6285c, 8, lambda e: ["L=%04x R=%04x w3=%04x w4=%04x" % (rw(e), rw(e + 2), rw(e + 4), rw(e + 6))],
             "== camera limits ($626fa, table $6285c): words -> 1080(A5) left x limit (+44), 1078(A5) right x limit (+42), 1084(A5) (+48), 1082(A5) (+46) (y limits [I]; w3, w4 below)")
    per_area(0x627d8, 4, lambda e: ["%02x %02x %02x %02x" % (rb(e), rb(e + 1), rb(e + 2), rb(e + 3))],
             "== camera modes ($6268e, table $627d8): bytes -> 1086(A5) x mode (50(A6)), 1087(A5) y mode (51(A6)), 1214(A5) record 2 mode, 4th unread")
    per_area(0x62754, 4, lambda e: ["%04x,%04x" % (rw(e), rw(e + 2))], "== record 2 parameters ($6272a, table $62754): 1216(A5), 1218(A5)")
    for name, b in (("ch 0", 0x62ac2), ("ch 1", 0x62b16)):
        per_area(b, 4, lambda e: ["x=%04x y=%04x" % (rw(e), rw(e + 2))], "== pool-8 kind $22 %s spawned by $62a34 at an area start (stage < 6)" % name, nstage=6)
    print("== player state 8 handler ($dc08): A0 = $dc2a + word[$dc2a + 2*stage]; handler = A0 + word[A0 + 2*area]")
    for s in range(10):
        a0 = 0xdc2a + rw(0xdc2a + 2 * s)
        print("  stage %d" % s, ["%06x" % (a0 + rw(a0 + 2 * a)) for a in range(NAREAS[s])])
    print("== player state 10 sub 0 ($f44e, table $f488): 156(A6) x target, 158(A6) y (negative x: no walk, 158 word selects sub 6 / $a); one player, then 145(A6) != 0")
    for s in range(8):
        a0 = 0xf488 + rw(0xf488 + 2 * s)
        print("  stage %d" % s, ["a%d: %04x %04x | %04x %04x" % (a, rw(a0 + 8 * a), rw(a0 + 8 * a + 2), rw(a0 + 8 * a + 4), rw(a0 + 8 * a + 6)) for a in range(NAREAS[s])])
    print("== player state 10 sub 2 step 2 ($e9c2): byte table $e9e8 + word[$e9e8 + 2*stage], index = area; byte b = offset into the word table at $e9e0 (0 $ea10 default, 2 $ea7e, 4 $eada, 6 $eae8)")
    for s in range(10):
        a0 = 0xe9e8 + rw(0xe9e8 + 2 * s)
        bs = [rb(a0 + a) for a in range(NAREAS[s])]
        print("  stage %d" % s, bs, ["%06x" % (0xe9e0 + rw(0xe9e0 + b)) for b in bs])
    print("== player state 10 sub 4 ($eda0): A0 = $edd0 + word[$edd0 + 2*stage]; routine = A0 + word[A0 + 2*area]")
    for s in range(10):
        a0 = 0xedd0 + rw(0xedd0 + 2 * s)
        print("  stage %d" % s, ["%06x" % (a0 + rw(a0 + 2 * a)) for a in range(NAREAS[s])])
    print("== start state of every area ($a414, table $a446): long written to 2(A4)")
    for s in range(10):
        a0 = 0xa446 + rw(0xa446 + 2 * s)
        print("  stage %d" % s, ["%08x" % rl(a0 + 4 * a) for a in range(NAREAS[s])])
    print("== player spawn offset from the camera ($9d76, table $9dba): P1 dx,dy | P2 dx,dy")
    for s in range(8):
        a0 = 0x9dba + rw(0x9dba + 2 * s)
        print("  stage %d" % s, ["%04x,%04x | %04x,%04x" % (rw(a0 + 8 * a), rw(a0 + 8 * a + 2), rw(a0 + 8 * a + 4), rw(a0 + 8 * a + 6)) for a in range(NAREAS[s])])
    print("== stage-script segments and their continuation words ($5cb6: word after the entries = $8000 + 2*index of the table at $5cc2)")
    sys.path.insert(0, os.path.join(ROOT, 'reversing/finalfight/py/ai_kind45'))
    import script as S
    CONT = {0: 'wait for the tracked records or the timer, GO if w18, 30 frames, 278=0 ($5cce)', 2: 'next segment now ($5d1a)', 4: 'stage end, 297=1 ($5d26)',
            6: '291=1, 278=0 ($5d3e)', 8: 'stage end, 297=1 and $ff12fa=1 ($5d56)', 10: 'pause 30 frames ($5d74)'}
    base = S.SETS[2]
    for si in range(8):
        p = S.l(base + 4 * si); n = S.w(p) // 2
        for ai in range(n):
            a = p + S.w(p + 2 * ai)
            print("  stage %d area %d script %x" % (si, ai, a))
            for it in S.parse(a):
                if it[0] == 'seg':
                    sg = it[1]; h = sg['hdr']
                    print("    seg @%06x trigger %04x timer %5d count %d w18 %d %s cont %d: %s (entries %d, tracked %d)" % (
                        sg['at'], sg['trigger'], h[0], h[1], h[2], 'locks 278' if h[3] == 0 else 'no lock', sg['cont'], CONT.get(sg['cont'], '?'),
                        len(sg['ents']), sum(1 for e in sg['ents'] if e['track'])))
                elif it[0] == 'pause': print("    pause command @%06x" % it[1])
if __name__ == '__main__':
    main()

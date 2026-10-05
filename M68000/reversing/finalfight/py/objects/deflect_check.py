#!/usr/bin/env python3
"""deflect_check.py <log>... : a hovering bottle (deflect_run.sh) hit by the player's Button 1 attack. Prints, per log: the frame the bottle's +74 changed to 1 / its hurt index dropped,
the player's score (+132 BCD) change, whether a pool a kind $10 fire record appeared afterwards and the bottle's landing (state 4) frame."""
import sys
def b(h, o): return int(h[2*o:2*o+2], 16)
for log in sys.argv[1:]:
    rel = None; sc = None; ev = []; fire = None; st4 = None; b74 = None; lastx = None
    for line in open(log):
        p = line.split()
        if line.startswith('F '): rel = int(p[2].split('=')[1])
        elif line.startswith('R ') and rel is not None and rel >= 199:
            h = p[3]
            if p[1] == 'P':
                s = h[264:272]
                if sc is not None and s != sc: ev.append('score %s -> %s at %d' % (sc, s, rel))
                sc = s
            if p[1] == '6' and b(h, 19) == 4:
                if b(h, 74) != b74 and b74 is not None: ev.append('bottle +74 %02x -> %02x at %d (x=%04x y=%04x vx=%04x vy=%04x)' % (b74, b(h, 74), rel, int(h[12:16], 16), int(h[20:24], 16), int(h[160:164], 16), int(h[168:172], 16)))
                b74 = b(h, 74)
                if b(h, 2) == 4 and st4 is None: st4 = rel
            if p[1] == 'a' and b(h, 19) == 0x10 and fire is None: fire = rel
    print(log, ev, 'bottle reaches state 4 at', st4, '| fire created at', fire)

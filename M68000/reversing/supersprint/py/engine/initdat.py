"""INIT.DAT layout: $fd9a copies the file sequentially (source pointer -74(A4)) into A4-relative arrays with $fd7a(dst, len).
Parse the call list from ss.asm, cut INIT.DAT accordingly and cross-check against the live RAM of a snapshot taken after the load."""
import sys, os, re, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

def segments():
    lines = open(os.path.join(sscfg.WORK, 'ss.asm')).read().split('\n')
    i0 = next(i for i, l in enumerate(lines) if l.startswith('  $00fd9a:'))
    segs = []
    pend = None
    for l in lines[i0:i0 + 400]:
        m = re.match(r'\s+\$[0-9a-f]+: pea (-?\d+)\(A4\)', l)
        if m: dst = int(m.group(1)); continue
        m = re.match(r'\s+\$[0-9a-f]+: move\.w #\$([0-9a-f]+),-\(A7\)', l)
        if m: ln = int(m.group(1), 16); continue
        if 'jsr' in l and '$fd7a' in l: segs.append((dst, ln))
        if re.match(r'\s+\$[0-9a-f]+: rts', l) and segs: break
    return segs

if __name__ == '__main__':
    segs = segments()
    f = open(os.path.join(sscfg.FILES, 'INIT.DAT'), 'rb').read()
    print('%d segments, total %d bytes, INIT.DAT is %d bytes' % (len(segs), sum(l for _, l in segs), len(f)))
    r = Ram(sscfg.SNAP_RACE)
    o = 0; same = tot = 0
    for dst, ln in segs:
        chunk = f[o:o + ln]
        live = bytes(r.b[A4 + dst:A4 + dst + ln])
        eq = sum(1 for a, b in zip(chunk, live) if a == b)
        print('  file+%04x len %4d -> %6d(A4) = $%05x   bytes still equal in race snapshot: %d/%d' % (o, ln, dst, A4 + dst, eq, ln))
        o += ln; same += eq; tot += ln
    print('equal %d / %d' % (same, tot))

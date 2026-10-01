"""flag_census.py <snap>...: $438ee plane census. Planes: ALT=$438ee-16514, C1=$438ee-8257, C0=$438ee, FL=$438ee+8257.
Counts flag bits, bit1 cells vs settlement sites (+12 dest_cell, 4 cells c,c+1,c+64,c+65), and colour-plane relations."""
import sys
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap
B = 0x438ee
for s in sys.argv[1:]:
    r = ram_from_snap(ROOT / s)
    FL = lambda c: r[B + 8257 + c]
    n = 0x2000
    bits = [sum(1 for c in range(n) if FL(c) >> b & 1) for b in range(8)]
    print(s, 'flag bit counts b0..b7', bits)
    sett = []
    for i in range(240):
        a = 0x4f916 + 18 * i
        if r[a + 5]: sett.append(int.from_bytes(r[a + 12:a + 14], 'big'))
    ok = sum(1 for c in sett if all(FL(c + d) & 2 for d in (0, 1, 64, 65)))
    b1 = {c for c in range(n) if FL(c) & 2}
    claimed = {c + d for c in sett for d in (0, 1, 64, 65)}
    print('  settlements %d, all 4 cells bit1: %d; bit1 cells %d, in settlement claim set %d, outside %d' % (
        len(sett), ok, len(b1), len(b1 & claimed), len(b1 - claimed)))
    # colour plane values
    c0 = Counter(r[B + c] for c in range(n)); c1 = Counter(r[B - 8257 + c] for c in range(n))
    print('  colour0 distinct %d, colour1 distinct %d; zero: c0 %d c1 %d; both zero %d; ALT==0 all four corners %d' % (
        len(c0), len(c1), c0[0], c1[0], sum(1 for c in range(n) if r[B + c] == 0 and r[B - 8257 + c] == 0),
        sum(1 for c in range(n - 65) if not any(r[B - 16514 + c + d] for d in (0, 1, 64, 65)))))
    print('  c0 hist', sorted(c0.items())[:40])
    print('  c1 hist', sorted(c1.items())[:40])
    # bit7 vs altitude-derived diagonal check at $1021e: D4=A00,D5=A10,D6=A01,D7=A11
    A = lambda c: r[B - 16514 + c]
    dif = 0; tot = 0
    for c in range(n - 65):
        if r[B + c] == 0x1d or r[B - 8257 + c] == 0x1d: continue
        d4, d5, d6, d7 = A(c), A(c + 1), A(c + 64), A(c + 65)
        sg = lambda v: v - 256 if v > 127 else v
        e1 = abs(sg(d4) - sg(d7)); e2 = abs(sg(d5) - sg(d6))
        # $1021e: bset7 if |D5-D6| >= |D4-D7|
        tot += 1
        want = e2 >= e1
        if want and not FL(c) & 0x80: dif += 1
    print('  cells where |A10-A01|>=|A00-A11| but bit7 clear: %d of %d' % (dif, tot))

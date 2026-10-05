"""Compact trace of one record type: rectrace.py <objlog.txt> <type hex> [from] [to] [maxlines] [fields]  (default fields: +3 state, +16 variant, +18 sub, +5 health, +32).
One line per change of any chosen field, with the P1 position/state and hp."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ol
ty = int(sys.argv[2], 16)
f0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
f1 = int(sys.argv[4]) if len(sys.argv) > 4 else 1 << 30
mx = int(sys.argv[5]) if len(sys.argv) > 5 else 100
fields = [int(x) for x in sys.argv[6].split(",")] if len(sys.argv) > 6 else [3, 16, 18, 5, 32]
prev = {}
n = 0
for fr in ol.frames(sys.argv[1]):
    if not (f0 <= fr["f"] <= f1): continue
    for s, r in fr["A"].items():
        if r[2] != ty: continue
        k = tuple(r[o] for o in fields)
        if prev.get(s) != k:
            n += 1
            if n <= mx:
                print(f"f{fr['f']} s{s} P=({fr['px']:04x},{fr['py']:04x}) ps={fr['ps']:02x}/{fr['psub']:02x} hp={fr['hp']:02x} f40={fr['f40']:02x}/{fr['f41']:02x} x={ol.w(r,8):04x} y={ol.w(r,12):04x} " + " ".join(f"+{o}={r[o]:02x}" for o in fields))
            prev[s] = k
    for s in list(prev):
        if s not in fr["A"] or fr["A"][s][2] != ty:
            if n <= mx: print(f"f{fr['f']} s{s} GONE")
            del prev[s]

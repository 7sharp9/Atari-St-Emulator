"""P1 health drops in an objlog.txt (run with CB_HP=0): one line per frame where $80113 fell, with the amount, P1 state, and every live pool A / B record
(type:state:x) within 0x50 of P1 in x. usage: hpdrops.py <objlog.txt> [from] [to]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ol
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 0
f1 = int(sys.argv[3]) if len(sys.argv) > 3 else 1 << 30
prev = None
tot = 0
for fr in ol.frames(sys.argv[1]):
    if prev is not None and fr["hp"] < prev and f0 <= fr["f"] <= f1 and fr["f40"] & 0x80:
        near = [f"A{s}:{r[2]:02x}:s{r[3]:02x}:x{ol.w(r,8):04x}" for s, r in fr["A"].items() if abs(ol.w(r, 8) - fr["px"]) < 0x50]
        nearb = [f"B{s}:{r[2]:02x}:v{r[16]:02x}" for s, r in fr["B"].items() if abs(ol.w(r, 8) - fr["px"]) < 0x50 and r[2] in (0x3a, 0x2b, 0x2c)]
        print(f"f{fr['f']} hp {prev:02x}->{fr['hp']:02x} (-{prev - fr['hp']}) P1 state {fr['ps']:02x}/{fr['psub']:02x} {' '.join(near + nearb)}")
    prev = fr["hp"]

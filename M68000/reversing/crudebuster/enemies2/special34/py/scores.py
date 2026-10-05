"""P1 score changes in an objlog.txt (F line field 'score' = BCD long at $8013c, printed as hex digits): scores.py <objlog.txt>
Prints frame, delta (as decimal of the BCD digits) and the live pool A record types."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ol
prev = None
for fr in ol.frames(sys.argv[1]):
    s = fr["score"]
    if prev is not None and s != prev:
        d = int(f"{s:x}") - int(f"{prev:x}")
        types = " ".join(f"{r[2]:02x}:s{r[3]:02x}" for r in fr["A"].values())
        print(f"f{fr['f']} score {s:x} (+{d}) A:[{types}]")
    prev = s

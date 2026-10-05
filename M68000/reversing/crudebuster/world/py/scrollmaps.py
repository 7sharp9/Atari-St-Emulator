"""scrollmaps.py: decode the per-level scroll page maps ($8908 table; word index = (sy_page-1)*16 + (sx_page-1), page = high byte of $80406/$8040a).
Word: low nibble = blocked directions (bit0 up, bit1 right, bit2 down, bit3 left: a set bit blocks; the scroller $8a88 only moves up/down/right),
bit5 ($20) = hold while a lock-holder object keeps $80400 bit5 set, bit6 ($40) = forced scroll (all unblocked directions scroll every frame, $8b14),
bit7 ($80) = frozen (end of the scrollable area): the scroll routine is skipped."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
ptrs = [L(0x8908 + 4*i) for i in range(6)]
ends = ptrs[1:] + [0x8a88]
def sym(w):
    if w & 0x80: return " E "
    s = ""
    free = [n for n, bit in (("U", 1), ("R", 2), ("D", 4)) if not (w & bit) ]
    s = "".join(free) or "-"
    if w & 0x20: s += "k"
    if w & 0x40: s += "a"
    return s.ljust(3)
if __name__ == "__main__":
    for lv in range(6):
        n = (ends[lv] - ptrs[lv]) // 2
        print("level index %d map $%x, %d words" % (lv, ptrs[lv], n))
        for r in range(0, n, 16):
            row = [W(ptrs[lv] + 2*(r + c)) for c in range(min(16, n - r))]
            print("  row sy=%d:" % (r // 16 + 1), " ".join("%04x" % w for w in row))
            print("            ", " ".join(sym(w) for w in row))

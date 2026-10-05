"""Dump the level scripts $6c000 (A) and $6d000 (B): per level, entries (trigger word with axis, type, variant, x, y)."""
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
for name, base in (("A", 0x6c000), ("B", 0x6d000)):
    for lv in range(6):
        p = L(base + 4*lv); print("list %s level %d at %x" % (name, lv, p))
        while W(p) != 0xffff:
            t = W(p); print("  %05x trig=%s%04x type=%3d(%02x) var=%02x x=%04x y=%04x" % (p, "V" if t & 0x8000 else "H", t & 0x7fff, B(p+2) & 0x7f, B(p+2), B(p+3), W(p+4), W(p+6))); p += 8

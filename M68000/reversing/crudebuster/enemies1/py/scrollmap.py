"""Decode the per-level scroll map used by $8876 ($88a4..$88c0): ptr = longword table at $8908[level]; cell word at ptr + ((sy_hi-1)*16 + (sx_hi-1))*2 where sx_hi/sy_hi are the high bytes of the
scroll counters $8040a / $80406.  Low nibble ($80401) = scroll directions allowed (bit0 right? see doc), bit 5 = boss-lock cell (locked while $80400 bit 5 is set), bit 6, bit 7 = always locked.
usage: scrollmap.py [level]"""
import os, struct, sys
ROOT = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
R = open(os.path.join(ROOT, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def L(a): return struct.unpack(">I", R[a:a+4])[0]
def W(a): return struct.unpack(">H", R[a:a+2])[0]
for lv in ([int(sys.argv[1])] if len(sys.argv) > 1 else range(6)):
    base = L(0x8908 + 4*lv)
    print("level %d map at $%x" % (lv, base))
    for row in range(4):
        cells = [W(base + (row*16 + c)*2) for c in range(16)]
        print("  row %d (sy_hi=%d): " % (row+1, row+1) + " ".join("%04x" % c for c in cells))

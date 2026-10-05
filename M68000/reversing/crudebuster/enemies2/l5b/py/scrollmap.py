"""Dump the per-level scroll-permission grid read by $8876 (pointer table $8908, 16 words per row of 16 columns,
index (($80406>>8)-1)*0x20 + (($8040a>>8)-1)*2: word; low nibble -> $80401, bit5/bit7 special flags in $8044e).
usage: scrollmap.py [level]"""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
lvl = int(sys.argv[1]) if len(sys.argv) > 1 else 5
p = int.from_bytes(rom[0x8908 + 4 * lvl:0x890c + 4 * lvl], "big")
print("level", lvl, "grid at $%x" % p)
print("rows = y>>8 (1-based), cols = x>>8 (1-based); value = word; low nibble: allowed scroll dirs (bit0 down? bit1 right, bit2 up?, bit3 left?)")
print("     " + " ".join("x%02x " % c for c in range(1, 17)))
for r in range(16):
    row = [int.from_bytes(rom[p + 32 * r + 2 * c:p + 32 * r + 2 * c + 2], "big") for c in range(16)]
    print("y%02x  " % (r + 1) + " ".join("%04x" % v for v in row))

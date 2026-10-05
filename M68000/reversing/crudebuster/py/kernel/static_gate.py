"""Static gates of architecture.md on the decrypted program ROM (cbuster_main.bin).
usage: static_gate.py [rom.bin]
"""
import struct, sys, os
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
d = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
L = lambda a: struct.unpack(">I", d[a:a + 4])[0]
W = lambda a: struct.unpack(">H", d[a:a + 2])[0]
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m)

ok(L(0) == 0x84000 and L(4) == 0x600, "reset: SSP $84000, PC $600")
crash = [i for i in range(2, 64) if L(4 * i) != 0xffffffff and i != 28]
ok(L(0x70) == 0xb1e and all(L(4 * i) < 0x400 for i in crash), "every used vector but level 4 (IRQ4 -> $b1e) points below $400 (crash dumper); used vectors: %d" % len(crash))
ok(all(L(0x10358 + 4 * i) == 0x81000 + 0x40 * i for i in range(16)), "pool A: 16 records of $40 at $81000 (table $10358)")
ok(all(L(0x10398 + 4 * i) == 0x81400 + 0x40 * i for i in range(32)), "pool B: 32 records of $40 at $81400 (table $10398)")
ok(all(L(0x106a8 + 4 * i) == 0x81c00 + 0x20 * i for i in range(8)), "pool C: 8 records of $20 at $81c00 (table $106a8)")
def tbl(b, e):
    return [L(a) for a in range(b, e, 4)]
A, B = tbl(0x10418, 0x10558), tbl(0x10558, 0x106a8)
C = [L(a) for a in range(0x106c8, 0x10778, 4)]
ok(all(0x10778 <= x < 0x22000 for x in A), "pool A: 80 type handlers, all in $10778-$21fff (%d distinct)" % len(set(A)))
ok(all(0x28000 <= x < 0x2c000 for x in B), "pool B: 84 type handlers, all in $28000-$2bfff (%d distinct)" % len(set(B)))
ok(all(0x22000 <= x < 0x23000 for x in C), "pool C: 44 type handlers in $22000-$22fff (%d distinct)" % len(set(C)))
tot = {}
for base, name in ((0x6c000, "A"), (0x6d000, "B")):
    row = []
    for lvl in range(6):
        p = L(base + 4 * lvl); n = 0
        while W(p) != 0xffff: p += 8; n += 1
        row.append(n)
    tot[name] = row
ok(tot["A"] == [42, 33, 59, 32, 60, 47] and tot["B"] == [26, 57, 25, 34, 28, 6], "level scripts: list A (enemies) %s, list B (props) %s entries, $ffff terminated" % (tot["A"], tot["B"]))

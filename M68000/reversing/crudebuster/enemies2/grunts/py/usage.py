"""usage.py: every list A entry of the GRUNTS types (0x35 0x39 0x3f 0x40 0x44) in the level scripts, plus the carrier type 0x1a (which spawns riders of these types)
and the pool A spawners of these types (callers of $21eb6 with D6 = one of them): counts per level and variant."""
import os, collections
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
def w(a): return int.from_bytes(rom[a:a+2], "big")
types = (0x35, 0x39, 0x3f, 0x40, 0x44, 0x1a, 0x17)
cnt = collections.defaultdict(collections.Counter)
for lvl in range(6):
    a = l(0x6c000 + 4 * lvl)
    print(f"-- level index {lvl} (list A at ${a:06x})")
    while w(a) != 0xffff:
        trig, ty, var, x, y = w(a), rom[a + 2], rom[a + 3], w(a + 4), w(a + 6)
        if ty in types:
            print(f"   trig ${trig:04x} type {ty:02x} var {var:02x} x ${x:04x} y ${y:04x}")
            cnt[lvl][(ty, var)] += 1
        a += 8
print("-- counts per level index: (type, variant) x n")
for lvl in sorted(cnt): print(f"   level {lvl}: " + ", ".join(f"{t:02x}/{v:02x} x{n}" for (t, v), n in sorted(cnt[lvl].items())))

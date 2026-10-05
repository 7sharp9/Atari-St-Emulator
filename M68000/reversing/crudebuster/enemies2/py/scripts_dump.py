"""Parse the level scripts $6c000 (list A) and $6d000 (list B): per level, every entry and a type/variant census.
usage: scripts_dump.py   (env CB_ROM selects another image)  -> prints entries (trigger, type, variant, x, y) and a per-level count table."""
import os, sys, collections
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.environ.get("CB_ROM") or os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def w(a): return int.from_bytes(rom[a:a+2], "big")
def l(a): return int.from_bytes(rom[a:a+4], "big")
def entries(base, lvl):
    p = l(base + 4 * lvl); out = []
    while w(p) != 0xffff:
        out.append((p, w(p), rom[p+2], rom[p+3], w(p+4), w(p+6))); p += 8
    return out
if __name__ == "__main__":
    for name, base in (("A", 0x6c000), ("B", 0x6d000)):
        for lvl in range(6):
            es = entries(base, lvl)
            print(f"== list {name} level {lvl}: {len(es)} entries at ${l(base+4*lvl):x}")
            for p, t, ty, v, x, y in es:
                print(f"  {p:06x} trig={t:04x} {'V' if t & 0x8000 else 'H'}{t & 0x7fff:04x} type={ty:02x}({ty}) var={v:02x} x={x:04x} y={y:04x}")
    print("== census list A: (type,variant) per level")
    for lvl in range(6):
        c = collections.Counter((e[2], e[3]) for e in entries(0x6c000, lvl))
        print(lvl, " ".join(f"{t:02x}/{v:02x}x{n}" for (t, v), n in sorted(c.items())))

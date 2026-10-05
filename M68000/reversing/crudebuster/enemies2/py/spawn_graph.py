"""Static spawn graph: for every call of the three spawners in handler code, the (type, variant) loaded into D6/D7 just before.
 $21eb6 -> pool A record (D6 type, D7 variant), $21efa -> pool B (24 records), $21e72 -> pool C (hit boxes: D6 type, D7 facing).
Owner = handler containing the call (pool A $10418 / pool B $10558). Reads the linear listing: a `move.b #n,D6` / `moveq #n,D6` within the 8
preceding instructions gives the type; D7 likewise (or 4(A6) / 2(A6)+1 expressions are printed as text).
usage: spawn_graph.py [A|B|C]   (default A)"""
import os, re, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
L = [(int(x[3:9], 16), x[11:].strip()) for x in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt"))]
def owner(a):
    for name, base, n in (("A", 0x10418, 80), ("B", 0x10558, 84)):
        hs = sorted(set(l(base + 4 * i) for i in range(n)))
        lim = 0x22000 if name == "A" else 0x2c000
        lo = [h for h in hs if h <= a]
        if lo and a < lim and (name == "B") == (a >= 0x28000):
            h = lo[-1]
            return f"pool {name} ${h:06x} types " + ",".join(f"{i:02x}" for i in range(n) if l(base + 4 * i) == h)
    return "other/shared"
target = {"A": "21eb6", "B": "21efa", "C": "21e72"}[sys.argv[1] if len(sys.argv) > 1 else "A"]
def val(ctx, reg):
    v = None
    for _, ins in ctx:
        m = re.match(rf"(?:move\.b|moveq|move\.w) #?\$?(-?[0-9a-f]+),{reg}$", ins)
        if m:
            raw = m.group(1)
            v = ("$%x" % int(raw, 16)) if ins.startswith("move") and "#$" in ins else raw
            if ins.startswith("moveq"):
                v = "$%x" % (int(raw) & 0xff)
        else:
            m2 = re.match(rf"move\.b (\S+),{reg}$", ins)
            if m2: v = m2.group(1)
    return v
rows = {}
for i, (a, ins) in enumerate(L):
    if re.search(rf"\${target}(\.l)?$", ins) or ins.endswith(f"== ${target}"):
        if not (ins.startswith("jsr") or ins.startswith("bsr")): continue
        ctx = L[max(0, i - 8):i]
        rows.setdefault(owner(a), []).append((a, val(ctx, "D6"), val(ctx, "D7")))
for o in sorted(rows):
    print(o)
    for a, t, v in rows[o]: print(f"    call ${a:06x}: type {t} variant {v}")

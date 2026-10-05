"""List every writer of $80040 bit 2/3/4 and $80041 bit 7 in the linear listing, with the owning handler type
(pool A handler by address range via table $10418; code at $22000-$27fff is shared engine and is attributed to the types whose
24/30-entry state tables point at the routine) and which levels' scripts spawn that type.
usage: setters.py   (M68000_ROOT or derived from __file__)"""
import os, re, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
lin = {}
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lin[int(a[1:], 16)] = ins
starts = sorted((l(0x10418 + 4 * t), t) for t in range(0x50))
def owner(pc):
    if not (0x10778 <= pc < 0x22000): return None
    best = None
    for s, t in starts:
        if s <= pc: best = (s, t)
    return best
# state tables: reuse handler_tables.tables over the pool A code, map table entries to the type that owns the dispatch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
import importlib.util
spec = importlib.util.spec_from_file_location("ht", os.path.join(root, "reversing/crudebuster/enemies2/py/handler_tables.py"))
sys.argv = ["x", "0", "0"]
ht = importlib.util.module_from_spec(spec); spec.loader.exec_module(ht)
users = {}   # routine -> set of types whose table lists it
for a, t, ents in ht.tables(0x10778, 0x22000):
    o = owner(a)
    for i, e in enumerate(ents):
        users.setdefault(e, set()).add((o[1] if o else None, i))
# level scripts: which levels spawn which type
spawn = {}
for lv in range(6):
    p = l(0x6c000 + 4 * lv)
    while rom[p:p+2] != b"\xff\xff":
        spawn.setdefault(rom[p + 2], set()).add(lv); p += 8
pat = re.compile(r"(bset|bclr) #(\d),\$8004([01])\.l")
for a in sorted(lin):
    m = pat.match(lin[a])
    if not m: continue
    op, bit, which = m.group(1), int(m.group(2)), m.group(3)
    if (which, bit) not in (("0", 2), ("0", 3), ("0", 4), ("1", 7)): continue
    o = owner(a)
    if o:
        ty = f"pool A type {o[1]:#x} (handler ${o[0]:06x}), spawned in levels {sorted(spawn.get(o[1], []))}"
    elif 0x22000 <= a < 0x28000:
        # shared routine containing this pc: find the routine start = the highest table entry <= pc
        cand = max((e for e in users if e <= a), default=None)
        ts = sorted({t for t, i in users.get(cand, [])}) if cand else []
        ty = f"shared engine routine ${cand:06x} used (state slot) by types " + ", ".join(f"{t:#x}" for t in ts if t is not None) if cand else "shared engine"
    else:
        ty = "outside pool A/shared code (player/main loop)"
    print(f"$8004{which} bit{bit} {op} at ${a:06x}: {ty}")

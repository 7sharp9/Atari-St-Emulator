"""List every writer of the level/boss flags in the linear listing, mapped to its owning handler (pool A type, pool B type or other code).
Flags: $80040 bits 2,3,4 ; $80041 bit 7 ; $80400 bits 5,6,7 (camera lock/auto-scroll). Owner = the handler of the address in pool A ($10418, 80 types)
or pool B ($10558, 84 types); `other` otherwise; $22000-$27fff is the shared engine (earlier version attributed the shared boss-death setters to type $4f, the last handler below them). usage: flag_setters.py"""
import os, re, struct
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
A = sorted(set((l(0x10418 + 4 * i), i) for i in range(80)))
B = sorted(set((l(0x10558 + 4 * i), i) for i in range(84)))
def owner(a):
    best = None
    for name, tab in (("A", A), ("B", B)):
        for h, ty in tab:
            if h <= a: 
                nxt = min([x for x, _ in tab if x > h] + [1 << 30])
                if a < nxt and (best is None or True):
                    types = [t for hh, t in tab if hh == h] if False else None
                    best = (name, h)
    return best
types_by_h = {}
for name, base, n in (("A", 0x10418, 80), ("B", 0x10558, 84)):
    for i in range(n):
        types_by_h.setdefault((name, l(base + 4 * i)), []).append(i)
def own(a):
    if 0x22000 <= a < 0x28000: return "shared engine code (boss death states $23cf2/$23e66 and helpers)"
    c = []
    for name, base, n in (("A", 0x10418, 80), ("B", 0x10558, 84)):
        hs = sorted(set(l(base + 4 * i) for i in range(n)))
        lo = [h for h in hs if h <= a]
        if lo:
            h = lo[-1]
            nxt = min([x for x in hs if x > h] + [1 << 30])
            if a < nxt and a >= 0x10000: c.append((name, h))
    if not c: return "other"
    name, h = c[-1] if len(c) == 1 else max(c, key=lambda x: x[1])
    return f"pool {name} handler ${h:06x} types {[hex(t) for t in types_by_h[(name, h)]]}"
pats = [(r"(bset|bclr) #(\d),\$80040\.l", "$80040"), (r"(bset|bclr) #(\d),\$80041\.l", "$80041"), (r"(bset|bclr) #(\d),\$80400\.l", "$80400")]
want = {("$80040", 2), ("$80040", 3), ("$80040", 4), ("$80041", 7), ("$80400", 5), ("$80400", 6), ("$80400", 7)}
rows = []
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a = int(line[3:9], 16); ins = line[11:].strip()
    for p, name in pats:
        m = re.match(p, ins)
        if m and (name, int(m.group(2))) in want:
            rows.append((name, int(m.group(2)), m.group(1), a, own(a)))
rows.sort(key=lambda r: (r[0], r[1], r[3]))
for name, bit, op, a, o in rows: print(f"{name} bit{bit} {op} at ${a:06x}  {o}")

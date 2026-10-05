"""List every caller of the pool spawners ($21eb6 pool A, $21efa pool B, $21e72 pool C) with the D6 (type) / D7 (variant) immediates set before it,
and the pool A handler (type) whose code range holds the call.   usage: spawners.py [A|B|C]  (default A)"""
import os, re, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
hs = [int.from_bytes(rom[0x10418 + 4 * i:0x10418 + 4 * i + 4], "big") for i in range(80)]
order = sorted(set(hs))
def owner(a):
    best = None
    for h in order:
        if h <= a: best = h
    if best is None or a >= 0x22000: return None
    return [i for i, x in enumerate(hs) if x == best]
pool = {"A": 0x21eb6, "B": 0x21efa, "C": 0x21e72, "S": 0x24056}[sys.argv[1] if len(sys.argv) > 1 else "A"]
lines = []
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lines.append((int(a[1:], 16), ins))
for i, (a, ins) in enumerate(lines):
    m = re.match(r"jsr (\$[0-9a-f]+)\.l$", ins)
    m2 = re.match(r"jsr (-?\d+)\(PC\) == \$([0-9a-f]+)$", ins)
    tgt = int(m.group(1)[1:], 16) if m else (int(m2.group(2), 16) if m2 else None)
    if tgt != pool: continue
    d6 = d7 = None
    for b, ins2 in reversed(lines[max(0, i - 8):i]):
        mm = re.match(r"move\.b #\$([0-9a-f]+),D6", ins2) or re.match(r"moveq #(\d+),D6", ins2)
        if mm and d6 is None: d6 = mm.group(1)
        mm = re.match(r"move\.b #\$([0-9a-f]+),D7", ins2) or re.match(r"moveq #(\d+),D7", ins2)
        if mm and d7 is None: d7 = mm.group(1)
    o = owner(a)
    print(f"${a:06x} D6={d6} D7={d7} owner types={[f'{t:02x}' for t in o] if o else None}")

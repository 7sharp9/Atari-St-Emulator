"""List every caller of the pool A spawner $21eb6 with the D6 (type) / D7 (variant) loaded in the few lines before it,
the enclosing handler (by the handler range table of $10418) and the instruction text. usage: spawners.py [type hex ...]"""
import os, sys, re
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
lines = []
for line in open(os.path.join(root, "scratchpad/crudebuster/all_lin.txt")):
    a, _, ins = line.strip().partition(": ")
    lines.append((int(a[1:], 16), ins))
hand = sorted(set(int.from_bytes(rom[0x10418+4*t:0x10418+4*t+4], "big") for t in range(80)))
types_by_h = {}
for t in range(80): types_by_h.setdefault(int.from_bytes(rom[0x10418+4*t:0x10418+4*t+4], "big"), []).append(t)
def owner(a):
    h = max([x for x in hand if x <= a] or [0])
    return h, types_by_h.get(h)
for i, (a, ins) in enumerate(lines):
    if ("$21eb6" in ins or "== $21eb6" in ins) and ins.startswith("jsr"):
        d6 = d7 = None
        for b, jn in lines[max(0, i-8):i]:
            m = re.match(r"(?:moveq|move\.b|move\.w) #\$?(-?[0-9a-f]+),D([67])", jn)
            if m:
                v = int(m.group(1), 16) if "$" in jn else int(m.group(1))
                if m.group(2) == "6": d6 = v
                else: d7 = v
        h, ts = owner(a)
        print(f"${a:06x} in handler ${h:06x} (types {[hex(t) for t in ts or []]}) spawns D6={d6 and hex(d6)} D7={d7 and hex(d7)}   {ins}")

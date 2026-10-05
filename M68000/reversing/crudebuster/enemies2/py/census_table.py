"""Markdown census tables of list A (and list B) for the given levels from the ROM, with type names from NAMES (json file, optional).
usage: census_table.py A|B <level> [names.json]   -> markdown table: order, trigger (H = $8040a, V = $80406), type, variant, x, y, name, observed arrival
Observed arrival: if out/l<level>/objlog.txt exists, the scroll x of the frame in which a record matching the entry became active."""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from scripts_dump import entries
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
lst, lvl = sys.argv[1], int(sys.argv[2])
names = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
es = entries(0x6c000 if lst == "A" else 0x6d000, lvl)
log = os.path.join(root, f"reversing/crudebuster/enemies2/out/l{lvl}/objlog.txt")
acts = []
if lst == "A" and os.path.exists(log):
    pf = {}; sc = {}
    for line in open(log):
        p = line.split()
        if p[0] == "F": sc[int(p[1])] = (int(p[3], 16), int(p[4], 16))
        elif p[0] == "A": pf.setdefault(int(p[1]), {})[int(p[2])] = bytes.fromhex(p[3])
    for f in sorted(pf):
        for s, r in pf[f].items():
            was = pf.get(f - 1, {}).get(s)
            if was is None or was[2] != r[2]: acts.append((f, r))
used = set()
print("| # | trigger | type | var | x | y | name | first seen at scroll |")
print("|---|---|---|---|---|---|---|---|")
for i, (p, t, ty, v, x, y) in enumerate(es):
    ty &= 0x7f if lst == "B" else 0xff
    seen = ""
    for k, (f, r) in enumerate(acts):
        if k in used: continue
        if r[2] == ty and r[16] == v and abs(int.from_bytes(r[8:10], "big") - x) <= 0x20 and abs(int.from_bytes(r[12:14], "big") - y) <= 0x20:
            used.add(k); seen = f"x=${sc[f][0]:04x} y=${sc[f][1]:04x} (frame {f})"; break
    print(f"| {i+1} | {'V' if t & 0x8000 else 'H'}${t & 0x7fff:03x} | ${ty:02x} | {v} | ${x:04x} | ${y:04x} | {names.get(f'{ty:02x}', '')} | {seen} |")

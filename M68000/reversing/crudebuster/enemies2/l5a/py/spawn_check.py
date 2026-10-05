"""Compare the first row of every pool A episode (a record seen active for the first time, or after a gap) in drive5.lua logs with the level 5 list A script entries
($6c82c, parsed from agents/enemies2/out/scripts.txt): an entry is 'seen' when an episode of the same type/variant and x/y within 8 px (the handler moves the record in the spawn frame) first appears.
Spawns by handlers (types $41, $47, $49 ...) have no script entry and are listed as 'not in script'.
usage: spawn_check.py <log> [<log> ...] [--types 4a,4b,4c,4d]"""
import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))
from loglib import load, u16
args = sys.argv[1:]
types = None
if "--types" in args:
    i = args.index("--types"); types = {int(x, 16) for x in args[i+1].split(",")}; args = args[:i] + args[i+2:]
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
ent = []
sec = False
for line in open(os.path.join(root, "reversing/crudebuster/enemies2/out/scripts.txt")):
    if line.startswith("== list A level 5"): sec = True; continue
    if line.startswith("==") and sec: break
    if sec:
        m = re.search(r"trig=(\w+) .*type=(\w+)\(\d+\) var=(\w+) x=(\w+) y=(\w+)", line)
        if m: ent.append(tuple(int(x, 16) for x in m.groups()))
seen = {}
other = {}
for log in args:
    F, eps = load(log)
    for ep in eps:
        f, b = ep.rows[0]
        key = (ep.type, ep.var, u16(b, 8), u16(b, 12))
        hit = [e for e in ent if (e[1], e[2]) == key[:2] and abs(e[3] - key[2]) <= 8 and abs(e[4] - key[3]) <= 8]
        if hit:
            seen.setdefault(hit[0], []).append((os.path.basename(os.path.dirname(log)), f, F[f]['sx'], F[f]['sy']))
        else:
            other.setdefault((ep.type, ep.var), []).append((os.path.basename(os.path.dirname(log)), f, u16(b, 8), u16(b, 12), b[3]))
print("script entries (trig type var x y) seen as a first row of an episode with the same type/variant and x/y within 8 px (the handler moves the record in the spawn frame):")
for e in ent:
    if types and e[1] not in types: continue
    s = seen.get(e)
    print(f"  trig {e[0]:04x} type {e[1]:02x} var {e[2]:02x} x {e[3]:04x} y {e[4]:04x}: " + (f"{len(s)} run(s), first {s[0][0]} frame {s[0][1]} scroll {s[0][2]:04x},{s[0][3]:04x}" if s else "-"))
print("episodes not matching a script entry (type, var): count, examples")
for k, v in sorted(other.items()):
    if types and k[0] not in types: continue
    print(f"  {k[0]:02x}/{k[1]:02x}: {len(v)}  e.g. {v[0]}")

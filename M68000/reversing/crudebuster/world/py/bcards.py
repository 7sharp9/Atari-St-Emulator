"""bcards.py: markdown tables for pool B (84) and pool C (44) types from static data (handler class, script usage, code spawn sites),
the census logs (out/c/census_lN.txt) and the forced-spawn logs (out/f/force_pv0_B.txt free/on, force_hit0.txt, force_pv0_C.txt).
The 'draws' column is read by eye from shots/B_pv*_N.png (forced-spawn contact sheets), tag (D) = drawn, never from a name table."""
import sys, os, re
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")
Bt = [L(0x10558 + 4*i) for i in range(84)]; Ct = [L(0x106c8 + 4*i) for i in range(44)]
script = [Counter() for _ in range(6)]
for lv in range(6):
    p = L(0x6d000 + 4*lv)
    while W(p) != 0xffff: script[lv][B(p+2) & 0x7f] += 1; p += 8
# code spawn sites (callers of $21efa with literal D6) from callers.py
import subprocess
PY = sys.executable
txt = subprocess.run([PY, os.path.join(HERE, "callers.py"), "21efa"], capture_output=True, text=True).stdout
spawn = defaultdict(set)
for l in txt.split("\n"):
    m = re.match(r"(\$[0-9a-f]+) \| \S+ (moveq|move\.\w) #(\$?)(-?[0-9a-f]+),D6", l)
    if m:
        ty = int(m.group(4), 16) if (m.group(2) != "moveq" and True) else int(m.group(4))
        if m.group(2) == "moveq" and m.group(3) == "$": ty = int(m.group(4), 16)
        spawn[ty].add(m.group(1))
# census
cen = defaultdict(Counter)
for lv in range(6):
    fn = os.path.join(OUT, "c", "census_l%d.txt" % lv)
    if not os.path.exists(fn): continue
    for l in open(fn):
        if l.startswith("S "):
            t = l.split(" "); h = t[4].strip()
            if t[2] == "B": cen[int(h[4:6], 16)][lv] += 1
def force(fn):
    res = {}; cur = None
    if not os.path.exists(fn): return res
    for l in open(fn):
        l = l.rstrip()
        if l.startswith("CASE"):
            m = re.match(r"CASE (\w) (\d+) (\w+) var=(\d+)", l); cur = (int(m.group(2)), m.group(3)); res[cur] = {"D": None, "hp": [], "kids": []}
        elif cur and l.startswith("D "): res[cur]["D"] = int(l.split()[1])
        elif cur and l.startswith("P "):
            f = l.split(); res[cur]["hp"].append(int(f[3], 16))
    return res
fr = force(os.path.join(OUT, "f", "force_pv0_B.txt")); hit = force(os.path.join(OUT, "f", "force_hit0.txt"))
if __name__ == "__main__":
    from bnames import NAMES
    print("| type | draws (D) | handler | script uses (stage: n) | spawned by code at | census (stage: n) | free: dies at frame | on player: hp change | punch test (b1 x5 per 20 frames, 100 frames) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for t in range(84):
        su = ", ".join("%d: %d" % (lv+1, script[lv][t]) for lv in range(6) if script[lv][t]) or "-"
        sp = " ".join(sorted(spawn.get(t, []))[:4]) or "-"
        ce = ", ".join("%d: %d" % (lv+1, cen[t][lv]) for lv in range(6) if cen[t][lv]) or "-"
        f = fr.get((t, "free"), {}); o = fr.get((t, "on"), {}); h = hit.get((t, "hit"), {})
        hp = [x for x in o.get("hp", [])]; dmg = ""
        if hp and min(hp) < 0x38: dmg = "-%d" % (0x38 - min(hp))
        print("| %d | %s | `$%x` | %s | %s | %s | %s | %s | %s |" % (t, NAMES[t], Bt[t], su, sp, ce, f.get("D", "-") if f.get("D") else "never (100)", dmg or "0", ("dies at %s" % h["D"]) if h.get("D") else "survives"))

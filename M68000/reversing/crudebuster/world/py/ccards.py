"""ccards.py: markdown table for pool C (44 types): handler, code spawn sites ($21e72 callers), harness damage (force_pv0_C.txt: record on P1, parent = P1 record)."""
import sys, os, re, subprocess
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
from cbrom import *
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "out")
Ct = [L(0x106c8 + 4*i) for i in range(44)]
txt = subprocess.run([sys.executable, os.path.join(HERE, "callers.py"), "21e72"], capture_output=True, text=True).stdout
sites = defaultdict(list)
for l in txt.split("\n"):
    m = re.match(r"(\$[0-9a-f]+) \| \S+ move\.b #\$?([0-9a-f]+),D6", l)
    if m: sites[int(m.group(2), 16)].append(m.group(1))
dmg = {}; died = {}; cur = None
for l in open(os.path.join(OUT, "f", "force_pv0_C.txt")):
    l = l.rstrip()
    if l.startswith("CASE"): cur = int(l.split()[2]); dmg[cur] = []; died[cur] = None
    elif cur is not None and l.startswith("P "): dmg[cur].append(int(l.split()[3], 16))
    elif cur is not None and l.startswith("D "): died[cur] = int(l.split()[1])
print("| type | handler | spawned by pool-A code at | harness: damage to P1 (hp of 56) | record life (frames) |")
print("|---|---|---|---|---|")
for t in range(44):
    d = 0x38 - min(dmg.get(t, [0x38])); 
    print("| %d | `$%x` | %s | %s | %s |" % (t, Ct[t], " ".join(sites.get(t, [])) or "-", d if d else "0", died.get(t) or ">=60"))

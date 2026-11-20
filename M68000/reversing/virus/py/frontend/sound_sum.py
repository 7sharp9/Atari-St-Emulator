"""sound_sum.py [snap] [steps]: every sound trigger in a demo run comes from one of the whole-image call sites.
`hits <steps>` on the shared body $17932 and on all call-site addresses from sound_sites.py; the site counts must sum to the body's count.
Default snapshot $VIRUS_WORK/demo/S1b.snap, 300,000,000 steps (about 1 minute). Output: per-effect totals and 'sum ok' or 'sum FAIL'."""
import os, re, subprocess, sys, collections
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from fcommon import run, WORK
snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "demo", "S1b.snap")
steps = int(sys.argv[2]) if len(sys.argv) > 2 else 300000000
sites = {}
for l in subprocess.run([sys.executable, os.path.join(d, "sound_sites.py")], capture_output=True, text=True).stdout.splitlines():
    a, kind, d0, _ = l.split("\t"); sites[a[1:].lstrip("0")] = int(d0[3:])
out = run(snap, [f"hits {steps} 17932 " + " ".join(sites)])
cnt = {m.group(1): int(m.group(2)) for m in re.finditer(r"\$0*([0-9a-f]+)\s+(\d+)\s+first", out)}
total = cnt["17932"]; per = collections.Counter()
for a, e in sites.items(): per[e] += cnt.get(a, 0)
print("sites:", len(sites), "effects triggered:", dict(sorted((e, n) for e, n in per.items() if n)))
print(f"sum {'ok' if sum(per.values()) == total else 'FAIL'}: site counts sum {sum(per.values())} vs body count {total}")

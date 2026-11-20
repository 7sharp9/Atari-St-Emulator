"""sound_verify.py [snap] [N]: stop N times at $17932 (the shared body of Sound_Trigger $17924 / Sound_TriggerAttenuated $1790c),
read D0 (effect id) and the return address, and check each (D0, return-6) against the static call-site table from sound_sites.py.
Output: the observed (effect, caller) pairs with counts and 'matched N/N'."""
import os, re, subprocess, sys, collections
d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, d)
from fcommon import run, ROOT, WORK
snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "demo", "S1b.snap")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 120
static = {}
for l in subprocess.run([sys.executable, os.path.join(d, "sound_sites.py")], capture_output=True, text=True).stdout.splitlines():
    a, kind, d0, _ = l.split("\t"); static[int(a[1:], 16)] = (kind, int(d0[3:]))
cmds = []
for _ in range(N): cmds += ["bp 17932 20000000", "bt 1"]
out = run(snap, cmds)
d0s = [int(m, 16) for m in re.findall(r"^D0:([0-9a-f]{8})", out, re.M)]
rets = [int(m, 16) for m in re.findall(r"return address \(A7\) = \$([0-9a-f]{8})", out)]
ok = 0; seen = collections.Counter()
for d0, r in zip(d0s, rets):
    site = r - 6                        # jsr abs.l is 6 bytes
    seen[(d0, f"${site:06x}")] += 1
    if site in static and static[site][1] == d0: ok += 1
for (d0, s), n in sorted(seen.items()): print(f"effect {d0:2d} from {s}  x{n}")
bad = sum(1 for d0, r in zip(d0s, rets) if (r - 6) in static and static[r - 6][1] == d0 + 1)     # control: every effect id shifted by one
print(f"matched {ok}/{len(d0s)} stops (D0, caller) against the static table")
print(f"control (static table ids + 1): matched {bad}/{len(d0s)} stops")

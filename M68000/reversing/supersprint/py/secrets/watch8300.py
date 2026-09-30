"""watch8300.py - who writes -8300(A4)? Watch the word over attract (27M steps) and a race->winner flow (ss_prep, 20M)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
for tag, snap, steps in (('attract', sscfg.SNAP_ATTRACT, 27000000), ('race', sscfg.SNAP_RACE, 20000000)):
    r = R(snap)
    addr = sscfg.A4 - 8300
    print(tag, 'initial value', r.g16(-8300))
    r.cmd('watch %x 2' % addr); r.err()
    pcs = {}
    done = 0
    while done < steps:
        r.cmd('s 1000000'); done += 1000000
        for l in r.err().splitlines():
            m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) Write(\w+) \$([0-9a-f]+) <- \$([0-9a-f]+)', l)
            if m: pcs.setdefault(m.group(2), []).append((int(m.group(1)), m.group(3), m.group(5)))
    print(tag, 'writers (pc -> count, first):', {k: (len(v), v[0]) for k, v in pcs.items()}, 'final', r.g16(-8300))
    r.close()

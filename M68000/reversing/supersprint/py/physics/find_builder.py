"""Which PCs write a RAM region while a race is being set up from ss_select.snap (drive.repl join sequence)?
usage: find_builder.py <hexaddr> <len> [--chunk N]   prints pc, count, first/last step, min/max address written."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pl import *

lo, n = int(sys.argv[1], 16), int(sys.argv[2])
script = ['kbd 2a', 's 3000000', 'kbd aa', 's 3000000', 'kbd fe 80', 's 3000000', 'kbd fe 00', 's 6000000']
e = Emu(sscfg.SNAP_SELECT)
e.cmd('watch %x %d' % (lo, n))
seen = {}
for c in script:
    out, _ = e.cmd(c)
    for l in out:
        m = re.match(r'WATCH: step=(\d+) pc=\$([0-9a-f]+) (\w+) \$([0-9a-f]+)', l)
        if m:
            pc, st, a = int(m.group(2), 16), int(m.group(1)), int(m.group(4), 16)
            d = seen.setdefault(pc, [0, st, st, a, a])
            d[0] += 1; d[2] = st; d[3] = min(d[3], a); d[4] = max(d[4], a)
print('pc count first_step last_step minaddr maxaddr')
for pc, d in sorted(seen.items(), key=lambda kv: kv[1][1]):
    print('%06x %6d %d %d %x %x' % (pc, *d))
e.close()

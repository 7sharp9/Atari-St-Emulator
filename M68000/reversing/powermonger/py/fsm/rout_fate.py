#!/usr/bin/env python3
"""rout_fate.py <watch file>...: from WATCH lines over the object array's bytes 30/31 (natrun-style filtered `watch 51b66 25600`),
follow every ROUT stamp (pc $561c, prev := $3c) and classify what happens to that record's previous mode before its next
mode write by the $10 arrival ($14fdc):
  kept    - prev still $3c at the arrival: the arrival sets mode $3c
  rewrit  - prev rewritten first (by which pc, e.g. $3c84.. inside $3c08 via the $1b8c unlink, or a later order)
  open    - no arrival before the end of the run.
Prints counts and, per class, the rewriting pcs."""
import re, sys, collections
R = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) (\w+) \$([0-9a-f]{8}) <- \$([0-9a-f]+)')
for f in sys.argv[1:]:
    ev = collections.defaultdict(list)
    for l in open(f):
        m = R.search(l)
        if not m:
            continue
        a = int(m.group(4), 16); off = (a - 0x51b66) % 50
        pc = int(m.group(2), 16); v = int(m.group(5), 16)
        if m.group(3) == 'WriteWord':
            ev[a - off].append((pc, 'P', v >> 8)); ev[a - off].append((pc, 'M', v & 0xff))
        else:
            ev[a - off].append((pc, 'P' if off == 30 else 'M', v))
    cls = collections.Counter(); who = collections.Counter(); arr_modes = collections.Counter()
    for rec, es in ev.items():
        for i, (pc, k, v) in enumerate(es):
            if pc != 0x561c:
                continue
            prev, fate = 0x3c, 'open'
            for pc2, k2, v2 in es[i + 1:]:
                if pc2 == 0x561c:
                    break
                if k2 == 'P':
                    if v2 != prev:
                        who['%x' % pc2] += 1
                    prev = v2
                elif pc2 == 0x14fdc:
                    fate = 'kept' if v2 == 0x3c else 'rewrit'
                    arr_modes['%02x' % v2] += 1
                    break
            cls[fate] += 1
    print(f, dict(cls), 'arrival modes', dict(arr_modes), 'prev rewriters', dict(who))

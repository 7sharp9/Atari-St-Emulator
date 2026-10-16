#!/usr/bin/env python3
"""chase_fate.py <watch> [lead_addr]: every $5350 pick that aims a man at the lead (word 48 := lead offset), and what
ends that chase first. Input: WATCH lines over the object array, filtered with wfilter.py 46-49.
  engaged   the lead's word 48 := this man's offset at $5716 ($56a6 stamping the lead from this man)
  diverted  this man's word 48 rewritten by another engagement ($5716: someone engaged him; $138e: struck back)
  repick    this man's word 48 rewritten by his own next pick ($5350)
  dead      his side byte 5 negated (written <= 0)
  open      none of these by the end of the trace"""
import re, sys
from collections import Counter

O = 0x51b66
lead = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x52fe8
LO = lead - O
R = re.compile(r'step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)')
ev = []
for l in open(sys.argv[1]):
    m = R.search(l)
    if m:
        ev.append((int(m.group(1)), int(m.group(2), 16), m.group(3), int(m.group(4), 16), int(m.group(5), 16)))
chases = [(s, (a - 48 - O)) for s, pc, k, a, v in ev if pc == 0x5350 and v == LO and (a - O) % 50 == 48]
fates = Counter()
for s0, me in chases:
    if me == LO:
        continue
    fate, at, by = 'open', None, None
    for s, pc, k, a, v in ev:
        if s <= s0:
            continue
        off = a - O
        if off == LO + 48 and pc == 0x5716 and v == me:
            fate, at = 'engaged', s; break
        if off == me + 48:
            fate, at, by = ('repick' if pc == 0x5350 else 'diverted'), s, '$%x->%04x' % (pc, v); break
        if off == me + 5 and k == 'Byte' and (v == 0 or v >= 0x80):
            fate, at = 'dead', s; break
    fates[fate] += 1
    print('$%05x picks lead at %d: %s%s' % (O + me, s0, fate, '' if at is None else ' after %d steps %s' % (at - s0, by or '')))
print(dict(fates), 'lead self-picks skipped')

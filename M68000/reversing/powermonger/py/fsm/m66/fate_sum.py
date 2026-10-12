#!/usr/bin/env python3
"""fate_sum.py <watch>...: one line per run. For the records $5106 stamped prev $66: how many were water-vetoed ($161f0) while
the prev was still $66, how many went afloat ($14c9a) or to $0a ($14caa), the steps from the first stamp to the first camp
rewrite ($36f2 member prev $20 or $371a lead $6868) and to the first veto, and every $14fdc arrival with its value while the
prev was $66. The lead is the record whose word 30 $371a writes."""
import sys, re
for fn in sys.argv[1:]:
    st = {}; prev66 = set(); veto = set(); afl = set(); to0a = set(); first = None; camp = None; fveto = None; arr = []; lead = set()
    for l in open(fn):
        m = re.search(r'step=(\d+) pc=\$(\w+) Write(\w+) \$(\w+) <- \$(\w+)', l)
        if not m: continue
        s, pc, wd, a, v = m.groups(); s = int(s); a = int(a, 16); r, off = divmod(a - 0x51b66, 50)
        if pc == '005106': prev66.add(r); first = first or s; continue
        if pc in ('0036f2', '00371a'):
            if r in prev66: prev66.discard(r); camp = camp or s
            if pc == '00371a': lead.add(r)
            continue
        if r not in prev66: continue
        if pc == '0161f0': veto.add(r); fveto = fveto or s
        if pc == '014c9a': afl.add(r)
        if pc == '014caa': to0a.add(r)
        if pc == '014fdc': arr.append((s - first, r, v))
    rel = lambda x: x - first if (x and first) else None
    print(f'{fn}: stamp@{first} vetoed={len(veto)} afloat={len(afl)} to0a={len(to0a)} lead={sorted(lead)} lead_vetoed={bool(lead & veto)} '
          f'first_veto=+{rel(fveto)} camp=+{rel(camp)} arrivals_with_prev66={arr[:8]}')

"""service_calls.py [overlay_levelN.lst ...]: for each listing written by overlay_map.py, find the export-table trampoline
(`movea.l 392(A5),A6 / movea.l 0(A6,D6.w),A6 / jmp (A6)`) and list every call site `moveq #<4n>,D6 ... bsr/bra <tramp>`
(D6 set within the previous 3 instructions) as service n.  Prints, per level, {service n: [call-site offsets]} and the
call sites that set D6 by other means.  Expected (level 0): services 0,2,3,6,7,10,12,14,15,16,17,18; level 1 see output."""
import sys, re, collections
paths = sys.argv[1:] or ['scratchpad/cadaver/secrets_out/overlay/overlay_level0.lst', 'scratchpad/cadaver/secrets_out/overlay/overlay_level1.lst']
for p in paths:
    L = [l.rstrip('\n') for l in open(p)]
    rows = []
    for l in L:
        m = re.match(r'\s+\$([0-9a-f]+) \(\+([0-9a-f]+)\): (.*)', l)
        if m: rows.append((int(m.group(1), 16), int(m.group(2), 16), m.group(3)))
    tramp = None
    for i, (a, o, t) in enumerate(rows):
        if t.startswith('movea.l 392(A5),A6'): tramp = a
    calls = collections.defaultdict(list); odd = []
    for i, (a, o, t) in enumerate(rows):
        m = re.match(r'(bsr|bra|jsr) \$([0-9a-f]+)', t)
        if m and int(m.group(2), 16) == tramp:
            d6 = None
            for j in range(i - 1, max(i - 4, -1), -1):
                mm = re.match(r'moveq #(-?\d+),D6', rows[j][2])
                if mm: d6 = int(mm.group(1)); break
            if d6 is None: odd.append('+%x' % o)
            else: calls[d6 // 4].append('+%x' % o)
    print(p, 'trampoline $%06x' % tramp)
    for n in sorted(calls): print('  service', n, 'D6=%d' % (4 * n), calls[n])
    print('  D6 not set by a moveq within 3 instrs:', odd)

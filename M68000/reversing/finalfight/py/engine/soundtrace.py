#!/usr/bin/env python3
"""soundtrace.py <z80tap.txt> : per 68000 sound command (latch $800180 writes other than the idle $ff), the Z80 activity until the next command: YM2151 writes (count, key-on events
register $08: channel and operator mask), OKI6295 writes (phrase starts: first byte bit 7 = phrase number, second byte = channel mask and attenuation), latch reads.
Prints one block per command (frame, id) and a summary per id."""
import re, sys, collections
ev = []
for l in open(sys.argv[1]):
    m = re.match(r'f=(\d+) (Z|M) (\S+) (.*)', l)
    if not m: continue
    f = int(m.group(1)); t = m.group(2)
    ev.append((f, t, m.group(3), m.group(4)))
cmds = [(f, int(re.search(r'd=([0-9a-f]+)', rest).group(1), 16) & 0xff) for f, t, k, rest in ev if t == 'M' and k == 'w' and 'a=800180' in rest]
cmds = [(f, d) for f, d in cmds if d != 0xff]
# add the frame of the next command as the end of each window
summ = collections.defaultdict(lambda: collections.Counter())
byid = collections.defaultdict(list)
for i, (f, d) in enumerate(cmds):
    end = cmds[i + 1][0] if i + 1 < len(cmds) else f + 60
    end = min(end, f + 120)
    ym = collections.Counter(); keyon = []; oki = []; nym = 0; reads = collections.Counter()
    for (ff, t, k, rest) in ev:
        if ff < f or ff >= end or t != 'Z': continue
        if k == 'ym':
            a = int(re.search(r'a=([0-9a-f]+)', rest).group(1), 16); dd = int(re.search(r' d=([0-9a-f]+)', rest).group(1), 16)
            nym += 1
            if a == 0xf001: ym[('data', dd)] += 0
        elif k == 'w':
            a = int(re.search(r'a=([0-9a-f]+)', rest).group(1), 16); dd = int(re.search(r' d=([0-9a-f]+)', rest).group(1), 16)
            if a == 0xf002: oki.append(dd)
    byid[d].append((f, nym, oki[:6]))
print('commands:', len(cmds))
for d in sorted(byid):
    for f, nym, oki in byid[d][:3]:
        print('id %02x frame %5d  ym writes %4d  oki bytes %s' % (d, f, nym, ' '.join('%02x' % x for x in oki)))

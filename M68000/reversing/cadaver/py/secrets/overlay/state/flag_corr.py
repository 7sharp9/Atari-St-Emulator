"""flag_corr.py: static correlation of the record flag bits with what the record carries, over every non-static record (+15 bit 7 clear) of a snapshot:
+3 bit 5 <-> an event-16 (examine) block;  +3 bit 6 <-> an event-9 block;  +3 bit 4 <-> a mover block of >= 14 bytes (rec[14]-rec[13]);  +3 bit 7 and bits 0-3 (never set in data?).
Also +15 bit 0 (set in data) <-> template +12 bit 2 and the anim byte ($fe/$ff/0).   usage: flag_corr.py SNAP..."""
import sys, collections
from st import St
for snap in sys.argv[1:]:
    s = St(snap); C = collections.defaultdict(collections.Counter); n = 0
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        r = s.mem(a, s.size(6, i))
        if r[15] & 0x80: continue
        t = (r[6] << 8) | r[7]; tm = s.mem(s.tmpl(t), 32)
        evs = set(); p = 0x10
        for _ in range(r[11]): evs.add(r[p + 1] & 0x7f); p += r[p]
        n += 1
        C['bit5 vs event16'][(bool(r[3] & 0x20), 16 in evs)] += 1
        C['bit6 vs event9'][(bool(r[3] & 0x40), 9 in evs)] += 1
        C['bit4 vs mover block'][(bool(r[3] & 0x10), r[14] - r[13] >= 14)] += 1
        C['bit7 hidden'][bool(r[3] & 0x80)] += 1
        C['+3 low nibble'][r[3] & 0x0f] += 1
        if tm[12] & 4 and r[14] + 10 <= len(r): C['+15 bit0 vs anim byte'][(bool(r[15] & 1), r[r[14]])] += 1
    print(snap, 'records', n)
    for k, v in C.items(): print('   %-24s (flag, other) -> count: %s' % (k, dict(v)))

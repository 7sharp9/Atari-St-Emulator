"""data_strings.py - every NUL-terminated string in the DATA segment ($1bfd0..$1c4f2) with its A4 offset and the
instructions in ss.asm that take its address (pea/lea/move off(A4)) or a covering range."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reach, sscfg
raw = open(sscfg.IMG, 'rb').read()
A4 = sscfg.A4
lo, hi = 0x1bfd0, 0x1c4f2
ins = reach.load()
byoff = {}
for a, t in ins:
    for m in re.finditer(r'(-?\d+)\(A4\)', t):
        byoff.setdefault(int(m.group(1)), []).append((a, t))
i = lo
out = []
while i < hi:
    j = i
    while j < hi and raw[j - 0xa304] != 0:
        j += 1
    s = raw[i - 0xa304:j - 0xa304]
    if len(s) >= 2 and all(32 <= c < 127 or c == 10 for c in s):
        off = i - lo
        users = []
        for o in range(off, off + len(s) + 1):
            users += [(o, a, t) for a, t in byoff.get(o, [])]
        out.append((i, off, s.decode(), users))
    i = j + 1
for i, off, s, users in out:
    print('%06x %6d %-46r %s' % (i, off, s[:46], ' | '.join('%x:%s(+%d)' % (a, t, o - off) for o, a, t in users[:5])))

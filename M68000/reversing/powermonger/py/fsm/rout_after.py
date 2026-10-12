#!/usr/bin/env python3
"""rout_after.py <tag.after> [<watch> <out>]: who still targets a routed man 200 steps after his stamp.
<tag.after>: rout_caller.sh's stops at every $561c stamp (A3 = the routed man) each followed by `s 200` and a dump of
the record array ($51b66, 512 records of 50 bytes). For each stamp lists the live records (byte 5 > 0) whose word 48
(the link target) is the man's offset, with their mode byte 31. With routrun.sh's <watch>/<out> of the same span, each
stamp is labelled with its fate as in rout_caller.py (re-routed: a second stamp with no $14fdc arrival between; arrival
with prev reset: he reached another mode; arrival with prev $3c), and the counts of stamps with and without a
melee ($32) or chasing ($2e) man still on him are printed per fate."""
import re, sys, collections
after = sys.argv[1]
st = []; cur = None
for l in open(after):
    m = re.match(r'A0:\S+ A1:(\S+) A2:\S+ A3:(\S+)', l.strip())
    if m: cur = {'a3': int(m.group(2), 16)}; continue
    t = l.split()
    if cur is not None and len(t) == 25600 and all(len(x) == 2 for x in t[:4]):
        cur['ram'] = bytes(int(x, 16) for x in t); st.append(cur); cur = None
def on(s):
    off = s['a3'] - 0x51b66; ram = s['ram']; r = []
    for k in range(512):
        b = ram[50 * k:50 * k + 50]
        if 50 * k == off or b[5] == 0 or b[5] >= 0x80: continue
        if int.from_bytes(b[48:50], 'big') == off: r.append((0x51b66 + 50 * k, b[31]))
    return r
fate = {}
if len(sys.argv) > 3:
    R = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) Write(Byte|Word|Long) \$([0-9a-f]{8})')
    SZ = {'Byte': 1, 'Word': 2, 'Long': 4}; ev = collections.defaultdict(list)
    for l in open(sys.argv[2]):
        m = R.search(l)
        if not m: continue
        s0, pc, sz, a = int(m.group(1)), int(m.group(2), 16), SZ[m.group(3)], int(m.group(4), 16)
        for i in range(sz):
            off = (a + i - 0x51b66) % 50
            if (off == 30 and pc in (0x561c,)) or (off == 31 and pc == 0x14fdc) or (off == 30 and pc not in (0x561c, 0x5708)):
                ev[a + i - off].append((s0, pc))
    order = sorted((s0, rec) for rec, es in ev.items() for s0, pc in es if pc == 0x561c)
    for s0, rec in order:
        es = ev[rec]; nxt = [x for x, pc in es if pc == 0x561c and x > s0]; s1 = nxt[0] if nxt else None
        arr = [x for x, pc in es if pc == 0x14fdc and x > s0 and (s1 is None or x < s1)]
        reset = any(pc not in (0x561c, 0x14fdc) and x > s0 and (not arr or x < arr[0]) for x, pc in es)
        fate[len(fate)] = 're-routed' if s1 and not arr else ('arrival, prev reset' if arr and reset else ('arrival, prev $3c' if arr else 'run end'))
print(f'{after}: {len(st)} stamps dumped')
grid = collections.Counter()
for i, s in enumerate(st):
    r = on(s); modes = sorted(set(m for _, m in r))
    has = 'melee/chase on him' if any(m in (0x32, 0x2e) for _, m in r) else 'none on him'
    f = fate.get(i, '?'); grid[(f, has)] += 1
    if f != 'arrival, prev $3c':
        print(f"  #{i:3d} ${s['a3']:x} {f:20s} on him: " + (' '.join(f'${a:x}:{m:02x}' for a, m in r) or '-'))
for k, n in sorted(grid.items()): print('  ', k, n)

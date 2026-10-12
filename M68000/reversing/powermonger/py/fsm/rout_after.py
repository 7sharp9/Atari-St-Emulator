#!/usr/bin/env python3
"""rout_after.py <tag.after>[,<tag.fill>] [<watch> <out>]: who still targets a routed man 200 steps after his stamp.
<tag.after>: rout_caller.sh's stops at every $561c stamp (A3 = the routed man) each followed by `s 200` and a dump of
the record array ($51b66, 512 records of 50 bytes). For each stamp lists the live records (byte 5 > 0) whose word 48
(the link target) is the man's offset, with their mode byte 31. With routrun.sh's <watch>/<out> of the same span, each
stamp is labelled with its fate as in rout_caller.py (re-routed: a second stamp with no $14fdc arrival between; arrival
with prev reset: he reached another mode; arrival with prev $3c), and the counts of stamps with and without a
melee ($32) or chasing ($2e) man still on him are printed per fate. A dump is paired with its stamp by step (the
cumulative `after N steps` of the stops, origin from <out>'s $561c `first` count), not by position: the `s 200` after
each stop skips a stamp that lands within 200 steps of the previous one, and such stamps are listed as undumped.
Stops past the end of the <out> run's span (the last `bp` budget runs on) are dropped."""
import re, sys, collections
after = sys.argv[1]
st = []; cur = None
for l in (l for f in after.split(',') for l in [None] + list(open(f))):
    if l is None: t0 = 0; continue        # t0: cumulative step from the start snapshot of each $561c stop, per file
    m = re.search(r'breakpoint \$0000561c hit .* after (\d+) step', l)
    if m: t0 += int(m.group(1)); cur = {'step': t0}; t0 += 200; continue
    m = re.match(r'A0:\S+ A1:(\S+) A2:\S+ A3:(\S+)', l.strip())
    if m and cur is not None: cur['a3'] = int(m.group(2), 16); continue
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
    first = int(re.search(r'\$00561c\s+\d+\s+first (\d+)', open(sys.argv[3]).read()).group(1))
    order = sorted((s0, rec) for rec, es in ev.items() for s0, pc in es if pc == 0x561c)
    origin = order[0][0] - first
    for s0, rec in order:
        es = ev[rec]; nxt = [x for x, pc in es if pc == 0x561c and x > s0]; s1 = nxt[0] if nxt else None
        arr = [x for x, pc in es if pc == 0x14fdc and x > s0 and (s1 is None or x < s1)]
        reset = any(pc not in (0x561c, 0x14fdc) and x > s0 and (not arr or x < arr[0]) for x, pc in es)
        fate[s0 - origin] = (rec, 're-routed' if s1 and not arr else ('arrival, prev reset' if arr and reset else ('arrival, prev $3c' if arr else 'run end')))
print(f'{after}: {len(st)} stamps dumped')
grid = collections.Counter()
if fate:
    byst = {x['step']: x for x in st}
    for k, (rec, f) in fate.items():
        if k not in byst: print(f'  undumped stamp at {k} on ${rec:x}: {f}')
        elif byst[k]['a3'] != rec: sys.exit(f'dump at {k} has A3 ${byst[k]["a3"]:x}, the stamp is on ${rec:x}')
    st = [x for x in st if x['step'] in fate]
for i, s in enumerate(st):
    r = on(s); modes = sorted(set(m for _, m in r))
    has = 'melee/chase on him' if any(m in (0x32, 0x2e) for _, m in r) else 'none on him'
    f = fate[s['step']][1] if fate else '?'; grid[(f, has)] += 1
    if f != 'arrival, prev $3c':
        print(f"  #{i:3d} ${s['a3']:x} {f:20s} on him: " + (' '.join(f'${a:x}:{m:02x}' for a, m in r) or '-'))
for k, n in sorted(grid.items()): print('  ', k, n)

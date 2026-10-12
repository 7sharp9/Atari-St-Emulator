#!/usr/bin/env python3
"""rout_target.py <watch> <out> <tag.calls> <tag.after>: who points the re-engager's word 48 at a re-routed man.
<watch>/<out>: routrun.sh's run with the extra filter `46-49` (record offsets 0..7, 28..31 and the link target word
48) and its hits line (the step origin); <tag.calls>/<tag.after>: rout_caller.sh's $56a6 stops and its dumps 200
steps after every $561c stamp over the same snapshot and span.
For each re-routed stamp (a second $561c stamp on the man with no $14fdc arrival between, rout_fate.py's class) it
takes the first $5708 re-engage of the man, the re-engager A1 of the $56a6 call before it ($15368 and $15332 read A3
from 48(A1)), the pc and step of the last write of A1's word 48 := the man, and A1's mode writes (byte 31) from the
stamp to the re-engage. Stamps are split as in rout_after.py: with or without a
$32/$2e man on him in the +200 dump (or no dump). Prints one line per stamp and the writer-pc counts per group."""
import re, sys, collections
watch, out, calls, after = sys.argv[1:5]
B = 0x51b66
R = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) Write(Byte|Word|Long) \$([0-9a-f]{8}) <- \$([0-9a-f]+)')
SZ = {'Byte': 1, 'Word': 2, 'Long': 4}
b30 = collections.defaultdict(list)    # rec -> [(step, pc)] byte 30 writes and $14fdc arrivals
w48 = []                               # (step, pc, rec, value) word 48 writes
m31 = collections.defaultdict(list)    # rec -> [(step, pc, mode)]
for l in open(watch):
    m = R.search(l)
    if not m: continue
    st, pc, sz, a, v = int(m.group(1)), int(m.group(2), 16), SZ[m.group(3)], int(m.group(4), 16), int(m.group(5), 16)
    vb = v.to_bytes(sz, 'big')
    for i in range(sz):
        b = a + i; off = (b - B) % 50; rec = b - off
        if off == 30 or (off == 31 and pc == 0x14fdc): b30[rec].append((st, pc))
        if off == 31: m31[rec].append((st, pc, vb[i]))
    off = (a - B) % 50
    if off == 48 and sz >= 2: w48.append((st, pc, a - off, int.from_bytes(vb[:2], 'big')))
    elif off == 46 and sz == 4: w48.append((st, pc, a - off, int.from_bytes(vb[2:4], 'big')))
first_rel = None
for l in open(out):
    m = re.search(r'\$00561c\s+(\d+)\s+first (\d+)', l)
    if m: first_rel = int(m.group(2))
def stops(path):                       # cumulative relative step, A1, A3, return address of every bp stop
    cs = []; t = 0; cur = None
    for l in open(path):
        m = re.search(r'breakpoint \$0000[0-9a-f]{4} hit .* after (\d+) step', l)
        if m: t += int(m.group(1)); cur = {'step': t}; continue
        m = re.match(r'A0:\S+ A1:(\S+) A2:\S+ A3:(\S+)', l.strip())
        if m and cur is not None: cur['a1'], cur['a3'] = int(m.group(1), 16), int(m.group(2), 16); continue
        m = re.search(r'return address \(A7\) = \$([0-9a-f]+)', l)
        if m and cur is not None: cur['ret'] = int(m.group(1), 16); cs.append(cur); cur = None; t += 1
    return cs
cs = stops(calls)
# +200 dumps (rout_after.py's parse: paired with their stamp by step; `<tag.after>,<tag.fill>` adds the fill dumps)
dumps = {}; cur = None
for l in (l for f in after.split(',') for l in [None] + list(open(f))):
    if l is None: t0 = 0; continue
    m = re.search(r'breakpoint \$0000561c hit .* after (\d+) step', l)
    if m: t0 += int(m.group(1)); cur = t0; t0 += 200; continue
    t = l.split()
    if cur is not None and len(t) == 25600 and all(len(x) == 2 for x in t[:4]):
        dumps[cur] = bytes(int(x, 16) for x in t); cur = None
def on_him(man, ram):
    off = man - B
    return [ram[50 * k + 31] for k in range(512) if 50 * k != off and 0 < ram[50 * k + 5] < 0x80
            and int.from_bytes(ram[50 * k + 48:50 * k + 50], 'big') == off]
stamps = sorted((st, rec) for rec, es in b30.items() for st, pc in es if pc == 0x561c)
origin = stamps[0][0] - first_rel
grp = collections.defaultdict(collections.Counter); rows = 0
for s0, man in stamps:
    ram = dumps.get(s0 - origin)
    es = b30[man]
    nxt = [x for x, pc in es if pc == 0x561c and x > s0]
    if not nxt or any(pc == 0x14fdc and s0 < x < nxt[0] for x, pc in es): continue
    re_eng = [x for x, pc in es if pc == 0x5708 and s0 < x < nxt[0]]
    if not re_eng: continue
    r = re_eng[0]
    c = [c for c in cs if c['a3'] == man and c['step'] <= r - origin]
    if not c: continue
    att = c[-1]['a1']; via = {0x1536e: '$15368', 0x15338: '$15332'}.get(c[-1]['ret'], hex(c[-1]['ret']))
    tw = [w for w in w48 if w[2] == att and w[0] < r]
    if not tw or tw[-1][3] != man - B: print(f'  man ${man:x}: re-engager ${att:x} word 48 not him'); continue
    st, pc, _, _ = tw[-1]
    on = on_him(man, ram) if ram else None
    kind = 'no dump' if on is None else 'melee/chase on him' if any(x in (0x32, 0x2e) for x in on) else 'none on him'
    modes = [md for x, p, md in m31[att] if s0 - 2000 <= x <= r]
    pre = [md for x, p, md in m31[att] if x <= st]
    grp[kind][(f'${pc:x}', 'before stamp' if st < s0 else 'after stamp')] += 1; rows += 1
    print(f'{kind:18s} man ${man:x} stamp {s0} re-engage +{r - s0} by ${att:x} via {via}: word 48 := him at ${pc:x}, '
          f'{"+" if st >= s0 else ""}{st - s0} from the stamp, mode then ${pre[-1] if pre else 0:02x}; '
          f'modes stamp-2000..re-engage: {" ".join(f"{x:02x}" for x in modes[-12:])}')
print(f'{rows} re-routed stamps')
for k, c in grp.items(): print(f'  {k}: ' + ', '.join(f'{p} {n}' for p, n in c.most_common()))

#!/usr/bin/env python3
"""rout_caller.py <watch> <out> <calls>: attribute every $5708 re-engage of a re-routed man to its $56a6 caller.
<watch>/<out>: routrun.sh's run (record bytes 0..7, 28..31 and the hits line that fixes the step origin);
<calls>: rout_caller.sh's bp/bt stops over the same snapshot and span (A3 = engaged man, (A7) = return address).
A re-routed stamp is a $561c stamp (byte 30 := $3c) followed by a second $561c stamp on the same man with no $14fdc
arrival (byte 31) between them (rout_fate.py's re-routed class); every $5708
write to his byte 30 between the two is joined to the latest $56a6 call with A3 = that man at or before it.
Prints the caller counts for the re-engages of re-routed men, and over all $5708 writes as a control."""
import re, sys, collections
watch, out, calls = sys.argv[1:4]
R = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) Write(Byte|Word|Long) \$([0-9a-f]{8}) <- \$([0-9a-f]+)')
SZ = {'Byte': 1, 'Word': 2, 'Long': 4}
first_rel = None
for l in open(out):
    m = re.search(r'\$00561c\s+(\d+)\s+first (\d+)', l)
    if m: first_rel = int(m.group(2))
ev = collections.defaultdict(list)                     # rec -> [(abs step, pc)]: byte 30 writes, $14fdc arrivals
for l in open(watch):
    m = R.search(l)
    if not m: continue
    st, pc, sz, a = int(m.group(1)), int(m.group(2), 16), SZ[m.group(3)], int(m.group(4), 16)
    for i in range(sz):
        b = a + i; off = (b - 0x51b66) % 50
        if off == 30 or (off == 31 and pc == 0x14fdc): ev[b - off].append((st, pc))
stamps = sorted(st for es in ev.values() for st, pc in es if pc == 0x561c)
origin = stamps[0] - first_rel
# the bp/bt stops: cumulative relative step of each $56a6 entry
cs = []; t = 0; cur = None
for l in open(calls):
    m = re.search(r'breakpoint \$000056a6 hit .* after (\d+) step', l)
    if m: t += int(m.group(1)); cur = {'step': t}; continue
    m = re.match(r'A0:\S+ A1:(\S+) A2:\S+ A3:(\S+)', l.strip())
    if m and cur is not None: cur['a1'], cur['a3'] = int(m.group(1), 16), int(m.group(2), 16); continue
    m = re.search(r'return address \(A7\) = \$([0-9a-f]+)', l)
    if m and cur is not None: cur['ret'] = int(m.group(1), 16); cs.append(cur); cur = None; t += 1
CALLER = {0x15338: '$15332 ($2e arrival)', 0x1536e: '$15368 (melee)'}
byrec = collections.defaultdict(list)
for c in cs: byrec[c['a3']].append(c)
def caller(rec, rel):
    prior = [c for c in byrec[rec] if c['step'] <= rel]
    return (CALLER.get(prior[-1]['ret'], f"${prior[-1]['ret']:x}"), rel - prior[-1]['step']) if prior else ('no call', None)
allw = collections.Counter(); rer = collections.Counter(); lags = []; rows = []
for rec, es in ev.items():
    for st, pc in es:
        if pc == 0x5708: allw[caller(rec, st - origin)[0]] += 1
    st_stamps = [st for st, pc in es if pc == 0x561c]
    for s0, s1 in zip(st_stamps, st_stamps[1:]):
        if any(pc == 0x14fdc and s0 < st < s1 for st, pc in es): continue   # arrived first: not a re-route
        eng = [st for st, pc in es if pc == 0x5708 and s0 < st < s1]
        for st in eng:
            who, lag = caller(rec, st - origin); rer[who] += 1; lags.append(lag); rows.append((rec, s0 - origin, st - origin, who))
print(f'{calls}: {len(cs)} $56a6 stops; $5708 writes to byte 30: {sum(allw.values())}')
print('  all $5708 writes by caller:', dict(allw))
print(f'  re-routed men, $5708 between two stamps: {sum(rer.values())} on {len(set(r[0] for r in rows))} men; by caller:', dict(rer))
if lags and None not in lags: print(f'  steps from $56a6 entry to $5708: {min(lags)}..{max(lags)}')
for rec, s0, w, who in sorted(rows, key=lambda r: r[2]): print(f'    ${rec:x} stamp {s0} engage {w} {who}')

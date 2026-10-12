#!/usr/bin/env python3
"""rout_caller.py <watch> <out> <calls> [<rout>]: attribute every $5708 re-engage of a re-routed man to its $56a6 caller.
<watch>/<out>: routrun.sh's run (record bytes 0..7, 28..31 and the hits line that fixes the step origin);
<calls>: rout_caller.sh's bp/bt stops over the same snapshot and span (A3 = engaged man, (A7) = return address).
A re-routed stamp is a $561c stamp (byte 30 := $3c) followed by a second $561c stamp on the same man with no $14fdc
arrival (byte 31) between them (rout_fate.py's re-routed class); every $5708
write to his byte 30 between the two is joined to the latest $56a6 call with A3 = that man at or before it.
Prints the caller counts for the re-engages of re-routed men, and over all $5708 writes as a control.
With <rout> (the $5590 stops): every stamp is joined to the latest $5590 call with A3 = that man, giving the routing
blow's source (melee $1539c or arrow $5b58) and its striker (A1); prints each stamp's fate by source, and whether the
man who re-engages a re-routed man is his striker."""
import re, sys, collections
watch, out, calls = sys.argv[1:4]
rout = sys.argv[4] if len(sys.argv) > 4 else None
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
def stops(path):
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
CALLER = {0x15338: '$15332 ($2e arrival)', 0x1536e: '$15368 (melee)'}
byrec = collections.defaultdict(list)
for c in cs: byrec[c['a3']].append(c)
def last_call(by, rec, rel):
    prior = [c for c in by[rec] if c['step'] <= rel]
    return prior[-1] if prior else None
def caller(rec, rel):
    c = last_call(byrec, rec, rel)
    return (CALLER.get(c['ret'], f"${c['ret']:x}"), rel - c['step']) if c else ('no call', None)
allw = collections.Counter(); rer = collections.Counter(); lags = []; rows = []; reeng = {}
for rec, es in ev.items():
    for st, pc in es:
        if pc == 0x5708: allw[caller(rec, st - origin)[0]] += 1
    st_stamps = [st for st, pc in es if pc == 0x561c]
    for s0, s1 in zip(st_stamps, st_stamps[1:]):
        if any(pc == 0x14fdc and s0 < st < s1 for st, pc in es): continue   # arrived first: not a re-route
        eng = [st for st, pc in es if pc == 0x5708 and s0 < st < s1]
        for st in eng:
            who, lag = caller(rec, st - origin); rer[who] += 1; lags.append(lag); rows.append((rec, s0 - origin, st - origin, who))
            reeng[(rec, s0)] = last_call(byrec, rec, st - origin)
print(f'{calls}: {len(cs)} $56a6 stops; $5708 writes to byte 30: {sum(allw.values())}')
print('  all $5708 writes by caller:', dict(allw))
print(f'  re-routed men, $5708 between two stamps: {sum(rer.values())} on {len(set(r[0] for r in rows))} men; by caller:', dict(rer))
if lags and None not in lags: print(f'  steps from $56a6 entry to $5708: {min(lags)}..{max(lags)}')
for rec, s0, w, who in sorted(rows, key=lambda r: r[2]): print(f'    ${rec:x} stamp {s0} engage {w} {who}')
if rout:
    SRC = {0x153a2: 'melee $1539c', 0x5b5e: 'arrow $5b58', 0x5a5e: '$5a5a'}
    rs = stops(rout); byvic = collections.defaultdict(list)
    for c in rs: byvic[c['a3']].append(c)
    grid = collections.Counter(); same = collections.Counter(); odd = []
    for rec, es in ev.items():
        st_stamps = [st for st, pc in es if pc == 0x561c]
        for k, s0 in enumerate(st_stamps):
            s1 = st_stamps[k + 1] if k + 1 < len(st_stamps) else None
            arr = [(st, pc) for st, pc in es if pc == 0x14fdc and st > s0 and (s1 is None or st < s1)]
            fate = 're-routed' if s1 is not None and not arr else ('arrival' if arr else 'run end')
            reset = any(pc not in (0x561c, 0x5708, 0x14fdc) and s0 < st and (not arr or st < arr[0][0]) for st, pc in es)
            b = last_call(byvic, rec, s0 - origin)
            src = SRC.get(b['ret'], f"${b['ret']:x}") if b else 'no $5590'
            grid[(src, fate, 'prev reset' if reset else 'prev $3c')] += 1
            if fate == 're-routed' and (rec, s0) in reeng and b:
                same['re-engager is the striker' if reeng[(rec, s0)]['a1'] == b['a1'] else 're-engager is another man'] += 1
            if fate == 'arrival' and reset: odd.append((rec, s0 - origin, src, b['a1'] if b else None))
    print(f'{rout}: {len(rs)} $5590 stops; stamps by blow source, fate and prev:')
    for k, n in sorted(grid.items()): print('  ', k, n)
    print('  re-routed:', dict(same))
    for rec, s0, src, a1 in odd: print(f'    escaped: ${rec:x} stamp {s0} {src} striker {a1 and hex(a1)}')

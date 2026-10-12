#!/usr/bin/env python3
"""rout_fate.py <watch> <out>: Input: WATCH lines of `watch 51b66 25600`
kept for record offsets 0..7 and 28..31 (routrun.sh), and the run's .out (its `hits` line for $561c gives the step origin).
For every ROUT stamp (pc $561c, byte 30 := $3c) follow the record until its next stamp or the run end:
  kept / rewrit  - the $14fdc arrival writes mode $3c (prev still $3c) / another mode (prev rewritten first), as the first version;
  no arrival     - classified by what happened first after the stamp:
     engaged     - $5708 (in $56a6: mode/prev := $32, 48 := attacker) set prev $32 before any arrival;
     died/freed  - byte 5 went <= 0 first;
     other       - another pc rewrote byte 30 first;
     run end     - nothing wrote byte 30 and byte 5 stayed > 0 until the end of the run.
For each no-arrival stamp prints: record, stamp step, first rewriter, then the window's last writer of 30/31 and its value,
steps from stamp to run end, and the record's end state (re-routed, died, alive in mode M)."""
import re, sys, collections
R = re.compile(r'step=(\d+) pc=\$([0-9a-f]+) Write(Byte|Word|Long) \$([0-9a-f]{8}) <- \$([0-9a-f]+)')
SZ = {'Byte': 1, 'Word': 2, 'Long': 4}
watch, out = sys.argv[1], sys.argv[2]
first_rel = steps = None
for l in open(out):
    m = re.search(r'hits over (\d+) step', l)
    if m: steps = int(m.group(1))
    m = re.search(r'\$00561c\s+(\d+)\s+first (\d+)', l)
    if m: nhits, first_rel = int(m.group(1)), int(m.group(2))
ev = collections.defaultdict(list)       # rec -> [(step, pc, off, value)]
for l in open(watch):
    m = R.search(l)
    if not m: continue
    st, pc, sz, a, v = int(m.group(1)), int(m.group(2), 16), SZ[m.group(3)], int(m.group(4), 16), int(m.group(5), 16)
    for i in range(sz):
        b = a + i; off = (b - 0x51b66) % 50; rec = b - off
        ev[rec].append((st, pc, off, (v >> (8 * (sz - 1 - i))) & 0xff))
stamps = sorted((e[0], rec) for rec, es in ev.items() for e in es if e[1] == 0x561c and e[2] == 30)
origin = stamps[0][0] - first_rel; end = origin + steps
print(f'{watch}: {len(stamps)} stamps (hits $561c {nhits}), run end step {end}')
fates_of = collections.defaultdict(list); cls = collections.Counter(); grid = collections.Counter(); rows = []
for st0, rec in stamps:
    es = [e for e in ev[rec] if e[0] > st0 or (e[0] == st0 and e[1] != 0x561c)]
    prev = 0x3c; reset = None; engaged = None; died = None; last = None; outcome = None; arr = None
    for st, pc, off, v in es:
        if pc == 0x561c and off == 30:
            outcome = ('re-routed', st - st0); break
        if off == 5 and (v == 0 or v >= 0x80) and died is None:
            died = (st - st0, pc, v); outcome = ('died/freed', st - st0); break
        if off == 30:
            if pc == 0x5708 and engaged is None: engaged = st - st0
            if v != prev and reset is None and pc != 0x5708: reset = (pc, v, st - st0)
            prev = v
        if off in (30, 31): last = (st, pc, off, v)
        if off == 31 and pc == 0x14fdc:
            arr = v; outcome = ('arrival', st - st0); break
    if outcome is None: outcome = ('run end', end - st0)
    grp = 'prev reset' if reset else 'prev $3c'
    fate = ('arrival $3c' if arr == 0x3c else 'arrival other') if outcome[0] == 'arrival' else outcome[0]
    fates_of[rec].append((grp, fate)); cls[fate] += 1; grid[(grp, fate, 'engaged' if engaged is not None else '-')] += 1
    if outcome[0] != 'arrival':
        rows.append((rec, st0, grp, reset, engaged, fate, outcome[1], last, end - st0))
print(dict(cls))
for k, n in sorted(grid.items()): print('  ', k, n)
for rec, st0, grp, reset, engaged, fate, dt, last, left in rows:
    rs = f'reset {reset[0]:x}={reset[1]:02x} +{reset[2]}' if reset else 'no reset'
    en = f'5708 +{engaged}' if engaged is not None else 'no 5708'
    lw = f'last {last[1]:x}:{last[2]}={last[3]:02x}' if last else 'last -'
    print(f'  rec ${rec:x} @{st0} {rs:22s} {en:13s} {fate:10s} +{dt:<9d} {lw:16s} to-end {left}')
# per record: the sequence of stamp outcomes, so a re-routed group member's last stamp can be matched to its arrival
seq = collections.defaultdict(list)
for st0, rec in stamps: seq[rec].append(st0)
multi = {r: v for r, v in seq.items() if len(v) > 1}
print(f'records stamped: {len(seq)}, stamped more than once: {len(multi)} ({sum(len(v) for v in multi.values())} stamps)')
pat = collections.Counter(' -> '.join(f'{g}/{f}' for g, f in v) for v in fates_of.values())
print('per-record stamp sequences:')
for k, n in pat.most_common(): print(f'  {n:3d}  {k}')

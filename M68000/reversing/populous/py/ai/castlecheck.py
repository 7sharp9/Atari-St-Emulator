"""castlecheck.py LOGDIR - the computer castle release at $e5a6..$e638 in a natural run:
every WATCH write busy<-1 from pc $e638 must fall on a frame with frame%8 == 0, and the side's
busy must have been 0 just before (last earlier write to +8 in that frame). Also lists every pc
that wrote a ctrl word (+6)."""
import bisect, collections, json, os, re, sys
from join import dedup, WRE
d = sys.argv[1]
L = dedup([json.loads(l) for l in open(os.path.join(d, 'log.jsonl'))], 'step')
steps = [e['step'] for e in L]
busyw = {0: [], 1: []}; ctrlpc = collections.Counter()
for line in open(os.path.join(d, 'watch.txt')):
    m = WRE.match(line)
    if not m: continue
    a, st, pc, v = int(m.group(4), 16), int(m.group(1)), int(m.group(2), 16), int(m.group(5), 16)
    for s in (0, 1):
        if a == 0x21e0c + s * 0x2e + 8: busyw[s].append((st, pc, v))
        if a == 0x21e0c + s * 0x2e + 6: ctrlpc['%06x' % pc] += 1
ok = n = 0; sides = collections.Counter()
for s in (0, 1):
    for k, (st, pc, v) in enumerate(busyw[s]):
        if pc != 0xe638: continue
        i = bisect.bisect_left(steps, st)
        if i >= len(L) or i == 0: continue
        n += 1; sides[s] += 1
        frame = L[i]['frame']
        before = busyw[s][k - 1] if k else None
        good = frame % 8 == 0 and before is not None and before[2] == 0 and before[0] > steps[i - 1]
        ok += good
print('castle releases: %d/%d on frame%%8==0 with busy 0 before; by side %s' % (ok, n, dict(sides)))
print('ctrl (+6) writers:', dict(ctrlpc))

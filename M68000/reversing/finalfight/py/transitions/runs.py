"""runs.py <log> <f0> <f1> [field...]: forward-fill the C lines of a trans.lua log and print the runs (value, first frame, length) of the given fields
(default p1st p1s45) over frames f0..f1, plus the position at the run start from the P lines when available."""
import sys, re
log, f0, f1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
fields = sys.argv[4:] or ['p1st', 'p1s45']
cur = {}
rows = {}
for ln in open(log):
    if not ln.startswith('C '): continue
    p = ln.split()
    f = int(p[1])
    for kv in p[2:]:
        k, v = kv.split('=')
        cur[k] = v
    rows[f] = dict(cur)
frames = sorted(rows)
# forward fill per frame
state = {}
prev = None
out = []
fi = 0
for f in range(frames[0], f1 + 1):
    if f in rows: state = rows[f]
    key = tuple(state.get(k) for k in fields)
    if f >= f0:
        if key != prev: out.append([f, key, 1]); prev = key
        else: out[-1][2] += 1
for f, key, n in out: print(f, ' '.join('%s=%s' % kv for kv in zip(fields, key)), 'for', n, 'frames')

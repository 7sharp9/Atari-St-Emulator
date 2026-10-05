# compact timeline of a poked hit: hitreact.py <rec.bin> <record idx> <from frame> <to frame>   (states (2,3,4) run-lengths)
import rec, sys
fs = rec.load(sys.argv[1])[1:]; i = int(sys.argv[2]); a, b = int(sys.argv[3]), int(sys.argv[4])
prev = None; n = 0; out = []
for f in fs:
    if f.f < a or f.f > b: continue
    r = f.p2[i]
    k = (r[2], r[3], r[4]) if r[0] else None
    if k != prev:
        if prev is not None or n: out.append((prev, n))
        prev = k; n = 0
    n += 1
out.append((prev, n))
print(' '.join('%s:%d' % ('-' if k is None else '%d.%d.%d' % k, n) for k, n in out))

"""trend_bytes.py <starts dir> <tag>: for every RAM byte outside stack/screens/object map, the value series over the demo-start snapshots;
prints the bytes (and big-endian words) whose series is monotone non-decreasing or non-increasing with >= 4 distinct values, and the 20 with the
largest |Spearman| against game index (p not corrected for the ~1M bytes scanned; this is a candidate list, not a test)."""
import sys, os, glob
d, tag = sys.argv[1], sys.argv[2]; OFF = 87
fs = sorted(glob.glob(os.path.join(d, f'{tag}_g*.snap'))); R = [open(f, 'rb').read()[OFF:OFF+0x100000] for f in fs]; n = len(R)
skip = lambda a: 0x52a58 <= a < 0x70000 or 0x32a58 <= a < 0x42a58 or 0x42a58 <= a < 0x52a58
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0]*len(v); i = 0
    while i < len(o):
        j = i
        while j+1 < len(o) and v[o[j+1]] == v[o[i]]: j += 1
        for k in range(i, j+1): r[o[k]] = (i+j)/2+1
        i = j+1
    return r
gi = rank(list(range(n)))
def rho(v):
    b = rank(v); ma = sum(gi)/n; mb = sum(b)/n
    num = sum((p-ma)*(q-mb) for p, q in zip(gi, b)); den = (sum((p-ma)**2 for p in gi)*sum((q-mb)**2 for q in b))**.5
    return num/den if den else 0
res = []; mono = []
for a in range(0, 0x100000 - 1, 1):
    if skip(a): continue
    v = [r[a] for r in R]
    if len(set(v)) < 2: continue
    res.append((abs(rho(v)), a, 'b', v))
    if len(set(v)) >= 4 and (all(x <= y for x, y in zip(v, v[1:])) or all(x >= y for x, y in zip(v, v[1:]))): mono.append((a, v))
print(f'{n} starts; bytes monotone with >= 4 distinct values: {len(mono)}')
for a, v in mono[:40]: print(f'  ${a:06x}', ' '.join(f'{x:02x}' for x in v))
res.sort(reverse=True)
print('top |rho| bytes:')
for r, a, _, v in res[:20]: print(f'  ${a:06x} rho={r:.2f}', ' '.join(f'{x:02x}' for x in v))

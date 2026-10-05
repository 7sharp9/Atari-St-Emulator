"""cmpkinds.py <flowA> <baseA> <flowB> <baseB>: align the code of two flow listings by relative offset from the kind base and print differing instructions
(addresses inside the kind normalised to offsets)."""
import re, sys
def load(fn, base):
    d = {}
    for l in open(fn):
        m = re.match(r'  ([0-9a-f]{6}): (.*)$', l.rstrip('\n'))
        if not m or m.group(2).startswith('.dw'): continue
        a = int(m.group(1), 16)
        t = m.group(2)
        t = re.sub(r'\$([0-9a-f]+)', lambda x: ('@%x' % (int(x.group(1), 16) - base)) if base <= int(x.group(1), 16) < base + 0x4000 and len(x.group(1)) >= 5 else x.group(0), t)
        t = re.sub(r'== \$[0-9a-f]+\+?', '== ', t)
        d[a - base] = t
    return d
A = load(sys.argv[1], int(sys.argv[2], 16)); B = load(sys.argv[3], int(sys.argv[4], 16))
keys = sorted(set(A) | set(B))
same = diff = 0
for k in keys:
    if A.get(k) == B.get(k): same += 1
    else:
        diff += 1
        print('%05x  %-44s | %s' % (k, A.get(k, '-'), B.get(k, '-')))
print('same', same, 'diff', diff)

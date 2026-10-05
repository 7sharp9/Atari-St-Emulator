"""seqdiff.py <flowA> <baseA> <flowB> <baseB>: difflib over normalised instruction sequences (branch/jsr targets inside the kind replaced by '@')."""
import re, sys, difflib
def load(fn, base, size=0x3000):
    L = []
    for l in open(fn):
        m = re.match(r'  ([0-9a-f]{6}): (.*)$', l.rstrip('\n'))
        if not m or m.group(2).startswith('.dw'): continue
        a = int(m.group(1), 16); t = m.group(2)
        t = re.sub(r'== \$[0-9a-f]+\+?\w*', '', t)
        t = re.sub(r'\$([0-9a-f]{5,})', lambda x: '@' if base <= int(x.group(1), 16) < base + 0x8000 else x.group(0), t)
        L.append((a, t))
    return L
A = load(sys.argv[1], int(sys.argv[2], 16)); B = load(sys.argv[3], int(sys.argv[4], 16))
sm = difflib.SequenceMatcher(None, [t for _, t in A], [t for _, t in B], autojunk=False)
eq = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal': eq += i2 - i1; continue
    print('--- %s A[%06x..%06x] B[%06x..%06x]' % (tag, A[i1][0] if i1 < len(A) else 0, A[i2 - 1][0] if i2 > i1 else 0, B[j1][0] if j1 < len(B) else 0, B[j2 - 1][0] if j2 > j1 else 0))
    for k in range(i1, i2): print('  A %06x %s' % A[k])
    for k in range(j1, j2): print('  B %06x %s' % B[k])
print('equal', eq, 'of', len(A), len(B))

"""Which spawn types are referenced?  Sources: (a) the five spawn lists (MDATAn expanded, offset $2200 = $27200-$25000, 4-byte records, $7fff ends),
(b) the random re-spawn tables ($ff76: mask longword + pointer per world; records of 3 words? see below), (c) drop groups ($179d8: 4 types per world, picked
with random 0-3 by $17984), (d) immediate types loaded before jsr/bsr $10006 in the code.  Descriptor table = longwords at $10474 (type byte indexes it)."""
import sys, struct, re, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from lsd import depack
from huff import expand
r = ram()
# descriptor table extent: longwords at $10474 that point into the image
# the table ends where the first descriptor begins: N = (lowest non-null pointer - $10474) / 4
allp = []
i = 0
while True:
    p = int.from_bytes(r[0x10474 + 4*i: 0x10474 + 4*i + 4], 'big')
    if p and not (0x10000 <= p < 0x30000): break
    allp.append(p); i += 1
    nz = [q for q in allp if q]
    if nz and 0x10474 + 4*i >= min(nz): break
ptrs = allp
nulls = [t for t, q in enumerate(ptrs) if q == 0]
print('descriptor pointer table $10474: %d entries (types 0..%d); null pointers (no descriptor) at types %s' % (len(ptrs), len(ptrs) - 1, nulls))
used = collections.defaultdict(set)
names = {1: 'Klondike', 2: 'Orient', 3: 'Amazon', 4: 'Ice Land', 5: 'Bermuda'}
for w in range(1, 6):
    e, _ = expand(depack(rd(f'MDATA{w}.DCH'))[0])
    a = 0x2200
    while e[a:a+4] == b'\0\0\0\0': a += 4
    n = 0
    while int.from_bytes(e[a:a+2], 'big') != 0x7fff:
        used[e[a+3]].add(('list', w)); n += 1; a += 4
    print('world', w, names[w], 'spawn list records', n, 'distinct types', len({t for t, s in used.items() if ('list', w) in s}))
# (b) random tables $ff76: 8 bytes per world (mask long, pointer)
for w in range(5):
    mask = int.from_bytes(r[0xff76 + 8*w: 0xff76 + 8*w + 4], 'big'); p = int.from_bytes(r[0xff76 + 8*w + 4: 0xff76 + 8*w + 8], 'big')
    n = mask + 1
    print('random table world', w + 1, 'mask', hex(mask), 'ptr', hex(p), 'records', n, [r[p + 4*k: p + 4*k + 4].hex() for k in range(n)])
    for k in range(n):
        rec = r[p + 4*k: p + 4*k + 4]
        # record = column word, row byte, type byte  (same as the spawn list)
        t = rec[3]
        if int.from_bytes(rec[:2], 'big') != 0xffff: used[t].add(('random', w + 1))
# (c) drop groups
for w in range(5):
    g = list(r[0x179d8 + 4*w: 0x179d8 + 4*w + 4])
    for t in g: used[t].add(('drop', w + 1))
    print('drop group world', w + 1, g)
# (d) immediate spawns in code
asm = open(WORK + '/data/full.asm').read().split('\n')
imm = collections.Counter()
for k, l in enumerate(asm):
    if re.search(r'(jsr|bsr) \$10006', l):
        ctx = asm[max(0, k-8):k]
        for c in reversed(ctx):
            m = re.search(r'move\.b #\$([0-9a-f]+),D0', c) or re.search(r'moveq #(\d+),D0', c)
            if m:
                t = int(m.group(1), 16) if 'move.b' in c else int(m.group(1)); imm[t] += 1; used[t].add(('code', l.split()[0])); break
print('immediate spawn types at jsr/bsr $10006 (the list walker and the random re-spawner pass a record pointer in A0, so none):', sorted(imm.items()))
# (e) $1365a: 'spawn a child of type D3' entry used by enemy handlers; D3 immediates at its four callers
for k, l in enumerate(asm):
    if re.search(r'(jsr|bsr) \$1365a', l):
        for c in reversed(asm[max(0, k-9):k]):
            m = re.search(r'move\.b #\$([0-9a-f]+),D3', c)
            if m:
                used[int(m.group(1), 16)].add(('child', l.split()[0])); print('  $1365a caller', l.split()[0], 'child type', int(m.group(1), 16)); break
print()
allt = set(t for t in range(1, len(ptrs)) if ptrs[t])
unref = sorted(t for t in allt if t not in used)
print('types with a descriptor and no reference in any of the four sources:', unref)
print('referenced only by code/random/drop/child (not in any list):', sorted(t for t in used if t in allt and all(s[0] != 'list' for s in used[t])))
print('candidates per descriptor kind:', {t: (r[ptrs[t]], r[ptrs[t]+1:ptrs[t]+6].hex()) for t in unref})

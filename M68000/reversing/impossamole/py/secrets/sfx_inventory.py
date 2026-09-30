"""Effect inventory from the tables: entry (type, record index), the 13-byte record fields, audible VBLs (model), and static references to the sound index."""
import sys, re, struct, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
from sfx_engine import Engine
r = ram()
imm = collections.defaultdict(list)
L = open(WORK + '/data/full.asm').read().split('\n')
for i, l in enumerate(L):
    if re.search(r'(jsr|bsr) \$1c840', l):
        for c in reversed(L[max(0, i-8):i]):
            m = re.search(r'move\.b #\$([0-9a-f]+),D0', c) or re.search(r'moveq #(\d+),D0', c)
            if m:
                v = int(m.group(1), 16) if 'move.b' in c else int(m.group(1)); imm[v].append(l.split()[0]); break
for w, base in ((0, 0xc), (1, 0xd)): pass
table_refs = {}
for w in range(3): table_refs[0xc + 1 + w] = ['$db00: $c + weapon level $bb72']; table_refs[0xf + 1 + w] = ['$dbba: $f + weapon level $bb72']
for w, v in enumerate(r[0xfb92:0xfb97]): table_refs.setdefault(v, []).append(f'$fb76 table $fb92[world {w+1}]')
for w, v in enumerate(r[0x13be6:0x13beb]): table_refs.setdefault(v, []).append(f'$13ba0 table $13be6[world {w+1}]')
out = []
out.append('idx rec  peak susp dur flags(9) rate(7,8) sweep(5,6) audible_VBLs static references')
for i in range(53):
    typ, rec = struct.unpack('>HH', r[0x1cabe+8*i:0x1cabe+8*i+4])
    b = r[0x1d430 + 13*rec:0x1d430 + 13*rec + 13]
    aud = 0
    if i:
        e = Engine(r); e.start(i)
        for k in range(400):
            g = e.vbl()
            if any(v > 0 for rg, v in g if rg in (8, 9, 10)): aud = k + 1
    refs = imm.get(i, []) + table_refs.get(i, [])
    out.append(f'{i:3d} {rec:3d}  {b[4]:3d} {b[2]:4d} {b[12]:3d}  {b[9]:#04x}  {b[7] | b[8] << 8:5d}  {b[5]:3d},{b[6]:3d}   {aud:4d}   {len(refs)} ' + ' '.join(str(x) for x in refs[:3]))
open(WORK + '/data/sfx_inventory.txt', 'w').write('\n'.join(out))
print('\n'.join(out))
used = set(imm) | set(table_refs)
print('sound indices never referenced (no immediate, no table):', [i for i in range(1, 53) if i not in used], ' index 0 referenced by table $13be6[world 2]')

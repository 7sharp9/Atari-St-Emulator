"""census.py <snap>...: mode histogram of live persons, $57fd0, per-lord goods, farmers carrying code 8, equipment bytes.
Run from M68000/: python3 reversing/powermonger/py/equip_census.py <snap>..."""
import os, sys, collections
ROOT = os.path.abspath(os.environ.get('M68000_ROOT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from disassemble import ram_from_snap
w = lambda r, a: (r[a] << 8) | r[a + 1]
for p in sys.argv[1:]:
    r = ram_from_snap(p)
    print('==', p, 'season $57fd0 =', hex(w(r, 0x57fd0)))
    modes = collections.Counter(); farm8 = 0; farm = 0; c33 = collections.Counter(); c44 = collections.Counter()
    special = []
    for i in range(512):
        a = 0x51b66 + 50 * i
        if r[a+5] == 0 or r[a+5] > 127 or r[a+6] != 0: continue
        job = 9 if r[a+7] & 0x10 else r[a+7] & 0xf
        modes[r[a+31]] += 1
        if job == 1:
            farm += 1
            if r[a+33] == 8: farm8 += 1
        c33[(job, r[a+33])] += 1; c44[(job, r[a+44])] += 1
        if r[a+31] in (0x7c, 0x90): special.append((i, r[a+5], job, hex(r[a+30]), hex(r[a+31]), r[a+33], r[a+44]))
    print(' modes', {hex(k): v for k, v in sorted(modes.items())})
    print(' farmers', farm, 'carrying code 8:', farm8)
    print(' (job,byte33)', {k: v for k, v in sorted(c33.items()) if k[1]})
    print(' (job,byte44)', {k: v for k, v in sorted(c44.items())})
    print(' mode 7c/90 men (idx,side,job,prev,mode,b33,b44):', special)
    for k in range(64):
        b = 0x4e514 + 32 * k
        if r[b] == 0 and w(r, b + 4) == 0: continue
        print('  leader %2d side %d food %4d field %3d goods %s' % (k, r[b], w(r, b + 6), w(r, b + 8), list(r[b+24:b+32])))

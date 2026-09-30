"""filemap.py SNAPRAM.bin : locate every 256-byte block of INIT.DAT/SUPER1.DAT/SUPER.DAT inside a RAM dump (as produced by
dumpram.py), merge runs with equal (ram - fileoff) delta.  Blocks that are all-zero / all-equal are ignored (ambiguous)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ssh
from ssh import sscfg
ram = open(sys.argv[1], 'rb').read()
for f in ('INIT.DAT', 'SUPER1.DAT', 'SUPER.DAT'):
    d = open(os.path.join(sscfg.FILES, f), 'rb').read()
    print('==', f, len(d))
    prev = ('x',); start = 0; out = []
    for off in range(0, len(d), 256):
        blk = d[off:off + 256]
        if len(set(blk)) <= 2:
            key = ('amb',)
        else:
            i = ram.find(blk)
            key = (i - off,) if i >= 0 else ('none',)
        if key != prev:
            if off > 0: out.append((start, off, prev))
            start, prev = off, key
    out.append((start, len(d), prev))
    for s, e, k in out:
        print('  file %06x-%06x  %s' % (s, e, ('ram = file + %x  (%x..%x)' % (k[0], k[0] + s, k[0] + e)) if len(k) == 1 and isinstance(k[0], int) else k[0]))

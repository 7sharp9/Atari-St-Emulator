"""Where do INIT.DAT / SUPER1.DAT / SUPER.DAT sit in RAM in the race snapshot, and which parts were altered?"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
ram, _ = load_ram(sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE)
for name in ['INIT.DAT', 'SUPER1.DAT', 'SUPER.DAT']:
    f = open(os.path.join(sscfg.FILES, name), 'rb').read()
    print(name, len(f))
    # probe 32-byte chunks at stride 512 of the file
    hits = []
    for off in range(0, len(f) - 32, 256):
        chunk = f[off:off+32]
        if chunk == b'\0'*32 or len(set(chunk)) < 3: continue
        i = ram.find(chunk)
        hits.append((off, i))
    n = sum(1 for o, i in hits if i >= 0)
    print(' probes', len(hits), 'found', n)
    prev = None
    for o, i in hits[:40]:
        print('  file+%06x -> ram %s' % (o, hex(i) if i >= 0 else None))

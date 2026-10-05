"""atkscripts.py <table base> <nsub>: decode the attack script chooser ($28dc8 / $2b018): words at base: [sub offsets..., script offsets..]; word[base+2*sub] -> 32-byte pick table (index rand&0x1f) of script ids (byte = word offset into
the script-offset table at base+4 (kind 1: $28df4)); script = bytes of 4(A6) attack ids ending with $ff."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim import rom, rw
base = int(sys.argv[1], 16); nsub = int(sys.argv[2], 10)
sbase = int(sys.argv[3], 16) if len(sys.argv) > 3 else base + 4   # script offset table ($28df4 = $28df0 + 4; kind 3: $2e79a)
for sub in range(nsub):
    pk = base + rw(base + 2 * sub)
    ids = list(rom[pk:pk + 32])
    uniq = sorted(set(ids))
    print('sub%d pick table %06x: %s' % (sub, pk, ' '.join('%02x' % i for i in ids)))
    for i in uniq:
        so = sbase + rw(sbase + i)
        # decode script bytes
        bs = []; a = so
        while rom[a] != 0xff and len(bs) < 40: bs.append(rom[a]); a += 1
        print('   id %02x x%d -> script %06x: %s ff' % (i, ids.count(i), so, ' '.join('%02x' % b for b in bs)))

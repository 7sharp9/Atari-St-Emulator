#!/usr/bin/env python3
"""screen66.py <snap>...: list object records (slots 1..511, $51b66 stride 50) with prev byte 30 == $66 or mode byte 31 in
{$36,$66}: slot, address, side(5) cat(6) sub(7) word28, prev/mode, byte 33 (== $a: carrying a Boat), flag bit 5 of byte 7
(afloat), x/y words 8/10, target 48. Summary per snapshot: count, lone (word 28 == 0), with Boat."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
OBJ = 0x51b66
def w(r, a): return (r[a] << 8) | r[a + 1]
verbose = '-v' in sys.argv
for sn in [a for a in sys.argv[1:] if a != '-v']:
    r = ram_from_snap(sn); hits = []
    for k in range(1, 512):
        b = OBJ + 50 * k
        if r[b + 30] == 0x66 or r[b + 31] in (0x36, 0x66):
            hits.append((k, b, r[b + 5], r[b + 6], r[b + 7], w(r, b + 28), r[b + 30], r[b + 31], r[b + 33], w(r, b + 8), w(r, b + 10), w(r, b + 48)))
    lone = sum(1 for h in hits if h[5] == 0); boat = sum(1 for h in hits if h[8] == 0xa)
    print(f'{sn}: n={len(hits)} lone={lone} boat={boat}')
    if verbose:
        for h in hits:
            print('  slot %3d $%05x side %02x cat %02x sub %02x w28 %04x prev %02x mode %02x b33 %02x x %04x y %04x t48 %04x' % h)

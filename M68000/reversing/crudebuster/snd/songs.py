#!/usr/bin/env python3
"""Static view of the HuC6280 song table: header at logical $4000 (bank 1, MPR2): [max id][oki table ptrs x3 at $4001/$4003/$4005] then song pointers at
$4005+2*id.  Song header (read by $E32C..): $5D $5E $5F $16 $17 then 2 bytes per set channel bit (ch0-7 from $5D, ch8-15 from $5E, MSB = lowest channel of the byte) = channel stream pointers.
Logical->physical with the MPRs the IRQ handlers run with: $4000 bank1, $6000 bank2, $8000 bank3, $A000 bank4, $C000 bank5, $E000 bank0."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('M68000_ROOT') or os.path.abspath(os.path.join(HERE, '..', '..', '..'))
D = open(os.path.join(ROOT, 'scratchpad/crudebuster/rom/cbuster_huc.bin'), 'rb').read()
BANK = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 0}   # logical page (addr>>13) -> physical bank in the handlers
def phys(a): return (BANK[(a >> 13) & 7] << 13) | (a & 0x1fff)
def rb(a): return D[phys(a)]
def rw(a): return rb(a) | rb(a + 1) << 8
MAXID = rb(0x4000)
def header(i):
    p = rw(0x4005 + 2 * i)
    h = [rb(p + k) for k in range(5)]
    chans = []
    q = p + 5
    for x in range(16):
        m = h[0] if x < 8 else h[1]
        if m & (0x80 >> (x & 7)):   # E4D6 = 80 40 20 10 08 04 02 01: channel x <-> bit 7-(x&7)
            chans.append((x, rw(q))); q += 2
    return p, h, chans, q
if __name__ == '__main__':
    print('max id %02x, oki tables A=%04x B=%04x C=%04x' % (MAXID, rw(0x4001), rw(0x4003), rw(0x4005)))
    for i in range(1, MAXID + 1):
        p, h, chans, q = header(i)
        print('%02x hdr@%04x mask=%02x%02x flag=%02x ov=%02x%02x end=%04x ch=%s' % (i, p, h[1], h[0], h[2], h[4], h[3], q, ' '.join('%d:%04x' % c for c in chans)))

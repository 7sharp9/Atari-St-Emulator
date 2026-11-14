"""status_check.py <depacked BLOOD.COM, scratchpad/captainblood/depacked/BLOOD.COM> <arm.txt>...: planet status byte (table +3) from the file's state bit array ($810, bit 100+5*i, 5 bits) vs RAM dump, per arm.
Also: which planets qualify for contact (bits 0 and 3) and the race (index>>4)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diffarms import parse
com = open(sys.argv[1], 'rb').read(); st = com[0x810:]
def bits(i):   # b942: 16-bit window at byte (b>>3) little-endian, >> (b&7), & 0x1f, b = 100+5i
    b = 100 + 5 * i; w = st[b >> 3] | (st[(b >> 3) + 1] << 8); return (w >> (b & 7)) & 0x1f
fileb = [bits(i) for i in range(128)]
for p in sys.argv[2:]:
    t = parse(p)[0]
    ok = sum(t[4*i+3] == fileb[i] for i in range(128)); w2 = sum(t[4*i+2] == 0 for i in range(128))
    print(os.path.basename(p), 'status byte == file bits: %d/128; +2 byte zero: %d/128' % (ok, w2))
q = [i for i in range(128) if fileb[i] & 9 == 9]
print('contact-capable (bits 0 and 3):', len(q)); print('status histogram', {hex(v): fileb.count(v) for v in sorted(set(fileb))})
from collections import Counter
print('contact-capable per race (index>>4):', dict(sorted(Counter(i >> 4 for i in q).items())))

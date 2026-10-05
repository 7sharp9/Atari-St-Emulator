"""ranktab.py: per-rank AI parameters read by kind 1 ($281da), kind 2 ($2a3c8..): tables of 3 x 32 bytes per subtype: A0[rank] -> 142(A6) (attack roll threshold: rand&$f <= it),
 A0[32+rank] -> 143(A6) (chain-continue threshold: rand&$1f < it), A0[64+rank] -> 169(A6) (kind 1: dodge roll /32) or 168(A6) (kind 2: guard roll /32)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anim import rom, rw
def dump(base, nsub, name):
    for sub in range(nsub):
        a = base + rw(base + 2 * sub)
        print('%s sub%d table %06x' % (name, sub, a))
        for lab, o in (('142 atk-roll/16', 0), ('143 chain/32', 32), ('dodge/guard /32', 64)):
            print('  %-16s %s' % (lab, ' '.join('%2d' % rom[a + o + r] for r in range(32))))
dump(0x28204, 2, 'kind1')
dump(0x2a3ea, 2, 'kind2')

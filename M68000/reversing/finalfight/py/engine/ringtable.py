#!/usr/bin/env python3
"""Every call of $2874 with the command word that precedes it (ringcallers.py heuristic) and the decoded effect.
Types (high byte): 0/12 text ($65f4c), 1 typewriter task ($13ba, table $68646), 2/3/4/5/7 layer clears, 6 high-score panel ($193c),
8 coin pulse task ($2738), 9 tile block ($1bf2, table $67046), 10 tile-word strings ($1342, $6718a), 11 big font ($14e8, $681fc)."""
import os, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
from ringcallers import callers, prev_d0
import ringmsgs
TYPES = {0: 'text', 1: 'typewriter task', 2: 'clear scroll1', 3: 'clear scroll2', 4: 'clear scroll3', 5: 'clear obj', 6: 'high-score panel', 7: 'clear all',
         8: 'coin pulse task', 9: 'tile block', 10: 'tile-word strings', 11: 'big font text', 12: 'text (attr |$180)'}
def decode(v):
    t, p = v >> 8, v & 0xff
    d = TYPES.get(t, '?')
    extra = ''
    try:
        if t in (0, 12):
            lines = ringmsgs.type0(p & 0x7f)
            extra = ('ERASE ' if p & 0x80 else '') + ' / '.join(s.strip() for _, _, _, s in lines)[:70]
        elif t == 10:
            extra = ('ERASE ' if p & 0x80 else '') + 'idx %02x' % (p & 0x7f)
    except Exception as e: extra = '?'
    return '%02x:%02x %-18s %s' % (t, p, d, extra)
if __name__ == '__main__':
    for c, k in callers(0x2874):
        p = prev_d0(c)
        print('%06x %-5s %s' % (c, k, decode(p[1]) if p and p[0] != 'moveq' else ('moveq #%x' % p[1] if p else '?')))

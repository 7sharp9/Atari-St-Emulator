"""wptables.py - dump the waypoint tables of all 8 tracks from SUPER.DAT.

Table layout (proven against the live RAM copy in t1/wp_live_check): the tables live at the end of
SUPER.DAT, loaded to RAM base B ($55c3a in the ss_prep snapshot; -4080(A4)).  Per-track slot count
COUNT[t] and byte offset OFF[t] are the two word tables set in $1199e ($11ca2/$11cc6); the active
table pointer is B + OFF[t] + 2 (-4084(A4), computed by $f386), records are 8 bytes (X, Y, d, f).
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sscfg
COUNT = [0x54,0x56,0x5a,0x8a,0x66,0x8a,0x7a,0x7c]
OFF = [0,0x2a2,0x554,0x826,0xc78,0xfaa,0x13fc,0x17ce]
SD = open(os.path.join(sscfg.FILES,'SUPER.DAT'),'rb').read()
BASE_FILE = SD.find(struct.pack('>4h',1299,326,110,12)) - 2
def table(t):
    p = BASE_FILE + OFF[t] + 2
    return [struct.unpack('>4h', SD[p+8*i:p+8*i+8]) for i in range(COUNT[t])]
if __name__ == '__main__':
    print('BASE_FILE', BASE_FILE, 'file len', len(SD))
    for t in range(8):
        tb = table(t)
        flags = [(i, r[3]) for i, r in enumerate(tb) if r[3] & ~0xf]
        nz_odd = [i for i, r in enumerate(tb) if i % 2 and r != (0,0,0,0)]
        print('track', t+1, 'slots', COUNT[t], 'first', tb[0], 'flag records', flags, 'nonzero odd', nz_odd)

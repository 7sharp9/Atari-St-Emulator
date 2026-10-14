"""captains.py <snap> ...: the leader-flag men in every lord's settlements, the men a revolt can turn into a new group.
`$550e` walks the lord's settlement chain and the unit chain of each settlement (`10(settl)`, next at `24(man)`) for a
captain: owner > 0, flags (byte 7) bit 4, mode (byte 31) `$8a` or `$3c`. `$5c2c` then defects him and `$25d6` makes him
the lead of a new group on the lord's new side, unless he leads a group that still has members (`42(man)`) or the lord
has no men at home, which hand him to `$4bc8` instead (economy.md section 3, ai.md "the revolt chain"). One line per
leader-flag man: lord idx, side, kind, men at home, the settlement, his mode, 42(man), and whether `$550e` would pick
him (`cand`, the mode test only; the last candidate in the walk is the one reconciled)."""
import struct, sys
from observe import load, cell, LORDS, LSTRIDE, SETTL, SSTRIDE, NSETTL, OBJ, LORD_KIND

for path in sys.argv[1:]:
    R = load(path)
    H = lambda a: struct.unpack_from('>H', R, a)[0]
    print('==', path)
    for i in range(NSETTL):
        a = SETTL + SSTRIDE * i
        if R[a + 5] == 0:
            continue
        lo = H(a + 14); lord = LORDS + lo if lo % LSTRIDE == 0 else None
        o, n = H(a + 10), 0
        while o and n < 512:
            m = OBJ + o; n += 1
            if R[m + 7] & 0x10:
                mode = R[m + 31]
                print('lord %3s side %d %-8s men %3d | settl %3d %s owner %d | man $%04x owner %d mode $%02x 42()=$%04x %s' % (
                    lo // LSTRIDE if lord else '?', R[lord] if lord else 0, LORD_KIND.get(R[lord + 1]) if lord else '',
                    H(lord + 8) if lord else 0, i, cell(H(a + 12)), R[a + 5], o, struct.unpack_from('b', R, m + 5)[0],
                    mode, H(m + 42), 'cand' if mode in (0x8a, 0x3c) else ''))
            o = H(m + 24)

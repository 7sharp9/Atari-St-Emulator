"""lolo.py - check LOLO1.GAM against the $1db98 save layout.

The save is a flat sequence of Fwrite()s (save_game $1db98); load_game $1e146 Freads the same
list and never checks the byte counts. This prints the layout, where LOLO1.GAM's 14336 bytes
end, and cross-checks the regions it does hold: the cell altitude $33be4 and the terrain class
$36e78 are both derived from the heights by $c0ee (popgen.World.tiles), so a file in this layout
must have alt == tiles(heights) and (unclaimed/unrocked) class == tiles(heights).
"""
import os, sys, struct
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
from popcfg import WORK
from popgen import World

LAYOUT = [  # (runtime address, bytes, name), order of save_game $1db98 / load_game $1e146
    (None, 4, 'magic $ffffb615'),
    (0x34be4, 0x2102, 'heights 65x65 w'), (0x33be4, 0x1000, 'cell altitude'),
    (0x36e78, 0x1000, 'terrain class'), (0x3c522, 0x1000, 'feature/building'),
    (0x37fd4, 0x1000, 'occupancy'), (0x3b226, 0x20, 'side records'),
    (0x3b278, 0x1222, 'entities 211 x $16'), (0x21e0c, 0x2e, 'god_rec 0'),
    (0x21e3a, 0x2e, 'god_rec 1'), (0x21d50, 2, '$21d50'), (0x3d52e, 2, 'seed'),
    (0x37ec2, 2, '$37ec2 world seed'), (0x3affe, 2, 'human side'), (0x3b246, 2, 'landscape'),
    (0x3d524, 2, 'armageddon'), (0x3c4c8, 2, 'frame counter'), (0x22ad8, 10, 'level record'),
    (0x21d5e, 2, '$21d5e'), (0x3b276, 2, 'paint mode'), (0x3c514, 4, 'battles won'),
    (0x219b2, 2, 'game options'), (0x3c51a, 2, '$3c51a'), (0x36cea, 4, 'score'),
    (0x3d52c, 2, 'checksum'),
]


def main():
    d = open(os.path.join(WORK, 'files', 'LOLO1.GAM'), 'rb').read()
    off = 0
    print('%-6s %-8s %-6s %s' % ('off', 'addr', 'len', 'field'))
    for a, n, name in LAYOUT:
        got = max(0, min(n, len(d) - off))
        mark = '' if got == n else ('  <- file ends: %d of %d bytes' % (got, n) if got else '  (absent)')
        print('%-6d %-8s %-6d %s%s' % (off, '$%x' % a if a else '-', n, name, mark))
        off += n
    print('full layout = %d bytes, LOLO1.GAM = %d (%d clusters of 1024)' % (off, len(d), len(d) // 1024))
    assert struct.unpack_from('>I', d, 0)[0] == 0xffffb615
    h = list(struct.unpack_from('>4225h', d, 4))
    wd = World(0); wd.h = h
    wd.tiles(0, 0, 63, 63)
    alt = d[8454:8454 + 4096]
    ok = sum(1 for c in range(4096) if alt[c] == wd.alt[c])
    print('altitude $33be4 == tiles(heights): %d/4096' % ok)
    cls = d[12550:14336]
    n = len(cls); same = claimed = rock = other = 0
    for c in range(n):
        v, m = cls[c], wd.shape[c]
        if v == m: same += 1
        elif m == 0xf and v in (0x1f, 0x20): claimed += 1
        elif v in (0x2f, 0x30, 0x31): rock += 1
        else: other += 1
    print('terrain class, first %d cells: %d == tiles, %d flat->claimed $1f/$20, %d rock, %d other'
          % (n, same, claimed, rock, other))
    print('max height %d, heights > 8: %d' % (max(h), sum(1 for v in h if v > 8)))


if __name__ == '__main__':
    main()

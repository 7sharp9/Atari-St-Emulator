"""Per-track 40x25 surface-attribute map (1 byte per 8x8 cell) built by $15550 from the stroke list INIT.DAT -3598(A4)
   (4-byte strokes x,y,run[bit7=horizontal],mask) between the per-track start indexes INIT.DAT -1172(A4) (9 words).
   $b798 samples this map (-1910(A4)) at each car's position."""
import sys; sys.path.insert(0,'.')
from tkcommon import *
import initmap, struct
_init = None
def init():
    global _init
    if _init is None: _init = {off: b for off, ln, pos, b in initmap.split_init()[0]}
    return _init

def strokes(track):
    i = init(); idx = struct.unpack('>9H', i[-1172])
    lst = i[-3598]
    return [tuple(lst[4*k:4*k+4]) for k in range(idx[track], idx[track+1])]

def attr_map(track, with_overflow=False):
    """1000-byte map (40 cols x 25 rows). $15550 does `or.b mask,(cell)` with no bounds test, so a stroke past row 24 writes
    beyond the 1000 bytes (into the next buffer); such writes are returned separately as {offset: mask}."""
    cells = bytearray(1000); over = {}
    for x, y, run, mask in strokes(track):
        pos = x + y * 40
        step = 1 if run & 0x80 else 40
        for k in range(run & 0x7f if run & 0x80 else run):
            p = pos + step * k
            if p < 1000: cells[p] |= mask
            else: over[p] = over.get(p, 0) | mask
    return (bytes(cells), over) if with_overflow else bytes(cells)

if __name__ == '__main__':
    import collections
    for t in map(int, sys.argv[1:] or range(8)):
        m = attr_map(t)
        s = 'track %d: %d strokes; values %s' % (t, len(strokes(t)), dict(sorted(collections.Counter(m).items())))
        try:
            ram = load_snap(out('snaps', 'race_%d.snap' % t))
            live = ram[0x671f6:0x671f6+1000]
            s += '   vs live -1910(A4): %d/1000 equal' % sum(1 for a, b in zip(m, live) if a == b)
        except FileNotFoundError: pass
        print(s)

"""Gate: plane 2 (federation $1e208, G2 byte 0) is a descent field on the carve number, written by $24f4c.

    uv run python -I reversing/captive/py/mapgen/flowfield.py <lo> <hi> [d2] [--snap <natural.snap>]

Model of $24f4c (transcribed): for every cell whose G0 is not 0 and not $ffff, start with best = $4000, value = $fe;
by its G1 feature byte, first try the lift destinations: up ($25092: floor k+1 at + offset, value 4) for features
$1c, $37, $06, $1a, $35, $04; down ($250ac: floor k-1 at - offset, value 5) for $1c, $37, $06, $1b, $36, $05; then,
unless the feature is $1c, $1a or $1b, the four neighbours N (0), S (2), E (3), W (1) in that order ($250c6). Each
candidate ($250f6) in the grid with G0 not 0, not $ffff and G0 <= best (unsigned) becomes best and sets the value.
The value is stored in G2 byte 0; a feature of 0 becomes 7. Then the entry cell (32(A6), row 0) gets G2 word 0, and
the cells listed at 13410(A6) (5 groups of 5 (x, y) byte pairs, word < 0 = unused) get 4, or 5 after a feature-$1d
cell in the group (whose own value is 1, or 3 at x = 0 or with a $ffff cell to its left) ($2503c).
So each arrow points to the open neighbour (or lift partner) with the lowest carve number: following arrows walks
the digger's carve order backwards to the entry. Values 4 and 5 mean "take the lift up / down".

For D0 = lo..hi-1 (D1 = $ffff, D2 = 0 unless given, D3 = 0) through gen.py's call: stop at $23cb8 (the return from
$24d78, just before $24f4c) to read G0, G1 and the module variables, run to $23cbc (its return) and compare all 2048
G2 byte-0 values with the model; then run on to the end and check G2 did not change after $24f4c.
With --snap, also compares the two federation layers of the first case with that snapshot's RAM ignoring bit 7 (the
flag federation sets in play): the check that the shortcut call reproduces a natural base-mode call.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import MA6, R, RET, grids, start  # noqa: E402
from stclient import StServer  # noqa: E402

UP = (0x1c, 0x37, 0x06, 0x1a, 0x35, 0x04)
DOWN = (0x1c, 0x37, 0x06, 0x1b, 0x36, 0x05)
NO_NEIGHBOURS = (0x1c, 0x1a, 0x1b)


def s16(b, off):
    return int.from_bytes(b[off:off + 2], 'big', signed=True)


def model(g0, g1, v, lst):
    """g0: 2048 words; g1: 4096 bytes; v: module bytes 0..55; lst: module bytes 13410..13460."""
    g2 = [None] * 2048

    def ok(x, y):
        return 0 <= x < 64 and 0 <= y < 32 and g0[64 * y + x] not in (0, 0xffff)

    feat = bytearray(g1)
    for y in range(32):
        for x in range(64):
            i = 64 * y + x
            if g0[i] in (0, 0xffff):
                continue
            best, val = 0x4000, 0xfe
            f = g1[2 * i + 1]
            k = v[(y >> 3) * 4 + (x >> 4)]
            cands = []
            if f in UP:      # $2514c: D3+1, + words at 16 / 24 + 2*(k-1)
                cands.append((x + s16(v, 16 + 2 * (k - 1)), y + s16(v, 24 + 2 * (k - 1)), 4))
            if f in DOWN:    # $25136: words at 16 / 24 + 2*(k-2), subtracted
                cands.append((x - s16(v, 16 + 2 * (k - 2)), y - s16(v, 24 + 2 * (k - 2)), 5))
            if f not in NO_NEIGHBOURS:
                cands += [(x, y - 1, 0), (x, y + 1, 2), (x + 1, y, 3), (x - 1, y, 1)]
            for cx, cy, cv in cands:
                if ok(cx, cy) and g0[64 * cy + cx] <= best:
                    best, val = g0[64 * cy + cx], cv
            g2[i] = val
            if f == 0:
                feat[2 * i + 1] = 7
    ex = int.from_bytes(v[32:34], 'big')
    g2[ex] = 0
    for grp in range(5):
        d6, d4 = 4, 26
        for w in range(5):
            o = 10 * grp + 2 * w
            if s16(lst, o) < 0:
                continue
            x, y = lst[o], lst[o + 1]
            i = 64 * y + x
            if feat[2 * i + 1] == 0x1d:
                g2[i] = 3 if x == 0 or g0[i - 1] == 0xffff else 1
                d6, d4 = 5, 27
            else:
                g2[i] = d6
                feat[2 * i], feat[2 * i + 1] = 0, d4
    return g2


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    snap = sys.argv[sys.argv.index('--snap') + 1] if '--snap' in sys.argv else None
    if snap:
        args.remove(snap)
    lo, hi = int(args[0]), int(args[1])
    d2 = int(args[2]) if len(args) > 2 else 0
    s = StServer(R)
    tot_ok = tot = later = 0
    first_out = None
    try:
        for d0 in range(lo, hi):
            start(s, d0, 0xffff, d2, 0, stops=[0x23cb8])
            g0b = s.read(MA6 + 56, 4096)
            g0 = [int.from_bytes(g0b[2 * i:2 * i + 2], 'big') for i in range(2048)]
            g1 = s.read(MA6 + 4168, 4096)
            v = s.read(MA6, 56)
            lst = s.read(MA6 + 13410, 50)
            s('run', max_steps=10_000_000, until_pc=0x23cbc)
            g2b = s.read(MA6 + 8280, 4096)
            m = model(g0, g1, v, lst)
            cells = [i for i in range(2048) if m[i] is not None]
            good = sum(m[i] == g2b[2 * i] for i in cells)
            s('run', max_steps=60_000_000, until_pc=RET)
            g2e = s.read(MA6 + 8280, 4096)
            ch = sum(a != b for a, b in zip(g2b, g2e))
            print(f'D0 {d0}: G2 = model on {good}/{len(cells)} open cells; G2 bytes changed after $24f4c: {ch}')
            tot_ok += good
            tot += len(cells)
            later += ch
            if first_out is None:
                first_out = {'outa': s.read(0x1d9e8, 2048), 'outb': s.read(0x1e208, 2048)}
    finally:
        s.close()
    print(f'match {tot_ok}/{tot} open cells over D0 = {lo}..{hi - 1}, D2 = {d2}; G2 bytes changed later: {later}')
    if snap:
        from gfxview import load_ram
        ram, base = load_ram(snap)
        for k, a in (('outa', 0x1d9e8), ('outb', 0x1e208)):
            ref = ram[a - base:a - base + 2048]
            d = sum((x ^ y) & 0x7f != 0 for x, y in zip(first_out[k], ref))
            b7 = sum(x != y for x, y in zip(first_out[k], ref))
            print(f'{k} ${a:x} vs {os.path.basename(snap)}: {2048 - d}/2048 equal ignoring bit 7 '
                  f'({b7} differ in any bit)')


if __name__ == '__main__':
    main()

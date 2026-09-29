"""Compare Impossamole's sprite banks and per-world loader tables across snapshots.

    uv run python <this dir>/compare_banks.py <ref.snap> <other.snap> [<other2.snap> ...]

The world loader $b328 (README "world34") reads, per world w = $bb76-1 (12-byte records at $b3ea, three name
pointers): MDATAn.DCH -> $53000 (0xc800, packed level data), XXX22.DAT -> $40600 (0x2800) and XXX33.DAT ->
$4c400 (0x6c00). The common loader $b288 reads SPRTS22.DAT -> $3b600 (0x5000) and SPRTS33.DAT -> $42e00
(0x9600). So bank 1 ($3b600, 128-byte frames) is common for frames 0-159 (up to $40600) and world-specific for
frames 160-239 ($40600-$42e00); bank 2 ($42e00, 384-byte frames) is common for frames 0-99 (up to $4c400)
and world-specific for frames 100-171 ($4c400-$53000). This script prints, per snapshot pair, how many frames
of each part are byte-identical, plus the loader tables read from the snapshot (names per world).
"""
import os, struct, sys
from pathlib import Path

ROOT = Path(os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))))
sys.path.insert(0, str(ROOT / 'tools'))
from pm_export import ram_from_snap  # noqa: E402


def cstr(r, a):
    return r[a:r.index(0, a)].decode('latin1')


def frames(r, base, stride, lo, hi):
    return [bytes(r[base + i * stride: base + (i + 1) * stride]) for i in range(lo, hi)]


def main():
    ref = ram_from_snap(Path(sys.argv[1]))
    print('loader tables ($b3ac..$b3d0 common, $b3ea per world):')
    print('  common :', [cstr(ref, a) for a in (0xb3ac, 0xb3b8, 0xb3c4, 0xb3d0, 0xb3dd)])
    for w in range(5):
        p = [struct.unpack_from('>I', ref, 0xb3ea + 12 * w + 4 * i)[0] for i in range(3)]
        print(f'  $bb76={w + 1}:', [cstr(ref, a) for a in p])
    parts = [('bank1 frames 0-159   ($3b600)', 0x3b600, 128, 0, 160),
             ('bank1 frames 160-239 ($40600)', 0x3b600, 128, 160, 240),
             ('bank2 frames 0-99    ($42e00)', 0x42e00, 384, 0, 100),
             ('bank2 frames 100-171 ($4c400)', 0x42e00, 384, 100, 172)]
    for path in sys.argv[2:]:
        o = ram_from_snap(Path(path))
        print(f'{sys.argv[1]} (world {ref[0xbb76]}) vs {path} (world {o[0xbb76]}):')
        for name, base, stride, lo, hi in parts:
            a, b = frames(ref, base, stride, lo, hi), frames(o, base, stride, lo, hi)
            same = sum(x == y for x, y in zip(a, b))
            nz = sum(any(x) for x in b)
            print(f'  {name}: {same}/{hi - lo} identical, {nz}/{hi - lo} non-blank in the other')
        # last non-blank frame of each bank
        for bank, base, stride, n in ((1, 0x3b600, 128, 240), (2, 0x42e00, 384, 172)):
            last = max((i for i in range(n) if any(o[base + i * stride: base + (i + 1) * stride])), default=-1)
            print(f'  bank {bank}: last non-blank frame {last} of {n}')


if __name__ == '__main__':
    main()

"""Print every animation list in a RAM range as `addr: frames CONTROL` (frame words end at $fffe/$fffd/$fffc/$ffff).

    uv run python anim_map.py [snap] [lo hi]     (default: pass103/room188.snap, $21f00..$22300)

`$fffc` is followed by a long (jump to another list), see `$00b5b6`. Used to name the sub-animation each handler writes
to 22(A0).
"""
import os, struct, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
from tiles import ram_from_snap

NAMES = {0xfffe: 'loop', 0xfffd: 'hold', 0xffff: 'end', 0xfffc: 'jump'}


def lists(ram, lo, hi):
    a, out, cur, start = lo, [], [], lo
    while a < hi:
        v = struct.unpack_from('>H', ram, a)[0]
        a += 2
        if v == 0xfffc:
            tgt = struct.unpack_from('>I', ram, a)[0]
            a += 4
            out.append((start, cur, f'jump ${tgt:05x}'))
            cur, start = [], a
        elif v >= 0xfffd:
            out.append((start, cur, NAMES[v]))
            cur, start = [], a
        else:
            cur.append(v)
    return out


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('0x') else os.path.join(ROOT, 'scratchpad/impossamole/pass103/room188.snap')
    lo = int(sys.argv[2], 16) if len(sys.argv) > 3 else 0x21f00
    hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x22300
    ram = ram_from_snap(Path(snap))
    for start, fr, end in lists(ram, lo, hi):
        print(f'${start:05x}: {fr} {end}')


if __name__ == '__main__':
    main()

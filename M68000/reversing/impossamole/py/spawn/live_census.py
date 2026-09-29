"""Census of live enemy objects in every Impossamole snapshot: which spawn types are live where.

    uv run python live_census.py [--types 109,111,...] [snap ...]     (default: every .snap under scratchpad/impossamole)

A live kind-1 object's 94(A0) is descriptor+24 (the entry-pointer table), so descriptor = 94(A0)-24 and the type is
the index of that descriptor in the pointer table at $10474. Prints snap, slot, type, x, y, frame word 6(A0),
hp 103, invuln 102, dead 101, state 100, 78, 82.
"""
import os, sys, struct, glob
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
from tiles import ram_from_snap
W = lambda ram, a: struct.unpack_from('>H', ram, a)[0]
L = lambda ram, a: struct.unpack_from('>I', ram, a)[0]
SW = lambda ram, a: struct.unpack_from('>h', ram, a)[0]


def type_of_desc(ram, d):
    for t in range(256):
        if L(ram, 0x10474 + 4 * t) == d:
            return t
    return None


def live_objects(ram, slots=range(0, 20)):
    out = []
    for s in slots:
        a = 0x1a2ea + s * 108
        tw = W(ram, a)
        if tw == 0:
            continue
        p = L(ram, a + 94)
        d = p - 24
        typ = type_of_desc(ram, d) if 0x10474 < d < 0x13000 and ram[d] == 1 else None
        out.append(dict(slot=s, addr=a, tw=tw, x=SW(ram, a + 2), y=SW(ram, a + 4), frame=W(ram, a + 6), anim=L(ram, a + 22),
                        type=typ, hp=ram[a + 103], inv=ram[a + 102], dead=ram[a + 101], st=ram[a + 100], b78=ram[a + 78],
                        w82=W(ram, a + 82), w16=SW(ram, a + 16), w18=SW(ram, a + 18), b20=ram[a + 20], b21=ram[a + 21]))
    return out


def main():
    args = sys.argv[1:]
    want = None
    if args and args[0] == '--types':
        want = {int(x) for x in args[1].split(',')}
        args = args[2:]
    snaps = args or sorted(glob.glob(os.path.join(ROOT, 'scratchpad/impossamole/**/*.snap'), recursive=True))
    for sp in snaps:
        try:
            ram = ram_from_snap(Path(sp))
            if ram[0x10474 + 4:0x10474 + 8] == b'\0\0\0\0':
                continue
        except (ValueError, OSError, struct.error) as e:
            print('skip', sp, e, file=sys.stderr)
            continue
        for o in live_objects(ram, range(7, 16)):
            if o['type'] is None or (want and o['type'] not in want):
                continue
            print(f"{os.path.relpath(sp, ROOT + '/scratchpad/impossamole')} slot {o['slot']} type {o['type']} x {o['x']} y {o['y']} "
                  f"fr {o['frame']} hp {o['hp']} inv {o['inv']} dead {o['dead']} st {o['st']} b78 {o['b78']} w82 {o['w82']} "
                  f"w16 {o['w16']} w18 {o['w18']} b20 {o['b20']}")


if __name__ == '__main__':
    main()

"""Descriptor-derived columns of the per-type behaviour table (README "Spawn types"), for every kind-1 Amazon type.

    uv run python spawn_behaviour.py [snap]

Prints, per type: hit points, contact damage, type word (bank), hit-box half sizes (+1, +2) and offsets (+10, +12), start
speeds (+14, +16 -> 16/18(A0), pixels per frame), start direction bytes (+3 -> 20(A0), +4 -> 21(A0)), animation tick
count (+5), score (+18 -> 106(A0), added to `$bb6e`), handler, and the entry pointers (+24...) with the frames of the
first sub-animation at each. Handler-specific rules are in the README table; this only reads the descriptors.
"""
import os, struct, sys
from pathlib import Path
ROOT = os.environ.get('M68000_ROOT', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')))
sys.path.insert(0, os.path.join(ROOT, 'reversing/impossamole/py'))
from tiles import ram_from_snap
from spawn_types import anim_frames
W = lambda ram, a: struct.unpack_from('>H', ram, a)[0]
L = lambda ram, a: struct.unpack_from('>I', ram, a)[0]


# `$e5a0` trigger parameters (D0, D1, D2, D3) read off each handler; D2 of the chameleons is descriptor word +32's low half
TRIGGERS = {110: (0, 0x40, 0, 0x40), 111: (8, 8, 0, -8), 113: (0, 0x20, 0, 0x20), 128: (8, 8, -32, -8), 129: (8, 8, 32, -8),
            132: (0x20, 0, -16, 0)}


def trigger_box(ram, t):
    """Hero top-left minus object top-left, open intervals (dx, dy), from `$e5a0` + `$b71a` (see trigger_scan.py)."""
    d = L(ram, 0x10474 + 4 * t)
    D0, D1, D2, D3 = TRIGGERS[t]
    off8, off10, w0, h0 = W(ram, d + 10), W(ram, d + 12), ram[d + 1], ram[d + 2]
    Wd, Hd = (2 * D0 + 0x20) & 0xff, (2 * D1 + 0x18) & 0xff
    return (D2 + off8 + D0 - Wd, D2 + off8 + D0 + w0), (D3 + off10 + D1 - Hd, D3 + off10 + D1 + h0)


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'scratchpad/impossamole/pass103/room188.snap')
    ram = ram_from_snap(Path(snap))
    print('type  hp dmg tw box(w,h) off(x,y) speed(vx,vy) dir(20,21) tick score handler   entries (first sub-animation frames)')
    for t in list(range(109, 133)):
        d = L(ram, 0x10474 + 4 * t)
        if ram[d] != 1:
            continue
        ents = []
        for i in range(4):
            p = L(ram, d + 24 + 4 * i)
            if 0x20000 < p < 0x24000:
                fr, end, _ = anim_frames(ram, p)
                ents.append(f'${p:05x}{fr[:6]}{end and format(end, "x")}')
            else:
                ents.append(f'{p:#x}')
        print(f"{t:4} {ram[d+6]:4} {ram[d+7]:3} {W(ram, d+8):2} ({ram[d+1]:2},{ram[d+2]:2}) ({W(ram, d+10)},{W(ram, d+12)}) ({W(ram, d+14)},{W(ram, d+16)}) "
              f"({ram[d+3]},{ram[d+4]}) {ram[d+5]:4} {W(ram, d+18):5} ${L(ram, d+20):06x}  " + ' '.join(ents))
    print('\ntrigger boxes (hero top-left minus object top-left, open intervals): type dx dy')
    for t in TRIGGERS:
        (x0, x1), (y0, y1) = trigger_box(ram, t)
        print(f'{t:4} dx ({x0},{x1}) dy ({y0},{y1})')


if __name__ == '__main__':
    main()

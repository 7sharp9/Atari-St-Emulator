"""prep.py <in.snap> <out.snap> <steps> side:k [side:k ...]: take each named side's slot and send drop equipment `$18`
(gate_orders.sh arm drope: `$6cda` -> `$39d4` D7 = 2, the carried boats dropped) to each named group, one order per
slot per batch, batches 2M steps apart (the slot is consumed in one executor pass); then run to <steps> and snapshot.
Prints, per named group, carried boats and how many of its men (lead + roster) still hold a boat (byte 33 == $0a),
before and after. Why: a Boat carrier skips the walker's water probe (astar.py header, mode $10), so the AI groups of
rand1, which all carry boats, cross water and are no test of land movement. The drop empties the group's carried
boats but every man keeps the one he holds (rand1: 2:0 12/12, 3:0 13/13, 4:0 14/14 still holding), so after the run
each named group's men get byte 33 := 0 (a harness poke) before the snapshot."""
import struct, sys
from move import ROOT, CMD
sys.path.insert(0, str(CMD))
from observe import observe, load          # noqa: E402
from act import from_json                  # noqa: E402
from loop import Emu                       # noqa: E402

OBJ = 0x51b66
H = lambda R, a: struct.unpack_from('>H', R, a)[0]


def boats(R, side, k):
    gb = 0x51538 + 0x13c * side + 0x4c + 2 * k           # check_ungated.py roster_boats
    ms = [H(R, gb - 12)]; o = H(R, gb - 36)
    while o and len(ms) < 200:
        ms.append(o); o = H(R, OBJ + o + 26)
    carried = struct.unpack_from('>h', R, gb + 84 + 48)[0]
    return carried, sum(1 for m in ms if m and R[OBJ + m + 33] == 0xa), len(ms)


def main(a):
    insnap, outsnap, steps = a[0], a[1], int(float(a[2]))
    gs = [tuple(map(int, x.split(':'))) for x in a[3:]]
    R0 = load(ROOT / insnap)
    for s, k in gs:
        print('before', s, k, 'carried boats, men holding a boat, men:', boats(R0, s, k))
    emu = Emu(ROOT / insnap, (ROOT / outsnap).with_suffix('.err'))
    batches = []
    for s, k in gs:
        for b in batches:
            if s not in {x['side'] for x in b}:
                b.append(dict(side=s, type=0x18, x=0, y=0, group=k)); break
        else:
            batches.append([dict(side=s, type=0x18, x=0, y=0, group=k)])
    batches[0] = [dict(side=s, take=True) for s in sorted({s for s, _ in gs})] + batches[0]
    clock = 0
    for b in batches:
        emu.mem(0x58010, 0x40)
        emu.poke(from_json(emu.ram, b))
        clock += emu.run(2_000_000)[0]
    emu.run(steps - clock)
    # strip: every man of each named group holding a boat (byte 33 == $0a) gets byte 33 := 0, one longword `w` of
    # bytes 32..35 with 32, 34, 35 read back first (a harness poke, the same for both arms of an A/B)
    R = bytearray(emu.read('m', None))
    for s, k in gs:
        gb = 0x51538 + 0x13c * s + 0x4c + 2 * k
        ms = [H(R, gb - 12)]; o = H(R, gb - 36)
        while o and len(ms) < 200:
            ms.append(o); o = H(R, OBJ + o + 26)
        for m in ms:
            a = OBJ + m + 32
            b = emu.mem(a, 4)
            if b[1] == 0xa:
                emu.poke([f'w {a:x} {b[0]:02x}00{b[2]:02x}{b[3]:02x}'])
    emu.save(ROOT / outsnap)
    emu.close()
    R = load(ROOT / outsnap)
    for s, k in gs:
        print('after ', s, k, 'carried boats, men holding a boat, men:', boats(R, s, k))


if __name__ == '__main__':
    main(sys.argv[1:])

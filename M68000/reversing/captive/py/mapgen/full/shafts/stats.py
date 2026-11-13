"""Census of what the shaft layout, the reservations and the second room pass produce, over captured bases.

    uv run python -I reversing/captive/py/mapgen/full/shafts/shafts.py stats <capture.bin> [...]

Runs the gated ports (shafts.py) from the emulator's own state before each routine and records what each one did;
then reads the emulator's state after the digger ($23cb4) for which shafts were opened.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'digger'))  # dig.py
from dig import G0, G1  # noqa: E402
from shafts import Gen  # noqa: E402


class Census(Gen):
    def __init__(self, b):
        super().__init__(b)
        self.draws = 0
        self.rooms = []    # (mode, placed, w, h)

    def randcell(self):
        self.draws += 1
        super().randcell()

    def room(self):
        mode = self.W(13584)
        before = bytes(self.m[G0:G0 + 4096]) + bytes(self.m[G1:G1 + 4096])
        Gen.room(self)
        after = bytes(self.m[G0:G0 + 4096]) + bytes(self.m[G1:G1 + 4096])
        self.rooms.append((mode, before != after, self.W(12430), self.W(12432)))


def W(b, o):
    return (b[o] << 8) | b[o + 1]


def stats(recs):
    C = collections.Counter
    groups_req, glen, gstart, retries = C(), C(), C(), C()
    dirs, opened, nres, npass = C(), C(), C(), C()
    res_cells = p2_cells = p2_on_res = 0
    res_placed = res_tried = p2_placed = p2_tried = 0
    for r in recs:
        st = r['st']
        pre = st[0x23ca4][1]
        d0 = r['seed']
        g = Census(pre)
        g.shafts()
        nf = W(pre, 46)
        G = 0 if d0 <= 1 else min((d0 >> 1) - 1, 4) + 1
        groups_req[G] += 1
        retries[g.draws - G] += 0
        post = st[0x23ca8][1]
        assert g.m == post
        for k in range(5):
            ents = [(post[13410 + 10 * k + 2 * e], post[13410 + 10 * k + 2 * e + 1]) for e in range(5)
                    if not post[13410 + 10 * k + 2 * e] & 0x80]
            if k >= G:
                continue
            glen[(len(ents), nf)] += 1
            if ents:
                x, y = ents[0]
                gstart[(pre[((y & 0x18) * 8 + x) >> 4], nf)] += 1
                for (x, y) in ents:
                    dx = post[13360 + 10 * k + 2 * ents.index((x, y))] - x
                    dirs[dx] += 1
                dig = st[0x23cb4][1]
                o = sum(dig[G1 + 2 * (64 * y + x) + 1] == 0x1d for x, y in ents)
                opened[(o, len(ents))] += 1
        # reservations
        pre2 = bytearray(st[0x23ca8][1])
        pre2[12404:12406] = pre[12404:12406]
        g = Census(pre2)
        g.reserve()
        rs = [x for x in g.rooms if x[0] == 1]
        nres[len(rs)] += 1
        res_tried += len(rs)
        res_placed += sum(x[1] for x in rs)
        b = st[0x23cb0][1]
        resset = {i for i in range(2048) if W(b, G0 + 2 * i) == 0xfffd}
        res_cells += len(resset)
        # pass 2
        g = Census(st[0x23ccc][1])
        g.pass2()
        ps = [x for x in g.rooms if x[0] == 2]
        npass[len(ps)] += 1
        p2_tried += len(ps)
        p2_placed += sum(x[1] for x in ps)
        e = st[0x23cd0][1]
        new = [i for i in range(2048) if e[G1 + 2 * i + 1] == 0x23 and st[0x23ccc][1][G1 + 2 * i + 1] != 0x23]
        p2_cells += len(new)
        p2_on_res += sum(i in resset for i in new)
    n = len(recs)
    print(f'{n} bases')
    print('shaft groups requested per base (G):', dict(sorted(groups_req.items())))
    print('entries per requested group, by floor count (entries, floors):', dict(sorted(glen.items())))
    print('start floor of a non-empty group (floor, floors):', dict(sorted(gstart.items())))
    print('door x - $1c x (direction):', dict(dirs))
    print('groups opened by the digger, (entries with $1d after $244b6, entries):', dict(sorted(opened.items())))
    print(f'reservations: rooms tried per base {dict(sorted(nres.items()))}; placed {res_placed}/{res_tried}; '
          f'$fffd cells at $23cb0 {res_cells}')
    print(f'pass 2: rooms tried per base {dict(sorted(npass.items()))}; placed {p2_placed}/{p2_tried}; new $23 cells '
          f'{p2_cells}, of them on a cell reserved before the digger {p2_on_res}')

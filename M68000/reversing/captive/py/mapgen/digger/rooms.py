"""Room census over the digger's output (reversing/captive/mapgen.md, "The digger and rooms").

    uv run python -I <this dir>/rooms.py <capture.bin> [...]

For each base, runs the port (dig.py) on the emulator's pre-digger block and uses it only when its post block equals
the emulator's. Each room instance (the cells one $249da carve pass wrote, from the port's carve tags) is checked
against its size byte s (the G1 parameter byte of its cells, = 12436(A6)): the bounding box must be
((s & 7) + 2) by (((s >> 3) & 7) + 2) cells in some orientation, and every rock cell inside the box a pillar. Also
checks that each room-list entry 12952(A6) + 4k, k >= 13208(A6) at the return, is (x, y, floor, s) of the last
carved cell of a room. Room cells only count while they keep a room-floor feature ($1f/$33): a lift end written later
($35-$37) has parameter 0.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dig import Dig, load  # noqa: E402


def main():
    n = ok = full = multi = small = lift_end = unexpl = 0
    lst = lok = 0
    nb = 0
    for seed, d2, steps, regs, pre, post in load(sys.argv[1:]):
        d = Dig(pre)
        d.run()
        if bytes(d.m) != post:
            continue
        nb += 1
        inst = {}
        for i, t in d.tag.items():
            if t[0] == 'room' and 0 < ((post[56 + 2 * i] << 8) | post[57 + 2 * i]) < 0xff00:
                inst.setdefault(t[1], []).append(i)
        last = {}
        for rid, cs in inst.items():
            n += 1
            xs = [i & 63 for i in cs]
            ys = [i >> 6 for i in cs]
            s = {post[4168 + 2 * i] for i in cs if post[4169 + 2 * i] in (0x1f, 0x33)}
            if len(s) != 1:
                multi += 1
                continue
            s = s.pop()
            want = sorted(((s & 7) + 2, ((s >> 3) & 7) + 2))
            got = sorted((max(xs) - min(xs) + 1, max(ys) - min(ys) + 1))
            ok += want == got
            if want != got:
                small += got[0] <= want[0] and got[1] <= want[1]
            full += len(cs) == got[0] * got[1]
            last[rid] = s
        lo = (post[13208] << 8) | post[13209]
        for k in range(lo, 64):
            o = 12952 + 4 * k
            x, y, f, s = post[o:o + 4]
            if (x, y, f, s) == (0, 0, 0, 0) or (x, y, f, s) == (255, 255, 255, 255):
                continue
            lst += 1
            i = y * 64 + x
            t = d.tag.get(i)
            t2 = d.tag.get(i)
            le = bool(t2 and t2[0] == 'room' and post[4169 + 2 * i] not in (0x1f, 0x33))
            lift_end += le
            good = bool(t and t[0] == 'room' and post[4168 + 2 * i] == s
                        and post[(((i >> 6) & 0x18) << 3 | (i & 63)) >> 4] == f)
            lok += good
            unexpl += not good and not le
    print(f'{nb} bases; rooms {n}: bounding box ((s & 7) + 2) x (((s >> 3) & 7) + 2) in {ok}; '
          f'without pillars (box fully carved) {full}; no single room-floor s {multi}; box smaller than s gives {small}')
    print(f'room-list entries {lst}: (x, y) is a room cell whose G1 parameter is s and whose block floor is the entry\'s '
          f'floor in {lok}; entries whose cell became a lift end since ($35-$37, parameter 0) {lift_end}; '
          f'mismatches not explained by that {unexpl}')


if __name__ == '__main__':
    main()

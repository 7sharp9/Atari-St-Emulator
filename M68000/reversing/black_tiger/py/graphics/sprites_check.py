"""sprites_check.py - prove the sprite bank format against live frames.
For every actor (object table $1f010, stride $10) whose nominal rectangle is on screen in the draw
buffer ($c31a) of each snapshot, slide the decoded frame (current frame and frame-1, both facings,
+-10 px) over the buffer and report the best ok/tot over its non-transparent pixels.
frame-1: the snapshot is taken at the page flip, after the actor routine stored frame+1 ($e514)."""
import glob
import os
import sys

from sprites import *  # noqa


def main():
    names = sorted(glob.glob(os.path.join(OUT, "snaps", "*.snap")))
    tot_act = exact = 0
    lines = []
    for n in names:
        ram = load_snap(n)
        base = os.path.basename(n)
        for i in range(0xb3):
            a = 0x1f010 + i * 16
            t = ram[a]
            if t == 0 or ram[a + 1] in (6, 7) and t != 0xff:
                continue
            try:
                r = actor_frame(ram, a, read_file("BTMAN"), read_file("BTSPR"))
            except Exception:
                r = None
            if r is None:
                continue
            sx, sy, ww = w16(ram, 0x1efec), w16(ram, 0x1efee), w16(ram, 0x1effe)
            x, y = w16(ram, a + 4), w16(ram, a + 6)
            dx = (x - sx) % ww
            if dx > ww // 2:
                dx -= ww
            if not (-40 < dx < 290 and 0 < y - sy < 190):
                continue
            ok, tot, fd, ddx, ddy, flip = search_actor(n, a, rng=10, ram=ram)
            tot_act += 1
            if tot and ok == tot:
                exact += 1
            line = "%-12s actor %05x type %02x state %2d frame %2d: best %4d/%-4d  frame%+d  dx=%+d dy=%+d  mirrored=%d" % (
                base, a, t, ram[a + 1], ram[a + 2], ok, tot, fd, ddx, ddy, flip)
            lines.append(line)
            print(line)
    s = "actors tested %d, exact (ok==tot) %d" % (tot_act, exact)
    print(s)
    open(os.path.join(OUT, "sprites_check.txt"), "w").write("\n".join(lines) + "\n" + s + "\n")


main()

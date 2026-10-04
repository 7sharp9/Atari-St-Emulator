"""hero_check.py - for each snapshot, find which BTMAN slot (any of the 23), facing and offset best
explains the hero rectangle in the draw buffer; exact means every non-transparent hero pixel equals the
screen pixel (the weapon overlay is drawn after the body, so overlay-covered pixels are excluded by
requiring >= 90% coverage and listing the shortfall)."""
import glob
import os

from sprites import *  # noqa


def main():
    man = read_file("BTMAN")
    b = parse_bank(man, 0)
    slots = [decode_frame(man, 0x1fe + k * 512, 2, 32) for k in range(23)]
    lines = []
    for n in sorted(glob.glob(os.path.join(OUT, "snaps", "*.snap"))):
        ram = load_snap(n)
        scr = screen_indices(ram, l32(ram, 0xc31a))
        sx, sy = w16(ram, 0x1efec), w16(ram, 0x1efee)
        x, y = w16(ram, 0x1f014), w16(ram, 0x1f016)
        px0, py0 = x - sx - 16, y - sy - 32
        best = (0, 1, -1, 0, 0, 0)
        for k, rows in enumerate(slots):
            for flip in (0, 1):
                rr = mirror(rows) if flip else rows
                for ddx in range(-12, 13):
                    for ddy in range(-3, 4):
                        tot = ok = 0
                        for yy in range(32):
                            Y = py0 + ddy + yy
                            if not 0 <= Y < 160:
                                continue
                            for xx, c in enumerate(rr[yy]):
                                if c == 0:
                                    continue
                                X = px0 + ddx + xx
                                if 0 <= X < 256:
                                    tot += 1
                                    ok += scr[20 + Y][32 + X] == c
                        if tot > 150 and ok / tot > best[0] / best[1]:
                            best = (ok, tot, k, flip, ddx, ddy)
        line = "%-12s hero state %2d frame %2d facing %d: best slot %2d mirrored=%d dx=%+d dy=%+d  %d/%d (%.1f%%)" % (
            os.path.basename(n), ram[0x1f011], ram[0x1f012], ram[0x1f013], best[2], best[3], best[4], best[5], best[0], best[1], 100.0 * best[0] / best[1])
        print(line)
        lines.append(line)
    open(os.path.join(OUT, "hero_check.txt"), "w").write("\n".join(lines) + "\n")


main()

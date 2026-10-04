"""tiles_residual.py - where do the playfield pixels that differ from the tile render live?
Mask = HUD overlay rectangles seen in the playfield (rows 0..15: time/vitality/score/coin) plus a
+-48 px box around every active actor record ($1f010+, stride $10, type != 0) and the hero.
Reports mismatching pixels outside the mask (expected 0 if tiles are the only other layer)."""
import glob
import os

from tiles import *  # noqa


def main():
    tot_pix = tot_out = 0
    for n in sorted(glob.glob(os.path.join(OUT, "snaps", "*.snap"))):
        ram = load_snap(n)
        base = l32(ram, 0xc31a)
        rows = screen_indices(ram, base)
        lvl = ram_val(ram, 0x17846)
        sx, sy, ww = ram_val(ram, 0x1efec), ram_val(ram, 0x1efee), ram_val(ram, 0x1effe)
        ts = load_tileset(LEVEL_TSET[lvl])
        w, h, words = load_map(lvl)
        pf = playfield_from_tiles(ts, w, h, words, sx, sy, ww)
        mask = [[False] * 256 for _ in range(160)]
        for y in range(16):
            for x in range(256):
                mask[y][x] = True
        for i in range(0xb3):
            a = 0x1f010 + i * 16
            if ram[a] == 0 or ram[a + 1] in (6,) and ram[a] != 0xff:
                continue
            x, y = ram_val(ram, a + 4), ram_val(ram, a + 6)
            dx = (x - sx) % ww
            if dx > ww // 2:
                dx -= ww
            for yy in range(max(0, y - sy - 80), min(160, y - sy + 40)):
                for xx in range(max(0, dx - 64), min(256, dx + 64)):
                    mask[yy][xx] = True
        bad = out = 0
        for y in range(160):
            for x in range(256):
                if rows[20 + y][32 + x] != pf[y][x]:
                    bad += 1
                    if not mask[y][x]:
                        out += 1
        tot_pix += bad
        tot_out += out
        print("%-14s level %d: %5d differing playfield pixels, %d outside HUD/actor boxes" % (os.path.basename(n), lvl, bad, out))
    print("TOTAL differing %d, outside masks %d" % (tot_pix, tot_out))


main()

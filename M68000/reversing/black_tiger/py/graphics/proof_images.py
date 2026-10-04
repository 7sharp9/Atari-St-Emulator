"""proof_images.py - side-by-side proof images: live frame | game-format render.
 proof_tiles.png : live draw buffer of L2 and L5 | tile-only render of the 256x160 playfield at the live scroll
 proof_bosses.png: live boss frame (crop) | the decoded frame drawn at the matched offset, for BTA, BTB, type 1, type $c
 shop_a.png      : the shop snapshot rendered."""
import numpy as np
from ram_actors import *
from tiles import load_tileset, load_map, playfield_from_tiles, LEVEL_TSET, level_palette


def tile_proof():
    tiles = []
    for n in (2, 5):
        ram = load_snap("agents/graphics/snaps/L%da.snap" % n)
        scr = screen_indices(ram, l32(ram, 0xc31a))
        pal = palette_rgb(load_video_regs(snap_path("agents/graphics/snaps/L%da.snap" % n))["palette_words"])
        lvl, sx, sy, ww = w16(ram, 0x17846), w16(ram, 0x1efec), w16(ram, 0x1efee), w16(ram, 0x1effe)
        ts = load_tileset(LEVEL_TSET[lvl]); w, h, words = load_map(lvl)
        pf = playfield_from_tiles(ts, w, h, words, sx, sy, ww)
        live = Image.new("RGB", (256, 160)); mine = Image.new("RGB", (256, 160))
        a, b = live.load(), mine.load()
        for y in range(160):
            for x in range(256):
                a[x, y] = pal[scr[20 + y][32 + x]]
                b[x, y] = pal[pf[y][x]]
        tiles.append((live, mine))
    m = Image.new("RGB", (512 + 8, 320 + 8), (30, 0, 30))
    for r, (l, t) in enumerate(tiles):
        m.paste(l, (0, r * 168)); m.paste(t, (264, r * 168))
    m.save(os.path.join(PNG, "proof_tiles.png"))


def boss_proof():
    cases = [("B2_0", 1), ("B4_5", 1), ("B0_3", 2), ("B3_7", 1)]
    crops = []
    for name, slot in cases:
        n = "agents/graphics/boss/%s.snap" % name
        ram = load_snap(n)
        scr = screen_indices(ram, l32(ram, 0xc31a))
        pal = palette_rgb(load_video_regs(snap_path(n))["palette_words"])
        a = 0x1f010 + slot * 16
        best, info = search(ram, scr, a)
        ok, tot, fd, ddx, ddy, flip = best
        buf, base = bank_of(ram, ram[a])
        b = parse_bank(buf, base)
        an = b["anims"][ram[a + 1]]
        rows = decode_frame(buf, base + an["frames"][ram[a + 2] + fd], an["code"], b["H"])
        if flip:
            rows = mirror(rows)
        H, W = len(rows), len(rows[0])
        px0, py0 = info["vis"][0] + ddx, info["vis"][1] + ddy
        live = Image.new("RGB", (W, H)); mine = Image.new("RGB", (W, H), (0, 0, 0))
        la, ma = live.load(), mine.load()
        for y in range(H):
            for x in range(W):
                X, Y = px0 + x, py0 + y
                la[x, y] = pal[scr[20 + Y][32 + X]] if 0 <= X < 256 and 0 <= Y < 160 else (0, 0, 0)
                if rows[y][x]:
                    ma[x, y] = pal[rows[y][x]]
        crops.append((live, mine, "%s type %02x %d/%d" % (name, ram[a], ok, tot)))
    Wm = max(c[0].width for c in crops) * 2 + 12
    Hm = sum(c[0].height + 6 for c in crops)
    m = Image.new("RGB", (Wm, Hm), (30, 0, 30))
    y = 0
    for live, mine, lab in crops:
        m.paste(live, (0, y)); m.paste(mine, (live.width + 12, y)); y += live.height + 6
    m.save(os.path.join(PNG, "proof_bosses.png"))
    print([c[2] for c in crops])


if __name__ == "__main__":
    tile_proof()
    boss_proof()
    import subprocess

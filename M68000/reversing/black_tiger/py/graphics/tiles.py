"""tiles.py - Black Tiger tilesets (T0..T7), level maps (0..7) and the live-screen proof.

Formats (read from the drawing routines, see notes.md sec 3):
  T<n>   : +$00 palette A (16 words $0RGB), +$20 palette B, +$40 512 bytes tile class table
           (collision class per tile index, read by $ecb4), +$240 tiles: 16x16, 128 bytes,
           ST-interleaved 4 planes (row = 4 words, plane0..3), tile = 16 rows, no mask.
  map n  : word width, word height, then width*height words; word & $3ff = tile index into the
           tile bank, word >> 10 = object code (spawn marker, handled by the mechanics side).
           Tile (x,y) = word[y*width + x]; the world is cyclic in x (modulus width*16).
Screen: the playfield is a 256x160 window at screen (32,20), scrolled by ($1efec,$1efee).

Usage:
  python tiles.py atlas            # PNG atlas for every T file (both palettes)
  python tiles.py level [n]        # whole-level reconstruction PNG(s)
  python tiles.py check [snap...]  # slide/identity check against live snapshots
"""
import os
import sys

from bt_common import *  # noqa

TILE_OFF = 0x240
CLASS_OFF = 0x40
LEVEL_TSET = {0: "T0", 1: "T0", 2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6", 7: "T7"}  # table "00234567" at $175fb


def load_tileset(name):
    d = read_file(name)
    pal = [pal_from_bytes(d, 0), pal_from_bytes(d, 0x20)]
    cls = list(d[CLASS_OFF:CLASS_OFF + 0x200])
    n = (len(d) - TILE_OFF) // 128
    tiles = [decode_st16(d, TILE_OFF + i * 128, 16) for i in range(n)]
    return dict(name=name, pal=pal, cls=cls, tiles=tiles, n=n, raw=d)


def load_map(n):
    d = read_file(str(n))
    w, h = w16(d, 0), w16(d, 2)
    words = [w16(d, 4 + 2 * i) for i in range(w * h)]
    assert len(d) == 4 + 2 * w * h, (len(d), w, h)
    return w, h, words


def level_palette(n, ts):
    """Palette the game shows in level n: T-file palette A ($25f8c); level 1 reuses the resident T0 and
    $ccbe..$ccd2 pokes colours 1..3 to $0010,$0121,$0032 first.  Verified equal to the shifter palette
    of the level snapshots L0a..L7a (8/8)."""
    p = list(ts["pal"][0])
    if n == 1:
        p[1], p[2], p[3] = 0x0010, 0x0121, 0x0032
    return p


def tile_img(ts, i, pal):
    return indexed_image(ts["tiles"][i], pal)


def atlas(ts, pal_i, cols=16):
    n = ts["n"]
    rows = (n + cols - 1) // cols
    img = Image.new("RGBA", (cols * 17 + 1, rows * 17 + 1), (255, 0, 255, 255))
    for i in range(n):
        im = tile_img(ts, i, ts["pal"][pal_i])
        img.paste(im, (1 + (i % cols) * 17, 1 + (i // cols) * 17))
    return img.resize((img.width * 2, img.height * 2), Image.NEAREST)


def render_level(n, pal_i=0):
    ts = load_tileset(LEVEL_TSET[n])
    lp = level_palette(n, ts) if pal_i == 0 else ts["pal"][1]
    w, h, words = load_map(n)
    img = Image.new("RGBA", (w * 16, h * 16), (0, 0, 0, 255))
    cache = {}
    missing = set()
    for y in range(h):
        for x in range(w):
            t = words[y * w + x] & 0x3ff
            if t >= ts["n"]:
                missing.add(t)
                continue
            if t not in cache:
                cache[t] = tile_img(ts, t, lp)
            img.paste(cache[t], (x * 16, y * 16))
    return img, ts, (w, h, words), missing


def playfield_from_tiles(ts, w, h, words, sx, sy, width_px):
    """256x160 rows of colour indices for scroll (sx,sy) with x wrap."""
    rows = []
    for y in range(160):
        wy = (sy + y)
        ty, py = wy // 16, wy % 16
        row = []
        for x in range(256):
            wx = (sx + x) % width_px
            tx, px = wx // 16, wx % 16
            t = words[ty * w + tx] & 0x3ff if 0 <= ty < h else 0
            row.append(ts["tiles"][t][py][px] if t < ts["n"] else 0)
        rows.append(row)
    return rows


def cmd_atlas():
    for i in (0, 2, 3, 4, 5, 6, 7):
        ts = load_tileset("T%d" % i)
        for p in (0, 1):
            atlas(ts, p).save(os.path.join(PNG, "tiles_T%d_pal%s.png" % (i, "AB"[p])))
        print("T%d: %d tiles" % (i, ts["n"]))


def cmd_level(ns):
    for n in ns:
        img, ts, (w, h, words), missing = render_level(n)
        p = os.path.join(PNG, "level_%d_map.png" % n)
        img.save(p)
        used = sorted(set(x & 0x3ff for x in words))
        print("level %d: %dx%d tiles -> %s ; tileset %s (%d tiles), max index used %d, indices >= bank size: %s" %
              (n, w, h, p, ts["name"], ts["n"], max(used), sorted(missing)[:20]))


def ram_val(ram, a, size=2):
    return int.from_bytes(ram[a:a + size], "big")


def check_snap(name, verbose=True, draw=False):
    """draw=True: score the *draw* buffer ($c31a) instead of the displayed one; use it for
    snapshots taken at the page-flip entry $aad8, where the finished frame is still the draw buffer
    and the scroll variables belong to it."""
    rows, palw, base, ram = snap_screen(name)
    if draw:
        base = int.from_bytes(ram[0xc31a:0xc31e], "big")
        rows = screen_indices(ram, base)
    lvl = ram_val(ram, 0x17846)
    sx, sy, ww = ram_val(ram, 0x1efec), ram_val(ram, 0x1efee), ram_val(ram, 0x1effe)
    ts = load_tileset(LEVEL_TSET[lvl])
    w, h, words = load_map(lvl)
    pf = playfield_from_tiles(ts, w, h, words, sx, sy, ww)
    # live playfield: window at screen (32,20)
    cell_ok = cell_tot = 0
    px_ok = 0
    for cy in range(10):
        for cx in range(16):
            ok = True
            for y in range(16):
                for x in range(16):
                    a = rows[20 + cy * 16 + y][32 + cx * 16 + x]
                    b = pf[cy * 16 + y][cx * 16 + x]
                    if a == b:
                        px_ok += 1
                    else:
                        ok = False
            cell_tot += 1
            cell_ok += ok
    if verbose:
        print("%s: level %d tileset %s scroll=(%d,%d) width=%d  pixels %d/%d (%.2f%%)  16x16 cells exactly equal %d/%d" %
              (name, lvl, ts["name"], sx, sy, ww, px_ok, 160 * 256, 100.0 * px_ok / (160 * 256), cell_ok, cell_tot))
    return px_ok, cell_ok, cell_tot, (lvl, sx, sy)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "atlas":
        cmd_atlas()
    elif cmd == "level":
        cmd_level([int(a) for a in sys.argv[2:]] or range(8))
    elif cmd == "check":
        draw = "--draw" in sys.argv
        for s in [a for a in sys.argv[2:] if not a.startswith("--")] or ["play_start.snap"]:
            check_snap(s, draw=draw)


def diff_image(name, out_path, draw=True):
    """live playfield with every pixel that differs from the tile render painted red."""
    rows, palw, base, ram = snap_screen(name)
    if draw:
        base = int.from_bytes(ram[0xc31a:0xc31e], "big")
        rows = screen_indices(ram, base)
    lvl = ram_val(ram, 0x17846)
    sx, sy, ww = ram_val(ram, 0x1efec), ram_val(ram, 0x1efee), ram_val(ram, 0x1effe)
    ts = load_tileset(LEVEL_TSET[lvl])
    w, h, words = load_map(lvl)
    pf = playfield_from_tiles(ts, w, h, words, sx, sy, ww)
    img = Image.new("RGB", (320, 200), (0, 0, 0))
    px = img.load()
    pal = palette_rgb(palw)
    for y in range(200):
        for x in range(320):
            px[x, y] = pal[rows[y][x]]
    for y in range(160):
        for x in range(256):
            if rows[20 + y][32 + x] != pf[y][x]:
                px[32 + x, 20 + y] = (255, 0, 0)
    img.save(out_path)

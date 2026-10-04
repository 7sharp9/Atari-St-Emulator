"""sprites.py - Black Tiger sprite banks (BTMAN hero bank, BTSPR enemy/object banks).

Bank layout (read from the actor draw routine $e19e..$e75c and the piece dispatcher $ed4c):
  +0  word H          rows per sprite piece (every frame of the bank has this height)
  +2  word animoff    offset of the animation table
  anim entry, 10 bytes at animoff + state*10 (state = actor byte 1):
     +0 word  offset of this animation's frame list (words)
     +2 byte  frame count      +3 sbyte x displacement  +4 sbyte y displacement
     +5 byte  width code (1..8) +6 byte trigger frame (ff = none)
     +7 byte  overlay kind (0 none) +8 word overlay record offset
  frame list: one word per frame = offset (from the bank start) of the frame's pixel data.
  pixel data: width code -> pieces left to right; a 32 px piece is H rows x 16 bytes (four longs,
  plane0..plane3, drawn by trap #3 fn4 $a86c); a 16 px piece is H rows x 8 bytes (four plane words,
  ST interleaved, fn3 $a6fa).  Colour index 0 is transparent (mask = NOT(p0|p1|p2|p3)).
  code: 1=[16] 2=[32] 3=[32,16] 4=[32,32] 5=[32,32,16] 6,7=[32,32,32] 8=[32,32,32,32]
"""
import os
import sys

from bt_common import *  # noqa

PIECES = {1: [16], 2: [32], 3: [32, 16], 4: [32, 32], 5: [32, 32, 16], 6: [32, 32, 32], 7: [32, 32, 32],
          8: [32, 32, 32, 32]}


def piece_bytes(code, H):
    return sum(H * (16 if p == 32 else 8) for p in PIECES[code])


def decode_frame(buf, off, code, H):
    """returns rows (H lists of indices) of width sum(pieces); None if outside buffer"""
    pieces = PIECES[code]
    need = piece_bytes(code, H)
    if off < 0 or off + need > len(buf):
        return None
    cols = []
    o = off
    for p in pieces:
        if p == 32:
            cols.append(decode_lin32(buf, o, H))
            o += H * 16
        else:
            cols.append(decode_st16(buf, o, H))
            o += H * 8
    return [sum((c[y] for c in cols), []) for y in range(H)]


def parse_bank(buf, base):
    """parse one bank at `base` of buf. returns dict(H, anims=[...]) ; anims have frames offsets."""
    H = w16(buf, base)
    ao = w16(buf, base + 2)
    first = None
    anims = []
    i = 0
    while True:
        o = base + ao + i * 10
        w0 = w16(buf, o)
        if first is None or w0 < first:
            first = w0
        if ao + i * 10 + 10 > first:
            break
        anims.append(dict(listoff=w0, n=buf[o + 2], dx=(buf[o + 3] ^ 0x80) - 0x80, dy=(buf[o + 4] ^ 0x80) - 0x80,
                          code=buf[o + 5], trig=buf[o + 6], ovk=buf[o + 7], ovoff=w16(buf, o + 8)))
        i += 1
    for a in anims:
        a["frames"] = [w16(buf, base + a["listoff"] + 2 * k) for k in range(a["n"])]
    return dict(H=H, ao=ao, anims=anims, base=base)


if __name__ == "__main__":
    d = read_file("BTMAN")
    b = parse_bank(d, 0)
    print(b["H"], len(b["anims"]))
    for k, a in enumerate(b["anims"]):
        print(k, {x: (hex(y) if isinstance(y, int) else [hex(z) for z in y]) for x, y in a.items() if x != "listoff"})


def bank_sheet(buf, base, pal, name, cols=12, scale=2, size=None):
    """sheet of every distinct frame of a bank; returns (image, frames list)"""
    b = parse_bank(buf, base)
    H = b["H"]
    frames = []
    seen = set()
    for ai, a in enumerate(b["anims"]):
        for fi, off in enumerate(a["frames"]):
            key = (off, a["code"])
            if key in seen:
                continue
            seen.add(key)
            rows = decode_frame(buf, base + off, a["code"], H)
            frames.append((ai, fi, off, a["code"], rows))
    return b, frames


def sheet_image(frames, pal, cols=8, scale=2, label=False):
    if not frames:
        return None
    cw = max((len(f[4][0]) for f in frames if f[4]), default=16) + 2
    ch = max((len(f[4]) for f in frames if f[4]), default=16) + 2
    n = len(frames)
    rows = (n + cols - 1) // cols
    img = Image.new("RGBA", (cols * cw, rows * ch), (40, 0, 40, 255))
    for i, (ai, fi, off, code, px) in enumerate(frames):
        if px is None:
            continue
        im = indexed_image(px, pal, transparent0=True)
        img.alpha_composite(im, ((i % cols) * cw + 1, (i // cols) * ch + 1))
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def mirror(rows):
    return [r[::-1] for r in rows]


def actor_frame(ram, a, btman, btspr):
    """(rows, H, code, anim) for the actor record at address a, using the files' banks."""
    t = ram[a]
    if t == 0:
        return None
    if t & 0x80:
        buf, base = btman, 0
    else:
        offs = l32(btspr, 4 * (t - 1))
        buf, base = btspr, offs
        if offs == 0 or offs >= len(btspr):
            return None
    b = parse_bank(buf, base)
    st, fr = ram[a + 1], ram[a + 2]
    if st >= len(b["anims"]):
        return None
    an = b["anims"][st]
    if fr >= len(an["frames"]):
        return None
    rows = decode_frame(buf, base + an["frames"][fr], an["code"], b["H"])
    return rows, b["H"], an["code"], an


def check_actors(name, verbose=True):
    """Draw every live actor over the tile render and compare with the draw buffer."""
    from tiles import load_tileset, load_map, playfield_from_tiles, LEVEL_TSET
    ram = load_snap(name)
    base = l32(ram, 0xc31a)
    scr = screen_indices(ram, base)
    lvl = w16(ram, 0x17846)
    sx, sy, ww = w16(ram, 0x1efec), w16(ram, 0x1efee), w16(ram, 0x1effe)
    ts = load_tileset(LEVEL_TSET[lvl])
    w, h, words = load_map(lvl)
    pf = playfield_from_tiles(ts, w, h, words, sx, sy, ww)
    btman, btspr = read_file("BTMAN"), read_file("BTSPR")
    res = []
    for i in range(0xb3):
        a = 0x1f010 + i * 16
        if ram[a] == 0:
            continue
        r = actor_frame(ram, a, btman, btspr)
        if r is None:
            continue
        rows, H, code, an = r
        x, y = w16(ram, a + 4), w16(ram, a + 6)
        dx = (x - sx) % ww
        if dx > ww // 2:
            dx -= ww
        px0 = dx - code * 8
        py0 = y - sy - H
        if px0 + len(rows[0]) <= 0 or px0 >= 256 or py0 + H <= 0 or py0 >= 160:
            continue
        best = {}
        for flip in (0, 1):
            rr = mirror(rows) if flip else rows
            tot = ok = 0
            for yy in range(H):
                for xx in range(len(rr[0])):
                    c = rr[yy][xx]
                    X, Y = px0 + xx, py0 + yy
                    if c == 0 or not (0 <= X < 256 and 0 <= Y < 160):
                        continue
                    tot += 1
                    ok += scr[20 + Y][32 + X] == c
            best[flip] = (ok, tot)
        res.append((a, ram[a], ram[a + 1], ram[a + 2], ram[a + 3], x, y, best))
        if verbose:
            print("  actor %05x type %02x state %d frame %d facing %d at (%d,%d): as-stored %d/%d  mirrored %d/%d" %
                  (a, ram[a], ram[a + 1], ram[a + 2], ram[a + 3], x, y, best[0][0], best[0][1], best[1][0], best[1][1]))
    return res


def search_actor(name, addr, frames=(0, -1), rng=12, flips=(0, 1), ram=None):
    """slide the actor's sprite around its nominal position; return best (ok, tot, frame_delta, dx, dy, flip)."""
    from tiles import load_tileset, load_map, playfield_from_tiles, LEVEL_TSET
    ram = ram or load_snap(name)
    base = l32(ram, 0xc31a)
    scr = screen_indices(ram, base)
    btman, btspr = read_file("BTMAN"), read_file("BTSPR")
    t = ram[addr]
    if t & 0x80:
        buf, bb = btman, 0
    else:
        buf, bb = btspr, l32(btspr, 4 * (t - 1))
    b = parse_bank(buf, bb)
    an = b["anims"][ram[addr + 1]]
    H, code = b["H"], an["code"]
    sx, sy, ww = w16(ram, 0x1efec), w16(ram, 0x1efee), w16(ram, 0x1effe)
    x, y = w16(ram, addr + 4), w16(ram, addr + 6)
    dx0 = (x - sx) % ww
    if dx0 > ww // 2:
        dx0 -= ww
    px0, py0 = dx0 - code * 8, y - sy - H
    best = (-1, 0, 0, 0, 0, 0)
    for fd in frames:
        f = ram[addr + 2] + fd
        if not 0 <= f < len(an["frames"]):
            continue
        rows = decode_frame(buf, bb + an["frames"][f], code, H)
        for flip in flips:
            rr = mirror(rows) if flip else rows
            for ddx in range(-rng, rng + 1):
                for ddy in range(-rng, rng + 1):
                    tot = ok = 0
                    for yy in range(H):
                        Y = py0 + ddy + yy
                        if not 0 <= Y < 160:
                            continue
                        row = rr[yy]
                        srow = scr[20 + Y]
                        for xx, c in enumerate(row):
                            if c == 0:
                                continue
                            X = px0 + ddx + xx
                            if 0 <= X < 256:
                                tot += 1
                                ok += srow[32 + X] == c
                    if tot >= 20 and ok / tot > best[0] / max(best[1], 1):
                        best = (ok, tot, fd, ddx, ddy, flip)
    return best

#!/usr/bin/env python3
"""Dump everything the dither infographic needs from one settled PowerMonger RAM image.

Usage (from M68000/):  uv run python reversing/powermonger/py/dither_atlas.py [ram] [out.json]

Reads `tools/pm_render_ref.py` (the byte-exact port of the terrain pipeline), replays the
terrain walk with hooks on the triangle rasteriser, and writes:

  * the live pattern table ($2e000, 101 slots of 16x16 palette indices) and the three season
    sources inside it;
  * one record per triangle the game draws (cell, which plane supplied the colour byte, the
    raw byte, whether $ef62 forced 0x1c, the three screen vertices, visible pixel count);
  * a per-pixel triangle-id map and the game's own frame buffer for comparison.

It also proves two claims the page makes, and exits non-zero if either fails:
  1. the frame rebuilt from (triangle id -> colour byte) and the table alone equals the
     reference renderer's own frame pixel for pixel;
  2. the season fade (LCG walk over source pixels) reproduces pm74_late's live slots.
"""
import base64
import json
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../M68000
sys.path.insert(0, str(ROOT / "tools"))
import pm_render_ref as r                          # noqa: E402

W, H = r.W, r.H
NSLOT = 0x65                                        # slots 0x00..0x64 cover the live slots + 3 sources
SRC = {"summer": 0x2F, "spring": 0x41, "winter": 0x53}   # first slot of each 18-slot source
LIVE0, NLIVE = 0x1D, 18                             # live working copy: slots 0x1d..0x2e


def tile(dith, slot):
    """16 rows x 16 px of palette indices for one 128-byte slot."""
    out = []
    for y in range(16):
        a = slot * 128 + y * 8
        l0 = struct.unpack_from(">I", dith, a)[0]
        l1 = struct.unpack_from(">I", dith, a + 4)[0]
        row = []
        for x in range(16):
            b = 15 - x
            row.append(((l0 >> (16 + b)) & 1) | (((l0 >> b) & 1) << 1)
                       | (((l1 >> (16 + b)) & 1) << 2) | (((l1 >> b) & 1) << 3))
        out.append(row)
    return out


def hexrows(t):
    return "".join("%x" % v for row in t for v in row)


def fade(dith_live_from, dith_src, steps):
    """The $1abaa season fade: start from the table `dith_live_from` (live slots as bytes),
    copy `steps` LCG-chosen pixels from `dith_src`. Both are 18*128-byte slot blocks."""
    live = bytearray(dith_live_from)
    x = 0
    for _ in range(steps):
        x = (x * 0x24A1 + 0x24DF) & 0x1FFF
        if x == 0:
            break
        row, bit = x >> 4, x & 15
        if row < 0x120:
            for plane in range(4):
                o = row * 8 + plane * 2
                w_live = (live[o] << 8) | live[o + 1]
                w_src = (dith_src[o] << 8) | dith_src[o + 1]
                w_live = (w_live & ~(1 << bit)) | (w_src & (1 << bit))
                live[o], live[o + 1] = w_live >> 8, w_live & 0xFF
    return bytes(live)


def block(dith, first):
    return bytes(dith[first * 128:(first + NLIVE) * 128])


def build_scene(ram, name, title, extra_ticks=(), tick_adjust=0):
    """One settled frame -> the dict the page renders. `extra_ticks` are further RAM images of
    the same camera at the other water ticks; each must also reproduce from the table.
    `tick_adjust`: the compose buffer that `R["ref"]` reads was finished one tick before the RAM
    image was taken, so the frame it holds used `[$4bb3e] - 1` (-1 for captures of a water scene)."""
    R = r.load_ram(ram)
    ram_tick = R["tick"]
    R["tick"] = (R["tick"] + tick_adjust) & 3
    dith = R["dith"]
    planes, corners = R["planes"], R["corners"]
    cam_x, cam_y = R["cam"]
    assert ((R["yaw"] + 8) >> 5) & 6 == 6, "hooks below assume the quadrant-3 walk (yaw 0xe0-0xff)"

    # ---- hooks -----------------------------------------------------------------------
    tris = []                      # one dict per ef62_raster call, in draw order
    triid = bytearray(W * H)       # last triangle to paint each pixel
    cur = [0]
    real_ef62, real_dda, real_dith = r.ef62_raster, r._dda_walk, r.dither_index

    def ef62(idxbuf, cov, dith_, p0, p1, p2, colour, tick, **kw):
        tris.append(dict(raw=colour, verts=[list(map(int, p)) for p in (p0, p1, p2)],
                         cell=None, src=None, forced=False, final=None))
        cur[0] = len(tris)
        return real_ef62(idxbuf, cov, dith_, p0, p1, p2, colour, tick, **kw)

    def dda(idxbuf, cov, dith_, colour, *a, **kw):
        t = tris[cur[0] - 1]
        t["final"] = colour
        return real_dda(idxbuf, cov, dith_, colour, *a, **kw)

    def dith_hook(d, colour, y, x, phase_bias=0):
        triid[y * W + x] = cur[0]
        return real_dith(d, colour, y, x, phase_bias=phase_bias)

    r.ef62_raster, r._dda_walk, r.dither_index = ef62, dda, dith_hook
    idx = bytearray(W * H)
    cov = bytearray(W * H)
    mark = [0]

    def after_cell(row, col):
        for t in tris[mark[0]:]:
            t["cell"] = [cam_x + col, cam_y + row]
        mark[0] = len(tris)

    R["after_cell"] = after_cell
    r.walk_q3(idx, cov, R)
    r.ef62_raster, r._dda_walk, r.dither_index = real_ef62, real_dda, real_dith

    # ---- which plane fed each triangle (q3 call order, see walk_q3) ---------------------
    def packed(q):
        return (q[0] << 16) | (q[1] & 0xFFFF)

    i = 0
    for k in range(8):
        col = 7 - k
        for j in range(8):
            cx, cy = cam_x + col, cam_y + j
            C10, C01 = corners[(j, col + 1)], corners[(j + 1, col)]
            if not (planes["flg"](cx, cy) & 0x80):
                order = ("type", "height")
            elif packed(C01) <= packed(C10):
                order = ("height", "type")
            else:
                order = ("type", "height")
            for src in order:
                t = tris[i]
                t["src"] = src
                want = planes["typ" if src == "type" else "hgt"](cx, cy)
                assert t["raw"] == want and t["cell"] == [cx, cy], (i, t, want)
                i += 1
    assert i == len(tris) == 128

    tick = R["tick"]
    counts = Counter(triid)
    for n, t in enumerate(tris, 1):
        raw = t["raw"]
        after_tick = (raw + tick) & 0xFF if raw < 0x0C else raw
        t["tick_added"] = raw < 0x0C
        t["forced"] = t["final"] is not None and t["final"] == 0x1C and after_tick != 0x1C
        if t["final"] is None:
            t["final"] = after_tick                       # degenerate: never painted
        t["px"] = counts.get(n, 0)


    # ---- proof 1: rebuild the frame from triangle ids + table only ------------------------
    tb = {s: tile(dith, s) for s in range(NSLOT)}

    def colour_of(t, tk):
        return 0x1C if t["forced"] else (t["raw"] + tk) & 0xFF if t["raw"] < 0x0C else t["raw"]

    bad = drawn = 0
    for p in range(W * H):
        n = triid[p]
        if not n:
            continue
        drawn += 1
        y, x = divmod(p, W)
        if idx[p] != tb[colour_of(tris[n - 1], tick)][(y + R["phase_bias"] // 8) & 15][x & 15]:
            bad += 1
    assert bad == 0, f"{bad} pixels differ between the rebuilt frame and the reference renderer"

    ref = R["ref"]
    exact = sum(1 for p in range(W * H) if triid[p] and idx[p] == ref[p])
    print(f"[{name}] proof 1: {drawn} terrain pixels rebuilt from (triangle -> colour byte -> slot[(y + phase/8) & 15][x & 15]), "
          f"0 differ from pm_render_ref; {exact}/{drawn} = {100 * exact / drawn:.1f}% equal the game's own frame "
          f"(rest: sprites, unit markers)")

    # the same camera at the other water ticks: only water triangles may change
    tick_check = [dict(tick=tick, ram=ram.name, exact=exact, drawn=drawn)]
    for other in extra_ticks:
        R2 = r.load_ram(other)
        R2["tick"] = (R2["tick"] + tick_adjust) & 3
        assert R2["cam"] == R["cam"] and R2["yaw"] == R["yaw"]
        i2 = bytearray(W * H)
        c2 = bytearray(W * H)
        r.walk_q3(i2, c2, R2)
        t2 = tile_table(R2["dith"])
        bad2 = ex2 = 0
        for p in range(W * H):
            n = triid[p]
            if not n:
                continue
            y, x = divmod(p, W)
            if i2[p] != t2[colour_of(tris[n - 1], R2["tick"])][(y + R2["phase_bias"] // 8) & 15][x & 15]:
                bad2 += 1
            ex2 += i2[p] == R2["ref"][p]
        assert bad2 == 0
        tick_check.append(dict(tick=R2["tick"], phase=R2["phase_bias"], ram=other.name, exact=ex2, drawn=drawn))
        print(f"[{name}] tick {R2['tick']}: rebuilt frame equals the reference renderer (0 differ); "
              f"{ex2}/{drawn} = {100 * ex2 / drawn:.1f}% equal the game's frame")

    cells = [[cam_x + c, cam_y + rr, planes["typ"](cam_x + c, cam_y + rr),
              planes["hgt"](cam_x + c, cam_y + rr), planes["flg"](cam_x + c, cam_y + rr) >> 7]
             for rr in range(8) for c in range(8)]
    bycb = Counter()
    for t in tris:
        bycb[colour_of(t, tick)] += t["px"]
    print(f"[{name}] visible pixels by colour byte:", {hex(k): v for k, v in sorted(bycb.items())})
    print(f"[{name}] triangles by (src, forced):", dict(Counter((t["src"], t["forced"]) for t in tris)),
          f"; fully overdrawn: {sum(1 for t in tris if t['px'] == 0)}")

    return dict(
        name=name, title=title, source=ram.name, tick=tick, ram_tick=ram_tick, phase=R["phase_bias"], yaw=R["yaw"],
        cam=[cam_x, cam_y], season_word=(R["ram"][0x57FD0] << 8) | R["ram"][0x57FD1],
        slots=[hexrows(tb[s]) for s in range(NSLOT)], tris=tris, cells=cells, tick_check=tick_check,
        triid=base64.b64encode(bytes(triid)).decode(),
        ref=base64.b64encode(bytes(ref)).decode(),
    )


def tile_table(dith):
    return {s: tile(dith, s) for s in range(NSLOT)}


def fade_proof():
    """The season fade reproduces pm74_late's live slots (mid-fade, 485 ticks in)."""
    late = (ROOT / "scratchpad" / "pm74_late.ram").read_bytes()
    lb = late[struct.unpack_from(">I", late, 0xFF9E)[0]:][:0x4000]
    steps = 16 * ((late[0x57FEC] << 8) | late[0x57FEC + 1])
    got = fade(block(lb, SRC["winter"]), block(lb, SRC["spring"]), steps)
    want = block(lb, LIVE0)
    assert got == want, "season fade model does not reproduce pm74_late"
    print(f"fade proof: winter -> spring, {steps} LCG steps, equals pm74_late's live slots "
          f"{LIVE0:#x}..{LIVE0 + NLIVE - 1:#x} byte for byte ({len(want)} bytes)")
    return dict(steps=steps, ram="pm74_late.ram", live=base64.b64encode(want).decode(),
                blocks={k: base64.b64encode(block(lb, v)).decode() for k, v in SRC.items()})


def write_pngs(data, outdir):
    """dither_atlas.png: every slot 0x00..0x40 of the mission-1 table at 6x, labelled.
    dither_triangles.png: mission 1 as the game draws it, then coloured by colour byte, then by plane."""
    from PIL import Image, ImageDraw
    pal = [tuple(c) for c in data["palette"]]
    sc = data["scenes"][0]
    K, cols, top = 6, 11, 14
    n = 0x41
    rows = (n + cols - 1) // cols
    cell = 16 * K + 6
    im = Image.new("RGB", (cols * cell + 6, rows * (16 * K + top + 4) + 6), (246, 244, 238))
    d = ImageDraw.Draw(im)
    for s in range(n):
        ox, oy = 6 + (s % cols) * cell, 6 + (s // cols) * (16 * K + top + 4)
        d.text((ox, oy), f"0x{s:02x}", fill=(30, 29, 26))
        px = sc["slots"][s]
        for i, ch in enumerate(px):
            x, y = i % 16, i // 16
            d.rectangle([ox + x * K, oy + top + y * K, ox + x * K + K - 1, oy + top + y * K + K - 1], fill=pal[int(ch, 16)])
    im.save(outdir / "dither_atlas.png")

    W_, H_ = data["W"], data["H"]
    triid = base64.b64decode(sc["triid"])
    tick, phase = sc["tick"], sc["phase"]
    xs = [p % W_ for p in range(W_ * H_) if triid[p]]
    ys = [p // W_ for p in range(W_ * H_) if triid[p]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = x1 - x0 + 1, y1 - y0 + 1
    tiles = [[int(c, 16) for c in t] for t in sc["slots"]]
    cbs = sorted({0x1C if t["forced"] else t["raw"] for t in sc["tris"]})
    import colorsys
    def ramp(i, m):
        r_, g_, b_ = colorsys.hls_to_rgb((230 - 230 * i / max(m - 1, 1)) / 360, .52 if i % 2 else .58, .68)
        return int(r_ * 255), int(g_ * 255), int(b_ * 255)
    views = [Image.new("RGB", (w, h), (22, 21, 17)) for _ in range(3)]
    for p in range(W_ * H_):
        n_ = triid[p]
        if not n_:
            continue
        y, x = divmod(p, W_)
        t = sc["tris"][n_ - 1]
        c = 0x1C if t["forced"] else (t["raw"] + tick) & 255 if t["raw"] < 12 else t["raw"]
        views[0].putpixel((x - x0, y - y0), pal[tiles[c][(((y + phase // 8) & 15) << 4) | (x & 15)]])
        views[1].putpixel((x - x0, y - y0), ramp(cbs.index(c) if c in cbs else 0, len(cbs)))
        views[2].putpixel((x - x0, y - y0), (31, 95, 139) if t["src"] == "type" else (180, 70, 30))
    Z = 3
    sheet = Image.new("RGB", (3 * (w * Z + 8) + 8, h * Z + 16), (246, 244, 238))
    for i, v in enumerate(views):
        sheet.paste(v.resize((w * Z, h * Z), Image.NEAREST), (8 + i * (w * Z + 8), 8))
    sheet.save(outdir / "dither_triangles.png")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scratchpad" / "pm130" / "dither" / "dither_data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    sc = ROOT / "scratchpad"
    cap = sc / "pm121" / "cap"
    scenes = [
        build_scene(sc / "pm78_settle.ram", "mission1", "Mission 1, inland"),
        build_scene(sc / "pm122/agents/dissolve/nat2/k5_x1.ram", "coast", "Land 5, a coast", tick_adjust=-1),
    ]
    # four consecutive ticks of one coast camera: the water shimmer, rebuilt from the table at each
    series = build_scene(cap / "k5_22_0.ram", "series", "tick series", tick_adjust=-1,
                         extra_ticks=[cap / f"k5_22_{n}.ram" for n in (1, 2, 3)])
    assert all(c["exact"] / c["drawn"] > 0.99 for c in series["tick_check"]), series["tick_check"]
    pal = json.loads((ROOT / "reversing/powermonger/port/assets/palette.json").read_text())["palettes"][0]["rgb"]
    data = dict(W=W, H=H, palette=pal[:16], src_first=SRC, live0=LIVE0, nlive=NLIVE,
                scenes=scenes, tick_series=series["tick_check"], fade=fade_proof())
    out.write_text(json.dumps(data, separators=(",", ":")))
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    write_pngs(data, ROOT / "reversing" / "powermonger")
    tmpl = Path(__file__).with_name("dither_infographic.tmpl.html")
    if tmpl.exists():
        page = ROOT / "reversing" / "powermonger" / "dither_infographic.html"
        page.write_text(tmpl.read_text().replace("__DATA__", out.read_text()))
        print(f"wrote {page} ({page.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

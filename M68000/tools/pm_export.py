#!/usr/bin/env python3
"""
pm_export.py -- PowerMonger [cr Replicants] iso-renderer asset + constant export.

Reads a full 1 MiB RAM image of the running game (the game sits at its absolute
link addresses, base $1050) and writes everything the isometric terrain renderer
reads into  reversing/powermonger/port/assets/ , with a machine-readable
manifest.json giving one line of provenance per file (which address, which
routine reads it).

This is the 76th-pass precursor to porting the renderer to Godot/F#. The proof
that the export is complete is tools/pm_render_ref.py rebuilding a frame from
assets/ alone and diffing it against reference/isoframe.png.

Inputs
------
  --ram   scratchpad/pm74_late.ram      settled iso view, PC $124c0 (default)
  --snap  scratchpad/pm74_late.snap     alternative: extract the RAM from a .snap
  --frame scratchpad/pm76_fr/f000100.bin a frame-dump record for the live palette
  --fight scratchpad/pm73_fight.ram     optional: pull combat-only sprite frames
  --out   reversing/powermonger/port/assets

Everything here is READ-ONLY analysis. No emulator behaviour changes.

Address map (relocated game image, base $1050) -- see reversing/powermonger/*.md
  $438ee  g_terrain        type plane +0, height plane -8257, flag plane +8257
  $3f86c  g_cell_control    per-cell height the projector ($fec6) actually reads
  $2e000  dither table      base = long at $ff9e; cyclic 16-bit bitplane masks
  $33000  g_minisprite_sheet 0x37 (55) bytes/frame, 11 rows x 5 bytes, 1bpp+mask
  $1675a  t_heading_frame   16 bytes, heading 0..15 -> sprite frame, $ff = skip
  $ff96/$ff98/$ff9a/$ff9c   horizon / eye distance / yaw / zoom scale
  $fdea..$fe02             13 zoom-geometry constants ($fe04 output)
  $1400a  sin/cos table     Q15, used by $12d56
  $13f8a  yaw rotation table (see note in manifest)
  $51b66  g_object_records  511 x 50 bytes
  $4f916  g_settlement_table 18 bytes each
  $4e514  g_leader_table    32 bytes each
"""

import argparse
import json
import struct
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# RAM accessor
# ---------------------------------------------------------------------------


class Ram:
    def __init__(self, data: bytes):
        self.d = data
        if len(data) < 0x100000:
            print(f"warning: RAM image is {len(data)} bytes, expected >= 0x100000",
                  file=sys.stderr)

    def u8(self, a):
        return self.d[a]

    def s8(self, a):
        v = self.d[a]
        return v - 256 if v >= 128 else v

    def u16(self, a):
        return struct.unpack_from(">H", self.d, a)[0]

    def s16(self, a):
        return struct.unpack_from(">h", self.d, a)[0]

    def u32(self, a):
        return struct.unpack_from(">I", self.d, a)[0]

    def blk(self, a, n):
        return self.d[a:a + n]


def ram_from_snap(path: Path) -> bytes:
    """A68S snapshot: skip 5 + 19*4 + 2, read a 4-byte LE length, then the image."""
    s = path.read_bytes()
    off = 5 + 19 * 4 + 2
    ln = struct.unpack_from("<I", s, off)[0]
    return s[off + 4:off + 4 + ln]


# ---------------------------------------------------------------------------
# tiny PNG writer (no numpy/PIL dependency for the core; PIL used only if present
# for the optional upscaled previews)
# ---------------------------------------------------------------------------

import zlib


def write_png(path: Path, width: int, height: int, rgb_rows):
    """rgb_rows: iterable of `width` (r,g,b) tuples per row, `height` rows."""
    raw = bytearray()
    for row in rgb_rows:
        raw.append(0)  # filter: none
        for (r, g, b) in row:
            raw += bytes((r, g, b))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def write_gray_png(path: Path, width: int, height: int, values, scale=1):
    """values: flat list of 0..255, row-major."""
    def rows():
        for y in range(height):
            yield [(v, v, v) for v in
                   (values[y * width + x] for x in range(width))]
    if scale == 1:
        write_png(path, width, height, rows())
    else:
        big = []
        base = list(rows())
        for r in base:
            rr = []
            for px in r:
                rr += [px] * scale
            for _ in range(scale):
                big.append(rr)
        write_png(path, width * scale, height * scale, big)


# ---------------------------------------------------------------------------
# ST 3-bit-per-gun palette
# ---------------------------------------------------------------------------


def stf_rgb(word):
    r = (word >> 8) & 7
    g = (word >> 4) & 7
    b = word & 7
    # STF: 3 bits, 0..7 -> 0..255. (STE 4-bit ordering not used by this build.)
    return (r * 255 // 7, g * 255 // 7, b * 255 // 7)


# ---------------------------------------------------------------------------
# terrain grid geometry
# ---------------------------------------------------------------------------

GRID_STRIDE = 64          # cells per row in every plane ($ffa6 seeder: D2<<6 + D1)
GRID_ROWS = 128           # 6-bit x (0..63), 7-bit y (0..127) -> 64*128 = 8192
TERRAIN = 0x438ee
CTRL = 0x3f86c
HEIGHT_OFF = -8257
FLAG_OFF = 8257
WATER_LEVEL = 0x0c        # $f898: cmpi.w #$c,D3 ; bge ... ; add.w tick&3
SEA_STATIC_BIT = 0x80     # flag plane bit 7: corner did not move -> skip fill


def export_terrain(ram: Ram, out: Path, man: list):
    n = GRID_STRIDE * GRID_ROWS
    typ = ram.blk(TERRAIN, n)
    hgt = ram.blk(TERRAIN + HEIGHT_OFF, n)
    flg = ram.blk(TERRAIN + FLAG_OFF, n)
    ctl = ram.blk(CTRL, n)

    # terrain.bin: 4 interleaved planes, cell-major, row stride 64.
    #   byte 0 = type, 1 = height ($438ee planes), 2 = flag, 3 = control ($3f86c)
    packed = bytearray(n * 4)
    for i in range(n):
        packed[i * 4 + 0] = typ[i]
        packed[i * 4 + 1] = hgt[i]
        packed[i * 4 + 2] = flg[i]
        packed[i * 4 + 3] = ctl[i]
    (out / "terrain.bin").write_bytes(packed)

    write_gray_png(out / "terrain_height.png", GRID_STRIDE, GRID_ROWS, hgt, scale=4)
    write_gray_png(out / "terrain_type.png", GRID_STRIDE, GRID_ROWS, typ, scale=4)
    write_gray_png(out / "terrain_control.png", GRID_STRIDE, GRID_ROWS, ctl, scale=4)

    # bounding box of the mission-1 island (non-zero control cells)
    xs = [i % GRID_STRIDE for i in range(n) if ctl[i]]
    ys = [i // GRID_STRIDE for i in range(n) if ctl[i]]
    bbox = [min(xs), min(ys), max(xs), max(ys)] if xs else None

    man.append({
        "file": "terrain.bin",
        "bytes": len(packed),
        "provenance": (
            f"$438ee type plane (+0), $438ee-8257 height plane, $438ee+8257 flag "
            f"plane, $3f86c control/height plane. Read by pm_render_terrain ($f898) "
            f"for colour and pm_project_grid ($fec6/$fecc) for geometry "
            f"(the projector reads $3f86c, entity sampling reads $438ee)."),
        "format": (
            f"{GRID_STRIDE} x {GRID_ROWS} cells, row-major, stride {GRID_STRIDE}. "
            "4 bytes/cell: [0]=type [1]=height [2]=flag [3]=control. "
            f"water: height < {WATER_LEVEL} (0x0c); "
            f"static-sea skip: flag & 0x{SEA_STATIC_BIT:02x} (corner unmoved this frame)."),
        "island_bbox_xyxy": bbox,
    })
    for name, note in (
        ("terrain_height.png", "height plane, 4x nearest, grey = raw byte"),
        ("terrain_type.png", "type plane (== palette colour index for the type triangle)"),
        ("terrain_control.png", "$3f86c control plane (projector height source)"),
    ):
        man.append({"file": name, "provenance": note,
                    "format": f"{GRID_STRIDE*4} x {GRID_ROWS*4} grayscale PNG"})
    return typ, hgt, flg, ctl, bbox


# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------


def export_palette(frame_path: Path, out: Path, man: list):
    b = frame_path.read_bytes()
    rez = b[0]
    rr = b[1 + 32000:]
    recs = [rr[i * 34:i * 34 + 34] for i in range(200)]
    rows = []
    unique = {}
    for y, r in enumerate(recs):
        base = (r[0] << 8) | r[1]
        words = [struct.unpack_from(">H", r, 2 + i * 2)[0] for i in range(16)]
        rgb = [stf_rgb(w) for w in words]
        rows.append({"y": y, "screen_base": base,
                     "shifter_words": [f"{w:04x}" for w in words],
                     "rgb": rgb})
        key = tuple(words)
        unique.setdefault(key, []).append(y)

    pal = {
        "rez": rez,
        "note": (
            "PowerMonger writes the shifter palette directly to $FFFF8240 (no "
            "XBIOS Setpalette). This capture is per-scanline (row-record from an "
            "ATARI_FRAME_DIR dump) so a mid-frame raster split would show as more "
            "than one distinct palette below."),
        "distinct_palettes": len(unique),
        "iso_view_uses_one_palette": len(unique) == 1,
        "palettes": [
            {"rows": ys, "shifter_words": [f"{w:04x}" for w in key],
             "rgb": [stf_rgb(w) for w in key]}
            for key, ys in unique.items()
        ],
        # per-row is only interesting when there is a mid-frame raster split
        "per_row": rows if len(unique) > 1 else "identical every row (see palettes[0])",
    }
    (out / "palette.json").write_text(json.dumps(pal, indent=1))

    # a 16x1 swatch strip of the dominant palette, 16x upscaled
    dom = max(unique.items(), key=lambda kv: len(kv[1]))[0]
    strip = [[stf_rgb(w) for w in dom] * 1]
    big = []
    for px in strip[0]:
        pass
    rows_img = []
    for _ in range(16):
        rr2 = []
        for w in dom:
            rr2 += [stf_rgb(w)] * 16
        rows_img.append(rr2)
    write_png(out / "palette.png", 16 * 16, 16, rows_img)

    man.append({
        "file": "palette.json",
        "provenance": (
            f"per-scanline shifter palette captured from {frame_path.name} "
            "(ATARI_FRAME_DIR row-records). Written by the game to $FFFF8240."),
        "format": ("distinct_palettes + per_row[200]. Each colour is a $0RGB "
                   "shifter word; rgb[] is the 3-bit-per-gun expansion (x*255/7)."),
        "distinct_palettes": len(unique),
    })
    man.append({"file": "palette.png",
                "provenance": "dominant palette, 16 indices x 16px swatches",
                "format": "256 x 16 RGB PNG"})
    return dom  # tuple of 16 shifter words


# ---------------------------------------------------------------------------
# dither table
# ---------------------------------------------------------------------------


def export_dither(ram: Ram, out: Path, man: list):
    base = ram.u32(0xff9e)
    # 77th-pass correction. The fill ($e3e6..$e4de, aligned disasm) computes its
    # read pointer as
    #     A5 = base + colourByte*128 + (topY & 15)*8            [byte address]
    # and then advances +4 bytes per scanline while each 16-px screen cluster
    # consumes 8 bytes (two 32-bit longs: long0 = {plane0:plane1},
    # long1 = {plane2:plane3}).  colourByte is the raw terrain byte (max 62 on
    # mission 1) plus the water shimmer (+[$4bb3e]&3), so the deepest base offset
    # is ~ (62+2)*128 = 8192, plus (15*8) + a ~50-line triangle's 200 bytes of
    # roll.  Dump 16 KiB so the whole addressable span is covered.
    LEN = 0x4000
    tbl = ram.blk(base, LEN)
    (out / "dither.bin").write_bytes(tbl)

    words = struct.unpack(f">{LEN // 2}H", tbl)
    # render as 4 stacked 1bpp planes, 16 px wide, LEN/8 scanlines
    scan = LEN // 8
    planes_img = []
    for p in range(4):
        for row in range(scan):
            w = words[row * 4 + p]
            planes_img.append([(255, 255, 255) if (w >> (15 - c)) & 1 else (0, 0, 0)
                               for c in range(16)])
    write_png(out / "dither.png", 16, 4 * scan, planes_img)

    # the table is indexed absolutely (colourByte*128), not cyclically -- there is
    # no meaningful global period. Report the per-colourByte slot size instead.
    period = 128

    man.append({
        "file": "dither.bin",
        "provenance": (
            f"4bpp pattern table at ${base:x} (= long at $ff9e). Read by the span "
            "fill ($e3e6 setup, $e4de/$e4a6 inner loops -- 77th-pass aligned "
            "disasm). Per triangle: A5 = base + colourByte*128 + (topY & 15)*8 "
            "(byte address). Per 16-px screen cluster the fill reads two 32-bit "
            "big-endian longs: long0 = {plane0<<16 | plane1}, long1 at A5+4 = "
            "{plane2<<16 | plane3}; pixel index = plane0.bit | plane1.bit<<1 | "
            "plane2.bit<<2 | plane3.bit<<3 with bit = 15-(screenX & 15). A5 then "
            "advances +4 bytes/scanline (the roll) and +8 bytes/cluster."),
        "format": (f"{LEN} bytes dumped ({LEN//128} colourByte slots of 128 bytes "
                   "= 16 eight-byte sub-patterns each; sub-pattern picked by "
                   "(topY & 15), rolled +4 B/line). Big-endian. colourByte->index: "
                   "0x08-0x0b water (14/15), 0x18-0x1c rock (1-3/6), 0x24-0x2c "
                   "grass ramp (13/12/11), 0x3e brightest (9/10/11)."),
        "table_base_addr": f"${base:x}",
        "water_shimmer_add": ram.u32(0x4bb3e) & 3,
    })
    man.append({"file": "dither.png",
                "provenance": "dither.bin as 4 stacked 1bpp planes",
                "format": f"16 x {4*scan} PNG (4 planes stacked vertically)"})
    return base, tbl


# ---------------------------------------------------------------------------
# mini-sprite sheet
# ---------------------------------------------------------------------------

SPRITE_SHEET = 0x33000
SPRITE_FRAME_BYTES = 0x37   # 55 = 11 rows x 5 bytes
SPRITE_ROWS = 11
SPRITE_W = 8

# Two more sprite sheets besides $33000 (all 4-bitplane + AND-mask, MSB-first):
#   $312a0  16w x 16h  -- 0xa0 (160) B/frame, 10 B/row [mask,p0,p1,p2,p3] words.
#           cat 9 ($11c36->$1225c), cat 15 / cat 1 ($1198a/$117d8->$119d4).
#           Cell-CENTRED (position = (C00+C10+C01+C11)>>2, +0x38 X / -8 Y).
#   $37c7c  32w x 24h  -- 0x1e0 (480) B/frame, 20 B/row = 2x 16px groups of
#           [mask,p0,p1,p2,p3] words. cat 2 ($1168c->$1227c/$124a8). Also
#           cell-centred. (87th: strides + row counts from $1227c/$1225c/$124a8
#           disasm + a live cat-2 trace.)
SPRITE2_SHEET = 0x37c7c
SPRITE2_FRAME_BYTES = 0x1e0
SPRITE3_SHEET = 0x312a0
SPRITE3_FRAME_BYTES = 0xa0

# 87th pass -- the $115e0 per-cell entity dispatch, ripped from the jump tables in
# RAM ($1162e prepare, $1165c blit -- SPEC.md said $1165a, off by 2) plus a
# disassembly of each per-category "prepare" handler and a live trace of the men
# path (cat 0) from scratchpad/pm78_settle.snap. Every frame-index formula below
# is the D2 value handed to the blitter. `[$xxxx]` = a live word read; byte N =
# object record ($51b66, stride 50) field N. See SPEC.md section 6.
#
# Shared by every $33000-sheet prepare handler: the entity's screen position is a
# bilinear lerp of the cell's 4 projected corners (from the $3f364 buffer, packed
# (screenX<<16)|screenY) by (fx,fy) = (byte8 & 0xff, byte10 & 0xff), then
# screenX += 0x3c, screenY -= 8  ($11f1a, verified: a0 at entry points at
# &$3f364[cellRow*64 + cellCol*4], the cell's TL corner).
SPRITE_TRIGGERS = {
    "note": (
        "PowerMonger per-cell entity (sprite) dispatch. $115e0 (pm_draw_cell_"
        "entities) is called INLINE per cell from the terrain grid-walk handler "
        "(q3: $fdbc), right after that cell's two triangles, in far->near "
        "painter's order -- so no sprite floats over a hill it is behind. This is "
        "the path that draws the little men / animals / trees / buildings ON the "
        "iso terrain. $16738->$e6ee is a SEPARATE pass ($165b2, selected-group "
        "marker + HUD glyphs), positioned by raw cell coordinate + a fixed "
        "per-frame descriptor X -- NOT the iso entities. (87th live trace, "
        "scratchpad/pm78_settle.snap.)"),
    "dispatch": {
        "record_category_field": 6,
        "prepare_table_addr": "$1162e",
        "blit_table_addr": "$1165c",
        "prepare_target": "$1162e + word[$1162e + category]",
        "blit_target": "$1165c + word[$1165c + category]  (word 0 => handler "
                       "blits inline or draws nothing)",
    },
    "position": {
        "sub_cell": {
            "routine": "$11f1a",
            "used_by_categories": [0, 3, 4, 5, 6, 7, 10, 11, 13, 14],
            "corners": "a0 = &$3f364[cellRow*64 + cellCol*4]; C00=(a0) C10=4(a0) "
                       "C01=64(a0) C11=68(a0); each packed (screenX<<16)|screenY",
            "frac": "(fx, fy) = (record[8] & 0xff, record[10] & 0xff)",
            "formula": "pos = lerp(lerp(C00,C10,fx/256), lerp(C01,C11,fx/256), "
                       "fy/256); screenX = pos.x + 0x3c; screenY = pos.y - 8",
        },
        "centred": {
            "routine": "$1182a / $1198a head",
            "used_by_categories": [1, 2, 8, 9, 15],
            "formula": "pos = (C00 + C10 + C01 + C11) >> 2  (packed, so both "
                       "halves); screenX = pos.x + 0x38; screenY = pos.y - 8",
        },
    },
    "armed_variant": (
        "cat 0 (and the melee branch): D2 += 0x40 iff record[7] bit 4 is set AND "
        "(record[7] bit 7 is clear OR the unit's group [$51538 + record[42], "
        "word -48] == [$57ffe] the selected group). Frames 0x40..0x7f are that "
        "variant of frames 0x00..0x3f. (87th: live man had record[7]=0x10 => "
        "frame 64.)"),
    "categories": {
        "0": {"name": "man / troop", "prepare": "$11c8a",
              "blit": "$11f78 -> $11f82", "sheet": "$33000", "frame_bytes": 55,
              "frame": "(record[5]-1)*16 + (((record[17] + [$ff9a] + 0x10) & "
                       "0xff) >> 5)*2   [+armed_variant, +1 if [$4bb41]&1 anim]. "
                       "record[5]=faction (blocks of 16), record[17]=heading, "
                       "[$ff9a]=camera yaw => facing is YAW-RELATIVE (8 steps). "
                       "record[33]==8 && record[7]==1 also blits a small overlay "
                       "($11f82, table $11e40); record[44]>=0xe blits a weapon "
                       "overlay ($11ebc -> $12258, (record[44]-0xe)*4 + 0x1b + "
                       "(masked>>1)). MELEE (record[31] in {0x32,0x34}): base "
                       "0x80, D2 = weapon*8 + (faction-1)*4 + facing2*2 + anim "
                       "[+armed], facing2 = ((heading + [$ff9a] + 0x40)&0xff)>>7. "
                       "record[31]==0x46 = dying (counter side effect only).",
              "verified": "live trace + full disasm"},
        "1": {"name": "structure? (shares cat 15 path)", "prepare": "$117d8",
              "blit": "$119d4 (centred, via $119b2)", "sheet": "$312a0",
              "frame_bytes": 160,
              "frame": "if record[7]==0x0a: frame from record[16]/7 and "
                       "record[12]/10 (a directional pick, $117f8..$11818); else "
                       "$1181c branch (not ripped). D2 = D4.",
              "verified": "partial disasm"},
        "2": {"name": "building / tree", "prepare": "$1168c",
              "blit": "inline via $1227c/$124a8 (centred)", "sheet": "$37c7c",
              "frame_bytes": 480, "sprite_wh": [32, 24], "frame_count": 28,
              "frame": "record[7] + word[$57fd0-relative] offset "
                       "($116c6..$116d0); special-cases record[7] in {0x0d,0x0e}. "
                       "Full offset table not ripped. Sheet = 28 clean frames "
                       "(8 house types, tower, well, ruins, bell, 9 tree types, "
                       "duck); frame 28+ is a different geometry/sheet.",
              "verified": "live trace (stride+wh) + partial disasm + visual"},
        "3": {"name": "settlement marker (== cat 12)", "prepare": "$117b0",
              "blit": "$11f78", "sheet": "$33000", "frame_bytes": 55,
              "frame": "record[7] + 0x100; if == 0x112 then + ([$57fec] & 3) "
                       "(4-frame animation). Frames 0x100+ = number / flag "
                       "glyphs.",
              "verified": "disasm"},
        "4": {"name": "animal (sheep)", "prepare": "$11a86", "blit": "$11f78",
              "sheet": "$33000", "frame_bytes": 55,
              "frame": "(((record[14] + [$ff9a]) & 0xff) >> 5)*2 + 0x117   "
                       "[+1 if [$4bb41]&1]. record[14]=heading, yaw-relative "
                       "=> 16 frames at base 0x117 (8 facings x {a,b}).",
              "verified": "disasm"},
        "5": {"name": "effect / decoration", "prepare": "$11772",
              "blit": "$11f78 (x2)", "sheet": "$33000", "frame_bytes": 55,
              "frame": "if record[33]: ((record[33]-8) >> 1) + 0x10f  (blit); "
                       "then if record[44]: (record[44] >> 1) + 0x142  (blit)",
              "verified": "disasm"},
        "6": {"name": "boat / floating?", "prepare": "$11bbc",
              "blit": "$11f78 (x2)", "sheet": "$33000", "frame_bytes": 55,
              "frame": "underlay (0x103 - record[5]) then main (record[32] + "
                       "0x100); screenY -= (0xa0 - record[18])",
              "verified": "disasm"},
        "7": {"name": "flag / banner?", "prepare": "$11bf4", "blit": "$11f78",
              "sheet": "$33000", "frame_bytes": 55,
              "frame": "record[5] + 0x13e   (faction-indexed). Side effect: if "
                       "[$14d12+316] == 0x60 the handler rewrites record[6] "
                       "(category) -- a state transition, ignore for rendering.",
              "verified": "disasm"},
        "8": {"name": "leader goods icons", "prepare": "$1192e", "blit": "none",
              "sheet": "$33000", "frame_bytes": 55,
              "frame": "loop slot 0..7 over [$4e514 + record[14]] byte 24+slot "
                       "(goods[8] = Pike/Sword/Bow/Plough/Boat/Pot/Catapult/"
                       "Cannon counts); for each non-zero, jump table $11886 -> "
                       "a per-slot handler, base ~0x116 via $11f78. Table not "
                       "fully ripped.",
              "verified": "disasm (structure)"},
        "9": {"name": "structure (16x16)", "prepare": "$11c36",
              "blit": "$1225c (centred)", "sheet": "$312a0", "frame_bytes": 160,
              "frame": "record[14]; if negative, D2 = record[14] + 0x2f, blit "
                       "via $1225c. (record[14] is a signed word here.)",
              "verified": "disasm"},
        "10": {"name": "structure w/ flag", "prepare": "$11b3c",
               "blit": "$11f82 + $e6ee", "sheet": "$33000", "frame_bytes": 55,
               "frame": "main $11f82 D2=0x148; if record[14]!=0 also $e6ee "
                        "D2=5 at y-=record[14]; if A3==$4c112 also $11f82 "
                        "D2=0x151 at y-=record[15]; returns D2 = ([$57fec] & 7) "
                        "+ 0x127.",
               "verified": "disasm"},
        "11": {"name": "structure w/ flag (== cat 10)", "prepare": "$11b2a",
               "blit": "$11f82 + $e6ee", "sheet": "$33000", "frame_bytes": 55,
               "frame": "if record[15] < 0: counter side effect; else falls "
                        "into cat 10's body ($11b44).",
               "verified": "disasm"},
        "12": {"name": "== cat 3", "prepare": "$117b0", "blit": "$11f78",
               "sheet": "$33000", "frame_bytes": 55, "frame": "see cat 3"},
        "13": {"name": "faction marker", "prepare": "$1174e", "blit": "$11f78",
               "sheet": "$33000", "frame_bytes": 55,
               "frame": "(record[5] & 0xff) + 0x149   [+1 if [$4bb41]&1]. "
                        "faction-indexed, animated.",
               "verified": "disasm"},
        "14": {"name": "marker / icon", "prepare": "$11b0c", "blit": "$11f78",
               "sheet": "$33000", "frame_bytes": 55,
               "frame": "0x150 default; if record[5] > 0 then ([$57fec] & 1) + "
                        "0x14e",
               "verified": "disasm"},
        "15": {"name": "large structure", "prepare": "$1198a",
               "blit": "$119d4 (centred)", "sheet": "$312a0", "frame_bytes": 160,
               "frame": "D2 = 0x0c default; then record[8]-indexed ($119ae..; "
                        "mulu #$a on record[8] within the $312a0 frame). Not "
                        "fully ripped.",
               "verified": "disasm (structure)"},
        "16": {"name": "?", "blit": "$1168a", "frame": "not ripped"},
        "17": {"name": "?", "blit": "$11f78", "sheet": "$33000",
               "frame_bytes": 55, "frame": "not ripped"},
        "18": {"name": "?", "blit": "$12258", "frame": "not ripped"},
        "19": {"name": "?", "blit": "$12258", "frame": "not ripped"},
    },
}


def decode_minisprite(frame: bytes):
    """8 x 11 four-bitplane sprite (77th-pass, from the aligned $11fe4..$12034
    blitter loop). Per row = 5 bytes: [AND-mask, plane0, plane1, plane2, plane3].
    The mask is shared across all four planes. `dst = (dst & mask) | data`: a
    mask bit of 1 keeps the background pixel, a bit of 0 clears it so the plane
    data shows. So a pixel is **opaque where the mask bit == 0**.

    Returns (px[11][8] palette index 0..15, msk[11][8] 1 = opaque)."""
    px = [[0] * SPRITE_W for _ in range(SPRITE_ROWS)]
    msk = [[0] * SPRITE_W for _ in range(SPRITE_ROWS)]
    for r in range(SPRITE_ROWS):
        m, p0, p1, p2, p3 = frame[r * 5:r * 5 + 5]
        for b in range(SPRITE_W):
            bit = 7 - b
            msk[r][b] = 1 - ((m >> bit) & 1)
            px[r][b] = (((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) |
                        (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3))
    return px, msk


def decode_wordsprite(frame: bytes, w: int, h: int):
    """4-bitplane + AND-mask sprite whose rows are WORDS (16 px/group), MSB-first
    -- the $312a0 (16w) and $37c7c (32w = 2 groups) sheets. Row = w//16 groups of
    5 big-endian words [mask, p0, p1, p2, p3]. Opaque where the mask bit == 0.
    Returns (px[h][w], msk[h][w])."""
    groups = w // 16
    row_bytes = groups * 10
    px = [[0] * w for _ in range(h)]
    msk = [[0] * w for _ in range(h)]
    for r in range(h):
        for g in range(groups):
            o = r * row_bytes + g * 10
            m, p0, p1, p2, p3 = struct.unpack_from(">5H", frame, o)
            for b in range(16):
                bit = 15 - b
                x = g * 16 + b
                msk[r][x] = 1 - ((m >> bit) & 1)
                px[r][x] = (((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) |
                            (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3))
    return px, msk


def _contact_sheet(path: Path, frames_px_msk, w: int, h: int, pal_rgb, cols: int,
                   up: int = 4):
    cw, chh = w * up + 4, h * up + 4
    rowsN = (len(frames_px_msk) + cols - 1) // cols
    img = [[(40, 40, 40)] * (cols * cw) for _ in range(rowsN * chh)]
    for i, (px, msk) in enumerate(frames_px_msk):
        ox, oy = (i % cols) * cw + 2, (i // cols) * chh + 2
        for r in range(h):
            for c in range(w):
                col = pal_rgb[px[r][c]] if msk[r][c] else (60, 0, 60)
                for dy in range(up):
                    for dx in range(up):
                        img[oy + r * up + dy][ox + c * up + dx] = col
    write_png(path, cols * cw, rowsN * chh, img)


def export_sprites(ram: Ram, out: Path, man: list, dom_pal):
    sd = out / "sprites"
    sd.mkdir(exist_ok=True)
    pal_rgb = [stf_rgb(w) for w in dom_pal]

    # -- $33000 mini-sprite sheet (men / animals / small props / effects) --------
    # 87th: the category handlers ($11c8a men, $11a86 animals, $11b0c ... -- see
    # SPRITE_TRIGGERS) reach frame bases up to 0x150. Rip 0x160 frames (an upper
    # bound -- the exact count per category is still open); past ~0x150+count the
    # address space runs into the $37c7c prop sheet. Was: first 64 (men only).
    # $11f82 reads 0x37 (55) B/frame = 11 rows x [AND-mask, plane0..3].
    nframes = 0x160
    frames = [ram.blk(SPRITE_SHEET + f * SPRITE_FRAME_BYTES, SPRITE_FRAME_BYTES)
              for f in range(nframes)]
    (sd / "sheet_raw.bin").write_bytes(
        ram.blk(SPRITE_SHEET, nframes * SPRITE_FRAME_BYTES))

    up = 6
    cols = 16
    rowsN = (nframes + cols - 1) // cols
    cw, chh = SPRITE_W * up + 4, SPRITE_ROWS * up + 4
    sheet = [[(40, 40, 40)] * (cols * cw) for _ in range(rowsN * chh)]
    for i, fr in enumerate(frames):
        px, msk = decode_minisprite(fr)
        ox, oy = (i % cols) * cw + 2, (i // cols) * chh + 2
        for r in range(SPRITE_ROWS):
            for c in range(SPRITE_W):
                col = pal_rgb[px[r][c]] if msk[r][c] else (60, 0, 60)
                for dy in range(up):
                    for dx in range(up):
                        sheet[oy + r * up + dy][ox + c * up + dx] = col
    write_png(sd / "sheet_contact.png", cols * cw, rowsN * chh, sheet)

    # -- $312a0 structure sheet (cats 1, 9, 15) : 16x16, 160 B/frame -----------
    # It runs from $312a0 up to $33000 -> at most (0x33000-0x312a0)/0xa0 = 47.
    n3 = (SPRITE_SHEET - SPRITE3_SHEET) // SPRITE3_FRAME_BYTES
    (sd / "struct_sheet_raw.bin").write_bytes(
        ram.blk(SPRITE3_SHEET, n3 * SPRITE3_FRAME_BYTES))
    _contact_sheet(sd / "struct_sheet_contact.png",
                   [decode_wordsprite(ram.blk(SPRITE3_SHEET + f * SPRITE3_FRAME_BYTES,
                                              SPRITE3_FRAME_BYTES), 16, 16)
                    for f in range(n3)], 16, 16, pal_rgb, 12)

    # -- $37c7c prop sheet (category 2: trees / obstacles) : 32x24, 480 B ------
    # 87th: frames 0..27 decode cleanly as buildings + trees at 32x24. From
    # frame 28 the row structure changes (top-row mask stops being 0xffff) --
    # either a different geometry or a different sheet begins there. Rip 0..27.
    n2 = 28
    (sd / "prop_sheet_raw.bin").write_bytes(
        ram.blk(SPRITE2_SHEET, n2 * SPRITE2_FRAME_BYTES))
    _contact_sheet(sd / "prop_sheet_contact.png",
                   [decode_wordsprite(ram.blk(SPRITE2_SHEET + f * SPRITE2_FRAME_BYTES,
                                              SPRITE2_FRAME_BYTES), 32, 24)
                    for f in range(n2)], 32, 24, pal_rgb, 8)

    # -- heading -> frame table (used only by the $e6ee marker/HUD path) --------
    ht = ram.blk(0x1675a, 16)
    headings = {h: (None if ht[h] == 0xff else ht[h]) for h in range(16)}
    (out / "headings.json").write_text(json.dumps({
        "table_addr": "$1675a",
        "note": ("heading (byte 17 of the object record, 0..15) -> frame index "
                 "for pm_pick_sprite_frame ($16738), which blits via $e6ee. "
                 "0xff = draw nothing for this facing. 87th: this is the "
                 "$165b2 selected-group-marker / HUD path -- NOT the iso-terrain "
                 "entity path. The terrain men use cat 0's own yaw-relative "
                 "formula (see sprites/sprite_triggers.json)."),
        "heading_to_frame": headings,
        "raw": ht.hex(),
    }, indent=1))

    # -- the category dispatch (the actual iso-entity draw path) ----------------
    (sd / "sprite_triggers.json").write_text(json.dumps(SPRITE_TRIGGERS, indent=1))

    man.append({
        "file": "sprites/sheet_raw.bin + sprites/sheet_contact.png",
        "frames": nframes,
        "provenance": (
            f"g_minisprite_sheet at $33000, {SPRITE_FRAME_BYTES:#x} bytes/frame. "
            "Blitted by $11f82, reached from $115e0's per-cell category dispatch "
            "(jump tables $1162e prepare / $1165c blit). 87th: full populated "
            "sheet (was: first 64 = men only)."),
        "format": (
            f"sheet_raw.bin = {nframes} x {SPRITE_FRAME_BYTES} raw bytes. "
            f"Each frame is {SPRITE_W} x {SPRITE_ROWS} FOUR-bitplane (16-colour), "
            "5 bytes/row = [AND-mask, plane0..3]; opaque where mask bit == 0. "
            "sheet_contact.png = 16-wide, 6x, real palette / magenta = clear. "
            "Frames 0-63 = men (4 faction blocks of 16); 0x117 = animals; "
            "0x100/0x10f/0x13e/0x14e/0x150 = other categories -- see "
            "sprite_triggers.json for each category's base."),
    })
    man.append({
        "file": "sprites/prop_sheet_raw.bin + sprites/prop_sheet_contact.png",
        "frames": n2,
        "provenance": (
            f"category-2 (tree/obstacle) sheet at $37c7c, "
            f"{SPRITE2_FRAME_BYTES:#x} (480) B/frame. Blitted inline by $1168c "
            "via $1227c/$124a8. 87th: 32w x 24h, 20 B/row = 2 groups of "
            "[mask,p0..p3] words (from the $124a8 disasm + a live trace)."),
        "format": "48-frame sample. decode_wordsprite(frame, 32, 24).",
    })
    man.append({
        "file": "sprites/struct_sheet_raw.bin + sprites/struct_sheet_contact.png",
        "frames": n3,
        "provenance": (
            f"structure sheet at $312a0 (cats 1, 9, 15), "
            f"{SPRITE3_FRAME_BYTES:#x} (160) B/frame. Blitted centred via "
            "$1225c / $119d4. 87th: 16w x 16h, 10 B/row [mask,p0..p3] words."),
        "format": "decode_wordsprite(frame, 16, 16).",
    })
    man.append({
        "file": "sprites/sprite_triggers.json",
        "provenance": ("87th: $115e0 category dispatch. Jump tables $1162e / "
                       "$1165c read from RAM; per-category frame formulas from a "
                       "disassembly of each prepare handler + a live men-path "
                       "trace (scratchpad/pm78_settle.snap)."),
        "format": "dispatch + position_lerp + per-category {prepare, blit, "
                  "sheet, frame formula, verified}",
    })
    man.append({"file": "headings.json",
                "provenance": "heading->frame table at $1675a, read by $16738 "
                              "($e6ee marker/HUD path, not the iso entities)",
                "format": "heading_to_frame: {0..15: frame|null}"})
    return nframes


def dom_pal_rgb(dom_pal, idx):
    return stf_rgb(dom_pal[idx])


# ---------------------------------------------------------------------------
# HUD glyph sheet
# ---------------------------------------------------------------------------


def export_hud(ram: Ram, out: Path, man: list):
    hd = out / "hud"
    hd.mkdir(exist_ok=True)
    # $e6ee reads a 4-long-per-entry descriptor table at $e6ee+110 (PC-relative)
    # then blits with a 32-byte row stride (lsl.w #5,D1). The source sheet address
    # is one of those descriptor longs. Dump the descriptor table raw for the port
    # to resolve; a full HUD rip is out of scope for the terrain-renderer proof.
    desc = ram.blk(0xe6ee + 110, 4 * 16)
    (hd / "descriptor_table.bin").write_bytes(desc)
    longs = struct.unpack(">16I", desc)
    (hd / "descriptor_table.json").write_text(json.dumps({
        "table_addr": "$e6ee+110 (PC-relative, read by pm_blit_hud_sprite)",
        "row_stride": 32,
        "entries": [f"${v:x}" for v in longs],
        "note": ("each entry is a 4-long descriptor; one long is the source glyph "
                 "sheet address. Resolve against a live snapshot before ripping "
                 "the HUD -- not needed for the terrain-layer proof."),
    }, indent=1))
    man.append({"file": "hud/descriptor_table.bin",
                "provenance": "$e6ee+110 descriptor table (pm_blit_hud_sprite)",
                "format": "16 x 4-long entries, 32-byte glyph row stride",
                "status": "raw dump; full HUD rip deferred"})


# ---------------------------------------------------------------------------
# tables.json -- projection / zoom / rotation constants
# ---------------------------------------------------------------------------

ZOOM_FF9C = [None, 84, 42, 28, 21, 17, 14, 12]   # $13f83


def export_tables(ram: Ram, out: Path, man: list):
    consts = {f"${a:04x}": ram.s16(a) for a in range(0xfdea, 0xfe04, 2)}
    proj = {
        "horizon_ff96": ram.s16(0xff96),
        "eye_distance_ff98": ram.s16(0xff98),
        "yaw_ff9a": ram.u16(0xff9a),
        "zoom_scale_ff9c": ram.u16(0xff9c),
        "height_bias_fec4": ram.s16(0xfec4),
        "note": (
            "pm_perspective_div ($ff7c): "
            "d = eye - z ; sx = x*eye/d ; sy = (z - horizon)*eye/d + horizon. "
            "Then $fecc: screenX = sx + 0x80, screenY = 0x7c - sy. "
            "z = (cellHeight - height_bias) * zoom_scale >> 4. "
            "grid pos = -col*zoom_scale, -row*zoom_scale, rotated by yaw."),
    }
    heading_frame = list(ram.blk(0x1675a, 16))
    sincos = [ram.s16(0x1400a + i * 2) for i in range(64)]
    yawtab = [ram.u16(0x13f8a + i * 2) for i in range(64)]

    tables = {
        "zoom_geometry": {
            "ff9c_by_index": ZOOM_FF9C,
            "current_index": (ZOOM_FF9C.index(ram.u16(0xff9c))
                              if ram.u16(0xff9c) in ZOOM_FF9C else None),
            "derived_constants_fdea_fe02": consts,
            "constant_meaning": {
                "$fdea": "A0 grid-row advance byte stride in $3f364 (col loop remainder)",
                "$fdec": "grid half-extent: inner/outer loops run -this..+this (=4 -> 9x9)",
                "$fdee": "A1 height-plane row advance (64 - tilepx - 1)",
                "$fdf0": "loop bound for the $faa8 second-pass row loop",
                "$fdf2": "A1 row advance in the main $f898 loop; A2 advance = 2x",
                "$fdf4": "A0 row advance in the main $f898 loop (= $fdea + 4)",
                "$fdf6": "$faa8 pass A1 advance",
                "$fdf8": "$faa8 pass A0 advance",
                "$fdfa": "$fdc6-pass A0 back-step ((tilepx<<6)+1)",
                "$fdfc": "$fdc6-pass A0 back-step ((tilepx*64)+4)",
                "$fdfe": "derived screen offset ((half+1+bound)*bound + bound)",
                "$fe00": "derived ((tilepx*64)+tilepx*4)",
                "$fe02": "tilepx*4",
            },
            "note": ("$fe04 takes D1 = grid half-extent (== zoom index on the "
                     "preset path) and D2 = tile pixel size (8 at index 4) and "
                     "derives the 13 words above. Hand-poking them is unsafe "
                     "(inconsistent stride sends the span filler into code)."),
        },
        "projection": proj,
        "heading_to_frame": heading_frame,
        "sincos_1400a_q15": sincos,
        "yaw_table_13f8a": yawtab,
        "yaw_table_note": (
            "$13f8a: 64 u16 entries. $fecc indexes it by (yaw<<1), reads one word "
            "as the high half of a {cos,sin} pair in D7, then re-indexes at "
            "+128 bytes for the low half. Values rise monotonically 0..0x5843 "
            "over the first 32 entries -- an angle-scaled parameter, not a raw "
            "sine. Pair it with sincos_1400a for the exact rotation basis when "
            "porting; the reference renderer approximates rotation as a true "
            "2D rotate by (yaw/16 * 22.5 deg)."),
    }
    (out / "tables.json").write_text(json.dumps(tables, indent=1))
    man.append({
        "file": "tables.json",
        "provenance": (
            "$fdea..$fe02 (zoom geometry, $fe04 output), $ff96/$ff98/$ff9a/$ff9c "
            "(projection params), $fec4 (height bias), $1675a (heading->frame), "
            "$1400a (Q15 sin/cos), $13f8a (yaw table)."),
        "format": "see keys; all ints are decoded from big-endian words",
    })


# ---------------------------------------------------------------------------
# strings.json
# ---------------------------------------------------------------------------


def decode_strtab(ram: Ram, addr, count):
    """PowerMonger string tables: u16 offsets from the table base into a string
    pool that follows. Strings appear to carry a 1-byte length/attr prefix. We
    return best-effort decodes plus the raw pool for the port to finish."""
    offs = [ram.u16(addr + i * 2) for i in range(count)]
    entries = []
    for i, o in enumerate(offs):
        if o == 0 or o > 0x400:
            entries.append(None)
            continue
        p = addr + o
        # try prefix byte = length
        ln = ram.u8(p)
        cand = ram.blk(p + 1, min(ln, 40)) if 0 < ln < 40 else b""
        printable = all(32 <= c < 127 for c in cand) if cand else False
        if printable:
            entries.append(cand.decode("latin1"))
        else:
            # fall back: null-terminated from p
            end = p
            while end < len(ram.d) and ram.d[end] and end - p < 40:
                end += 1
            s = ram.blk(p, end - p)
            entries.append(s.decode("latin1", "replace"))
    return {"table_addr": f"${addr:x}", "offsets": offs,
            "decoded_best_effort": entries,
            "pool_raw_first_256": ram.blk(addr, 256).hex()}


def export_strings(ram: Ram, out: Path, man: list):
    s = {
        "item_names_a242": decode_strtab(ram, 0xa242, 9),
        "building_names_a15a": decode_strtab(ram, 0xa15a, 10),
        "settlement_sizes_a128": decode_strtab(ram, 0xa128, 8),
        "loyalty_terms_959e": decode_strtab(ram, 0x959e, 9),
        "animal_names_a0ca": {"note": "sequential null-terminated",
                              "values": ["Sheep", "Cow", "Pigeon"]},
        "note": ("string-table decode is best-effort: the u16-offset + "
                 "length-prefixed-pool model fits 'Village'/'Hamlet'/'Town'/"
                 "'Ranch' but not every entry. The raw pool bytes are included "
                 "so a port can finish the decode. NOT renderer-critical."),
    }
    (out / "strings.json").write_text(json.dumps(s, indent=1))
    man.append({"file": "strings.json",
                "provenance": "$a242 / $a15a / $a128 / $959e string tables",
                "format": "per table: offsets[] + decoded_best_effort[] + raw pool",
                "status": "best-effort; raw pool included"})


# ---------------------------------------------------------------------------
# entities.json -- one frame's live object / settlement / effect state
# ---------------------------------------------------------------------------

OBJ = 0x51b66
OBJ_STRIDE = 50


def decode_object(r: bytes):
    # field map from ai.md "As a C struct" (array $51b66, stride 50):
    #  +0 bucket_next, +5 active(byte5>0 live), +6 category, +8/+10 world x/y,
    #  +12/+13 step x/y, +17 heading (0..15, sometimes stored <<4), +18 dwell,
    #  +20 long target pos, +30 prev_mode, +31 mode, +34 nation_off, +42 group_off
    return {
        "bucket_next": struct.unpack_from(">H", r, 0)[0],
        "active5": r[5],
        "category6": r[6],
        "world_x": struct.unpack_from(">h", r, 8)[0],
        "world_y": struct.unpack_from(">h", r, 10)[0],
        "step_x12": struct.unpack_from(">b", r, 12)[0],
        "step_y13": struct.unpack_from(">b", r, 13)[0],
        "heading17": r[17],
        "prev_mode30": r[30],
        "mode31": r[31],
        "nation_off34": struct.unpack_from(">H", r, 34)[0],
        "group_off42": struct.unpack_from(">H", r, 42)[0],
        "raw": r.hex(),
    }


def export_entities(ram: Ram, out: Path, man: list):
    objs = []
    for s in range(1, 512):
        r = ram.blk(OBJ + s * OBJ_STRIDE, OBJ_STRIDE)
        o = decode_object(r)
        if o["active5"] and o["active5"] != 0xff:
            o["slot"] = s
            objs.append(o)
    settlements = []
    for s in range(0, 240):
        r = ram.blk(0x4f916 + s * 0x12, 0x12)
        if any(r):
            settlements.append({"slot": s, "raw": r.hex(),
                                "owner5": r[5], "kind7": r[7],
                                "cell": struct.unpack_from(">H", r, 12)[0],
                                "leader14": struct.unpack_from(">H", r, 14)[0]})
    leaders = []
    for s in range(0, 8):
        r = ram.blk(0x4e514 + s * 32, 32)
        if any(r):
            leaders.append({"slot": s, "raw": r.hex(),
                            "side": r[1], "cell": struct.unpack_from(">H", r, 4)[0],
                            "troops_reserve": struct.unpack_from(">H", r, 6)[0],
                            "troops_field": struct.unpack_from(">H", r, 8)[0],
                            "goods": list(r[24:32])})
    herd = []
    for s in range(0, 400):
        r = ram.blk(0x4d252 + s * 12, 12)
        if any(r):
            herd.append({"slot": s, "raw": r.hex(),
                         "category6": r[6], "breed7": r[7],
                         "packed_cell": struct.unpack_from(">H", r, 10)[0]})
    effects = []
    for s in range(0, 48):
        r = ram.blk(0x4be00 + s * 0x10, 0x10)
        if any(r):
            effects.append({"slot": s, "raw": r.hex()})

    # -- render_entities: the $47970 per-cell bucket walk -------------------
    # A faithful replay of what $115e0 (pm_draw_cell_entities) sees, so the
    # port's Sprites.drawEntities can be fed a real record stream (Task 4/2).
    # This MIRRORS tools/pm_render_ref.py load_ram exactly (same camera window,
    # same SIGNED $51b66-relative offset, same fx4/fy4 address-jitter, same
    # field set) -- the two are cross-checked byte-exact on synthetic data
    # (scratchpad/pm90_xcheck.*), so the parse has to agree here too.
    BUCK, OBJ_BASE = 0x47970, 0x51B66
    cam_x = ram.u16(0x4BB3A) - ram.u16(0x57FFC)
    cam_y = ram.u16(0x4BB3C) - ram.u16(0x57FFC)
    render_objs = []
    seen = set()
    for wcy in range(cam_y - 1, cam_y + 10):
        for wcx in range(cam_x - 1, cam_x + 10):
            if not (0 <= wcx < 64 and 0 <= wcy < 128):
                continue
            d4 = ram.u16(BUCK + (wcy * 64 + wcx) * 2)
            depth = 0
            while d4 and depth < 96:
                off = d4 - 0x10000 if d4 >= 0x8000 else d4
                o = OBJ_BASE + off
                if not (0x40000 <= o < 0x60000) or (o, wcx, wcy) in seen:
                    break
                seen.add((o, wcx, wcy))
                depth += 1
                rec = ram.blk(o, 50)
                a2 = 0x47970 + (wcy * 64 + wcx) * 2
                a0 = 0x3F364 + (wcy - cam_y) * 64 + (wcx - cam_x) * 4
                s = (a2 + o) & 0xFFFF
                render_objs.append({
                    "addr": o, "wcx": wcx, "wcy": wcy,
                    "b6": rec[6], "b5": rec[5], "b7": rec[7], "b14": rec[14],
                    "b17": rec[17], "b31": rec[31],
                    "fx": rec[9], "fy": rec[11],
                    "fx4": (s << 3) & 0xFF, "fy4": (s + (a0 & 0xFFFF)) & 0xFF,
                    "group": (rec[42] << 8) | rec[43],
                })
                d4 = ram.u16(o)
    tsel = ram.u16(0x57FD0)
    entity_ctx = {
        "cam_x": cam_x, "cam_y": cam_y,
        "yaw": ram.u16(0xFF9A),
        "anim": ram.u8(0x4BB41) & 1,
        "sel_group": ram.u16(0x57FFE),
        "tile_off": ram.u16(0x11746 + tsel) if tsel in (0, 2, 4, 6) else 0,
        "rot_phase": ram.u8(0x57FED),
        "render_source": "pm88_f1.ram (frame-start anchor; the rest of assets/ is pm74_late)",
        "half": ram.u16(0xFDEC),
        "sheet33": "sprites/sheet_raw.bin",       # $33000, 55 B/frame
        "sheet_prop": "sprites/prop_sheet_raw.bin",  # $37c7c, 480 B/frame
        "note": ("feed render_entities[] as PmLogic.Sprites.EntityRec and call "
                 "Sprites.drawEntities(buf, ctx, corners, cam_x, cam_y, recs). "
                 "byte6 drawn: 0 (men) 4 (building/tree) 8 (animal) 14 (banner) "
                 "6/24 (marker). See SPEC.md section 6."),
    }

    e = {
        "note": ("one frame of live entity state from the settled iso view. "
                 "world coords pack as {x: low byte, y: high byte}; the renderer "
                 "maps (worldX, worldY) -> grid cell via "
                 "cell = ((worldY & 0xff00) >> 2) + (worldX & 0xff) "
                 "(pm_relink_bucket $163ea)."),
        "object_record_stride": OBJ_STRIDE,
        "objects": objs,
        "settlements": settlements,
        "leaders": leaders,
        "herd": herd,
        "effects": effects,
        "entity_ctx": entity_ctx,
        "render_entities": render_objs,
    }
    (out / "entities.json").write_text(json.dumps(e, indent=1))
    man.append({
        "file": "entities.json",
        "provenance": ("$51b66 object records (50 B, slots 1..511), $4f916 "
                       "settlements, $4e514 leaders, $4d252 herd, $4be00 effects; "
                       "render_entities[] = the $47970 per-cell bucket walk "
                       "($115e0's view, SIGNED $51b66 offset), entity_ctx = the "
                       "per-frame Sprites.drawEntities constants."),
        "format": "decoded key fields + raw hex per record",
        "active_objects": len(objs),
        "render_entities": len(render_objs),
    })


# ---------------------------------------------------------------------------
# reference frame
# ---------------------------------------------------------------------------


def decode_planar(screen: bytes, pal_words):
    pal = [stf_rgb(w) for w in pal_words]
    for y in range(200):
        row = screen[y * 160:y * 160 + 160]
        out_row = []
        for xw in range(20):
            planes = struct.unpack_from(">4H", row, xw * 8)
            for bit in range(16):
                idx = 0
                for p in range(4):
                    if planes[p] & (1 << (15 - bit)):
                        idx |= (1 << p)
                out_row.append(pal[idx])
        yield out_row


def export_reference(frame_path: Path, out: Path, man: list, dom_pal):
    b = frame_path.read_bytes()
    screen = b[1:1 + 32000]
    rd = out / "reference"
    rd.mkdir(exist_ok=True)
    write_png(rd / "isoframe.png", 320, 200, decode_planar(screen, dom_pal))
    # also index-map (palette index per pixel) for the renderer diff
    idxmap = bytearray(320 * 200)
    for y in range(200):
        row = screen[y * 160:y * 160 + 160]
        for xw in range(20):
            planes = struct.unpack_from(">4H", row, xw * 8)
            for bit in range(16):
                idx = 0
                for p in range(4):
                    if planes[p] & (1 << (15 - bit)):
                        idx |= (1 << p)
                idxmap[y * 320 + xw * 16 + bit] = idx
    (rd / "isoframe_indices.bin").write_bytes(idxmap)
    man.append({
        "file": "reference/isoframe.png",
        "provenance": (
            f"live shifter output from {frame_path.name}. 77th: verified equal to "
            "the RAM snapshot's BACK buffer $24400 to 231/64000 px (moving "
            "sprites only) -- so it is consistent with the $3f364 corner buffer "
            "and is the right target for the pm_render_ref.py diff. The front "
            "buffer $1c700 is the previous (mid-animation) frame."),
        "format": "320 x 200 RGB PNG; isoframe_indices.bin = 1 byte palette index/px",
    })


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent.parent
    ap.add_argument("--ram", default=str(here / "scratchpad/pm74_late.ram"))
    ap.add_argument("--snap", default=None)
    ap.add_argument("--frame", default=str(here / "scratchpad/pm76_fr/f000100.bin"))
    ap.add_argument("--out", default=str(here / "reversing/powermonger/port/assets"))
    args = ap.parse_args()

    if args.snap:
        data = ram_from_snap(Path(args.snap))
    else:
        data = Path(args.ram).read_bytes()
    ram = Ram(data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frame = Path(args.frame)

    man = []
    export_terrain(ram, out, man)
    dom_pal = export_palette(frame, out, man)
    export_dither(ram, out, man)
    export_sprites(ram, out, man, dom_pal)
    export_hud(ram, out, man)
    export_tables(ram, out, man)
    export_strings(ram, out, man)
    export_entities(ram, out, man)
    export_reference(frame, out, man, dom_pal)

    manifest = {
        "generated_by": "tools/pm_export.py",
        "source_ram": args.snap or args.ram,
        "source_frame": args.frame,
        "game": "PowerMonger (1990)(Bullfrog)[cr Replicants], settled iso view",
        "grid": {"stride": GRID_STRIDE, "rows": GRID_ROWS,
                 "water_level": WATER_LEVEL, "sea_static_bit": SEA_STATIC_BIT},
        "files": man,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"exported {len(man)} asset groups to {out}")
    for m in man:
        print(f"  {m['file']}")


if __name__ == "__main__":
    main()

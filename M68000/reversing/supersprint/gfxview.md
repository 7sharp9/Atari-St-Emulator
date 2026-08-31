# Looking at Super Sprint's graphics in RAM with `tools/gfxview.py`

`title.png` / `gameplay.png` in this directory are the *live framebuffer*. This
note is about everything behind it: the palettes and bitmaps the game has decoded
out of `SUPER.DAT` into RAM. Tool reference: the `tools/gfxview.py` section of
`M68000/DEVELOPING.md`.

## How the snapshots were taken

```
unzip "Super Sprint.zip"                                    # -> "Super Sprint.ST"
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 26000000 \
  snapshot ss_26M.snap --disk-a "Super Sprint.ST"           # in-attract gameplay demo
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 34000000 \
  snapshot ss_34M.snap --disk-a "Super Sprint.ST"           # title / logo screen

python tools/gfxview.py ss_34M.snap --html ss_34M.html --contact gfx_ram_contact.png
```

`.snap` files hold a full 1 MB RAM image, most of it the copyrighted program, so
like the game binary they are **not committed** - retake them per session. Only
the three rendered PNGs below are here.

## What the tool finds

```
$ python tools/gfxview.py ss_34M.snap --html ss_34M.html
  a4=0x0001eb44  a5=0x00000000  pc=0x00fc0738
  23 palette(s):
    0x0001c9e0 STF  8 colours
    0x0001caa4 STF  7 colours
    0x0001d37a STF 10 colours
    ... 0x0001d3ba .. 0x0001d5fa : a run of 19 sixteen-colour STF palettes ...
    0x0001d9ca STF ..
    0x0003c794 STF ..
  5 data span(s):
    0x0000a000-0x0001c000    72 KB  entropy 5.74   <- SSPRINT.PRG text/data ($a304+)
    0x0001c800-0x0001f000    10 KB  entropy 4.89   <- game state + the palette table
    0x00021000-0x00061000   256 KB  entropy 3.82   <- screen buffers + decoded gfx
    0x0006c800-0x0006f800    12 KB  entropy 2.61
    0x000f8000-0x00100000    32 KB  entropy 3.06   <- framebuffer ($f8000)
```

### Palettes - `gfx_palette_ramp.png`

The 19 consecutive 16-colour palettes at `$1d3ba`..`$1d5fa` are a **fade ramp**:
the title-screen fade-in/fade-out, precomputed and stored as a table. The image is
the framebuffer at `$f8000` (step 34M) decoded through each one in turn - the same
bitmap darkening to black at one end and washing to orange/white at the other. The
game's live hardware palette at that instant is not in the RAM image (`$FFFF824x`
is outside the 1 MB dump), so `gfx_title.png` picks `$1d4da`, a near-final frame of
the ramp, to show the bitmap in plausible colour: the F1 car, "SUPER SPRINT" in
perspective, "© 1986 ATARI GAMES".

### Bitmaps - `gfx_ram_contact.png`

Whole-RAM contact sheet, one pixel per byte, 512 bytes/row (so `y*512` = address).
The lit band is `$0`..`~$6a800`; below it is unused heap; the strip at the bottom
(`~row 1980`) is the framebuffer at `$f8000`. The regular vertical-stripe texture
around `$2b000`..`$34800` is packed sprite/tile data.

`$20000` holds an off-screen screen-format copy of the title bitmap (composed
there, then blitted). Load `ss_34M.html`, set base `20000`, layout
`st-interleaved`, 320x200x4, palette `$1d4da` - the logo screen appears cleanly.

The sprite/tile source data (`$2b000`+, and the `-1188(a4)` table at `$3b150`)
does **not** decode as plain ST screen memory. Super Sprint's blitter at `$15436`
reads it transposed - bitplanes at `src+8/+16/+24`, source advancing one byte per
row. In the viewer that is layout `planar-linear` with `plane_stride 8`,
`row_stride 1` (the "SS sprite tile 8x8x4" preset); structure resolves as you nudge
the strides, but a clean full rip needs the per-object width/height from the sprite
table, which is a separate reverse-engineering job.

## The `.gfx` sidecar producer (56th pass) - `obs_palettes.png`

`ATARI_GFX_SIDECAR=<snap>.gfx` makes the emulator record, as it runs, every
address the program hands to **XBIOS Setpalette** (`palette $xxxxxxxx`) and the
log / phys bases from every **XBIOS Setscreen** (`pointer screen_log|screen_phys
$xxxxxxxx`, a `$ffffffff` "query" arg skipped). Both are plain XBIOS arguments -
no game knowledge in the emulator. It is behaviourally inert, exactly like
`ATARI_TRACE_OS`: the file is the only thing it writes. `gfxview.py` auto-loads
`<snap>.gfx`, tags matching detected palettes `(observed Setpalette)`, and
**force-includes** any observed address the `$0RGB`-run heuristic missed - the
game told us that exact address is a palette, so it is authoritative.

```
ATARI_NOTRACE=1 ATARI_GFX_SIDECAR=ss.snap.gfx \
  dotnet exec bin/Debug/net8.0/M68000.dll 6000000 snapshot ss.snap --disk-a "Super Sprint.ST"
$ cat ss.snap.gfx
palette $0002102c
palette $0001d590
pointer screen_log  $00021100
pointer screen_phys $00021100
pointer screen_log  $000f8000
pointer screen_phys $000f8000
palette $0001d610
```

`$21100` / `$f8000` are exactly the two buffers the attract loop flips between.
None of the three Setpalette addresses were auto-detected (the heuristic finds
the `$1d3xx` fade-ramp *table*, not these live 16-word windows), so the sidecar
is what surfaces them. `obs_palettes.png` is those three decoded: `$1d590` and
`$1d610` are full game palettes (car reds/oranges/yellows, track greys, sky
blue, white); `$2102c`, staged just before the `$21100` framebuffer, is a
sparser partial.

## Tile-sheet layout mode (56th pass)

The viewer gained a **`tiles 8x8x4`** layout: a sheet of 32-byte planar cells
(4 planes of 8 bytes, one byte per row, planes contiguous), `width/8` cells per
row - the standard packed layout for 4-plane fonts and small tiles. Decoder
unit-checked against hand-built cells. Super Sprint's own sprite/tile source
does *not* use it (it is the transposed `planar-linear 8/1` format described
above), so this is a general-purpose addition rather than the key to SS's art;
the "tile sheet 32x32 cells" preset drives it.

## Files

| file | what |
|------|------|
| `gfx_palette_ramp.png` | `$f8000` (step 34M) through all 19 detected `$1d3xx` fade-ramp palettes |
| `gfx_title.png` | `$f8000` (step 34M) via `st-interleaved` 320x200x4 + palette `$1d4da` |
| `gfx_ram_contact.png` | whole-RAM contact sheet (grey, 512 bytes/row) |
| `obs_palettes.png` | the three Setpalette blocks the `.gfx` sidecar producer captured on a 6M-step run, decoded |

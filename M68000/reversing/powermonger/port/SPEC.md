# PowerMonger isometric renderer — porting specification

This is the contract for re-implementing PowerMonger's isometric terrain view
outside the 68000. It is written so a renderer can be built from this document
plus the asset pack in `assets/`, without reading the disassembly.

Scope: the **terrain + sprite render path only** — projection, rasterisation,
sprite compositing, the frame pipeline. The simulation (entity FSM, AI, economy)
is one layer up and is documented in `../ai.md`, `../strategy.md`, `../economy.md`.
The renderer only *reads* the heightmap, the palette, the cell buckets, and each
entity's world position + heading.

Provenance: every constant here is decoded from a live RAM image of the settled
mission-1 iso view (`scratchpad/pm74_late.ram`, PC `$124c0`) and cross-checked
against the disassembly in `../graphics.md`. Addresses are in the relocated game
image (link base `$1050`).

Verification status: `tools/pm_render_ref.py` rebuilds the frame from `assets/`
alone. The **island silhouette, footprint orientation and height shading**
reproduce (see `assets/reference/render_compare.png`). Two things are **not**
closed to a pixel diff and are flagged under "Open questions": the exact
vertical calibration of the perspective divide, and the phase into the dither
table. Neither blocks a port — a modern port replaces the dither with a shader
and re-tunes the camera against a screenshot.

---

## 1. Coordinate systems

| space | units | range | notes |
|-------|-------|-------|-------|
| **world** | 1/256 cell | x: 0..`$3fff`, y: 0..`$3fff` | entity `world_x`/`world_y` (object record +8/+10). `worldX = cellX*256 + fracX`. |
| **grid cell** | 1 cell | x: 0..63, y: 0..127 | the heightmap. `cell_index = y*64 + x` (row-major, stride 64). |
| **packed cell** | — | {x: bits 0-5, y: bits 6-12} | order slots, muster cells. `x = p & 0x3f`, `y = (p >> 6) & 0x7f`. |
| **screen** | pixel | 320 x 200, 4bpp | ST low-res. The iso view fills the whole buffer; the left ~44 px and the border rows are the HUD/stone-table, composited from the terrain master, not projected. |

World → grid cell (used to bucket entities for draw, `pm_relink_bucket` `$163ea`):

```
cell = ((worldY & 0xff00) >> 2) + (worldX & 0x00ff)      // shift + byte add, no mul
     = (worldY >> 8) * 64 + (worldX >> 8)                 // equivalent, cellY*64 + cellX
```

The iso axis mapping is baked into the world-coordinate encoding — there is no
separate world-to-iso matrix at the sim layer.

---

## 2. The heightmap (`assets/terrain.bin`)

Two parallel data sets, both 64 x 128 cells, row-major, stride 64:

| plane | source addr | used for |
|-------|-------------|----------|
| **type** | `$438ee + 0` | colour of the *second* triangle of each cell; terrain class |
| **height (438ee)** | `$438ee - 8257` | colour of the *first* triangle; entity-side terrain sampling |
| **flag** | `$438ee + 8257` | bit 7 = "this cell's projected corners did not move this frame" → skip its fill (still-camera optimisation) |
| **control / height (3f86c)** | `$3f86c + 0` | the height the **projector** reads for cell Z. On mission 1 it tracks the 438ee height plane closely but is the authoritative geometry source. |

`terrain.bin` interleaves all four as `[type, height, flag, control]` per cell,
4 bytes/cell, 32768 bytes total.

Derived rules:

- **water**: `height < 0x0c`. Water cells add `masterTick & 3` to their colour
  byte before the fill (a 4-frame shoreline shimmer), and only while the camera
  is moving (a still camera skips the fill via the flag bit).
- **static-sea skip**: `flag & 0x80` → do not re-fill this cell.
- mission-1 island bounding box in cells: **x 8..45, y 41..75** (rest is sea /
  off-map zero).

A modern port loads this as a 64 x 128 R16 heightfield (use the `control`
plane) plus a 64 x 128 R8 type map, and builds either an `ArrayMesh` or samples
it in a vertex/fragment shader.

---

## 3. Projection

Per-frame, only when the camera cell, yaw or zoom changed (`pm_project_grid`
`$fecc`). Produces one screen-space corner `(sx, sy)` per grid vertex into the
`$3f364` corner buffer (9 x 9 vertices at zoom index 4 — see §5).

### Constants (`assets/tables.json → projection`)

| symbol | addr | value (mission 1, zoom 4) | meaning |
|--------|------|--------------------------|---------|
| `EYE` | `$ff98` | 320 | eye distance for the perspective divide |
| `HORIZON` | `$ff96` | 130 | horizon screen-Y |
| `ZOOM` | `$ff9c` | 21 | world-unit scale (from `$13f83[zoomIndex]`) |
| `YAW` | `$ff9a` | `0xf0` | rotation, 16 steps of `0x10` (`& 0xf0`) |
| `HBIAS` | `$fec4` | *dynamic* | **min** control-plane height over the visible window; recomputed each projection (`$fe8e`) |

### Rotation basis

`$fecc` indexes a fine sine table at `$13f8a` by `YAW * 2`:

```
P = i16( table_13f8a[ YAW*2 ] )           //  = round(32768 * sin(theta))
Q = i16( table_13f8a[ YAW*2 + 0x80 ] )    //  = round(32768 * cos(theta))
theta = YAW * 2 * (22.5deg / 32) = YAW * 1.40625 deg
```

Verified: at `YAW = 0xf0`, `theta = 337.5deg`, `P = -12540`, `Q = 30274`, and
`-12540/32768 = sin(337.5deg)`, `30274/32768 = cos(337.5deg)` exactly. So the
"$13f8a table" is just a plain 0.703deg-resolution sine table; a port uses
`sin`/`cos` directly.

### Per-vertex maths

For grid vertex at `(col, row)` relative to the camera cell, both in
`-HALF .. +HALF` (HALF = 4 at zoom 4):

```
h  = control_plane[camCell + row*64 + col]
z  = ((h - HBIAS) * ZOOM) >> 4                    // scaled height

c  = col * ZOOM                                   // world offset, pre-rotate
r  = row * ZOOM

rx = (c*Q - r*P) >> 15                            // rotate by -theta  ($ff36..$ff4e)
ry = (r*Q + c*P) >> 15

// perspective divide  ($ff7c):  ry is the depth
d  = EYE - ry
sx = (rx * EYE) / d
sy = ((z - HORIZON) * EYE) / d + HORIZON

screenX = sx + 0x80                               // + screen centre  ($ff54)
screenY = 0x7c - sy                               // flip Y           ($ff5c)
```

All arithmetic is 16.16-ish fixed point on the 68000 (`muls`/`divs`, `>>15` via
`add.l`+`swap`). A port does it in float; the `>>15` after the rotate keeps
`rx, ry` in world-pixel units.

The projection **is perspective** (`x / (EYE - depth)`), not an affine 2:1 iso.
The "isometric" look is a fixed camera pitch baked into the fixed `HORIZON`/`EYE`
pair plus the 16-step yaw. A port that wants true axonometric can drop the
divide and the corners become an affine transform, at the cost of PM's subtle
foreshortening.

### Camera cell

`$4bb3a` / `$4bb3c` hold the camera grid cell; the projector offsets by the
command-select index `$57ffc` (normally the player, small). Effective far/anchor
corner of the visible grid:

```
camCellX = $4bb3a - $57ffc          // mission 1: 40 - 4 = 36
camCellY = $4bb3c - $57ffc          //            51 - 4 = 47
```

The grid then spans `camCell .. camCell + 2*HALF` in both axes (the camera cell
is the far/top corner of the drawn diamond, not its centre).

---

## 4. Rasterisation — two triangles per cell

`pm_render_terrain` `$f898` walks the projected grid **far → near** (painter's
order — no depth buffer). For each cell it has 4 corners `TL, TR, BL, BR` (BR =
next row, next col; the corner buffer row stride is 64 bytes = 16 longs, 9 used):

```
// quad split: follow the slope. corners are packed (screenX:16, screenY:16).
if  packed(BR) > packed(TL):
        tri(TL, TR, BL,  colour = height_plane[cell])     // "height" triangle
        tri(TR, BL, BR,  colour = type_plane[cell])       // "type"   triangle
else:
        tri(TL, TR, BR,  colour = height_plane[cell])
        tri(TL, BL, BR,  colour = type_plane[cell])
```

`colour` is the raw terrain byte. If `byte < 0x0c` add `masterTick & 3` (water).
A sloped cell shows a two-tone split because one triangle is coloured by the
height byte and the other by the type byte.

Then, still in the same per-cell step:

```
if  cell_bucket[cell] != 0:  draw_cell_entities(cell)     // §6, sprites inline
```

Because sprites are drawn immediately after their cell's terrain, in far→near
order, the painter's algorithm is free: no sprite ever floats over a hill it
should be behind.

### The fill: rolling-bitplane dither (`$ef62 → $e3e2 → $e4de`)

PowerMonger has **no flat fill and no texture map**. Every triangle span is
stippled from one ~2 KB cyclic table of 16-bit bitplane masks
(`assets/dither.bin`, base = the long at `$ff9e`):

```
// phase into the table, per triangle:
A5_bytes = (dither_base + colourByte + (topY << 4)) >> 1      // $e3e8..$e3fa
// per scanline y (from topY down):
A5_bytes += 4                                                 // $e44a: +2 u16 words
// per 16-px SCREEN-ALIGNED group in the span:
w = table_u16[ A5_bytes/2 .. A5_bytes/2 + 3 ]                 // planes 0..3
for column c in the group (bit b = 15 - (screenX & 15)):
    idx = w0.b | (w1.b << 1) | (w2.b << 2) | (w3.b << 3)
```

The cursor advances **2 words/scanline while consuming 4**, so scanline *y*'s
planes 2 & 3 are re-read as *y+1*'s planes 0 & 1 — the pattern "rolls up"
through the bitplanes, which is why the dither is 2-scanline coherent (a CRT's
line blur averages the pair). `colourByte` and `topY` are only a **phase
offset** into this one shared stream: terrain shading / height banding is a
*phase shift of a single fixed dither texture*, not distinct flat colours.

Observed result on mission 1: grass cells resolve to palette indices **11/12/13**
(the green ramp), water to **14/15** (blue), slopes pick up **1/2/3** (khaki).

**A modern port should not reproduce this.** Replace it with either:
- a flat fill using a height→palette ramp (see `flat_index()` in
  `pm_render_ref.py` — indices `[13,12,12,11,11,3,2,1]` across the land-byte
  range `0x1c..0x40`), or
- a fragment shader that samples the 16-colour palette by height with a small
  ordered-dither for the retro look.

The exact table + phase are preserved in `assets/dither.bin` for a
pixel-faithful port that wants them.

---

## 5. Zoom — 7 discrete geometry sets

Zoom is a 7-level LOD select, **not** a continuous scale and **not** an art
switch. `pm_zoom_set` `$13f60` (from the mouse-cursor dispatch) sets
`$ff9c = $13f83[index]` and calls `pm_zoom_geometry` `$fe04` with the grid
half-extent, which derives 13 constants at `$fdea..$fe02`
(`assets/tables.json → zoom_geometry`):

| index | `$ff9c` (ZOOM) | HALF (`$fdec`) | tile px (`$fdee` derives from) |
|-------|----------------|----------------|-------|
| 1 | 84 | 1 | largest |
| 2 | 42 | 2 | |
| 3 | 28 | 3 | |
| **4** | **21** | **4** | **default (mission start)** |
| 5 | 17 | 5 | |
| 6 | 14 | 6 | |
| 7 | 12 | 7 | smallest |

The 13 constants are all grid-buffer strides / loop bounds / screen offsets for
the specific `(HALF, tilePx)` pair — see `zoom_geometry.constant_meaning` in
`tables.json`. Hand-poking them is unsafe (an inconsistent stride sends the span
filler into code). A port computes its own strides from `HALF` and the tile
size; the only value that feeds the projection maths is `ZOOM` (`$ff9c`).

Every zoom draws the same triangle fill with more/fewer, larger/smaller cells.

---

## 6. Sprites

### Selection

Each entity has a `heading` byte (object record +17, 0..15 — sometimes stored
`<< 4`). `pm_pick_sprite_frame` `$16738` maps it through
`assets/headings.json` (`t_heading_frame` at `$1675a`):

```
frame = [ 0xff,5,15,8,10,5,16,0xff, 0xff,8,10,15,12,5,16,0xff ][heading & 0x0f]
0xff  => draw no sprite for this facing (the 16 headings fold to ~8 drawn
         frames + a horizontal flip)
```

### The mini-sprite blitter (`$11f82`, `assets/sprites/sheet_raw.bin`)

The little men / animals are **1-bitplane masked silhouettes**, `0x37` (55)
bytes per frame = 11 rows x 5 bytes:

```
per row: alternating (AND-mask, OR-data) bytes -> two+ 8-px columns
    D0 = 8 - (destX & 7)                       // sub-word shift
    mask = rol.w D0, next_byte                 // 1 byte -> shifted 16-bit AND mask
    data = rol.w D0, next_byte                 // 1 byte -> shifted 16-bit OR data
    dst = (dst & mask) | data                  // punch + paint one word
row stride in the back buffer: += 0x98 (after the sprite width)
```

The sprite carries no colour — it is punched into whatever plane the blitter is
pointed at, so the man's colour comes from the plane / the terrain underneath.
Anchor: the entity's projected `(screenX, screenY)` from §3, sprite drawn
up-left of the anchor (foot at the cell).

`$33000` is a **multi-category sheet** (men / animals / trees / buildings blit
at different strides). `assets/sprites/sheet_raw.bin` is the first 64 frames at
the 55-byte men stride (raw — decode with `decode_minisprite()` in
`pm_export.py`); `sheet_contact.png` is a preview. The 5-bytes-per-row split
(alternating AND-mask / OR-data) is approximate; a full per-category rip is
deferred (same as the Super Sprint sprite rip).

### HUD / selected-unit marker (`$e6ee`)

A separate wider multi-plane blitter, 32-byte glyph row stride, 4-long
descriptor table at `$e6ee+110` (`assets/hud/descriptor_table.bin`). Used for
the pulsing selected-group marker (`$165b2`, sprite toggled by `$4bb41` bit 0)
and the on-screen HUD glyphs. Not on the terrain hot path; a full rip is
deferred.

### Trees / buildings / mountains

- **Mountains are terrain** — a run of high cells, drawn by the same triangle
  fill with a high colour byte. No mountain sprites.
- **Trees / buildings are bucket sprites** (`$115e0`, their own category
  values) drawn over the cell they occupy — they pop in/out at cell granularity
  when the camera rotates.

---

## 7. Frame pipeline

Screen output is **direct-to-shifter**, double-buffered by the base register
(no XBIOS). Two compose buffers `$2df7c` (front) / `$2df78` (back), plus a
**terrain master** `$e0d4` built once per mission.

```
once per mission ($13b9a):
    build terrain master -> $12ce0 copy into both compose buffers

per simulation tick ($13000), present rate gated by $57ff0/$57fee (=1 normally):
    $1870   spin until the VBL flag                       ; frame sync
    $12ce0  copy terrain master -> back buffer            ; ~1/3 frames, movem, 500 rows
    $178ae  render setup
    $fec6   re-project grid corners  IF camera/yaw/zoom changed
    $f898   terrain: per-cell "flag & 0x80 unchanged" skip -> often near-no-op
  -- every tick --
    $14b62  entity FSM      (relinks $47970 cell buckets via $163ea)
    $6a3a   order executor
    $7a56   sprite / HUD compositor -> back buffer
    $165b2  selected-group marker
  -- at the VBL ISR --
    $187a   swap front <-> back, write (front >> 8) to $FFFF8200
```

A still camera skips the whole terrain fill (frame-diff confirmed: over 249
consecutive settled frames the palette is byte-identical and only ~77 screen
bytes change — moving sprites + the marker blink). Water only re-colours while
the camera moves.

Palette: one 16-colour shifter palette for the whole iso view
(`assets/palette.json`, `distinct_palettes: 1`). Index semantics:

| idx | RGB | role | idx | RGB | role |
|-----|-----|------|-----|-----|------|
| 0 | 0,0,0 | black / shadow | 8 | 182,72,0 | orange |
| 1-5 | khaki ramp (dark→light) | rock / paths / table | 9-10 | 182,145,36 / 218,218,36 | gold / yellow |
| 6-7 | 109,72,36 / 145,109,36 | brown (slope, earth) | 11-13 | green ramp (light→dark) | **grass** |
| — | — | — | 14-15 | 0,72,109 / 72,109,145 | **water** |

---

## 8. Faithful vs. modern

| element | faithful (emulate) | modern port |
|---------|--------------------|-------------|
| geometry | 9x9..15x15 projected grid, per-frame `divs` per corner | `ArrayMesh` heightfield, or sample `terrain.bin` in a vertex shader; project once, scroll by pixel delta |
| fill | rolling-bitplane dither from `dither.bin` | height-ramp fragment shader over the 16-colour palette, optional ordered dither for the look |
| draw order | far→near grid walk, sprites inline | **keep this** — per-cell (terrain then occupants); do not add a separate sorted sprite pass |
| zoom | 7 discrete geometry sets, `$fe04` | 7 camera distances (or continuous); same mesh |
| rotation | 16 yaw steps, `$13f8a` sine table | continuous yaw; `sin`/`cos` |
| water | `colourByte += tick&3`, fill-driven, still-camera gated | palette-index animation or a small UV scroll in the shader |
| perspective | real `x/(EYE-depth)` divide | keep for PM's look (free in a vertex shader), or go axonometric |

---

## 9. Open questions (not closed this pass)

1. **Vertical calibration of the perspective divide.** `pm_render_ref.py` with
   the constants above reproduces the island *shape and orientation* but places
   it ~15-20 px lower than the reference and slightly larger. Candidates: the
   `HORIZON`/`EYE` pair is read PC-relative in `$ff7c` and may not be exactly
   `$ff96`/`$ff98` (re-disassemble `$ff7c`'s PC-relative operands against a
   fresh linear disasm — the 74th-pass `pm74_disasm.txt` is misaligned in the
   `$e000..$f000` region); or the camera-cell offset includes a term this pass
   missed; or `screenY = 0x7c - sy` uses a different Y flip origin.
2. **Dither phase.** `dither_index()` in `pm_render_ref.py` phases `dither.bin`
   by `(colourByte + topY*16) >> 1` +`2/scanline` and lands on blue/brown
   entries, not the green ramp the reference shows. Either the table base
   (`$ff9e` = `$2e000`) is stale in this snapshot (it is shared with the sound
   mixer — capture it fresh via a `watch $ff9e` during a camera move), or the
   `>>1` in `$e3e8` means the phase is in half-units and the real word index is
   `>> 2`, or the plane→index bit order is reversed. Resolve by disassembling
   `$e3e2`/`$e4de` from a correctly-aligned image.
3. **Full sprite sheet.** `$33000` past frame ~16 is other categories at other
   strides; only the men are decoded. Same deferral as the Super Sprint rip.
4. **HUD art.** `$e6ee` descriptor table is dumped raw; the glyph sheet address
   needs resolving from a live snapshot.

None of these block starting the Godot port: items 1-2 are a camera/​shader
re-tune against a screenshot, which a modern port does anyway.

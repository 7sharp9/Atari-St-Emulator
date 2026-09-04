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

Verification status (79th pass): `tools/pm_render_ref.py --ram <settled.ram>`
ports the real quadrant-3 grid walk (`$fccc`) + the `$ef62` colour/winding
rules and renders from the game's own `$3f364` corner buffer, diffed against the
`$1c700` compose buffer in the same RAM. **~78 % exact palette index, 93 %
within ±1** over the drawn terrain (`scratchpad/pm78_settle.ram`; +12-13 pts
each on `pm74_late` / `pm70_iso` too). `walk_q3` covers **96 %** of the game's
actual per-frame terrain layer (614 px missed at edges, of 14 417).

**79th-pass correction -- there is NO "sea fill inside the iso diamond".** The
composed frame (`$1c700`) differs from the `$78000` master **only** in the
island terrain blob (idx 6/7/11/12/13, ~14.4 k px) plus a handful of sprites.
The sea (idx 14/15, ~2 460 px in the viewport) is **byte-identical** between the
composed frame and the master — it is pre-rendered into the master, which
`$13b9a` builds once at mission load. The 78th's "sea fill drawn by neither the
walk nor the master, source unmapped, main blocker" was a misdiagnosis. So a
per-frame renderer only draws the island; a from-scratch full frame composites
that over the master (which carries the HUD + border + sea + the black diamond
edge). See `assets/reference/render_faithful_composite.png`.

**79th-pass dither phase.** `dither_index()` gains `DITHER_COLOUR_BIAS = -1`
(colourByte − 1, ≡ A5 − 128): the greens came out one shade too light
everywhere; the −1 lifts exact-index 65.8 % → 78 % with within-1 unchanged (a
pure phase shift). The `$e3e6` setup formula is verified byte-exact from the
live `$f1e2` record and the roll is +8/scanline, so the −1 is in the roll/topY
term or the unmodelled `$ece2`/`$ec62`/`$eca2` sub-scanline maths, not the
setup. Kept as an explicit knob, not silently baked in.

Trace-verified (78th, still holds): the walk's cell↔corner↔colour mapping (3
sampled cells), the `$ef62` "force colourByte `0x1c`" coast rule, and the
**+64 px draw inset** (`$e420` draw pointer `$e3e2` = `buffer + 0x20` bytes; a
sweep re-confirms +64 px is the unique optimum on `pm78_settle`).

- **Projection — closed.** The reference renderer's projected 9×9 vertex grid
  reproduces the game's own `$3f364` corner buffer **byte-exact** (all 81
  vertices). The 76th-pass "island sits ~15-20 px low" was a bad diff: it
  compared against a *live* frame dump (`pm76_fr/f000100.bin`) whose camera had
  drifted a little from the RAM snapshot the geometry was read from. The
  consistent reference is the snapshot's own **back buffer `$24400`**, which
  equals `assets/reference/isoframe.png` to 231 / 64000 px (moving sprites
  only). `EYE` and `HORIZON` are confirmed `$ff98`=320 / `$ff96`=130 from the
  aligned `$ff7c` disasm (PC-relative operands `26(PC)`→`$ff98`,
  `12(PC)`/`4(PC)`→`$ff96`).
- **Dither phase — formula closed, pixel match partial.** The 77th aligned
  disasm of `$e3e6..$e4de` gives the real phase (§4). Decoding the table at
  `colourByte*128` now lands on the correct palette families: `0x24-0x2c` →
  green ramp 11/12/13, `0x08-0x0b` → water 14/15, `0x18-0x1c` → rock 1-3/6. The
  rebuilt greens match the reference distribution within ~5 % (11/12/13 =
  1649/4009/1407 px vs reference 1644/4585/912). The residual gap is the dark
  shadowed lower-left slopes (reference idx 0-2 heavy, this renderer draws them
  khaki) — that needs the yaw-quadrant quad-split corner remap (`$f97e` jump
  table) and the exact height-vs-type triangle pick, which this reference
  renderer approximates. Not pixel-exact; see `assets/reference/render_compare.png`.

Neither residual blocks a port — a modern port replaces the dither with a shader
and the yaw-quadrant split with a real mesh.

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

**Draw inset (78th).** The corners in `$3f364` are relative to the **iso window
origin**, not the screen. The `$e420` fill writes to `$e3e2` (a runtime-patched
pointer) = `compose_buffer + 0x20` bytes = **+64 screen pixels**. So the final
`screenX = $3f364.sx + 64`. The left 64 px is the HUD portrait / compass strip.
`pm_render_ref.py` reads the inset back as `($e3e2 & 0x3f) * 2`.

All arithmetic is 16.16-ish fixed point on the 68000 (`muls`/`divs`, `>>15` via
`add.l`+`swap`). A port does it in float; the `>>15` after the rotate keeps
`rx, ry` in world-pixel units.

**Verified byte-exact (77th):** running this maths in integer for the 9×9 grid
of `pm74_late.ram` (camCell 36,47; YAW 0xf0; ZOOM 21; HBIAS 4) reproduces every
one of the 81 `(screenX, screenY)` pairs in the game's own `$3f364` corner
buffer. `$ff7c`'s PC-relative operands resolve to `26(PC)`→`$ff98` (EYE) and
`12(PC)`/`4(PC)`→`$ff96` (HORIZON). The loop is 9×9 vertices at zoom 4 (`$fdec`
= HALF = 4), row/col counters `-4..+4`, `A1` walking the `$3f86c` control plane
forward from the camera cell (row stride 64), corner buffer `$3f364` row stride
64 bytes (9 × 4 used). `tools/pm_render_ref.py`'s float version matches to ≤1 px.

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

### The fill: 4bpp pattern table (`$ef62 → $e3e6 → $e4de`, 77th-pass aligned disasm)

PowerMonger has **no flat fill and no texture map**. Every triangle span is
painted from one pattern table (`assets/dither.bin`, 16 KB from `$2e000`).

```
// per triangle ($e3e6..$e3fa), from the live $f1e2 record (colour 0x1c,
// topY 75 -> A5 = $2ee58, byte-exact):
//   D6 = record[0]<<8                       ; colourByte in the HIGH byte
//   D6 += [$ffa2]  (= $5c000 = 2 * [$ff9e]) ; NB: the doubled base
//   D6 += (topY << 4) & 0xff                ; = (topY & 15) << 4  (add.b)
//   A5 = D6 >> 1
// == $2e000 + colourByte*128 + (topY & 15)*8              // BYTE address
//    [ $5c000 >> 1 == $2e000; the >>1 turns colourByte*256 into *128 ]
// per scanline (from topY down):  A5 += 8   (+4 roll $e44a, +4 edge `and.l (A5)+`)
// long0 = big-endian u32 at A5      -> plane0 = hi16, plane1 = lo16
// long1 = big-endian u32 at A5 + 4  -> plane2 = hi16, plane3 = lo16
// -- the ENTIRE span on one scanline is this ONE 16-px pattern, tiled
//    screen-X-aligned; the left/right edges only AND a partial-word coverage
//    mask ($ec62 / $eca2), the Duff-device middle ($e4de) just repeats
//    (long0, long1). So the pattern is a pure function of colourByte and y:
//        A5(y) = $2e000 + colourByte*128 + (topY & 15)*8 + 8*(y - topY)
//              = $2e000 + colourByte*128 + 8*y - 128*(topY >> 4)
for column c in the span (bit b = 15 - (screenX & 15)):
    idx = plane0.b | (plane1.b << 1) | (plane2.b << 2) | (plane3.b << 3)
```

`$5c000` (the raw `[$ffa2]` value) is a **different** table — small signed ints,
looks like a slope/delta table — not the dither patterns; it is only used here
as the doubled base constant. `pm_render_ref.py`'s `dither_index()` also carries
`DITHER_COLOUR_BIAS = -1` (79th, empirical): with the formula above the greens
render one palette step too light everywhere, and colourByte − 1 fixes it
(exact-index 65.8 % → 78 %, within-1 flat). The setup is verified exact, so the
−1 lives in the roll/topY term or the unmodelled `$ece2` sub-scanline offset.

`colourByte` is the raw terrain byte (`$f9ae` / handler variants: height plane
`$438ee-8257` for one triangle, type plane `$438ee+0` for the other), **+
`[$4bb3e] & 3`** if `< 0x0c` (water shimmer — a fixed +2 in the reference
frame, not `tick&3`). Each `colourByte` owns a **128-byte slot = 16 eight-byte
sub-patterns**; `(topY & 15)` picks the start and the `+8/scanline` roll walks
through them, and a triangle tall enough to leave its slot reads the next
colour's — the vertical shading gradient.

`pm_render_ref.py`'s `dither_index()` now implements this exactly; the residual
diff is the missing sea + dark slopes, which come from the yaw-quadrant grid
walk (below) selecting different cells than the naive `(camCell + gc, gr)`.

Decoding `assets/dither.bin` at `colourByte*128` (verified against reference
pixels):

| colourByte | palette indices | terrain |
|-----------|-----------------|---------|
| `0x08`–`0x0b` | 14, 15 (+ 4) | water |
| `0x18`–`0x1c` | 1, 2, 3, 6 | rock / dark earth |
| `0x24`–`0x28` | 13, 12 | grass (dark→mid) |
| `0x2c` | 11, 12 | grass (light) |
| `0x30`–`0x3c` | 7, 9, 11, 12 mixed | bright slope |
| `0x3e` | 9, 10, 11 | brightest ridge |

### The yaw-quadrant grid walk (`$f898` → `$f97e` → 4 handlers)

`$f898` picks one of four grid-walk handlers by rotation quadrant:

```
q = ((YAW + 8) >> 5) & 6           // yaw 0xf0 -> q = 6 -> handler index 3
handler = [$f98c, $fa98, $fbb2, $fccc][q >> 1]     // jump via the $f986 word table
```

Each handler walks the **projected corner buffer `$3f364` and the terrain
planes `$438ee` together**, but with a quadrant-specific **start offset**
(`A0 += $fe02`, `A1 += $fdf0` …), **iteration count** (`$fdf0` = 7, not 8) and
**corner→triangle-vertex assignment** (`(A0)`, `4(A0)`, `64(A0)`, `68(A0)` in
different D0/D1/D2 slots), so the far→near painter order stays correct as the
camera rotates. This is why `pm_render_ref.py`'s naive
`cell(camCell + gc, camCell + gr)` walk draws a slightly different cell set
(and misses the sea wedge + the shadowed NW slope) — it always uses the
quadrant-0 assignment. Porting the four handlers is the remaining work for a
pixel-exact terrain layer.

**Quadrant 3 (`$fccc`), fully ported + trace-verified (78th).** The walk is
`for k in 0..7 (D7): for j in 0..7 (D6)`, `A0` at `$3f364 + $fe02(=0x1c=28 B =
corner col 7)`, `A1` at the type plane `$438ee + camCell + 7`, both advancing
`+64` per inner step (corner row +1 / cellY +1) and `-513` / `-516` per outer
step (cellX -1 / corner col -1). So

```
cell (cx, cy)   = (camCellX + col, camCellY + row)     col = 7-k, row = j
corner names    C00=(A0)  C10=4(A0)  C01=64(A0)  C11=68(A0)   [(row,col) .. (row+1,col+1)]
```

Per cell, `8257(A1)` bit 7 (**not** "corner unmoved" -- it is the **diagonal
selector**, a per-cell heightmap-derived bit; both branches draw):

```
bit 7 CLEAR ($fcea): split on the C00-C11 diagonal
    $ef62(C10, C11, C00, colour = type_plane[cell])       // NE triangle
    $ef62(C01, C00, C11, colour = height_plane[cell])     // SW triangle
bit 7 SET   ($fd2e): split on the C10-C01 diagonal, sub-order by packed(C01) vs packed(C10)
    if packed(C01) <= packed(C10):
        $ef62(C00, C10, C01, height) ; $ef62(C11, C01, C10, type)
    else:
        $ef62(C11, C01, C10, type)   ; $ef62(C00, C10, C01, height)
```

colour = `type_plane` (`$438ee+0`) or `height_plane` (`$438ee-8257`), `+
[$4bb3e]&3` if `< 0x0c`. **Verified** against a live trace at cells (43,47),
(38,47), (37,47): the corner indices, the flag-bit branch, and both plane reads
match byte-for-byte. `pm_render_ref.py`'s `walk_q3` is this, exactly.

### `$ef62` -- the "force `0x1c`" rule (78th, trace-verified)

`$ef62` writes `colourByte` to the record at `$efd8` **before** the flat/general
split, then at `$f06c`/`$f154` it forces the record's colour byte to **`0x1c`**
(dark khaki, dither slot 0x1c → palette 1-3) whenever the input winding already
has vertex 1 on the **left** (general: edge-2 slope > edge-1 slope; flat-top:
`sx1 < sx0`). This is not a bug -- it is how PM shades the **coastal / front
triangles** dark. Trace: cell (37,47)'s SW triangle entered `$ef62` with
`colourByte = 0x2b` (green) and reached `$e3e6` with the record holding `0x1c`.
`pm_render_ref.py`'s `ef62_raster` implements both variants.

### The triangle rasteriser (`$ef62` → `$e420`)

`$ef62` builds a span record at `$f1e2` and `bra`s into `$e3e6`:

| off | field | from |
|-----|-------|------|
| 0 | colour byte (or `0x1c` for a flagged variant) | `$efd8` / `$f07a` |
| 1 | 0 (pad) | — |
| 2 | top screen-Y | `$efdc` |
| 4, 6 | top screen-X (both edge X accumulators, 16.16) | `$eff8` |
| 8, 14 | edge segment 1 / 2 heights | `$f080` |
| 10, 16 | edge 1 / 2 X-slope, **16.8 fixed** (`$f000`: `divu` after `lsl.l #8`) | `$f088` |
| 20 | mid-segment height (the Y where the short edge switches) | `$f09c` |
| 22 | slope-of-slope for the second segment | `$f0da` |

`$e420` is the DDA span walker: two edge X accumulators stepped by their
16.8 slopes each scanline, the slope reloaded from a `(run:u16, slope:i32)`
stream in `A0` when its run counter `D7` expires; per scanline it converts the
two fixed X's to byte offsets through `$ece2` (`[0]*16 + [8]*16`), clips, then
fills:

- **width 0** (one cluster): `$e470`, `mask = leftMask[$ec62] & rightMask[$eca2]`
- **wide**: left cluster (`$ec62` mask) → Duff-device middle (`$e4de`, tiles
  `long0/long1` from `movem.l (A5)`) → right cluster (`$eca2` mask)

`$ec62` (16 longs, `0xffffffff, 0x7fff7fff, … 0x00010001`) clears the leftmost
`k` bits; `$eca2` (`0x80008000, 0xc000c000, … 0xffffffff`) keeps the leftmost
`k+1` — the two partial-word edge-coverage masks, each replicated into both
words of the long (same mask for the plane pair). `k = (accumulator >> 1) & 15`.

**Coordinate resolution (78th).** The X accumulators `D4`/`D5` start at the
record's `topX` (integer screen X, e.g. 54) and each scanline do
`D = swap(swap(D) + slope)` (16.8 slope in the low word, integer carry into the
high word) plus a transient `lsr.w #1` / `add.w D4,D4` around the table lookup.
Net: `D4.w` at the lookup = `2 * screenX`. `$ece2` is **word-indexed** (byte
offset `2*screenX` → word `screenX`), and `$ece2[screenX] = (screenX >> 4) * 8`
bytes = the containing 16-px cluster. **The `2×` and the word-index cancel:
`screen_x == corner_sx` (+ the §3 inset), no scale.** An earlier "factor of 2"
worry is closed. `pm_render_ref.py` uses a plain `floor()`'d span (no DDA); a
pixel-exact port needs the `slope`-stepped accumulator + the `$ec62`/`$eca2`
partial-word masks + the `$e4de` Duff middle, but the *coordinate mapping* is
now settled.

Decoding `assets/dither.bin` at `colourByte*128` (verified against reference
pixels):

| colourByte | palette indices | terrain |
|-----------|-----------------|---------|
| `0x00` | 14, 15 | **open sea** (this is how water is drawn — colourByte 0, not a water flag) |
| `0x08`–`0x0b` | 14, 15 (+ 4) | shallow water |
| `0x18`–`0x1c` | 1, 2, 3, 6 | rock / dark earth |
| `0x24`–`0x28` | 13, 12 | grass (dark→mid) |
| `0x2c` | 11, 12 | grass (light) |
| `0x30`–`0x3c` | 7, 9, 11, 12 mixed | bright slope |
| `0x3e` | 9, 10, 11 | brightest ridge |

`pm_render_ref.py` now phases the dither exactly per scanline; the residual is
the quadrant grid walk (above) — the pixel-exact terrain layer is the 78th's
first job.

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

### Category dispatch (`$115e0`, 77th-pass trace)

Per bucket entity, `$115e0` reads object-record **byte 6 = category** and calls
two per-category handlers via jump tables:

| table | addr | target = base + `word[addr + cat]` | role |
|-------|------|-----------|------|
| 1 | `$1162e` | `cat 0`→`$11c8a`, `4`→`$11a86`, `2`→`$1168c`, `3`/`12`→`$117b0`, `5`→`$11772`, `6`→`$11bbc`, `7`→`$11bf4`, `8`→`$1192e`, `9`→`$11c36`, `10`→`$11b3c`, `11`→`$11b2a`, `13`→`$1174e`, `14`→`$11b0c`, `15`→`$1198a` | position / prepare |
| 2 | `$1165a` | `cat 0`→`$1187c` (men-special); `4,5,7,8,11,12,13,14,15,18`→`$11f78` (≈ `$11f82`); `+17`→`$1168a`; `+19`→`$12258` | blit |

`cat 0` = men, `cat 4` = animals; the rest are trees / buildings / effects /
markers. Which frame each handler picks (from `$16754`, the heading table, and
the entity mode) → still to be mapped into `assets/sprite_triggers.json`.

### The mini-sprite blitter (`$11f82`, `assets/sprites/sheet_raw.bin`)

**77th-pass, from the aligned `$11fe4`–`$12034` loop.** Each frame is an
**8 × 11 four-bitplane (16-colour) sprite**, `0x37` (55) bytes = 11 rows of
**5 bytes: `[AND-mask, plane0, plane1, plane2, plane3]`**:

```
A1 = $33000 + frame*0x37
D0 = 8 - (screenX & 15)                         // sub-word rotate ($11fe4 case, X&15<8;
                                                //  $12036 handles ==8, $12070 handles >8)
per row:
    mask = rol.w D0, (0xFF00 | mask_byte)       // D2 = -1 first -> vacated bits keep bg
    for plane in 0..3:
        data = rol.w D0, plane_byte
        screen_word[plane] = (screen_word[plane] & mask) | data
    A0 += 0x98                                  // + 152 = 160 (screen row) - 8 already stepped
```

`dst = (dst & mask) | data`, so a pixel is **opaque where the mask bit is 0**.
The 4 planes are the 4 interleaved screen words of one 16-px group → a real
16-colour sprite, not a silhouette. Anchor: the entity's projected
`(screenX, screenY)` from §3, drawn up-left of the anchor (foot at the cell).

`assets/sprites/sheet_contact.png` (first 64 frames) decodes cleanly as the
little men: **4 faction-colour blocks of 16** (khaki / blue / orange / yellow),
each block = 8 headings × {stand, walk}. `$33000` continues past frame 64 with
the animal / tree / building / effect categories at the same 55-byte stride;
each category's frame base + count lives in its `$1162e` handler and is not yet
ripped.

Two frame-selection paths exist and are not fully separated: `$16738` computes
`t_heading_frame[heading + flipHalf]` (16-entry table at `$1675a`, `flipHalf` =
0 or 8) and blits via **`$e6ee`**; `$115e0`'s category dispatch blits via
`$11f82`. Which path draws the terrain men vs. the marker/overlay still needs a
trace.

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

**The `$78000` master (78th trace, 79th corrected).** `$12ce0` copies from
`A0 = $78000` (32000 B) to the back buffer every ~3rd frame. `$78000` is the
**HUD + stone border + the pre-rendered open sea + a hole where the island
goes** — built once at mission load by `$13b9a`. It is NOT "a solid black
diamond with no terrain": the sea (palette idx 14/15) is baked into it.

Per frame, `$f898` redraws **only the island** into that hole (verified: the
composed `$1c700` buffer differs from the `$78000` master **only** in idx
6/7/11/12/13 pixels — the island — plus a few unit sprites; the ~2 460 water
pixels in the viewport are byte-identical to the master across `pm78_settle` /
`pm74_late` / `pm70_iso`). On a still camera `$f898` skips cells whose projected
corners did not move, so even the island mostly persists from earlier frames.

Consequence for a port: the per-frame renderer draws the projected 8×8 terrain
grid and nothing else. A from-scratch full frame composites that over the master
(HUD + border + sea). The `$f922` `jsr $11f82` with frame `0x149` and
`D0 = camCellX-3` is **not** a sea fill — `$11f82` is the 8×11 four-plane
mini-sprite blitter (`mulu #$37,D2`, `$33000` base, D0/D1 = screen x/y), so this
draws sprite frame 329 at a camera-derived screen position (a small overlay /
marker).

```
once per mission ($13b9a):
    build the $78000 master (HUD + stone border + open sea + island-shaped hole)
    -> $12ce0 copy into both compose buffers

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
| fill | 4bpp pattern table `dither.bin`, indexed `colourByte*128 + (topY&15)*8`, rolling | height-ramp fragment shader over the 16-colour palette, optional ordered dither for the look |
| draw order | far→near grid walk, sprites inline | **keep this** — per-cell (terrain then occupants); do not add a separate sorted sprite pass |
| zoom | 7 discrete geometry sets, `$fe04` | 7 camera distances (or continuous); same mesh |
| rotation | 16 yaw steps, `$13f8a` sine table | continuous yaw; `sin`/`cos` |
| water | `colourByte += [$4bb3e]&3`, fill-driven, still-camera gated | palette-index animation or a small UV scroll in the shader |
| perspective | real `x/(EYE-depth)` divide | keep for PM's look (free in a vertex shader), or go axonometric |

---

## 9. Open questions

1. **Quadrant-3 walk + projection — CLOSED (78th), coverage confirmed (79th).**
   `pm_render_ref.py --ram` ports `$fccc` exactly (cell↔corner↔colour, the
   flag-bit diagonal, both plane reads -- all trace-verified) and the `$ef62`
   colour/winding rules, reads the game's own `$3f364` corners, applies the
   **+64 px §3 inset**, and covers **96 %** of the game's real per-frame terrain
   layer (composed frame vs the `$78000` master; 614 / 14 417 px missed at
   edges), scoring **~78 % exact / 93 % within ±1** palette index. The other
   three quadrant handlers (`$f98c`/`$fa98`/`$fbb2`, yaw ≠ 0xf0) are
   disassembled (§4) but not ported -- only needed for camera rotation.
   **The "sea fill inside the diamond" (78th's open item) does not exist** — the
   sea is baked into the `$78000` master (§7). **Still open for pixel-exact:**
   - `$e420`'s **sub-pixel edge coverage** (`$ec62`/`$eca2` masks + the
     slope-stepped accumulator; `pm_render_ref.py` uses `floor()`'d spans) —
     accounts for the NE-edge diff band,
   - the dither phase: `DITHER_COLOUR_BIAS = -1` is an empirical fix (65.8 % →
     78 %); the residual is the brightest ridges (idx 13 over-drawn) and the
     dark `0x1c` coast triangles (game spreads idx 1-7, port draws ~idx 1 flat).
2. **Dither phase — formula CLOSED (77th), −1 phase knob (79th).** Full span
   walker disassembled (`$e3e6`→`$e5a6`). Real phase (§4):
   `A5(y) = $2e000 + colourByte*128 + (topY & 15)*8 + 8*(y - topY)` — verified
   byte-exact against the live `$f1e2` record (`[$ffa2]` = `$5c000` doubled base,
   `>>1`). The whole span on one scanline is a single 16-px pattern (`long0` @ A5
   = planes {0,1}, `long1` @ A5+4 = planes {2,3}), tiled screen-X-aligned; edges
   only AND a partial-word mask (`$ec62`/`$eca2`). `dither_index()` implements
   this; a uniform `colourByte − 1` was still needed empirically (greens one step
   too light) — narrowed to the roll/topY term, not the setup.
3. **Full sprite sheet — category dispatch mapped (77th), rip still deferred.**
   `$115e0` dispatches on object-record byte 6 (category) through two jump
   tables: **table 1 `$1162e`** (16 per-category "prepare" handlers —
   `cat 0`→`$11c8a` men, `cat 4`→`$11a86` animals, `cat 2`→`$1168c`,
   `cat 3`/`12`→`$117b0`, `cat 5`→`$11772`, `cat 6`→`$11bbc`, `cat 7`→`$11bf4`,
   `cat 8`→`$1192e`, `cat 9`→`$11c36`, `cat 10`→`$11b3c`, `cat 11`→`$11b2a`,
   `cat 13`→`$1174e`, `cat 14`→`$11b0c`, `cat 15`→`$1198a`) and **table 2
   `$1165a`** (blitter: `cat 0`→`$1187c` men-special, most others→`$11f78`
   ≈ the `$11f82` mini-sprite blitter, `+17`→`$1168a`, `+19`→`$12258`).
   `$11f82` decode is **closed** (aligned `$11fe4`–`$12034`): 8 × 11, four
   bitplanes, 5 bytes/row `[mask, p0, p1, p2, p3]`, opaque where mask bit 0,
   `rol.w (8 - (screenX & 15))`, dest row stride `0x98`. `sheet_contact.png`
   decodes as the men (4 faction-colour blocks of 16). Still open: the
   per-category frame base/count in each `$1162e` handler, and which of
   `$16738`→`$e6ee` vs `$115e0`→`$11f82` draws the terrain men.
4. **HUD art.** `$e6ee` descriptor table dumped raw; glyph sheet address still
   needs resolving from a live snapshot. Deferred.
5. **Border / stone-table master, world-map minimap + compass panel.** Not
   started — `$e0d4` master + the left-strip compositor. Deferred.

None of items 3-5 block the Godot port (terrain + camera are the port's spine).

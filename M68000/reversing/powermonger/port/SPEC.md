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

Verification status (83rd pass): **all 4 yaw-quadrant grid-walk handlers are
now ported** (`Fill.walkQ0`/`walkQ1`/`walkQ2`/`walkQ3`, dispatched by
`Fill.walk` the same way `$f97e`/`$f982` picks a handler from yaw) and wired
into `TerrainView.cs` — PageUp/PageDown rotate the live camera through all 16
yaw steps. `walkQ0`/`walkQ1`/`walkQ2` are each live-trace-verified against a
real RAM capture at that quadrant's yaw range (register dump at the first
`$ef62` call matched the predicted vertex/colour assignment exactly — see §4
and `powermonger.sym`) and cross-checked byte-exact against a synthetic-data
F#-vs-Python run (`scratchpad/pm83_synth_check.{py,fsx}`, every CLEAR/SET and
both comparison directions exercised). **Also fixed a stale-address bug**:
the three handlers' entry points were recorded as `$f98c`/`$fa98`/`$fbb2` by
an earlier pass's imprecise read — the real jump table at `$f986` (read via
`jmp 2(PC,D0.w)`) gives `$f98e`/`$fa9a`/`$fbb4`; the old addresses landed on
the RTS of the *preceding* handler (or, for `$f98c`, a byte inside the table
itself). Re-verified live in Godot with real GPU screenshots at yaw steps 3
(quadrant 0) and 11 (quadrant 2) — two more distinct island silhouettes from
the same `RenderFrame()` path (`assets/reference/godot_screenshot_yaw{3_q0,
11_q2}.png`).

Verification status (82nd pass): `Fill.walkQ3` + `Projection.projectGrid` are
**wired into and run live inside Godot 4.7.2-stable mono**
(`port/godot/game/TerrainView.cs`, the software-layer shape — a `TextureRect`
fed an `Image` built per-frame from `Fill.Buffer` through `assets/palette.json`).
Verified with real screenshots (`--write-movie`, GPU-rendered, not headless —
see `assets/reference/godot_screenshot_*.png`), at two different camera cells,
proving live re-projection/re-rasterisation, not a static blit. Fixed a real
structural bug found in the process: `Godot.NET.Sdk` writes its build output
relative to the **csproj's own directory**, not the Godot project root, so a
csproj inside `game/` (the skeleton's original layout) never loads at runtime
("Cannot instantiate C# script ... class could not be found") — the csproj now
lives at the Godot project root (`port/godot/PowerMongerPort.csproj`), sources
stay in `game/`. See `port/README.md` "Verification (82nd pass)".

Verification status (81st pass): the rasteriser this section documents is now
ported to F# — `port/godot/logic/Fill.fs`'s `walkQ3`/`ef62Raster`/`fixedSlope`/
`ditherIndex` are a 1:1 port of the functions below, cross-checked byte-exact
against `pm_render_ref.py` on synthetic triangles/grids (every code path: general
split, flat-top, the `$f134` reorder, the coast-force, the mid-vertex switch,
water shimmer, both `walk_q3` diagonal branches).

Verification status (80th pass): `tools/pm_render_ref.py --ram <settled.ram>`
ports the real quadrant-3 grid walk (`$fccc`) + the `$ef62` triangle setup +
the `$e420` 16.16 DDA span walker, and renders from the game's own `$3f364`
corner buffer, diffed against the `$1c700` compose buffer in the same RAM.
**~94 % exact palette index, ~95 % within ±1** over the drawn terrain
(`scratchpad/pm78_settle.ram`; `pm74_late` 93.9 %, `pm70_iso` 93.4 %). The
residual is: unit sprites on the hill (`walk_q3` draws terrain only), the tall
`0x1c` coast slopes (the game spreads idx 1-7, the port lands nearer flat), and
a ~1 px NE island edge.

**80th-pass DDA + dither wrap.** `_fixed_slope` (`$f000`) + `_dda_walk`
(`$e420`) replace the float+`floor()`'d spans of the 79th. Two 16.16 edge X
accumulators, one slope per scanline, the shorter edge bending toward the far
vertex at its own scanline; the `$ec62`/`$eca2` partial-word masks reduce to
"draw pixel x iff `ixL <= x <= ixR`" (`ixL`/`ixR` = accumulators truncated
`>>16`). And the dither phase, live-traced from `$e420`: **A5 wraps modulo 128
inside the colour's 128-byte slot** (the `$e44a` roll's `addq.b #8` on `2*A5`
byte-overflows at `A5 & 0x7f == 124`), so

```
A5 = $2e000 + colourByte*128 + ((8 * y) mod 128)          (y = absolute scanline)
```

— the `topY` term drops out entirely. This kills the 79th's empirical
`DITHER_COLOUR_BIAS = -1` (which was compensating for the missing wrap, and was
only right for 16-32 px-tall triangles). Exact-index 78 % → 94 %.

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
- **Dither phase — closed (80th).** Live single-step of `$e420` (cell topY 75,
  colourByte `0x26`): `A5 = 2f358 2f360 2f368 2f370 2f378 → 2f300 2f308 …` — it
  wraps back to the start of the colour's 128-byte slot, never advancing to slot
  `cb+1`. So `A5 = $2e000 + colourByte*128 + ((8*y) mod 128)` (y = absolute
  scanline). The 77th's `+ (topY&15)*8 + 8*(y-topY)` was right for the first
  slot but the wrap makes the `topY` term vanish under mod 128. The greens now
  match: 11/12/13 = 2212/7928/2581 px vs reference 2057/7528/2519.
- **Span endpoints — closed (80th).** The `$e420` 16.16 DDA is ported
  (`_fixed_slope` `$f000`, `_dda_walk`); the `$ec62`/`$eca2` partial-word masks
  are provably equivalent to a hard `ixL <= x <= ixR` per-pixel span.

Residual (≈6 %): unit sprites (out of scope for the terrain walk), the tall
`0x1c` coast slopes (game dithers idx 1-7, port lands nearer flat), a ~1 px NE
edge. None blocks a port — a modern port replaces the dither with a shader.

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
| **flag** | `$438ee + 8257` | bit 7 = **diagonal selector** (78th-pass correction — earlier read as "corners unmoved, skip fill"; see section 4) |
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

**The clip check runs on the RAW, pre-inset value (85th).** `$ef62`'s own
`screenX <= 255` clip (§4) applies to `$3f364.sx` directly, before the `+64`
above -- i.e. the real window is `raw sx in [0,255]`, which is `absolute
screenX in [64,319]`, not `[0,255]`. `pm_render_ref.py`'s `--ram` path used to
apply the `<=255` bound to the already-inset-shifted coordinate, truncating
the true window's right ~64 px on every score; fixed by threading `x_inset`
through `ef62_raster`/`_dda_walk` so the clip bound shifts with the
coordinate space it's given (`port/README.md` 85th). `Fill.fs`/`Projection.fs`
never had this bug -- they stay in raw space throughout, matching `$ef62`
itself -- but `TerrainView.cs`'s blit read the buffer at `(x,y)` instead of
`(x-64,y)`, which is the same bug at the opposite end of the pipeline (fixed
the same pass, verified with a real screenshot).

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

### The fill: 4bpp pattern table (`$ef62 → $e3e6 → $e420`)

PowerMonger has **no flat fill and no texture map**. Every triangle span is
painted from one pattern table (`assets/dither.bin`, 16 KB from `$2e000`).

Setup, per triangle (`$e3e6..$e3fa`): `A5 = ([$ffa2] + record[0]<<8 +
((topY<<4) & 0xff)) >> 1`. `record[0]<<8` is `colourByte*256` (big-endian, byte
1 is the pad); `[$ffa2]` = `$5c000` = `2*[$ff9e]` = `2*$2e000` (the raw `$5c000`
is a *different* small-int table, used here only as the doubled base); the
`add.b` puts `(topY & 15)*16` in the low byte; the `>>1` halves everything. So
the first scanline reads `$2e000 + colourByte*128 + (topY & 15)*8`.

**Per scanline the roll advances `+8` but wraps modulo 128 inside the colour's
slot** (80th, live single-step of `$e420`: `A5 = 2f358 2f360 2f368 2f370 2f378
→ 2f300 …`). The `$e44a` roll does `add.b #8` on the low byte of `2*A5`, which
byte-overflows at `A5 & 0x7f == 124`, pinning `A5` in `[slotBase, slotBase+128)`.
So the phase is:

```
A5 = $2e000 + colourByte*128 + ((8 * y) mod 128)          // y = absolute scanline
long0 = big-endian u32 @ A5      -> plane0 = hi16, plane1 = lo16
long1 = big-endian u32 @ A5 + 4  -> plane2 = hi16, plane3 = lo16
for x in the span (bit b = 15 - (x & 15)):
    idx = plane0.b | plane1.b<<1 | plane2.b<<2 | plane3.b<<3
```

The whole span on one scanline is that ONE 16-px pattern, tiled screen-X-aligned
(the `$e4de` Duff middle just repeats `long0, long1`; the edges AND a
partial-word mask — see the DDA section). `colourByte` owns a **128-byte slot =
16 eight-byte sub-patterns**; `(8*y) mod 128` cycles through all 16 with period
16 scanlines. The 77th's `(topY&15)*8 + 8*(y-topY)` form is equivalent for the
first slot; the mod-128 wrap makes the `topY` term drop out (`128*(topY>>4)` ≡ 0
mod 128). This killed the 79th's empirical `DITHER_COLOUR_BIAS = -1`.

`colourByte` is the raw terrain byte (height plane `$438ee-8257` for one
triangle, type plane `$438ee+0` for the other), **+ `[$4bb3e] & 3`** if `< 0x0c`
(water shimmer), or forced to `0x1c` by the `$ef62` coast rule (below).

Decoding `assets/dither.bin` at `colourByte*128` (verified against reference
pixels):

| colourByte | palette indices | terrain |
|-----------|-----------------|---------|
| `0x00` | 14, 15 | **open sea** (colourByte 0, not a water flag) |
| `0x08`–`0x0b` | 14, 15 (+ 4) | shallow water |
| `0x18`–`0x1c` | 1, 2, 3, 6 | rock / dark earth / coast shading |
| `0x24`–`0x28` | 13, 12 | grass (dark→mid) |
| `0x2c` | 11, 12 | grass (light) |
| `0x30`–`0x3c` | 7, 9, 11, 12 mixed | bright slope |
| `0x3e` | 9, 10, 11 | brightest ridge |

### The yaw-quadrant grid walk (`$f898` → `$f97e` → 4 handlers)

`$f898` picks one of four grid-walk handlers by rotation quadrant:

```
q = ((YAW + 8) >> 5) & 6           // yaw 0xf0 -> q = 6 -> handler index 3
handler = [$f98e, $fa9a, $fbb4, $fccc][q >> 1]     // jump via the $f986 word table
```

(83rd pass: the entry points are `$f98e`/`$fa9a`/`$fbb4`/`$fccc`, read exactly
from the jump table at `$f986` — `jmp 2(PC,D0.w)` with offsets `$8`/`$114`/
`$22e`/`$346` from `$f986` itself. Earlier passes recorded `$f98c`/`$fa98`/
`$fbb2`, each 2 bytes low: those land on the RTS of the *preceding* handler
(`$fbb2`/`$fa98`), or, for `$f98c`, a byte inside the jump table.)

Each handler walks the **projected corner buffer `$3f364` and the terrain
planes `$438ee` together**, but with a quadrant-specific **start offset**
(`A0 += $fe02`, `A1 += $fdf0` …), **iteration count** (`$fdf0` = 7, not 8) and
**corner→triangle-vertex assignment** (`(A0)`, `4(A0)`, `64(A0)`, `68(A0)` in
different D0/D1/D2 slots), so the far→near painter order stays correct as the
camera rotates. This is why `pm_render_ref.py`'s naive
`cell(camCell + gc, camCell + gr)` walk draws a slightly different cell set
(and misses the sea wedge + the shadowed NW slope) — it always uses the
quadrant-0 assignment.

**All 4 handlers are ported (83rd pass)** — `pm_render_ref.py`'s `walk_q0` /
`walk_q1` / `walk_q2` / `walk_q3`, dispatched by `walk_by_yaw`, and their F#
twins `Fill.walkQ0`/`walkQ1`/`walkQ2`/`walkQ3` behind `Fill.walk`. Each cell's
corners are named the same way as q3's (`C00`/`C10`/`C01`/`C11` = the 2×2
corner block for that cell — see the q3 write-up below); only the loop order,
start point, and which branch (CLEAR vs SET) carries the sub-order comparison
differ:

| quadrant | yaw range | outer loop | inner loop | cell (cx,cy) | CLEAR branch | SET branch |
|----------|-----------|-----------|-----------|--------------|--------------|------------|
| q0 (`$f98e`) | `$00-$30` | row 0→7 (N→S) | col 0→7 (W→E) | `(camX+col, camY+row)` | split C00-C11, sub-order by packed(C00) vs packed(C11) | unconditional, split C10-C01 |
| q1 (`$fa9a`) | `$40-$70` | col 0→7 (W→E) | row 7→0 (S→N) | `(camX+col, camY+row)` | unconditional, split C00-C11 | split C10-C01, sub-order by packed(C01) vs packed(C10) |
| q2 (`$fbb4`) | `$80-$b0` | row 7→0 (S→N) | col 7→0 (E→W) | `(camX+col, camY+row)` | split C00-C11, sub-order by packed(C00) vs packed(C11) | unconditional, split C10-C01 |
| q3 (`$fccc`) | `$c0-$f0` | col 7→0 (E→W) | row 0→7 (N→S) | `(camX+col, camY+row)` | unconditional, split C00-C11 | split C10-C01, sub-order by packed(C01) vs packed(C10) |

q0/q2 and q1/q3 pair up (same CLEAR/SET shape, mirrored start point and loop
direction) — a symmetry that fell out of the derivation, not an assumption
going in. **Trace-verified (83rd)**: for each of q0/q1/q2, a live RAM capture
at a yaw in that quadrant's range (`scratchpad/pm83_q{0,1,2}c.ram`, rotated
via the keypad-poke recipe below) plus a register dump at the first `$ef62`
call after resuming to the settled PC matched the derived vertex assignment
and colour-plane choice (type vs height) exactly — e.g. q1 at cell (40,50):
`D0=C01 D1=C00 D2=C11 D3=$29`, and `hgt(40,50) == $29`. Cross-checked
byte-exact against the F# port on synthetic data exercising every branch
(`scratchpad/pm83_synth_check.py` / `.fsx`).

**Not modelled by this table**: the residual ~6% rasteriser inaccuracy (the
`0x1c` coast slope's multi-segment dither spread, §9 item 1) is *more*
exposed at non-`$f0` yaws — q0/q1/q2 scored 35-50% exact-index against their
own live captures (vs q3's 94%) despite the geometry trace-verifying exactly,
because a different camera angle puts more triangle edges into the unmodelled
tall-coast-slope case. This is the same known `ef62Raster`/DDA limitation,
not a new bug in the quadrant walk — see §9 item 1.

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

### The triangle rasteriser (`$ef62` → `$e3e6` → `$e420`)

`$ef62`: clip each vertex (`screenX <= 255`, `screenY <= 199`, else `$f202`
clips + re-submits); cyclic-rotate the min-Y vertex to the front (**not** a full
sort — the other two keep cyclic order); build a span record at `$f1e2`; `bra`
into `$e3e6`.

| off | field | notes |
|-----|-------|-------|
| 0   | colour byte (or `0x1c`, coast rule) | `$efd8` / `$f07a` / `$f15a` |
| 2   | top screen-Y (integer word) | |
| 4, 6 | left / right edge X start (integer word) | equal for a general tri (apex), differ for a flat-top |
| 8, 14 | left / right edge run in scanlines | |
| 10, 16 | left / right edge X-slope, **16.16 fixed** (`$f000`) | high word = int part, low = fraction; the accumulator is stored swapped |
| 20, 22 | 2nd-segment run + slope | the shorter edge reloads to this at its own scanline |

**The `$f000` slope** (`_fixed_slope`): steep (`dy <= |dx|`) →
`((|dx|<<8) // dy) << 8` (truncates *before* the `<<8`); shallow →
`(|dx|<<16) // dy`; sign from `dx`; `divu` overflow clamps to exactly `$10000`.

**The `0x1c` coast rule** (`$f072` / `$f154`): `$ef62` forces the record colour
to `0x1c` (dark, dither slot → palette 1-7) whenever the mid vertex is already
the **left** vertex (general: `slope(top→bot) > slope(top→mid)`; flat-top:
`sx_right < sx_left`). This is how PM shades the coastal / front-facing slopes
dark. Trace: cell (37,47)'s SW triangle enters with `colourByte = 0x2b` (green)
and reaches `$e3e6` with `0x1c`.

**`$e420` — the DDA span walker.** Two 16.16 X accumulators (`D4` left, `D5`
right), each `+= slope` per scanline; scanline 0 uses the start X with no step
(`$e41a bra $e456`). Each edge decrements its run counter; whichever expires
first consumes `record[20]/[22]` and switches slope (the shorter edge bending
toward the far vertex). Per scanline: `ixL = D4 >> 16`, `ixR = D5 >> 16`; abort
the triangle if `ixR < ixL` (`$e468`).

The span is written with two partial-word masks: `$ec62[ixL & 15]` clears the
leftmost `ixL&15` bits of the left cluster, `$eca2[ixR & 15]` keeps the leftmost
`(ixR&15)+1` of the right cluster (`$ece2[ix] = (ix>>4)*8` = the cluster's byte
offset in the row; `A6` base = `$ece2`, so `$ec62 = A6-128`, `$eca2 = A6-64`).
Middle clusters are full. **This reduces exactly to: draw pixel x iff
`ixL <= x <= ixR`** — a per-pixel index buffer needs no planar masking.

**Coordinate resolution (78th, still holds):** the accumulator's `2*screenX`
and `$ece2`'s word indexing cancel, so `screen_x == corner_sx` + the §3 inset,
no scale.

`pm_render_ref.py`'s `_fixed_slope` + `_dda_walk` port all of this; `ef62_raster`
does the record build + the `0x1c` rule. ~94 % exact palette index.

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

### Two separate sprite paths — settled by a live trace (87th)

The 87th pass live-traced one frame of `scratchpad/pm78_settle.snap` to answer
the long-standing "which path draws the terrain men" question. The answer:

- **`$115e0` (`pm_draw_cell_entities`) is the iso-terrain entity path.** It is
  called **inline, per cell, from the terrain grid-walk handler** (`$fccc` for
  q3, at `$fdbc`) — right after that cell's two triangles are filled, in
  far→near painter's order. So a man / animal / tree / building is composited
  immediately over its own cell's terrain and correctly occluded by nearer
  cells drawn later. This draws **everything that stands on the hill.**
- **`$16738` → `$e6ee` is NOT that path.** In `pm78_settle` it fires only from
  `$165b2` (the selected-group marker) — a flat scan over every object record
  (`$16626` loop, stride 50, to `$57f66`) that draws one glyph per record whose
  **byte 5 == `[$57ffe]`** (the selected group id), positioned by *raw cell
  coordinate* (`record[8]`, `record[10]+6`) plus a fixed per-frame descriptor X,
  not by a projected position. It blinks via `$4bb41` bit 0 (which flips
  `flipHalf` 0↔15; `flipHalf` 15 pushes every heading to the `0xff` "draw
  nothing" table slot — that is the "off" phase). `$e6ee` is also the HUD-glyph
  blitter. `assets/headings.json` feeds *this* path only.

### Category dispatch (`$115e0` → `$1162e` / `$1165c`)

Per bucket entity, `$115e0` reads object-record **byte 6 = category**, then:

| table | addr | target | role |
|-------|------|--------|------|
| prepare | `$1162e` | `$1162e + word[$1162e + cat]` | interpolate screen position, pick a frame index (into D2), sometimes blit inline |
| blit | `$1165c` | `$1165c + word[$1165c + cat]`; **word 0 ⇒ no separate blit** | hand D2 to a blitter |

**Corrections to earlier passes (verified from the RAM tables + a disasm of each
handler, 87th):** the blit table is at **`$1165c`**, not `$1165a`. Category 0
(men) blits via **`$11f78` → `$11f82`** (the 55-byte mini-sprite path), *not*
`$1187c` — `$1187c` (`pm_blit_man_sprite`) is not referenced by the blit table
at all and is reached only from `$11c8a`'s melee/dying mode branches (record
byte 31 ∈ {`$32`,`$34`,`$06`,`$46`}). `$115e0`'s dispatch is `$1162e`'s 16
prepare handlers exactly as the previous table listed (re-read from RAM, all
confirmed), plus `cat 16`→`$1168a`, `cat 17`→`$11f78`, `cat 18/19`→`$12258` in
the blit table.

### Position — bilinear over the projected cell corners (`$11f1a`)

Every `$33000`-sheet prepare handler places the entity by interpolating the
cell's four **projected** corners (from `$3f364`, packed `(screenX<<16)|screenY`
— §3) by the entity's sub-cell fraction:

```
a0 = &$3f364[cellRow*64 + cellCol*4]          // the cell's TL corner
C00 = (a0)   C10 = 4(a0)   C01 = 64(a0)   C11 = 68(a0)
fx  = record[8]  & 0xff                        // low byte of the world_x word
fy  = record[10] & 0xff
pos = lerp( lerp(C00, C10, fx/256), lerp(C01, C11, fx/256), fy/256 )   // parallel 16-bit halves
screenX = pos.x + 0x3c                         // sprite anchor (cf terrain +64; −4 = ½ frame)
screenY = pos.y - 8
```

(Verified: `a0` at `$11c8a` entry = `$3f474` for a cell at camera-offset
`(+4,+4)` = `$3f364 + 4*64 + 4*4`.)

### Frame index per category

`assets/sprites/sprite_triggers.json` carries the full ripped dispatch + every
per-category frame formula. The important ones:

There are **four sprite sheets** (all 4-bitplane + AND-mask, MSB-first, opaque
where the mask bit is 0):

| sheet | frame | geom | blitter | positioning | categories |
|-------|-------|------|---------|-------------|------------|
| `$33000` | 55 B | 8 × 11, byte planes | `$11f82` | sub-cell lerp | 0, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14 |
| `$312a0` | 160 B | 16 × 16, word planes (10 B/row) | `$1225c` / `$119d4` | cell-centred | 1, 9, 15 |
| `$37c7c` | 480 B | 32 × 24, word planes (2 groups/row) | `$1227c` / `$124a8` | cell-centred | 2 |
| `$e6ee`+desc | — | 32 B glyph row | `$e6ee` | raw cell coord + fixed X | the `$165b2` marker / HUD only |

`$37c7c` decodes cleanly as **buildings + trees**; `$312a0` as small
structures / siege engines (catapult, cannon) / explosions.

| cat | name | sheet | frame (D2) |
|-----|------|-------|------------|
| 0 | man / troop | `$33000` | `(faction−1)*16 + (((heading + YAW + 0x10) & 0xff) >> 5)*2` `[+0x40 armed, +1 anim]`. faction = record[5], heading = record[17], **YAW = `[$ff9a]` ⇒ facing is camera-relative** (8 steps). Melee (record[31] ∈ {0x32,0x34}): base **0x80**, `weapon*8 + (faction−1)*4 + facing2*2 + anim` `[+0x40]`, `facing2 = ((heading + YAW + 0x40) & 0xff) >> 7`. Overlays: record[33]==8 && record[7]==1 → small extra ($11f82, table $11e40); record[44]≥0xe → weapon overlay ($12258). |
| 1 | structure | `$312a0` | record[7]==0x0a → directional pick from record[16]/7 & record[12]/10; else `$1181c` (open). Centred. |
| 2 | building / tree | `$37c7c` | `record[7]` + a `[$57fd0]`-relative offset; special-cases record[7] ∈ {0x0d,0x0e}. Centred. |
| 3, 12 | settlement marker | `$33000` | `record[7] + 0x100`; if `== 0x112` add `[$57fec] & 3` (4-frame anim). 0x100+ = number/flag glyphs. |
| 4 | animal (sheep) | `$33000` | `(((record[14] + YAW) & 0xff) >> 5)*2 + 0x117` `[+1 anim]` — 16 frames, camera-relative facing. |
| 5 | effect | `$33000` | `((record[33]−8) >> 1) + 0x10f`, then `(record[44] >> 1) + 0x142` (two blits) |
| 6 | boat? | `$33000` | underlay `0x103 − record[5]`, main `record[32] + 0x100`; `screenY −= (0xa0 − record[18])` |
| 7 | flag / banner | `$33000` | `record[5] + 0x13e` (faction-indexed) |
| 8 | leader goods icons | `$33000` | loop slot 0..7 over `[$4e514 + record[14]]` goods[8]; per non-zero slot, jump table `$11886` → ~`0x116`+ |
| 9 | siege engine / effect | `$312a0` | `record[14]` signed; if < 0, `record[14] + 0x2f`. Centred. |
| 10, 11 | structure w/ flag | `$33000` | `$11f82` D2=`0x148`; conditional `$e6ee` D2=5 and `$11f82` D2=`0x151`; returns `([$57fec] & 7) + 0x127` |
| 13 | faction marker | `$33000` | `(record[5] & 0xff) + 0x149` `[+1 anim]` |
| 14 | marker / icon | `$33000` | `0x150`, or `([$57fec] & 1) + 0x14e` if `record[5] > 0` |
| 15 | large structure | `$312a0` | `0x0c` default, then a `record[8]`-indexed pick. Centred. |

**The `+0x40` "armed" variant (cat 0):** `D2 += 0x40` iff `record[7] bit 4` set
**and** (`record[7] bit 7` clear **or** the unit's group == `[$57ffe]` the
selected group). (87th: the live man had `record[7] = 0x10` → frame 64.)

Frame *counts* per category, the cat-2 `[$57fd0]` offset table, the `$11886`
goods table, and the cat 1/15 detail are still open (88th).

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

`assets/sprites/sheet_contact.png` shows the **full 352-frame `$33000` sheet**
(87th — was the first 64 only): 0–127 = the four faction man blocks, stand/walk
+ armed variants; 128–287 = the melee/action poses; `0x117`+ = animals;
`0x100`+ = number / flag glyphs; `0x14e`/`0x150` = icons. `prop_sheet_contact
.png` (`$37c7c`, `decode_wordsprite(f,32,24)`) and `struct_sheet_contact.png`
(`$312a0`, 16 × 16) decode cleanly as buildings/trees and small
structures/siege-engines respectively.

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
**terrain master at `$78000`** (32000 B), built once per mission.

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

1. **All 4 quadrant walks + the rasteriser — CLOSED (78th q3 walk, 80th
   rasteriser, 83rd q0/q1/q2 walks).** `pm_render_ref.py --ram` auto-selects
   the right handler from the RAM's own yaw (`walk_by_yaw`) and ports each
   exactly (cell↔corner↔colour, the flag-bit diagonal, both plane reads), the
   `$ef62` colour/winding + coast rule, and the `$e420` 16.16 DDA span walker
   (`_fixed_slope`, `_dda_walk`), reading the game's own `$3f364` corners with
   the **+64 px §3 inset**. Against `pm78_settle.ram` (yaw `$f0`, q3) it covers
   **96 %** of the game's real per-frame terrain layer (composed frame vs the
   `$78000` master; 614 / 14 417 px missed at edges), scoring **~94 % exact /
   ~95 % within ±1** palette index. q0/q1/q2 are live-trace-verified exactly
   (register dump at the first `$ef62` call matches the predicted vertex +
   colour-plane assignment — §4) but score lower against their own live
   captures (**35-50 % exact-index**, `pm83_q{0,1,2}c.ram`) because the
   residual item below (tall coast-slope dither spread) is more exposed at
   those camera angles — not a new bug, see §4's closing note. **The "sea fill
   inside the diamond" (78th's open item) does not exist** — the sea is baked
   into the `$78000` master (§7). **Residual (≈6 % at yaw `$f0`, larger at
   other yaws):** unit sprites on the hill (the walk is terrain-only), the
   tall `0x1c` coast slopes (the game dithers idx 1-7, the port lands nearer
   flat idx 1 — needs the multi-segment slope-of-slope chain past the single
   mid-vertex switch `_dda_walk` models), and a ~1 px NE island edge.
   **85th (continued): the `0x1c` coast-slope theory is WRONG for yaw `$f0`
   — corrected, don't reuse.** Instrumented `walk_q3` to track, per final
   pixel, which draw call last owns it (proper painter's-order occlusion,
   cross-checked against the official 14469-pixel score). Result: every
   tall `0x1c`-forced triangle checked (up to 32 scanlines, both in
   `pm78_settle` and `pm83_q1c`) has **zero surviving pixels** in the final
   composite — nearer cells always fully overdraw them. Across the whole
   `pm78_settle` frame only **12 of 14469** drawn pixels are finally
   `0x1c`-owned; that colour doesn't even appear in the top mismatch list.
   **The real yaw-`$f0` residual is overwhelmingly unit sprites**: mismatched
   pixels (810 total, 5.6% of drawn) form **44 connected components, and just
   8 of them account for 94% of all mismatches** — several with bounding
   boxes matching the documented 8×11 sprite format almost exactly (e.g. 8×11
   at (128,78), 9×8 at (109,93)); the largest few (35×15, 18×12) plausibly
   read as clusters of adjacent sprites (a group of units/animals), not
   terrain. This means Task 2 (sprite rip, §9 item 3, still NOT STARTED) is
   the actual path to closing yaw-`$f0`'s ≈6% gap, not further rasteriser
   work — also ruled out (live-checked, not guessed) two more candidate
   causes for the record[20]/[22] mechanism: `$e420`'s edge-reload loop reads
   an arbitrary-length (run,slope) stream from a single pointer shared
   between both edges, terminating the WHOLE triangle on any zero run-count
   — a mechanism that could in principle read stale garbage past `$ef62`'s
   documented 26-byte record and draw a spurious 3rd segment, but the 6
   spare bytes at record offset 26-31 read **consistently zero across 8 live
   triangle draws**, so this never fires in practice. Also checked the dither
   setup's `move.w (A0)+,D6` at `$e3e6`, which reads a WORD at record offset
   0-1 even though `$ef62` only ever writes the BYTE at offset 0 (colour) —
   offset 1 could in principle carry stale garbage into the A5 phase
   calculation, but it reads **consistently `$00` across 6 live triangle
   draws** too. Neither mechanism is the cause.
   **New, unresolved lead: q0/q1/q2 have a qualitatively different, much
   bigger mismatch than yaw `$f0`'s sprite-shaped blobs.** Same
   connected-component analysis on `pm83_q{0,1,2}c.ram`: 95-97% of all
   mismatched pixels form **one single giant connected region** spanning
   most of the drawable window (e.g. q1: 9101 of 9552 mismatched px in one
   175-225px-wide blob), not sprite-sized clusters. `render_faithful_compare
   .png` for q1 shows why by eye: the island *silhouette* matches closely,
   but the real frame's dither shading has a pronounced diagonal banding
   texture the port's reproduces much more faintly — the diff panel shows
   diagonal red/green *stripes* over most of the hill, not a uniform wash.
   The error-magnitude histogram is bimodal: ~52% of mismatches are exactly
   ±1 index (consistent with a phase-off-by-a-bit issue), but ~39% are large
   swaps (mostly ref 6-13 steps *darker* than the port, echoing the 84th's
   "green vs black" framing at a much larger scale) — suggests the shared
   `ef62Raster`/`ddaWalk` dither-phase formula (verified only against ONE
   live-traced yaw-`$f0` triangle, 80th pass) may not generalise to whatever
   `colourByte`/`topY`/`HBIAS` combinations these other yaws actually
   produce. **Not yet traced** — needs a live single-step of an actual q1/q2
   triangle's dither A5 sequence compared row-by-row against
   `pm_render_ref.py`'s computed sequence for the same triangle, which is a
   fresh investigation, not a continuation of the (now closed) `0x1c`
   coast-slope lane. This is very likely also the real explanation for the
   84th's green-vs-black anomaly (same "port lighter than ref" direction,
   same camera-anchor region falls inside q2's giant blob) but that
   connection is inferred, not traced — don't state it as confirmed.
   **85th did that trace — found a real bug in the formula's assumption, but
   it's NOT the dominant cause of q0/q1's giant-blob mismatch.** `[$ffa2]`
   (used by `$e3e6`'s A5 setup) has been assumed exactly `2*[$ff9e]` since
   the 78th pass; live-checked, that's only true for `pm78_settle`/`pm83_q2c`
   — `pm83_q0c`/`q1c` have `[$ffa2] = 2*[$ff9e] + 128` (confirmed frame-
   stable across 20 consecutive live `$ef62` calls, not a volatile/shared-
   with-sound-mixer artifact). Single-stepped a real q1 triangle's full
   22-row A5 sequence from `$e420` and matched it exactly (22/22) once the
   correction (`((8*y + phase_bias) & 0x7F)`, phase_bias = `([$ffa2]>>1) -
   [$ff9e]`) was applied **inside** the mod-128 wrap — a first attempt that
   added it after the mask matched only the rows that didn't need an extra
   wrap and was silently wrong for the rest. **But even with a
   hardware-exact A5 and hardware-exact dither-table bytes** (both directly
   verified against live memory, not inferred), the traced triangle (cell
   (43,54), q1) still scored 0/327 exact-match against the reference frame —
   its computed index (mostly 12, grass) vs the reference's actual shown
   index (mostly 0-2, dark/rock) are just different terrain families, not a
   phase-shifted grass. That specific mismatch is NOT a dither bug at all —
   most likely this cell isn't even the thing visible at those screen pixels
   in the real game (an occlusion or wrong-cell/wrong-diagonal bug elsewhere
   in the walk). Applying the corrected `phase_bias` frame-wide made q0/q1's
   aggregate exact-index score WORSE (46.6%→40.4%, 44.6%→40.3%), meaning more
   triangles were hurt than helped — some other triangles' errors were
   apparently cancelling against the old wrong assumption by coincidence.
   **Reverted the correction's application** (the `phase_bias` parameter
   still exists on `dither_index`/`_dda_walk`/`ef62_raster`, default 0, for
   future use) rather than ship a net-negative scoring change; scores are
   back to pre-85th-continuation values. The real cause of q0/q1's blob is
   still open — next candidate is the occlusion/cell-identity bug the traced
   triangle points at, not the dither formula.
   **84th: an unexplained green-vs-black mismatch**, found but not resolved —
   on `pm83_q2c.ram`, screen rows y≥155 near the iso window's right edge
   render solid green in the port where the reference shows near-black, for
   large (33-36 scanline) legitimately-grass cells right at the camera-anchor
   corner ((36,47)/(37,47)/(38,47)). **85th ruled out both of the 84th's
   candidate causes**: `$f202` vertex-clip-and-resubmit never fires for these
   cells (their raw screenX tops out ≈210, well inside `$ef62`'s [0,255]
   bound), and the right-edge clip/framing bug fixed this pass doesn't touch
   this region either (same reason — nowhere near either clip boundary). Cause
   still open; next candidate is the coast-slope dither residual itself
   (spreading further at this camera angle than modelled) or a capture-
   specific settle artifact (`pm83_q2c.ram` was reached via 16 synthetic
   rotation pulses, not natural mission startup like `pm78_settle.ram`).
   **81st: ported to F# unchanged** — `port/godot/logic/Fill.fs`, cross-verified
   byte-exact against `pm_render_ref.py` on synthetic data. **83rd: q0/q1/q2
   added to `Fill.fs` the same way**, wired into `TerrainView.cs` behind
   `Fill.walk`/PageUp/PageDown, and verified with real Godot screenshots at
   yaw steps 3 and 11 (`assets/reference/godot_screenshot_yaw{3_q0,11_q2}.png`).
   **85th: fixed a real, separate right-edge clip/framing bug** (the window's
   true right edge is absolute screenX 319, not 255 — see "The clip check
   runs on the RAW, pre-inset value" above) in both `pm_render_ref.py --ram`
   and `TerrainView.cs`'s blit, verified with a real Godot screenshot showing
   the expected shift. Exact-index score on q0/q1/q2 does **not** improve
   from this (it is a coverage fix, not an accuracy fix, and the newly-drawn
   strip is dominated by the residual below) — see `port/README.md` 85th for
   the full breakdown. Still does **not** explain the specific
   green-vs-black mismatch noted below (checked and ruled out: those cells'
   own vertices never approach either the old or the corrected clip
   boundary).
   **86th: the terrain renderer is byte-exact for q0/q1/q2 — the low
   `--ram` score against `pm83_q{0,1,2}c` is a bad-capture artifact, not a
   renderer bug.** Live single-stepped `pm83_q2c` (`walk_q2`, yaw `$90`) to a
   standard no prior pass reached: (1) all **128/128** `$ef62` calls in one
   frame match the live game exactly — same 3 vertices, same colour byte,
   zero diff; (2) the dither `A5` phase sequence is byte-exact every scanline
   on two traced triangles (`colour*128 + ((8*y) & 0x7f)` reproduces the real
   `$e456` register, phase_bias correctly 0); (3) the `$e420` DDA span
   endpoints (`ixL`/`ixR`) are byte-exact every scanline of a traced 27-row
   triangle (call 102, col `0x2b`) vs the real `$e462` register lookups; (4)
   `_fixed_slope` re-verified against fresh `$f000` disasm; (5) the fill's
   plane layout (planes 0,1 ← `dith[A5]`, planes 2,3 ← `dith[A5+4]`, one 16px
   pattern tiled screen-X-aligned, `A5 += 8`/scanline in *all* span paths)
   re-derived from fresh `$e3e6`/`$e420`–`$e5a6` disasm and matches the port.
   Given geometry + colour + phase + spans + dither table all byte-exact, the
   port's per-pixel output for any triangle is byte-identical to the game's,
   so the 35–50% exact-index against `pm83_q{0,1,2}c` measures the **captured
   `$1c700`/`$24400` reference buffer**, which for these synthetic-rotation
   captures does not correspond to the state the frozen `$3f364` corner
   buffer describes. Evidence it's the capture: `pm83_q2c`'s `load_ram`
   buffer heuristic picks `$24400` (35.4%) but `$1c700` scores **52.7%** and
   is far closer to the `$78000` master in the HUD strip (25 vs 153 px diff);
   `pm83_q1c` and `pm83_q2c` have the *same* `$e3e2` draw pointer
   (`0x1c720`) yet opposite correct buffers, i.e. `pm83_q2c` was frozen at a
   different point in the frame/swap cycle. The mismatch's two buckets —
   large errors form **coast/diamond-edge-shaped blobs** (65×49, 89×24 at the
   bottom-right and left edges), not 8×11 unit clusters; ±1 errors form one
   frame-wide blob (q0: 3035 px, 150×89) — are both consistent with a
   sub-step camera drift between the displayed framebuffer and the captured
   corners, not with a per-triangle rasteriser error. `pm78_settle` (natural
   settle, clean capture) scores 94.4% with the residual being genuine unit
   sprites (85th's connected-component proof). **Next: a clean q0/q1 capture
   via natural in-game camera rotation — settle many frames, verify the
   display buffer is stable across two consecutive dumps — or Task 2 (sprite
   rip). Do NOT generate a 7th rasteriser hypothesis against `pm83_*c`.**
2. **Dither phase — CLOSED (80th).** Full span walker disassembled
   (`$e3e6`→`$e5a6`) and live single-stepped. `A5` wraps **modulo 128** inside
   the colour's slot (`$e44a`'s `addq.b #8` on `2*A5` byte-overflows at
   `A5 & 0x7f == 124`): `A5 = $2e000 + colourByte*128 + ((8*y) mod 128)`, y =
   absolute scanline — the `topY` term drops out under the mod. This kills the
   79th's empirical `DITHER_COLOUR_BIAS = -1` (which only happened to be right
   for 16–32 px-tall triangles). Trace: cell topY 75, colour `0x26` → `A5` =
   `2f358 2f360 2f368 2f370 2f378 2f300 2f308 2f310 2f318` across 9 scanlines.
3. **Sprites — the iso-entity path is settled (87th); frame formulas mostly
   ripped; per-category counts + the cat-2 layout still open.** Which path
   draws the terrain men: **`$115e0`, inline per cell in the grid walk** (not
   `$16738`→`$e6ee`, which is the `$165b2` selected-group marker + HUD). The
   dispatch (`$1162e` prepare / **`$1165c`** blit — the old `$1165a` was 2
   bytes low), the `$11f1a` bilinear-over-projected-corners positioning, and
   the frame-index formulas for **all of cats 0-15** are ripped into
   `assets/sprites/sprite_triggers.json` (§6); positioning is `$11f1a`'s
   sub-cell lerp for the mobile categories, a 4-corner centroid for the
   structures. Cat 0 (men) blits via `$11f78`->`$11f82`, **not `$1187c`** (a
   melee/dying sub-case). The `+0x40` "armed" variant = `record[7]` bit 4
   (with a selected-group gate). **Four sheets, all decoded**: `$33000` 8x11
   byte-planes (352 frames), `$312a0` 16x16 and `$37c7c` 32x24 word-planes --
   the last two decode cleanly as small structures/siege-engines and
   buildings/trees.
   **87th (cont.): `pm_render_ref.py` grew an entity compositor** --
   `_decode_frame_byte`/`_decode_frame_word` (all 3 sheets), object-record
   parse from `$51b66`, per-cell bucketing, the `$11f1a` sub-cell lerp + a
   4-corner centroid, and `_entity_frame` (cats 0/2/3/4/7/13/14). It runs as a
   **diagnostic only** (on a copy -- it currently *lowers* the score, 94.4% ->
   92.3%, so it is not composited into the output). **Two blockers found:**
   (a) `pm78_settle`'s dominant visible entity is a **26-record cat-14
   marching group** (`b31 = 0x68`, chained across cells 39-41 / 50-52) whose
   **draw path is not confirmed** -- `$11b0c` (the disasm-derived cat-14
   handler) had **zero calls** in the 87th's frame trace, so cat 14 is drawn
   some other way (the `$16738`/`$e6ee` group path is the prime suspect --
   `$16738` positions by `record[8]` as a *descriptor-table index*, not a
   pixel); (b) the cat-2 buildings + cat-7 markers seen in the trace (~20 +
   ~35 per frame) are **not in `$51b66`** -- they come from a separate scenery
   / settlement array (`$4f916`?) that also feeds the `$47970` buckets.
   **88th:** live-trace what actually draws the cat-14 group and the scenery,
   fix `_entity_frame` + the anchor, get the re-score to climb, then
   `Sprites.fs` wiring + a byte-exact cross-check.
   **Also still open:** exact frame *counts* per category; the cat-2 `[$57fd0]`
   offset table; the `$11886` goods table; cat 1/15 detail; the packed-corner
   word order (X hi vs lo).
4. **HUD art.** `$e6ee` descriptor table dumped raw; glyph sheet address still
   needs resolving from a live snapshot. Deferred.
5. **Border / stone-table master, world-map minimap + compass panel.** Not
   started — `$e0d4` master + the left-strip compositor. Deferred.

None of items 3-5 block the Godot port (terrain + camera are the port's spine).

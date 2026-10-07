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
against the disassembly in `../graphics.md`, which is the reference for the
plane names used below. Addresses are in the relocated game
image (link base `$1050`).

## Status

What is done, with its evidence (the sections named hold the detail), and what is genuinely open.
Evidence levels (Proven, Corroborated, Observed, Hypothesis) are defined in `../ai.md`
"Evidence taxonomy".

**Done.**

- **Projection (§3), Proven vs the real 68000.** `$fecc` called in isolation with `A3 = $13f8a`
  recomputes a `$3f364` byte-identical to the stored buffer on four captures, and an integer
  reconstruction of it matches 3240/3240 vertices (36 generated camera states plus 4 natural
  captures). The port's `Projection.projectGrid` is float and agrees with the game's corners to
  within a pixel at 78-95% of vertices; the terrain scores use the game's own corners.
- **Rasteriser (§4), byte-exact against a live single-step.** `$ef62` / `$e3e6` / `$e420`: all
  128/128 `$ef62` calls of a quadrant-2 frame (vertices and colour), the dither `A5` phase on every
  scanline of two traced triangles, and the DDA span endpoints of a 27-row triangle. All four
  yaw-quadrant grid walks (`$f98e`, `$fa9a`, `$fbb4`, `$fccc`) are ported
  (`Fill.planQ0`..`planQ3`, `pm_render_ref.py` `walk_q0`..`walk_q3`), live-trace-verified at a yaw in
  each quadrant, and the F# port equals the Python reference byte for byte on synthetic triangles and
  grids exercising every code path.
- **The whole frame (§6 "Draw order", "Scoring a capture").** Terrain away from sprites matches the
  game's compose buffer at 99.7-99.96%; with every ported sprite category drawn inline, 27 frames from
  12 views on lands 0, 5, 25 and 60 (snow, rain, a fight, a projectile, boats included) match the game
  pixel for pixel. The sea, HUD and minimap are baked into the `$78000` master (§7); there is no
  per-frame sea fill.
- **Sprites (§6).** Four sheets decoded, the `$115e0` dispatch and every category's frame formula
  ripped (`assets/sprites/sprite_triggers.json`), positions byte-exact against live `D0`/`D1`, the
  per-cell entity pass ported (`Sprites.fs`, 13/13 synthetic cases and 2881/2881 covered pixels on
  the real 53-record stream, byte-identical to `pm_render_ref.draw_entities`).
- **Seasons, zoom, weather, minimap (§4 "Seasons", §5, §7).** `Season.fading` reproduces the whole
  16 KB pattern table byte for byte on seven captures; zoom 1-7 terrain matches at 99.2-99.7%;
  rain and snow match the game pixel for pixel; the minimap (`$107d6`) is gated 512000/512000
  bytes (`../graphics.md` "The minimap and the conquest map").

**Open.**

- Category `byte6` 18, 28, 34, 36, 38 and 42 were never seen drawn on 37 lands (the writers of 18 are
  dead code in this build, §6), and the frame a `byte6` 6 camp marker draws (`$111` by the shared `$117b0`
  formula) has not been captured. The plough and siege-engine overlays of the men and the
  `record[7] == $0a` overlay of a settlement building (`$119b2`) are ported from the code but were
  never seen on screen. Per-category frame counts are not tabulated.
- HUD art: the glyph sheet behind `$e6ee`'s descriptor table and the compass panel are not decoded as
  assets (the `$78000` master as a whole is `assets/backdrop.bin`).
- Whether a territory change re-bakes the minimap or tints it per frame is undecided: none of the
  captures taken for the minimap holds an ownership change, and the one capture that does (land 60,
  `scratchpad/pm121/flip/`, the `$550e` revolt) has not been diffed.
- `pm78_settle` scores 94.6% because its two compose buffers disagree on the entity layer (`$115e0`
  redraws a subset per frame); that is the capture, not the renderer (§9). The `0x1c` override was
  measured at one pose only (§4).
- Godot runs at zoom 4 only; the stepper and the Godot view do not draw weather; `Equipment.fs` is
  called by nothing because the port has no entity simulation.

**Scratch-only scripts (not promoted).** Several results above and below were produced by scripts that
live only in the gitignored `scratchpad/` (some only on `gpubox`, not on the Mac), so they cannot be
re-run from the repository: `scratchpad/pm83_synth_check.{py,fsx}` (F# vs Python on
synthetic quadrant data), `scratchpad/pm90_xcheck.{py,fsx}` and `pm91_ent_{fs.fsx,py.py}` (entity pass cross-checks),
`scratchpad/pm118/` (`baseline.fsx`, `order_test.fsx`, `phase_test.fsx`), `pm118b/` (`lastrow_fix.fsx`),
`pm119/` (`season_check.fsx`, `pan_check.fsx`, `zoom_check.fsx`, `jitter_check.fsx`) and
`scratchpad/pm121/allpairs.txt`. The committed equivalents are `../py/parity.py`, `../py/score.fsx`,
`../py/season_check.fsx`, `../py/dump_frame.py`, `../py/capture.sh` and `walkthrough/probe.fsx`;
anything below that cites a scratch path is a record of what was run, not a reproduction recipe.

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

Four parallel planes, all 64 x 128 cells, row-major, stride 64. The names are
`../graphics.md`'s:

| plane | source addr | used for |
|-------|-------------|----------|
| **colour B** | `$438ee + 0` | colour byte of the cell's NE / SE triangle (the second triangle in the walk of §4) |
| **colour A** | `$438ee - 8257` = `$418ad` | colour byte of the cell's NW / SW triangle; entity-side terrain sampling reads these planes |
| **flags** | `$438ee + 8257` = `$4592f` | bit 7 = **diagonal selector** (which diagonal splits the cell, §4); bit 1 pins the altitude |
| **altitude** | `$3f86c` (`_alts`) | the height the **projector** reads for cell Z; the colour planes are baked from it by `$10058` (a slope shade; `../graphics.md` "The land build") |

`terrain.bin` interleaves them as `[0] colour B, [1] colour A, [2] flags, [3] altitude` per
cell, 4 bytes/cell, 32768 bytes. **The code keeps older names for these bytes:**
`pm_export.py`, `manifest.json`, `terrain_type.png` / `terrain_height.png` /
`terrain_control.png` and the F# `Terrain.Map` fields (`Type`, `HeightPlane`, `Flag`, `Control`,
`TypeAt`, `HeightAt`, `ControlAt`) call byte 0 "type", byte 1 "height" and byte 3 "control";
they are colour B, colour A and the altitude plane. Where this file says `type_plane` or
`height_plane` in older text, read colour B or colour A respectively.

Derived rules:

- **water**: a colour byte `< 0x0c`. Water triangles add `[$4bb3e] & 3` to their colour
  byte before the fill (a 4-step shimmer). `$f898` loads that term on every
  walk (`$f95e`) and refills every cell, so the shimmer runs whenever water is
  inside the drawn window, whether or not the camera moves (§7).
- **diagonal selector**: `flags & 0x80` picks which diagonal splits the cell (§4).
- mission-1 island bounding box in cells: **x 8..45, y 41..75** (rest is sea /
  off-map zero).

A modern port loads this as a 64 x 128 R16 heightfield (use the altitude
plane) plus a 64 x 128 R8 colour map, and builds either an `ArrayMesh` or samples
it in a vertex/fragment shader.

---

## 3. Projection

Per-frame, only when the camera cell, yaw or zoom changed (`pm_project_grid`
`$fecc`). Produces one screen-space corner `(sx, sy)` per grid vertex into the
`$3f364` corner buffer ((2·HALF+1)² vertices: 9 x 9 at the default zoom 4, see §5).

### Constants (`assets/tables.json → projection`)

| symbol | addr | value (mission 1, zoom 4) | meaning |
|--------|------|--------------------------|---------|
| `EYE` | `$ff98` | 320 | eye distance for the perspective divide |
| `HORIZON` | `$ff96` | 130 | horizon screen-Y |
| `ZOOM` | `$ff9c` | 21 | cell size in world units, `$13f82[zoom index]` (§5) |
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
h  = altitude_plane[camCell + row*64 + col]
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

**Draw inset.** The corners in `$3f364` are relative to the **iso window
origin**, not the screen. The `$e420` fill writes to `$e3e2` (a runtime-patched
pointer) = `compose_buffer + 0x20` bytes = **+64 screen pixels**. So the final
`screenX = $3f364.sx + 64`. The left 64 px is the HUD portrait / compass strip.
`pm_render_ref.py` reads the inset back as `($e3e2 & 0x3f) * 2`.

**The clip check runs on the RAW, pre-inset value.** `$ef62`'s own
`screenX <= 255` clip (§4) applies to `$3f364.sx` directly, before the `+64`
above -- i.e. the real window is `raw sx in [0,255]`, which is `absolute
screenX in [64,319]`, not `[0,255]`. Applying the `<=255` bound to the
already-inset-shifted coordinate would truncate the true window's right ~64 px,
so `pm_render_ref.py`'s `--ram` path threads an `x_inset` parameter through
`ef62_raster`/`_dda_walk`, and the clip bound shifts with the coordinate space
it is given (`port/README.md`, "Verification record"). `Fill.fs`/`Projection.fs`
stay in raw space throughout, matching `$ef62` itself; `TerrainView.cs`'s blit
reads the buffer at `(x-64,y)` (reading `(x,y)` is the same error at the
opposite end of the pipeline), verified with a real screenshot.

All arithmetic is 16.16-ish fixed point on the 68000 (`muls`/`divs`, `>>15` via
`add.l`+`swap`). A port does it in float; the `>>15` after the rotate keeps
`rx, ry` in world-pixel units.

**Verified byte-exact:** running this maths in integer for the 9×9 grid
of `pm74_late.ram` (camCell 36,47; YAW 0xf0; ZOOM 21; HBIAS 4) reproduces every
one of the 81 `(screenX, screenY)` pairs in the game's own `$3f364` corner
buffer. `$ff7c`'s PC-relative operands resolve to `26(PC)`→`$ff98` (EYE) and
`12(PC)`/`4(PC)`→`$ff96` (HORIZON). The loop is 9×9 vertices at zoom 4 (`$fdec`
= HALF = 4), row/col counters `-4..+4`, `A1` walking the `$3f86c` altitude plane
forward from the camera cell (row stride 64), corner buffer `$3f364` row stride
64 bytes (9 × 4 used). `tools/pm_render_ref.py`'s float version matches to ≤1 px.

**Proven vs the real 68000.** Using the
emulator's `callcap` primitive (call a routine in isolation from a captured
state, capture its full register + changed-memory delta, snapshot-restore):

- **Entry contract:** `$fecc` reads `0(A3,D0.w)` with `D0 = YAW*2` on entry, so
  **`A3` must point at the sine table `$13f8a`**. Everything else (YAW/ZOOM/HALF
  at `$ff9a`/`$ff9c`/`$fdec`, the camera cell at `$4bb3a`/`$4bb3c`, `$57ffc`, the
  strides `$fdea`/`$fdee`, the altitude plane `$3f86c`) is from fixed memory. A
  bare `bsr $fecc` with a garbage `A3` produces 158/162 wrong corner bytes — this
  is what `callcap` surfaces, and why per-routine entry-contract discovery is the
  first step of any differential test.
- With `A3 = $13f8a`, the freshly recomputed `$3f364` is **byte-identical to the
  stored buffer** across `pm78_settle` / `pm88_f1` / `pm73_fight` / `pm74_late`.
  So the in-RAM corner buffer that the terrain scores rely on *is* the projection
  output, reproducibly; the comparison is not circular.
- A from-disassembly integer reconstruction (`py/proj/proj_ref.py`; promoted, see Status —
  `$fecc` + `$fe8e` HBIAS + `$ff7c` divide, transcribed line-for-line, **no float
  `sin`/`cos`, zero fudge factors**) matches the real `$fecc` output over **36
  generated camera-cell states + 4 natural captures: 3240/3240 vertices exact**,
  full corner-buffer comparison (`py/proj/gate_fecc.py`, rerun from the repository).
- Pre-registered falsifier: any single vertex X or Y off by ≥1. Pass bar: 100%
  exact over ≥30 generated states + all 4 natural captures. Result: PASS.

The projection **is perspective** (`x / (EYE - depth)`), not an affine 2:1 iso.
The "isometric" look is a fixed camera pitch baked into the fixed `HORIZON`/`EYE`
pair plus the 16-step yaw. A port that wants true axonometric can drop the
divide and the corners become an affine transform, at the cost of PM's subtle
foreshortening.

### Camera cell

`$4bb3a` / `$4bb3c` hold the cell at the centre of the view, and `$57ffc` is
the zoom index, which is also HALF (§5). The window starts HALF cells before
the centre:

```
camCellX = $4bb3a - $57ffc          // mission 1: 40 - 4 = 36
camCellY = $4bb3c - $57ffc          //            51 - 4 = 47
```

The grid then spans `camCell .. camCell + 2*HALF` in both axes (the camera cell
is the far/top corner of the drawn diamond). Changing the zoom keeps the centre
cell, so the window grows or shrinks around it. `$12fd8` clamps the centre to
`[$57ffc, 64 - $57ffc]` in x and `[$57ffc, 128 - $57ffc]` in y every tick; the
port clamps the window's top-left cell to `0 .. 63 - 2*HALF` and
`0 .. 127 - 2*HALF`, one cell tighter at the far edge, so that every corner it
projects is inside the 64-wide plane.

---

## 4. Rasterisation — two triangles per cell

`pm_render_terrain` `$f898` walks the projected grid **far → near** (painter's
order — no depth buffer). For each cell it has 4 corners `TL, TR, BL, BR` (BR =
next row, next col; the corner buffer row stride is 64 bytes = 16 longs, 9 used):

```
// quad split: flag bit 7 (+8257) picks the diagonal; both branches draw two triangles.
if  !(flag[cell] & 0x80):  split on C00-C11          // CLEAR branch
else:                      split on C10-C01          // SET branch
// one triangle takes colour B [cell], the other colour A [cell]; which
// branch compares packed corners to fix the pair's draw order depends on the
// quadrant -- see the table below.
```

`colour` is the raw terrain byte. If `byte < 0x0c` add `masterTick & 3` (water).
A sloped cell shows a two-tone split because one triangle is coloured by its
colour A byte and the other by its colour B byte.

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

**Dither phase.** `[$ffa2]` is not constant. `$f898` sets it to `2*[$ff9e]` on its
first call (`$f89e..$f8ac`), then `bchg #7,$ffa5` (`$f8e4`) flips bit 7 of its low
byte every time it re-projects because the camera cell, yaw or zoom changed. After
the `>>1` the read point moves 64 bytes (8 scanlines) inside every 128-byte colour
slot, and moves back on the next camera change: phase = `([$ffa2]>>1) - [$ff9e]` ∈
{0, 64}, added inside the mod-128 wrap. The port models it as
`Fill.withPhase dith phase` (each slot rotated by the phase); the viewer and
`TerrainView.cs` flip it on every camera change. Evidence: `pm88_f1.snap` with
`w ff9a 00YY0015` then 2M steps, three yaws (`scratchpad/pm118/rot{40,90,c0}`,
`phase_test.fsx`), terrain exact-index 43.5 / 46.7 / 47.1% without the phase and
93.8 / 84.6 / 91.1% with it (phase 0 at the unrotated `pm88_f1`: 93.9% either way).

**Per scanline the roll advances `+8` but wraps modulo 128 inside the colour's
slot** (live single-step of `$e420`: `A5 = 2f358 2f360 2f368 2f370 2f378
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
16 scanlines. A form with `(topY&15)*8 + 8*(y-topY)` is equivalent for the
first slot only; the mod-128 wrap makes the `topY` term drop out (`128*(topY>>4)` ≡ 0
mod 128).

`colourByte` is the raw colour byte (colour plane A `$418ad` for one
triangle, colour plane B `$438ee` for the other), **+ `[$4bb3e] & 3`** if `< 0x0c`
(water shimmer), or forced to `0x1c` by the `$ef62` coast rule (below).

Decoding `assets/dither.bin` at `colourByte*128` (verified against reference
pixels):

| colourByte | palette indices | terrain |
|-----------|-----------------|---------|
| `0x00` | 14, 15 | **open sea** (colourByte 0, not a water flag) |
| `0x08`–`0x0b` | 14, 15 (+ 4) | shallow water (no map checked produces these bytes; `../graphics.md`) |
| `0x18`–`0x1c` | 1, 2, 3, 6 | rock / dark earth / coast shading |
| `0x24`–`0x28` | 13, 12 | grass (dark→mid) |
| `0x2c` | 11, 12 | grass (light) |
| `0x30`–`0x3c` | 7, 9, 11, 12 mixed | bright slope |
| `0x3e` | 9, 10, 11 | brightest ridge |

The grass and slope slots (`0x1d`-`0x2e`) change with the season; the rows above
are from `pm74_late`, near the end of the fade into season 1 (green).

### Seasons (`$1ab60`, `$1abaa`)

The landscape has four seasons. `word[$57fd0]` holds the season as 0, 2, 4 or
6 (the port uses that value / 2), and two things follow it: the grass colours
and the tree frames.

**Grass.** Colour slots `$1d`-`$2e` of the pattern table (18 slots x 128 bytes,
`$2e000 + $e80`) are a working copy. The table itself also holds three source
versions of those 18 slots, and `word[$1aba2 + word[$57fd0]]` picks one:

| season | `$57fd0` | source | grass |
|---|---|---|---|
| 0 | 0 | `$2e000 + $2980` | khaki and grey, no green (palette 1-5): winter |
| 1 | 2 | `$2e000 + $2080` | green (11-13): spring |
| 2 | 4 | `$2e000 + $1780` | green mixed with brown and gold (6, 7, 9): summer |
| 3 | 6 | `$2e000 + $2080` | green again, the same source as season 1: autumn |

Everything outside the 18 live slots, the sources included, is identical in
every capture, so `assets/dither.bin` plus a season gives the whole table.
`$1ab60` (world build, `$13c66`) copies the season's source over the live slots
in one go. After that, `$1abaa` (in the `$13000` tick, right after `$f898`)
fades towards the source 16 pixels per tick:

```
[$57fec] += 1                              // ticks into the fade
repeat 16 times:
    x = (x * $24a1 + $24df) & $1fff        // [$57ff6], a full-period 13-bit LCG
    if x == 0:                             // every pixel visited: the fade is over
        $57fd0 = ($57fd0 + 2) & 6          // next season; the next fade starts
        (x, [$57fec]) = 0
        stop
    row = x >> 4, bit = x & 15
    if row < $120:                         // 288 rows of 8 bytes = the 18 slots
        copy bit `bit` of all four plane words of row `row`
            from the source into the live slots
```

A fade takes 8192 LCG steps (the 13-bit LCG has a full period of 8192 including 0, so the
wrap, the step that reaches 0, is the 8192nd), 512 ticks: about 118M emulator steps in
mission 1 and 86M on a Play Random Land (`pm142/rand1.snap`). The word-sized phase counter
at the head of `$1abaa` (`$1aba0 += $1ab9e`, always `$100`) never skips a tick. `x = 0`
ends the fade without copying, so pixel 0 of row 0 only changes at world build;
it is the same in all three sources. The first fade after world build copies
the season's source onto itself and so changes nothing.

**Trees.** `$116c6` adds `word[$11746 + word[$57fd0]]` = {0, 3, 6, 9} to the
building/tree frame (§6). Tree frames 15-17, 18-20, 21-23 and 24-26 are bare,
blossoming, leafy green and autumn brown. The tree frames therefore change the
moment `$57fd0` advances, while the grass takes the whole fade to catch up:
straight after a change, the game shows the old season's grass under the new
season's trees.

At the same moment `$1abaa` also sets one random `$4d252` record whose byte 7
is `$0d` to `$0e + (word 10 & 3)` (not ported). `$1ad74`, which reads
`$1ad9c[$57fd0]`, starts rain or snow (§7 "Weather").

The sprite sheets are the same in every season: `$37c7c`, `$3af1c`, `$312a0` and
`$33000` are byte-identical on land 5 built in seasons 0, 2 and 3 and on mission 1
(poke `byte[$58146]` at `$13b9a` to choose, `../README.md` "Driving a later
land"). Only the frame offset and the grass change.

The port's `Season.fs` has `table` (`$1ab60`), `fading` (`$1abaa`) and
`treeTileOffset`. Evidence: `Season.fading(dither.bin, season, steps)` equals
the whole 16 KB `$2e000` table byte for byte on `pm88_f1`, `pm78_settle`,
`pm74_late`, `pm73_fight` and the three `rot*` captures, with steps = 16 x
`[$57fec]` in each (`scratchpad/pm119/season_check.fsx`, scratch only). On land 5 built in
seasons 0, 2 and 3 and on land 60, still inside the first fade, the RAM table
equals `Season.table(dither.bin, season)` byte for byte, mission 1's `dither.bin`
included, and the tree offset matches `$11746` (`../py/season_check.fsx`). Two Hatari
screenshots of mission 1 at the start pose (yaw 15, and yaw 3 phase 0) match the
port's settled season 2 at 88.3% and 89.1% of terrain pixels, and seasons 0, 1
and 3 at 3-35%. The viewer and `TerrainView.cs` default to the season
`entities.json` was captured in (2), and the Y key cycles it.

### The yaw-quadrant grid walk (`$f898` → `$f97e` → 4 handlers)

`$f898` picks one of four grid-walk handlers by rotation quadrant:

```
q = ((YAW + 8) >> 5) & 6           // yaw 0xf0 -> q = 6 -> handler index 3
handler = [$f98e, $fa9a, $fbb4, $fccc][q >> 1]     // jump via the $f986 word table
```

(The entry points are `$f98e`/`$fa9a`/`$fbb4`/`$fccc`, read exactly
from the jump table at `$f986` — `jmp 2(PC,D0.w)` with offsets `$8`/`$114`/
`$22e`/`$346` from `$f986` itself. The addresses `$f98c`/`$fa98`/
`$fbb2` found in older notes are each 2 bytes low: they land on the RTS of the *preceding* handler
(`$fbb2`/`$fa98`), or, for `$f98c`, a byte inside the jump table.)

Each handler walks the **projected corner buffer `$3f364` and the terrain
planes `$438ee` together**, but with a quadrant-specific **start offset**
(`A0 += $fe02`, `A1 += $fdf0` …), **iteration count** (`$fdf0` = 7, not 8) and
**corner→triangle-vertex assignment** (`(A0)`, `4(A0)`, `64(A0)`, `68(A0)` in
different D0/D1/D2 slots), so the far→near painter order stays correct as the
camera rotates. A naive
`cell(camCell + gc, camCell + gr)` walk draws a slightly different cell set
(and misses the sea wedge + the shadowed NW slope), because it always uses the
quadrant-0 assignment.

**All 4 handlers are ported** — `pm_render_ref.py`'s `walk_q0` /
`walk_q1` / `walk_q2` / `walk_q3`, dispatched by `walk_by_yaw`, and their F#
twins `Fill.planQ0`..`planQ3` behind `Fill.plan`/`Fill.walk`. Each cell's
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
direction). **Trace-verified**: for each of q0/q1/q2, a live RAM capture
at a yaw in that quadrant's range (`scratchpad/pm83_q{0,1,2}c.ram`, rotated
via the keypad-poke recipe in `../graphics.md` "In-game camera control") plus a register dump at the first `$ef62`
call after resuming to the settled PC matched the derived vertex assignment
and colour-plane choice (A vs B) exactly — e.g. q1 at cell (40,50):
`D0=C01 D1=C00 D2=C11 D3=$29`, and `hgt(40,50) == $29`. Cross-checked
byte-exact against the F# port on synthetic data exercising every branch
(`scratchpad/pm83_synth_check.py` / `.fsx`, scratch only, see Status).

**Scores at other yaws.** q0/q1/q2 score 35-50% exact-index against the captures
`pm83_q{0,1,2}c.ram`, which were rotated by synthetic keypad pulses and frozen
mid-frame; that measures the captures, not the walk or the rasteriser (§9 "Ruled-out
causes"). Clean captures of `pm88_f1.snap` rotated in the emulator score 99.7-99.96%
on terrain away from sprites.

**Quadrant 3 (`$fccc`), fully ported and trace-verified.** The walk is
`for k in 0..7 (D7): for j in 0..7 (D6)`, `A0` at `$3f364 + $fe02(=0x1c=28 B =
corner col 7)`, `A1` at colour plane B `$438ee + camCell + 7`, both advancing
`+64` per inner step (corner row +1 / cellY +1) and `-513` / `-516` per outer
step (cellX -1 / corner col -1). So

```
cell (cx, cy)   = (camCellX + col, camCellY + row)     col = 7-k, row = j
corner names    C00=(A0)  C10=4(A0)  C01=64(A0)  C11=68(A0)   [(row,col) .. (row+1,col+1)]
```

Per cell, `8257(A1)` bit 7 (the **diagonal
selector**, a per-cell heightmap-derived bit; both branches draw):

```
bit 7 CLEAR ($fcea): split on the C00-C11 diagonal
    $ef62(C10, C11, C00, colour = colourB[cell])          // NE triangle
    $ef62(C01, C00, C11, colour = colourA[cell])          // SW triangle
bit 7 SET   ($fd2e): split on the C10-C01 diagonal, sub-order by packed(C01) vs packed(C10)
    if packed(C01) <= packed(C10):
        $ef62(C00, C10, C01, colourA) ; $ef62(C11, C01, C10, colourB)
    else:
        $ef62(C11, C01, C10, colourB) ; $ef62(C00, C10, C01, colourA)
```

colour = colour plane B (`$438ee+0`) or colour plane A (`$438ee-8257`), `+
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

**The `0x1c` override** (`$f072` / `$f154`):
`$ef62` forces the record colour to `0x1c` (dark, dither slot → palette 1-7)
whenever the mid vertex is already the **left** vertex (general:
`slope(top→bot) > slope(top→mid)`; flat-top: `sx_right < sx_left`). Trace: cell
(37,47)'s SW triangle enters with `colourByte = 0x2b` (green) and reaches `$e3e6`
with `0x1c`. At the mission-1 start pose (cam 36,47, yaw 15) it applies to 52
of 128 triangles, which draw 3298 px; 6 of those px remain in the finished
frame (13 725 terrain px), because nearer terrain overdraws the rest
(`walkthrough/probe.fsx rasters`). At that pose it marks mostly back-facing
triangles, and its visible effect is a few dark pixels along the island
silhouette. Other poses are unmeasured.

**`$e420` — the DDA span walker.** Two 16.16 X accumulators (`D4` left, `D5`
right), each `+= slope` per scanline; scanline 0 uses the start X with no step
(`$e41a bra $e456`). Each edge decrements its run counter; whichever expires
first consumes `record[20]/[22]` and switches slope (the shorter edge bending
toward the far vertex). Per scanline: `ixL = D4 >> 16`, `ixR = D5 >> 16`; abort
the triangle if `ixR < ixL` (`$e468`). The walk draws rows `0 .. totalRows-1`,
where `totalRows = max(dy1, dy2)`: a run counter reaching zero ends the walk before
that row is drawn (`$e42a`/`$e43e`; the run stream ends on a zero word, `$f12c` /
`$f13e` clear `record[20]`), so the bottom vertex's own scanline is never filled.
Evidence: drawing that extra row puts a one-pixel line of wrong colour at the bottom of
every triangle (21-22 px per triangle where the game shows what is behind),
29 px per `pm88_f1` frame; with the bound `row < totalRows` all of them match
(`scratchpad/pm118b/`, `lastrow_fix.fsx`, scratch only).

The span is written with two partial-word masks: `$ec62[ixL & 15]` clears the
leftmost `ixL&15` bits of the left cluster, `$eca2[ixR & 15]` keeps the leftmost
`(ixR&15)+1` of the right cluster (`$ece2[ix] = (ix>>4)*8` = the cluster's byte
offset in the row; `A6` base = `$ece2`, so `$ec62 = A6-128`, `$eca2 = A6-64`).
Middle clusters are full. **This reduces exactly to: draw pixel x iff
`ixL <= x <= ixR`** — a per-pixel index buffer needs no planar masking.

**Coordinate resolution:** the accumulator's `2*screenX`
and `$ece2`'s word indexing cancel, so `screen_x == corner_sx` + the §3 inset,
no scale.

`pm_render_ref.py`'s `_fixed_slope` + `_dda_walk` port all of this; `ef62_raster`
does the record build + the `0x1c` rule (~94 % exact palette index against
`pm78_settle`, the residual being its sprites and its two disagreeing compose buffers).

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

The zoom index lives in `$57ffc`, 1..7. The game's zoom buttons (`$1338e` /
`$133a0`) step it by one, clamped to 1..7, and call `pm_zoom_set` `$13f60`, which
stores the index, sets `$ff9c = $13f82[index]` and calls `pm_zoom_geometry`
`$fe04` with the index as HALF:

| index `$57ffc` = HALF `$fdec` | `$ff9c` (ZOOM) | window | building/tree sheet (§6) |
|---|---|---|---|
| 1 | 84 | 2 x 2 cells | `$3af1c` 32 x 32 |
| 2 | 42 | 4 x 4 | `$3af1c` 32 x 32 |
| 3 | 28 | 6 x 6 | `$3af1c` 32 x 32 |
| **4** | **21** | **8 x 8** (mission start) | `$37c7c` 32 x 24 |
| 5 | 17 | 10 x 10 | `$37c7c` 32 x 24 |
| 6 | 14 | 12 x 12 | `$312a0` 16 x 16 |
| 7 | 12 | 14 x 14 | `$312a0` 16 x 16 |

`$fe04` derives 13 words at `$fdea..$fe02` from HALF, with N = 2·HALF cells per
side (`assets/tables.json → zoom_geometry` has the zoom-4 values):

```
$fdec = HALF           $fdf0 = N-1 (both walk loops: dbf, so N passes)
$fdf2 = 64-N           $fdee = 63-N               plane advance per row
$fdea = (15-N)*4       $fdf4 = $fdea + 4          corner-buffer row remainder
$fdf6 = 64*(N-1)       $fdfe = 65*(N-1)           plane start/step for q1 / q2
$fdf8 = 64*(N-1)       $fe02 = 4*(N-1)            corner start: q1 row N-1 / q3 col N-1
$fe00 = 68*(N-1)       $fdfa = 64N+1   $fdfc = 64N+4   corner start q2, back-steps
```

The corner buffer's row stride is fixed at 64 bytes, 16 corners, so N + 1 <= 16;
with N even that is N <= 14, HALF <= 7: the seven zooms. Every loop count, start offset and stride in the projector
(`$fecc`) and the four walk handlers comes from these words, so the walks in §4
are the same code at every zoom with 8 replaced by N: q3 visits
`(row, col) = (i, N-1-strip)`, q1 `(N-1-i, strip)`, q2 `(N-1-strip, N-1-i)`, q0
`(strip, i)`. Only ZOOM enters the projection maths. `$ff9c` alone (the keypad
path at `$137da`/`$137e8`) rescales the corners without changing the grid, and
`$57ffc` alone (`$137f6`/`$13810`) changes the grid without the scale; `$13f60`
sets both. Hand-poking the 13 words is unsafe unless they are all consistent
with one HALF (an inconsistent stride sends the span filler into code).

A zoom change keeps the centre cell `$4bb3a/$4bb3c` (§3) and is a camera change
for `$f898` (it compares `$fdec`), so it flips the dither phase.

Port: `Projection.Params.WithZoom` (HALF and `zoomScale`), `Fill.planQ0..3` over
N x N cells, `Sprites.propSheet` (§6). Evidence: captures of `pm88_f1.snap` at
zooms 1, 2, 3, 5, 6 and 7 (`$57ffc`, `$ff9c` and the 13 words poked as `$13f60`
writes them, then 2M steps; `scratchpad/pm119/zoom*.snap`,
`zoom_check.fsx`, scratch only). Terrain away from sprites matches the game's screen at
99.2-99.7% at every zoom. Sprite pixels match at 74-84% with `$12244`'s sheet,
and at 17-52% at zooms 1-3 and 6-7 with the 32 x 24 sheet forced. The float
`Projection.projectGrid` agrees with the game's own corners to within one pixel
at 78-95% of vertices (zoom 4: 73 of 81); the terrain scores use the game's
corners.

---

## 6. Sprites

### Two separate sprite paths — settled by a live trace

A live trace of one frame of `scratchpad/pm78_settle.snap` shows which path draws
the terrain men:

- **`$115e0` (`pm_draw_cell_entities`) is the iso-terrain entity path.** It is
  called **inline, per cell, from the terrain grid-walk handler** (`$fccc` for
  q3, at `$fdbc`), right after that cell's two triangles are filled, in
  far→near painter's order. So a man / animal / tree / building is composited
  immediately over its own cell's terrain and correctly occluded by nearer
  cells drawn later. This draws **everything that stands on the hill.**
- **`$16738` → `$e6ee` is NOT that path.** In `pm78_settle` it fires only from
  `$165b2` (the selected-group marker): a flat scan over every object record
  (`$16626` loop, stride 50, to `$57f66`) that draws one glyph per record whose
  **byte 5 == `[$57ffe]`** (the selected group id), positioned by *raw cell
  coordinate* (`record[8]`, `record[10]+6`) plus a fixed per-frame descriptor X,
  not by a projected position. It blinks via `$4bb41` bit 0 (which flips
  `flipHalf` 0↔15; `flipHalf` 15 pushes every heading to the `0xff` "draw
  nothing" table slot, which is the "off" phase). `$e6ee` is also the HUD-glyph
  blitter. `assets/headings.json` feeds *this* path only.

### Category dispatch (`$115e0` → `$1162e` / `$1165c`)

`$115e0` gets its per-cell head from the **`$47970` bucket array** (one word per
cell, index `(cellY*64 + cellX)*2`, set up at `$f938`); then
`A3 = $51b66 + (int16)head` — **a SIGNED offset**, so records live below
`$51b66` (the `~$4b000..$51b66` leader/settlement/scenery pool) as well as in
the arena above. Per cell it follows a singly-linked list: `next =
(int16)word[A3 + 0]`, `0` ends it.

Per record, `$115e0` reads **byte 6 = category**, an **EVEN value**; both
tables have entries for 0..44 (0 = no handler), and dispatches:

| table | addr | target | role |
|-------|------|--------|------|
| prepare | `$1162e` | `$1162e + word[$1162e + byte6]` | interpolate screen position, pick a frame index (into D2), sometimes blit inline |
| blit | `$1165c` | `$1165c + word[$1165c + byte6]`; **word 0 ⇒ no separate blit** | hand D2 to a blitter |

`byte6` indexes the table *directly* (it is already even, 0..44), not as `0..15`
times 2. `byte6 == 2N` is not "category N" (the numbering of older notes and
scripts), and every frame formula except the men's is keyed on `byte6` itself.
The blit table is at **`$1165c`** (`$1165a` in older notes is wrong);
`byte6 == 0` (men) blits via **`$11f78` → `$11f82`**, *not* `$1187c` (a
melee/dying sub-case, record byte 31 ∈ {`$32`,`$34`,`$06`,`$46`}).

**Every category.** Prepare and blit targets are decoded from the two
tables with `disassemble.py --jumptable 1162e 23` / `--jumptable 1165c 23`.
"Frames" says what the port draws; "checked" names the captures where the
port's frame equals the game's, pixel for pixel (see "Scoring a capture" below).

| `byte6` | prepare / blit | what it is | frames | checked |
|---------|----------------|------------|--------|---------|
| 0 | `$11c8a` / `$11f78` | man | walk or melee frame; plough and siege-engine overlays; flags bit 5 → the boat of 26 | walk, melee, boat (lands 0, 5, 25, 60) |
| 2 | `$117d8` / – | settlement building | building frame `record[7]` | all |
| 4 | `$1168c` / – | tree, building | `record[7]` + season offset | all |
| 6, 24 | `$117b0` (`a_object`) / `$11f78` | 24: the fishermen's catch marker; 6: a group's camp marker, placed by `$3744` (same drawer, `record[7] = $11`) | `record[7] + $100` (a catch marker has `record[7] = $10`, frame `$110` = a rowboat on the pond; a camp marker, formula only, `$111`) | 24: all; 6: not captured |
| 8 | `$11a86` / `$11f78` | animal | 16 facings | all |
| 10 | `$11772` / – | dropped equipment (a dead man's `record[33]`/`[44]` once `$1623c` finishes) | `$10f + (r33 − 8) >> 1`, `$142 + r44 >> 1` | land 5 |
| 12 | `$11bbc` / `$11f78` | dead man (`$5590` kill: side negated, `word[18] := $a0`) | body `$103 + (−record[5] & $ff)`; figure `$100 + record[32]` lifted `$a0 − word[18]` | land 5 |
| 14 | `$11bf4` / `$11f78` | banner / group member | `record[5] + $13e` | all |
| 16 | `$1192e` / – | leader's base (`$4f916` record) | building frame 7, then the leader's goods icons | lands 0, 5 |
| 18 | `$11c36` / – | projectile, `$312a0` art | `word[14] < 0`: 16 x 16 frame `word[14] + $2f` (`$1225c`); else 8 x 11 `$146` (`$11f7c`) | never seen; not ported |
| 20 | `$11b3c` / `$11f78` | carrier pigeon (`$4c112` pool, 26 B) | shadow `$148`; bird `$127 + (tick & 7)` lifted `record[15]`; `$151` for `$4c112` only | land 5 |
| 22 | `$11b2a` / `$11f78` | bird of a flock (`$4c5f4` pool, 22 B, `$4672` at world build) | as 20 | land 5 |
| 26 | `$1174e` / `$11f78` | boat | `$149 + record[5]`, 1 px lower on `[$4bb41] & 1` | via byte6 0 bit 5 (land 0) |
| 28 | `$11b0c` / `$11f78` | set at `$15462` in winter only | – | never seen; not ported |
| 30 | `$1198a` / – | building going up (`$5e3a`) | frame `$0c`, top rows cut off while `word[8]` counts down from `$10` | land 25 |
| 32 | `$1168a` / `$1168a` | nothing: `rts` in both passes (the end state of a dead man without goods) | – | – |
| 34 | `$11ab8` / `$11f78` | – | – | never seen; not ported |
| 36, 38, 42 | prepare word 0 / `$12258`, `$12258`, `$12244` | – | – | never seen |
| 40 | `$11c64` / – | projectile (`$57f0`, weapon tier in `D1`) | one colour-0 pixel (`$e6ee`) | land 25 |
| 44 | `$1184e` / – | dropped goods pile (`$3ac8`) | a goods icon per non-zero word at `record + 10 + 2e` | lands 5, 25 |

**Census of the categories.** Two rolls were screened, each by settling lands
and reading the bucket records.

- *Preview roll.* 37 lands: 33 built with `../py/build_land.sh` and settled 30M
  steps (`k` = 0-142), plus `k` = 20, 60, 100, 143. Categories 20, 22, 32, 40, 44
  and 12 occur at settle; 10, 30 and more 40/44 appear once armies fight
  (200M-step runs). No land showed 18, 28 or 34.
- *Play Random Land roll.* `PAGES0=1`, `k` = 0, 4, .., 140 and 143, settled 30M
  steps (`py/census.py`), 37 lands: categories 0, 2, 4, 8, 14, 16 and 24 occur on
  all 37, 20 on 31, 32 on 24, 6 on 17, 12 on 13, 22 on 10, 44 on 7, 40 on 4; none
  of 10, 18, 28, 30, 34, 36, 38 and 42 (tree records 221 to 342 a land).

**Goods icons, `$11886`.** Nine entries, each a frame and an offset from the
blit corner, laid out as a 3 x 3 block 2 px apart: `$116` (−2,−2), `$143`
(0,−2), `$144` (2,−2), `$145` (−2,0), `$23` (0,0, 16 x 16 `$312a0`), `$109`
(2,0), `$110` (−2,2), `$146` (0,2), `$1b` (2,2, 16 x 16 `$312a0`). Read in
`../economy.md`'s goods order, entry 0 is food and entries 1-8 are pike, sword,
bow, plough, boat, pot, catapult and cannon (the plough frame `$109` is also
the carried-plough overlay, and `$1b`/`$23` are the siege-engine art). byte6 44 draws
entry e for each non-zero word at `record + 10 + 2e`; byte6 16 draws entry
i + 1 for each non-zero goods byte i of its leader
(`$4e514 + word[record + 14]`, bytes 24-31). Port: `Sprites.goodsIcon`; the
exporter computes the mask (`pm_export.render_icons`).

**Men (`$11c8a`).** Flags bit 5 (in a boat) → `$1174e`. Melee modes `$32`/`$34`:
frame `$80 + weapon * 8 + (side − 1) * 4`, weapon = `record[44]` (0 if `>= $e`),
`+1` on tick parity `$57fec & 1` (with weapon 6, only when byte 18 is `$14`),
`+2` when facing away (`((heading + yaw + $40) & $ff) >> 7`), `+$40` if flags
bit 4. Otherwise `(side − 1) * 16 + facing * 2` (8 facings), `+$40` armed, `+1` on
`[$4bb41] & 1`. A man carrying a plough (`record[33] == 8`, `record[7] == 1`)
first draws `$109 + k` at `$11e40/$11e50[k]`, k = frame & 7; a man hauling a
siege engine (`record[44] >= $e`) first draws the 16 x 16 `$312a0` frame
`$1b + (record[44] − $e) * 4 + k` at the same offsets (`$11ebc`), k = facing
(melee: `(record[44] & $f) >> 1`). Plough and siege engines were never seen.

### Position — bilinear over the projected cell corners (`$11f1a`)

Every `$33000`-sheet prepare handler places the entity by interpolating the
cell's four **projected** corners (from `$3f364`, packed `(screenX<<16)|screenY`
— §3) by the entity's sub-cell fraction:

```
a0 = &$3f364[cellRow*64 + cellCol*4]          // the cell's TL corner
C00 = (a0)   C10 = 4(a0)   C01 = 64(a0)   C11 = 68(a0)
fx  = record[9]                                // = low byte of the BE word at record+8
fy  = record[11]                               //   ($11f12: move.w 8(A3),D6; andi.w #$ff)
pos = lerp( lerp(C00, C10, fx/256), lerp(C01, C11, fx/256), fy/256 )   // see below
screenX = pos.x + 0x3c                         // sprite anchor (cf terrain +64; −4 = ½ frame)
screenY = pos.y - 8
```

The lerp works on the packed longs, and the port copies it word for word
(`Sprites.packedLerp`, `pm_render_ref._packed_lerp`). Each edge delta is a
32-bit `sub.l`, so a borrow out of the low (y) half takes 1 off the x delta.
Each step is `muls` by the fraction with only the low word kept, then
`asr.w #8`. The two edge points are built swapped, `(y << 16) | x`, so in the
final `sub.l` the borrow runs from x into y. Treating the halves as two
independent lerps puts about one sprite in ten a pixel off; the exact version
matches the game's `D0`/`D1` at every blit checked and scores the captures
below pixel for pixel.

The corners here are the **raw** `$3f364` values (window-relative, no +64 HUD
inset; that inset is applied only via the terrain draw pointer `$e3e2`). So a
sprite sits at `raw + 0x3c` while its terrain cell sits at `raw + 64`, i.e. the
`0x3c` is "+64 inset − 4 for the half-frame". `pm_render_ref.py`'s `px − 4` over
+64-inset corners is the identical anchor. **Live-verified:** the 26
`byte6 == 14` sprites' computed positions match the `$11f82` D0/D1 registers to
≤ 1 px. (`a0` at `$11c8a` entry = `$3f474` for a cell at camera-offset `(+4,+4)`
= `$3f364 + 4*64 + 4*4`.)

### Frame index per category

`assets/sprites/sprite_triggers.json` carries the full ripped dispatch and every
per-category frame formula; the important ones follow the sheet table.

There are **four sprite sheets** (all 4-bitplane + AND-mask, MSB-first, opaque
where the mask bit is 0):

| sheet | frame | geom | blitter | positioning | categories |
|-------|-------|------|---------|-------------|------------|
| `$33000` | 55 B | 8 × 11, byte planes | `$11f82` | sub-cell lerp or centroid | byte6 0, 6, 8, 10, 12, 14, 20, 22, 24, 26, 28 and the goods icons |
| `$312a0` | 160 B | 16 × 16, word planes (10 B/row) | `$1225c` | as the caller | siege engines, goods icons 7-8, byte6 18, and the building sheet at zoom 6-7 |
| `$37c7c` / `$3af1c` | 480 / 640 B | 32 × 24 / 32 × 32, word planes | `$12244`→`$12326`/`$124a8` | sub-cell lerp (4) or centroid (2, 16, 30) | byte6 2, 4, 16, 30 |
| `$e6ee` | — | one pixel | `$e6ee` (`movep.l`) | any | byte6 40, the byte6 20/22 dot, the minimap |

`$37c7c` decodes cleanly as **buildings + trees** (verified byte-exact
against `pm78_settle`'s `$24400` live tree pixels). `$312a0` holds the same 27
building pictures at 16 x 16 (zoom 6-7), then the catapult (`$1b`-`$22`, 8
facings) and cannon (`$23`-`$2a`) frames the siege-engine overlay and goods icons
use.

| `byte6` | name | sheet | frame (D2) |
|---------|------|-------|------------|
| 0 | man | `$33000` | `(side−1)*16 + (((heading + YAW + 0x10) & 0xff) >> 5)*2` `[+0x40 armed, +1 anim]`. side = record[5], heading = record[17], **YAW = `[$ff9a]` ⇒ facing is camera-relative** (8 steps). Melee, plough and siege-engine overlays and the boat: "Men" above. |
| 2 | settlement building | `$37c7c` | `record[7]`, centroid (see "Settlement buildings" below) |
| 4 | tree / building | `$37c7c` | **(live-verified, D2 at `$12288`)** `r7 = record[7]`: `r7 == 0x0d` → `0x0d`; `(r7 & 0x7f) == 0x0e` → `0x0e`; else `(r7 & 0x7f) + word[$11746 + word[$57fd0]]`. `word[$57fd0] = ($58146 & 3)*2` (per-mission tile-set selector); table `$11746 = {0:0, 2:3, 4:6, 6:9}`. Mission 1 (`$57fd0`==4) → `+6`, so `r7` 0x11/0x10/0x0f → frame 0x17/0x16/0x15. **Position: `$11f1a` sub-cell lerp** (like the men) with an *address-jitter* `fx/fy` = `fx = (((A2+A3)&0xffff)<<3)&0xff`, `fy = (((A2+A3)&0xffff)+(A0&0xffff))&0xff` where `A2 = &$47970[cellY*64+cellX]`, `A3 = record`, `A0 = &$3f364[row*64+col*4]`; then `$12272` `−4/−8` → raw anchor `(lerpX+0x38, lerpY−16)`. |
| 6, 24 | 24: the fishermen's catch marker (`a_object` `$117b0`; planted on shore cells by `$2984`, `../economy.md` 5a; side in `record[5]`, `record[7] = $10`); 6: a camp marker (`$35f4` calls `$3744`, which writes it into the pool slots after the fishermen's markers, `record[5]` an AI side, `record[7] = $11`; evidence under the table) | `$33000` | `record[7] + 0x100`; if `== 0x112` add `[$57fec] & 3` (4-frame anim). Centroid (`$1182a`). A catch marker (`r7 == 0x10`) draws frame 0x110, a rowboat on the pond (`../catch_marker_boats.png`; live: `bp 1182a`, 30 of 30 marker records had `D4` low word `$0110`). `$61f8` turns the marker into one boat for the group that takes it (`../economy.md`, `../strategy.md`). |
| 8 | animal (sheep) | `$33000` | `(((record[14] + YAW) & 0xff) >> 5)*2 + 0x117` `[+1 anim]` — 16 frames, camera-relative facing. **Live-verified:** D2 = 0x123/0x124 at `$11ab6`. Sub-cell lerp. |
| 10 | dropped equipment | `$33000` | `$10f + ((record[33] − 8) >> 1)` if `record[33] != 0`, then `$142 + (record[44] >> 1)` if `record[44] != 0`, same place |
| 12 | dead man | `$33000` | body `$103 + (−record[5] & $ff)`; figure `$100 + record[32]` at `screenY − ($a0 − word[18])` |
| 14 | banner / group member | `$33000` | `record[5] + 0x13e` (side-indexed) |
| 16 | leader's base | `$37c7c` + icons | building frame 7 (`$12244`), then the goods icons |
| 18 | projectile | `$312a0` / `$33000` | `word[14] < 0`: `word[14] + 0x2f` (16 x 16); else `$146` |
| 20, 22 | pigeon, flock bird | `$33000` | `$148` shadow; `$127 + ([$57fec] & 7)` and (record `$4c112` only) `$151` lifted `s8(record[15])` (`+$30` if negative); a colour-5 pixel at `screenY − record[14]` if `record[14] != 0` |
| 26 | boat | `$33000` | `(record[5] & 0xff) + 0x149`, one pixel lower when `[$4bb41] & 1` |
| 28 | (winter only, `$15462`) | `$33000` | `0x150`, or `([$57fec] & 1) + 0x14e` if `record[5] > 0` (not ported) |
| 30 | building going up | building sheet | frame `$0c` with the top rows cut off, see the table above |
| 40 | projectile | `$e6ee` | one pixel, colour 0 |
| 44 | dropped goods | icons | the goods icons |

**Camp markers (byte6 6).** The camp marker is created by `$35f4` through
`$3744`. Evidence that `$3744` is the writer: 2 of 2 new records between two
snapshots of one land matched 2 `$3744` hits, and 4 of 4 records read on two lands
(0 and 60) sit at pool slots 30 to 32 with byte 7 `$11` and sides 2 to 4. A camp
marker occurs only after the build: it is present in 17 of 37 Play Random Land
lands settled 30M steps, and the preview-roll screen under "Census of the
categories" did not list it.

**The `+0x40` "armed" variant (cat 0):** `D2 += 0x40` iff `record[7] bit 4` set
**and** (`record[7] bit 7` clear **or** the unit's group == `[$57ffe]` the
selected group). (The live man checked had `record[7] = 0x10` → frame 64.)

**Byte6 4 (trees and buildings).** The frame formula, the `$11746`/`$57fd0`
offset table and the address-jitter position are all **pinned and
live-verified** (D2 at `$12288`); the 32 × 24 word-plane decode is byte-exact
against `$24400`'s live tree pixels. `word[$57fd0]` is the season, which
`$1abaa` advances once per fade (§4 "Seasons"), so a faithful port reads it each
frame rather than baking `+6`. `pm_render_ref.py`'s `_entity_frame` + `load_ram` +
the `draw_entities` "prop" path implement it, and `Sprites.fs` has
`frameForProp` / `Season.treeTileOffset` / `propJitter` / `propScreenPos` /
`decodeFrameWord`. It is **not in `COMPOSITE_CATS`**: compositing it lowers the
score, but not from a formula error. `pm78_settle`'s two compose buffers
disagree on the entity layer by ~14.6 k px (`$115e0` redraws a *subset* of
entities per frame, double buffered), so neither reference buffer holds all 25
trees. Scoring it needs a clean single-buffer populated capture (§9 "Ruled-out
causes").

**The per-cell entity pass in F#.** It lives in `Sprites.fs` (`EntityRec` /
`EntityCtx` / `entityFrame` / `blitEntity` / `drawEntities`) and is
**cross-checked byte-exact** against `pm_render_ref.draw_entities` on synthetic
corners + record fields: 13/13 cases, `byte6 ∈ {0, 4, 8, 14, 24}`, covering the
melee→nothing case, the prop `r7 ∈ {0x0d, 0x0e}` special-cases, animal/banner
facing, and the centroid markers (`scratchpad/pm90_xcheck.fsx` / `.py`, scratch
only, see Status). `drawEntities` replays `$115e0` as a post-terrain far→near
pass in `walkQ3` cell order (same approximation `pm_render_ref` uses); `byte6
6/24` use the `$1182a` centroid, everything else the `$11f1a` sub-cell lerp. Fed
the real 53-record stream and the `$3f364` corners of `pm88_f1.ram`, the F#
output is byte-identical to `pm_render_ref.draw_entities`: 2881/2881 covered
pixels, `byte6 ∈ {0, 4, 6, 8, 14, 24}` (`scratchpad/pm91_ent_fs.fsx` /
`pm91_ent_py.py`, scratch only).

**The record stream (`entities.json`).** `tools/pm_export.py`'s `export_entities`
walks every cell's `$47970` bucket chain over the whole map, from `pm88_f1`
(`--entities-ram`), and writes `render_entities[]`: per record its address, its
world cell and the fields the drawn categories read (`byte6`/`b5`/`b7`/`b14`/
`b17`/`b31`/`fx`/`fy`/`group`), 276 records. `entity_ctx` carries the capture's
view (`cam_x`/`cam_y`/`yaw`/`half`), `season`, the animation phases and the four
sheet paths. A record reached twice, or a link outside the record pools, is an
export error: it means the capture caught a bucket chain mid-relink.

The `byte6 == 4` jitter is not stored: it depends on the cell's place in the
window, so `Sprites.recordJitter` computes it per frame from the record address,
the bucket slot and the corner address. At the capture camera it reproduces the 53
jitters `load_ram` computes.

With the records from the whole map, the port draws sprites at every camera cell.
At two cells panned in the emulator from `pm88_f1.snap` (`w 4bb3a`, 2M steps;
`scratchpad/pm119/pan_{e,w}`, `pan_check.fsx`), drawing the exported records gives
the same frame as drawing each capture's own records (identical at `pan_e`; at
`pan_w` one man had moved), and the inline order beats sprites-last there too.

**Draw order: sprites are drawn inside the walk.** `$f898`'s walk calls `$115e0` for each
cell straight after drawing that cell's two triangles, so nearer terrain covers farther
sprites and nearer sprites cover farther terrain. In the port, `Fill.plan` returns the walk
as data (`planQ0`..`planQ3` → a `Cell list` in draw order, each cell with its corners and its
two `Tri`s in order), `Scene.steps` puts each cell's `$47970` bucket sprites after its
triangles, and `Scene.render` draws the result, which is what `TerrainView.cs` and the viewer draw.
`Fill.walk` draws the plan without sprites and is byte-identical to a direct walk (16 yaws ×
5 cams × 2 ticks, `scratchpad/pm118/baseline.fsx`). Evidence for the order, drawing every
ported category, scored against the game's own compose buffer
(`scratchpad/pm118/order_test.fsx`, inputs from `load_ram` via `dump_frame.py`):

| capture | terrain only | sprites last (`drawEntities`) | inline (`Scene.render`) | px where the orders differ: game = last / inline / neither |
|---|---|---|---|---|
| `pm88_f1` (yaw `$f0`) | 94.1% | 92.28% | **99.99%** | 0 / 1171 / 1 of 1172 |
| `pm78_settle` (`$f0`) | 94.6% | 86.90% | **94.62%** | 0 / 1171 / 1 of 1172 |
| `pm74_late` (`$f0`) | 94.4% | 93.62% | **99.69%** | 0 / 909 / 4 of 913 |
| `rot40` (`$40`) | 94.4% | 92.66% | **99.97%** | 0 / 1326 / 0 of 1326 |
| `rot90` (`$90`) | 84.8% | 96.75% | **99.92%** | 0 / 425 / 1 of 426 |
| `rotc0` (`$c0`) | 91.1% | 95.03% | **99.81%** | 0 / 658 / 0 of 658 |

The `rot*` captures are `pm88_f1.snap` rotated in the emulator (`w ff9a 00YY0015`,
2M steps, `scratchpad/pm118/rot*.snap`). Terrain-only scores are low where trees and
buildings cover the most terrain (`rot90`); away from sprites the terrain matches at
99.7-99.96% (`scratchpad/pm118b/`). Drawn inline, every ported category raises the
score.

`pm_render_ref.py` draws the same way (a per-cell `_cell_done` hook in every walk
handler, all categories it knows): it matches `Scene.render` on all 15178 drawn
pixels of `pm88_f1` (`reversing/powermonger/py/parity.py`). It lacks the later-land
categories. `Sprites.drawEntities` / `pm_render_ref.draw_entities` are the
sprites-last path, kept for the parity checks.

`pm78_settle` stays near its terrain-only score, consistent with its two compose
buffers disagreeing on the entity layer (not checked further). The remaining pixels
of the other five are units that moved between the snapshot and the frame on screen
(see "Scoring a capture"). At yaws `$40`/`$90`/`$c0` the game shows every visible
sprite pixel the port draws.

Screenshots: `assets/reference/godot_screenshot_backdrop_118th.png` (inline, over
the `$78000` backdrop), `godot_screenshot_inline_118th.png`, and
`godot_screenshot_entities_91st.png` (sprites last).

**Scoring a capture.** A snapshot stopped at `$f898` holds the state the
next frame is drawn from, while its finished compose buffer holds the frame drawn
from the previous state (one water tick, one flap, one step of every walker
behind). So the port's frame for snapshot i is scored against the screen in
snapshot i + 1, the next `$f898` (`reversing/powermonger/py/capture.sh` takes such a
sequence, `score.fsx a.json+b.json` pairs them). Scored that way at the RAM's own
water tick, 27 frames from 12 views on lands 0, 5, 25 and 60 (including winter
snow, autumn rain, a fight, a projectile and boats) match the game pixel for
pixel, 100.00%, with every category in view at 100% of its visible pixels
(`scratchpad/pm121/allpairs.txt`). Scoring land 60 with tick − 1 is the same
pairing seen from the other side: that tick is the previous frame's tick.

**Settlement buildings, `byte6 == 2` (`$117d8`).** Frame `record[7]` with no tile-set
offset, anchored at the cell centroid (`$1182a`: +`$38`, -8 over raw corners), then
`$12244` like the trees. At zoom 4-5 that is the 32 x 24 sheet and (-4, -8), so in
+64-inset corner space the top-left is centroid + (-12, -16). `record[7] == $0a` also
draws an overlay via `$119b2` from `record[12]`/`[16]` (not ported). This is the keep
inside the hilltop fort; drawing it raises `pm88_f1` inline from 95.93% to 96.80%.

**Zoom: `$12244` picks the building/tree art.** The same 27 pictures exist at three sizes,
packed back to back: `$37c7c + 27 * 480 = $3af1c`, and the 27 32 x 32 frames end before
the `$3f364` corner buffer. `$12244` picks by the zoom index `[$57ffc]`:

| `[$57ffc]` | sheet | frame | offset added to the anchor |
|---|---|---|---|
| 1-3 | `$3af1c` (`prop32_sheet_raw.bin`) | 32 x 32, 640 B | (-8, -16), `$12294` |
| 4-5 | `$37c7c` (`prop_sheet_raw.bin`) | 32 x 24, 480 B | (-4, -8), `$12272` |
| 6-7 | `$312a0` (`struct_sheet_raw.bin`) | 16 x 16, 160 B | none, `$12258` |

Men, animals, banners and markers use the 8 x 11 `$33000` frames at every zoom; only
their positions scale. Port: `Sprites.propSheet`. Evidence in §5.

**Open.** Per-category frame *counts*; byte6 18 and 28, and the plough and
siege-engine overlays, are ported from the code but never seen on screen (18 and
28 not ported); and the `byte6 == 2`, `record[7] == $0a` overlay (`$119b2`), which
a byte6 18 hit on a settlement building sets (`$596a`).

**Why 18 and 28 are missing from the runs** (from the writers).

*Byte6 18 and 40.* `$52fc` fires byte6 18 when the shooter's `44(obj)` is `$e` or
`$10`, and byte6 40 when it is 6. Nothing ever writes `$e` or `$10` there. The
writers of `44` are the world build (`$2452` copies byte 21 of the side block
`$580a6[side]` into the side's first unit, but `$245c` then overwrites it with 6;
`$2500` gives each follower byte 23, which is 0, 2, 4 or 6 in all 195
campaign-table entries) and the equip paths `$16124` / `$159de`, which write 2, 4
or 6. So byte6 18 is unreachable in this build: the `$e`/`$10` arm of `$52fc` is
dead, and so are the other `44 >= $e` tests (`$3ffc`, `$39d4`). The four run
lands' men carry only `44 ∈ {0, 6}` (3,851 bucket-walk men over the 28
`pm121/run` snapshots).

*Byte6 28.* `$15462` needs winter, a group of 2 or fewer and `33(obj) == 8` (a
plough), which only `$1616c` writes, from the leader's goods slot `27(L)`; that
slot was stocked in 1 leader-snapshot of the runs. So 28 is reachable but rare
and not observed.

### The mini-sprite blitter (`$11f82`, `assets/sprites/sheet_raw.bin`)

From the aligned `$11fe4`–`$12034` loop: each frame is an
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
(0–127 = the four faction man blocks, stand/walk
+ armed variants; 128–287 = the melee/action poses; `0x117`+ = animals;
`0x100`+ = number / flag glyphs; `0x14e`/`0x150` = icons). `prop_sheet_contact.png`
(`$37c7c`, `decode_wordsprite(f,32,24)`) and `struct_sheet_contact.png`
(`$312a0`, 16 × 16) decode cleanly as buildings/trees and small
structures/siege-engines respectively.

### The pixel plotter (`$e6ee`)

`$e6ee` sets one pixel: `D0` = screen x, `D1` = screen y, `D2` = colour, into the
buffer at `A0`. The long at `$e762 + 4x` holds `(x & 7) * 8` in its high word (an
index into the bit masks at `$e722`) and `(x >> 4) * 8 + ((x >> 3) & 1)` in its low
word (the byte in the row), for x = 0..319. It adds `y * 160`, then
`movep.l 0(A1),D2` / `and.l mask` / `or.l colour` / `movep.l D2,0(A1)` writes the
one bit in all four planes, the colour's plane bytes coming from `$e6ae + 4c`. It
does not clip. (`disassemble.py` shows the two `movep.l` opcodes, `$0549`/`$05c9`,
as `subi`.) It draws the byte6 40 projectiles, the byte6 20/22 dot, and the
minimap dots, including the blinking selected group (`$165b2`, one dot per member
at its raw cell coordinate). `assets/hud/descriptor_table.bin` is this table
(320 longs from `$e762`; the operand of `move.l 110(PC,D0.w)` at `$e6f2` is
relative to `$e6f4`); all 320 entries match the formula above.

### Trees / buildings / mountains

- **Mountains are terrain**: a run of high cells, drawn by the same triangle
  fill with a high colour byte. No mountain sprites.
- **Trees / buildings are bucket sprites** (`$115e0`, their own category
  values) drawn over the cell they occupy; they pop in/out at cell granularity
  when the camera rotates.

---
## 7. Frame pipeline

Screen output is **direct-to-shifter**, double-buffered by the base register
(no XBIOS). Two compose buffers `$2df7c` (front) / `$2df78` (back), plus a
**terrain master at `$78000`** (32000 B), built once per mission.

**The `$78000` master.** `$12ce0` copies from
`A0 = $78000` (32000 B) to the back buffer every ~3rd frame. `$78000` is the
**HUD + stone border + the pre-rendered open sea + a hole where the island
goes**, built once at mission load by `$13b9a`. The sea (palette idx 14/15) is
baked into it; it is not a solid black diamond.

Per frame, `$f898` redraws **only the island** into that hole. Verified: the
composed `$1c700` buffer differs from the `$78000` master **only** in idx
6/7/11/12/13 pixels (the island) plus a few unit sprites; the ~2 460 water
pixels in the viewport are byte-identical to the master across `pm78_settle` /
`pm74_late` / `pm70_iso`. `$f898` refills the whole island each time it runs;
its camera/yaw/zoom compare (`$f8b6..$f8e2`, against copies at `$f890..$f896`)
gates only the `$fec6` re-projection, never the fill.

Consequence for a port: the per-frame renderer draws the projected 8×8 terrain
grid and nothing else. A from-scratch full frame composites that over the master
(HUD + border + sea). The `$f922` `jsr $11f82` with frame `0x149` and
`D0 = camCellX-3` is **not** a sea fill: `$11f82` is the 8×11 four-plane
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
    $f898   terrain: refill every island cell, sprites inline
  -- every tick --
    $14b62  entity FSM      (relinks $47970 cell buckets via $163ea)
    $6a3a   order executor
    $7a56   sprite / HUD compositor -> back buffer
    $165b2  selected-group marker
  -- at the VBL ISR --
    $187a   swap front <-> back, write (front >> 8) to $FFFF8200
```

On `pm71_run1.snap`, `$12ce0`, `$f898` and the swap `$187a` each run once per
sim tick (13 hits each in ~2.78M steps; one tick ≈ 15 VBLs), so every presented
frame holds a freshly filled island.

**Weather.** Rain and snow are drawn over the finished frame.

*Start and end of a spell.* `$1ad74` starts a spell when
`([$4bb4a] + [$57fec]) & $a0 == $a0`: `[$4bb42] := word[$1ad9c + word[$57fd0]]`
(winter 2 = snow, spring and autumn 1 = rain, summer 0 = none) and
`[$4bb44] := (that sum & $3f) + $20` ticks. `$4bb4a` is always 0, so the start is
at `[$57fec]` = 160 and the counter is `$40`, which draws 65 times. The start
needs `[$4bb44] >= 0`: the wrap of a season sets it to 0 and the end of a spell
leaves -1, so each season has at most one spell. While `[$4bb42] != 0`, `$1ad2a`
calls `$1a856` (16 word-groups by `$c2` rows from row 6, x 64, i.e. the whole iso
window) and counts `[$4bb44]` down; below 0 the spell ends.

*Drawing.* Each call adds `$40` to the byte at `$1aac8` (4 animation frames); row
r takes the long at `table[(phase − 4r) & $ff]`, its low word on even groups and
its high word on odd ones. Rain (`$1a8a4`) ORs the word into all four planes,
colour 15; snow (`$1a9c8`) ORs planes 0 and 2 and clears 1 and 3, colour 5. The
two tables are `assets/weather.bin`, the port is `Weather.fs`, and winter snow
and autumn rain frames of land 5 match the game pixel for pixel.

*Strategy effect.* While a spell lasts, `$3fb0` takes `$10` off a group figure
(and winter 8 more), so weather also slows something in the strategy layer
(`../economy.md` §3).

**Water shimmer.** `$4bb3e` is a longword tick counter, written only at `$13034`
in the `$13000` tick and incremented once per tick. Water cells (`< 0x0c`) add
`[$4bb3e] & 3` to their colour byte; dither slots `0x00`-`0x03` and
`0x08`-`0x0b` hold the same colours in different stipples, so water inside the
drawn window changes pattern every tick and repeats every four ticks. The open
sea outside the window is part of the static `$78000` master. The palette never
changes.

| capture (`pm71_run1.snap`, 249 frames, `ATARI_FRAME_DIR`) | result |
|---|---|
| start camera (window cells x 36-43, y 47-54, heights `0x1d`-`0x3b`, no water) | ~77 bytes change, all unit sprites and the marker blink |
| `w 4bb3a 002c0033` (window x 40-47, over the east coast) | every tick 2147-2371 px change, ~96 % water (idx 14/15) in the walk-drawn sea strip (x 197-317, y 91-158); frame N == frame N+60 |

**The HUD minimap.** It is baked once into the `$78000` master by `$13b9a`
(`$107d6`, `../graphics.md` "The minimap and the conquest map"), not drawn per
frame. `$13b9a` first `$df8c`-copies a pre-built frame bitmap (resource dispatch
via the `$e040` / `$e084` / `$e0c4` tables), then `$107d6` plots the 63 x 128
cells with `$e6ee`.

*Placement.* Cell (x, y) of the source plane `$418ad` (colour A) is the master
pixel (x, y + 6): a static read of `$107d6` shows `D3` counting x from 0 into
`D0`, `D4` starting at 6, and `$e762[0]` mapping x = 0 to byte 0 / mask `$80`, so
there is no `+1`; this is also what `py/maps/gate_minimap.py` proves pixel-exact
(1024000/1024000 pixels over 4 modes on 4 snapshots). The port's
`MinimapOrigin = (1, 6)` plots cells indexed from `$418ae`
(`pm_render_ref.draw_minimap(src="418ae")`, 100% against the master), which is the
same pixel. The stand-in that plots colour plane B (`TypeAt`, a from-scratch port
with no `$13b9a` buffer) agrees with the master at 94.5% and 98.8% land/water over
2442 cells at that empirical offset.

*Colours.* `$107d6` maps the source byte to a shifter palette index through the
66-byte table `$108ce` (mode 2; reconstructed as `Terrain.minimapPaletteIndex` /
`pm_render_ref._minimap_palette_index`): `0 → 14` (sea); `≤ 0x1c → 3`;
`0x1d → 2`; `0x1e, 0x28 → 12`; `0x23-0x27 → 13`; `0x29-0x2c → 11`;
`0x2d-0x38 → 10`; `0x39 → 6`; `0x3a → 7`; `0x3b+ → 9` (gold coast and peaks), a
terrain-elevation ramp like `Terrain.flatPaletteIndex`. The HUD chrome clips the
visible part to roughly `y ≤ 82`.

*Camera box.* `TerrainView.cs` draws the minimap panel with a live camera-window
box (`assets/reference/godot_screenshot_minimap_90th.png`); the game draws no
camera-viewport rectangle, the box is a port addition.

*Per-frame differences.* Between a settled compose buffer and the master in the
minimap rectangle there are three: (a) the software cursor / selected-unit marker
`pm_draw_cursor_marker` `$138c` (a save-under sprite, saved address `$1c49a`,
position `$2df92` / `$2df94`, about 8 x 11, colour 8; it is drawn over the iso view
and the minimap wherever the cursor sits), (b) a static diagonal chrome mark of
about 6 px at the minimap's top-left corner (screen (5..10, 6..10)), and (c) in
`pm73_fight` only, about 5 px of colour 5 at an enemy lord's own cell (29, 62)
during the fight there, a candidate lord-position dot not confirmed as systematic.
The master's minimap region and the `$3f86c` plane are byte-identical across
`pm78_settle`, `pm73_fight`, `pm74_late` and `pm89_pan_e`, and a one-frame `watch`
of `pm88_f1` found 0 px of difference, so an ownership tint is unconfirmed
(Status).

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
| fill | 4bpp pattern table `dither.bin`, indexed `colourByte*128 + ((8*y) mod 128)` | height-ramp fragment shader over the 16-colour palette, optional ordered dither for the look |
| draw order | far→near grid walk, sprites inline | **keep this** — per-cell (terrain then occupants); do not add a separate sorted sprite pass |
| zoom | 7 discrete geometry sets, `$fe04` | 7 camera distances (or continuous); same mesh |
| rotation | 16 yaw steps, `$13f8a` sine table | continuous yaw; `sin`/`cos` |
| water | `colourByte += [$4bb3e]&3`, fill-driven, applied on every walk | palette-index animation or a small UV scroll in the shader |
| perspective | real `x/(EYE-depth)` divide | keep for PM's look (free in a vertex shader), or go axonometric |

---

## 9. Evidence notes and ruled-out causes

What is open is listed in "Status" at the top. This section keeps the evidence levels and
the causes that were checked and excluded, so they are not re-investigated.

**Evidence levels.** See `../ai.md` "Evidence taxonomy".

- **Proven.** The projection maths (§3) and the `$ef62` / `$e420` rasteriser (§4): every
  triangle input, every scanline's DDA span and the dither phase byte-exact against a live
  single-step, all 81 projected vertices byte-exact, and `$fecc` Proven by `callcap`
  (3240/3240 vertices). The dying-entity path `$1623c` that feeds byte6 12/10/32, against the
  real 68000 (275/275 tracked bytes over 23 states on natural kills, `../py/diff_1623c.py`).
- **Corroborated.** The sprite frame formulas and the `$115e0` bucket walk (§6): by
  disassembly, live `D0`/`D1`/`D2` probes and the F#-vs-Python cross-check, and every ported
  category in view matches the game pixel for pixel on 27 later-land frames (§6 "Scoring a
  capture").
- **Observed.** "No per-frame sea fill" and "the minimap is baked once" (true for
  `pm78_settle`, `pm88_f1`, `pm73_fight`, `pm74_late`, `pm89_pan_e`).
- **Not covered here.** The simulation routines (entity FSM, combat, heartbeat, regroup,
  teardown and the rest) are proven in `../ai.md` and `../economy.md`.

**Ruled-out causes of the residual error.**

1. **The `0x1c` coast-slope dither is not the yaw-`$f0` residual.** With `walk_q3`
   instrumented for painter's-order occlusion (cross-checked against the 14469-pixel score),
   every tall `0x1c`-forced triangle checked (up to 32 scanlines, in `pm78_settle` and `pm83_q1c`)
   has **zero surviving pixels** in the final composite: nearer cells overdraw them. Across the
   whole `pm78_settle` frame only **12 of 14469** drawn pixels are finally `0x1c`-owned.
2. **The yaw-`$f0` residual is unit sprites.** The 810 mismatched pixels (5.6% of drawn) form
   44 connected components, and 8 of them account for 94%; several have the bounding box of an
   8 x 11 sprite (8 x 11 at (128,78), 9 x 8 at (109,93)) and the largest (35 x 15, 18 x 12) read as
   clusters of adjacent sprites. With the sprites composited (§6) the score rises, and the
   remaining pixels of the captures are units that moved between the snapshot and the frame on
   screen.
3. **No stale bytes in the `$ef62` record.** `$e420`'s edge-reload loop reads an
   arbitrary-length (run, slope) stream from one pointer shared by both edges, ending the triangle
   on any zero run count, so it could read stale data past the documented 26-byte record. The 6
   spare bytes at record offsets 26-31 read **zero across 8 live triangle draws**. The dither
   setup's `move.w (A0)+,D6` at `$e3e6` reads a word at record offset 0-1 although `$ef62` writes
   only the colour byte; offset 1 read `$00` across 6 live draws.
4. **The low scores of `pm83_q{0,1,2}c.ram` (35-50% exact-index) measure the captures.**
   - *How the captures were made.* They were reached by 16 synthetic rotation pulses and frozen
     mid-swap. `[$ffa2]` flips by 128 on every re-projection (§4 "Dither phase").
   - *Evidence.* A real q1 triangle's 22-row `A5` sequence matches exactly (22/22) with the
     phase added inside the mod-128 wrap, but the captures score 35-47% with or without it,
     while clean captures at the same yaws (`scratchpad/pm118/rot*`) score 85-94% with it and
     99.7-99.96% on terrain away from sprites. In `pm83_q2c` the buffer heuristic picks `$24400`
     (35.4%) but `$1c700` scores 52.7% and is far closer to the `$78000` master in the HUD strip
     (25 vs 153 px); `pm83_q1c` and `pm83_q2c` have the same `$e3e2` draw pointer (`0x1c720`) yet
     need opposite buffers.
   - *Error shape.* The large errors form coast / diamond-edge-shaped blobs (65 x 49, 89 x 24)
     and the ±1 errors one frame-wide blob (q0: 3035 px, 150 x 89): sub-step camera drift
     between the displayed framebuffer and the captured corners, not a per-triangle error.
   - *Live single-step.* On `pm83_q2c` all 128/128 `$ef62` calls, the `A5` phase of two
     triangles and the DDA endpoints of a 27-row triangle are byte-exact (§Status).
   - *Gate.* Do not form further rasteriser hypotheses against `pm83_*c`.
5. **The green-versus-black region in `pm83_q2c`** (rows y ≥ 155 near the iso window's right edge,
   33-36 scanline grass cells at (36,47), (37,47), (38,47): solid green in the port, near-black in the
   reference) is not explained. Excluded: `$f202` vertex clip-and-resubmit (the cells' raw screenX
   tops out near 210, inside `$ef62`'s `[0,255] x [0,199]` bounds) and the right-edge clip (§3). The
   likeliest cause is the capture (item 4); that is inferred, not traced.
6. **A populated second reference is not obtainable by moving the camera.** The mission map is a
   pure function of the world RNG seed `$12c9a` (which fills `$58146`) plus the size override
   `$5809c`, consumed by `$13b9a` / `$10d1e` on the briefing-OK click; `$58148 < $2000` ("small
   preset") already gives 10-13 lords. Mission 1's own map has `byte6 ∈ {0,2,4,8,14,16,24}`
   map-wide (only `{0,2,4,14}` in the default camera window; the 16 and 24 records, the lord's
   base and the catch markers, are NW of the start). A camera poke (`$4bb3a` / `$4bb3c`) brings
   them into view but re-triggers the per-frame terrain redraw and gives a capture that is not a
   scoring reference. Populated references are built lands (`../py/build_land.sh`,
   `../README.md` "Driving a later land"); `pm88_f1` remains the regression anchor.

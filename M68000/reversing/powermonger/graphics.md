# PowerMonger ST — the graphics pipeline, and what a modern port would change

This is the narrative account of how PowerMonger draws its screens and what a port
would change: the terrain rasteriser (projection, grid walk, pattern fill, seasons,
water shimmer), the land build that bakes the planes, sprites and their draw order,
the minimap and conquest map, backdrop pieces, palettes and fades, the frame
pipeline, measured renderer profiles, camera control, zoom, and a modern-port plan.
The porting contract, with every constant, table layout and verification record, is
`port/SPEC.md`; where this file is less detailed, SPEC is the reference.
Addresses are in the relocated game image (link base `$1050`). Claims are labelled as
in `strategy.md`: **proven** (a gate script with a match count), **live**, **code
read** or **inferred**. The system services of the same address range (sound, save
disks, serial link) are in `system.md`; the simulation that feeds the renderer is
`ai.md` / `strategy.md`.

## Summary

The isometric view is a **software heightmap-grid rasteriser**:

- `$fec6` projects the grid corners with a rotation and a true perspective
  divide, and only when the camera cell, yaw or zoom changes.
- `$f898` walks the grid far to near and fills **two triangles per cell** from
  a 4-plane pattern table, using the terrain byte as the colour index.
- Each cell's sprites are drawn straight after that cell's triangles, so the
  walk order is the depth order.
- There is no mesh, no texture map, no light model and no palette cycling.
- The frame is composed off screen and shown by swapping the shifter base
  register.

## Pipeline shape (world map / menus / iso view all share it)

| routine | role | shape |
|---------|------|-------|
| `$88ac`–`$8960` | menu / dialog / credits compositor | 4-bitplane word blit: per plane `move.w (A0)+,Dn / rol.w / andi.w #$fNNN`, OR the 4 planes, `move.w Dn,(A5)+`; unrolled ×6, `lea 152(A5),A5` row stride, `dbf D6` outer; command stream at `A4` |
| `$11422` | world-map per-VBL screen refresh | `lea $3f364,A0` (off-screen composed buffer), `mulu #$a0,D0` (row×160), `movem.l (A0)+,#$7cf8` / `movem.l #$7cf8,(A1)` (44 B/`movem`), 58 inner × 3 outer |
| `$1870`–`$1876` | VBL-wait spin | dominates every static screen (world map, briefing, settled iso view) |

Screen output is **direct-to-shifter**: the displayed base is written to
`$FFFF8201/8203` (`$024400` at menus, `$01c700` in the iso view), not through
`_v_bas_ad`, and the palette goes straight to `$FFFF8240`. There are no XBIOS
`Setscreen` / `Setpalette` calls. Every screen is built in an off-screen RAM
buffer with software plane blits and shown by a base-register swap.

## The terrain mechanism

### The model is a heightmap grid

There is **no vertex list in RAM**. The terrain lives in parallel 8 KB planes
around `$438ee` (`ai.md`), index `(y << 6) + x`: the **altitude** plane `-16514(A1)` = `$3f86c` (`_alts`), the height source the
projector reads (proven by poking it: a plateau, 10938 pixels, `py/alts_render_check.py`); a **colour** byte for the cell's first
triangle at `0(A1)` and one for the second at `-8257(A1)`, both derived from the altitude plane by the build pass `$10058` (a slope
shade, so the lighting is baked in; 0 = open sea; poking either changes the tone of one triangle, ~2200 pixels, geometry unchanged,
`scratchpad/pm136/planes/plane_ab.py`); and a flag byte at `+8257(A1)` (`$4592f`): bit 7 selects the diagonal that splits
the cell, bit 1 pins the cell's altitude against the `$10410` smoothing pass (settlement sites; the river carver `$10458` has no direct caller). Corners are generated
during the walk, so the mesh is implicit in the grid.

### `$fec6` — project the grid corners

```c
// A0 = $3f364 corner buffer (2 words/corner: screenX, screenY)
// A1 = $3f86c + camera offset  (height source)
// D7 = {cos, sin} from the $13f8a sine table, indexed by $ff9a
for (row = -H; row <= H; row++)             // H = $fdec, zoom-dependent half-extent
  for (col = -H; col <= H; col++) {
     int z = (cellHeight - $fec4) * $ff9c >> 4;          // height, scaled by zoom
     int wx = -col * $ff9c,  wy = -row * $ff9c;          // grid pos in world units
     int rx = wx*cos - wy*sin,  ry = wx*sin + wy*cos;    // rotate by $ff9a
     // $ff7c: perspective divide
     int sx = rx * $ff98 / ($ff98 - ry);
     int sy = (z - $ff96) * $ff98 / ($ff98 - ry) + $ff96;
     *A0++ = sx + 0x80;                                  // + screen centre X
     *A0++ = 0x7c - sy;                                  // flip Y
  }
```

- **`$ff96` = HORIZON (130) and `$ff98` = EYE (320)** are the projection
  parameters. `$ff7c` reads them PC-relative (`4(PC)`, `12(PC)`, `26(PC)`), so
  they do not appear as absolute operands. Changing them has no visible effect
  until something forces a `$fec6` rebuild.
- The projection **is perspective** (`x / (EYE - depth)`), not an affine 2:1
  iso. The isometric look comes from a fixed camera pitch plus 16 yaw steps
  (`$ff9a`). `$ff7c` does two `divs` per corner.
- The integer maths reproduces the game's `$3f364` corner buffer byte for byte
  (SPEC §3). `$fec6` is the entry (`lea $13f8a.l,A3`, then it falls into the body at `$fecc`).
  **Proven vs the real 68000 with `callcap`:** `$fecc` called in isolation with `A3 = $13f8a` (a bare call with a
  garbage `A3` leaves 158 of 162 corner bytes wrong) recomputes a `$3f364` byte-identical to the stored buffer on
  four captures, and an integer reconstruction of `$fecc` + `$fe8e` (HBIAS) + `$ff7c` (the divide), with no float and
  no fudge, matches it on 36 generated camera-cell states plus 4 natural captures, **3240/3240** vertices
  (`scratchpad/pm92/proj_ref.py`, `diff_fecc.py`; not promoted to `py/`, SPEC §3 "Proven vs the real 68000").

### `$f898` — the render entry

`$f898` compares the camera cell (`$4bb3a`/`$4bb3c`), yaw (`$ff9a`) and zoom
half-extent (`$fdec`) with copies it keeps at `$f890..$f896`. On any difference
it toggles bit 7 of `$ffa5` and calls `$fec6` to re-project. It then always
runs the grid walk, so **every island cell is refilled each time `$f898` runs**,
whether or not the camera moved. It runs once per present, which at normal speed (`$57fee` = 1) is once per sim tick. Before the walk it
loads the water-shimmer term `D5 = [$4bb3e] & 3` (`$f95e`) and picks one of
four yaw-quadrant walk handlers:

```
q = ((YAW + 8) >> 5) & 6
handler = [$f98e, $fa9a, $fbb4, $fccc][q >> 1]     // word table at $f986
```

Each handler has its own start corner, loop direction, iteration count (7) and
corner-to-vertex assignment, so the walk stays far to near at every yaw. One
handler's per-cell step (quadrant 3; all four are tabulated in SPEC §4):

```c
for (D7 = rows; ...; A0 += $fdf4, A1 += $fdf2)          // next grid row
  for (D6 = cols; ...; A0 += 4, A1 += 1, A2 += 2) {     // next cell
     C00=A0[0], C10=A0[4], C01=A0[64], C11=A0[68];      // 64 = one corner row
     if (!(A1[+8257] & 0x80)) {                         // split on C00-C11
         tri(C10,C11,C00, colour(A1[0]));               // colour plane B ($438ee)
         tri(C01,C00,C11, colour(A1[-8257]));           // colour plane A ($418ad)
     } else {                                           // split on C10-C01,
         ...                                            // order by packed(C01) vs packed(C10)
     }
     if (A2[0] != 0) draw_cell_entities($115e0);        // sprites over this cell
  }
```

`colour(b)` is the raw colour byte, plus `[$4bb3e] & 3` when `b < 0x0c`
(the water shimmer). The colour is a slope shade computed from the four corner
altitudes at world build (`$10058`, read in code; the band arithmetic is not checked cell by cell); the height only
enters through the projection `$fec6`. Each triangle of a cell has its own colour byte (`0` and `-8257`), which gives sloped
cells their two-tone split.

### `$ef62` → `$e3e6` → `$e420` — the pattern fill

`$ef62` clips each vertex, **cyclically rotates** the minimum-Y vertex to the
front (the other two keep their cyclic order), builds a span record at `$f1e2`
(colour byte at `+0`, top screen-Y at `+2`, two 16.16 edge X-slopes from
`$f000`, and a second-segment run/slope for the shorter edge), and branches to
`$e3e6`. `$e420` is the 16.16 DDA span walker. The span middle is the `$e4de`
Duff device (`move.l D0,(A2)+ / move.l D1,(A2)+`); the ends go through the
partial-word masks `$ec62`/`$eca2` and the cluster-offset table `$ece2` (`A6`).
The masks amount to "draw pixel x iff `ixL <= x <= ixR`".

**All surface colour comes from one pattern table** at `[$ff9e]` = `$2e000`
(`port/assets/dither.bin`). Each colour byte owns a 128-byte slot of sixteen
8-byte sub-patterns. Per scanline:

```
A5    = $2e000 + colourByte*128 + ((8 * y) mod 128)      ; y = absolute scanline
long0 = BE u32 @ A5      -> plane0 = hi16, plane1 = lo16  ; D0
long1 = BE u32 @ A5 + 4  -> plane2 = hi16, plane3 = lo16  ; D1
```

The setup (`$e3e6..$e3fa`) starts at `colourByte*128 + (topY & 15)*8`. The
`$e44a` roll adds 8 to the low byte of `2*A5` each scanline; the byte overflow
keeps `A5` inside the colour's slot, which is why the phase depends only on the
absolute scanline. The span on one scanline is a single 16-px pattern tiled in
screen-X alignment. The pattern-table pointer `[$ffa2]` is also flipped by 128 (`bchg #7,$ffa5` at `$f8e4`) every time `$f898`
re-projects, which moves the read point 64 bytes inside the slot: the phase is added inside the mod-128 wrap and is 0 or 64 (port/SPEC.md §4 "Dither phase";
terrain exact-index on three rotated captures 43.5 / 46.7 / 47.1% without it, 93.8 / 84.6 / 91.1% with it). No texture map is read anywhere in the terrain path.

The table is 128 slots of 128 bytes (`dither_atlas.png` decodes slots `0x00`-`0x40`;
`dither_infographic.html` is the interactive version). A slot is a 16 x 16 tile of
4-bit pixels: row `r` is the 8-byte sub-pattern, pixel column `x & 15`.

| colourByte | palette indices | what it is |
|-----------|-----------------|------------|
| `0x00`-`0x03` | 0, 14, 15 | open sea: four stipples of the same colours (the water shimmer) |
| `0x04`-`0x07`, `0x08`-`0x0b` | 0/14/15, 4/14/15 | water bytes 4-11: four identical tiles each, no shimmer. Not produced by any map checked (seven RAM images, five lands: every sub-12 byte in either plane is 0) |
| `0x0c`-`0x1b` | 1, 2, 3 | rock / low ground: two 8-step ramps, 1 to 2 (`0x0c`-`0x13`) then 2 to 3 (`0x14`-`0x1b`) |
| `0x1c` | 0, 1, 6 | only ever the `$ef62` forced colour: no terrain cell holds byte `0x1c` (the plane bytes seen skip 28) |
| `0x1d`-`0x2e` | season dependent | the **live** copy of the current season's 18 slots (`port/SPEC.md` §4 "Seasons") |
| `0x2f`-`0x40` | 6, 7, 9, 11, 12, 13 | high ground. Never replaced; these 18 slots are also the stored summer table (source `$2e000+$1780`), so terrain bytes above `0x2e` (seen up to `0x3f`) read the summer colours in every season |
| `0x41`-`0x52`, `0x53`-`0x64` | spring/autumn, winter | the other two stored season tables. No terrain byte seen reaches them |
| `0x65`-`0x7f` | mixed | not dither tiles (other data) |

**Ramp structure** (`py/dither_atlas.py`, checked on `pm78_settle`): the rock ramp
is a nested ordered dither. One fixed 16 x 16 threshold map gives each pixel a
rank 0-8 (16, 32 x 7, 16 pixels per rank); slot `0x0c + k` switches the rank <= k
pixels to the next colour, each slot containing the previous one, and the second
half (2 to 3) uses the identical map. The grass ramps are not nested: five fixed
scatters of 32, 80, 128, 192 and 224 pixels, the same five masks for each colour
pair (13 over 1, 12 over 13, 11 over 12; identical in all three), with overlaps
between neighbours of 0 of 32, 48 of 80, 64 of 128 and 160 of 192.

**The `0x1c` override** (`$f072` / `$f154`): `$ef62` forces the colour byte to
`0x1c` when the triangle's winding puts the middle vertex on the left. At the
mission-1 start pose (cam 36,47, yaw 15) it applies to 52 of 128 triangles,
which draw 3298 px; 6 px of those remain in the finished frame, because
nearer terrain paints over the rest (`port/walkthrough/probe.fsx rasters`). At
that pose it therefore marks mostly back-facing triangles, and the visible
effect is limited to a few dark pixels along the island silhouette.

### Seasons

`$57fd0` holds the season as 0, 2, 4 or 6 (winter, spring, summer, autumn;
`port/SPEC.md` §4 "Seasons"), and two things follow it. **The grass:** slots
`0x1d`-`0x2e` of the pattern table are a working copy of one of three stored 18-slot
sources (winter `$2e000 + $2980` = slots `0x53`-`0x64`, spring and autumn `$2080` =
`0x41`-`0x52`, summer `$1780` = `0x2f`-`0x40`). The copy is made in one go at world
build (`$1ab60`) and after that `$1abaa` dissolves it towards the current season's
source, 16 pixels per tick, in the pixel order of the 13-bit LCG `$57ff6`. A fade takes
512 ticks (about 118M emulator steps in mission 1, 86M on a Play Random Land; the tick count is fixed, the cost per tick is not) and its end rotates
`$57fd0 = ($57fd0 + 2) & 6` (`strategy.md` "What `$1abaa` actually is"). **Proven**
(SPEC §4): the port's `Season.fading` equals the whole 16 KB table byte for byte on seven
captures, with steps = 16 × `$57fec`; `scratchpad/pm136/season/tilediff.py` shows the
dissolve live (half summer and half autumn art at count 255, 98% the new art at 496).
**The trees:** `$116c6` adds `word[$11746 + $57fd0]` = {0, 3, 6, 9} to the tree and
building frame, so the frames change the moment `$57fd0` advances while the grass takes
the whole fade to catch up. The sprite sheets are identical in every season.

### Water shimmer

The water shimmer is a fill effect: the palette never changes. `$4bb3e` is a
longword tick counter, written only at `$13034` in the `$13000` sim tick and
incremented once per tick. Water cells (`b < 0x0c`) add `[$4bb3e] & 3` to their
colour byte, so each tick moves them to the next of four stipple slots and the
pattern repeats every four ticks.

The compose buffer holds the frame finished one tick earlier, so a RAM image taken at
the `$f898` frame driver shows terrain drawn with `([$4bb3e] - 1) & 3`: four consecutive
captures of one coast view (`pm121/cap/k5_22_0..3`) match the rebuilt frame at 100.0, 100.0,
99.9 and 99.9 % with that offset, and six water scenes score 90-100 % with it against 40-70 %
without; `tools/pm_render_ref.py`'s `load_ram` applies the offset (`tick`; the raw counter is `ram_tick`). Dither phase on those captures is 64.

The shimmer appears only where water lies inside the drawn window. The open
sea outside the window is part of the static `$78000` master and does not
change.

| capture (`pm71_run1.snap`, 249 frames, `ATARI_FRAME_DIR`) | result |
|---|---|
| start camera (window cells x 36–43, y 47–54, heights `0x1d`–`0x3b`, no water) | 77 bytes change over 240 frames, all unit sprites and the marker blink; palette identical |
| camera cell word `$4bb3a` = `$2c` (window x 40–47, over the east coast) | every tick (15 frames) 2147–2371 px change, ~96 % water (idx 14/15) inside the walk-drawn sea strip; frame N equals frame N+60; palette identical |

### `$165b2` — the selected-group marker

`$165b2` (called at `$130bc` in the tick) draws the pulsing marker over the
**selected group's lead** (`$51538[$57fd2]` → lead object → world x/y). Bit 0 of
`$4bb41` toggles it.

## The land build: planes, roads, town ground, the script

`$13b9a` builds a land in this order (live, from `pm67_ok_pre` after the briefing OK; the same sequence is in `strategy.md` "Mission / world setup"): `$10768` clears `$3f364..$57ff8`; `$10d1e` (a random land's parameters) or `$ffa6` (a stored land's altitude walk, then the `$10410` smoothing); `$2266`; `$ac20` (the land script below);
`$1073c` (every `$4b9f2` site: `$2eac` places the town's buildings, `$10638` levels the ground); `$10058` (the colour bake); `$4672` (forests); `$2984` (the population); `$238c`; `$2906`; `$107d6` (the minimap). The planes are all 64 × 128, cell n = y × 64 + x: altitude `$3f86c`,
colour A `$418ad`, colour B `$438ee`, flags `$4592f`, bucket heads `$47970` (a word per cell). Flag bits: 7 the diagonal selector, 6 an edge mark (only the dead `$10b62` uses it), 5 skip the split, 4 a near-ambiguous diagonal, 3 and 2 colour B and colour A fixed, 1 altitude pinned.

### `$10058` — the colour planes are baked from the altitudes

For each cell the four corner altitudes a (this), b (+1), c (+64), d (+65) (the reads run past the row end and into the next plane) form a 4-bit water pattern, `8·(a = 0) + 4·(b = 0) + 2·(c = 0) + (d = 0)`, that indexes a 16-entry jump table (`fejt` `$10096`):

```
0 (no water):       findspli; flag7 ? land_nw + land_se : land_ne + land_sw
1: set7 land_nw, coast_se     2: clr7 land_ne, coast_sw     4: clr7 land_sw, coast_ne     8: set7 land_se, coast_nw
3, 5, 10, 12:       findspli; flag7 ? coast_nw + coast_se : coast_sw + coast_ne
6: set7 coast_nw, coast_se    9: clr7 coast_ne, coast_sw
7: set7 coast_nw, colour B = 0     11: clr7 coast_ne, colour A = 0     13: clr7 coast_sw, colour B = 0     14: set7 coast_se, colour A = 0
15: both colours 0 (open sea)
findspli (`$1021e`): skipped when colour A or B is already $1d or flag 5; d1 = −|a−d|, d2 = −|b−c| (bytes); set flag 7 unless d2 < d1; set flag 4 when ||a−d| − |b−c|| <= 4
nw: A = (b−a + c−a)/4 + 9      ne: B = (d−a)/2 + 10      sw: A = (d−a)/2 + 9      se: B = (d−c + d−b)/4 + 10      (shade clamped 0..15)
land = shade + $1f      coast = shade + $c, and + $26 when the highest of its three corners is <= 6      each writes only if its fixed bit (2 for A, 3 for B) is clear
```

Colour `$1d` is the first of the 18 live season slots (table above): it is the road and town-ground colour, `$1e` the farm field. Proven: `py/maps/gate_maps.py`, **125219/125219** tracked bytes identical over 16 `callcap $10058` calls (8 random lands and 8 stored lands, entered at their natural calls).
The smoothing pass `$10410` (neighbour average, skipping cells with flag bit 1): **45779/45779** over 16 calls.

### `$10910` — roads are terrain: a causeway painted into the planes

`_do_road` is a line walk, not a Bresenham or a spline, and it draws nothing on a screen. Inputs: D0/D1 the start and end cell index, D4/D5 their altitudes.

```
steps = max(|dx|, |dy|)                                        // Chebyshev
dalt  = ((alt_end − alt_start) << 16) / steps  as a long       // 0 (a flat road) when steps == 0 or the quotient overflows 16 bits
pos   = alt_start << 16
loop: paint both triangles of the cell colour $1d; flags |= $0e, and |= 2 on the cells +1, +64, +65; write (pos >> 16) & $ff to the cell's four corner altitudes
      pos += dalt
      if x == x2: if y == y2 return, else step y;  else step x, then step y if y != y2
      a diagonal step also paints the corner cell $1d with flags $28/$24/$a8/$a4, so the road is 4-connected
```

A road crosses open sea as a causeway (`terrain_roads.png`: land `k5_s4`, the roads link the islands; the `$1d` cells are white, 383 of them). **Proven: 2561/2561** over 12 calls. `$10638` (`_town_gr`) levels a settlement site the same way: it paints `$1d` on the occupied cells and on the edge triangles by the 4-neighbour occupancy pattern, **260/260** over 11 calls.
`_pospos` `$10c18`, `_mapline` `$10c7e`, `_how_far` `$10cae` and `_distanc` `$10ce4` are a DDA line-walk library over the **colour** planes (not the altitude plane). `$10c18` takes two packed cell indices (`y<<6|x`) in D0/D1 and returns a 16.16 DDA (D0/D2 start row/column, D1/D3 per-step row/column, D4 = max(|dx|,|dy|) steps); the other three call it and walk the line (cell index `y*64+x`, planes `-8257(A1)` = A and `0(A1)` = B). `$10c7e` adds `$80` to both colour bytes of every cell after the start (flips bit 7, self-inverse); `$10cae` returns in D0.w the first cell where the signed byte D6 is >= both colour bytes (else -1); `$10ce4` returns -1 at the first cell whose two colour bytes are both 0, else the line length. `callcap` from `m1_ready` on a 10-cell row (D0 = `$28a`, D1 = `$294`): `$10c7e` changed exactly 20 map bytes `00->80` (10 per colour plane), `$10cae` (D6 = `$20`) returned cell `$28b`, `$10ce4` returned -1 (`py/capture_misc/line_walkers.sh`). `_do_vriv` `$10458` (a river carver) walks all 64 rows from column 32, shifting one column per row by `(rand & $fff) mod 3 - 1` (RNG `$12c9a`, biased by the previous step), and per row writes a random 8-cell-wide cross-section (six cells set, mirrored: outer bank `$1e+(r&4)`, inner bank `$19+(r&8)`, bed `$01+(r&4)`, the two centre cells left alone), colour bytes `$0c..$15` on the bed-side cells (which of `$0c/$0d`, `$0e/$0f`, `$10/$11`, `$12..$15` depends on the sign of the step; code read), and flag bits 1 (altitude pinned), 2 and 3 (colour A/B fixed). `callcap` from `m1_ready` (15,298 steps) changed 382 altitude, 128 colour-A, 128 colour-B and 504 flag bytes, in all 64 rows (`py/capture_misc/vriv_planes.py`). `_fix_map` `$10a46`/`_edge_ro` `$10b62` a BITMAP.DAT decoder only the fixed-map branch (`$58148 < $100`, no land) would reach: no direct caller or literal pointer
(`find_ram_callers.py`, `find_literal_ptr.py`; `find_jump_table_hit.py` finds no table entry for `$10458` and one for `$10c7e` that is ASCII text at `$aaa0`, a false positive), 0 hits in 20M steps on two snapshots (`m1_ready`, `pm142/rand1`) for `$10458`, `$10c18`, `$10c7e`, `$10cae` and `$10ce4`. The shipped build therefore never runs them; the DDA routines' purpose is not established (the callers' names suggest distance and line-of-sight tests).

### `$ac20` — the land script

`_dec_oth` decodes the 4-byte records `{x, y, d0, type}` at `$58152` (type 0 ends). Type < `$10`: a site; when `d0 != 0` the words `{d0, x, y, kind}` are queued at `$4b9f2` (the pointer advances 8 either way), then `_flat_ci` `$ae58` flattens a disc of radius = type cells to the centre altitude
(minimum 1). `$10`: a side's group start cell, written to `word[$51538 + d0 × $13c + 100]`, its 2 × 2 block raised to at least 5. `$11`: a road from this cell to the next record's cell (that record is consumed; one that is itself `$11` is re-read as the next road's start). `$12`: a hand-made shape `d0` stamped by `_fix_it` `$105d0`
(altitude, colour A and colour B planes); when it follows an `$11` it is only the road's end. Above `$12`: ignored. Over the 195 stored lands (`py/maps/script_census.py`): 456 group starts, 1695 sites, 507 roads and 15 stamps (lands 12, 19, 20, 21, 38, 40, 53, 67, 72, 150, 162, 173, 180).
**Proven: 14539/14539** tracked bytes over 16 `callcap $ac20` calls.

## Sprites and draw order

### Sprites are drawn inline in the terrain walk — `$115e0`

The walk calls `$115e0` for every cell whose `$47970` bucket is non-empty,
straight after that cell's two triangles. `$115e0` follows the cell's bucket
chain and, per record, dispatches twice on the category byte (byte 6):

```c
void draw_cell_entities(int cell) {
    for (obj *e = &obj[$47970[cell]]; e; e = &obj[e->bucket_next]) {
        PREPARE[e->category]();     // $1162e: position + frame index into D2
        BLIT   [e->category]();     // $1165c: blitter (word 0 = none)
    }
}
```

The head word of a cell's chain and every link are **signed** 16-bit offsets from `$51b66` (`adda.w D4,A3`), so scenery and
animal records also live below `$51b66`, and the category byte 6 takes even values 0 to 30 (`word[$1162e + byte6]`). The
26-record marching group is byte 6 == 14, drawn by `$115e0` to `$11bf4` to `$11f78` to `$11f82` (frame `record[5] + 0x13e`).

Because the grid is walked **far cell to near cell** and each cell's sprites
follow its terrain, the painter's algorithm falls out of the walk order: there
is no depth sort and no Z buffer. A near hill is drawn over a far unit, and a
unit in a near cell is drawn over the near hill.

### Sprite sheets and blitters

| sheet | frame | blitter | contents |
|-------|-------|---------|----------|
| `$33000` | 8 × 11, 4 planes + AND mask, 55 B | `$11f82` (men via `$11f78`) | men, animals, markers, flags, icons |
| `$37c7c` | 32 × 24 word planes, 480 B | `$12244` | trees, buildings |
| `$312a0` | 16 × 16 word planes, 160 B | `$1225c` / `$119d4` | small structures, siege engines, explosions |

The `$11f82` mini-sprite blitter:

```
A1 = $33000 + frame * 0x37        ; 11 rows x [AND-mask, plane0..plane3]
A0 = dest group in the back buffer; from the entity's projected screen (x,y)
per row:
    D0   = 8 - (x & 15)           ; sub-word rotate (separate paths for ==8 / >8)
    mask = rol.w D0, ($ff00 | mask_byte)
    for plane in 0..3:  word[plane] = (word[plane] & mask) | rol.w D0, plane_byte
    A0 += 0x98
```

A pixel is opaque where its mask bit is 0; the plane bytes carry the sprite's
own 16-colour data. Sprites are positioned by bilinear interpolation over their
cell's four projected corners using the entity's sub-cell fraction, so they sit
on slopes. Frame selection is per category in the `$1162e` handlers; for men
it is `(faction−1)*16 + (((heading + YAW + 0x10) & 0xff) >> 5)*2`, so facing is
relative to the camera. Per-category formulas are in SPEC §6.

### The preparers and drawers by category (code read unless noted)

`sjt` `$1162e` and `djt` `$1165c` are 23-word tables indexed by byte 6: 0 `a_person`, 2 `a_house`, 4 `a_tree`, 6 and `$18` `a_object` (`$117b0`: frame `$100 + byte 7`; byte6 `$18` is a fisherman's catch marker with byte 7 `$10`, so it draws frame `$110`, a rowboat on the pond, `catch_marker_boats.png`; the developer table names the pair `a_boat`/`a_object`), 8 `a_animal` (`$11a86`), `$a` `a_equipm`, `$c` `a_special` (`$11bbc`), `$e` `a_sitting` (`$11bf4`, 2316 hits per 30M steps on `k5_s4`), `$10` `a_workshop`, `$12` `a_ball` (`$11c36`),
`$14` `a_pigeon` (`$11b3c`), `$16` `a_flight` (`$11b2a`), `$1a` `a_inboat`, `$1c` `a_shag` (`$11b0c`), `$1e` `a_mine` (`$1198a`, with `a_part_b` `$119b2` for a building going up: D6 = `8(A3)` rows of progress, the frame offset and shortened by D6), `$20` no draw, `$22` `a_bigcow` (`$11ab8`), `$28` `a_arrow` (`$11c64`).
`$120ea` `scaled` (22 words by category, 1 for 2, 4, `$a`, `$10`, `$1c`: those use the large sprite's rectangle in `check_sh`, live dump on `m1_s0`) and `$12116` `dscale` (by zoom) are data. `a_pigeon` and `a_flight` share the tail `do_for_a` `$11b44`: the interpolated position (`$11f12`), a colour-5 dot at `(x, y − 14(A3))` (`$e6ee`)
when `14(A3)` is non-zero, the shadow icon `$148` (`$11f82`), y lowered by `15(A3)` (plus `$30` when it is negative) and the frame `$127 + (tick $57fec & 7)`, the flapping bird; category `$16` is drawn the same way, which fits the developers' name `_birds` for the `$4c5f4` records. Not natural: 0 hits in 30M steps on `k5_s4` and `m1_atk`
and 7 `k5` series frames; with a flag record poked to byte6 `$16`, `callcap $11b2a` returned D0 = 204, D1 = 46, D2 = `$12d`, raised the sound event word `$12a79` and changed 6 screen bytes. `a_stock` `$1184e` draws a goods pile with nine icons (`draw_foo/pik/swo/bow/plo/boa/pot/cat/can` `$11898..$1191e`: food `$116`, pike `$143`, sword `$144`,
bow `$145`, plough `$109`, boat `$110`, pot `$146`; the catapult `$1b` and cannon `$23` as 16 × 16 sprites through `check_sh`), `a_workshop` `$1192e` the workshop frame 7 plus the icons of the stocked weapons of the eight goods slots `24($4e514 + 14(A3), k)`. `$1182a` (`do_for_a`, the first) is the cell-centre position
(x = (c0 + c1 + c2 + c3)/4 + `$38`, y = ... − 8). The main loop's tail `$13864` (`after_ke`) redraws the panels and fades (`$187a`, `$1a276`) and re-enters `_again` `$12fd8`: once per tick (193 hits per 30M steps on `k5_s4`).

### The 16 and 32 pixel blitters and the sprite pick

`$12244` (`_draw_sp`) takes the sheet from the zoom `$57ffc`: 3 or less the 32 × 32 sheet `$3af1c` (D0 − 8, D1 − 16), 4 and 5 the 32 × 24 sheet `$37c7c` (D0 − 4, D1 − 8), 6 and above the 16 × 16 sheet `$312a0`; `$1225c`, `$119ca`, `$11a02`, `$11a44` and the HUD (`$178ac`, the eyes `$1699e`)
reach the same two clip fronts. These are a family of masked planar blitters, not a scroller:

`$122b6` (`_s16_dra`, 16 wide) and `$12326` (`_s32_dra`, 32 wide) take D0.w the x of the left pixel (negative or past 319 allowed), D1.w the y of the top row, D2.w the rows, A0 the screen page (the long at `$2df7c`) and A1 the frame. A 16-pixel row is `[mask, p0, p1, p2, p3]` words (10 bytes), a 32-pixel row two such blocks, left first;
a set mask bit keeps the screen pixel, `new = (old & mask) | plane`; the screen is 4 interleaved planes, 160 bytes a row. Rows outside 0..199 are dropped, then x picks a back end:

| back end | used for | cost per row |
|---|---|---|
| `_all_16` `$123ac` | 16 px wholly inside: two destination groups per row (`ror.l` by x & 15) | 46 steps |
| `_left_16` `$1241a` | x −15..−1: group 0 only | 26 |
| `_right_1` `$12460` | x >> 4 = 19: left group only, the spill dropped (also block 0 of a 32 px sprite at group 19) | 29 / 30 |
| `_all_32` `$124a8` | 32 px inside: block 0 to groups g, g+1 and block 1 to g+1, g+2 | 91 |
| `_left_32` `$12576` | x −15..−1: block 0 shifted left into group 0, block 1 right into groups 0 and 1 | 73 |
| `_right_3` `$12628` | group 18: block 0 to g, g+1, block 1 to g+1 only | 75 |

The 32-wide front also sends x −31..−17 to `_left_16` on block 1 and group 19 to `_right_1` on block 0; x ≤ −32 or group ≥ 20 draws nothing, and for 16 px x ≤ −16 or ≥ 320 draws nothing. **Proven: `py/blit/blit_gate.py`, 450/450** `callcap` calls (150 per sheet, random frames, x in −40..330 plus the edge set, y in −40..210, against a model of the
pixel rule; every variant exercised, 56 to 58 fully clipped calls per sheet changed nothing); `blit_route.py` confirms from the steps per drawn row that the label named is the routine that ran; `blit_variants.png` shows one call of each (before and after).

`check_sh` `$12138` is the **sprite pick** (not a window cull, as an older `.sym` comment had it: `$2df92/$2df94` are the live cursor and `$2df8e/$2df90` the pending click, not an extent): it runs with every sprite draw, after the pointer test, so it decides which drawn sprite a click belongs to (9 callers: `$11912`, `$11922`, `$119ca`, `$11a02`, `$11a44`, `$11f78`, `$12258`, `$12278`, `$1229a`).

```
check_sh(D0 = x, D1 = y of the sprite, A3 = record, A2 = its cell's bucket slot, D2 = frame):
  if $57fd4 == 0 and not ($2df96 != 0 and $57fea != 0): return           // no armed order, no examine click
  size = 8;  if scaled[byte6] != 0 { size = dscale[zoom] }               // $120ea words by category (1 for 2, 4, $a, $10, $1c), $12116 words by zoom: 0, $20, $20, $20, $18, $18, $10 ...
  (px, py) = $2df96 ? ($2df8e, $2df90) : ($2df92, $2df94)                // the click position when a click is pending, else the live pointer
  if not (0 <= px − x < size and 0 <= py − y < size): return
  if $57fea: if $2df96 { $115de = 0; $95f6() }; return                   // examine mode: open the info panel ("The game's own text", strategy.md)
  if $58000 != 0: return                                                  // nothing writes it in the whole image (code read)
  X = cell & 63;  Y = (cell >> 6) + 6;  $13892(X, Y)                      // the line from the selected captain's lead to this cell
  if D2 != 0 and $2df96: $115de = 0; slot = [$58034]; slot[1] = $57fd4; slot[2] = X; slot[3] = Y − 6; $1898e()    // post the armed order at the sprite's cell and disarm
```

Live, six `callcap $12138` cases from one natural entry (a tree, D0 = 215, D1 = 67; pokes of `$2df92/$2df8e/$2df96/$57fd4/$57fea`; rerun from `rand1` as `py/capture_misc/check12138.sh`: 6/6, 0, 33, 84, 0, 368 and 0 bytes): idle 0 bytes; an armed order with the pointer inside and no click draws only the line; armed plus click posts `{02, 43, 48}` into the command slot (the cell predicted from A2 exactly) and disarms;
the pointer outside 0 bytes; `$57fea = 1` plus a click opens the tree panel; `$57fea = 1` without a click 0 bytes. The same through the real UI (icon `$2c` at (75,191), then a tree at (225,78): `info_click.png`). `$115de` (`_used_bu`) is set to 1 at the start of each record of `$115e0`'s chain and `$11624` clears `$2df96` only if it is still 0, so with several sprites
under the pointer only the last record's flag survives (inferred).

The draw preparers also post the sound events: see `strategy.md` `$127e6`.

### The pixel plotter — `$e6ee`

`$e6ee` sets one pixel (x `D0`, y `D1`, colour `D2`): a per-x table at `$e762`
gives the byte in the row and a bit-mask index, `y * 160` is added, and two
`movep.l` instructions read and write that bit in all four planes. It does not
clip. It draws every minimap pixel (`$107d6`, "The minimap and the conquest map"), including the blinking selected group
(`$165b2` → `$16738`, one dot per member at its raw cell coordinate, y + 6 = the
minimap's rows), the one-pixel arrows (byte6 40) and the byte6 20/22 dot on the
iso view. Details: port SPEC §6 "The pixel plotter".

### Trees / buildings / mountains

Mountains are terrain: a run of high cells drawn by the same triangle fill.
Trees and buildings are bucket sprites drawn over the cell they occupy, which
is why they appear and disappear at cell granularity when the camera rotates.
A tree or building (byte 6 == 4, handler `$1168c`, blitted inline by `$12244`) takes the frame
`(record[7] & 0x7f) + word[$11746 + word[$57fd0]]`, with the table `$11746 = {0, 3, 6, 9}`, `word[$57fd0] = ($58146 & 3) * 2`
(a per-land tile-set selector; mission 1 reads 4, so `+6`) and the special cases `record[7] == 0x0d` and `(record[7] & 0x7f) == 0x0e`
(no offset). Its position is the `$11f1a` lerp over the cell's four raw `$3f364` corners with a jitter derived from the
record, bucket-slot and corner addresses (`fx = (((A2 + A3) & 0xffff) << 3) & 0xff`), then `$12272` subtracts 4 and 8;
live-checked against D2 at `$12288` and D0/D1, with the 32 x 24 decode byte-exact against a live frame (`port/SPEC.md` §6).

## The minimap and the conquest map

**The minimap** `$107d6` (`_draw_ma`, with `$1078e` `draw_con`; called from `$13c5a`, `$187f0`, `$b3ca` and the strip click `$131ee`) is baked once into the master buffer (`[$e0d4]` = `$78000`): cell (x, y) with x < 63 is the pixel (x, y + 6), plotted by `$e6ee`. The mode word `$58098` (`_show_ma`; default 2) is set by a click in the strip above the map
(x / 16):

- mode 0: contour colours, `$107c6[(altitude + 7) >> 3]`;
- mode 2: the terrain colour, `$108ce[colour A]` (a 66-byte table);
- mode 1: as 2, but the first record of the cell's bucket chain with byte6 4 / 2 / `$10` colours it 8 (tree) / 9 (settlement building) / 10 (base);
- mode 3: chain records of byte6 2 or `$10` use their lord: d = `word[$4e514 + lord + 6] − word[... + 8]` (food less manpower), colour 0 when d ≤ 0, else `min((d >> 5) + 1, 5)`.

Chain offsets are sign-extended words: a tree record sits below `$51b66` (bucket `$b800` is `$4d366`); a transcription that missed it was off by 169 pixels. **Proven: `py/maps/gate_minimap.py`, 512000/512000 bytes and 1024000/1024000 pixels** over 4 modes on 4 snapshots (`m1_s0`, `k5_s4`, `k0`, `pm78_settle`); `minimap_modes.png` shows the four modes on `k5_s4`.

**The conquest map** (`_select_` `$1120e`, entered from `$13cfa` and `$13ec0`) is a 320 × 608, 4-plane bitmap (resource 10, `$3f364..$57164`) holding a **13 × 15 land grid of 24 × 40 cells** (`worldmap_full.png`). `_draw_pa` `$11422` copies 32000 bytes from `$3f364 + scroll × 160` to the screen (the scroll `$11420`, 0..`$198`, set by dragging;
a straight copy: 96000/96000 bytes at scrolls 0, 137 and 408). `_draw_da` `$11458`, once at the picker's entry, ORs the 16 × 16 dagger glyph (`dagger` `$1153e`: 16 rows of a keep-mask word and four plane words, 160 bytes) onto every land whose byte in `$3f2a0` is non-zero: the first at byte `$3fd65` (row 16, x = 8), advancing 15 or 9 bytes by the address parity of
the start (an odd start splits over two 16-pixel groups) and 6400 per land row; 89310/89310 changed bytes over 12 poked tables. The pick box is 16 × 32 at (24c + 8, 40r + 8), drawn by `$e5aa` as a 17 × 33 outline at (24c + 7, 40r + 7 − scroll), colour 10 for a conquered land and 8 for land 0 or a free land with a conquered 4-neighbour
(`gate_pick.py`: 18 of 18 probes agree: 4 boxes, 14 negatives). A click on any boxed land, even a conquered one, runs `$113a8` by the code (not tested).

## Backdrop pieces, palettes and fades

- **The balance** `scale_da` `$16bf8` (5 frames of 640 bytes, 20 rows of 32 bytes, 64 pixels wide) is the force-ratio picture: `_draw_sc` `$16bb8` copies frame `4 − D0`, D0 = the ratio word `$57fce` (0..4), into the backdrop at `$e0d4 + $5320` (pixel row 133, x 0..63); callers `$d2be` (when the ratio changes) and `$188e0`. A pair of scales with a shield on each
  side tilting with the ratio (`scale_da.png`; which pan is the player's is inferred). 2 natural hits live in `m1_atk`.
- **The captains' eyes** `eyes` `$169d8` (data, not code: 480 bytes up to `_draw_sc` `$16bb8`, reached only by the PC-relative `lea 22(PC,D2.w)` at `$169c0` inside `_draw_ey`; 6 captains × 4 frames × 20 bytes) are one-row, 32-pixel strips blitted by `_draw_ey` `$1699e` (D0 = 2 × slot, D1 = frame `word[$2df92] & 3` (the cursor X: poking `$2df92` to `$a0..$a3` at `$3e9e` gives D1 = 0, 1, 2, 3, `py/capture_misc/eyes_frame_poke.sh`), sole caller `$3ea8` in `$3e06` for a slot whose `28(A3)` is non-zero) at the pairs of `eye_coor` `$16986`, (85,30) (132,29) (182,20) (224,29) (260,30) (295,40), into the backdrop through
  `$12326` with D2 = 1. The routine opens with its own `movem.l #$ffe0,-(A7)` (`48e7 ffe0` at `$1699e`) and ends in the matching pop, so it is `callcap`able (97 hits per 30M steps on `k5_s4`; an earlier reading that it had no push came from a listing that started two bytes early). `py/fsm15/eyes_check.py`: all 6 slots x 4 frames return in 141 steps (slots 0-4) or 128 (slot 5, whose strip is clipped at the right edge, inferred); 21 of the 24 calls write backdrop bytes, every one of them in the single row y of the slot's pair and only in the 16-pixel groups covering x..x+31 (the 3 that write nothing are frame 0 of slots 0-2, probably strips equal to the backdrop: inferred).
- **Palettes.** `_work_pa` `$1a2d8` and `_game_pa` `$1a358` (the same earth-tone palette), `_zero_pa` `$1a318` (all black), `_con_pal` `$1a398` (red-brown, "glorious victory", resource `$f`) and `_lost_pa` `$1a3d8` (orange and brown, defeat, resource `$e`) are 64 bytes each: sixteen `$0RGB` words with a 4-bit linear nibble per
  channel, plus padding (`fade_palettes.png`, rows in that order). `_show_a_` `$1a82a` rotates each nibble into the STe hardware order (`(x << 3 & $888) | (x >> 1 & $777)`) and writes `$ff8240..`.
- **The fade** `_do_one_` `$1a418` moves each differing nibble of the 16 colours by D0 (±1) toward the target at A1, shows it (`$1a82a`) and waits 20000 iterations; `_fade_sc` `$1a2bc` makes 16 calls; fade-in (`$1a276`: flag `$1a2ba` cleared, D0 = +1, target `$1a358`) is called from `$cf24`, `$11398`, `$13872`, `$13d94`, `$13e36` and fade-out
  (D0 = −1, target zero, flag −1) from `$6f0a`, `$113c6`, `$13d60`, `$13e62` and the conquest screens. `callcap $1a418` with work colours 0..3 zeroed and D0 = +1: colours 1, 2 and 3 each gained `$0111`, colour 0 stayed (3 of 3 nibbles).
- **Text** `do_text` `$1a238` draws a string at A2 (D0 = x, D1 = y): the letters A..Z only, 55-byte glyph records at `$19ca2`, advance 9, through `$11f90` (code read). `_copymem` `$1a7a6` copies 32000 bytes; `_draw_ne*` `$1a808`/`$1a81e` store `{offset.w, count.w, longs...}` lists at `A4 + offset` until the offset is negative (the end screens' delta frames,
  `strategy.md` "How a land ends").

## The frame pipeline

Two compose buffers, `$2df7c` (on screen) and `$2df78` (back), are swapped via
the shifter base register. The **terrain master** at `$78000` holds the HUD,
the stone border, the pre-rendered open sea and a hole where the island goes.
`$13b9a` builds it once per mission.

```
  once per mission ($13b9a):  build the $78000 master -> $12ce0 copy into both buffers

  per simulation tick ($13000), present rate gated by $57ff0/$57fee (= 1 normally):
    $1870   spin until the VBL flag $2df8c is set                 ; frame sync
    $12ce0  copy terrain master ($78000) -> back buffer ($2df78)  ; 500 rows, movem
    $178ae  HUD group bars (food, men, the lead's health)
    $f898   re-project if camera/yaw/zoom changed; refill every island cell, sprites inline
  --- every tick (the full order is in strategy.md "Where it runs") ---
    $1abaa  seasons and weather (dissolves the live tileset 16 px per call)
    $17878  compass
    $165b2  selected-group marker
    $14b62  entity FSM      (ai.md), relinks $47970 buckets via $163ea
    $6a3a   order executor
    $7a56   dialog / info-panel renderer (cell grids of the `$7a36` slots) -> back buffer
    ... at the VBL ISR: $187a swaps $2df7c <-> $2df78, writes ($2df7c >> 8) to $FFFF8200
```

On `pm71_run1.snap` the master copy `$12ce0`, the island refill `$f898` and the
buffer swap `$187a` each run exactly once per sim tick (13 hits each in ~2.78M
steps, so a tick is ~214k steps, about 18 VBLs; `strategy.md` "Measured cadence"
counts 13 ticks in 3M steps, 19 VBLs each), so every presented frame holds a complete
island.

The zoom LOD (`$fe04`, 7 levels → 13 constants `$fdea..$fe02`) changes the grid
extent, strides and the `$ff9c` scale; it never switches tile art. Every zoom
draws the same triangle fill with more or fewer, larger or smaller cells.

## Isometric renderer, measured

Profiled from `pm67_p4c.snap` / `pm68_isoview.snap` with `ATARI_TRACE_EVENTS`
and `trace_cfg.py --blocks`, over the world build and 20–30 frames of the
settled view.

| routine | role | what it does | measured |
|---------|------|--------------|----------|
| `$14b62` | entity iteration + projection driver | walks the 50-byte object records `$51b66+$32 .. $57f66` (~490 slots), `tst.b 5(A1)` active-gate, per-type `jmp` table `$14bba` keyed on `31(A1)`; calls `$163ea` per moved entity | ~27 active entities scanned/frame (×511 over 19 VBLs) |
| `$163ea` | entity world → grid cell | `cell = ((worldY & $ff00) >> 2) + (worldX & $ff)`: shift + add, no MUL/DIV; `beq $1648c` skips the relink when the cell is unchanged | per moved entity |
| `$1648e` | terrain colour sampler | `lea $438ee,A4`, index by `worldX>>2` / `worldX>>6`; returns the colour byte of the triangle the point lies in, `0(A4)` or `-8257(A4)`, chosen by flag bit 7 (`+8257(A4)`) and the position inside the cell | per terrain cell touched |
| `$164bc` | entity step toward a target | `sub.w D6,D0 / sub.w D7,D1 / ext.l / divu D2,D0 / divu D0,D1`: 4-quadrant fold, then `divu speed` on the major axis; `16(A1)` = speed, can be 0 | per moving entity |
| `$16738` | selected-group marker blit | visibility test `btst #7,7(A6)` / `btst #6,7(A6)`; feeds `$e6ee` | per marked record |
| `$e4de`+ | unrolled span filler | `$e4da: jmp 82(PC,D6.w)` into a ~120-deep `move.l D0/D1,(A2)+` chain, span length in D6; caller loop `$e45a`/`$e45e`/`$e462`. The fill-rate hot path | ~40 % of all instructions in the settled view |
| `$f000`–`$f13c` | fixed-point slope divide | `divu` + `lsl.l #8` normalise, dx/dy and dy/dx, feeds the span walk | ~8800 instr-equiv / 30 settled frames |
| `$12ce0` | terrain master → back buffer | `move.w #$1f3,D0` then `movem.l (A0)+,#$0cfc` / `movem.l #$0cfc,(A1)` ×2, `adda.w D1,A1`, `dbf`: 500 rows, 24 B/`movem` | 10 hits / 30 frames, same settled or moving |
| `$fe04` | zoom → geometry | from D1 = zoom index (1–7) derives 13 tile-size / stride / cell-count words at `$fdea`–`$fe02` | on every zoom change (via `$13f60`) |
| `$fe8e`–`$ff94` | height re-scan for the projection | per-cell scan, bounds `$fdec`/`$fdee`; runs when `$ff9a` changes | ~4600 cell iterations per angle step |
| `$12d08` | 16×16 → 32 multiply helper | 3-`mulu` partial-product long multiply, via `$12c9a` | fixed-point scale during the build |
| `$1af32` | timer ISR (`rte` at `$1af44`) | not a renderer; hot only because it interrupts everything | ~12–15 % of instructions, settled == moving |

Findings (`pm68_isoview.snap`, zoom index 4, instruction-weighted, 30 frames
settled vs 30 with the rotate key held):

1. **Fill-rate bound.** The `$e4de` span filler is ~40 % of all executed
   instructions, including in the settled view, because `$f898` refills the
   island every tick. `$163ea` and `$164bc` together are under 1 %.
2. **A rotation step costs almost nothing in aggregate (+0.6 %).** One angle
   change adds ~4600 `$fe8e` iterations; the `$1870` VBL spin absorbs it
   (settled 382k instr-equiv, rotating 384k).
3. **The settled view is not idle.** It runs `$163ea` (~14/frame), `$16738`
   (~4/frame) and `$12ce0` every ~3 frames.

Zoom is a discrete 7-level select (index in `$57ffc`, `$13f82` table `[_,84,42,28,21,17,14,12]`,
index → `$fe04` → the 13 constants at `$fdea`–`$fe02`; `port/SPEC.md` §5). The zoomed-out slowdown
players report is the `$f000` slope-divide cost (9× more edges for many small
tiles) once the map is dense enough to outweigh the entity, sprite and fill
saving; see "Zoom comparison".

## The renderer as modern pseudocode

```python
def build_projection(camera):                 # $fec6 -- only on camera/yaw/zoom change
    cos, sin = ROT_TABLE[camera.yaw]          # 16 discrete yaw steps
    for row in range(-H, H+1):                # H, strides from the zoom LOD ($fe04)
        for col in range(-H, H+1):
            h  = heightmap[camera.y+row][camera.x+col]
            z  = (h - H_BIAS) * camera.zoom_scale >> 4
            wx, wy = -col*camera.zoom_scale, -row*camera.zoom_scale
            rx = wx*cos - wy*sin
            ry = wx*sin + wy*cos
            sx = rx * EYE / (EYE - ry)                 # true perspective
            sy = (z - HORIZON) * EYE / (EYE - ry) + HORIZON
            corner[row][col] = (sx + 128, 124 - sy)

def draw_terrain(camera):                     # $f898, once per sim tick
    blit(back_buffer, terrain_master)         # $12ce0
    for row in far_to_near:                   # quadrant-specific order, SPEC §4
        for col in far_to_near:
            c = corner                        # this cell's 4 projected corners
            split = 'C10-C01' if flag[row][col] & 0x80 else 'C00-C11'
            h, t = heightmap[...][...], typemap[...][...]
            if h < 0x0c: h += tick & 3        # water shimmer, [$4bb3e] & 3
            if t < 0x0c: t += tick & 3
            fill_tri(tri_a, colour_index=t)   # $ef62 -> $e3e6 -> $e420
            fill_tri(tri_b, colour_index=h)
            for e in cell_bucket[row][col]:   # $115e0, same walk
                blit_sprite(back_buffer, SHEET[frame_for(e)],
                            lerp_corners(c, e.frac_x, e.frac_y))

def fill_tri(tri, colour_index):              # $ef62 / $e3e6 / $e420 / $e4de
    if winding_puts_mid_left(tri): colour_index = 0x1c
    for y in scanlines(tri):                  # 16.16 DDA, slopes from $f000
        xL, xR = edge_x(y)
        a5 = 0x2e000 + colour_index*128 + (8*y) % 128
        p0, p1 = u32be(a5) >> 16, u32be(a5) & 0xffff
        p2, p3 = u32be(a5+4) >> 16, u32be(a5+4) & 0xffff
        span_fill_bitplanes(back_buffer, y, xL, xR, (p0, p1, p2, p3))

def present():                                # $1870 + $187a
    wait_vblank()
    swap(front_buffer, back_buffer)
    shifter_base = front_buffer >> 8
```

The simulation is one layer up (`ai.md` / `strategy.md`); the renderer only
reads `heightmap`, `typemap`, `cell_bucket` and each entity's world position
and heading.

## What a modern port would do differently

1. **Cache the fill setup per zoom.** Projection is already cheap, but a
   precomputed per-zoom screen-space quad mesh removes the per-frame edge-slope
   `DIVU`s and span setup; per frame you only translate by the scroll offset.
2. **Span / occlusion buffer.** The plane blit writes every word whether or not
   it is later covered. A per-scanline span buffer drawn front to back removes
   the overdraw that dominates the zoomed-out frame.
3. **Redraw only what changed.** PM copies the `$78000` master into the back
   buffer and refills the whole island every tick, and re-projects on every
   camera move. A modern version scrolls the previous frame by the pixel delta
   and refills only the newly exposed strip, the water cells and the cells
   under moving sprites.
4. **Per-zoom tile art.** The 7 zoom levels are one triangle fill at different
   scales. Pre-rendered tile art per zoom, or flat cells at the furthest zoom,
   removes the per-vertex maths and the perspective divide.
5. **Blitter-shaped fills.** The unrolled `move.l D0/D1,(A2)+` span pusher and
   the pattern fill become blitter ops or a `memcpy`-class span fill on an STE
   or modern target. Or replace the rasteriser with a GPU heightmap mesh and a
   per-vertex colour ramp, keeping the flat-shaded look.
6. **Keep the draw order.** The far-to-near grid walk with sprites drawn inline
   is the Z order. A port should draw per cell, terrain then occupants, and not
   add a separate sorted sprite pass.
7. **Perspective.** `$ff7c` does a real `x/(EYE-z)` divide per corner. An
   axonometric projection would remove it, but the slight foreshortening is
   part of PM's look and costs nothing in a vertex shader.

## In-game camera control

**IKBD ISR `$18be`** (vector `$118`). On each `$fffc02` byte, `$f7` starts a
5-byte absolute mouse packet (→ `$1c48f` / `$2df92` / `$2df94`); anything below
`$f6` is a scancode handled at `$1962`:

- `$2a` / `$36` (left / right **shift** make) only set the flag `$2df8a`; they
  are never written to the key array.
- Every other make code sets `array[sc] = $ff` at `$2de6c`; a break code
  (bit 7) clears `array[sc & $7f]`.

**Per-frame camera loop `$13762`** reads that array:

| slot (dec) | scancode | effect |
|-----------|----------|--------|
| 54 | `$36` right-shift | **gate** for the rotate / horizon / eye / zoom rows below: `tst.b 54(A0) / beq` skips them (not the arrow block, next paragraph) |
| 71 / 82 | `$47` / `$52` | rotate `$ff9a += / -= $10`, then `& $f0` |
| 74 / 78 | `$4a` / `$4e` | `$ff96 += / -= $a` |
| 99 / 100 | `$63` / `$64` | `$ff98 -= / += $a` |
| 101 / 102 | `$65` / `$66` | `$ff9c -= / += 1` |
| 51 / 52 | `$33` / `$34` | zoom index `$57ffc ∓ 1`, then `jsr $fe04` (leaves `$ff9c` alone) |

The gate slot 54 is the right-shift slot, which `$18be` never writes, so this
block cannot be reached from the keyboard.

**The arrow keys are a separate, ungated block** (`$13824`, slots 72/75/77/80 =
scancodes `$48` up, `$4b` left, `$4d` right, `$50` down): each held tick moves
the camera cell `$4bb3a`/`$4bb3c` by 1. Live from `pm78_settle.snap`, holding `$4b`
for 500,000 steps moves X `$28` to `$26`, and the reader bodies `$13838` etc. fire
2 times (the loop runs every 187k steps on `pm142/rand1.snap`, 226k on `pm78_settle.snap`); `$48`/`$50` likewise move Y.
Keyboard scrolling therefore exists besides the minimap and compass scrolling. To drive it from the REPL, poke the
gate and the key together:

```
w 2dea2 ff000000     # slot 54 (gate) = $ff   -- $2de6c + $36
w 2deb2 00ff0000     # slot 71 ($47, rotate +) = $ff  -- covers $2de6c+$46..49
s 12000              # one frame; re-poke each frame, the loop steps ~1 in 6
```

Effects:

- **`$ff9a` (rotation)** re-projects the whole terrain (`iso_rotated.png`); 16
  discrete angles.
- **`$ff96` / `$ff98`** are HORIZON and EYE. The keypad changes them but does not
  force a `$fec6` rebuild, so the frame does not change until something else
  triggers a re-projection. Iso-view scrolling is minimap click and drag, the compass rose
  and the arrow keys (`strategy.md` "The player's commands" items 2 and 4, "Per-frame camera loop");
  there is no pointer-at-screen-edge test in the main loop `$12fd8`..`$13888` (code read). Poking the camera cell `$4bb3a`/`$4bb3c` directly (e.g.
  `w 4bb3a 002c0033`) does trigger a re-projection on the next `$f898`.
- **`$ff9c` (keypad zoom) has no effect.** `$137da` / `$137e8` change `$ff9c`
  but never call `$fe04`, so the tile geometry (`$fdea`–`$fe02`) is never
  recomputed.

## Zoom comparison

**How zoom is set.** `$13f60` (from the `$13212` mouse-cursor command dispatch,
cases `$13386` / `$1338a` / `$1338e` / `$133a0`) stores the index in `$57ffc`,
sets `$ff9c = $13f82[index]` and calls `$fe04` with `D1 = index` (1–7). `$fe04` derives the 13 render
constants at `$fdea`–`$fe02` (formulas in `scratchpad/pm69_fe04_notes.txt`).
`$13b9a`, the mission-view build run on the briefing OK click, does the same at
`$13bbe` with a fixed `#$4`. To reach either extreme without the mouse, patch
that immediate in `pm67_p4c.snap` (briefing, before OK), `w 13bc0 000<idx>33c1`
and `w 13bb8 00<tab>0000`, then run the OK click: `iso_zoom_in.png` = index 1,
`iso_zoom_out.png` = index 7 (`pm69_zi1.snap` / `pm69_zi7.snap`). Poking
`$fdea`–`$fe02` by hand is unsafe: an inconsistent stride sends the `$e4de`
filler into code at `$f0xx`.

**Result** (`trace_cfg.py --blocks`, instruction-weighted, 30 VBLs each, no
dropped frames at either zoom):

| region | zoom-in (idx 1) | zoom-out (idx 7) | out / in |
|--------|----------------:|-----------------:|---------:|
| `$14b62` entity driver          |  6196 |  1032 | 0.17× |
| `$16738` marker blit            |   650 |   109 | 0.17× |
| `$163ea` entity cell projection |  1062 |   374 | 0.35× |
| `$1648e` terrain sampler        |   417 |   118 | 0.28× |
| `$164bc` entity step DIVU       |    14 |     0 | —     |
| `$e4de` span filler             | 42396 | 32772 | 0.77× |
| **`$f000` fixed-point slope divide** |  2253 | **20867** | **9.26×** |
| `$1af32` timer ISR (fixed)      | 47806 | 48624 | 1.02× |
| **total instr-equiv**           | **423527** | **391580** | **0.92×** |
| with one rotation step / frame  | 428162 | 392576 | (`$fe8e` re-scan 3545 → 12483) |

1. **The bottleneck changes with zoom.** Zoomed in, the frame is bound by fill,
   sprites and entities: long spans, large sprites, and 6× the on-screen
   entities. Zoomed out, it is bound by geometry: ~9× the `$f000` slope divides
   for the many small tiles.
2. **Zoom-out is ~8 % cheaper on the first-mission island**, where the entity,
   sprite and fill saving outweighs the extra edge maths. On a dense late-game
   map the 9× `$f000` cost dominates, which is the zoomed-out slowdown players
   report.
3. **Rotation is absorbed at both zooms.** A rotation step adds ~3.5k (index 1)
   / ~12.5k (index 7) `$fe8e` iterations, and total load stays within 1 % of
   settled. No VBLs are dropped.
4. **These are instruction counts, not cycles.** The ratios hold, but a `divu`
   costs ~140 cycles on a real 68000, so the zoom-out `$f000` cost is heavier in
   wall-clock time than its instruction weight suggests.

## Open questions

- The `pm68_isoview.snap` profile counted `$12ce0` 10 times in 30 frames,
  where `pm71_run1.snap` runs it once per ~18-VBL tick. Whether the tick rate
  differs between the two captures has not been checked.
- The `0x1c` override has been measured at one pose only; its effect at other
  yaws and cameras is untested.

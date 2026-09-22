# PowerMonger ST — the graphics pipeline, and what a modern port would change

This is the narrative account of how PowerMonger draws its screens. The
porting contract, with every constant, table layout and verification record, is
`port/SPEC.md`; where this file is less detailed, SPEC is the reference.
Addresses are in the relocated game image (link base `$1050`).

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
around `$438ee` (`ai.md`): a **type** byte at `0(A1)` (grass / rock / water), a
**height** byte at `-8257(A1)`, and a per-cell flag byte at `+8257(A1)` whose
bit 7 selects the diagonal that splits the cell. The control array `$3f86c` is
the height source the projector reads. Corners are generated during the walk,
so the mesh is implicit in the grid.

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
  (SPEC §3).

### `$f898` — the render entry

`$f898` compares the camera cell (`$4bb3a`/`$4bb3c`), yaw (`$ff9a`) and zoom
half-extent (`$fdec`) with copies it keeps at `$f890..$f896`. On any difference
it toggles bit 7 of `$ffa5` and calls `$fec6` to re-project. It then always
runs the grid walk, so **every island cell is refilled each time `$f898` runs**,
whether or not the camera moved. It runs once per sim tick. Before the walk it
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
         tri(C10,C11,C00, colour(A1[0]));               // type plane
         tri(C01,C00,C11, colour(A1[-8257]));           // height plane
     } else {                                           // split on C10-C01,
         ...                                            // order by packed(C01) vs packed(C10)
     }
     if (A2[0] != 0) draw_cell_entities($115e0);        // sprites over this cell
  }
```

`colour(b)` is the raw terrain byte, plus `[$4bb3e] & 3` when `b < 0x0c`
(water). The colour index is therefore the terrain value itself: height banding
is the shading. One triangle of each cell takes the height byte and the other
the type byte, which gives sloped cells their two-tone split.

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
screen-X alignment. No texture map is read anywhere in the terrain path.

| colourByte | palette indices | terrain |
|-----------|-----------------|---------|
| `0x00`–`0x03` | 0, 14, 15 | open sea (each slot a different stipple) |
| `0x08`–`0x0b` | 4, 14, 15 | shallow water (each slot a different stipple) |
| `0x18`–`0x1c` | 1–3, 6 | rock / dark earth |
| `0x24`–`0x2c` | 11–13 | grass ramp |
| `0x30`–`0x3e` | 7, 9–12 | bright slopes, ridge |

**The `0x1c` override** (`$f072` / `$f154`): `$ef62` forces the colour byte to
`0x1c` when the triangle's winding puts the middle vertex on the left. At the
mission-1 start pose (cam 36,47, yaw 15) it applies to 52 of 128 triangles,
which draw 3298 px; 6 px of those remain in the finished frame, because
nearer terrain paints over the rest (`port/walkthrough/probe.fsx rasters`). At
that pose it therefore marks mostly back-facing triangles, and the visible
effect is limited to a few dark pixels along the island silhouette.

### Water shimmer

The water shimmer is a fill effect: the palette never changes. `$4bb3e` is a
longword tick counter, written only at `$13034` in the `$13000` sim tick and
incremented once per tick. Water cells (`b < 0x0c`) add `[$4bb3e] & 3` to their
colour byte, so each tick moves them to the next of four stipple slots and the
pattern repeats every four ticks.

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

### The HUD / marker blitter — `$e6ee`

`$16738` → `$e6ee` is a separate, wider multi-plane blitter (`add.w D0,D0 /
add.w D0,D0 / move.l 110(PC,D0),D0` → a 4-long descriptor table; `lsl.w #5,D1`
= 32-byte row stride). It draws the selected-group marker (`$165b2`) and the
HUD glyphs and is not on the terrain path.

### Trees / buildings / mountains

Mountains are terrain: a run of high cells drawn by the same triangle fill.
Trees and buildings are bucket sprites drawn over the cell they occupy, which
is why they appear and disappear at cell granularity when the camera rotates.

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
    $178ae  render setup (group exec sub-record)
    $f898   re-project if camera/yaw/zoom changed; refill every island cell, sprites inline
  --- every tick ---
    $14b62  entity FSM      (ai.md), relinks $47970 buckets via $163ea
    $6a3a   order executor
    $7a56   sprite / HUD compositor -> back buffer
    $165b2  selected-group marker
    ... at the VBL ISR: $187a swaps $2df7c <-> $2df78, writes ($2df7c >> 8) to $FFFF8200
```

On `pm71_run1.snap` the master copy `$12ce0`, the island refill `$f898` and the
buffer swap `$187a` each run exactly once per sim tick (13 hits each in ~2.78M
steps, one tick ≈ 15 VBLs), so every presented frame holds a complete island.

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
| `$1648e` | terrain height / type sampler | `lea $438ee,A4`, index by `worldX>>2` / `worldX>>6`; type at `0(A4)`, height/flag at `∓8257(A4)` | per terrain cell touched |
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

Zoom is a discrete 7-level select (`$13f83` table `[_,84,42,28,21,17,14,12]`,
index → `$fe04` → the 13 constants at `$fdea`–`$fe02`). The zoomed-out slowdown
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
| 54 | `$36` right-shift | **master gate**: `tst.b 54(A0) / beq` skips the whole block |
| 71 / 82 | `$47` / `$52` | rotate `$ff9a += / -= $10`, then `& $f0` |
| 74 / 78 | `$4a` / `$4e` | `$ff96 += / -= $a` |
| 99 / 100 | `$63` / `$64` | `$ff98 -= / += $a` |
| 101 / 102 | `$65` / `$66` | `$ff9c -= / += 1` |
| 51 / 52 | `$33` / `$34` | commander select `$57ffc ∓ 1`, then `jsr $fe04` |

The gate slot 54 is the right-shift slot, which `$18be` never writes, so this
block cannot be reached from the keyboard. To drive it from the REPL, poke the
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
  triggers a re-projection. Iso-view scrolling is cursor/edge driven
  (`$13118`+). Poking the camera cell `$4bb3a`/`$4bb3c` directly (e.g.
  `w 4bb3a 002c0033`) does trigger a re-projection on the next `$f898`.
- **`$ff9c` (keypad zoom) has no effect.** `$137da` / `$137e8` change `$ff9c`
  but never call `$fe04`, so the tile geometry (`$fdea`–`$fe02`) is never
  recomputed.

## Zoom comparison

**How zoom is set.** `$13f60` (from the `$13212` mouse-cursor command dispatch,
cases `$13386` / `$1338a` / `$1338e` / `$133a0`) sets `$ff9c = $13f83[index]`
and calls `$fe04` with `D1 = index` (1–7). `$fe04` derives the 13 render
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
  where `pm71_run1.snap` runs it once per ~15-frame tick. Whether the tick rate
  differs between the two captures has not been checked.
- The `0x1c` override has been measured at one pose only; its effect at other
  yaws and cameras is untested.

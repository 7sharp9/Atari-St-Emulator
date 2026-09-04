# PowerMonger ST — the graphics pipeline, and what a modern port would change

## Status (73rd pass; dither corrected 74th; projection + dither phase corrected 77th)

**77th-pass corrections** (aligned re-disasm of `$fecc`/`$ff7c`/`$e3e6..$e4de`,
folded into `port/SPEC.md` §3-4/§9):

- **Projection is exact, not "~15-20 px low".** Running the `$fecc`/`$ff7c`
  maths in integer for the 9×9 grid reproduces the game's own `$3f364` corner
  buffer **byte-for-byte** (81/81 vertices). `EYE` = `$ff98` = 320, `HORIZON`
  = `$ff96` = 130, confirmed from `$ff7c`'s PC-relative operands. The 76th's
  low-island claim was a diff against a live frame dump whose camera had drifted
  from the RAM snapshot.
- **Dither phase is `A5(y) = colourByte*128 + (topY & 15)*8 + 8*(y - topY)`.**
  Whole span walker disassembled (`$e3e6`→`$e5a6`). The table (`$2e000` =
  `[$ff9e]`) is **absolutely indexed by colour** — 128 B / colourByte = 16
  sub-patterns. A5 advances **+8 every scanline** (+4 roll `$e44a`, +4 from the
  right-edge `and.l (A5)+`), and the **whole span on one scanline is one 16-px
  pattern** (`long0` @ A5 = planes {0,1}, `long1` @ A5+4 = planes {2,3}), tiled
  screen-X-aligned; the Duff middle repeats it, the edges only AND a partial
  mask (`$ec62`/`$eca2`). Decoding at `colourByte*128`: **`0x00` → sea (idx
  14/15)** — that is how water is drawn, colourByte 0, no flag; `0x24-2c` →
  green 11/12/13, `0x18-1c` → rock 1-3/6. Not ~240 B, not cyclic (~8.5 KB).
- **`$f898` uses 1 of 4 yaw-quadrant grid-walk handlers** (`$f97e` →
  `$f98c` / `$fa98` / `$fbb2` / `$fccc` by `((yaw+8)>>5)&6`), each with its own
  grid start offset, 7-not-8 iteration count and corner→vertex assignment (keeps
  the far→near painter order across rotation). `$ef62` builds a span record at
  `$f1e2` (colour, topY, topX, two 16.8 edge slopes via `$f000`, a mid-segment
  switch height + slope-of-slope); the `$e420` DDA walker fills it. Full field /
  table layout in `port/SPEC.md` §4. **pm_render_ref.py still uses only the
  quadrant-0 walk — that is the last terrain-layer gap (missing sea + NW slope).**
- **Sprite category dispatch mapped** (`$115e0` → jump tables `$1162e` /
  `$1165a`): `cat 0` men (`$11c8a` / `$1187c`), `cat 4` animals (`$11a86`),
  most others share the `$11f78` ≈ `$11f82` mini-sprite blitter.
- **`$11f82` mini-sprite decode corrected** (not "1bpp masked silhouette"):
  8 × 11, **four bitplanes**, 55 bytes/frame = 11 rows × `[AND-mask, plane0,
  plane1, plane2, plane3]`, opaque where the mask bit is 0. `sheet_contact.png`
  now decodes as the little men — 4 faction-colour blocks (khaki/blue/orange/
  yellow) of 16. Per-category frame base/count + the `$16738`→`$e6ee` vs
  `$115e0`→`$11f82` split still deferred.

## Status (73rd pass, dither corrected 74th)

The 73rd pass added **"The terrain mechanism"** below (the 69th pass had a
profile, not the mechanism): PM's iso view is a **software heightmap-grid
rasteriser** — `$fec6` projects the grid corners (rotate + perspective divide),
`$f898` walks the grid far→near drawing **two rolling-bitplane-dithered triangles
per cell** with the terrain byte as the colour index, and cell sprites are drawn
inline in the same walk. No mesh, no texture, no light model, no palette
cycling (frame-diff confirmed). Sprites + draw order + the frame pipeline are
Pass 4 (still open).

**74th-pass correction** (`$ef62` → `$e3e2` → `$e4de` section below): the span
fill is not a "pre-expanded per-colour 4-plane pattern" with a "2-line vertical
dither" — it reads a **single ≈240-byte cyclic table of raw 16-bit bitplane
masks** whose base is the long at `$ff9e`, and the colour byte / triangle top-Y
only phase-shift the read cursor into it. The dither is 2-scanline-coherent
because the cursor advances half a tile per line, so each scanline's high two
planes are the next scanline's low two.

## Status (69th pass)

PM [cr Replicants] is driven all the way into the **isometric battle view**
(`iso_view.png`): world map, scroll icon, "Between Pages 1-5" briefing, click OK
(`$b814` commits the population, `$13b9a` builds the world), then the terrain
renderer composites the land onto the stone table. Recipe and the dialog decode
that found the OK click are in `README.md`.

The 69th pass reversed PM's in-game key handling (the "input-gated idle"
blocker), drove the camera, and profiled the renderer at both zoom extremes.
**Q2 is closed:** the zoomed-in vs zoomed-out hit-count comparison is in "Q2
zoom comparison — measured" below; the camera-control decode and the settled-vs-
moving profile are in "In-game camera control" and "Isometric renderer,
measured". Headline: zoom-in is fill/sprite/entity bound, zoom-out is slope-
divide bound (`$f000`, 9×), and on this early map zoom-out is ~8% cheaper
overall.

## Pipeline shape (world map / menus / iso view all share it)

| routine | role | shape |
|---------|------|-------|
| `$88ac`–`$8960` | menu / dialog / credits compositor | 4-bitplane word blit: per plane `move.w (A0)+,Dn / rol.w / andi.w #$fNNN`, OR the 4 planes, `move.w Dn,(A5)+`; unrolled ×6, `lea 152(A5),A5` row stride, `dbf D6` outer; command stream at `A4` |
| `$11422` | world-map per-VBL screen refresh | `lea $3f364,A0` (off-screen composed buffer), `mulu #$a0,D0` (row×160), `movem.l (A0)+,#$7cf8` / `movem.l #$7cf8,(A1)` (44 B/`movem`), 58 inner × 3 outer |
| `$1870`–`$1876` | VBL-wait spin | dominates every static screen (world map, briefing, settled iso view) |

Screen output is **direct-to-shifter**: displayed base from `$FFFF8201/8203`
(`$024400` at menus, `$01c700` in the iso view), not `_v_bas_ad`. Palette
straight to `$FFFF8240`. No XBIOS `Setscreen` / `Setpalette`. The whole pipeline
is: build the frame into an off-screen RAM buffer with software plane blits,
then one bulk `movem` copy to the shifter buffer, double-buffered via the
shifter base register.

## The terrain mechanism (73rd pass)

The 68th–69th passes *profiled* the isometric renderer (fill-bound, `$f000`
slope-divide heavy at zoom-out). This section is the *mechanism* — what it
actually draws and how — from disassembly of `scratchpad/pm70_iso.ram` plus a
consecutive-frame diff of the settled view.

### It is a software heightmap grid, not a polygon mesh

There is **no vertex list in RAM**. The terrain model is the two 8 KB planes at
`$438ee` (`ai.md`): a **type** byte at `0(A1)` (grass / rock / water) and a
**height** byte at `-8257(A1)`, plus a per-cell flag byte at `+8257(A1)`. The
per-cell *control* array `$3f86c` is reused by the projector as the height
source. Corners are generated on the fly during the draw walk — the "mesh" is
implicit in the grid.

### `$fec6` — project the grid corners (once per camera / rotation / zoom change)

```c
// A0 = $3f364 vertex buffer (2 words/corner: screenX, screenY)
// A1 = $3f86c + camera offset  (height source)
// D7 = rotated {cos, sin} pair from the $13f8a table, indexed by $ff9a
for (row = -H; row <= H; row++)             // H = $fdec, zoom-dependent half-extent
  for (col = -H; col <= H; col++) {
     int z = (cellHeight - $fec4) * $ff9c >> 4;          // height, scaled by zoom
     int wx = -col * $ff9c,  wy = -row * $ff9c;          // grid pos in world units
     int rx = wx*cos - wy*sin,  ry = wx*sin + wy*cos;    // rotate by $ff9a
     // $ff7c: perspective divide -- NOT a pure 2:1 iso
     int sx = rx * $ff98 / ($ff98 - ry);
     int sy = (z - $ff96) * $ff98 / ($ff98 - ry) + $ff96;
     *A0++ = sx + 0x80;                                  // + screen centre X
     *A0++ = 0x7c - sy;                                  // flip Y
  }
```

Two corrections to the 69th pass fall out of this:

- **`$ff96` / `$ff98` are not dead scroll variables** — they are the
  **projection parameters** (`$ff96` = horizon Y, `$ff98` = eye distance). The
  69th pass missed them because `$ff7c` reads them **PC-relative** (`4(PC)`,
  `12(PC)`, `26(PC)`), not as absolute addresses, and because `$f898`'s
  change-detector doesn't list them, so poking them without also forcing a
  `$fec6` rebuild changed nothing. They are set at zoom time and left alone.
- The projection **is perspective** (`x / (d - z)`), not an affine 2:1 iso. The
  "isometric" look is a fixed camera pitch plus the 16-step yaw (`$ff9a`). This
  is where a chunk of the `$f000` / DIVS cost the 68th pass measured actually
  goes — `$ff7c` does two `divs` per grid corner.

### `$f898` — walk the grid far→near, two dithered triangles per cell

```c
for (D7 = rows; ...; A0 += $fdf4, A1 += $fdf2)          // next grid row
  for (D6 = cols; ...; A0 += 4, A1 += 1, A2 += 2) {     // next cell
     if (A1[+8257] & 0x80) continue;                    // <-- per-cell "unchanged" skip
     // the cell's quad = 4 projected corners from the $3f364 buffer:
     int yTL=A0[0], yTR=A0[4], yBL=A0[64], yBR=A0[68];  // 64 = one grid row
     // split the quad on the diagonal that follows the slope:
     if (yBR > yTL) { tri(yTL,yTR,yBL, colour(A1[-8257]));    // height plane
                      tri(yTR,yBL,yBR, colour(A1[0])); }      // type plane
     else           { tri(yTL,yTR,yBR, ...); tri(yTL,yBL,yBR, ...); }
     if (A2[0] != 0) draw_cell_entity($115e0);          // sprite over this cell
  }
```

`colour(h)`: `h` is the terrain byte; if `h < 0x0c` (water) `h += masterTick & 3`.
So the colour index is **the terrain height / type value directly** — height
banding *is* the shading, there is no separate light model. One triangle of the
split takes the **height** byte, the other takes the **type** byte, which is why
a sloped grass cell shows a subtle two-tone split.

### `$ef62` → `$e3e6` → `$e4de` — the 4bpp pattern fill

> **77th-pass correction.** The 74th's aligned-disasm entry here read a
> mis-aligned image (`$e3e2` is the tail of an int→ASCII routine; the fill
> entry is `$e3e6`). Corrected facts: the phase is
> `A5 = [$ff9e] + colourByte*128 + (topY & 15)*8` (byte address); the table is
> **absolutely indexed by colour** (128 B / colourByte = 16 sub-patterns),
> **not** a ~240-byte cyclic loop — it spans ~8.5 KB for mission 1. Per 16-px
> screen cluster the fill reads **two** big-endian longs: `long0` at A5 =
> `{plane0<<16 | plane1}`, `long1` at A5+4 = `{plane2<<16 | plane3}`, then A5 +=
> 8; A5 also += 4 per scanline (the roll). Decoding the real table:
> `0x24-0x2c` → green ramp, `0x08-0x0b` → water, `0x18-0x1c` → rock. The
> paragraphs below (from the 74th) are kept for the edge-mask / Duff-device
> detail but their phase formula and "≈240 bytes / not per-colour" claims are
> superseded — see `port/SPEC.md` §4.

`$ef62` bounds-checks and sorts the 3 screen-Y corners, sets up two edge slopes
with `$f000` (fixed-point `dy/dx` via `divu`), writes the **colour byte** to
`0(A0)` and the triangle's **top screen-Y** to `2(A0)` of the span record
(`$f1e2`), and emits a per-scanline edge stream. `$e3e2` walks it; the span
middle is the `$e4de` Duff device (`move.l D0,(A2)+ / move.l D1,(A2)+` × ~40),
the ends are composited through the partial-word edge-mask tables at
`$ec62`/`$eca2` and the x-fraction table `$ece2` (`A6`).

**What `D0`/`D1` are, exactly.** They are `movem.l (A5),#$0003` — two consecutive
longwords from a **cyclic table of 16-bit bitplane masks** whose base is the
long at `$ff9e` (`$2e000` in `pm71_run1`/`pm74_late`; `$ffa2` holds `2×` that for
the `add.l/​lsr.l` addressing idiom in `$e3e2`). The table is **≈240 bytes and
repeats** (`$2e0f0 == $2e000`). It is **not** per-colour and **not** "solid
colour packed across 16 px" — most words are mixed-bit stipples like `$ff0d`,
`$a8ff`, `$1bfd`.

The fill writes `D0` then `D1` per 16-px group and the Duff device just repeats
that pair, so **every span is a horizontally-periodic-16 stipple**: for column
`c` (bit `b = 15-c`) the palette index is
`p3·8 + p2·4 + p1·2 + p0`, with `p0 = word[k]·b`, `p1 = word[k+1]·b`,
`p2 = word[k+2]·b`, `p3 = word[k+3]·b` (`word[]` = the table as u16s, `k` the
scanline's start index).

**The addressing is the whole trick:**

```
A5  =  ( [$ff9e]  +  colourByte  +  (topY << 4) )  >> 1          ; $e3e8..$e3fa
per scanline:  A5 = ((A5<<1) + 8) >> 1   ==   A5 + 4             ; $e44a..$e452
```

`A5 += 4` is **+2 u16 words per scanline**, while each scanline consumes 4 words.
So **scanline y's planes 2 & 3 are re-read as scanline y+1's planes 0 & 1** — the
pattern *rolls upward through the bitplanes*, which is what makes the dither
2-scanline-coherent (a monitor's line blur averages the pair). And `colourByte`
plus `topY` only add a **phase offset** into this one shared stream
(`colourByte/2 + 8·topY` bytes, i.e. `colourByte/2 + 4·(y + topY)` total). So
terrain "shading" / height banding is a **phase shift of a single fixed dither
texture**, not distinct flat colours — hence the woven look at height
transitions, and hence the 73rd-pass frame-diff finding *no* palette animation
(the shimmer is spatial and baked into this table, not cycled).

For `colourByte = 0, topY = 0` the emitted tile indices roll through the set
`{0, 3, 8, B, E, F}` — e.g. column 0 down successive scanlines is
`F, B, E, 3, 0, 8, E, …` (decoded from `$2e000`; `scratchpad/pm74_disasm.txt`
context + the table dump). The two 16-bit halves of each `D0`/`D1` longword are
usually equal (`$ff0dff0d`) → `plane0 == plane1`, `plane2 == plane3` for a
uniform run; the "transition" words (`$a800`, `$000d`) are where the two 16-px
sub-tiles differ, i.e. the band edge. **No texture map is read anywhere in the
terrain path** — this table is the entire surface-appearance model.

### Frame diff — the settled sea does not animate

`ATARI_FRAME_DIR` capture of 249 consecutive frames from `pm71_run1.snap`
(`ATARI_FRAME_EVERY=1`, `scratchpad/pm73_fr/`):

- **Palette: byte-identical across every frame** (all 200 per-line palette
  row-records unchanged). PM's water is **not** palette cycling.
- **Screen: 77 bytes changed over 240 frames**, all in two small clusters
  (y16–27 and y56–59) — moving unit sprites and the selected-group marker
  blink. The sea is completely static.
- Frame-to-frame screen deltas are 0 for ~19 frames then a ~120–170 byte burst
  — the sim-tick cadence (2.6 Hz), i.e. only unit animation.

So the `h += masterTick & 3` water-shimmer path exists but is gated out by the
per-cell `+8257 & 0x80` "unchanged" flag that `$fec6` sets when a corner didn't
move: a still camera skips the terrain fill entirely (matching the 69th-pass
"recomputes nothing while still"). Water only re-colours while the camera is
moving. On this sparse first map that is barely visible; on a water-heavy map it
would be the familiar shoreline shimmer, but still driven by the fill, not by
`$FFFF8240`.

### `$165b2` is the selected-group marker, not water animation

Corrected: `$165b2` (`$130bc` in the tick) draws the pulsing marker over the
**selected group's lead** (`$51538[$57fd2]` → lead object → world x/y), sprite
toggled by `$4bb41` bit 0. The sym file's old `pm_water_anim` name was wrong.

## Sprites and draw order (73rd pass)

### Sprites are drawn inline in the terrain walk — `$115e0`

`$f898`'s per-cell loop ends with `if ($47970[cell] != 0) jsr $115e0` (see "The
terrain mechanism"). `$115e0` walks that cell's bucket chain and, per entity,
does a **two-stage jump-table dispatch on `category` (byte 6)**:

```c
void draw_cell_entities(int cell) {
    for (obj *e = &obj[$47970[cell]]; e; e = &obj[e->bucket_next]) {
        DRAW_PRIMARY [e->category]();     // table at ~$11630: body sprite
        DRAW_OVERLAY [e->category]();     // table at ~$11664: shadow / banner / bar (0 = none)
    }
}
```

Because the grid is walked **far cell → near cell**, and each cell's sprites are
drawn immediately after that cell's terrain triangles, the **painter's
algorithm falls straight out of the walk order** — there is no depth sort and no
Z buffer. A near hill's terrain is drawn after (over) a far unit; a unit in a
near cell is drawn after the near hill. This is why PM never has a sprite
"floating" over a hill it should be behind: draw order *is* world order.
(Contrast the 68th-pass note on Super Sprint's full `exg` sort network every
frame — PM doesn't need one.)

### The mini-sprite blitter — `$11f82`

The little men / animals / trees are **1-bitplane masked sprites**:

```
A1 = $33000 + frame * 0x37        ; sprite sheet, 0x37 (55) bytes per frame
                                  ; = 11 rows x 5 bytes  (1 plane, ~16 px wide + mask)
A0 = dest word in the back buffer ; from the entity's projected screen (x,y)
per row (D2 = 11, clipped to screen top/bottom):
    D0 = 8 - (x & 7)              ; sub-word shift
    mask = rol.w D0, (A1)+        ; 1 byte -> shifted 16-bit AND mask
    data = rol.w D0, (A1)+        ; 1 byte -> shifted 16-bit OR data
    (A0) = ((A0) & mask) | data   ; punch + paint, one word
    ... repeated across the sprite width, then A0 += 0x98 (row stride - width)
```

So a mini-sprite is a **monochrome silhouette** punched into whatever plane the
blitter is pointed at (the entity's colour comes from which plane / the terrain
underneath, not from the sprite data). Frame selection is by the entity's
`heading` (byte 17) — `$16738` indexes a per-heading frame table (`$16754`),
`-1` meaning "no sprite for this facing" (the 16 headings fold to ~8–9 drawn
frames + horizontal flip). A full pixel-accurate rip needs the per-category
frame counts and the sheet extent — deferred, same as the Super Sprint rip.

### The HUD / marker blitter — `$e6ee`

A separate, wider multi-plane blitter (`add.w D0,D0 / add.w D0,D0 / move.l
110(PC,D0),D0` → a 4-long-per-entry descriptor table; `lsl.w #5,D1` = 32-byte
row stride) used by `$16738` for the selected-unit marker (`$165b2`) and the
on-screen HUD glyphs. Not on the terrain hot path.

### Trees / buildings / mountains

Mountains are **terrain**, not sprites — a mountain is just a run of high cells,
drawn by the same `$f898` triangle fill with a high colour index. Trees and
buildings are **bucket sprites** (`$115e0`, their own `category` values) drawn
over the terrain cell they occupy — which is why they pop in/out cleanly at the
cell granularity when the camera rotates.

## The frame pipeline (73rd pass)

Screen output is direct-to-shifter, double-buffered by the base register. Two
compose buffers, `$2df7c` (on screen) and `$2df78` (back); a **master terrain
buffer** at `$e0d4`.

```
  once per mission ($13b9a):  build terrain master -> $12ce0 copy into BOTH buffers

  per simulation tick ($13000), present rate gated by $57ff0/$57fee (= 1 normally):
    $1870   spin until the VBL flag $2df8c is set                 ; frame sync
    $12ce0  copy terrain master ($e0d4) -> back buffer ($2df78)   ; 500 rows, movem, ~1/3 frames
    $178ae  render setup A  (group exec sub-record)
    $f898   terrain: per-cell "+8257 & $80 unchanged" skip -> often a near-no-op
            ($fec6 re-projects the grid only if camera / $ff9a / zoom changed)
  --- ungated (every tick) ---
    $14b62  entity FSM      (ai.md)  -- also relinks $47970 buckets via $163ea
    $6a3a   order executor
    $7a56   sprite / HUD compositor  -> draws sprites into the back buffer
    $165b2  selected-group marker
    ... at the VBL ISR: $187a swaps $2df7c <-> $2df78, writes ($2df7c >> 8) to $FFFF8200
```

The zoom LOD (`$fe04`, 7 levels → 13 constants `$fdea..$fe02`) only changes the
grid extent / stride / the `$ff9c` scale factor `$fec6` multiplies by — it does
**not** switch to different tile art. Every zoom draws the same triangle fill
with more or fewer, larger or smaller cells (69th-pass "Q2 zoom comparison").

Measured cadence is in "Isometric renderer, measured" and "Q2 zoom comparison":
the settled view costs ~nothing (terrain skipped, ~4 sprites/frame, `$12ce0`
every ~3 frames); a moving camera pays the full `$fec6` re-projection + `$f898`
fill; the fill (`$e4de`) is ~40 % of all instructions when it runs.

## Isometric renderer, measured (68th–69th pass)

Profiled from `pm67_p4c.snap` / `pm68_isoview.snap` + the OK click:
`ATARI_TRACE_EVENTS` over the world-build (terrain appears ~13 frames in) and
over 20–30 frames of the settled view; `trace_cfg.py --blocks`. Addresses are in
the relocated game image (base `$1050`), disassembled from the snapshot RAM.

| routine | role | what it does | measured |
|---------|------|--------------|----------|
| `$14b62` | entity iteration + projection driver | walks the 50-byte object records `$51b66+$32 .. $57f66` (~490 slots), `tst.b 5(A1)` active-gate, per-type `jmp` table `$14bba` keyed on `31(A1)`; calls `$163ea` per moved entity | ~27 active entities scanned/frame (x511 over 19 VBLs) |
| `$163ea` | entity world → screen-cell projection | `cell = ((worldY & $ff00) >> 2) + (worldX & $ff)` (byte-wise add): **shift + add, no MUL/DIV**, the iso axis mapping is baked into the world-coord encoding. Compares old vs new projected cell, `beq $1648c` skips the redraw when unchanged | per moved entity |
| `$1648e` | terrain height / type sampler | `lea $438ee,A4`, index by `worldX>>2` / `worldX>>6`; type byte at `0(A4)`, height/flag at `∓8257(A4)` (two parallel 8 KB planes) | per terrain cell touched |
| `$164bc` | terrain-quad edge slope | `sub.w D6,D0 / sub.w D7,D1 / ext.l / divu D2,D0 / divu D0,D1`, dx/dy then dy/dx for a scanline walk of a quad edge. **The DIVU the 67th-pass overflow / divide-by-zero fix unblocked** (`16(A1)` = edge height, can be 0 or push the quotient past 16 bits) | per drawn terrain edge |
| `$16738` | per-entity sprite blit | visibility-culled via `btst #7,7(A6)` / `btst #6,7(A6)`; painter order from cell buckets and the per-commander `$13c`-byte records at `$51538` (`mulu #$13c` index), not from a sort | per visible entity |
| `$e4de`+ | unrolled span filler | `$e4da: jmp 82(PC,D6.w)` into a ~120-deep `move.l D0/D1,(A2)+` chain (Duff device), span length in D6; the caller loop is `$e45a`/`$e45e`/`$e462`. **This is the fill-rate hot path** | ~40% of all instructions in the settled view (69th) |
| `$f000`–`$f13c` | fixed-point slope divide | `divu` + `lsl.l #8` normalise, dx/dy and dy/dx, feeds the span walk | ~8800 instr-equiv / 30 settled frames |
| `$12ce0` | offscreen buffer → shifter screen | `move.w #$1f3,D0` then `movem.l (A0)+,#$0cfc` / `movem.l #$0cfc,(A1)` ×2, `adda.w D1,A1`, `dbf`: 500 rows, 24 B/`movem`, 32-byte stride | **~once per 3 frames** (10 hits / 30 frames, 69th — periodic double-buffer flush, *not* motion-gated) |
| `$fe04` | zoom → geometry | from D1 = zoom index (1–7) derives 13 tile-size / stride / cell-count words at `$fdea`–`$fe02`; the renderer reads those, **not `$ff9c`** | on every zoom change (via `$13f60`) |
| `$fe8e`–`$ff94` | rotation terrain re-scan | per-cell height scan, bounds `$fdec`/`$fdee` (zoom-dependent); runs when `$ff9a` (rotation angle, `& $f0`, 16 steps) changes | ~4600 cell iterations per angle step (69th) |
| `$12d08` | 16×16 → 32 multiply helper | classic 3-`mulu` partial-product long multiply, via `$12c9a` | fixed-point scale during the build |
| `$1af32` | timer ISR (`rte` at `$1af44`) | **not a renderer**, hottest in the trace only because it interrupts everything | fixed ~12–15% of instructions, settled == moving |

Findings (69th pass, `pm68_isoview.snap` at zoom index 4, `trace_cfg.py --blocks`,
instruction-weighted, 30 frames settled vs 30 with the rotate key poked):

1. **Fill-rate bound, not geometry bound.** The `$e4de` unrolled `move.l` span
   filler is ~40% of all executed instructions. `$163ea` projection (shift + add)
   and `$164bc` DIVU are together <1%. The 68th-pass conclusion holds and is now
   quantified.
2. **A rotation step is nearly free in aggregate (+0.6%).** One angle change adds
   ~4600 `$fe8e` cell iterations but removes an almost equal amount of `$e4de`
   fill / `$e4xx` idle spin (settled 382k instr-equiv, rotating 384k). The view
   has large idle headroom — the `$1870` / `$e4xx` spin absorbs the transform
   cost. There is no per-frame full recomposite; `$163ea` / `$1648e` / `$16738`
   counts are byte-identical settled vs moving.
3. **The settled view is not idle.** It still runs `$163ea` (~14/frame),
   `$16738` (~4/frame) and flushes `$12ce0` every ~3 frames. The 68th-pass claim
   "`$12ce0` only fires when the camera moved / settled costs almost nothing" was
   imprecise — the flush is periodic, and unit-animation projection runs every
   frame.

Zoom is a discrete 7-level LOD select (`$13f83` table `[_,84,42,28,21,17,14,12]`,
index → `$fe04` → the 13 constants at `$fdea`–`$fe02`). The "zoomed-out
slowdown" players report is the `$f000` slope-divide cost (9× more edges to set
up for many small tiles) once the map is dense enough to outweigh the
entity/sprite/fill saving — see "Q2 zoom comparison — measured".

## The renderer as modern pseudocode (73rd pass)

The whole terrain + sprite path, decoupled from the ST:

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
            sx = rx * EYE / (EYE - ry)                 # $ff98 = EYE  -- true perspective
            sy = (z - HORIZON) * EYE / (EYE - ry) + HORIZON
            corner[row][col] = (sx + 128, 124 - sy)
            dirty[row][col]  = (corner[row][col] != old_corner[row][col])

def draw_terrain(camera):                     # $f898
    blit(back_buffer, terrain_master)         # $12ce0: start from the cached full terrain
    for row in far_to_near:                   # painter's order
        for col in far_to_near:
            if not dirty[row][col]:           # +8257 & 0x80 -- still camera => skip
                continue
            c = corner  # 4 projected corners of this cell's quad
            split = 'TL-BR' if c[BR].y > c[TL].y else 'TR-BL'   # follow the slope
            h, t = heightmap[...][...], typemap[...][...]
            if h < WATER_LEVEL: h += (tick & 3)                 # shoreline shimmer
            fill_tri(c0, c1, c2, colour_index=h, topY=min_y(c0,c1,c2))   # $ef62 -> $e4de
            fill_tri(c1, c2, c3, colour_index=t, topY=min_y(c1,c2,c3))   # 2nd tri: the type byte
            for e in cell_bucket[row][col]:                     # $115e0, same walk
                blit_sprite(back_buffer, SHEET[frame_for(e)],   # $11f82: 1bpp masked
                            project(e.world_x, e.world_y))

def fill_tri(a, b, c, colour_index, topY):    # $ef62 / $e3e2 / $e4de
    DITHER = u16_table_at(mem_long[0x00ff9e])         # ~240-byte cyclic bitplane-mask stream
    k0 = (colour_index // 2) + 8*topY                 # phase offset (bytes) into the stream
    for y in scanlines(a, b, c):                      # edges via fixed-point dy/dx ($f000)
        xL, xR = edge_x(y)
        k = (k0 // 2) + 2*y                           # +2 u16 words per scanline (A5 += 4)
        p0,p1,p2,p3 = DITHER[k], DITHER[k+1], DITHER[k+2], DITHER[k+3]   # planes 0..3
        # every 16-px group of the span is this same 4-word tile; y+1 reuses p2,p3 as its p0,p1
        span_fill_bitplanes(back_buffer, y, xL, xR, (p0,p1,p2,p3))       # ends via $ec62/$eca2 masks

def present():                                # $1870 + $187a
    wait_vblank()
    swap(front_buffer, back_buffer)
    shifter_base = front_buffer >> 8
```

Everything the AI/sim does is one layer up (`ai.md` / `strategy.md`); the
renderer only *reads* `heightmap` / `typemap` / `cell_bucket` / each entity's
`world_x/y` + `heading`.

## What a modern port would do differently

Grounded in the pipeline above (off-screen compose + bulk blit + software plane
fills):

1. **Cache the fill setup per zoom.** Projection itself is already cheap
   (finding 1), but a precomputed per-zoom screen-space quad mesh removes the
   per-frame edge-slope `DIVU`s and fill-span setup; per frame you only translate
   by the scroll offset.
2. **Span / occlusion buffer.** The `$88ac`-style blit writes every plane word
   whether or not it is later covered. A per-scanline span buffer drawn
   front-to-back removes the overdraw that dominates the zoomed-out frame.
3. **Scroll the previous buffer.** PM already keeps a terrain master (`$e0d4`)
   and re-copies it whole (`$12ce0`) every present, then re-fills every dirty
   cell. On a camera move that's a full re-projection + full re-fill. A modern
   version scrolls the master by the pixel delta and re-fills only the newly
   exposed edge strip + the cells under moving sprites.
4. **Per-zoom tile LOD as real assets.** The 7 zoom levels are the same triangle
   fill at different scales (73rd pass) — no art switch. Ship pre-rendered tile
   art per zoom; at the furthest zoom draw flat coloured cells with no
   per-vertex math and no `$ff7c` perspective divide.
5. **Blitter-shaped fills.** The hand-unrolled `move.l D0/D1,(A2)+` span pusher
   and the rolling-bitplane dither become blitter ops / a `memcpy`-class span fill on an
   STE or a modern target, roughly 4–8× off the fill cost. Or drop the software
   rasteriser entirely for a GPU heightmap mesh + a per-vertex colour ramp,
   keeping the flat-shaded look.
6. **The draw order is already right — keep it.** Unlike Super Sprint's full
   `exg` sort network every frame (`$e84c`), PM needs no sprite sort: the
   far→near grid walk with sprites drawn inline (`$115e0`) *is* the Z order.
   A modern port should preserve that structure (draw per-cell, terrain then
   occupants) rather than reintroducing a separate sorted sprite pass.
7. **Perspective, not iso.** `$ff7c` does a real `x/(EYE-z)` divide per corner
   (two `divs`). If the design can accept true axonometric (no foreshortening)
   the divide goes away and corners become an affine transform — but PM's subtle
   perspective is part of its look, so a GPU port would just do it in the vertex
   shader for free.

## In-game camera control (69th pass)

**IKBD ISR `$18be`** (vector `$118`, confirmed installed). On each `$fffc02`
byte: `$f7` starts a 5-byte mouse abs-position packet (→ `$1c48f` / `$2df92` /
`$2df94`); anything `< $f6` is a scancode → `$1962`:

- `$2a` / `$36` (left / right **shift** make) are intercepted and only set the
  flag `$2df8a` — they are **never written to the key array**.
- every other make code → `array[sc] = $ff` at `$2de6c`; break code (`bit7`) →
  `array[sc & $7f] = 0`.

**Per-frame camera loop `$13762`** reads that array:

| slot (dec) | scancode | effect |
|-----------|----------|--------|
| 54 | `$36` right-shift | **master gate**: `tst.b 54(A0) / beq` skips the whole block |
| 71 / 82 | `$47` / `$52` | rotate `$ff9a += / -= $10`, then `& $f0` |
| 74 / 78 | `$4a` / `$4e` | `$ff96 += / -= $a` |
| 99 / 100 | `$63` / `$64` | `$ff98 -= / += $a` |
| 101 / 102 | `$65` / `$66` | `$ff9c -= / += 1` |
| 51 / 52 | `$33` / `$34` | commander select `$57ffc ∓ 1`, then `jsr $fe04` |

The blocker resolves: the gate at slot 54 is the right-shift scancode slot, and
`$18be` **never sets it** (shift is special-cased out). `kbd 65` did nothing
because slot 54 was 0. To drive the camera from the REPL, poke both:

```
w 2dea2 ff000000     # slot 54 (gate) = $ff   -- $2de6c + $36
w 2deb2 00ff0000     # slot 71 ($47, rotate +) = $ff  -- covers $2de6c+$46..49
s 12000              # one frame; re-poke each frame, the loop only steps ~1 in 6
```

What actually moves the view:

- **`$ff9a` (rotation) is the only live camera parameter.** Poking it via the
  keypad path re-projects the whole terrain (full-screen frame diff, visually
  confirmed — `iso_rotated.png`). 16 discrete angles.
- **`$ff96` / `$ff98` are the projection parameters, not scroll** (73rd-pass
  correction — see "The terrain mechanism"). The 69th-pass abs-address search
  missed them because `$ff7c` reads them PC-relative; poking them without also
  forcing a `$fec6` rebuild is inert, which is why the keypad increments gave a
  byte-identical frame. Iso-view scrolling is cursor/edge driven (`$13118`+).
- **`$ff9c` (keypad zoom) is a latent no-op.** `$137da` / `$137e8` bump `$ff9c`
  but — unlike the rotate/commander cases — **never call `$fe04`**, so the tile
  geometry (`$fdea`–`$fe02`) is never recomputed. 11 increments → byte-identical
  frame. The only real reader of `$ff9c` is a coincidental data constant.

## Q2 zoom comparison — measured (69th pass)

**How zoom is set.** The functional path is `$13f60` (from the `$13212`
mouse-cursor command dispatch, cases `$13386` / `$1338a` / `$1338e` / `$133a0`):
it sets `$ff9c = $13f83[index]` **and** `jsr $fe04` with `D1 = index` (1–7).
`$fe04` derives the 13 render constants at `$fdea`–`$fe02` (formulas in
`scratchpad/pm69_fe04_notes.txt`). `$13b9a` (the mission-view build, run on the
briefing OK click) itself does this at `$13bbe` with a hard `#$4`. To reach the
two extremes without the mouse dispatch: from `pm67_p4c.snap` (briefing, pre-OK)
patch the `$13bbe` immediate — `w 13bc0 000<idx>33c1` and `w 13bb8 00<tab>0000`
— then run the OK click. `iso_zoom_in.png` = index 1, `iso_zoom_out.png` = index
7 (`pm69_zi1.snap` / `pm69_zi7.snap`); both re-render cleanly, `$fdea`–`$fe02`
land exactly on the D1=1 / D1=7 rows. (Hand-poking `$fdea`–`$fe02` instead is
unsafe — an inconsistent stride sends the `$e4de` filler into code at `$f0xx`;
not an emulator gap, `$f0xx` is never written in normal play.)

**Result** (`trace_cfg.py --blocks`, instruction-weighted, 30 VBLs each, no
dropped frames at either zoom):

| region | zoom-in (idx 1) | zoom-out (idx 7) | out / in |
|--------|----------------:|-----------------:|---------:|
| `$14b62` entity driver          |  6196 |  1032 | 0.17× |
| `$16738` sprite blit            |   650 |   109 | 0.17× |
| `$163ea` projection             |  1062 |   374 | 0.35× |
| `$1648e` terrain sampler        |   417 |   118 | 0.28× |
| `$164bc` edge DIVU              |    14 |     0 | —     |
| `$e4de` span filler            | 42396 | 32772 | 0.77× |
| **`$f000` fixed-point slope divide** |  2253 | **20867** | **9.26×** |
| `$1af32` timer ISR (fixed)      | 47806 | 48624 | 1.02× |
| **total instr-equiv**          | **423527** | **391580** | **0.92×** |
| with one rotation step / frame  | 428162 | 392576 | (rot re-scan `$fe8e` 3545 → 12483) |

**Findings.**

1. **The bottleneck swaps sides with zoom.** Zoom-**in** is fill-rate + sprite +
   entity bound: big tile spans (`$e4de`), big sprites (`$16738`), and far more
   on-screen entities to process (`$14b62` 6×). Zoom-**out** is geometry bound:
   ~9× the `$f000` slope divides, because many small tiles = many more quad
   edges to set up, even though each span is short.
2. **Zoom-out is ~8% cheaper here, not more expensive** — on this sparse
   first-mission island the entity/sprite/fill saving beats the extra edge
   math. On a dense late-game map the `$f000` 9× would invert that (this is the
   "zoomed-out slowdown" players report). The 69th-pass prediction that weight
   shifts toward `$fe8e` / projection was half right: it shifts to `$f000`, and
   `$163ea` projection actually *drops*.
3. **Rotation stays absorbed at both zooms.** A rotation step adds ~3.5k
   (`idx 1`) / ~12.5k (`idx 7`) `$fe8e` cell-scan iterations but total load
   barely moves (both within 1% of settled) — the `$1870` / `$e4xx` idle spin
   still has the headroom. No dropped VBLs at either zoom in any run.
4. **Instruction-count model, not cycles.** The ratios are meaningful; "within
   frame budget" is soft (this emulator is instruction-counted). A `divu` is
   ~140 cycles on a real 68000, so `$f000`'s 9× at zoom-out is heavier in
   wall-clock than the instruction weight suggests — reinforces finding 2.

# Midwinter: the 3D view

How one frame of the first-person view is built and drawn. Everything here is measured on **one frame at one pose**:
`s_3d_6.snap` (`scratchpad/midwinter/agents/static/`), heading 0, camera cell (50, 50), pitch words (163, 0), five
objects in view. `py/pipeline/run.sh` rebuilds the frame's snapshots and captures from that snapshot and prints every
count below. The cell scan is modelled for 40 headings and 6 camera cells (section 5a). Other pitches and vehicles are untested, and
three stages are counted and read but not modelled (section 6).

## 1. The frame

A frame is `$14e00` to the next `$14e00`: 225,171 steps, of which the landscape build `$18304` takes 45,381 and the
draw loop `$19ce2` 165,677. Calls in that one frame (`hits`, `py/pipeline/hits_frame.repl`):

```
$14e00 frame
  keys $14efc, vehicle control $12e9c (-> $158f4 step vectors, $159a4 camera cell), panel $129d2, sky fill $1580e
  $18304 landscape build
    $18362 x2    clear the 16 KB cell-record buffer
    $16d9c x1    the camera's own cell
    $16cf6 x1    ring scan outward from the camera: 150 cells (section 5a)
                 ($161f6/$163ba/$1657e/$16742 x8 each, always run; the corner routines
                 $16906/$16a02/$16afe/$16bfa, x6 each, and the eight side extensions are gated by the octant flags $172c4, set by $1710e)
    $17f20 x1    the four corners of the clip window (28..292, 51..181)
    $170e6 x1 -> $17444 x150   one cell record -> polygons
                 $1d41e x121   register the objects standing in the cell
                 $17b86/$17bbe x64   backface test (sign of the projected triangle's 2D cross product)
                 $17fa0 x310   clip an edge to the window by outcodes
                 $18802 x26, $188f0 x21, $189de x26, $18acc x23   polygon builders; $17e94 x0 (whole-window polygon)
                 $18bba x90    append a polygon to the draw list
  $19ce2 draw loop
    $19d6a x90   terrain polygon: $19f20 edge scan (x284), $1b1bc span fill -> $1b0e4 x2 (even rows, odd rows)
    $1d5a6 x5    object: $1dd14 shape renderer, $1d71c -> $19e08 x20 object polygons ($19f20 x73, $1b1bc x20)
  $1bbe6 goggle mask, $bd9a flip
```

The names are from the bodies read; the ring routines are modelled (section 5a), the builders' roles are inferred from
where they sit, since their logic is not modelled. The object renderer costs more than the terrain: an event trace of the frame puts
`$1d5a6` at 101,276 steps against 63,540 for the 90 terrain polygons, and 46,171 of the object steps inside `$122f0`,
a checksum over code that `$1dd14` calls once an object (an agent's trace, not re-run; that it is a protection check is
inferred).

**Visibility is painter's order with no sort.** The scan lists cells ring by ring outward from the camera
(Chebyshev distance in world axes, section 5a), each cell appends its polygons, and `$19ce2` walks the list from its end,
so the outermost ring is drawn first. Within a ring and between adjacent rings the order is not view depth: on the model,
26% to 33% of 8-adjacent listed cell pairs with a depth difference are drawn nearer-first, by at most 1.41 cells of depth
(inferred from the model, `py/scan/order_check.py`; whether it shows on screen is untested). An object is listed before its
cell's polygons, so it is drawn after its own ground and before any nearer cell.

## 2. Vertices and projection (proven for this frame)

`$159a4` turns the camera position (`$12c60`/`$12c64`, 512 units a cell, `$12c5a`) into the cell `$12c68`/`$12c6a`,
the fraction within it, and the height-grid pointer `$12c80` (`terrain.md` section 5: 100 x 100 cells of 4 bytes at
`$404c4`, 400 bytes a row). `$158f4` sets the per-cell step vectors `$171f8..$1720c` from the heading `$12c98` and the
sine table `$1c6bc` (512 words, amplitude 16384, 1024 heading units a circle).

A vertex is a 16.16 accumulator (D0, D1, D2) stepped by the row and column vectors; the cell's height minus the camera
height `$1721c` goes into Y times 16384 (`$17212`) and into Z times 64 (`$17210`). The integer parts are rotated by
the pitch words (`x' = X*c - Y*s`, `y' = Y*c + X*s`, c = `$17216`, s = `$17214`) and projected with two `divs`:
`sx = x'/z + 160`, `sy = -(y'/z) + 132`. A divide overflow or z <= 1 marks the vertex -1 (behind the camera). Each
projected point carries an outcode: 1 x < 28, 2 x > 292, 4 y < 51, 8 y > 181.

| check | script | result |
|---|---|---|
| camera-space records of the first cell's four vertices | `py/pipeline/cam_check.py` | 4 of 4 |
| every vertex of the 150 cell records: screen x, y, z, outcode, or the -1 mark | `py/pipeline/proj_check.py` | 190 of 190 (130 projected, 60 behind the camera) |

The projection check takes the game's camera-space records as its input, so what it proves is the rotate, divide and
outcode step; the camera-space arithmetic itself is checked on the first cell only.

## 3. Buffers (base pointers are globals; an index is a byte offset from the base)

| buffer | base | record |
|---|---|---|
| cell records | `$12cfa` = `$54000`, 16 KB | overlapping: stride 16 along a column, 336 along a row. +0 / +14 the projected and camera point offsets of P0; P3 at +16 / +30, P1 at +336 / +350, P2 at +352 / +366; +8 diagonal flag; +10, +11 the shade bytes of the two triangles (the height cell's `2(A0)`); +12 the distance band, 0, 100, 200 or 300 |
| points | `$12ce6` = `$60000` | camera record 12 bytes (x', y' longs, z in the low word at +10); projected record 8 bytes (sx, sy, z, outcode); clip points 8 bytes; next free offset `$12c88` |
| edges | `$12cea` = `$62000` | 8 bytes: start point, end point, a clip tag for each end (-1 none; 0 left, 8 right, 4 top, 12 bottom) |
| ring entries | `$12cee` = `$64000` | 6 bytes: edge offset, next entry (a polygon is a ring) |
| polygon headers | `$12cf2` = `$65000` | 8 bytes: colour index (shade 12..23 plus the band), first entry |
| draw list | words from `$18be2` to the pointer `$18bda` | a positive word is a polygon header offset; an object is a word followed by a negative id (below -15 the record `$70000 + id`, -1..-15 the slot `$1cd7e + (id-1)*$2c`) |

At the draw loop's entry the list holds 95 items, 90 polygons and 5 objects (ids -16, -3, -32, -2, -4); the polygons'
rings hold 284 entries, 76 triangles and 14 quads (`py/pipeline/polys.py`), which is the 284 calls `$19d6a` makes
to the edge scanner.

## 4. Edge scan `$19f20` (proven for this frame)

Two tables of 200 words, one x per screen row: `$1a622` for edges running up the screen and `$1a7b2` for edges
running down (pointers at `$1a61a`, `$1a61e`); `$1a616` is the polygon's ymax and `$1a618` its ymin. A horizontal edge
is skipped. For the rest, with dy rows and dx across: `q = |dx| / dy`, a 16-bit fraction `((|dx| mod dy) << 16) / dy`,
and an accumulator seeded `$4000` (up) or `$c000` (down); row k gets x1 plus or minus k steps of q with the fraction's
carries (`addx`/`subx`), for rows y1 to y2 - 1. The edge's last row is not written.

`py/pipeline/edge_model.py` against the tables the emulator holds at each of the 90 terrain fills
(`tables.repl`): the y range matches on 90 of 90 polygons and every row from ymin to ymax - 1 on both tables,
**713 of 713 rows**.

## 5. Span fill `$1b1bc` (proven for this frame)

Rows ymin to ymax, spans inclusive, 16-pixel groups of four plane words on the screen at `$12d0a`. The fill runs twice
(`$1b0e4`), over the even rows and then the odd rows, with a different dither pair each: `$1b340[colour]` is four
bytes, the pair for each pass (swapped when ymin is odd), and `$1b280` gives four plane words a colour; a pair is
mixed as `T[c0] & $5555 | T[c1] & $aaaa`. A pair of equal colours goes to solid-fill routines (`$1b300`).

**Row ymax is filled from stale table entries.** No edge writes its own last row, so the bottom row of every polygon
takes its span from whatever earlier polygons left in the tables at that row. A model has to carry the tables across
polygons to reproduce the screen.

`py/pipeline/fill_model.py` against the screen before and after each fill (`screens.repl`, `bp 1b1bc` and
`bp 1b27e`): with the emulator's tables, **110 of 110** fills are exact (90 terrain, 20 object polygons); with the
edge model's own rows for ymin to ymax - 1 and the emulator's row ymax, 90 of 90 terrain polygons are exact.

## 5a. The cell scan `$16cf6` (proven for 46 poses)

The scan is a fixed set of square rings in world axes around the camera cell, pruned by 12 flag bytes chosen by the
heading's octant. Cells are world offsets (x east, y north) from the camera cell. `$1710e` copies the 12 bytes at
`$172d0 + 12 * ((heading & $3fe) >> 7)` (8 rows, 128 heading units an octant) to the flags `$172c4..$172cf`. The list at
`$18f02` then gets, in order: the camera cell (`$16d9c`), and for each ring k = 1..8:

1. The four arms `$161f6`, `$163ba`, `$1657e`, `$16742`, always: (0,k), (k,0), (0,-k), (-k,0).
2. After each arm, two side extensions of n cells each (n = word p of `$17140` = 0,1,2,3,4,5,4,2 for k = 1..8; none when
   n is 0), each run only when its flag byte is nonzero:

   | arm | first extension (flag) | second extension (flag) |
   |---|---|---|
   | (0,k) `$161f6` | `$15a96` (`$172c4`) towards +x | `$15b82` (`$172cf`) towards -x |
   | (k,0) `$163ba` | `$15f32` (`$172c7`) towards -y | `$15e46` (`$172c6`) towards +y |
   | (0,-k) `$1657e` | `$15d5a` (`$172ca`) towards -x | `$15c6e` (`$172c9`) towards +x |
   | (-k,0) `$16742` | `$1601e` (`$172cd`) towards +y | `$1610a` (`$172cc`) towards -y |

3. For rings 1..6 only (gate words `$17150` = 1,1,1,1,1,1,0,0), the corner cells (k,k) `$16906` (flag `$172c5`), (k,-k)
   `$16a02` (`$172c8`), (-k,-k) `$16afe` (`$172cb`), (-k,k) `$16bfa` (`$172ce`). A flag of 0 skips the routine; a flag of 255
   (the `bmi` at `$1694a` and its three siblings) still advances the corner's cursor and projects its vertices but appends no
   list entry, because the neighbouring cells' polygons share those vertices. The 255 values occur only in the four corner
   flag positions (1, 4, 7, 10). In the extension routines a nonzero flag is just "run".

Each arm and corner keeps its own cursor (A0 height-grid pointer, the 16.16 accumulators D0..D2 and the A5 record
pointer) in a 20-byte block (`$17224`, `$17238`, `$1724c`, `$17260` for the arms, `$17274`, `$17288`, `$1729c`, `$172b0` for the
corners) that advances one ring a call. A list entry is a 16-byte cell record at `$12cfa + 3360 + 16 x + 336 y`; a record's
vertex slots are shared with its neighbours. The table `$17170` (8 bytes a ring, read through `(A6)+` into `$16d9a`) is all
zero in the snapshots, and the tags `$17160` (0,0,0,100,200,300,0,0, written to the corner cells' record +12) were not
observed, because the records are recycled before `$19ce2`: their role is unknown.

Reach and shape: up to 8 cells out; 17 cells wide (x = -8..8) on the camera's row, 5 wide at ring 8, corners to (6,6). The
footprint is a half-plane in front of the camera snapped to 45 degrees of heading, plus a wedge to one side behind it
(`scan_order.png`: numbers are positions in the list; heading 0 faces +y, 256 faces +x, inferred from the footprints). The
exact heading enters only the projection (step vectors `$158f4`), not the scan, and the camera position not at all
(the code reads only the `$12c80` pointer).

| check | script | result |
|---|---|---|
| the model's list against `$18f02` at `$19ce2`: 40 headings at camera cell (50,50), 0..992 step 32 plus 5, 77, 131, 300, 511, 700, 899, 1001 (poke `$12c98` at `$14e00`), and 6 poses at cells (30,45), (70,30), (34,59), (79,20), (60,65), (50,50) (poke `$12c60`/`$12c64` at `$14e00`, heading at `$18304`) | `py/scan/gate_scan.py` | 6900/6900 cells in order, 46/46 headings identical |
| broken-model control: last `$17140` word 2 to 3 | `gate_scan.py --break` | 6405/6900, 0/46 |
| projection and outcode check at other headings (poke `$12c98`, snapshot at `$1835a`) | `py/pipeline/proj_check.py` | 190/190 at 100, 300, 640, 899 (48, 55, 80, 61 behind the camera) |

`bash reversing/midwinter/py/scan/run.sh` captures everything fresh and prints these lines (gate `scan`). The model's three
tables are literals copied from RAM, so the gate proves the control structure and the octant formula, not the table
values. The projection check takes the game's own camera-space records as input, as in section 2. A heading poked alone is
overwritten by the vehicle control when the position is also poked (`$128b2` reloads it from character record +46;
`$13d8e` and `$14060` compute it for other vehicles), hence the later poke at `$18304`. A camera position off the island
(cell (20,70)) ended the run in other code, and the map edge (cell 0 or 99) is untested.

## 6. Open

1. The cell scan's remaining parts (section 5a covers the list): the cell records' payload (record +8, +10, +12: the
   records are recycled before `$19ce2`, so read them from a snapshot at `$1835a`), the corner tags `$17160`, the scan at the
   map edge, and whether the nearer-first inversions show on screen.
2. Vertices at other poses: headings are done for the projection stage (section 5a); other vehicles write the pitch and scale words (`$13078`, `$14530`, `$13b6e`).
3. Triangle build, clipping and the polygon rings (`$17444`, `$17fa0`, the four builders, `$17e94`): compare a model's
   headers, entries and edges with RAM at `$19ce2`.
4. Objects: the shape format `$1dd14` reads (from `$1de30` on), the object table `$1d288`/`$1d41a`, and what `$122f0`
   checks.
5. The aim pick `$19e76`/`$19ec4`: it runs inside the fill only when `$12d3a` is 4 and ran 0 times here. Read: when
   the screen centre (`$17218`, `$1721a`) lies inside the polygon being filled it copies `$14132` to `$14134`, so the
   last polygon drawn under the centre wins. Drive a snipe to prove it (`ai.md` Open, the encounter's objects on screen).
6. A whole frame, sky and terrain and objects and mask, against the screen at the flip.

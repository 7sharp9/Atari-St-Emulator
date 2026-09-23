# Populous ST: the graphics pipeline

Addresses are runtime absolute (TEXT loaded at `$ad58`). "Verified" means reproduced
pixel-for-pixel by `py/pop_render.py` against the emulator's own frame buffer; "code-read" means
taken from the disassembly and not independently exercised.

## Summary

- The play-field is a **fixed 8x8 window of pre-drawn isometric blocks**. There is no projection
  maths beyond `x = 16*(col-row)`, `y = 8*(col+row) - 8*height`. Each cell draws one 32x24 masked
  block chosen from 70 per land. Slopes are separate block graphics chosen from the corner
  heights (`$c0ee`), not rasterised.
- The frame is rebuilt from scratch every frame: a 32000-byte backdrop copy, then terrain, a
  sprite list, the minimap overlay and the status panel, into the back buffer. The buffers are
  swapped by writing the shifter base register directly.
- All graphics are plain 4-plane ST words with a 1-bits-transparent mask word. There is no
  blitter use (the ST blitter is never touched) and no palette cycling. Water animation is a
  two-frame block swap.
- `pop_render.py` rebuilds the whole 320x200 frame from RAM alone (map and entity tables, plus
  the asset files). It matches the emulator at **100.000% of pixels on 12 of 12 test frames**
  (details in "Verification").

## Memory map for graphics

| address | size | content |
|---|---|---|
| `[$3c51e]` (`$3f560` here) | 33600 | LAND block sheet, 70 x 480 bytes, reordered by `$1499a` |
| `[$3d534]` = `[$3c51e]+$8344` | 23520 | SPRITES0.DAT, 147 x 16x16 |
| `[$37e7c]` = `[$3d534]+$5be4` | 8320 | SPR_320.DAT, 13 x 32x32 |
| `$2360c` (DATA/BSS) | 4400 | FONT.DAT, 110 x 8x8 |
| `$150e2` (inside TEXT) | 24 x 128 | opaque 16x16 panel icons |
| `$16b8e` (inside TEXT) | 64 | 32x16 diamond outline for the EOR highlight |
| `[$3afd8]` (`$f8000`) | 32000 | backdrop: QAZ.PIC + minimap + mode highlights (= boot Physbase) |
| `[$3c4ce]` / `[$3c4d2]` | 2 x 32000 | displayed / draw screens, `$4f500` and `$57200`, swapped each frame |
| `$36e78` | 64x64 bytes | block map: block index per cell |
| `$33be4` | 64x64 bytes | cell base altitude (0..n) |
| `$34be4` | 65x65 words | corner heights (the terrain model; stride `$41` words) |
| `$3c522` | 64x64 bytes | overlay block per cell (buildings, trees, rocks, ruins) |
| `$37fd4` | 64x64 bytes | entity map: entity number (1-based) occupying the cell |
| `$3b278` | `$16` x n | entity records (count `$3c4e2`; numbers >= `$d1` are special objects) |
| `$3b00c` | 8 x n | per-frame draw list `{x, y, sprite, entity}`, count `$37eb2` |

The single `Malloc($ff52)` at `$aec4` is **86 bytes too small** for the three files
(`$8344+$5be4+$2080 = $ffa8`). The screen pair is allocated next (`$14af6`: `Malloc($fb00)` rounded
up to 256), so the log screen at `$4f500` overlaps the last 8 bytes of SPR_320 sprite 12. The
snapshot confirms 3 differing bytes at `$4f500`. The effect is invisible (bottom-right corner
pixels of one special-object frame).

## Palette

The game sets its palette once at boot: `$af12` loops `Setcolor(i, $22880[i])` for i = 0..15
(XBIOS 7). The same 16 words are in `$ffff8240` in every gameplay snapshot:

```
0 $000  1 $222  2 $333  3 $444  4 $555  5 $666  6 $310  7 $420
8 $500  9 $530 10 $550 11 $250 12 $140 13 $131 14 $124 15 $136
```

The four lands share this palette; they differ only in block art and minimap colours. The LORD
screen (`$1d30e`) loads its own 16 colours from LORD.PIC's header into `$37f92` and applies them
with Setcolor.

## Asset formats

All packed files use `[u32 packed_len incl. 8-byte header][u32 unpacked_len][LZ stream]`,
depacked in place by `$15054` → `$2019a` (it reads the packed data to the end of the destination
buffer, then unpacks forward). Decoders are in `py/pop_assets.py`. Every decode was byte-compared
with the RAM copy the game loaded (LAND0, SPRITES0, FONT identical; SPR_320 identical except the
overlap above).

**Masked image convention** (blocks, sprites, font): each 16-pixel group is `mask, p0, p1, p2,
p3`. Mask bit 1 = keep the screen pixel (transparent), and `screen = (screen & mask) | plane`.
Pixel colour = `p0 | p1<<1 | p2<<2 | p3<<3`.

### LAND0..LAND3 (`$14be8` loader)

A 0x72-byte header, then a packed 33600-byte block sheet.

| hdr off | len | RAM dest | consumer / meaning |
|---|---|---|---|
| 0x00 | 2 | `$37eb0` | game parameter (1/8/8/4); read at `$e0f4`, `$eac8`, `$ecae` (not graphics) |
| 0x02 | 22 | `$24998` | 11 words, added to walker strength at `$e8b8` (not graphics) |
| 0x18 | 22 | `$3b20c` | 11 words, read at `$e66c` (not graphics) |
| 0x2e | 22 | `$3b248` | 11 words, copied and sorted into `$3b25e` (`$14d96..$14e62`); `$3b25e` is the rank ladder the shield matches (`$d4fa`) |
| 0x44 | 22 | `$3c4fe` | 11 words (50,100,200,...,2000), read at `$1096e` (not graphics) |
| 0x5a | 6 | `$3c4e8` | 3 words (100,1000,3000), read at `$10c5e..$10c96` |
| 0x60 | 16 | `$21ea0` | **minimap colour per block shape 0..15**; `$14d6a` copies it to `$21eb0` so shapes 16..31 get the same colours |
| 0x70 | 2 | local | sprite-set digit; reloads `spritesN.dat`/`spr_N20.dat` via `$14e98` if it differs from `$22594` (0 in all four lands) |

Semantic names for the non-graphics fields belong to the people/AI docs.

The **block sheet** holds 70 blocks, 32x24 pixels, 480 bytes each (24 rows x 20 bytes). The file
stores each row word-interleaved `mL,mR,p0L,p0R,p1L,p1R,p2L,p2R,p3L,p3R`. After loading, `$1499a`
reorders every 20-byte row to `mL,p0L,p1L,p2L,p3L, mR,p0R..p3R`. The reordered sheet equals RAM
`[$3c51e]` byte for byte. Block `n` starts at `[$3c51e] + 480*n`.

Block index meaning (LAND0; see `land0_blocks.png`, and `land1..3_blocks.png` for desert, snow
and lava):

| blocks | content |
|---|---|
| 0 / 16 | sea, frames A / B (lava in LAND3) |
| 1..14 | slopes, shape = bitmask of raised corners (see "Block selection") |
| 15 | flat land (drawn one level lower; its art is one level tall) |
| 17..30 | the same 14 slope shapes at sea level (shoreline versions) |
| 31, 32 | flat farmed land, side 0 / side 1 (`$18206` counts block `$1f+side`) |
| 33..44 | settlement stages hut → castle (overlay map) |
| 45 (`$2d`) / 46 (`$2e`) | ankh / skull markers (papal magnets, cells `[$3c4ca]` / `[$3d526]`) |
| 47..49 | rocks; 50..52 trees; 53 swamp-ish flat; 54..65 ruins and burning settlements; 66 flat |
| 67..69 | empty |

`$2f` (47) is also a special value in the block map: `$c0ee` never overwrites it, and `$18198`
reports it as "rock" (return code 2).

The header's 16 minimap colours in LAND0 are `0e 0c 0b 0b 0c 0c 0b 0b 0d 0d 0c 0c 0d 0d 0c 0c`
(sea = 14, land = 11/12/13 by shape). Entries 32..46 of `$21ea0` are `$19`; `$c27a` replaces `$19`
with `$21ebf` (= 2).

### SPRITES0.DAT: 147 sprites, 16x16 masked, 160 bytes each

Each row is `m,p0,p1,p2,p3` (words); sprite `n` is at `[$3d534] + 160*n` (`$16916`, `$14540`).
See `sprites0.png`. Index use found in the code:

| index | use (where) |
|---|---|
| 0..15 / 16..31 | walker, side 0 / 1: `2*dir + [$3b222]` (dir 0..7 from `$21ee8`, `+$10*side`) |
| 32..63 | the same with `+$20` when the record's long `+14` is non-zero (knight form) |
| `$40..$43` (64..67) | settled-walker flag `$40 + [$3b222] + 2*side` (`$146b6`) |
| `$44` (68) | selected-walker shield marker, also pointer 0 (`$148ee`) |
| `$45` (69) | mana marker on the power rail (`$da52`) |
| `$4a/$4b` | leader marker, side 0 / 1 (`$14972`) |
| `$4c/$4d` (76/77) | earth side-wall tiles, front / right face (`$144fc` / `$144b4`) |
| 78..83 | mouse pointers (via `$22ac8`) |
| `$54` (84) | crosshair: minimap view marker (`$b7a8`) |
| `$5d..$6c` | bit-4 state walkers: `$5d + (ctr&3) + 4*side (+$10)` (swimming, inferred from art) |
| `$65..$6c` / `$7d..` | bit-5/6 state (`$d796`): `$65/$7d + 2*side + [$3b222]` (fighting, inferred from art) |
| `$69..$6c` | bit-7 state: `$69 + (ctr&3)`, fire (`$14644`) |
| 145, 146 | misc ("SPAT" text tile) |

### SPR_320.DAT: 13 sprites, 32x32 masked, 640 bytes each

Each row is `mL,p0L..p3L, mR,p0R..p3R`, with no reordering. Drawn by `$169e8` for draw-list
entries whose entity number is >= `$d1`, at `(x-8, y-16)`. The frame is the record's word `+6`.
Frames 0..4, 5..8 and 9..12 are three animated special objects (`spr_320.png`); which game
object each is belongs to the people doc.

### FONT.DAT: 110 glyphs, 8x8, 40 bytes each

Each row is 5 **bytes** `m,p0,p1,p2,p3`. The glyph for character `c` is `$2360c + 40*(c-$20)`.
Glyphs 0..94 cover ASCII `$20..$7e` (lowercase codes render red capitals, uppercase yellow),
and 95..109 are UI fragments. See `font.png`.

`$180b6(screen, x, y, str)` draws text. `x>>3` selects the byte column, so text sits on an 8-pixel
grid, with `(x&~15)/2` for the group and `+1` if bit 3 is set. The character cell is masked
per byte. `\r` or `\n` moves down 8 rows (`$500`). The routine hides the pointer around the
draw (`$16cf0`/`$16d20`), because it is also used on the displayed screen.

### Other pictures

- **QAZ.PIC**: packed raw 32000-byte screen, the in-game backdrop (`qaz.png`). Loaded by `$14b50`
  straight into `[$3afd8]`.
- **LORD.PIC** and **LOAD.PIC**: a 128-byte NEOchrome-style header. Bytes +4..+35 are 16 palette
  words, the filename field reads `"        .   "`, then the packed 32000-byte picture.
  `$14f54` reads 4 bytes, the 32-byte palette into `$37f92`, and discards 92 bytes, then depacks
  the picture into the draw screen. LORD.PIC has STe-looking palette values (`$089`, `$2aa`);
  the ST uses only bits 0-2 of each nibble. See `lord_pic.png`. LOAD.PIC is used only by DEMO.GOD
  (`load_pic.png`, own palette).
- **DEMOBACK.NEO** (DEMO.GOD): despite the name, it has no NEO header and is a bare packed 32000
  bytes. `demoback_gamepal.png` uses the game palette; the intro's palette was not traced.
- **MOUTHS.PIC**: 6 frames of 48x35, opaque, 840 bytes each. Each row is 12 words in plane-major
  order (`p0g0 p0g1 p0g2 p1g0 ...`). `$1500a` loads it into `$38fd8`, the buffer the map
  generator uses as scratch at other times. `$1db1e(screen, xq, y, rows, frame)` blits at byte
  offset `4*xq`. `$1d3ec` draws frame 5 (eyes) at (128,75) and `$1d4f2` draws the talking mouth
  at (144,135) over LORD.PIC (`mouths_lordpal.png`).
- **Panel icons at `$150e2`**: 24 opaque 16x16 icons in TEXT, 128 bytes each (4 plane words per
  row). `$167e8(screen, xg, y, n)` draws at x = 16*xg. Icons: 0 ankh, 1 skull, 2..11 rank
  weapons, 12..23 frame and bar pieces (`icons_150e2.png`).

## Frame composition (`$b510` main loop, once per frame)

```
$b6a4  [$3b222] ^= 1                        water/walker animation phase
$b6b6  $149ea : copy 32000 bytes [$3afd8] -> [$3c4d2]
$b6bc  [$37eb2] = 0                          empty draw list
$b6ea  $da52  : mana marker
$b6fc  $14364(cx=[$37e7a], cy=[$249ae])     terrain + walls; walkers appended to $3b00c
$b704  draw list: entity < $d1 -> $16916 16x16 at (x,y); else $169e8 32x32 at (x-8,y-16)
$b766  $16916 sprite $54 at (64+(cx+3)-(cy+3)-3, ((cx+3)+(cy+3))/2-3)   minimap view marker
$b7c2  $12f84 (special objects) + $db4c (AI; plots minimap dots)
       [or, if $3b274|$3b276: the $b7e2 loop plots dots for every entity]
$b8fc  $d482  : shield / status bars
$b902  $16ed8 : wait for VBL flag, swap buffers
```

All drawing goes to the draw screen `[$3c4d2]`, except the mouse pointer (below).

### Double buffering (`$16ed8`)

`$16f0a` spins until the VBL handler sets `$16cea`. `$16ed8` then swaps `[$3c4d2]` and
`[$3c4ce]`, and writes the new displayed base with `lsr.w #8,D0; move.l D0,$ffff8200`. That one
long write fills `$ff8201` (high byte) and `$ff8203` (mid byte). XBIOS `Setscreen` is used only
at level setup (`$b488`: `Setscreen($3afd8,$3afd8,-1)` while the backdrop and minimap are
built, then `$14a10` copies the backdrop to both screens, then `Setscreen(-1, [$3c4d2], -1)`).
In play the displayed base alternates between **`$4f500` and `$57200`**. `$f8000` is the
backdrop, not a display buffer.

## The terrain renderer (`$14364`)

### Projection

`$142d6(D0=col, D1=row, D2=lift_pixels, D3=block)` computes the destination:

```
A0 = [$2287a] + 8*col - 8*row + 160*(8*col + 8*row) - 160*D2      ; screen-relative bytes
if A0 < 0: return                                                  ; whole block skipped (top clip)
A0 += [$3c4d2]; blit 24 rows x 2 groups, masked, from [$3c51e] + $1e0*block
```

`[$2287a] = $2858` is the offset of view cell (0,0): x = 176, y = 64. The screen position is:

- `x = 176 + 16*(col - row)` (always a multiple of 16, so the block blit never shifts bits)
- `y = 64 + 8*(col + row) - lift`

A block is 32 pixels wide and 24 tall. Its top face is a 32x16 diamond, so one grid step is
(+16,+8) along columns and (-16,+8) along rows. **One altitude level is 8 pixels.**

### Per-cell draw (row-major: rows 0..7 outer, columns 0..7 inner, far to near)

```
b = blk[cell];  if b == 0 and [$3b222] == 0: b = $10          ; sea shimmer: blocks 0/16 alternate
lift = 8*hgt[cell]           ; draw block b
lift += 8;  if ovl[cell]: draw block ovl[cell] one level higher
if ent[cell] and [$2287a] == $2858: $1457e(...)              ; walker -> draw list (not drawn yet)
if cell == [$3d526]: draw block $2e ; if cell == [$3c4ca]: draw block $2d   ($2080 = none)
```

Walkers are added to a list and drawn after the whole terrain, so terrain never hides a walker.
Blocks overdraw in painter's order.

### Earth side walls

After the grid, the visible edges get earth skirts from 16x16 sprites drawn word-aligned by
`$14540`:

- **Right face:** for each row r, stack `hgt[(7,r)]` copies of sprite 77, 8 rows apart
  (`-$500`), starting at `[$2287a]+$2840 + r*$4f8`. That is the position of the right half of
  cell (7,r).
- **Front face:** for each column c = 7..0, stack `hgt[(c,7)]` copies of sprite 76 under the left
  half of cell (c,7) (`-$508` per column).

### Block selection from the corner heights (`$c0ee`, code-read)

For each cell (x,y), with corners at `$34be4 + 2*(x + 65*y)` (words, stride `$82` bytes):

```
avg = (c00 + c10 + c11 + c01) >> 2
shape = (c00>avg) | (c10>avg)<<1 | (c11>avg)<<2 | (c01>avg)<<3
if avg != 0 and shape == 0:  avg -= 1, shape = 15          ; flat land block, one level down
if avg == 0 and shape not in (0, 15): shape += 16           ; shoreline slope set
hgt[cell] = avg;  blk[cell] = shape  (unless it is $2f);  shape 0 clears ovl[cell]
```

The block index therefore encodes which corners are raised, and `hgt` is the base level it
sits on. Block 15 is drawn at `avg-1` because its art is a full level tall.

### Walker placement (`$1457e`, verified)

The walker routine receives `D0=col, D1=row` and `D2 = 8*hgt + 8`. It computes
`x = 16*(col-row)` and `y = 8*(col+row) - D2`. The entity record is at
`$3b278 + (n-1)*$16`, and its type byte `+0` selects the case:

- **Stationary** (type 1, or bit 3/5/6/7 set). Position `(x+$c0, y+$40)` (bit 7 uses `x+$b8`).
  Sprite as tabled above.
- **Moving** (type 2, or bit 4 set). `w10` = map step (-65,-64,-63,1,65,64,63,-1) and
  `w12` = progress 0..7. The table at `$146fe..$1486a` picks `(dx,dy)`, one of
  (0,-2) (2,-1) (4,0) (2,1) (0,2) (-2,1) (-4,0) (-2,-1), and the direction sprite base `0,2,..,14`.
  - Position: `x + dx*w12 + $b8`, `y + dy*w12 + $40 + (hgt[cell]-hgt[cell+w10])*w12`
    (the height difference is taken as a signed byte), plus 4 when the cell's block is not 15.
  - When `w12 > 4` and the step leaves the 8x8 window, the walker is **not drawn**
    (edge tests against col/row 0 and `$70`).
- `$148ee` appends `{x, y, sprite, n}`. If n is the selected entity `[$3c4c6]`, it also appends
  sprite `$44` at x+8. If n is its side's leader (`$3b226/$3b236 +0`), it appends `$4a+side` at
  x+8.

### Scrolling

The view origin (cx `$37e7a`, cy `$249ae`) is a cell coordinate in 0..56 (`$38`), so the window
is always fully on the 64x64 map. Keypad scan codes in `$37eae` step it by one cell per frame
(`$baf0` switch):

| key | effect |
|---|---|
| `$67` | cx-1 |
| `$68` | cx-1, cy-1 |
| `$69` | cy-1 |
| `$6a` | cx-1, cy+1 |
| `$6c` | cx+1, cy-1 |
| `$6d` | cy+1 |
| `$6e` | cx+1, cy+1 |
| `$6f` | cx+1 |

`$66` goes to `$b9fa`, which tests the mouse near (311+,10..20) and prints `$21478` "CHEAT". There is no sub-cell scrolling.

## Minimap (the book, top-left)

- **Projection:** `$166b2(cell, colour)` plots map cell (x,y) at screen
  `(64 + x - y, (x + y) >> 1)`, a 128x64 diamond. It uses `$16772(screen, x, y, colour)`, a
  single-pixel 4-plane set with 320x200 clipping.
- **Land:** `$c27a(x0,y0,x1,y1)` paints `$21ea0[blk]` into the **backdrop** `[$3afd8]`, so land
  persists between frames. `$132ca` repaints single cells after terraforming.
- **Dots:** dots go onto the draw screen every frame, from inside the AI pass (`$e926`, `$ec26`,
  `$ec9e`). **They alternate by frame parity:**
  - Settled walkers (type bit 0) are plotted when `[$3b222] == 0`, in colour
    `$21e0c[side*46 + 32]` (5 for side 0, 1 for side 1).
  - Moving walkers (bit 1) are plotted when `[$3b222] != 0`, in colour 15 (side 0) or 8 (side 1).
  - Opponent dots are shown only if `$219b0` is set.
  - `$10684` flashes one entity with `8 + 7*[$3b222]`.
- **View marker:** sprite `$54` (crosshair) at the window centre, see `$b766`.

## Power rail, shield and bars

- **Mana marker** (`$da52`). Level `k` is the first index with `mana <= $21984[k]`, with
  thresholds -250, 10, 200, 2500, 5000, 7500, 10000, 40000, 80000, 160000, 1999999. Mana is the
  player's side record long `+12`.
  - Sprite `$45` is drawn at `(160 + 16(k-1) + 2f, 8 + 8(k-1) + f)`, where
    `f = 8*(mana - th[k-1]) / (th[k] - th[k-1])` (0..7), so it slides down the diagonal rail of
    power icons.
  - Above the last level it is drawn at (311,87).
- **Side bars** (`$d918`, both always drawn). `$16834(screen, xcol, ybottom, total, filled,
  colour)` draws a 4-pixel column (byte mask `$3c`, x = 8*xcol+2..+5).
  - It draws `filled` rows in `colour` from `ybottom` upward, then `total-filled` rows in colour 2.
  - Left bar (xcol `$20`, colour 15) is side 0; right bar (`$27`, colour 8) is side 1.
  - Each is 32 rows ending at y=31, with `filled = long(+8)*31/50000 + 1`, or 0 if the value is 0.
  - `$168aa` is the per-row plane writer.
- **Shield** (`$d482`, only when `[$3c4c6]` selects a live entity; verified with two poked
  selections). If the selection is dead, `$d4c0` clears it and **skips the side bars for that
  frame**. The shield quarters are:
  - **Top-left** (272,4): icon = side (ankh / skull).
  - **Top-right** (288,4): icon `k+1`, where `$3b25e[k] == record byte +3` (rank weapon).
  - **Bottom-left** (272,22): the walker's sprite. For a settled walker it is instead flag sprite
    `$40+[$3b222]+2*side` at (268,22).
  - **Bottom-right**: two 16-row bars at xcol `$24/$25`, bottom y=37:
    - **Fighting** (bit 3): the good/evil strength share, colours 15/8.
    - **Settled**: `$18206` settlement score `*16/$131` in colour 10 (full for `$bea` = castle),
      then `strength*16/score` in colour 12.
    - **Otherwise**: strength `w4`, split `/$100` and `%$100/16` in colour 9, or `/$400` and
      `%$400` in colours 10/9 above `$1000`.
- **Mode highlights**: `$16b26(screen, a, b, off)` EORs the 32x16 diamond at `$16b8e` into bit
  plane 0 only, at `screen + a*$508 + b*$4f8 + off`. `$b510` applies four at game start to the
  backdrop (`(0,3,$5f90) (0,4,$5f90) (6,1,$4b00) (4,3,$4b00)`), and the click handlers toggle
  others (`$c4f2..$d254`).

## Mouse pointer (VBL, `$16d32`)

`$16bd8` installs `$16d32` in the first free `$456` VBL-queue slot. Each VBL it does four things:

- latches the mouse buttons (`$16c58`)
- if the pointer is not hidden (`$16ce8 == 0`), restores the 16x16 background saved at `$2474e`
  (`$16dac`), then draws the pointer on the **displayed** screen `[$3c4ce]` (`$16de2`)
- sends IKBD `$0d` (interrogate mouse position)
- sets the flip flag `$16cea` and bumps the tick count `$16cec`

The pointer is sprite `$22ac8[$2165c]` (table: 68, 78, 80, 81, 79, 83, 82; `$2165c` is set to
`3*side+1` at game start). It is drawn at (`$24748`, `$2474a`). Rows are clipped when y > 184,
and the right word is dropped when x > 304.

`$16cf0` / `$16d20` form a nesting hide/show counter. `$16cf0` restores the saved background
before hiding, so direct writes to the displayed screen (`$14a10`, `$16b26`, `$180b6`) are
safe.

## Mouse input: clicks, the command panel and the land cursor

The IKBD runs in absolute mode. The MFP 6 handler `$1ff8a` assembles the 6-byte `$f7` report
into `$2474c` (buttons: bit 2 left, bit 0 right) and `$24748`/`$2474a` (pointer x/y). The VBL
latch `$16c58` turns a press into `$3d528 = 0` (left) or `$3c4d6 = 0` (right) and copies the
pointer into `$3c518`/`$3c51c`; every hit test reads that latched copy. A latch at 1 is idle; 2
means "consumed, wait for release" (set by the panel handler and by a right-click lower), and the
main loop turns a consumed 0 back into 1 (`$bb8e`). So one click is one action; a held left
button in land mode re-latches every frame and raises repeatedly.

Per frame, `$b510` calls `$119e6` (land input) when `$21d50 & $e`, `$d3ee` (entity pick in query
mode) on a press, and `$c3e2` (panel) on a press, with arg = left button. `$c3e2` and `$119e6`
work in diamond coordinates `u = y + (x>>1) - 32`, `v = y - (x>>1) + 32` (`divs` truncates):

| test | region | action |
|---|---|---|
| `0 <= u,v < 64` | minimap | view origin `($37e7a,$249ae)` := (u-3, v-3), clamped 0..56 |
| `u > $112` | icons right of the land view | icon ((u-$110)/16, (v-$20)/16) |
| `v >= $92` | command panel, lower left | icon ((u-$60)/16, (v-$90)/16) |
| otherwise | land view | nothing in `$c3e2`; `$119e6` acts |

Command panel (`$c65a..$d05c`, dispatch on the column at `$d00e`):

| (col,row) | icon | effect |
|---|---|---|
| (0,0) | flood | cmd 14/4 |
| (1,0) | armageddon | cmd 14/3, not in paint mode |
| (1,1) | volcano | cmd 6 at the view origin |
| (2,0) | earthquake | cmd 3 at the view origin |
| (2,1) | knight | cmd 14/5 |
| (2,2) | swamp | arms the land cursor: `$21d50 = ($21d50&3)\|8`, pointer 5; needs mana > 5000 and power bit $10, or paint mode |
| (3..5, 0..2) | scroll arrows | view x -1/0/+1 by column, y -1/0/+1 by row; the centre (4,1) centres on the query entity |
| (3,3) (4,3) (5,3) (4,4) | walker modes | cmd 14/1 arg 0 go to papal magnet, 1 settle, 2 gather, 3 fight |
| (6,0) | query | `$21d50 = 1`, pointer 0 |
| (6,1) | land | `$21d50 = 2` (left raise, right lower), pointer `3*side+1` |
| (6,2) | papal magnet | arms the land cursor: `$21d50 = ($21d50&3)\|4`, pointer `side+2` |
| (7,0) | go to leader | left: view on the leader and query it (`$da28`), or on the papal magnet if there is no leader; right: view on the papal magnet |
| (7,1) | go to battle | view on the next entity of either side with flag bit 3 (fighting), and query it |
| (8,0) | go to knight | left: the next own knight (+14 set); right: the next own settlement; query it |

Icons right of the land view (`$c4a4..$c656`): (0,0) cmd 14/7 OPTIONS FOR EVIL (arg = left
button), (0,3) the music-note icon toggles `$21ffc` (no reader besides the save/restore at
`$1d18e`; music on/off is *inferred*), (0,4) "FX" toggles `$21920` (the VBL plays the `$36d02`
sound effect only while it is set), (1,1) cmd 14/8 GAME SETUP, (1,3) "zZ" cmd 14/6 pause
(toggles `$3b274`), (2,2) the telephone, cmd 14/2 send message. `panel_regions.png` outlines
every region over a game frame (numbers = order of the two lists above).

**Land cursor `$119e6`.** It acts only if armageddon is off, `$3e <= u <= $10a`,
`-$40 <= v <= $88`, `x >= $40`, and (one of your entities is in view, `$3d54e` bit 0 from the
sprite pass `$145d2`, or `$21d50 != 2`, or paint mode). The screen column `c = (x-$38)>>4`
selects a diagonal of corners from the view origin: 9 for c = 8, `c+1` starting at local
(0, 8-c) for c < 8, `17-c` starting at (c-8, 0) for c > 8, each next corner +1,+1. Corner k is
drawn at `sy + 16k - 8*height`, with `sy = $48 + 8*|c-8|`, and the **last** corner with that y
`<= pointer y + 4` is the one under the cursor (`$36e72/$36e76`), highlighted at y-3. On a
press: armed swamp posts cmd 4 and armed magnet cmd 5 at cell (cx-1, cy-1), each then disarming;
otherwise a left press posts cmd 1 (raise) at the corner. A right press posts cmd 2 (lower) when
`$21d50 == 2` and "only build up" is off. With "cannot build" (`$219b2&4`) nothing is posted;
with "build near towns" a corner above sea level needs an own settlement in view.

Proof (`py/popdrive.py`, which implements all of this and plans clicks from a snapshot): from
`game_start.snap` a minimap click at (58,12) set the view to (6,12) as predicted; a left click at
(208,104) raised corner (11,16) with **134/134** corner changes equal to the injected command
(`verify_cmd.py`) and none elsewhere; a right click there lowered it exactly as
`popgen.lower_pt`; the magnet icon then a click on corner (12,17) moved the papal magnet to
cell (11,16) for 200 mana; and 13 icon clicks (the four modes, query/magnet/land, three scroll
arrows, pause, FX, music) each changed exactly the variables the table predicts, **13/13**.

## Blitter routines (every one is a CPU routine)

| routine | draws |
|---|---|
| `$142d6` | 32x24 masked terrain block, 16-px aligned, top-clipped by skipping (hot: 12368 calls in 191 frames) |
| `$14540` | 16x16 masked sprite, word-aligned (walls) |
| `$16916` | 16x16 masked sprite at any x (`ror.l` shift, 2 words), clipped to 320x200, y<0 → skipped |
| `$169e8` | 32x32 masked sprite (3 words per plane row), same clipping |
| `$167e8` | 16x16 opaque icon from `$150e2`, x in 16-px units |
| `$16772` | set one pixel (clipped) |
| `$166b2` | minimap dot: cell → `$16772` |
| `$16834` / `$168aa` | vertical 4-px bar |
| `$16b26` | EOR diamond outline (plane 0) |
| `$180b6` | 8x8 masked text |
| `$1db1e` | 48xN opaque mouth frame |
| `$149ea` / `$14a10` | 32000-byte screen copies |
| `$16dac` / `$16de2` | pointer restore / save and draw |

**Correction to the per-frame call list:** these hot routines are **not** blitters.

- `$18198` returns a probe code (0 land, 1 off-map, 2 block `$2f`, 3 water).
- `$18206(side, cell)` is the settlement score over the 17 offsets at `$22b4e`, returning `$bea`
  for a castle.
- `$16702` is the RNG: `seed($3d52e) = (seed*$24a1 + $24df) & $7fff`.

## Verification

Every frame was rendered by `pop_render.py` from RAM and the asset files alone (`--files`: no
screen buffer is read). Truth is the emulator's finished draw buffer at the next `$16ed8` entry.

| frames | what was exercised | pixel match |
|---|---|---|
| `game_start`, `g90` (brief snapshots, next frame) | sea shimmer both phases; walker, flag and leader sprites; both dot phases | 100.000% each (64000/64000) |
| cx,cy = (55,53), (55,47), (8,4), each twice 0.2M steps apart | mountains up to several levels (walls), buildings, trees, rocks, walkers | 100.000% each |
| `sel6`, `sel12` (poked selection and both magnet cells) | shield: settled and walking paths, ankh/skull blocks, marker `$44` | 100.000% each |
| with `--pointer`, vs the displayed buffer after the flip and VBL | pointer included | 100.000% |

The draw list rebuilt by the Python port of `$1457e` equals RAM `$3b00c` on every frame.
"pre" snapshots are taken at `$14364` entry and "post" snapshots at `$16ed8` entry. Both are
needed, because the AI moves walkers after the terrain pass. Rendering from a post-AI snapshot
alone misplaces a moving walker by 2 px.

Not exercised: 32x32 special objects (entity >= `$d1`), the fighting-shield path, text
rendering in play, and the LORD/mouths screen live.

Reproduce (from this directory; the pre/post snapshot pairs live in `$POP_WORK` (default `M68000/scratchpad/pop/`, see README) under `agents/graphics/`):
`python py/pop_render.py $POP_WORK/agents/graphics/v5547_pre.snap out.png --post $POP_WORK/agents/graphics/v5547_post.snap --truth --files`.

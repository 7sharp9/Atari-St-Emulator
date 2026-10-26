# Midwinter: terrain

The island is not stored at the resolution it is drawn at. File `37.2` holds a 50 x 50 grid of heights for the whole
island; each time the 3D view needs ground, `$19962` refines that grid by five rounds of diamond-square subdivision into
a 100 x 100 grid centred on the player, at 32 times the file's resolution. The displacement each new point gets is a
hash of its four parents' seed words, not a random number, so the same place always gets the same hills. Three
post-passes then turn the generator's units into render heights, level the ground under buildings and shade every
cell's two triangles.

Proof: `py/terrain/gate_terrain.py` (fresh runs from `d_decisions.snap`, about 7 s) matches the model
`py/terrain/terrain_gen.py` against the game cell for cell: generator **70000/70000** cells over 7 windows (the natural
ski entry and 6 poked targets, no two grids alike), post-passes **10000/10000**. Every grid cell changes in both
calls; over the whole 1 MB RAM the generator model differs from the game only at the system timer `$4bc`, a VBL byte
`$637f` and the stack below A7. Dropping the building pads from the model breaks 475 cells.

| picture | what |
|---|---|
| `terrain_island.png` | file 37.2 after the first subdivision (`$1999a`): the whole island at 100 x 100, sea blue, land by height. Same coastline as the game's own map screen (`map.png`; visual check) |
| `terrain_local.png` | the 100 x 100 grid of `d_ski.snap` at the finest level, each cell's two triangles in the game's shading bytes |

`py/terrain/render_terrain.py <gen_in.snap> <d_ski.snap> <outdir>` draws both.

## 1. The cell and the grids

A cell is a longword. During generation it is `(height.w, seed.w)`; after `$1991a` it is `(height.w, shade.b, shade.b)`.

| where | size | what |
|---|---|---|
| `$4a104` | 50 x 50, rows of 200 bytes | file 37.2, loaded by `$19cac` (file number `$1b`, which the loader opens as 37.2: architecture.md section 5). Heights -515..7488, seeds 0..`$ff04` |
| `$404c4` (`$12ce2` holds it) | 100 x 100, rows of 400 bytes, ends at `$4a104` | the working grid: each subdivision's output, and the final grid the renderer reads |
| `$60000` | 50 x 50, rows of 200 bytes | the window copied out of the working grid before each zoom (`$2c20`) |
| `$66000`, `$66190` | 50 cells each | one output row's edge points (`$2ca6`); cleared to `-1` before each subdivision |
| `[$23064]`, `[$23068]` | 50 cells each | the centre points of this source row and the previous one, swapped after each row |

## 2. One subdivision: `$2ca6` and `$285a`

`$2c60` (and `$1999a` for the first round) clears the edge rows to `-1` and calls `$2ca6` 50 times, once per source row
`S` (and the row below it, `S'`). Each call writes two output rows of 100 cells:

```
C[i]  = mid(S[i], S[i+1], S'[i], S'[i+1])          i = 0..48   centres, into [$23064]
H[i]  = mid(C[i], Cprev[i], S[i], S[i+1])          i = 0..48   edge points on row S, into $66000
V[i]  = mid(C[i], C[i+1], S[i+1], S'[i+1])         i = 0..48   edge points between S and S', into $66194
out row 2r   = S[0] H[0] S[1] H[1] ... S[49] H[49]
out row 2r+1 = V[-1] C[0] V[0] C[1] ... V[48] C[49]
```

`mid(a, b, c, d)` is `$285a`, with `shift` = `$2305e`:

```
s      = a + b + c + d                  as 32-bit longwords, so a carry out of the seed sum reaches the height
seed'  = (s.lo ^ a.lo) & $3fff          a.lo is the first parent's seed
avg    = (s.hi as int16) >> 2
disp   = ((s.lo as int16) >> shift) * int16(avg * 8 + 5000) >> 16
height'= avg + disp                     16-bit wrap throughout
```

The displacement scales with the height of the point (higher ground gets rougher) and with a pseudo-random factor
that is the seed sum, so it is a pure function of the parents. `shift` is 4 on the first round and grows by one per
zoom, halving the amplitude each level: a fractal (diamond-square) refinement whose noise comes from the data.

The grid's edges read past the data on purpose or by omission, and the model reproduces it by working on a RAM copy:
`H[49]` is the cleared `-1`, `C[49]` is whatever the centre buffer held from the row before last, `V[-1]` is `$66190`'s
`-1`, and the last source row's `S'` is the 200 bytes after the source (after 37.2 on the first round, the stale tail
of `$60000` on the zooms). Those cells end up as sea or noise on the grid's border (bottom rows of
`terrain_island.png`, the frame of `terrain_local.png`).

## 3. Zooming to the player: `$19962`

```
$19962: level $19cd8 = 4, origin ($19cda, $19cdc) = (0, 0)
$1999a: shift = 4; subdivide file 37.2 into the working grid            whole island, 100 x 100
$199ec x 4 (level 4, 3, 2, 1):
    off = ((target - origin) >> level) - 25      target = ($19cd4, $19cd6); off -> $19cde/$19ce0 -> 12(A6)/14(A6)
    origin += off << level; level -= 1
    $2c20: copy the 50 x 50 window at off out of the working grid to $60000
    $2c60: subdivide it back into the working grid; shift += 1
```

The target is in finest-cell units: the island is 1600 cells across (50 file cells x 32), and the final grid is the
100 x 100 finest cells around the target. The window offset is not clamped: near the island's edge it reads outside
the working grid (the `$2c20` offset is a signed word added to `$404c4`).

`$19962` runs from three places:

- `$19954` (from `$125d8`, entering 3D travel): loads 37.2 with `$19cac`, then generates.
- `$152c0`, the re-centre, called by the per-vehicle movement handlers (`$13a46`, `$13ad2`, `$13e84`, `$14118`). The
  camera position `$12c60/$12c64` is in 1/`$200` of a cell; `$152c0` moves the target by the camera's even cell
  offset from the centre (`2 * (pos / $400) - 50`), puts the camera back at `$6400` (cell 50) plus its remainder and
  regenerates. It runs only while the latch `$14efa` is clear and sets it; what clears the latch is not read.
- `$14cc0` (in `travel_3d_main` after `$14d48`, through `$19954`): role not read.

## 4. Post-passes

In the order `$1498a`, `$14cc0` and `$152c0` call them:

1. `$1cf1c` collects the records of the feature list at `$2a150` (variable-length: kind byte, x and y words at
   +2/+4) whose x and y lie within `$5a` of twice the target into a 16-byte object table at `$70010` (x.l, y.l, type
   pointer, ...; count-1 in `$1d418`, `$40` on `d_ski`). Its `$1ce4a` clears a 10,000-byte table at `$3ddb4` and
   fills it from tests on the grid's heights. It writes no grid cell (generator output and the grid at `$1991a`
   are identical, 0 cells differ). The record format and `$3ddb4`'s meaning are not decoded.
2. `$1991a`, heights: `h < 0` becomes 0 (sea), `h <= 9` becomes `(h + 1) * 24`, otherwise `h + 250`; the seed word is
   cleared. Low ground is stretched, so the shoreline is a step rather than a slope.
3. `$1d1d2`, building pads: for each object, the cell under it (column `(x >> 2).w >> 7`, row `99 - ((y >> 2).w >> 7)`) copies its
   height to its neighbours at `-400`, `+4` and `-396`, levelling the quad the object stands on (195 height words on
   `d_ski`).
4. `$197ec`, shading: each cell is split into two triangles along a diagonal that alternates by
   `(row + col + $157a8) & 1`. For each triangle `$1988e` takes the two height differences `dx`, `dy` along its edges
   and the light constant `L` = `$12c84` (`$100`):

   ```
   if height | dx | dy == 0: shade = 24                         flat sea
   shade = clamp(8 * (2L + 3dy) / isqrt(dx^2 + dy^2 + L^2), 0, ..) + 2, then 23 if >= 24
   ```

   `$198d8` is an exact floor square root (0 differences from `math.isqrt` over 200,000 inputs). Byte 2 of the cell
   is the first triangle's shade, byte 3 the second's. The render's 23 land shades are spread over the whole range on
   `d_ski` (2 to 23; 24 on the 1541 sea cells).

## 5. Who reads the grid

- The landscape render `$18304` -> `$16d9c` starts at the camera's cell `[$12c80]` (`$4521c` on `d_ski`: row 49,
  col 50, the centre), reads each cell's height `(A0)` and its two shading bytes `2(A0)`, and steps a row with `lea -400(A0)`.
  The projection and polygon fill are item 2 of the handoff, not decoded here.
- The map screen (`$14ce`) copies 37.2 to `$60000` with a zero row below it (`$15d6`), subdivides once with `$2c60`
  and draws the result with `$2bc2` (per-row handler `[$22d50]`): the map is drawn from the height grid, not stored as a
  picture (inferred from the code; the render is not matched).

## Open

- What clears `$14efa` (when the view re-centres), and the role of the `$14cc0` rebuild.
- The feature list `$2a150` and the object table `$70010` (`$1cf1c`), and the table `$3ddb4` (`$1ce4a`).
- The map render `$2bc2`: prove it against `map.png`.

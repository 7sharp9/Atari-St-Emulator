# virus: Virus (David Braben, 1988), first look

Virus is a flight game over a procedural landscape: the player's craft takes off from a launch pad, flies over
a patchwork of coloured tiles and shoots the infection. The version analysed is the Union crack (the
`A-HA #[no number]` disk), which adds a trainer menu in front of the game. Reached in the emulator: the Union
menu, the trainer menu, the title picture, the "Press R" page, the game on the launch pad at wave 1, and flight
(thrust held, a real input run). The game is hand-written 68000 (no compiled-C idioms were met in the parts read), so it is analysed from snapshots, `bp`/`hits` runs and `callcap`, not a decompile.

Evidence is of three kinds. **Gated:** a Python model matched against the emulator's own output with a match count,
a broken-model control and a command in `py/README.md`. **Poked:** a result reached through a labelled poke.
**Read:** from the code only, marked "(read)". A section says which of these it is.

Gates: `uv run python tools/gates.py run virus` (`gates.toml`, one gate that runs every model on the captures;
about 5 s). The captures are rebuilt with `bash reversing/virus/drive.sh` then `bash reversing/virus/py/capture.sh`.

| Doc | Covers | Proof |
|---|---|---|
| this file | provenance, the drive, memory map, landscape generator, object scatter and RNG, renderer, flight model, the seeder behaviour, landscape selection by wave | terrain 65455/65455 on three landscapes, objects 571/571 and 1774/1774, grid 330/330 on four frames, tiles 132/132, slope table 8064/8064, flight 119/119, seeder 447/447 |
| [`demo.md`](demo.md) | the attract mode and its autopilot | see that doc |
| [`behaviours.md`](behaviours.md) | the actor pool's behaviours (every enemy kind), wave completion and the per-wave spawn table, readers of the demo flag, the draw-list residue | wave ends 4/4 against the rule, residue poke 500/500, census of game 1 |

What stands out: the landscape is a 256x256 byte height map computed once per level from a sum of eight table
sines, and levels 1 and 2 are the same routine with four instruction words patched; each of the 110 grid vertices
costs two `divs`, not a reciprocal table; a tile's colour is the low two bits of its height byte (a cycling band),
not a slope; the ship's whole tick is half-way attitude smoothing, 1/64 drag, thrust of a matrix column divided by
8 and a gravity that rises with the wave.

## Provenance

- Zip: `A-HA #[no number].zip`, 194,827 bytes, sha256
  `4ab4367fe87cfb04a43dfdd9c5666caee44e0fd48b0ba95bc2466be34fbe72f7`. It holds `A-HA #[no number].msa`
  (416,256 bytes, sha256 `bc8b0af5c9bd2baa832f2898c8c8f3402f5ec06143c7f5dd69d24357199bdf75`); `tools/msa2st.py`
  gives a `.ST` of 737,280 bytes (80 tracks, 2 sides, 9 sectors), sha256
  `3b66c47c4f58f51538008470a6586547c39798d9dba0f17f6dd2e33114bb2c87`. Neither is committed. The work copy is
  `scratchpad/virus/aha.st` (`uv run python -I tools/msa2st.py <msa> scratchpad/virus/aha.st`).
- The boot sector is not executable. `AUTO\MULTI2.PRG` (1,024 bytes) is a raster-bar menu that waits in GEMDOS
  `Crawcin` for F1 or F2 and runs `BR.TOS` (F1, "VIRUS") or `TBR_.TOS` (F2, "ARKANOID 2", a 396-byte stub whose game is
  not on this disk).
- Files: `BR.TOS` (37,499 bytes, the loader that reads `VIRUS.TEX`), `VIRUS.TEX` (119,808 bytes, the game plus the
  Union intro and trainer menu; its header names the trainer authors), `DOH.IMG` (327,680 bytes), `DOH.PI1`,
  `BLADERUN.DT0/1/2`, `TBR_.TOS`, `READ_ME.TXT`. `DOH.IMG`, `DOH.PI1` and `BLADERUN.*` belong to other titles on the
  compilation and were not examined. The disk holds Virus only of the two games the owner named: Archipelagos is not
  on it.
- `READ_ME.TXT` says the crack removed the checksum routine that otherwise disabled gravity and slowed the game
  (the Union text; not checked here).

## Running it

From `M68000/`, with `scratchpad/virus/aha.st` in place:

```
bash reversing/virus/drive.sh        # cold boot to the launch pad, about 25 s; snapshots and PNGs in scratchpad/virus/drive/
bash reversing/virus/py/capture.sh   # flight snapshots, callcaps and REPL logs the gates read, about 30 s
```

`drive.sh` is the exact drive (`--disk-a aha.st`, trace off):

| step | input | steps run | result |
|---|---|---|---|
| boot | none | 20,000,000 | the `MULTI2.PRG` menu (it looks black: its bars are raster effects; it waits for a key in `Crawcin`) |
| F1 | `kbd 3b`, 60,000, `kbd bb` | 38,000,000 | the Union intro and fade; `g_trainer.snap` |
| trainer | 3,000,000, then `kbd 31` (N), 60,000, `kbd b1`, 1,500,000, five times | | three prompts (energy, lives, rockets), all answered NO; the first presses are sometimes lost, so five are sent and the extras ignored |
| Return | 3,000,000, `kbd 1c`, 60,000, `kbd 9c` | 1,000,000 | the title picture, `g_title.snap`, `title.png` |
| SPACE | `kbd 39`, 60,000, `kbd b9` | 10,000,000 | the "Press R to redefine keyboard controls / You are about to see Virus demo mode... / press SPACE to continue" page; `g_press.snap` |
| SPACE | `kbd 39`, 60,000, `kbd b9` | 6,000,000, then 3,000,000 | the game on the launch pad, wave 1, score 0; `g_game1.snap`, `g_game2.snap`, `pad.png` |

The title picture needs about 10M steps to load; with a shorter wait the second SPACE lands on it and the run stops
there. Run `drive.sh` again if the last snapshot shows the title.

`g_game2.snap` is a live game, not the demo the "Press R" page announces: with no input the frame stays still (the ship
sits on the pad), a `mouse move` moves a box of pixels around the ship, and `mouse down l` held for 40,000 steps is
thrust, which launches it. `capture.sh` holds the button and takes `fl/m_fire.snap` and four flight snapshots
`fl/f1..f4.snap` 900,000 steps apart (`flight.png` is `f1`). The game polls the keyboard and mouse through the ACIA
like any ST program; the only inputs used are the ones in the tables here.

### Running long (a chain of attract games)

A natural attract game is about 640M steps (flight about 560M, then 50M of game-over screens and title idle), 127 s wall at 4.8M steps/s with
the REPL and `bp 25ba0` (24 games in 51 minutes); `bash reversing/virus/py/chain/gate_chain.sh long 24` runs a chain.
A lineage is serial (game k+1 starts from game k's end), so it runs at one emulator's speed. Measured from `demo/S1b.snap`, 30M steps,
three interleaved rounds (`py/chain/bench.py`; load average 5 to 10 from other sessions), steps/s median: argv `N resume` 4.19M, REPL `s N` 4.27M,
`s 1000000` chunks 4.29M, `bp <unreached> N` 3.97M (about 7% slower: it runs `CensusStep`), `stserver` `run` 3.84M. Nothing in the CLI skips work:
headless, `Step()` renders nothing unless `ATARI_FRAME_DIR` is set, and the GC and tiering knobs are already rejected in `DEVELOPING.md`
"Performance". Independent emulators scale (`py/chain/par.py`, `s 30M` each, median aggregate): 1 process 4.32M steps/s, 2 8.50M, 4 14.5M,
8 22.95M (8 physical cores, shared with other sessions). That helps only for independent lineages, which need different start states (a poked
RNG seed at game 1, not tested). Skipping the 50M-step wait after a game over would save at most 8.9% and was not tried (it may change the carried
RNG advance). The remaining emulator-side lever is the mutable `Cpu` listed in `DEVELOPING.md` (hypothesis, about 15%).

## Memory map (RAM, 1 MB)

| range | contents | how known |
|---|---|---|
| `$c000..$27000` | game code, about 40,000 listed lines (`tools/disassemble.py --snap <snap> --all c000 28000`); the end of the text is not checked | listing |
| `$d0fa` | sine table, 1024 words, `int(32767*sin(2*pi*k/1024))` with entry 256 = 32766 | 1024/1024 (below) |
| `$d8fa`, `$d9fa` | arctangent and tilt tables read by the mouse routine `$254aa` | (read) |
| `$246ba` | 81-byte launch-pad colour table (values 4, 6, 14, 15, 22) | gated through the grid gate |
| `$270b0` | ship state: x, y, z, vx, vy, vz (words) | flight gate |
| `$270ce` | camera x, y, z (words) | grid gate |
| `$270d4` | ship orientation matrix (9 words in a 3x3 with stride 6) | flight gate (mouse run) |
| `$2706e`, `$27072` | the RNG, two longs | scatter gate |
| `$31d54` | actor pool: the wave's enemies and the player's rockets, up to 128 records of 20 bytes; count at `$32a3e` | seeder gate, `behaviours.md` |
| `$302f6` | object pool: shots, debris, falling infection, bombs, score pop-ups; 18-byte records, count `$32a3c` | (read), `behaviours.md` |
| `$276fc..$2f6f3` | the ten depth-bucket draw lists, `$ccc` bytes each | `behaviours.md` |
| `$32a2e`, `$32a32`, `$32a3a` | fuel, smoothed attitude (2 words), gravity | flight gate |
| `$32a4c`, `$32a4e`, `$32a50` | last built landscape, current landscape (0, 1, 2), wave number | below |
| `$32a58` | object map: one byte per cell, low 5 bits the object type | scatter gate |
| `$42a58` | height map: 256 x 256 bytes, index `(y << 8) | x` | terrain gate |
| `$5ab58` | slope table, longs (the signed index covers `$52b58..$62b57`; the byte `$62a58` is a flag in it) | slope gate |
| `$70000`, `$78000` | the two screen buffers (the shifter base alternates) | `snap_render.py` |
| `$2f6f6` | the 64x64 four-plane minimap in the HUD corner | (read) |

Names are in `virus.sym`.

## Main loop

`$23198` runs once per game frame (about 2.47 VBLs: 81 calls of each frame routine in 200 VBLs, from an
`ATARI_TRACE_EVENTS` census of the flight snapshot). In order: `$2617a`, `$1fa72` (the object pool, into depth buckets),
`$255c2` (the ship tick), `$2157c` (the actor pool), `$24098` (the landscape grid and the whole painter), `$23c8c`
(`Buckets_Reset`: the ten list ends back to their starts), `$24956`, `$232e6` (`InfectionQueue_Advance`, `demo.md`), `$20f82`
(`Wave_CheckComplete`: the wave ends when only unhatched chasers are left, `behaviours.md`), `$183f2`. The roles of `$2617a`,
`$24956` and `$183f2` are not established (role unknown).

## The landscape generator (gated)

The builder `$2336a(D0 = landscape)` fills the height map `$42a58` (256 x 256 bytes) once per landscape, then clears
the object map `$32a58` and scatters the objects, then draws the minimap. The height loop at `$23414..$23448` steps
x (D6) and y (D7) in `$100` units over the whole 16-bit range, calls `$245b8`, subtracts `$fd61` from the returned word,
shifts right by 3 and stores the low byte.

`$245b8` is the sum of eight terms from the 1024-entry sine table, with `S[a] = table[(a & $ffff) >> 6]` and
x, y the two 16-bit coordinates:

```
sum = S[x-2y] + S[3x+y] + S[3y-2x] + S[4x-5y]/2 + S[2y-5x]/2 + S[6x+5y]/2 + S[11x-7y]/4 + S[11x+11y]/4
```

(each term a sign-extended word, the sum a 32-bit value). The result is `base - (sum >> shift)`, clamped to at most
`$560`, and stored as `((h + $29f) & $ffff) >> 3`. Byte 255 is the clamp (water, white in `heightmaps.png`). The nine
by nine cells with x and y below `$900` are a launch pad: a constant byte `$d7` (height `$420`), with their colour from
the 81-byte table at `$246ba`, not modelled.

The three landscapes are one routine. `$2336a` writes alternative instruction words into `$245b8` at `$24680`,
`$24682`, `$24686` and `$24688`:

| landscape | shift | first `neg` | second `neg` | base |
|---|---|---|---|---|
| 0 | 7 | yes | no | `$520` |
| 1 | 6 | no | no | `$700` |
| 2 | 6 | yes | yes (when the height is not negative) | `$600` |

Proof, `py/virus_terrain.py`, which generates its own sine table (1024/1024 against RAM; the one entry that differs
from the truncated sine is index 256, 32766 for 32767):

- level 0 from `g_game2.snap` (no poke): 65455/65455 cells (the 81 pad cells are checked separately: all `$d7`, 81/81 in RAM).
- levels 1 and 2 from a **poked stub** (code at `$90000`: `moveq #n,D0 / jsr $2336a / rts` under `callcap`; the memory
  delta is applied to the snapshot): 65455/65455 each.
- broken-model controls: one constant shifted 29124/65455; level 1's variant on level 2's data 10965/65455.

Command: `bash reversing/virus/py/gate_all.sh` (or one line of it). `heightmaps.png` shows the three fields.

## Object scatter and the RNG (gated)

The RNG state is two longs `a` (`$2706e`) and `b` (`$27072`), seeded `$1234abdf` and `$5678e7f2` at `$2300a`. A draw
is: the random word is the high word of the old `a`; then `a = a + b` and `b = swap(old a)`. Checked by a `callcap` of
`$236f8` (a `$35f0cf9b` to `$fa6f2591`, b to `$cf9b35f0`).

The scatter `$236f8(D0 = count - 1, D1 = type)` draws a random word, takes it as the cell index (high byte y, low byte x),
and accepts the cell if its height is at most `$510`, not `$420`: then `map = (map & $e0) | type`. The builder calls it
nine times, in this order (draws, type): (289,4) (129,1) (257,5) (769,6) (385,3) (257,2) (113,7) (97,8) (81,9). Types
and the markers 10, 11 and 12 written afterwards (a `$b` pattern, a `$a` triple and `$236ae`'s `$c`) are not named: role
unknown.

Proof, `py/virus_objects.py`, with the **poked-stub** callcaps (levels 1 and 2 only; level 0's stub skips the clear):
landscape 1 model 571 cells, RAM 571, identical type at the same cell 571; landscape 2 model 1775, RAM 1774, identical
1774. The one model-only cell `$e6c6` lies on the `$b` marker pattern that the builder writes afterwards, so it is
overwritten (inferred, not run separately). The RNG state comes from the pad snapshot, so these counts differ from an
earlier run from another snapshot (563/563, 1778/1778); each is exact for its own state. Controls: first scatter one
draw short 1767/1774 identical; two types scattered in the other order 1586/1774. A one-draw shift moves every set
against the next only at the nine scatter boundaries, so the set comparison is blind to a pure shift except there;
the order control is the strong one.

## The renderer

`$24098` is both the grid builder and, through its tail, the painter. Gated parts first.

**Grid and projection (gated).** The camera is read from `$270ce`. The origin cell is `D6 = (camx - $480) & $ff00`,
`D7 = (camz - $400) & $ff00`; the first column's offset is `-(camx - D6)`, the first row's depth `$e00 - (camz - D7)`.
The main block is 10 rows (depth step `$100`) by 11 columns (cell width `$100`). For each vertex the height comes from
`$24754` (`D1 = byte * 8 + $fd68`; the pad cells give `$420`; `D1 >= $560` is type 8, `$510 < D1 < $560` is type 7),
then the height minus the camera height and the projection:

```
sx = (dx << 8) / dz + $a0        sy = (dy << 8) / dz + $46        (one divs each; no reciprocal table)
```

The pair is stored at `-(A6)` from `$2758c` (52 bytes per row) and the type word at `-(A3)` from `$276e0`.
`py/virus_grid.py` reproduces all 330 words of the main block (110 vertices x 2 plus 110 type words) from the
snapshot's camera, height map and object map against `callcap 24098`: 330/330 on each of four flight frames (camera
x, y, z (1604,-6724,3047), (2332,-17310,9356), (3112,-23858,15057), (3970,-25424,19302)); control (first-row depth
`$f00`) 117/330. Not modelled: the side and far blocks of `$24098`, which add vertices to make rows of 13 over 12
rows. The flight frames show no ground (the ship is high); the grid is built regardless.

**Tile calls (gated).** The draw loop (`$243b6`) walks 11 rows of 12 tiles and calls the tile filler `$26b78` for each.
`py/virus_tiles_check.py` reads a REPL log of 132 `bp 26b78` stops: the 8 vertex words in D0..D7 are the words at A6
and A6+52 in the vertex rows, 132/132, and the colour index in A0 is the type word at A3-2, 132/132; control (type array
read two words off) 33/132.

**Tile colour is a height band (gated), not slope.** The type word for a land vertex is `9 + ((D1 >> 3) & 3)`, that is
the low two bits of the height byte (one value per four height steps, cycling: the contour stripes in the picture), 330/330
above. Water gives type 8 and the shore type 7. The filler takes one colour index per tile, the type word of the tile's
first vertex, and maps it through `$1f2bc` to a table of span routines (read). No slope term was found in this path.
`$18322` and `$23a2c` (called from `$24098` just before the tile loop) were not checked, so a slope shading elsewhere is
not ruled out. A cell whose object-map byte has bit 5 set takes its colour word from the table `$244b0` indexed by
`(D1 >> 2) & $e` (read).

**Slope table `$5ab58` (gated).** `entry[(dx << 7) + dy]` (the index is a signed word: dx from -64 to 63, dy from 1 to 63)
equals minus the truncated `dx * 65536 / dy` with its low eight bits cleared, in 16.16: 8064/8064 (`py/virus_slope.py`); control
(low byte kept) 1431/8064. The entries for dy 64 to 127 do not follow this formula (63 of 127 per dx match) and are not
understood. The filler uses the table to step an edge's x per scanline without dividing.

**Tile filler `$26b78` (read).** Rejects a quad if any of its four vertices is outside 320 x 184, sorts the vertices by y,
steps two edges with the slope table, and calls a span routine per scanline through `jsr 0(A0,A2.w)`, indexed by span
width, from the colour's table.

**Depth sorting of objects, shadows and actors (read, not gated).** `$1fa72` (the object pool `$302f6`) and `$2157c` (the actor pool)
subtract the camera, take a bucket `D6 = ((z - $900) >> 5) & $fff8` (ten buckets, 8-byte slots at `$23caa`, initial values
copied from `$23cfa`), project the point with the same two `divs` (`+$a0`, `+$46`) and append an 8-byte record, whose first
long is a draw routine, to that bucket's list. After each row of tiles the painter (`$243ec..$24474`) draws the list of the
matching bucket by `jsr (A0)` on each record. So the order is a painter's algorithm with one bucket per tile row, far to near.

## The flight model (gated, mouse run; autopilot poked)

The ship tick is `$255c2`. The ship state is `$270b0`: x, y, z, vx, vy, vz (words). The input routine returns a target
attitude (D0, D1) and flags (D2) at `$255d4`; the model gates what follows.

```
if y < $c900 (signed): thrust off
attitude += -((attitude - target) clamped above at $2800) >> 1       per axis, half way per tick
matrix = rotation from (yaw, pitch)                                  $1f646: table sines, products doubled
vel   -= vel >> 6                                                    drag 1/64 per axis
if thrust: vel -= column >> 3  (signed high bytes of matrix words +2, +8, +14); fuel -= 3
pos   += vel
vy    += g                                                           g = $32a3a, 3 at wave 1
```

The clamp on the negative side is unreachable (`bcc` is unsigned), so a large negative change is not limited. `py/virus_flight.py`
reads 120 `bp 255d4` stops from `fl/f1.snap` with a mouse nudge at the start and thrust held: 119 consecutive ticks,
position 119/119, velocity 119/119, attitude 119/119, matrix 119/119 (20 thrust ticks, 99 without). Control (thrust term
`>> 4`): 99/119, failing exactly on the 20 thrust ticks. The gravity `g` is read to be set to 3, 4, 5, 6 at wave thresholds in
`$20f26..$20f64` (read; only the value 3 is seen in the run). Not modelled: the mouse routine `$254aa` (mouse offsets about
`$80`, converted to an angle and tilt through the tables at `$d8fa` and `$d9fa`, read), the ground contact paths `$25a6e`,
`$25c28` and the exhaust particles.

`$2538c` is a second input routine that picks the target and flags from the ship's position against a target list at
`$270a6`, and `$62a5f` selects it in place of the mouse routine. **Poke:** `wb 62a5f ff` on `fl/f1.snap`. A `hits` run
of 300,000 steps then counts 10 entries of `$2538c` and 0 of `$254aa`, and the same tick model matches position, velocity
and attitude 119/119 (the thrust ticks 14/14, the others 105/105); control (thrust `>> 4`) 105/119. The orientation matrix
matches 4/119 in this run (119/119 in the mouse run); the cause is not established (inferred: other drawing code rewrites
`$270d4` between ticks, for example the call at `$23d5c`). This is a poked result, not a played one.

## The actor pool and the seeder (gated, one behaviour)

The pool `$31d54` holds the wave's enemies (named in [`behaviours.md`](behaviours.md)). It holds up to 128 records of 20 bytes, count `$32a3e`: +0 x, y, z; +6 vx, vy, vz; +12 a life and flag word;
+14 a pad word; +16 a behaviour code pointer (long). `$21722` appends a record. Each frame `$2157c` walks the pool: it reads
the ground height at the record's x, z (`$24754`); if the ground is at or above the record's y the flags `$a000` are or-ed
into the life word, and the record's behaviour is called through its pointer. A flagged record is removed by its behaviour
(`$21764`: a sound, then the last record is copied into its slot and the count falls by one); there is no bounce.

The seeder in flight (`$21792`, the pointer in three of the five records in the run: wave 0's three seeders), with word arithmetic:

```
pos += vel;  if life != 0: life -= 1   (when life is 0 and ground <= $320 the pointer becomes $21894, not modelled)
vy -= (y - ground + $280) >> 5          a spring toward ground - $280, not a gravity constant
vy -= vy >> 4                            drag on vy only
vy clamped to [-$60, $60]
```

`py/virus_particles.py` reads 150 `bp 2157c` stops from `fl/f1.snap` (pool count constant at 5) and checks the three seeders
over 149 frames: 447/447 updates with x, y, z, vx, vy, vz all equal; control (drag `>> 3`) 334/447, failing only
in vy. Not covered: the other behaviours present (`$21ae2`, `$21c42`, `$21c64`, `$21d08`: the waiting chaser and the patrol,
read in `behaviours.md`), the seeder's descent and landing (`$21894`, `$21976`: read, run in the census only), removal, and the
infection it drops (`$20702`) and the shadow record it appends.

## Landscape selection by wave (code read; poked-stub run)

`$32a50` is the wave number: it is incremented at `$20fd0`, passed to the wave-start routine `$20e74` at `$210ee`, and read
for the HUD at `$24906`; it is 0 at the start of wave 1. `$20e74(n)` appends the wave's waiting enemies from a table of 16 parameter
blocks at `$20e34` indexed by `n & 15` (per kind in `behaviours.md`) and then, in its tail at `$20f4a..$20f78`, calls `$2336a(1)` when `n == 4` and `$2336a(2)` when
`n == 9`; game start and restart call it with 0 (`$23092`, `$230b4`, `$25bf6`). **Poked stub** (`moveq #n,D0 / jsr $20e74 / rts`
under `callcap` from `fl/f1.snap`; `capture.sh` writes `cap/cc_n<n>.json`): `$32a4e` and `$32a4c` stay 0 for n = 3, 5, 10, become 1
for n = 4 and 2 for n = 9. The route by which a played game reaches wave 5 or 10 was not run, and `$32a3a`'s per-wave
values are read. A wave is completed by destroying every enemy except the unhatched chasers (`$20f82`, `behaviours.md`).

## Demo mode and the autopilot

The demo is an attract mode: 769 idle frames of the title loop set the flag `$62a5f`, and the next game is flown by the
autopilot `$2538c` through the same flight tick as the mouse. It is covered in its own doc, [`demo.md`](demo.md): how
the demo is entered, the pilot's routines and rules, runs to the pilot's natural death, a chain of six complete games
with no pokes (no trend in survival or score; a weak test), and what carries over a game over (the high-score table,
the infection target queue at `$27134`, the random state). Its scripts are in `py/demo/`.

## Open questions

1. Slope shading: `$18322` and `$23a2c` (called before the tile loop) and the span routines behind `$1f2bc` are unchecked,
   so whether the picture's shading has a slope term is open. Prove it by a callcap diff of the screen with one tile's
   vertex height changed.
2. The slope table's dy 64 to 127 entries.
3. The depth-bucket scheme is read, not gated: gate it by dumping a bucket's records at the start of the painter.
4. The matrix under the autopilot (4/119): trace the writers of `$270d4` with `watch`.
5. Landscapes 1 and 2 and the wave switch are from poked stubs: reach wave 5 played (or drive `$32a50` through the wave
   completion code `$20fd0`) and `watch` `$32a4e`.
6. The mouse routine `$254aa` and the ground-contact paths of the tick are unmodelled.
7. The object types 1 to 9 and the markers 10 to 12 are unnamed; the actor behaviours are named from their bodies in
   `behaviours.md`, gated only for the seeder.
8. The launch-pad table `$246ba` is not modelled (its 81 colour bytes are read from RAM).

## Files

| file | contents |
|---|---|
| `README.md` | this file |
| `drive.sh` | cold boot to the wave-1 launch pad (writes `scratchpad/virus/drive/`) |
| `gates.toml` | the gate `tools/gates.py` runs |
| `behaviours.md` | the actor pool's behaviours, waves, demo-flag readers, draw-list residue |
| `py/scan/` | that doc's census, wave-end, watch and residue scripts |
| `virus.sym` | names |
| `py/README.md` | each script, its command and expected line |
| `py/capture.sh`, `py/gate_all.sh` | fresh captures; every model with its control |
| `py/virus_terrain.py`, `virus_objects.py`, `virus_grid.py`, `virus_tiles_check.py`, `virus_slope.py`, `virus_flight.py`, `virus_particles.py` | the models and gates |
| `py/render_heightmaps.py`, `py/vcommon.py` | the heightmap renderer; shared paths |
| `heightmaps.png` | landscapes 0, 1 and 2 from the model (256 x 256 cells each, 2x; white is water) |
| `title.png`, `pad.png`, `flight.png` | the title picture, the wave-1 launch pad, a flight frame with exhaust |

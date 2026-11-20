# virus: Virus (David Braben, 1988), first look

Virus is a flight game over a procedural landscape: the player's craft takes off from a launch pad, flies over
a patchwork of coloured tiles and shoots the infection. It is an Atari ST game. The version analysed is the Union crack (the `A-HA #[no number]` disk), which adds a trainer menu in front of the game (a cheat menu, see `../GLOSSARY.md`).

**What this doc set has established.** The landscape is a 256x256 byte height map computed once per level from a sum of eight table
sines, and levels 1 and 2 are the same routine with four instruction words patched; each of the 110 grid vertices
costs two `divs`, not a reciprocal table; a tile's colour is the low two bits of its height byte (a cycling band),
not a slope; the ship's whole tick is half-way attitude smoothing, 1/64 drag, thrust of a matrix column divided by
8 and a gravity that rises with the wave.

**Where to find what.**

- How is the landscape generated, and why do levels 1 and 2 share code? "The landscape generator" below.
- Where are the objects placed, and how does the random number generator work? "Object scatter and the RNG".
- How is the picture drawn? "The renderer".
- How does the ship move? "The flight model".
- What do enemies do, when does a wave end, what spawns per wave? "The actor pool and the seeder"; [`behaviours.md`](behaviours.md).
- What does attract mode do? "Demo mode and the autopilot"; [`demo.md`](demo.md).
- What is still unknown? "Open questions".
- Where is each thing in RAM? "Memory map".
- How do I reproduce a result? "Running it", and "Gates" below.

Terms used here are defined in `../GLOSSARY.md`.

## What was reached, and how it is proved

Reached in the emulator: the Union
menu, the trainer menu, the title picture, the "Press R" page, the game on the launch pad at wave 1, and flight
(thrust held, a real input run). The game is hand-written 68000 (no compiled-C idioms were met in the parts read), so it is analysed from snapshots, `bp`/`hits` runs and `callcap`, not a decompile.

Evidence is of three kinds. **Gated:** a Python model matched against the emulator's own output with a match count,
a broken-model control and a command in `py/README.md`. **Poked:** a result reached through a labelled poke.
**Read:** from the code only, marked "(read)". A section says which of these it is.

Gates: `uv run python tools/gates.py run virus -j 8` (`gates.toml`, 14 gates, about 6 minutes at eight at once). `models` re-reads
the captures, which are rebuilt with `bash reversing/virus/drive.sh` then `bash reversing/virus/py/capture.sh`; the others run the
emulator afresh from the snapshots their `inputs` name, the chain starts among them (`py/chain/chain.py`, "Running long").

| Doc | Covers | Proof |
|---|---|---|
| this file | provenance, the drive, memory map, landscape generator, object scatter, the object types and RNG, renderer (tile colour, spans, depth buckets and paint order), flight model with the mouse and ground contact, the seeder behaviour, landscape selection by wave, which code runs | terrain 65455/65455 on three landscapes, objects 571/571 and 1774/1774, object shapes by render diff, grid 330/330 on four frames, tiles 132/132, slope table 16320/16320, spans 1440/1440, buckets 39523/39523, flight 119/119, mouse 180/180, seeder 447/447, wave pools 141/141 |
| [`frontend.md`](frontend.md) | the three frame routines, HUD, font, sound driver and effects, title, game over, hall of fame, score code | HUD digits 12/12, sound sites 5531/5531, hall of fame 10/10 |
| [`demo.md`](demo.md) | the attract mode and its autopilot | see that doc |
| [`behaviours.md`](behaviours.md) | the actor pool's behaviours (every enemy kind), wave completion and the per-wave spawn table, readers of the demo flag, the draw-list residue | wave ends 4/4 against the rule, bonus 7/7 natural wave ends, chaser 2818/2818, mothership launches 27/27, falling infection 8319/8319, residue poke 500/500, census of four games |

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

Hatari 2.6.1 (headless, `--fast-forward on`) runs the same flight 1.7 to 1.9 times as fast in game ticks per wall second:
from the game start (Hatari's own cold boot saved with `statesave`, ours `demo/S1b.snap`) both reach tick 1,190 score `$0621`
at 5,000 VBLs and tick 4,790 score `$155a` at 20,000, and over four interleaved rounds (load 5 to 9) ours ran 240M steps in a
median 44.0 s (110 ticks/s, 5.5M steps/s, build `c337526`) and Hatari 20,000 VBLs in 25.4 s (205 to 209 ticks/s); every Hatari
run was faster. Both spend about 4.15 to 4.18 VBLs a tick, so the gap is VBLs per second, not the frame length. With the state
transplanted after a desktop boot (a `--memstate` load restores the CPU settings it was saved with), `--cpu-exact off` gives
1.37 times default Hatari, adding `--compatible off` 1.45 and `--timer-d on` 2.28 (about 4.1 times ours), each with the
2,602-byte game state of `reversing/learning/py/hatari_game.py` identical at ticks 4,790 and 11,000; `--cpu-exact off`
broke the key-driven cold boot of this disk 5 of 5 times. Hatari has no step-exact stop, fork or `callcap`, and one
conditional breakpoint costs it 14 to 16%. Scripts and logs: `scratchpad/overseer/hatari_speed/` (`bench.sh`, `variants.py`;
record, not a gate).

## Memory map (RAM, 1 MB)

| range | contents | how known |
|---|---|---|
| `$c000..$27000` | game code and tables, about 40,000 listed lines (`tools/disassemble.py --snap <snap> --all c000 28000`); `$c000..$ce9a` is model data, not code (next row), and the end of the text is not checked | listing |
| `$aa72..$ce9a` | the 43 object models; per-type pointers at `$23f98` | `models3d` gate ("Model data and the model drawers") |
| `$d0fa` | sine table, 1024 words, `int(32767*sin(2*pi*k/1024))` with entry 256 = 32766 | 1024/1024 (below) |
| `$d8fa`, `$d9fa` | arctangent and square-root (tilt) tables read by the mouse routine `$254aa` | `flightctl` gate |
| `$e9fa` | the 8x9 proportional font, 10 bytes a glyph, index char - `$20` | HUD digits 12/12 (`frontend.md` "Text and the font") |
| `$177d2` | the sound-effect table: 54 longs into 18-byte effect records at `$17406` | read (`frontend.md` "Sound") |
| `$246ba` | launch-pad tile-type table, 75 bytes `$246ba..$24704` (values 4, 6, 14, 15, 22; `$24705` is a pad byte, code starts at `$24706`) | 96/96 reads, 0 writes ("Object scatter and the RNG", `py/objects/pad_table.py`) |
| `$270b0` | ship state: x, y, z, vx, vy, vz (words) | flight gate |
| `$270ce` | camera x, y, z (words) | grid gate |
| `$270d4` | the renderer's current rotation matrix (9 words, stride 6): the ship's own after the tick builds it at `$25654`, then overwritten by steering and draw ops | flight gate (mouse run), `flightctl` gate |
| `$270ec`, `$270fe`, `$27110` | three spinning rotation matrices rebuilt each frame from the frame counter by `$2617a`, used to draw the turning models | `watch` 111 writes a 37-frame run, 0 with `$2617a` stubbed (`frontend.md` "The three frame routines") |
| `$2706e`, `$27072` | the RNG, two longs | scatter gate |
| `$31d54` | actor pool: the wave's enemies and the player's rockets, up to 128 records of 20 bytes; count at `$32a3e` | seeder gate, `behaviours.md` |
| `$302f6` | object pool: shots, sparks, droplets, fragments, smoke, contrails, falling infection, bombs, score pop-ups; 18-byte records (x, y, z, vx, vy, vz, life, handler), count `$32a3c` | falling-infection kind gated 8319/8319 (`py/objects/gate_infection_fall.py`); handlers in `behaviours.md` "Two pools" |
| `$276fc..$2f6f3` | the ten depth-bucket draw lists, `$ccc` bytes each | `behaviours.md` |
| `$32a2e`, `$32a32`, `$32a3a` | fuel, smoothed attitude (2 words), gravity | flight gate |
| `$32a44` | frame counter: +1 at `$23198` each frame, cleared at game start `$230e6` | read (`frontend.md`) |
| `$32a4c`, `$32a4e`, `$32a50` | last built landscape, current landscape (0, 1, 2), wave number | below |
| `$32a58` | object map: one byte per cell, low 5 bits the object type (1 to 12, "Object scatter and the RNG"), bit 4 destroyed, bit 5 infected | scatter gate; shapes by render diff (`objects.png`) |
| `$42a58` | height map: 256 x 256 bytes, index `(y << 8) | x` | terrain gate |
| `$5ab58` | slope table, 16,320 longs (slots -8192..8127 of the signed index, `$52b58..$62a57`; from `$62a58` the bytes are flags) | slope gate, `py/shading/slope_full.py` |
| `$70000`, `$78000` | the two screen buffers (the shifter base alternates) | `snap_render.py` |
| `$2f6f6` | the 64x64 four-plane minimap in the HUD corner; the radar's dot list follows it at `$2fef6` (end pointer `$27076`) | `behaviours.md` "What the radar shows" |

Names are in `virus.sym`.

## Main loop

`$23198` runs once per game frame (about 2.47 VBLs: 81 calls of each frame routine in 200 VBLs, from an
`ATARI_TRACE_EVENTS` census of the flight snapshot). In order: `$2617a` (`SpinMatrices_Update`: the three rotating orientation matrices `$270ec`, `$270fe`, `$27110` the actors draw with), `$1fa72` (the object pool, into depth buckets),
`$255c2` (the ship tick), `$2157c` (the actor pool), `$24098` (the landscape grid and the whole painter), `$23c8c`
(`Buckets_Reset`: the ten list ends back to their starts), `$24956` (`Score_CheckExtraLifeAndDraw`: the extra-life check and the score digits), `$232e6` (`InfectionQueue_Advance`, `demo.md`), `$20f82`
(`Wave_CheckComplete`: the wave ends when only unhatched chasers are left, `behaviours.md`), `$183f2` (`Screen_FlipSetscreen`: the double-buffer flip and the Setscreen trap). All
three are proved in [`frontend.md`](frontend.md) (`py/frontend/flip_spin.py`: 37 flips, 37 traps and 999 matrix writes in 37 frames,
0 writes with `$2617a` stubbed; `py/frontend/hud_match.py`: 12/12 score renderings).

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
by nine cells with x and y below `$900` are a launch pad: a constant byte `$d7` (height `$420`), with their tile type from
the 75-byte table at `$246ba` (modelled in "Object scatter and the RNG", subsection "The object types").

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
- on **natural play** (`py/landscape/gate_landscape.sh`, game 050 of the unpoked chain): the map built for wave counter 2 is
  level 0 (65455/65455) and the map built when the counter reached 4 is level 1 (65455/65455, the same on games 014 and 045's
  counter-4 builds, run by `py/landscape/chain_waves.sh`); controls: level 0's model on level 1's map 10471/65455, base
  shifted 46802/65455. Level 2 is reached only by a labelled poke of `$32a50` (below): 65455/65455 at counters 9 and 16.

Command: `bash reversing/virus/py/gate_all.sh` (or one line of it). `heightmaps.png` shows the three fields.

## Object scatter and the RNG (gated)

The RNG state is two longs `a` (`$2706e`) and `b` (`$27072`), seeded `$1234abdf` and `$5678e7f2` at `$2300a`. A draw
is: the random word is the high word of the old `a`; then `a = a + b` and `b = swap(old a)`. Checked by a `callcap` of
`$236f8` (a `$35f0cf9b` to `$fa6f2591`, b to `$cf9b35f0`).

The scatter `$236f8(D0 = count - 1, D1 = type)` draws a random word, takes it as the cell index (high byte y, low byte x),
and accepts the cell if its height is at most `$510`, not `$420`: then `map = (map & $e0) | type`. The builder calls it
nine times, in this order (draws, type): (289,4) (129,1) (257,5) (769,6) (385,3) (257,2) (113,7) (97,8) (81,9). Types
1 to 9 are named below; the markers 10, 11 and 12 are written afterwards (a `$a` triple, a `$b` lattice and `$236ae`'s `$c`).

Proof, `py/virus_objects.py`, with the **poked-stub** callcaps (levels 1 and 2 only; level 0's stub skips the clear):
landscape 1 model 571 cells, RAM 571, identical type at the same cell 571; landscape 2 model 1775, RAM 1774, identical
1774. The one model-only cell `$e6c6` lies on the `$b` marker pattern that the builder writes afterwards, so it is
overwritten (inferred, not run separately). The RNG state comes from the pad snapshot, so these counts differ from an
earlier run from another snapshot (563/563, 1778/1778); each is exact for its own state. Controls: first scatter one
draw short 1767/1774 identical; two types scattered in the other order 1586/1774. A one-draw shift moves every set
against the next only at the nine scatter boundaries, so the set comparison is blind to a pure shift except there;
the order control is the strong one.

### The object types (gated by render diff)

`$24098`'s vertex loop tests the object-map byte under each grid vertex (`andi.b #$1f` at `$24120`) and, for a non-zero
type, `$23ef8` draws a 3-D shape chosen from the 64 longs at `$23f98`, indexed by `byte & $3f`: normal (0 to 15), damaged
(bit 4, 16 to 31), infected (bit 5, 32 to 47) and both (48 to 63). The shapes are drawn by `$26278` (read). Bit 4 is
"destroyed": a player or enemy shot over the cell sets it (`$1ff6e`, `$203d0`), and so does the ship touching it
(`$25856`); the cell then shows a grey wreck and a smoke puff (`Smoke_Spawn`) every eighth frame (`$23f32..$23f40`).
Bit 5 is infection, set only by `Infection_Plant` (`$20696`). What each type looks like on screen (`objects.png`: plain,
damaged, infected):

| type | name (from the drawn shape) | model | infected form | placed by |
|---|---|---|---|---|
| 1 | palm tree | `$ae30` | wilted pink palm (`$b23e`) | scatter 2nd call (129 draws) |
| 2 | bush | `$b162` | pink/red plant (`$b1ca`) | scatter 6th (257) |
| 3 | pine | `$b110` | pink cone (`$b2f6`) | scatter 5th (385) |
| 4 | palm tree (same model as 1) | `$ae30` | withered orange palm (`$b348`) | scatter 1st (289) |
| 5 | tall palm | `$aee8` | orange palm (`$b400`) | scatter 3rd (257) |
| 6 | fir | `$b0be` | unchanged | scatter 4th (769), the commonest |
| 7 | long house, red roof | `$b5e6` | unchanged | scatter 7th (113) |
| 8 | cottage, orange-tile hip roof | `$b806` | unchanged | scatter 8th (97) |
| 9 | archway, pink dome | `$b4e0` | unchanged | scatter 9th (81) |
| 10 | pad marker (thin red-over-yellow pole) | `$ba54` | unchanged | three fixed cells (rows 1, 3, 5, column 7; `$234ec..$234f8`) |
| 11 | tower (grey disc on a cyan cone; models `$c6f2`, `$c79c`) | | unchanged | an 8 by 8 lattice, one every 32 cells from (6,6) (`$23508..$23536`) |
| 12 | bonus craft (spinning teal and grey craft; model `$ac66`, turned by the frame counter `$32a44`) | | unchanged | one try by `$236ae`: a random cell, kept only if it is water (`$236dc`) |

Infection changes the shape only for types 1 to 5; for 6 to 12 the infected entries equal the plain ones and only the
ground tint (`$244b0`) changes. A shot that reaches an undamaged cell goes to `$20218` (read): an infected type 1 to 3
gives 40 points, 71 or 41 infection drops and provokes the patrols (`$1ffbc`, `$20092`, `$201b4`); types 4 and 5 give
nothing; type 11 first clears an 8 by 8 block of minimap pixels (`$23c08`), so the tower is probably a radar station
(inferred); type 12 gives 1000 points and is removed. The ship touching an undamaged non-zero cell is fatal
(`$25846..$25ad8`), after a 40-point award for an infected type 1 to 3.

Proof, `py/objects/object_shapes.py` (`gate_objects.sh`), from `demo/S1b.snap`: the ship state `$270b0` is poked at seven
arrivals at `$255c2` (the only intervention) to put the camera in front of a cell with an empty 3 by 3 neighbourhood, in five
poses, and the live screen is rendered twice, with the cell's byte kept and with it zeroed. The differing pixels near the
cell are the object. The cell's projected column (`160 + (x - camx) * 256 / depth`) lies inside the object's pixel columns
for 3/3 cells of each of types 1 to 9 and 11, and 2/2 for type 10 and for type 12 (the latter on land cells given the byte by
a poke, because the ship cannot be posed in front of the natural water cell); the cell two columns over lies inside
0/3 each (type 4 once in an earlier 4-cell run). With flags forced to `$10` and `$20` the column is inside the box 10/10
and 10/10 (`shapes` of the gate). The vertical position is not proved: objects of types 2, 7 and 8 lie 8 to 15 px
below the vertex's projected row (the diff boxes include the shadow), so "the foot is at the vertex" is not claimed.

**The launch-pad table `$246ba`.** It holds 75 tile-type bytes (`$246ba..$24704`; the byte `$24705` is a pad and code starts
at `$24706`), values 4, 6, 14, 15 and 22. Its only two readers are `lea d16(PC),A0` at `$2459e` (in `$245b8`) and `$24716`
(in `$24754`), by a raw scan of `$c000..$27000` (no absolute reference); a write watch over 12M steps of the demo's pad
and flight saw 0 writes (the ship state, 1698). For D6 (x) and D7 (z) both below `$900` the routines return height `$420` and
the type `T[(((D7 << 3) & $fc00) + D6) >> 8]`, which at a cell corner (256 k, 256 j) is `T[8 j + k]`: the row stride is 8, so
vertex (8, j) shares its entry with (0, j + 1) and entries 0 to 72 are used. So the "9 by 9" is a map of the pad's vertices
by tile type, the same type word the tile filler takes as colour. Proof, `py/objects/pad_table.py reads`: 96 pad-region
reads at `$245ae` and `$24726` (the instruction that loads the byte), the index in D3 equal to the model's and the byte
equal to `T[index]` 96/96 over 73 distinct indices; controls: index + 1 28/96, row-major `9 j + k` 25/96. On screen
(`pad_table.py screen`, from `drive/g_game2.snap`): poking one entry changes exactly one main-block type word, at grid row j and
column k + 1 (the grid's first column is x = -256), 12/12, and the screen changes each time; the tile that changes is not
identified (Open 8).

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
above. Water gives type 8 and the shore type 7. A cell whose object-map byte has bit 5 set takes its colour word from the
table `$244b0` indexed by `(D1 >> 2) & $e` (read). `$24754` reads one vertex's height byte and nothing from its neighbours,
and the filler takes one colour index per tile, the type word of the tile's first vertex, so the colour cannot carry a slope
term, and the shading the picture shows is the contour stripes plus the launch pad's authored colour table `$246ba`.
`$18322` and `$23a2c`, called from `$24098` just before the tile loop, are not shading: `$18322` (`ScreenClear_Draw184`)
zeroes 184 lines of the draw buffer `$27062` (skipped while the key-toggled byte `$62a5c` is non-zero; its sibling `$18390`,
`ScreenClear_Window`, clears an 80-byte-wide, 128-line window and is called at `$24c60` and `$24d28`, read) and `$23a2c` is
the HUD radar and bars (`behaviours.md`, "What the radar shows"). Proved by a height poke from one snapshot
(`py/shading/height_poke.py`, `scratchpad/virus/drive/g_game2.snap`, the cell at `$42b61`, outside the launch pad):
raising the byte by 32 steps (+256 height units, the same type band) leaves the 143 type words equal, 143/143, and changes
513 of 58880 screen pixels, all 513 to a colour already among the frame's tile colours or 0; raising it by one step (a new
type band, the positive control) changes the type word (142/143) and 143 screen pixels from colour 9 to 10; an unpoked
repeat matches 58880/58880.

**Slope table `$5ab58` (gated).** The index is the signed word `s = (dx << 7) + dy`, the entry at `$5ab58 + 4s`; writing
`s = dx*128 + dy` with dy in -64..63, the entry is 1 for dy = 0 and otherwise minus the truncated `dx * 65536 / dy` (the
sign of the quotient taken first) with the low eight bits of its magnitude cleared, in 16.16: 16320/16320 slots, slots -8192
to 8127 (`py/shading/slope_full.py`; control, low byte kept, 3111/16320). What was once read as "dy 64 to 127" is the dy
-64..-1 half of the next dx row, so there is no second formula; the longs from slot 8128 overlay the flag bytes at
`$62a58..` and are not table. `py/virus_slope.py` gates the dy 1..63 half alone, 8064/8064. The filler uses the table to
step an edge's x per scanline without dividing. In the pad frame every edge the filler walks lies in range, dx -64..63 and
dy 0..63, 348/348 (`py/shading/tile_gate.py`); the negative-dy slots are then not read by the filler, which sorts by y
(inferred from that frame), and an edge outside the range would alias into another dx row (not checked on other frames).

**Tile filler `$26b78` and the span routines (gated).** The filler rejects a quad if any of its four vertices is outside
320 x 184, rotates the vertices (v0, v1, v3, v2 around the perimeter) until v0 has the smallest y, steps two edges with the
slope table and calls a span routine per scanline through `jsr 0(A0,A2.w)`. The table `$1f2bc` (`ColourSpanWidthTables`) holds
24 longs, one per colour index; each points at 330 word offsets indexed by span width, relative to that table, and the
routines follow it: five per colour for widths 0, 1..17, 18..33, 34..49, 50..65 and 66..320 (widths 321..329 reach a few
other targets, unread). Entered with D4 the first pixel's x, D5 the width, A3 the scanline and A1 = `$ceba` (a table of word
masks by start and end pixel within a 16-pixel group), a routine does `or.w` (set) or `and.w ~mask` (clear) on each plane of
each group the span touches. Indices 0..15 are flat colours, each plane set or cleared by the bits of the index (24 tables
decoded, plane ops matching the index, 24/24: `py/shading/span_colours.py`); indices 16..23 set planes 0..2 from `c - 16` and
take plane 3 from the word `$1cb78` (`$aaaa`, inverted on every call), a one-pixel checker of colours `c - 16` and `c - 8`
that flips each scanline (the launch pad's colour 22 is a 6/14 grey). Called directly through `stserver` on a line of random
words, 1440/1440 span calls (24 colours, widths 1 to 300) colour exactly pixels x..x+width-1 and leave the rest of the line
(`py/shading/span_gate.py`; control, one pixel too wide, 93/1440). Replaying the 135 real tile calls of the pad frame
(`py/shading/tile_capture.py`, `tile_gate.py`) onto a zeroed buffer, 3491/3491 pixels at least 1.5 px inside the quad carry
the tile's colour and 31026/31026 pixels at least 1.5 px outside stay 0, with no tile missing; control (the bow-tie vertex
order) 721/724 and 61 tiles missing. So a tile is a flat fill of its type word's colour; the filler's exact edge-pixel rule
and its triangle and degenerate branches (`$26d44` on) are not modelled. All of this runs from `py/shading/gate_shading.sh`.

**Depth buckets and paint order (gated).** Ten lists of `$ccc` bytes at `$276fc + k*$ccc` (bucket 0 nearest, 9 farthest) hold
draw records. `$23caa` holds `{end pointer, limit}` per list and `$23cfa` `{start, area end}`; an append writes at the end
pointer if the record fits below the limit, then advances it; `Buckets_Reset` `$23c8c` copies the starts over the ends once
a frame. A record starts with the long address of its draw routine and its size follows from that routine:

| record | size | layout | made by |
|---|---|---|---|
| dot (`DrawRec_Dot_ColourN`, `$16fb4..$1735c`) | 8 | routine, sx, sy | object tails `$1faa8` (one dot) and `$1fb18` (a `$16fb4` shadow at the ground's sy, then the sprite, same sx, same bucket) |
| pop-up text `$173b4` | 8 | routine, sx, sy | handler `$20766` through `$1faa8` |
| model `$26222` | 32 | routine, model pointer, 3x3 matrix (9 words), (dx, dy, depth) | ship (`$258dc`), actor tail `$2167a`, object tail `$1fbbc`, cell objects `$23d88`/`$23e00` |
| `$261d2` | 32 | the same, drawn through `$2628c` (sets `$62a69`) and the A5 it leaves is kept at `$27086` | cell object `$23e00` |
| model without matrix `$26278` | 14 | routine, model pointer, (dx, dy, depth) | landscape cells `$23e76`, `$23f64` |
| `$2620e` | 4 | routine only: runs `$264c4` on the A5 saved at `$27086` | `$23ec0` |
| beam `$22a64` | 16 | routine, 6 words (two 3D points), three interpolated segments through `$22bbe` | `$225ac` |

Parse: every list of 780 captured frames (`$24098` entry; `reversing/virus/py/painter/analyze.py`) is a whole number of
records, 7800/7800. The records and their append sites are read; the record shapes are gated through that parse.

Bucket index, objects (`$1fa72`; the pool's update runs first, with the camera of the previous frame). With
`d2 = z - camz + $500` a record is queued only if `(x - (camx - $580)) & $ffff < $b00` and `d2 & $ffff < $a00`; the
bucket is `d2 >> 8`; `depth = d2 + $900`; `sx = ((x - camx) << 8) / depth + $a0` and `sy = ((y - camy) << 8) / depth + $46`
(two `divs`, truncating). `analyze.py` predicts every post-walk pool object from the pool and the walker's entry camera and
walks each bucket's dot records in pool order: 39,523 of 39,523 objects matched on 780 of 780 frames (flight `fl/f1.snap`,
demo `demo/S1b.snap`, chain game 50 from frame 600); controls: bucket shifted by `$100` 3, reversed (9 - b) 0, `d2 >> 9` 473
of 39,523. The shadow's sy (ground height from `$245b8`) is not gated, only its sx, order and bucket.

Bucket index, models (actor tail `$2165c`, ship `$258be`, `$1fbbc`, cell objects): `((depth - $900) >> 5) & $fff8` with
`depth = z - camz + $e00`, clamped (0 when negative, 9 when `>= $50`) instead of skipped: 1215 of 1215 model records sit in
the bucket their own depth word gives; without the clamp 1184 of 1215. The ship record is in every frame (780/780); object
model records (`$1fbbc` tails of the handlers at `$20882`, `$208f4`, `$2097a`) 149/149; actors in the window (`behaviours.md`)
286 of 291 have a record (the five others are inferred to be in a non-drawing state; not checked).

Paint order (`$243b6..$24474`). The loop draws a row of 12 tiles, then bucket `11 - row` (buckets 11 and 10 are skipped by
`cmp #$a`), so bucket 9 follows the third row and bucket 1 the last; bucket 0 is drawn after all rows. Within a bucket, list
order. `gate_order.py` stops at `$26b78`, `$243ec`, `$24436`, `$24478`: the order `T B11 T B10 T B9 ... T B1 B0` on 40 of 40
frames (consecutive tile stops under 64 steps apart are deduplicated by the harness, so tile counts per row are not read).
A bucket's dots use the mask table `$24488[b]`: bucket 0 the 3-pixel masks `$16f92`, buckets 1 to 6 the 2-pixel `$16f72`, 7 to 9
the 1-pixel `$ce9a`; `sgt $16fb2` makes buckets 5 to 9 paint one scanline and buckets 0 to 4 two (the shadow `$16fb4` always
one). Each dot routine paints one definite 4-plane colour (`or.w D2,(A0)+` sets a plane bit, `and.w D1,(A0)+` clears it), so
where two dots overlap the later one survives. `analyze_order.py` reads the screen at `$24478` and models every dot: of 4946
pixels covered by dots of different colours the screen shows the last-drawn dot on 4881 and the first-drawn on 15 (control);
the other 65 are inferred to be overdrawn by a model record (the ship), which is drawn later in the same or a nearer bucket.
Cross-bucket pairs (a far dot, then a nearer one): the nearer shows on 1262 of 1263 and the farther on 0. Example, `S1b.snap`,
pixel (157, 100): a bucket 5 `$170f4` (colour 3) then a bucket 4 `$17044` (colour 7); the screen shows 7. Colours, from the
routines' code: `$16fb4` 0 (shadow), `$16ff4` 15, `$17044` 7, `$1709c` 11, `$170f4` 3, `$1714c` 5, `$171a4` 12, `$171fc` 9,
`$17254` 4, `$172ac` 14, `$17304` 6, `$1735c` 1. A tile row painted after a bucket overdraws it (read from the loop; not
separately gated). `$173b4` is the pop-up text: it stores sx, sy at `$20756` and prints the string after them through `$182ea`
(read). Run `bash reversing/virus/py/painter/gate_painter.sh` (about 1 minute).
The actor loop queues only the records inside a window around the camera (gated: `behaviours.md`, "What the 3D view shows").

### Model data and the model drawers (gated)

The 43 object models lie back to back at `$aa72..$ce9a` (9,256 bytes; walked by their own header words with no gap, ending
at the 1-pixel mask table `$ce9a`; none below `$aa72` in `$8000..$27000`). A record, all words big-endian: byte +0 flags
(bit 0 rotated by the matrix `$270d4`, bit 1 casts a ground shadow), +2 vertex count - 1, +4 face count - 1, +6 the face
list's offset (always 8 + 6 * vertices), then 6-byte vertices (signed x, y down, z away) and 22-byte faces: a normal
(three 1.15 words), three longs `$27154 + 8 * i` that address vertex i's projected slot (every face is a triangle) and a
colour long (0..15 a palette entry, 16..23 the span routines' checkers; the models use 0..20 and 22). The per-type table
is the 64 longs at `$23f98`, indexed by the object-map byte `& $3f`: plain, damaged (grey wrecks `$afc8`, `$b01a`, `$b06c`
and others) and infected forms (`$b23e`, `$b1ca`, `$b2f6`, `$b348`, `$b400` for types 1 to 5; types 6 to 12 repeat the
plain model). 17 models are rotated (the ship `$ab62`, the actors, the bomb, the rocket); the rest are scenery and plumes.
Names of the non-scenery models come from the routine that points at them (`py/models3d/refs.py`), not from the shape.

`Model_Draw` `$26296` clears `$62a69` and falls into `Model_DrawRotated` `$2629c`, which goes to `Model_DrawUnrotated`
`$264e2` when flag bit 0 is clear. The rotated vertex loop (`$262bc..$263b0`) multiplies each vertex by the matrix rows in
1.15 (`muls`, `swap`, doubled, 16-bit wrap), adds the position (dx, dy, depth) and projects sx = (x << 8) / z + `$a0`,
sy = (y << 8) / z + `$46` (the grid's projection) into `$27154 + 8 * i`; with flag bit 1 the shadow vertex is projected at
the ground height (`$245b8` for rotated models, `$24754` for unrotated) into the slot's second half. The face loop rotates
each normal, fills a shadow triangle at once in colour 0 when the rotated normal's y is >= 0, and keeps a face whose
normal dotted with the position is <= 0 in the list at `$32754` (14 bytes a face). `Model_PaintList` `$264c4` paints that
list in order, so faces paint in data order with no depth sort; the deferred record `$261d2` sets `$62a69` and leaves the
list for the later record `$2620e`. The unrotated drawer adds the position only and draws every face, shadow first, with no
cull. `Tri_FillFlat` `$26780` rejects or clips against 320 x 184, sorts by y, steps the edges with the slope table
`$5ab58` and calls the `$1f2bc` span routines (above). Read, not gated: `$265e4` and the second triangle filler `$26972`
(the attract loop `$24c76` only), the clip branch `$26756`, and the below-ground flag `$62a61` the ship's model sets.

Gate `models3d` (`py/models3d/gate_models3d.sh`, about 40 s) predicts, for every model drawn, the vertex array at `$27154`
and the whole stream of `$26780` calls (six screen words and the colour index, in order) and compares them with `stserver`
stops: on natural frames `fl/f1` 1,853/1,853 vertices, 1,656/1,656 shadows, 251/251 streams and `main_g050` 3,757/3,757,
2,102/2,102, 386/386 (seven more snapshots matched as well in the agent's runs: `fl/f2`, `f3`, `g_game2`, `S1b`, `death/E1`,
the two pilot ends); all 43 models called directly in 40 random poses 14,680/14,680, 10,800/10,800, 1,720/1,720. Control
(the matrix transposed): `f1` 1,456/1,853, 1,259/1,656, 202/251; the poses 8,671/14,680 and 1,044/1,720. No pixels are
compared; the fill is the gated tile filler's span set. `py/models3d/virus_models.fsx` renders each model and two contact
sheets to SVG from a dump of the chain and the live palette (`dump_data.py`): a fixed 3/4 view with the stored normals
culled and faces sorted by centroid depth, which differs from the game's data-order paint for the unculled scenery
(`models3d.png`).

## The flight model (gated, mouse run; autopilot poked)

The ship tick is `$255c2`. The ship state is `$270b0`: x, y, z, vx, vy, vz (words). The input routine returns a target
attitude (D0 the tilt from vertical, D1 the heading, `$10000` a full turn) and flags (D2 bit 0 fire, bit 1 thrust) at
`$255d4`; the model gates what follows. y grows downward: gravity adds to vy and thrust at tilt 0 subtracts 15 a tick.

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
`$20f26..$20f64` (read; only the value 3 is seen in the run). The tick takes the target tilt and heading as plain words with no range check.

The mouse routine `$254aa` (`Input_Mouse`) tests `$62a5b` (nonzero: the keyboard reader `$2554a`), else reads the accumulated
mouse position through `$1fa54`: x and y words at `$1fa4a` (start `$80`, each IKBD packet added, no clamp), buttons in D2. A
displaced mouse is a held target, not a rate: the accumulator is recentred (`$1fa38`) only by the pad path, game start and a
new life. Each offset `(v - $80) << 8` is a word whose sign goes into an octant word; the heading is that octant word plus
`$d8fa[((min << 16) / max >> 8) & $fe]` (an arctangent table of 128 words, 1.0 at `$2000`), and equal magnitudes (a centred
mouse included) give `$2000`. The tilt is D0 = 2 x min(`$d9fa[((dx^2 + dy^2) >> 20) & $fffe]`, `$3fff`) (a square-root table),
so even values 0 to `$7ffe`. Proved by `py/flightctl/mouse_model.py` (gate `flightctl`) on `fl/f1.snap`, 300 random `mouse move`
inputs of up to 127 per axis, 180 of which reached `$255d4` (the rest gave up at the cap while the ship died): the model equals
the game's D0 and D1 on 180/180 stops (171 with a non-centred target); controls: axes swapped 10/180, wrong tilt shift 9/180;
the accumulator equals the previous one plus the move on 170/170 adjacent stop pairs. The keyboard path `$2554a` is read only.

`$2538c` is a second input routine that picks the target and flags from the ship's position against a target list at
`$270a6`, and `$62a5f` selects it in place of the mouse routine. **Poke:** `wb 62a5f ff` on `fl/f1.snap`. A `hits` run
of 300,000 steps then counts 10 entries of `$2538c` and 0 of `$254aa`, and the same tick model matches position, velocity
and attitude 119/119 (the thrust ticks 14/14, the others 105/105); control (thrust `>> 4`) 105/119. This is a poked result, not
a played one.

`$270d4` is the renderer's current rotation matrix, not a stored ship property, so its match count depends on where it is read.
The tick builds it from the new attitude at `$25654` (`jsr $1f646`) and the model equals it exactly: 119/119 on `S1b.snap`
read at `$25660` (control, yaw and pitch exchanged, 5/119: the identity attitude at the start). Before the next tick it is
rewritten by `Autopilot_Steer` `$22c1e` (a `$1f646` call once per patrol actor), and by the draw records `DrawRec_ModelDeferred` `$261d2` and `DrawRec_Model` `$26222`
(which load a 9-word matrix from the draw stream), and `$26256` builds it from two angles. A `watch 270d4 18` over 3,000,000
steps names no other writers. At 114 of 118 `$255d4` stops of the demo the last writer was a steering build and the matrix
equalled the model once (an identity coincidence); the other 4 stops are the identity attitude (`py/flightctl/matrix_writers.py`,
gate `flightctl`). So the 4/119 above is a measurement point after other writers, and the attitude words are the ship's
orientation at a tick boundary. The mouse run matched 119/119 because nothing else wrote the matrix after the tick there
(inferred: no patrol steering on the pad snapshot's side).

### Off the capture, and where free flight ends (gated)

`py/mpc/replay.py` drives the game through `stserver`: at every arrival at `$255d4` it overwrites the low words of D0, D1 and D2
with a control sequence and records the state, so any flight can be flown and compared with the model. An interrupt taken
exactly at `$255d4` returns to it and stops the breakpoint a second time after a few steps with the tick not run; the harness
counts a return in under 64 steps with no marker passed as the same tick. `py/mpc/exact.py` is the tick as functions
(`step_full`, and `step_game` with the conditions below). Gate `mpc_flight` (`bash reversing/virus/py/mpc/gate_flight.sh`,
fresh replays from `fl/f1.snap`):

- The capture replayed with its own recorded controls: 120/120 states on position, velocity, attitude and fuel. With no
  overwrite 0/120; with the thrust bit cleared position and velocity 0/120 and attitude 120/120. Capture stop j is arrival
  j + 1, and tick 0's controls are not in the capture: they are taken to be stop 0's (inferred).
- 21 seeded control sequences that the capture does not resemble (slow random inputs, fire, any word for D0 and D1, dives,
  low passes) and a scripted landing: 6,631 free-flight ticks, 6,631 equal on position, velocity, attitude and fuel, of
  which 475 are inside the low band and 1,309 above the ceiling. The 17 deaths are named by cause by the model in all 17.

The model is exact until one of these, with c = ground(x, z) - `$56` - y after the tick's move (`exact.clearance`):

- **A hull vertex below the ground** (5 deaths; the flag equal on every tick). The ship's draw routine (`$2629c..$264b6`,
  shape `$ab62`, nine vertices) rotates each vertex and sets `$62a62` when it is below the ground under that vertex; the next
  tick dies at `$257fe`. Tilted or over a slope this comes before c reaches 0 (deaths at c = 56 and c = 40).
- **c < 0** (the ground-contact paths `$25870` and `$25c28`; 9 deaths, 1 landing). The ship dies unless vy after gravity is at most `$28`, vy + |vx| + |vz| is at most `$28`,
  and x and z are both below `$800`; then it lands: y := `$3ca`, velocity 0, latch `$62a63` cleared.
- **0 <= c <= `$170` over an object cell** (3 deaths, 475 safe ticks): the byte at `$32a58 + ((x + $80) >> 8) + ((z + $80) &
  $ff00)` with any of its low five bits set and bit 4 clear.
- **On the pad** (`$25a6e`; 39 ticks, one run): latch clear and no thrust refuels by `$19` a tick up to `$1000`, holds y and ignores
  the inputs (the poked refuel run is in the table below); thrust sets the latch and the normal tick resumes.
- **Above the ceiling**, y < `$c900`: the thrust bit is dropped for that tick. **Fuel**: thrust needs 3 and costs 3, fire
  costs 1; with less there is no thrust and fuel becomes 0 (6/6 ticks, fuel poked to 7).

No code outside the tick wrote the ship's state, attitude or fuel in these replays; enemy contact is in `behaviours.md`,
"The player's shot, the targets and the ship box". Landscapes 1 and 2 and g other than 3 were not flown.

The ground the tick tests is the sum-of-sines height `$245b8` (`Landscape_SumOfSines`), not the cell height map. A raw scan of
code `$c000..$27ffe` for the longword `$42a58` finds the builder's `$23424` and `$24730`/`$2475e` (inside `$24754`,
`Landscape_HeightAt`) only; `$245b8` is called from the tick at `$257ee` and from the ship's vertex test at `$26378`, and none of
the 19 `bsr`/`jsr $24754` callers lies in the tick (read: raw scan and `tools/find_ram_callers.py`). `$245b8` returns the height
in D1 and a surface type in D3 (9 land, 7 shore for `$510 < h <= $560`, 8 water: h clamped to `$560`, the pad cells from
`$246ba`); the tick ignores D3, so a crash into water is the same branch as one into land, with D1 = `$560`.

The exits of the tick, each a code address and an entry count (`py/flightctl/death_census.py`, `hits` over an unpoked attract
game, taken branch = count at the branch minus count at its fall-through; gate `flightctl`):

| exit | address | what leaves the tick there |
|---|---|---|
| ceiling cut | `$255de` | `bclr #1,D2` while y < `$c900`; D2 `$2` becomes `$0` on `fl/f4.snap` at y `$9bb0` (proved, `py/flightctl/pad_ceiling.py`) |
| pad | `$25a6e` `Ship_PadHold` | latch clear and no thrust: `Mouse_Recentre` `$1fa38` when the target is not within `$19` of 0 (the mouse heading `$2000` always is), sound `$1d`, fuel + `$19` stored at `$25aae` while the sum is at most `$1000`, y := `$3ca`, vy := -g, back into the tick at `$25654`. No pad refuel occurred in the 126 census lives (`demo.md`, "Why the demo loses its lives"): the pilot does not land to refuel |
| enemy | `$257fa` | `$62a5d` nonzero goes to `$25ad8`. Four stores set it: `$20360` (enemy shot inside box `$c0`, fuel minus `$333`, set only on borrow), `$2083c` (bomb within `$400`, the same), `$21654` (`Pool_CommonTail` contact, unconditional) and `$225e6` (attractor drain to empty); in 126 census losses shot 25, contact 21, bomb 5, attractor 2 (`demo.md`, "Why the demo loses its lives") |
| vertex | `$257fe` | `$62a62` nonzero goes to `$25ad2`; `$264b6` ORs it from `$62a61`, which the ship model's draw sets at `$2638c` when a vertex is below the ground (13 of 126 census losses) |
| object cell | `$25846` | the object-map byte kills (`$25850` calls `$23c08` for type 11): with bit 5 clear it branches to `$25ad2` at `$25862`; with bit 5 set `$25866` calls `$2004a` and goes to `$25ad8` with `$62a5d` clear (3 of 126 census losses, all by the `$2004a` route) |
| ground contact | `$25870` `Ship_GroundContact` | c < 0: vy > `$28` dies at `$25ad2`, else `$25c28` `Ship_LandingTest` lands (`$25c52`) or dies |
| death | `$25ad2` `Ship_DieLowered`, `$25ad8` `Ship_Die` | y -= `$56`; clears `$62a5d`, `$62a62`; sets latch `$62a63` and `$62a5e`; explosion `$202a4`; 50 frames of the frame routines (`$25b12`, SPACE skips them); `$25ba0` takes a life |

Proved on the pad snapshot `drive/g_game2.snap` (`py/flightctl/pad_ceiling.py`): unpoked, 2 pad ticks and 0 refuel stores (fuel
`$0ff4` plus `$19` exceeds `$1000`); with the fuel word poked to `$0100`, 2 pad ticks and 2 stores, fuel `$0132`; with the left button
held, 0 pad ticks and 5 thrust-path entries in 5 ticks. The landing and the 39 pad ticks are the `mpc_flight` replay (618/618).
In three unpoked attract games (`chain/long100/starts/main_g001..003`, 600 to 640 million steps) the 16 lives lost split as 6
enemy exits, 8 ground contacts at vy > `$28` (one of them over water, `D3` 8, `D1` `$560`, y `$520`), 1 ground contact that
failed the landing test (vy `$21`, speed sum `$36`, over water, x above `$800`), and 1 vertex exit; no object-cell kill and no
landing occurred in them. The gate `flightctl` reruns games 1 and 3.

A plain floating-point copy of this tick is not a usable stand-in for it. `x - (x >> 6)` floors, so each tick keeps on average
about half a unit more velocity per axis than `x - x/64`: a 300-tick flight planned through the float copy to end within 216
units of a waypoint ended 14,712 units from it in the game, and 3,092 with the mean of the floors added to the float copy
(one start, one waypoint; the game equalled `exact.py` on 301/301 ticks of each replay). Record, not a gate: the planner
scripts are in `scratchpad/virus/mpc/plan/`.

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

## Landscape selection by wave (gated on natural play; landscape 2 poked)

`$32a50` is the wave counter: `$20fd0` increments it (wave-end code `$20fb4`, `behaviours.md`), it is passed to the wave-start
routine `$20e74` at `$210ee` and read for the HUD at `$24906`, and it is 0 at the start of wave 1 (game over zeroes it at
`$25bf0`). `$20e74(n)` appends the wave's waiting enemies from the 16 blocks at `$20e34` indexed by `n & 15` (per kind in
`behaviours.md`) and then, in its tail at `$20f24..$20f80`, sets the gravity `$32a3a`, calls `$2336a(1)` when `n == 4` and
`$2336a(2)` when `n == 9`. Both tests compare the unmasked `n`. Game start and restart call `$2336a(0)` (`$23092`, `$230b4`,
`$25bf6`).

`$2336a` stores its argument in `$32a4e` (the selector) and, when `$32a4e` equals `$32a4c`, branches past the instruction
patching and the height loop to `$23452` (`$23376..$2337c`; read). `$32a4c` is written only at the end of the height loop
(`$23448`), so it names the landscape whose height map is in RAM. Every call, skipped rebuild or not, still clears the object map
at `$23452` and runs the scatter (`jsr $236f8` from `$2346c` on), which is why the restart's second call (scatter B, `demo.md`
"Natural death and game over") lays out a new map on the landscape already built.

**Natural play** (`py/landscape/natural.sh`, game 050 of the unpoked chain, `watch 32a4c 6`; output through
`py/landscape/gate_landscape.sh`): the counter is written 1, 2, 3, 4, then `$32a4e` = 1 at `$2336a` and `$32a4c` = 1 at
`$23448`, then the counter 5: exactly seven writes, so a played game reaches counter 5 and landscape 1. A longer unpoked run
of the same game (continued through the game over; not in the gate) wrote `$32a50` = 0 at `$25bf0` and rebuilt landscape 0
through `$2336a(0)` (both selector words 0), then called `$2336a(0)` again at `$230ae`, which wrote neither selector word (equal words: the height loop is skipped). Games 014 and 045 reach counter 4 with
landscape 1 built (`py/landscape/chain_waves.sh`: map 65455/65455 against the model for each; run once, outside the gate).

**Poked** (labelled: `py/landscape/poked.sh`, `ww 32a50 0008` at a natural `$20fb4` stop, then an emptied pool so the wave
ends): the counter 9 builds landscape 2 (`$32a4e` = `$32a4c` = 2, map 65455/65455 against the model), and counters 10, 15
and 16 leave both words at 2 (counter 16: `n & 15` = 0 gives wave 0's block, 5 records, gravity 6, landscape unchanged). The
earlier poked-stub run (`moveq #n,D0 / jsr $20e74 / rts` under `callcap`, `capture.sh`'s `cap/cc_n<n>.json`) agreed: both
words stay 0 for n = 3, 5, 10 and become 1 for n = 4 and 2 for n = 9. A wave is completed by destroying every enemy except
the unhatched chasers (`$20f82`, `behaviours.md`).

## Demo mode and the autopilot

The demo is an attract mode: 769 idle frames of the title loop set the flag `$62a5f`, and the next game is flown by the
autopilot `$2538c` through the same flight tick as the mouse. It is covered in its own doc, [`demo.md`](demo.md): how
the demo is entered, the pilot's routines and rules, runs to the pilot's natural death, a chain of six complete games
with no pokes (no trend in survival or score; a weak test), and what carries over a game over (the high-score table,
the infection target queue at `$27134`, the random state). Its scripts are in `py/demo/`.

## Which code runs

A call census of one complete unpoked attract game (chain game 050, `scratchpad/virus/chain/long100/starts/main_g050.snap`:
waves `$32a50` = 0 to 5, 1.23 billion steps including the game over and the start of the next attract game), plus the
game-over path from `demo/death/long7.snap` to the next `$230c0` (49,998,717 steps) and 12M-step windows of
`drive/g_title.snap` and `drive/g_press.snap`. The call and branch events come from `ATARI_TRACE_EVENTS` (DEVELOPING.md),
taken in 10M-step chunks chained through a rolling snapshot and reduced to counts; the chained run reproduces
`chain.jsonl`'s life losses (chunks 19, 30 and 62 against steps 194.8M, 304.7M and 478M).

- **217 routine entry points** (targets of `jsr`/`bsr`) lie in `$c000..$27ffc`; 92 are reached by direct calls and 125
  only through `jsr (An)`, so the static listing's 154 direct targets miss every behaviour-table and span routine. 21.6M
  calls in all; 42.6% are indirect, and 49.5% go to routines with no `.sym` name.
- **Executed code is 31,228 of the 114,686 bytes in `$c000..$27ffd` (27.2%)**, nothing below `$16fb4` (that range is
  tables and data) and 44.8% of `$16fb4..$27ffd`. The figure is a lower bound: a flow-only log does not count the operand
  words of the terminating `jsr`/`jmp`. A flight wave runs 20 to 23% of the window, the game-over path 7.0%, the title 5.3%,
  the "press" page 16.0%.
- **No new routine appears after wave 3** (`$32a50` = 3): 131 targets run in every wave, 17 first appear in wave 1, 3 in
  wave 2 and 3 in wave 3, none after. 19 targets run only outside flight (title, press, game over, attract restart).
- Measured (`py/census/`, counts above from one game): the numbers are one game's bound, and a routine entered by `jmp`
  or a branch, never by a call, is not in the 217.

Commands (from `M68000/`; `py/census/gate_census.sh` runs the bounded window below, about a minute, into
`scratchpad/virus/census/gate/`):

```
bash reversing/virus/py/census/run_chunks.sh g050 scratchpad/virus/chain/long100/starts/main_g050.snap 123 10000000
bash reversing/virus/py/census/run_chunks.sh over scratchpad/virus/demo/death/long7.snap 1 49998717
bash reversing/virus/py/census/run_chunks.sh title scratchpad/virus/drive/g_title.snap 1 12000000
bash reversing/virus/py/census/run_chunks.sh press scratchpad/virus/drive/g_press.snap 1 12000000
.venv/bin/python reversing/virus/py/census/aggregate.py
```

The full run (about 8 minutes, one process) writes `scratchpad/virus/census/routines.csv` (calls per wave, `.sym` name, doc
mention count, call-site count), `ranked_unnamed.txt` (the to-do: unnamed targets in call-count order, led by the
span-cap and point-plot families) and `coverage.txt`. The gate window (game 050 to its first wave change, 50M steps, plus
the game-over path) gives 194 targets in the code window and 21.9% of the window executed. `virus.sym` names 101 of the 217
targets of the full run (`aggregate.py`'s first line; the `named` column of `routines.csv`); the 116 unnamed ones are mostly the
span-cap routines of the tile filler.

## Open questions

1. The landscape-cell records (`$26278`, `$261d2`, `$2620e`) are not gated against the object map, and the model drawers' read-only parts (`$265e4`, `$26972`, the clip branch `$26756`, the below-ground flag `$62a61`) are not driven ("Model data and the model drawers").
2. Landscape 2 is reached only by a poke of `$32a50` (no chain game gets past counter 5): a natural game to counter 9
   (landscape 2, wave HUD 10) would close it.
3. The tick's exits are named and counted (section above), but the enemy exit `$257fa` (6 of 16 deaths in three games) was not
   stepped into to name which of its writers (`$20360`, `$2083c`, `$21654`, `$225e6`) set `$62a5d`; the object-cell kill
   `$25846` had no event in three demo games; the keyboard input `$2554a` is read only.
4. The type names come from the shapes drawn; the radar role of type 11, the natural type-12 cell on screen and the
   vertical foot offset of types 2, 7 and 8 are open. The actor behaviours are named from their bodies in `behaviours.md`;
   the seeder, the chasers, the pursuers and the patrol states are gated; the bomber, the attractor and the damaged pursuer are not.
5. The pad table is modelled and read-gated (below); which tile each entry recolours is open: the changed pixels of a poked
   entry lie nearer than the main grid block's first row, so the front and side vertex blocks of `$24098` (`$24168..`) draw
   the pad cells too and were not read.

## Files

| file | contents |
|---|---|
| `README.md` | this file |
| `drive.sh` | cold boot to the wave-1 launch pad (writes `scratchpad/virus/drive/`) |
| `gates.toml` | the gate `tools/gates.py` runs |
| `behaviours.md` | the actor pool's behaviours, waves, demo-flag readers, draw-list residue |
| `py/scan/` | that doc's census, wave-end, watch and residue scripts |
| `frontend.md` | the three frame routines, HUD, font and text, sound driver and effect sites, title page, game over, hall of fame, score code |
| `py/frontend/` | that doc's scripts and `gate_frontend.sh` |
| `virus.sym` | names |
| `py/README.md` | each script, its command and expected line |
| `py/capture.sh`, `py/gate_all.sh` | fresh captures; every model with its control |
| `py/mpc/` | the replay harness, the tick, shot and actor models as functions, and gates `mpc_flight` and `mpc_shot` |
| `py/virus_terrain.py`, `virus_objects.py`, `virus_grid.py`, `virus_tiles_check.py`, `virus_slope.py`, `virus_flight.py`, `virus_particles.py` | the models and gates |
| `py/render_heightmaps.py`, `py/vcommon.py` | the heightmap renderer; shared paths |
| `py/shading/`, `py/painter/`, `py/flightctl/`, `py/landscape/`, `py/objects/`, `py/behaviours/`, `py/census/` | one gate each (`gate_<dir>.sh`, gates of the same names): tile colour and spans, depth buckets and paint order, mouse and ground contact, wave table and bonus, object types and the object pool, mothership and chasers, which code runs |
| `objects.png` | object types 1 to 9 and 11 as the game draws them, and their damaged and infected forms (`py/objects/objects_montage.py`) |
| `models3d.png` | the 43 models of `$aa72..$ce9a` rendered outside the game from their own vertex and face data (`py/models3d/virus_models.fsx`, `sheet_filled.svg` through `qlmanage -t -s 1400`) |
| `heightmaps.png` | landscapes 0, 1 and 2 from the model (256 x 256 cells each, 2x; white is water) |
| `title.png`, `pad.png`, `flight.png` | the title picture, the wave-1 launch pad, a flight frame with exhaust |

# The base generator, `fed_MapGen`

`fed_MapGen` builds every base Captive puts on a planet, and the planet surface around it, into one 64x32 grid.

**How it builds a base:**
- The grid is cut into 16 blocks of 16x8 cells. Each block is given to one of up to five floors.
- A random walk grows each floor over the blocks.
- Lifts join consecutive floors by a fixed translation.
- A turtle "digger" then carves single-width corridors that never break into another passage, and drops rooms and
  lifts as it goes.
- Every carved cell keeps the number of the dig step that made it. The generator turns those numbers into a flow
  field: from any cell, following the arrows walks the dig backwards to the entrance.

The whole base is a function of one 16-bit argument: the same argument gives the same base. Addresses are runtime
addresses with the module loaded at `$1f7b0`, as on landing in `scratchpad/captive/mg_entry.snap`. The module's
variables are at A6 = `$20376`; federation's are at A6 = `$1b5ce`, written `fed N(A6)` below. Proofs name a script
in `py/mapgen/` (its README gives each command and expected output); the rest is marked inferred.

![a five-block base](mapgen_base_d0_5.png)

`mapgen_base_d0_5.png` shows D0 = 5. The other examples are `mapgen_base_d0_1.png` and `mapgen_base_d0_12.png`.
- Colour: floors 1, 2 and 3 are blue, green and orange, with rooms lighter.
- White cells are lift ends; the red cell on the top row is the entrance.
- Grey lines are block walls between floors; black is rock.

## Call interface and seeds

`federation` loads the module into the buffer at `fed 15770(A6)` and calls it at `$b5c2` with `jsr 32(A4)` (code
offset 0). The arguments come from `$b574`-`$b5c0`.

| register | value | meaning |
|---|---|---|
| A0 | `fed 9242(A6)` = `$1d9e8` | base of federation's output regions |
| A1 | `$b532` | table of 14 signed word offsets |
| D0 | `fed 32(A6)` | base seed |
| D1 | `fed 14790(A6)` | surface seed |
| D2 | mode | from `fed 13564(A6)` |
| D3 | `fed 14776(A6)` | |
| D4 | -1 | the init path; `$20054`: `tst.w D4; bpl` skips it |
| A2 | `$303c` | the depacker |

The A1 offsets are accumulated into 14 pointers at `13684`..`13740(A6)` (`$20092`-`$200e6`).

The mode is computed as follows:
- `fed 13564(A6)` = 2 gives D2 = 6.
- 0 gives D2 = 14 (landing; the mode becomes 2).
- 3 gives D2 = 0.
- Any other value gives D2 = 2.
- With `fed 14782(A6)` = 0 the mode becomes 3 and D2 = 1.

The module stores D0 at `12408(A6)` and as the RNG seed at `12404(A6)`, D2 at `12412(A6)`, D2 & ~1 at `13276(A6)`,
D1 at `13280(A6)` and D3 at `13278(A6)` (`$2006a`-`$2008a`).

`fed_MapView` sets the seeds (`$2f636`-`$2f65a`; driven for mission 1, target 1: D0 = 0, D1 = 0, `world.md`
"Targets and landing seeds"):
- D0 = `fed 14776(A6)` × 11 + the target index. The index is 10 for the special target at `$2f67c`.
- D1 = (`fed 14776(A6)` & `$1ff`) × 150 + the object index, or `$ffff` when there is none.
- `fed 14776(A6)` is stepped by `$8804`: inferred to be the mission number.

**Branches on the mode.** Bit 1 of `13276(A6)` (`$23c78`) separates the base path from the surface path at `$23d58`:
- **Base (D2 = 0 or 1):** depends on D0 alone. Proven with `cmpcases.py`: D1 = `$1234` and D3 = 7 give a result
  byte-identical to D1 = 0 and D3 = 0, and two runs with the same arguments differ in 0 bytes. D2 = 1 adds the stage
  `$2676c` (`$23cde`), a 39-byte difference in the tile layer for D0 = 1.
- **Surface (D2 = 2, 6, 14):** re-seeds the RNG from D1 (`$23d58`). D2 = 2 is a target's compound, the walled area
  around the base entrance: in play (`py/ai/natural_base.repl`, D0 = 0, D1 = 0) it returns D0 = 48, D5 = the
  entrance cell (22,22) and D6 = the start (23,18) (`ai.md`, "Getting into a base"). D1 = `$ffff` builds the uniform landing surface:
  tile `$1e` everywhere, start (32, 16) in D6 (`$23d82`-`$23d86`). D1 = 164 and 165 differ in 406 tile bytes; at
  D2 = 14, D3 = 1 and 2 give identical output (`cmpcases.py --all`). D3 is read only by `$23e36` and `$23e80`; the
  surface generator past `$23d94` is not read.

**Running it.**
- **Shortcut call.** `gen.py` calls `$20054` directly, from `mg_ret.snap`, with the caller's registers (labelled
  pokes). It skips the Copylock prologue at code offset 0, which is the only part that reads the disk.
- **Proof against the landing call.** For the landing arguments the shortcut rewrites every output region to the
  natural call's bytes: G0, G1, G2, both federation layers, the module variables and federation's tables
  `$1bd3e`-`$1d9e8`. The outputs are pre-filled with `$5a` first (`cmp_ret.py`: 8 of 8 regions equal).
- **Proof against a base-mode call.** For a natural base-mode call (`scratchpad/captive/agents/ai/req4_mg.snap`:
  D0 = 1, D1 = `$ffff`, D2 = 0, stopped at `$b5c2`, mode request poked), the shortcut's two layers equal the later
  `req4.snap`'s on 2048/2048 bytes each, ignoring bit 7 (which federation sets in play; `flowfield.py --snap`).
- **Cost.** A base costs about 2.6M to 4.7M instructions (D0 = 1, D2 = 1: 2,644,857); the landing surface costs
  234,362.

**Where the code lives.**
- The prologue runs Copylock-style trace decryption over `$1f84e`-`$2003e`. From `$20040` the module ships in clear:
  RAM at `mg_entry.snap` and `mg_ret.snap` is identical over `$1f7d0`-`$20376`.
- The module's own variables (`$35bc` bytes, cleared at `$20064`) overlay the file from `$20376` to `$23931`. The
  generator's code is `$20040`-`$20366` plus `$23936` to the end.
- The prologue supplies the argument registers through `$20376` (`$2004e`) and no seed.

## Floors and lifts

**Random numbers.**
- `$23b96`: x = (x × `$5e5` + `$29`) mod 2^16 in `12404(A6)`, returning ror16(x, 4) xor `$800`. In the base path it
  is seeded with D0.
- A second stream with the same LCG at `13656(A6)` starts at 0 and returns ror16(x, 3) (`$245ce`).

**Blocks (`$2011e`).** Module bytes `0..15` hold one floor number per 16x8 block, row-major over a 4x4 grid.
- **Base size.** The mask table `$20110` (`cc00 f600 ff00 ff60 fff0 fff6 ffff`), indexed by min(D0, 6), gives the
  blocks in the base: 4, 6, 8, 10, 12, 14 or 16, bit 15 first. The others get 6, meaning outside.
- **Floor count.** 2 + (r & 3) floors, or 1 when D0 = 0.
- **Floor growth.** Each floor starts on a random empty block (`$20328`). It walks one block at a time in a random
  direction (`$2033e`, steps at `$20366`/`$2036e`), claiming empty blocks and passing over its own. It stops when it
  leaves the grid or meets another floor.
- **Leftovers.** When the walks leave blocks empty, each copies a random in-grid non-empty neighbour, possibly 6
  (`$2019a`-`$201da`).
- The floor count actually placed is stored at `46(A6)`.

**Lift offsets (`$201de`).** For each floor k below the last, one random block of floor k and one of floor k+1 are
chosen. Their block difference × (16, 8) is stored as words at `16(A6)` + 2(k-1) (x) and `24(A6)` + 2(k-1) (y). The
lift routines add these offsets going up (`$2514c`) and subtract them going down (`$25136`). A lift therefore keeps
its position within its block, and the two ends of a shaft lie in different blocks of the one grid.

**Entrance (`$20252`).** A random column 0..63 with (col & 15) ≠ 15, on row 0, stored at `32(A6)`; its block's floor
is at `34(A6)`. D0 = 0 replaces the table with a single column of floor-1 blocks (1, 5, 9) and the column with 30.

**Block walls (`$202a2`).** G0 gets `$ffff` along a block's right column and bottom row where the neighbouring block
is on a different floor, and 0 elsewhere.

**Proofs.**
- `zones.py` is a Python transcription of all of the above. `zones.py gate 0 1000` matches the emulator on module
  bytes 0..55, the RNG word and all 4096 bytes of G0 at `$202a2`'s return, for 1000 of 1000 seeds.
- Every lift end has its partner on the adjacent floor at exactly that pair's offset: `liftpair.py 0 41`, 510 of 510
  lift cells over D0 = 0..40. Lift-end features are 4 (up), 5 (down), 6 (both), and `$35`-`$37` on room floor.
- That floors are separate levels is inferred: federation's automap (`$10ff4`) draws only the cells whose block's
  floor, from its copy of the table at `fed 9206(A6)`, equals the current floor `fed 15688(A6)` & 7. The words
  "floor" and "lift" are this doc's; the game's strings do not name them.
- Module bytes 0..33 are copied to `fed 9206(A6)` at `$200f2`. The caller reads the entrance column from
  `fed 9238(A6)` into the position at `$b5d6`.

## The digger and rooms

**Proven by measurement.** `$244b6` (from `$23cb0`) is the bulk of the work: 1,708,805 of the 2,644,857 steps for
D0 = 1, D2 = 1 (`stages.py`). It writes 891 of the G0 bytes; no other stage moves more than 64 (`stagedump.py`).

**The digger (inferred from the code).** It is a turtle with:
- a position (D1, D2);
- a floor D3, starting on the entrance (`$244be`-`$244c4`);
- a heading at `12424(A6)`: 0, 2, 4, 6 for N, E, S, W, with the dx, dy tables at `$248c4` and `$248cc`; it starts
  facing E;
- a counter D4 that starts at 1.

**Carving.** `$24f3c` writes D4 into G0 and increments it. The entrance is carved twice (`$244e6`, `$244f0`), so it
holds 2 (observed in 4 of 4 bases, `bases.json`). In G0 a positive number is the dig order. 0 is rock, `$ffff` is a
block wall, and `$ffc4`, `$fffd`, `$fffe` are markers written by the room and structure code.

**Each step (`$24872`)** draws a random word into `12426(A6)` and, from its low bits and size:
- turns left or right;
- places a lift up or down (`$248f0`/`$24902`, only when the word is above `$ccb0` and D4 > 4), carving the far end
  on the next floor through the offsets;
- builds a structure (`$24c5c`, word ≤ `$7ad`);
- builds a room (`$249da`, word ≤ `$8f48`);
- otherwise moves one cell forward.

**The carve rule.** A cell is dug only when exactly 3 of its 4 neighbours are uncarved (`$24e8c` counts them,
`cmp.w #3,D6` at `$24514`). The cell must touch nothing but the cell it is dug from, so corridors never merge or loop:
the classic perfect-maze condition.
- **On failure** the digger restores its position (`$24d88`) and retries a random turn, 10 times (`$244f4`).
- **Then** it tries up to 100 random cells (`$2452a`). When the second RNG exceeds `$a200` it restarts from a carved
  room, lift or `$11` cell (features `$1f $35 $36 $04 $05 $33 $11`, `$24552`-`$24588`). Otherwise it restarts from
  any uncarved cell that touches exactly one carved cell.
- **Budgets:** 300 restarts (`12414(A6)`), 900 lifts (`12416(A6)`), and D4 ≤ `$3000`.

**Rooms (`$249da`).**
- **Size:** w × h. Let s = (r ror 6) & `$3f`, masked with `$1b` when r > `$3ff7`, where r is the step's random word.
  Then w = (s & 7) + 1 and h = ((s >> 3) & 7) + 1 (`$249de`-`$24a6a`).
- **Check, then carve:** every cell is first checked with the same neighbour test, and a failed check abandons the
  room. Then the rows are carved.
- **Pillars:** a room with w > 1 and h > 1 takes a pillar pattern from the bit table at `$24c1c` (row offset
  r & `$38`). Pillar cells stay rock, with feature `13652(A6)`: 0, or `$20` when r rol 2 exceeds
  `$eeff` - 8·min(D0, `$7f7`) (`$23bc6`, `$24a06`-`$24a18`).
- **Floor feature:** `$1f`, or `$33` for some rooms when D0 > 4 (`$24a22`-`$24a3e`).
- **Room list:** up to 63 rooms are recorded at `12952(A6)` as (x, y, floor, feature), counting down from `13208(A6)`.

What the rule produces is visible in the PNGs: single-width winding corridors with no loops, rectangular rooms, and
lifts between floors. The tree property itself is not counted.

## The flow field (plane 2)

`$24f4c` runs after the digger. For each cell whose G0 is neither 0 nor `$ffff`:
1. It looks for a better candidate, starting from a best of `$4000`:
   - first the lift partner on the floor above (value 4, features `$1c $37 $06 $1a $35 $04`);
   - then the lift partner on the floor below (value 5, features `$1c $37 $06 $1b $36 $05`);
   - then, unless the feature is `$1c`, `$1a` or `$1b`, the neighbours N (0), S (2), E (3) and W (1), in that order.
   A candidate counts when it is open and its G0 ≤ the best so far (`$250f6`); it then becomes the best and its value
   is kept.
2. The value goes into G2 byte 0.
3. A cell with no feature gets feature 7.
4. The entrance's G2 word is cleared (`$25010`-`$2501a`). The cells listed at `13410(A6)` (5 groups of 5 (x, y)
   pairs) get 4, or 5 after a feature-`$1d` cell in their group (`$2503c`).

Each arrow therefore points one step down the dig order, and following the arrows retraces the digger's path back to
the entrance, riding a lift where the dig did.

**Proof.** `flowfield.py` transcribes this and matches the emulator on every open cell:
- 43,832 of 43,832 cells for D0 = 1..40 with D2 = 0;
- 44,053 of 44,053 for D0 = 0..40 with D2 = 1;
- no later stage changes G2.

**Consequence.** The 4 and 5 cells are "take the lift" steps on the way back, not destinations.

**Use in play (inferred).** Federation exports this field as plane 2 (below), and creatures follow it
(`reversing/captive/ai.md`).

## Output encoding

`$23936` writes federation's two 64x32 byte layers, index y × 64 + x. Federation reads them the same way (`$88e4`,
`$adb6`).

**Layer A, tiles: `fed 9242(A6)` = `$1d9e8` (pointer `13684(A6)`).** Each byte is `$2397e`(G0, G1 feature, G1
parameter), evaluated in this order:
- G0 = `$ffff` gives 0. Feature `$20` gives `$a0`; `$1e` gives `$18`; `$09` gives `$28`; `$22` gives `$10` + ((param
  >> 1) & 3). These are tested before G0 = `$ffff`.
- Feature `$2c` gives the parameter byte, even on rock: decorated wall faces.
- Otherwise G0 = 0 (rock) or `$fffd` gives 0.
- Then a feature-to-tile list (`$239f4`-`$23b84`), for example `$15` gives param + `$40`, `$16` gives `$1b`, `$14`
  gives `$1e`, `$12` gives `$2c`, `$13` gives `$2e`, `$0e` gives `$1a`, lift features 4, 5, 6 give `$34`, `$31`, `$32`.
- Unlisted features give `$20`.
- Bit 7 of the feature sets bit 7 of the tile (`13594(A6)`).

**Measured** (`gen.py` over 7 seeds, one-off cross-tab): carved cells take tiles above `$1a` (422 of 448 for D0 = 1).
Rock with a feature takes tiles of `$1a` or below.

**Inferred:** tiles above `$1a` are open cells. Federation's automap draws only those (`$11000`: `cmpi.b #$1a`).

**Layer B, plane 2: `fed 11322(A6)` = `$1e208` (pointer `13688(A6)`).** For carved cells it holds
G2 byte 0 | (G2 byte 0 << 3). For rock and block walls it holds G2 byte 0. Bits 6 and 7 are read by federation at
`$119b6`-`$119c0`.

**The module's own grids.** All three are internal; the module buffer is reused after the call (`$b632`).

| grid | address | contents |
|---|---|---|
| G0 | `56(A6)` | 64x32 words |
| G1 | `4168(A6)` | (parameter, feature) byte pairs |
| G2 | `8280(A6)` | byte pairs; only byte 0 is set in the cases run |

**Other output regions.** The other A1-table pointers address federation regions that the generator clears and fills
(`$23bcc`-`$23c5a`): `13696` through `13740(A6)`, including the 25-word list copied from `13460(A6)` by `$245e2`. Their
contents are not read.

## The returned sheet mask

The returned D0 is `13748(A6)` (`$20102`). Federation stores it at `fed 13402(A6)` and loads creature sheets by its
bits (`$b5f0`, `$b6de`; `world.md`, section 4). `$2624a` sets it:
- D2 = 1 gives 8.
- D0 ≤ 9 gives the byte table `$26240`: `03 03 03 05 03 06 05 03 05 05`.
- Otherwise it is the high word of 3 × (D0 after two LCG steps), with 0, 1, 2 giving 3, 5, 6.
- The surface path sets `$30` (`$23d5e`).

Observed: 8 for every D2 = 1 base, 3 for D0 = 1 with D2 = 0 (the natural `req4_mg.snap` call also returned 3), and
`$30` on the surface. D5 and D6 come from `12392(A6)` and `12396(A6)`: 0 for a base, the start position for the
surface.

## Not read

- The 25 stages after `$24f4c`: `$25198` through `$268f8` (features, objects, doors, generators). `stagedump.py`
  gives the bytes each one changes.
- `$24c5c`: features `$11` and `$14`, with a marker `$fffe`.
- `$2676c`: D2 = 1 only.
- The tile list's game meaning: no tile has been matched to a picture.
- The surface generator past `$23d94`.
- What the Copylock prologue checks.
- Whether the digger's corridor network is a strict tree: implied by the carve rule, not counted.
- Why a carve number 1 occurs away from the entrance in some bases (2 of 4 in `bases.json`).

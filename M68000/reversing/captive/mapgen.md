# The base generator, `fed_MapGen`

`fed_MapGen` builds every base Captive puts on a planet, and the planet surface around it, into one 64x32 grid.

**How it builds a base:**
- The grid is cut into 16 blocks of 16x8 cells. Each block is given to one of up to five floors.
- A random walk grows each floor over the blocks.
- Lifts join consecutive floors by a fixed translation.
- A turtle "digger" then carves single-width corridors that never break into another passage. As it goes it drops
  rooms, looped caves and lifts, and opens pre-placed shafts between floors when a corridor reaches one.
- Every carved cell keeps the number of the dig step that made it. The generator turns those numbers into a flow
  field: from any cell, following the arrows walks the dig backwards to the entrance.
- Later stages prune dead ends (most of them in low-numbered bases, none from base 32 up), scatter features and
  decorated walls, and place doors, including coded doors whose corner code is drawn at random.

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

`$244b6` (from `$23cb0`) does most of the work: 1,708,805 of the 2,644,857 steps for D0 = 1, D2 = 1 (`stages.py`).
It writes 891 of the G0 bytes, and no other stage moves more than 64 (`stagedump.py`).

**Proof.** `py/mapgen/digger/dig.py` is a register-level port of `$244b6` and every routine it calls. Its output
equals the emulator's over the whole module variable block: G0, G1, G2, the room list, both RNG words `12404` and
`13656(A6)`, every other variable, and D1-D7 at the return. The port starts from the emulator's state at `$23cb0`.
- **Gate:** 1000/1000 for D2 = 1, D0 = 0..999, and 100/100 for D2 = 0, D0 = 0..99 (`digger/README.md`).
- **Controls** on the same 1000 seeds:
  - a carve rule that needs 2 uncarved neighbours instead of 3: 0/1000;
  - rooms one cell narrower: 0/1000;
  - no pillars: 24/1000.

The rules below are what the gated port computes. Readings that the gate does not separate are marked inferred.

**The turtle.**
- **State:**
  - a position (D1, D2);
  - a floor D3, starting on the entrance's floor (`$244be`-`$244c4`);
  - a heading at `12424(A6)`: 0, 2, 4, 6 for N, E, S, W (dx, dy tables at `$248c4`/`$248cc`), starting east;
  - a counter D4 that starts at 1.
- **Carving:** `$24f3c` writes D4 into G0 and increments it. The entrance is carved twice (`$244e6`, `$244f0`), so it
  holds 2.
- **Uncarved:** a cell counts as uncarved (`$24efc`) when it is rock, outside the grid, or has G0 above `$ffce`.
  That covers block walls, closed shaft doors (`$ffff`), the blob fence (`$fffe`) and the room reservations
  (`$fffd`) written before the digger by `$263c2`. The tested cell itself must be rock, or its count is 0.
- **Carve rule:** a corridor cell is dug only when exactly 3 of its 4 neighbours are uncarved (`$24e8c`,
  `cmp.w #3,D6` at `$24514`). It touches nothing but the cell it is dug from, so a single corridor carve never merges
  two passages: the perfect-maze condition. The whole base still has loops (below).

**Each step (`$24872`)** draws a random word into `12426(A6)` and, from its low bits and size, does one of:
- turn left or right, then move one cell forward in the same step;
- a lift up or down (`$248f0`/`$24902`), only when the word is above `$ccb0` and D4 > 4. The far end must lie in a
  block of the destination floor, at the floor pair's offset, with 4 uncarved neighbours. After a lift the turtle
  stands on the far end and draws a new word without carving (D5 = -1, `$249c0`). Every in-bounds lift attempt adds 1
  to the restart counter `12414` and takes 1 from the lift budget `12416`, whether or not it succeeds
  (`$2491e`/`$24922`);
- a blob (`$24c5c`, word ≤ `$7ad`);
- a room (`$249da`, word ≤ `$8f48`);
- otherwise one step forward.

**Failure and restarts.**
- **Retries:** when a carve fails, the turtle restores its position (`$24d88`) and retries up to 10 times. Each retry
  re-draws only a 2-bit selector, D0 = rng & 3 (`$2451e`), and keeps the step word, so a room, blob or lift word is
  retried with new directions.
- **Restart:** after 10 failures it tries up to 100 random cells (`$2452a`).
  - If the second RNG (`13656`) is above `$a200` and the cell is carved with feature `$1f $35 $36 4 5 $33 $11` (room
    floor, lift ends, blob floor), the restart is a lift attempt from that cell (`$2458a`-`$245a4`). It sets D0 = 2
    (3 when bit 4 of `12427(A6)` is set), forces the step word above `$ccb0`, takes one from the restart counter and
    runs the step. If the lift fails it steps forward instead.
  - Otherwise, and also when the drawn cell has none of those features, the restart takes any uncarved cell that
    touches exactly one carved cell.
- **End:** budgets of 300 restarts (`12414(A6)`) and 900 lifts (`12416(A6)`). D4 ≤ `$3000` is also tested but never
  ends a dig. Over the gated runs, D2 = 1 ended on the restart budget in 874 of 1000 and on the lift budget in 126;
  D2 = 0 in 89 and 11 of 100.

**Rooms (`$249da`).**
- **Size:** let s = (r ror 6) & `$3f`, masked with `$1b` when r > `$3ff7`, where r is the step word. The room is
  ((s & 7) + 2) × (((s >> 3) & 7) + 2) cells. The check loops at `$24a88`-`$24ae2` are `dbf` loops on the stored
  w - 1 and h - 1, so each runs once more than the stored count. **Proven** over 25,771 rooms in the 1000 gated bases:
  every bounding box has that size (`digger/rooms.py`).
- **Check, then carve:** the room's first cell (the one ahead of the turtle) needs 3 uncarved neighbours and every
  other cell 4, so a room touches the maze only at its entry. A failed check makes the step a plain forward move
  (`$24bde`-`$24bea`).
- **Pillars:** a room wider and taller than one cell takes a pillar pattern from the bit table at `$24c1c` (row
  offset r & `$38`). Pillar cells stay rock, with feature `13652(A6)`: 0, or `$20` when r rol 2 exceeds
  `$eeff` - 8·min(D0, `$7f7`) (`$23bc6`, `$24a06`-`$24a18`). 20,578 of the 25,771 rooms have none. A 9-row room reads
  its ninth pattern byte past the table, from the code at `$24c5c` (`$61`). That is harmless because the last row
  never takes pillars, but the port has to copy it.
- **Numbering:** room cells are not dig order. Row r starts at D4 + 8r, each cell adds 2 and each pillar 8. After the
  room, D4 grows by 8(h + 1) + `$48`.
- **Floor feature:** `$1f`, or `$33` for some rooms when D0 > 4 (`$24a22`-`$24a3e`).
- **Room list:** up to 63 rooms at `12952(A6)`, counting down from `13208(A6)`. Each entry is (x, y, floor, s), where
  (x, y) is the room's last carved cell and s its size byte (`12436(A6)`). **Proven** (`rooms.py`): 25,588 of 25,771
  entries match, and the other 183 are cells that later became lift ends; none is unexplained.

**Blobs (`$24c5c`).**
- **Fence:** `$24d2c` marks with `$fffe` every rock cell next to a carved cell, and the turtle's own cell.
- **Walk:** the blob carves the cell ahead with feature `$11` (`$14` when rol(r, 8) ≤ `$2710` and D0 ≠ 0), then walks
  50 random steps (`$24cd4`). It carves rock, walks over carved cells, and turns back at `$fffd`-`$ffff` or the grid
  edge.
- **Clear:** `$24d60` clears the fence afterwards.
- **Result:** a looped cave joined to the maze only through its first cell.
- **Side effect:** the blob's step `$2484e` overwrites the saved position `48`-`52(A6)`, so the next restore
  (`$2451a`) lands on the blob's last cell, not the turtle's.

**Shafts.** Before the digger, `$245e2` (through `$24606`/`$2465e`) lays out up to 5 groups of shaft entries, one entry
per floor. That `$245e2` writes them is inferred from the code; the layout is read from the emulator's state at
`$23cb0`.
- **Entry:** a cell with feature `$1c` and G0 = 2, a cell with feature `$18` and G0 = 1, and a closed door (G0 `$ffff`,
  feature `$0f`) walled with `$ffff`.
- **Lists:** doors at `13360(A6)`, `$1c` cells at `13410(A6)`, `$18` cells at `13460(A6)`. Each is 5 groups of 5 (x, y)
  pairs, with `$ffff` for unused.
- **Placement:** consecutive floors' entries sit at the lift offsets `16`/`24(A6)`. Seed 2 has (18,4), (50,4) and
  (34,12), with offsets (+32, 0) and (-16, +8).
- **Opening** (`$24d96`/`$24dda`, after every room, lift and blob cell): when a door has exactly 2 uncarved
  neighbours, that is, a passage has reached it:
  - that floor's door, `$18` and `$1c` cells are carved, and the `$1c` becomes `$1d`;
  - every other floor's door that touches exactly one carved cell is carved too;
  - the turtle moves to the last door opened (`13286`/`13288(A6)`, `$24dc2`-`$24dd0`) and digs on from there.
- **Routing:** the flow field's 4/5 values at `13410` (`$2503c`) are the way through these shafts.
- **Inferred:** the `$18` cells' G0 = 1 accounts for the carve number 1 seen away from the entrance.

**Loops** (`digger/dig.py tree`, over the 1000 gated bases). A cell counts as carved when 0 < G0 < `$ff00`. Edges join
orthogonally adjacent carved cells on one floor. A base is a forest when E - V + C = 0.
- **Raw cells:** 0 of 1000 are forests, because rooms and blobs are open areas.
- **Rooms and blobs contracted to one node each:** 819 of 1000 are forests. The 232 cycle-closing edges in the other
  181 all touch a shaft:
  - 228 between a blob and a shaft cell;
  - 3 between a corridor and a shaft cell;
  - 1 corridor-to-corridor edge (seed 958), dug beside a door while it was closed.
- **With lifts and shafts as edges:** every base is one connected component, and 503 of 1000 are forests (925
  cycles), because shafts and lifts give alternative routes between floors.

So the corridors are a perfect maze per floor, and the loops in a base come from its blobs and its shafts.

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

## After the flow field: dead ends, features and doors

After `$24f4c` the base path `$23bb0` makes 28 more calls of 26 routines (`$25198` and `$24d64` run twice), plus
`$2676c` at D2 = 1 only. Seventeen of these calls are ported to Python in `py/mapgen/stages/models.py`. Each model
starts from the emulator's own state just before its stage. It must reproduce the state after the stage byte for
byte: the whole module variable block (G0, G1, G2, lists, counters, RNG seed) and federation's table block
`$1bd3e`-`$1d9e8`.

**Proven**: every ported stage matches 80/80 cases, D0 = 0..39 at both D2 = 1 and D2 = 0 (`stages/gate.py 0 40`).
Each one has a broken-model control that loses cases. For example, `--stage 2533a --break 'prune_keep=(3,)'` gives
16/80 and `--stage 2630c --break pic_mod=5` gives 0/80; the README there lists all the controls. Unless a line below
says otherwise, the rules are what the gated models compute. Every random draw goes through the RNG `$23b96`. A
"random cell" is `$244a2`: x = r & `$3f`, y = (r ror 6) & `$1f`.

**Dead ends.**
- `$25198` lists the dead ends: open cells with exactly 3 blocked neighbours, scanned y = 31..0, x = 63..0.
  - It skips the entrance and the lift and special features `$06 $37 $1c $1d $1a $1b $05 $04 $36 $35 $0f $21 $18`.
  - It keeps at most 254, as (x, y) byte pairs at `12440(A6)` (count at `12438`), and gives each listed cell
    feature `$7f`.
- `$2533a` prunes them against a threshold T = D0 × 2048 for D0 ≤ 31, else `$ffff`. Bases 32 and up are therefore
  never pruned.
  - For each listed cell it draws r. When r > T it takes one step along the cell's plane-2 arrow.
  - If the cell it reaches does not have 2 or 3 blocked neighbours (it is a junction), the dead end is filled back
    to rock (G0 = G1 = 0).
  - So low-numbered bases lose most of their one-cell stubs. That later bases are meant to be harder mazes is
    inferred from this rule, not measured.
- `$25198` then runs again to rebuild the list.
- `$25162` shuffles the 256 slots with 513 random swaps, then restores the RNG seed.

**Feature scatter.** The feature numbers are G1 features; their tiles follow "Output encoding" below. Which game
object each feature is has not been matched.
- `$25240` places a 3x3 patch of feature 9 (tile `$28`).
  - Site: the first room-list entry (`12952(A6)`) whose kind byte has both bit fields 0-2 and 3-5 non-zero.
    Failing that, a random dead end (`$2567e`).
  - It grows in +x and +y only, into room or lift cells (`$25300`), and leaves lift features alone.
- `$256f0` makes room doorways, 61 tries.
  - It picks a random room (`$256be`), walks w + h + 2 arrows from it, then goes back 2 cells against the last
    arrow.
  - Where that cell is blocked or room floor it steps back once more.
  - When a side cell is blocked and both this cell and its arrow successor are room floor (`$1f`/`$33`), the cell
    gets feature `$21` with G0 `$ffec`, and the successor gets `$0e`.
- `$24d64` replaces every G0 word equal to D5 with D6. It runs twice: `$ffc3` to 0, then `$ffc4` to `$fff6`.
- `$24128` places feature `$16` at corridor cells.
  - It makes min(D0, 10) + 1 walks (21 when D0 > 10), each from a random cell, down the arrow field two steps at a
    time, to the first feature-7 cell.
  - The marker is skipped next to a door (`$15`).
- `$240c2` gives feature `$1e` (tile `$18`) to rock walls one cell thick (open on both N and S, or both E and W). It
  makes (4·D0, at most 80) + 1 tries of 5 cells rightwards.
- `$26438`, `$265cc` and `$26606` place features on cells:
  - `$26438`: feature `$24` (`$2a` on a `$28` cell), at most 11;
  - `$265cc`: feature `$25` (`$2b`), no cap;
  - `$26606`: feature `$26` on `$1f $33 $14 $11` cells, at most 8.
  - The try counts come from `$2640a`, a log-like compression of D0.
- `$26532` turns up to min(D0 - 5, 60)/2 + 1 plain corridor cells into `$0032`. It places nothing for D0 ≤ 5.
- `$26570` puts `$30`/`$31` on room cells, or `$30` on corridor cells open on all four sides.
- `$2630c` decorates wall faces: up to 100 faces, each taking up to 101 draws.
  - A candidate is a featureless rock cell with an open neighbour, and no open neighbour of feature `$15 $1e $12
    $13`.
  - It gets feature `$2c` with parameter = the mask of its open sides (N 1, E 2, S 4, W 8), and that parameter is
    the exported tile.
  - The picture number is (r >> 8) mod 6, with 1 mapped to 2, so it is one of 0, 2, 3, 4, 5.
  - Each face is recorded as (x, y, picture, 0) in the list at `fed 1930(A6)` = `$1bd58` (pointer `13704(A6)`).
- `$26854` marks lift pairs. It makes min(D0, 40) + 1 row scans for an up end (4/`$35`) or a down end (5/`$36`). Where
  the partner on the next floor is the matching end, the up end becomes `$2e` and the down end `$2f`.

**Code quirks the models keep.**
- `$24128` and `$2533a` follow arrows from rock (G2 = 0, read as north) and from `$fe` cells. That indexes the
  direction table `$25404` past its end, and some walks leave the grid. `$24128` reads outside the module block in
  14 of 80 cases; the model reads `mg_ret.snap`'s RAM there, which is static code. Neither routine writes outside
  the block.
- In `$26854` the `addq.w #1,D5` at `$2688c` is dead, because the loop re-enters at `$26866` and recomputes D5.

**Coded doors.** The combination lock's door list (`ai.md`, "Getting into a base") is written by the generator.
- **Proven** (`stages/doorwatch.py natural scratchpad/captive/base1/land_mg.snap 3000000`, no pokes): in the natural
  compound call for mission 1, the 8-entry list at `fed 2330(A6)` = `$1bee8` (pointer `13708(A6)`) is first cleared
  by `$23b8e`. It then gets exactly three writes: x = `$16` at `$242f0`, y = `$15` at `$242f2`, and state `$0080` at
  `$24300`. The list ends as `1615 0080`, the entry `base1/outside.snap` holds, and federation does not write it
  afterwards. The shortcut call `doorwatch.py shortcut 0,0,2,0` gives the same writes. The stack at `$242f0` returns
  to `$23dae`, inside the compound builder `$23e80`.
- **Inferred from the code**, and consistent with those writes:
  - `$23e80` walls the compound with turtle moves (`$23fde`/`$23fa2`; walls are G0 `$ffff`, feature `$80`).
  - It sites the compound at (22,20) for D0 = 0 when bits 2 and 3 of `13277(A6)` are clear. Otherwise the site is a
    random open cell in [3..60] × [3..28].
  - It ends in `bra $24298`, the door placer every stage shares, which dispatches on the door kind's low 3 bits:
    - 2: a coded door, only while the counter `13628(A6)` is non-zero;
    - 4: a coded door with no counter check (the compound door, and `$2676c`'s door at D2 = 1);
    - 3: a large structure at `$24306`, which ends by calling the group writer `$25e08`;
    - anything else: a plain door, counted in `13618(A6)`.
  - A coded door takes slot 7 - `13628`. The counter starts at 7 (`$23c66`) and counts down, so the slots fill from 0.
  - The door's code is the high word of (RNG word `12404(A6)` × 24), stored as state = code << 4. The code indexes
    the 24 corner orders at `$e358`. For the mission 1 compound, `$59c6` × 24 = `$86d10` gives code 8, the code
    `ai.md` found by play.
- **Proven, structurally**, over the 80 bases (`stages/doorlist.py 0 40`):
  - all 357 list entries name a door cell (feature `$15`) with state low nibble 0 and code < 24;
  - all 317 kind-2 door cells in the grids are listed;
  - the other 40 entries are kind 4, one per D2 = 1 base;
  - every code 0..23 occurs, 7 to 25 times.
- A door's code is therefore random per door, drawn from the base's RNG stream, and nothing in the generator
  writes it anywhere else.

**Not ported.**
- `$263fa`, a second dig pass: `$2640a`(D0) + 1 calls of the room builder `$249da` in mode `13584` = 2. The room
  builder is ported in `digger/dig.py`, so this stage can reuse it.
- `$2419a`, the doors (read, not ported):
  - first a plain door on each of the 25 cells of `13712(A6)`;
  - then 300 tries on corridor cells walled on both sides, with the kind from the byte table `$24228`;
  - D0 = 0 makes every door plain.
  - Its kind-3 doors reach the group writer `$25e08`, so it waits on the creature placement.
- The creature and object placement stages `$25c1e`, `$25722`, `$25414`, `$2543a` and `$25d88`: they write the group
  list (`fed 4532(A6)`, read by `ai.md`) and the object list `13724(A6)` = `$1bf3a`.
- `$26478`, `$264ac`, `$264c8` (append to `13724`), `$268f8` (D0 = 0 only), `$2676c` (D2 = 1 only).

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
(`$23bcc`-`$23c5a`): `13696` through `13740(A6)`, including the 25-word list copied from `13460(A6)` by `$245e2`.
Identified (read from the stage dumps; roles from their writers in "After the flow field"):
- `13704` = `$1bd58`: the decorated-wall list, 100 × (x, y, picture, n).
- `13708` = `$1bee8` (`fed 2330`): the coded-door list, 8 × (x, y, state word).
- `13712` = `$1bf08`: the 25-word door-cell list.
- `13716` = `$1c77e`: a header (`$1000`, `$ff8`, `$88828881`), then the creature group list at `$1c782` (`fed 4532`).
- `13724` = `$1bf3a`: the object list.
- `13740` = `$1d942`: the kind-3 structure list, 4 bytes per entry, at most 7 (count `13638`).

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

- The unported post-dig stages listed at the end of "After the flow field". `stagedump.py` gives the bytes each one
  changes.
- The shaft layout `$245e2`/`$24606`/`$2465e` and the room reservations `$263c2`: read in part, not ported.
- The tile list's game meaning: no tile or feature has been matched to a picture or object.
- The surface generator past `$23d94`.
- What the Copylock prologue checks.

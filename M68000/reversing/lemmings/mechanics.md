# Lemmings: behaviour

Addresses are runtime absolute, from `scratchpad/lemmings/lvl1.snap` (made by `drive.txt`), whose
whole-image listing is `disassemble.py --snap <snap> --all 0x2000 0x27000`. That listing misses the code
below `$2000` (it starts at `$400`: input, click dispatch, hit test); list `0x400 0x27000` for a whole-program
claim. `A5` is `$272d4` in game code but `lvl1_a.snap` stops in the cracktro with `A5 = $c822`: set it before a `callcap`. Globals live at
`A5 = $272d4`. Every claim below is labelled **proven** (emulator check with its count) or **read**
(from the listing, not yet driven under `callcap`).

## The lemming array

**Proven (10 of 10 records):** `$23484`, stride `$2c` (44 bytes), one record per spawned lemming; the
count spawned so far is `60(A5)` (`$27310`) and the level's total is `52(A5)`. Four snapshots 24,000
steps apart in level 1, with all 10 out, show word +0 and +2 of exactly ten records, `$2c` apart
(`$23484`, `$234b0`, ... `$23610`), moving by 1 per tick (x 694 to 851, y 76 to 84), and a word at +10 that
counts up per tick for each. The whole level is 1600 wide, so +0/+2 are the lemming's x/y in level pixels.

Fields **read** from the spawn routine `$34ac` (it clears the record, then writes):

| offset | size | set to at spawn | note |
|---|---|---|---|
| +0 / +2 | word | entrance x / y from `136(A5)`, indexed by `86(A5)` (0..3, alternates) | position |
| +4 / +6 | word | `-8` / `-10` | x/y offset from the position to the sprite's top left (hotspot) |
| +8 | word | `D4`, +1 or -1 | direction; `-1` when `$34fc` (the release-side flip) runs |
| +14 | long | 0 | state mask, one bit per state (the dispatch below) |
| +21 | byte | 0 | non-zero is a countdown (`bsr $80ea` when set; `$7938` stores `$4f`) |
| +24 | byte | 0 | non-zero: the record is dead or gone; every loop skips it |
| +36 | byte | `D4` | direction again as a byte (the minimap and counters test its sign) |
| +38 | long | `$1af30` | pointer (an animation or frame table) |
| +42 | word | `$21c` | unknown |

Spawn is gated in `$34ac`..`$34d8` by a release-rate counter (`72(A5)`, reloaded from `58(A5)`) and
`52(A5) != 60(A5)` (spawned < total); it runs once per tick of that counter.

Three other routines walk the array: `$475a` (minimap, one dot per record at `x/16`, `y/8`, skipping
`+24 != 0`), `$4c5a` (a visibility test against the scroll `48(A5)` and a window, counting
`+36` signs into `$26c16` and `$26ef2`), and the update loop below.

## The per-frame update

`$7802` (called while `25(A5)` is clear) loops the records, skipping `+24 != 0`. For each
it loads `D0 = x`, `D1 = y`, `D6 = long +14`, `D3 = byte +21`, calls `$80ea` when `D3 != 0`, then tests
the bits of `D6` in a fixed priority order and branches to a handler per bit; each handler writes
`D0`, `D1`, `D6` back to the record. This is a bit-mask state machine, not a per-state integer. With no
bit set the lemming walks (`$797c`).

Roles below come from two independent reads: the skill-assignment code (next section), which names the
bit each click sets, and the handler body. **Proven** means driven in the emulator.

| `btst` order | bit | handler | role |
|---|---|---|---|
| 1 | 16 | `$8064` | the 16-frame "Oh no" phase after the bomber countdown: sound at frame 5, `bsr $8134` at the end turns it into bit 10 (**proven** transition below) |
| 2 | 3 | `$8a62` | trap death from cell code 5: 16 ticks, the lemming keeps moving 2 pixels, then dead (**proven**, "Exit and traps") |
| 3 | 8 | `$81ba` | splat: 16 ticks, then `st 24(A0)` (record dead): **proven** (floater control below) |
| 4 | 10 | `$8156` | the explosion: frame 1 plays sound `$14` and releases a blocker (`bclr #7`, `bsr $8a06`: **proven**), dead at frame `$34` |
| 5 | 15 | `$7a9a` | fall: **proven**, 3 rows a tick (below) |
| 6 | 13 | `$801c` | ledge hop: the walker `$7a88` sets it for a step 3 to 6 rows high; 2 rows a tick (**proven**, "Collisions") |
| 7 | 1 | `$8aca` | **exit, proven**: 8 frames, then `addq.w #1,20(A3)` (the saved counter at `$26c18`) and the record dies |
| 8 | 2 | `$8b5c` | trap death from cell code 6: 14 ticks, x frozen, then dead (**proven**, "Exit and traps") |
| 9 | 14 | `$8850` | **digger, proven** (below) |
| 10 | 12 | `$86f2` | **climbing, proven** (below) |
| 11 | 11 | `$880a` | over the top of a wall, after the climb: **proven** transition (below) |
| 12 | 9 | `$851c` | **builder, proven** (below) |
| 13 | 7 | `$89a4` | **blocker, proven** ("Collisions" below) |
| 14 | 6 | `$81d0` | **basher, proven** ("Basher and miner" below) |
| 15 | 5 | `$7f06` | floating (floater's open parachute): **proven** (below) |
| 16 | 4 | `$7b88` | **miner, proven** ("Basher and miner" below) |
| 17 | 0 | `$86be` | the builder's "out of bricks" shrug before it walks on: observed after the 12th brick (below) |
| none | : | `$797c` | walk |

## Skill assignment (the click path)

The mouse/click state is a struct at `$26c04` (`A3`; a second one at `$26ee0` for the two-player view). Fields
from the code: `+2` scroll (copy of `48(A5)`), `+4`/`+5` left/right button latches (a handler clears `+4` with
`sf 4(A3)` when it consumes the click), `+6`/`+8` pointer x/y in screen pixels, `+16` the lemming
under the cursor (1-based record number, 0 = none), `+22` the selected skill, then the remaining counts.

- Click dispatch `$1754`: `y >= $b0` is the panel, otherwise a playfield click goes to `$18b8`, which branches
  on the selected skill. In the panel, `x < $10` is release rate minus, `x < $20` plus, and
  `(x - $20) >> 4` is the skill index written to `+22` (`$17ba`, **proven**: clicking the icon at x 152 wrote
  `$26c1a <- 7`, watch hit at pc `$17ba`).
- Skill index to skill, count offset in the struct, and what the assignment writes:

| index | skill | count at | assignment (routine) |
|---|---|---|---|
| 0 | climber | `+30` | `st 22(A0)` (`$1ee0`); refused if bits `$580` are set |
| 1 | floater | `+38` | `st 23(A0)` (`$1ea8`) |
| 2 | bomber | `+26` | `move.b #$4f,21(A0)` (`$1dea`): the same countdown `$7938` writes for every lemming on nuke |
| 3 | blocker | `+34` | `bset #7` (`$1b9c`); needs clear cells in the object map `$62f80` |
| 4 | builder | `+32` | `bset #9`, `20(A0) = $c` (`$1d6e`) |
| 5 | basher | `+36` | `bset #6` (`$1cd6`) |
| 6 | miner | `+40` | `bset #4` (`$1c2a`) |
| 7 | digger | `+28` | `bset #14`, frame `+10 = $11` (`$1e2c`) |

- Cursor hit test `$1540`: pointer world x is `6(A3) + 2(A3)`; the test is `x + 8` in `[lx - 5, lx + 5)` and
  `y + 8` in `[ly - 11, ly + 1)` against each record's `(lx, ly)`. To click a lemming aim the pointer at
  world `(lx - 8, ly - 13)`, screen x being world x minus the scroll. The scroll moves while the pointer is
  in the edge zones (pinning to the corner scrolls the view left), so read `+2(A3)` after the last move.

**Proven (digger):** `reversing/lemmings/click_digger.txt` from `lvl1_a.snap` selects the digger icon,
snapshots (`sel.snap`), then clicks lemming 0: its `+14` reads `$4000` (bit 14) at every later sample, x stays
at 732 and `y` goes 77 to 81 over 1.2M steps (a longer run of the same clicks: 77, 78, 80, 83 over 1.9M); the nine
others keep `+14 = 0` in the 160k-step samples.

## Collisions

Two independent layers, both read by the per-lemming update.

**Terrain bitmap** (`A1 = $41806`, one plane, row stride `D7 = $330`; a pixel is the bit `7 - (x & 7)` of the
byte `y*$330 + (x & $fff0)/2 + ((x >> 3) & 1)`). The walker `$797c` moves `x += dir`, then, all **read**:
pixel `(x, y)` clear: probe `y+1..y+3`; all three clear is a fall (sets bit 15, `19(A0) = 3`), otherwise `y` follows the
ground down. Pixel set: probe upward `y-1..y-7`: a clear row within 3 steps up is a smooth step; a clear row 4 to 7 up is
the ledge hop (bit 13); no clear row in 7 is a wall, which turns the lemming (`neg 8(A0)`) or, with `+22` set, starts the
climb (bit 12, `$8194`). **Proven (the step sweep, `py/stepsweep.sh`):** on flat ground (rows 50 to 79 cleared, ground
row 80) with a solid step of H rows at x = 752, lemming 0 (y = 80) gives, one sample per 36,000-step tick:
H = 1, 2: `y` becomes 79 or 78 at once with `+14 = 0` (smooth step); H = 3 to 6: bit 13 (`$2000`) for 1 to 3 ticks while `y`
rises 2 rows a tick (78, 77 for H = 3; 78, 76 for H = 4; 78, 76, 75 for H = 5; 78, 76, 74 for H = 6), ending on top of the
step at `y = 80 - H` with `+14 = 0`; H = 7, 8: no rise, `dir` becomes -1 at x = 752 and it walks back. In pixel terms a
step of H rows leaves its first clear row `H + 1` up, so the cut-offs are H <= 2 smooth, 3 <= H <= 6 hop, H >= 7 wall. The fall handler `$7a9a` drops 3 rows a tick and adds 3 to `19(A0)`;
landing with `19(A0) > $3c` and no floater sets the splat bit 8 (`$7b28`), and `> $10` with a floater opens it (bit 5).

**Object map** (`A2 = $62f80`, 4-pixel cells, one byte each, row stride `$198`; the lemming's cell is
`(x/4, y/4)`). After every update `$8b6e` stores that cell in `25(A0)` and the cell two columns ahead in the row two
above in `26(A0)` (the miner and basher steel and one-way tests), then dispatches on the cell's low nibble (the high
nibble indexes the `$23044` object table, stride `$22`):

| low nibble | effect (`$8b6e`) |
|---|---|
| 1 | state bit 1 (`$8aca`, the exit), sound `$11`; skipped if bit 1 or 15 is already set (**proven**) |
| 2 | reverse a lemming walking right (`8(A0) >= 0`); a left-walker passes (**proven**) |
| 3 | reverse a lemming walking left; a right-walker passes (**proven**) |
| 4 | marks object bit 1 and `st 24(A0)`: the lemming vanishes at once, no state bit (**proven**) |
| 5 / 6 | state bit 3 / bit 2 (the `$8a62` / `$8b5c` death handlers), skipped if already set (**proven**) |
| `$a`, 7, 8, 9 | nothing here (`$a` is the blocker's centre; 7, 8 are the one-way and 9 the steel tests of the digging skills) |

**Proven (blocker)**, `reversing/lemmings/click_blocker.txt` from `sel.snap` with the skill index (`$26c1a`) poked to 3 and
the count (`$26c26`) to 5: clicking lemming 0 at (732, 76) gives `+14 = $80`, `+38 = $1d808`, count 5 to 4, and
stamps a 3 by 3 patch of cells, rows `02 0a 03`, at columns 182..184 and rows 17..19, i.e. `((x-4)/4, (y-6)/4)` upward
(`$1b9c`-`$1c26`; the cells it overwrites are saved in `27..35(A0)`). Ten lemmings, 1,800,000 steps: the control arm (no
click) executes neither turn handler (`hits` on `$8bce`, `$8bdc`: 0 and 0) and its lemmings 1 and 5 walk on to x 755 and 717; with the
blocker `$8bce` runs once, for lemming 1 at x = 728 (the first column of cell 182, step 794,809) and `$8bdc` once, for
lemming 5 at x = 739 (the last column of cell 184, step 975,053); both then walk back (727 to 701, 740 to 761). The
blocker stays at (732, 76) with `+14 = $80`. A bomber assigned to it (index 2, count poked) counts `21(A0)` down from
`$4f`, about 35,000 steps a tick; at 0 `+14` is `$00010080` with the cells still stamped, 9 samples (60,000 steps
apart) later `+14 = $400` and all nine cells read 0 (restored from the saved bytes by `$8a06`, from `$8156` frame 1).
The handler `$89a4` also releases the blocker if the ground pixel under it clears (`bclr #7`, `bsr $8a06`; read).

**Exit and traps, proven** (`py/objdrive.py`). Level 1's object map (`$62f80`, 408-byte rows, 40 rows) holds one object in the
playfield: cells `(222, 33)` and `(222, 34)` = `$11` (object 1, code 1; world x 888 to 891, y 132 to 139), plus `$20` at
`(217..218, 31)` (code 0). The ground there is flat at y = 135 or 136. Lemming 0 is set down at (870, 135) facing right (a
position poke, an input), the other nine are untouched. Each arm is the same placement with the two cells poked to a code;
`hits` over 1,500,000 steps counts `$8b6e`, `$8aca`, `$8b5c`, `$8a62`; a tick is 36,000 steps:

| cells | tick 18 (x = 888) | later | `hits` |
|---|---|---|---|
| code 1 (the level's own) | `+14 = 2` (bit 1), x frozen, frame `+10` 0 to 7 | tick 26: `+24` set (dead), `$26c18` 0 to 1 | `$8aca` 8 |
| 0 (control) | `+14 = 0`, walks on to 895 and beyond | : | `$8aca` 0 |
| 2 | `dir` becomes -1 | walks back | none |
| 3 (right-walker) | unchanged | walks on | none |
| 3 (starts at 906 facing left) | : | tick 15, x = 891: `dir` becomes +1 | none |
| 2 (starts at 906 facing left) | : | unchanged | none |
| 4 | `+24` set at once, `+14 = 0` | : | none |
| 5 | `+14 = 8` (bit 3), keeps moving 2 pixels | tick 34: dead | `$8a62` 16 |
| 6 | `+14 = 4` (bit 2), x frozen | tick 32: dead | `$8b5c` 14 |

The exit also needs the lemming to arrive: on level 1 as shipped, lemming 0 paces between x = 686 and 853 (a walled pen,
60 samples of 360,000 steps) and never reaches the exit at 888 without a skill, so the position poke stands in for walking there.

## Basher and miner

Both erase terrain by AND-ing a mask from a table into the bitmap at `(x + dir + 4(A0), y + 6(A0))` (`$8218`-`$8256`
and `$7bd8`-`$7bfc`: a basher mask frame is 10 rows of a long (`$28` bytes), shifted by `x & 15` across two 16-pixel groups; the miner's frame is `$34` bytes). Basher masks are
at `$14cc2` (4 frames of `$28` bytes, mirrored `+160` for dir < 0), miner masks at `$14e02` (2 frames of `$34`,
mirrored `+104`). A game tick is 36,000 steps (3 VBL: `hits` on `$81d0` is 17 calls in 600,000 steps, 16 gaps of
35,900 on average). The driver is `py/skilldrive.py` (pokes the skill index and count, clicks lemming 0, dumps the
bitmap window as ASCII each sample) and `py/terrain_diff.py` (cleared and set pixels against the first frame);
`--wall gx0,gx1,y0,y1` pokes a solid block into the bitmap and `--cells c0,r0,r1,val` pokes object-map cells.

**Basher (index 5, count `+36` = `$26c28`), proven.** Click: `+14 = $40` (bit 6), count 5 to 4. The handler runs a
32-tick cycle (`10(A0)` is the tick, `& $1f`; the low nibble is the phase). Phases 2 to 5 erase one mask frame each,
**timed with `watch`**: `$81d0` increments `10(A0)` first (`& $1f`), then a post-increment low nibble of 2 to 5 selects mask
frame `nibble - 2` (`$8210`-`$8216`) and `$8246`-`$8352` ANDs its 10 rows by 8 words into the bitmap; a `watch` on rows 66 to 75
of group 46 saw 8 bursts of exactly 80 word writes (10 rows by 8, 125 steps each) at the ticks 2, 3, 4, 5 and 18, 19, 20, 21, one
burst a tick, and the next at tick 34 (= 2 of the next cycle) (`py/maskwatch.py`, 960 writes); phases 11 to 15 move `x += dir` one a tick
(`hits`: `$8422` runs 5 times, 4 ticks apart, per half cycle), and the 32-tick cycle holds two such erase-and-advance halves: against a poked wall (`--wall 46,48,56,74`, solid from x = 736) lemming 0 stays at x = 732, then 733, 734,
736, 737 over the first half cycle (+5), and after 40 samples of 36,000 steps the wall's left face has moved from x = 736 to
x = 746 over rows 70 to 75, the tunnel being the body height (about 9 rows above the feet row). With nothing to bash
(flat ground) it erases the few pixels of the shallow hill in front and then drops `+14` back to 0 after one cycle
(10 pixels cleared, `--samples 30` run): a swing at open ground ends. At the end of each half cycle `$84b4` tests the
cell under the lemming and the cell two rows up and two columns ahead (`25`/`26(A0)` as in "Collisions"): code 9
(steel) refuses, and codes 7 and 8 refuse when the lemming faces the matching way; a refusal calls `$1f18` and turns the lemming round
(`neg 8(A0)`, `bclr #6`). **Proven for steel:** with cells 186..193 poked to 9 (rows 14 to 24) the basher
quits at x = 735 and walks left (`dir = -1`, `+14 = 0`) at sample 15; the run without them keeps bashing to
x = 742 and beyond.

**Miner (index 6, count `+40` = `$26c2c`), proven.** Click: `+14 = $10` (bit 4), count 5 to 4. A 24-tick cycle
(`cmp #$18`): phase 0 steps `y + 1` and gives up at `y >= $b0`; phases 1 and 2 erase the two mask frames and step
`x += dir`, `y + 1` (**timed with `watch`**: `$7b88` increments `10(A0)` first, then post-increment ticks 1 and 2 of each cycle AND
a 13-row mask frame (`$34` bytes, 104 word writes in one burst), the second a row lower than the first because `$7bcc`-`$7bd0`
step `x`, `y` between them; bursts at tick intervals 23, 24, 47, 48 in a 60-tick run, 4 of 4 with 104 words, `py/maskwatch.py --miner`); phase 3 steps again with a ground test; phase 15 steps `x += 2*dir` after the wall
test (the steel and one-way cell test `$7e68`, same codes as the basher). Result from the click at (734, 78): after
four cycles the lemming is at (750, 86): +4 columns and +2 rows a cycle, i.e. a 2:1 slope (a tunnel of 17 columns for 9
rows in the dumped bitmap, rows 76 to 85, about 9 rows tall). **Proven for steel:** with the same poke the
miner stops and turns at x = 736 in the first cycle; without it the run above goes on to x = 750.

## The other skills (all driven from `sel.snap` with `py/skilldrive.py`, one tick = 36,000 steps)

Each run pokes the skill index and count (the click path is proven), clicks lemming 0, and dumps the bitmap window.
Where a control is named it is the same snapshot with `--noclick`. Pokes of terrain (`--wall`, `--wallval 0`) are
inputs, not findings, and are named in each line.

- **Builder** (index 4, count `$26c24`): `+14 = $200` (bit 9). The hill ahead of lemming 0 refuses it at once (it
  turned round after one tick, the head-clearance tests at `$85d0`/`$8602`), so rows 70 to 75 of groups 45 to 49
  were cleared first. Then 12 bricks (`20(A0)` counts `$c` down), a brick every 16 ticks: 6 pixels set per brick (72 set in all), the lemming climbing
  one row and two columns per brick, (732, 76) to (756, 64), then bit 0 (`$86be`, the shrug) when the count runs out.
  A solid pixel in front at head height, or one three cells ahead, ends the stair early (`$866a`: turn round).
- **Climber** (index 0, count `$26c22`): against a 19-row wall (`--wall 46,48,56,74`, face at x = 736) the walker
  reaches x = 736 and `+14` becomes `$1000` (bit 12): y 75 to 58 over about 28 ticks, then `$800` (bit 11) for the
  pull-over (y 58 to 56), then `+14 = 0` and it walks on along the top at 1 pixel a tick.
- **Floater** (index 1, count `$26c2a`): a pit (`--wall 47,47,76,139 --wallval 00000000`, x 752 to 767, rows 76 to 139)
  makes lemming 0 fall: `+14 = $8000` (bit 15), 3 rows a tick, `19(A0)` counting up by 3. With the floater, bit 5 (`$20`)
  appears about 6 ticks later (y 79 to 97, `19(A0) > $10`), the fall slows to about 2 rows a tick, it lands at y = 140 with
  `+14 = 0` and walks on. Control (no click): the fall continues at 3 rows a tick, lands at y = 140 with `+14 = $8100`
  (bits 15 and 8: the splat) and the record is dead (`+24`), 64 rows fallen.
- **Bomber** (index 2, count `$26c1e`): `21(A0)` counts down from `$4f` once a tick while the lemming keeps walking
  (731 to 810 in 79 ticks). At zero `+14 = $10000` (bit 16) for 16 ticks with x frozen (the "Oh no"), then `$400` (bit 10).
  The crater is erased at that change: 113 pixels in one sample (a bowl 16 pixels wide (x 802 to 817) and 8 rows deep (y 84 to 91) under the feet at
  (810, 84)). **The crater (proven):** at frame 1 of bit 10 `$8156` stores the record pointer in `152(A5)` (`$816e`: `move.l A0,152(A5)`,
  sound `$14`); the main loop at `$109a` calls `$55b6` once a frame, which takes the pointer (and clears it) and **refuses** when
  the cell code in `25(A0)` is 9 (steel), 5 or 1; otherwise it sets the clip window `$660 x $a4` and calls the general blitter
  `$8cf8` (the mask-AND entry, `$aae8`; its `A5` is the blit block `$c822`) with flags `$4d`, the 16 by 22 mask at `$14fd2`
  (22 words, a filled disc; a set bit erases), destination the terrain plane `$41800`, at `(x - 8, y - 14)`. The prediction
  (mask bits AND the pre-erase bitmap) matches the observed erase exactly: 113 of 113 pixels, 0 differing (lemming at (810, 84),
  window 768..863 by rows 62..101, the tick after the 16-tick "Oh no"); with steel (code 9) poked under the lemming's cell
  (columns 198..205, rows 19..23) 0 pixels clear over 100 ticks. `hits` over 4,200,000 steps: `$aae8` runs twice with a bomber
  (the first a 32 by 32 explosion sprite into the screen buffer from `$5348`, the second the terrain erase from `$5614`) and
  0 times in the no-click control. The record stays in bit 10 for 52 ticks, then it is dead (`$8156`).
- **Digger** and **blocker**: above.

## Still open

The object table behind the high nibble of a cell (`$23044`, stride `$22`: the animations and sounds of exits and traps) is unread; fields +10 (frame), +20, +36/+38/+42 beyond the readings above, and the release rate; the blocker's
refusal test (`$1b60`-`$1b94`, cells with codes 1, 2, 3, `$a` under the target) and the ground-loss release.

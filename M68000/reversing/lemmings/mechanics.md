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
| 2 | 3 | `$8a62` | probes terrain a lemming-width ahead (`8(A0)*8`): unnamed |
| 3 | 8 | `$81ba` | 16 frames then `st 24(A0)` (record dead): read as a splat or similar death |
| 4 | 10 | `$8156` | the explosion: frame 1 plays sound `$14` and releases a blocker (`bclr #7`, `bsr $8a06`: **proven**), dead at frame `$34` |
| 5 | 15 | `$7a9a` | fall (set by the walker `$797c` when 4 rows below are clear; 4-frame cycle): read |
| 6 | 13 | `$801c` | ledge hop: the walker `$7a88` sets it when the wall in front is 4 to 6 rows high (read) |
| 7 | 1 | `$8aca` | 8 frames, then `addq.w #1,20(A3)` and the record dies: read as the exit (the saved counter at `$26c18`) |
| 8 | 2 | `$8b5c` | 14 frames then dead: a trap death, unnamed |
| 9 | 14 | `$8850` | **digger, proven** (below) |
| 10 | 12 | `$86f2` | climber: `$8194` sets it from the walker when a wall 7 rows high blocks a lemming with `+22` set (read) |
| 11 | 11 | `$880a` | unnamed |
| 12 | 9 | `$851c` | builder: `$1d6e` sets bit 9 (read) |
| 13 | 7 | `$89a4` | **blocker, proven** ("Collisions" below) |
| 14 | 6 | `$81d0` | **basher, proven** ("Basher and miner" below) |
| 15 | 5 | `$7f06` | unnamed |
| 16 | 4 | `$7b88` | **miner, proven** ("Basher and miner" below) |
| 17 | 0 | `$86be` | unnamed |
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
ground down. Pixel set: probe upward `y-1..y-7`: a clear row within 3 steps up is a smooth step (`y` rises 1 to 3); a
clear row 4 to 6 up is the ledge hop (bit 13); seven solid rows is a wall, which turns the lemming (`neg 8(A0)`) or, with
`+22` set, starts the climb (bit 12, `$8194`). The fall handler `$7a9a` drops 3 rows a tick and adds 3 to `19(A0)`;
landing with `19(A0) > $3c` and no floater sets the splat bit 8 (`$7b28`), and `> $10` with a floater opens it (bit 5).

**Object map** (`A2 = $62f80`, 4-pixel cells, one byte each, row stride `$198`; the lemming's cell is
`(x/4, y/4)`). After every update `$8b6e` stores that cell in `25(A0)` and the cell two columns ahead in the row two
above in `26(A0)` (the miner and basher steel and one-way tests), then dispatches on the cell's low nibble (the high
nibble indexes the `$23044` object table, stride `$22`):

| low nibble | effect (`$8b6e`) |
|---|---|
| 1 | state bit 1 (`$8aca`, the exit), sound `$11`; skipped if bit 1 or 15 is already set |
| 2 | reverse a lemming walking right (`8(A0) >= 0`) |
| 3 | reverse a lemming walking left |
| 4 | marks object bit 1 and `st 24(A0)`: the lemming vanishes |
| 5 / 6 | state bit 3 / bit 2 (the `$8a62` / `$8b5c` death handlers), skipped if already set |
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

## Basher and miner

Both erase terrain by AND-ing a mask from a table into the bitmap at `(x + dir + 4(A0), y + 6(A0))` (`$8218`-`$8256`
and `$7bd8`-`$7bfc`: a mask is 6 rows of a long, shifted by `x & 15` across the 16-pixel groups). Basher masks are
at `$14cc2` (4 frames of `$28` bytes, mirrored `+160` for dir < 0), miner masks at `$14e02` (2 frames of `$34`,
mirrored `+104`). A game tick is 36,000 steps (3 VBL: `hits` on `$81d0` is 17 calls in 600,000 steps, 16 gaps of
35,900 on average). The driver is `py/skilldrive.py` (pokes the skill index and count, clicks lemming 0, dumps the
bitmap window as ASCII each sample) and `py/terrain_diff.py` (cleared and set pixels against the first frame);
`--wall gx0,gx1,y0,y1` pokes a solid block into the bitmap and `--cells c0,r0,r1,val` pokes object-map cells.

**Basher (index 5, count `+36` = `$26c28`), proven.** Click: `+14 = $40` (bit 6), count 5 to 4. The handler runs a
32-tick cycle (`10(A0)` is the tick, `& $1f`; the low nibble is the phase). Phases 2 to 5 erase one mask frame each
(read from the code; the diff only brackets the ticks), phases 11 to 15 move `x += dir` one a tick
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
`x += dir`, `y + 1` (read); phase 3 steps again with a ground test; phase 15 steps `x += 2*dir` after the wall
test (the steel and one-way cell test `$7e68`, same codes as the basher). Result from the click at (734, 78): after
four cycles the lemming is at (750, 86): +4 columns and +2 rows a cycle, i.e. a 2:1 slope (a tunnel of 17 columns for 9
rows in the dumped bitmap, rows 76 to 85, about 9 rows tall). **Proven for steel:** with the same poke the
miner stops and turns at x = 736 in the first cycle; without it the run above goes on to x = 750.

## Still open

Names for bits 0, 2, 3, 5, 8, 11 beyond the readings above; the builder (bit 9, the `$851c` stair) and the climber and floater are undriven; the
terrain thresholds (step, ledge, wall, fall, splat) are read, not driven; the exact basher and miner erase ticks need a per-tick (`watch`) trace, the diff only brackets them; the cell codes 1, 4, 5, 6 need their level objects (exit, traps) driven; the blocker's
refusal test (`$1b60`-`$1b94`, cells with codes 1, 2, 3, `$a` under the target) and the ground-loss release.

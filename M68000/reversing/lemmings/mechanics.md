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
| 1 | 16 | `$8064` | 16-frame cycle, sound at frame 5, `bsr $8134` at the end: read as the explosion (unproven) |
| 2 | 3 | `$8a62` | probes terrain a lemming-width ahead (`8(A0)*8`): unnamed |
| 3 | 8 | `$81ba` | 16 frames then `st 24(A0)` (record dead): read as a splat or similar death |
| 4 | 10 | `$8156` | 52 frames then dead; frame 1 plays sound `$14` and clears a blocker (`bclr #7`, `bsr $8a06`): read as the "Oh no" countdown before the explosion |
| 5 | 15 | `$7a9a` | fall (set by the walker `$797c` when 4 rows below are clear; 4-frame cycle): read |
| 6 | 13 | `$801c` | climb (set by the walker `$7a88` at a wall when `+22` is set): read |
| 7 | 1 | `$8aca` | 8 frames, then `addq.w #1,20(A3)` and the record dies: read as the exit (the saved counter at `$26c18`) |
| 8 | 2 | `$8b5c` | 14 frames then dead: a trap death, unnamed |
| 9 | 14 | `$8850` | **digger, proven** (below) |
| 10 | 12 | `$86f2` | unnamed |
| 11 | 11 | `$880a` | unnamed |
| 12 | 9 | `$851c` | builder: `$1d6e` sets bit 9 (read) |
| 13 | 7 | `$89a4` | blocker: `$1b9c`-`$1c26` sets bit 7 and stamps cells into the object map (read) |
| 14 | 6 | `$81d0` | basher: `$1cd6` sets bit 6; handler cycles `andi.w #$1f` = 32 frames (read) |
| 15 | 5 | `$7f06` | unnamed |
| 16 | 4 | `$7b88` | miner: `$1c2a` sets bit 4 (read) |
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

## Still open

Names for bits 0, 2, 3, 5, 8, 10, 11, 12, 16 beyond the readings above, the terrain bitmap format (the
walker tests one plane at `$41806`, row stride `$330`, 8 bytes per 16 pixels, `btst` bit `7 - (x & 7)`
of the byte `x/16*8 + ((x >> 3) & 1)`), and the object map at `$62f80` (4-pixel cells, stride `$198`; cell
low nibbles 1, 2, 3 and $a block a blocker or builder placement).

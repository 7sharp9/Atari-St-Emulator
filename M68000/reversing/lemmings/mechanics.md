# Lemmings: behaviour

Addresses are runtime absolute, from `scratchpad/lemmings/lvl1.snap` (made by `drive.txt`), whose
whole-image listing is `disassemble.py --snap <snap> --all 0x2000 0x27000`. Globals live at
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

**Read:** `$7802` (called while `25(A5)` is clear) loops the records, skipping `+24 != 0`. For each
it loads `D0 = x`, `D1 = y`, `D6 = long +14`, `D3 = byte +21`, calls `$80ea` when `D3 != 0`, then tests
the bits of `D6` in a fixed priority order and branches to a handler per bit; each handler writes
`D0`, `D1`, `D6` back to the record. This is a bit-mask state machine, not a per-state integer.

| `btst` order | bit | handler |
|---|---|---|
| 1 | 16 | `$8064` |
| 2 | 3 | `$8a62` |
| 3 | 8 | `$81ba` |
| 4 | 10 | `$8156` |
| 5 | 15 | `$7a9a` |
| 6 | 13 | `$801c` |
| 7 | 1 | `$8aca` |
| 8 | 2 | `$8b5c` |
| 9 | 14 | `$8850` |
| 10 | 12 | `$86f2` |
| 11 | 11 | `$880a` |
| 12 | 9 | `$851c` |
| 13 | 7 | `$89a4` |
| 14 | 6 | `$81d0` |
| 15 | 5 | `$7f06` |
| 16 | 4 | `$7b88` |
| 17 | 0 | `$86be` |
| none | : | `$797c` (the `tst.l D6 / beq` target; reads as the default walk) |

Roles are not assigned yet: name each handler from its own body (read to its first branch), then
confirm it under `callcap` on a snapshot where one lemming holds that bit. The skills' bit
positions are the first question, since the click on a skill icon sets or clears a bit in `+14`.

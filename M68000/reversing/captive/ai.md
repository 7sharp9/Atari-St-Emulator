# Captive: creature AI

How the groups of creatures inside a base decide to wander, chase, turn and attack, in `federation` (globals
A6-relative, A6 = `$1b5ce`; all addresses are runtime absolute). Scripts and the commands that reproduce every
count here are in `py/ai/` (its README holds the table). The state they run on is a base entered by a labelled
poke (section "Getting into a base"), so every live observation below is from that level: mission 1, level request
4, `fed_MapGen` called with D2 = 0, D3 = 0.

Proof labels: **proven** names the command and the count or observation; **inferred** is from code reading only.

## Summary

Creatures move as groups of up to nine in one map cell. Each group acts on its own timer and decides from four
inputs: its flags, its facing, the party's position, and one byte of the map cell it stands on. Sight is a straight
line: a group "sees" the party only on the same row or column and at most 6 cells away, with no wall test in the
decision. Out of sight, an aware group steers by a direction stored in its own map cell. That second map plane
starts as the level generator's dig tree: each open cell points to its neighbour that was dug earlier, so the
arrows lead back along the digger's path toward the entrance, with "take the lift" (4 or 5) where that path changed
floor. The party overwrites it as it walks: every cell the party leaves records the direction it went. A creature
that has lost sight of the party therefore walks the party's footprints when it is standing on them, and walks back
along the dig tree when it is not, until it reaches a lift cell, where a value of 4 or more makes it forget the
party. The breadcrumbs never fade.

## Scheduling

- `$102a0` (cr_UpdateAll) runs once per main frame, every 60,000 steps (5 VBLs). It advances the frame RNG, then
  walks the group list. **Proven**: 20 calls in 1.2M steps (call census, `base.evt`, from `req4.snap`).
- The frame RNG is `15530(A6)`: `x = x * $5e5 + $29` mod 65536 (`$102a0`-`$102ac`; the same step in `$105f8`,
  cr_Rand, for each wandering group). A second generator with the same constants at `1770(A6)` drives animation
  and attack rolls (`$10a78`, `$10e24`). **Inferred**.
- Each group has a timer at +6 and a period at +7. While timer <= period the timer counts up; when it exceeds the
  period it is cleared and `$10304` (cr_GroupThink) runs for the group, so a group acts every period + 2 frames
  (`$102de`-`$102fa`). **Proven**: `track.py p2.snap 200 7`, group 16 (period 16) acted at frames 4, 22, 40, 58 and
  76.
- A group whose forward step is blocked has its timer set to period / 2 (`$104f6`-`$10500`), so it retries sooner.
  **Inferred**.

## Data

### Group list

`4532(A6)` = `$1c782` (`$102d4`). Variable-length records chained by their own size word; a negative size ends the
list. **Proven** (layout): `dumplist.py req4.snap` walks 63 records to the end marker at `$1d152`.

| offset | field | evidence |
|---|---|---|
| +0, +1 | x, y (bytes) | compared with the party's `26(A6)`/`28(A6)` at `$1034a`; written on a move at `$1052e` |
| +2 | record size, 8 + 8 x members (`$10`..`$50`); negative = end | `$102d8`, `$102fe` |
| +4 | flag byte: bit 7 = the group may not enter tile `$1b` (the door at (14,2) in this level) | `$10648`-`$10652`; groups 0-2 have it |
| +5 bits 0-1 | facing: 0 N (-y), 1 W (-x), 2 S (+y), 3 E (+x) | direction table `$10372`-`$10394`; party facing `30(A6)` uses the same codes (keypad turns, `keys.py`) |
| +5 bit 2 | regroup pending | tested and cleared at `$10534`; no setter found by name or by raw scan |
| +5 bit 3 | aware: tracking the party | set `$10480`, cleared `$1045e`, `$104f0` |
| +5 bit 4 | hostile: may become aware and may attack | set `$10726` (contact with the party), tested `$10478`, `$10da2`; set by the generator for some groups |
| +5 bit 5 | cell action pending | set `$106a0`, handled `$10732` |
| +5 bit 6 | relentless: never forgets the party and never uses the trail | `$1043a`, `$1046a`, `$104e8` |
| +6, +7 | timer, period (frames) | section "Scheduling" |
| +8.. | members, 8 bytes each | below |

Meaning of bits 3 and 5, the facing, and bit 6's effect on the trail branch: **proven** by the gate (section
"Decision rule"). The rest of the table: **inferred**.

### Member

| offset | field | evidence |
|---|---|---|
| +0 | type (`8(A0)` is the lead member's type, the one the decision reads) | `$10328`, `$1065a` |
| +1 bits 0-3 | slot 0-8 in the cell's 3x3 grid; a lone member sits at `$14` (slot 4, the centre, with bit 4) | `$10560`-`$10566`, `$1058c`-`$10592` |
| +1 bits 5-6 | bit 6 flips at random while walking (animation); bit 5 = attacking | `$10a8c`-`$10a9c`, `$10e4a` |
| +2 | word, 72-1013 in this level; hit points is a guess, no writer read | `dumplist.py` |
| +5 | attack skill: the to-hit roll succeeds when (RNG2 >> 3) & `$ff` <= skill + 20 | `$10e34`-`$10e46` |

**Inferred**, except the value ranges (`dumplist.py`).

### Map planes

- Tile grid `9242(A6)` = `$1d9e8`, 64 x 32 bytes, cell = 64y + x (`$adb6`, map_CellAt; outside the map it
  returns a dummy cell at `$8910`). Bit 7 = occupied by the party or a group (moved at `$10526`-`$1052a`); the low
  bits are the tile. `$20`/`$60` are floor and 0 is wall (`$945c`-`$9468`; the party walks only on `$20` cells in
  `keys.py`). **Inferred** beyond those values.
- Plane 2, `11322(A6)` = `$1e208`, same indexing; the creature code reaches it as `2080(A1)` from a grid cell.
  - Bits 0-2: the generator's dig tree. Each open cell holds the direction (0 N, 1 W, 2 S, 3 E) of its open
    neighbour with the lowest dig-order number, or 4/5 where the lowest is its lift partner up/down. It is written
    by `fed_MapGen` (stage `$24f4c`) and exported by `$23936` as byte | byte << 3, so bits 3-5 start equal to bits
    0-2 (`mapgen.md`, "The flow field": `py/mapgen/flowfield.py` matches 43,832 of 43,832 open cells). **Proven** on this side: plane 2 is all zero before the generator
    call (`req4_mg.snap`), and in `req4.snap` bits 0-2 equal bits 3-5 in 2026 of 2048 cells.
  - Bits 3-5: the track direction the creatures read (section "The trail").
  - Bit 6: toggled at `$11800`; the door state is a guess (the door opened without its grid tile changing).
    **Inferred**.
  - Bit 7: "seen", set each frame on the party's cell and its four neighbours (`$8694`-`$86d8`). **Proven**:
    `walk.py` shows `$86a0`/`$86ae`/`$86bc`/`$86ca`/`$86d8` writing `$80`-ored values.

### Per-type tables

| table | content | read at |
|---|---|---|
| `$10aac` | property word per type; bits 8, 9, 12, 13 change what `cr_TestCell` (`$10642`) accepts | `$10654`-`$10680` |
| `$10b2c` | byte per type, 1 = may attack from a distance and while turning (1 for types 0, 1, 3, 4, 5, `$d`, `$f`; 0 for 2, 6-`$c`, `$e`) | `$103a0`, `$103fc` |
| `$10b6c` | word offsets to per-type attack descriptors; a negative first byte goes to `$10eec` | `$10e0e` |
| `$10d82` | front slots per facing, 8 bytes each | `$10dbc` |
| `$1063a` | slot pair per facing for a two-member group | `$10616` |
| `$10866`, `$1089e` | formation target slots and member order, by facing and size | `$1059c`, `$105bc` |

The use of `$10b2c` is **proven** by the gate (ATTACK and TURN_ATTACK only for types with a 1). The rest:
**inferred**.

## Decision rule (`$10304`, cr_GroupThink)

Inputs: the record's flags and facing, the lead type, the party's position `26(A6)`/`28(A6)`, the frame RNG
`15530(A6)` as it stands on entry, and the plane-2 byte at the group's cell. The near flag `15598(A6)` is cleared
on entry.

1. Bit 5 set: cell action (`$10732`).
2. Not aware (bit 3 clear), or lead type 6 or 8: wander (`$10464`).
3. The party is on the same row or column, 1 to 6 cells away: aim at it. The direction is S if the group's y <= the
   party's, else N; E if the group's x <= the party's, else W.
   - Facing it and more than one cell away: step forward if the type has no ranged flag or RNG <= `$31e0`;
     otherwise attack (`$10da2`).
   - Facing it and adjacent: attack.
   - Party 90 degrees off: turn one step toward it (`$1050e`). A ranged type with RNG <= `$7d0` turns and attacks
     (`$10408`).
   - Party behind: turn left or right at random (bit 6 of the RNG, `$104f6`).
4. Otherwise (not lined up, or lined up but more than 6 away): set the near flag if both distances are <= 6, then
   follow the trail. A relentless group (bit 6) wanders instead. Read bits 3-5 of the group's own cell: 4-7 means
   forget the party (clear bit 3, `$1045e`) and wander. A direction 0-3 is aimed at like step 3 without the attack
   options: facing it, step forward; 90 degrees off, turn (or turn and attack, as above); behind, step forward if
   the near flag is set, else turn at random.

**Proven**: `gate_decide.py p2.snap 3000 2` pokes one group record (position, flag byte, lead type), the plane-2
byte at its cell, the party's position and the RNG (all labelled pokes that build the inputs). It calls `$10304` with
interrupts masked and stops at the first decision label reached (`$10732`, `$10464`, `$1045e`, `$103be`, `$10408`,
`$1050e`, `$104c6`, `$104f6`). Result: 3000/3000 match the model in the script (WANDER 1231, TURN 659, FORWARD 422,
BEHIND_TURN 257, FORGET 202, SPECIAL 95, ATTACK 68, TURN_ATTACK 66). The model with the range 6 changed to 5 and
`<= $31e0` changed to `< $31e0` scores 2974/3000.

## The trail

When the party steps, the move code writes the direction of the step into bits 3-5 of the plane-2 byte of the cell
it leaves (`$9320`-`$9336`: `andi.b #$c7,(A1)` / `or.b D6,(A1)` with D6 = (`1764(A6)` & 3) << 3; the pointer is set
at `$88c8`). The cell the party stands on is not marked, and nothing clears or ages a mark.

**Proven**:
- `walk.py` (moves E, E, S from `req4.snap`): the breadcrumb writers are `$9332`/`$9336`.
- Cell dumps: after E, E, S (`p14.snap`) the cells left read 3, 3, 2. After four more steps S (`p2.snap`), (14,1)
  to (14,4) read 2.

So the field a creature follows is the generator's dig tree, overwritten wherever the party has been by "the way
the party went from here". Following the arrows from every non-wall cell (`field.py req4.snap`): 449 walks end at
the lift cell (24,3), 11 at the lift cell (2,4), and 74 at the entrance (12,0), the root of the dig, whose value is
0 (north) on the map's top edge. A walk stops at a lift cell because `field.py` does not follow the lift; a creature
standing there reads 4 or 5 and forgets the party. Bits 3-5 give 433, 10 and 75 after the party's first steps.

A natural chase, with no pokes after base entry (**proven**, `track.py p2.snap 200 7`): group 16 (one type-`$e`
member, aware and hostile) stood at (13,4) with the party at (14,5). Its cells' trail values were 0 at (13,4), 3 at
(13,3), and 2 at (14,3) (the party's own breadcrumb). Over five actions it stepped N to (13,3), turned E, stepped E
to (14,3), turned S toward the party now in line, and stepped S to (14,4), next to the party.

## Wander and hostility (`$10464`-`$1051e`)

**Inferred**: the gate stops at the WANDER label and does not cover what follows.

- Draw the next RNG value (`$105f8`) and rotate it right 3. If the group is relentless, or the value is <= `$ccb0`
  (about 80%), a hostile group (bit 4) becomes aware (bit 3).
- Rotate right 3 again. If bit 0 is set, try turning by a random 0-3. The new heading is kept only if the cell
  that way passes `cr_TestCell` (`$9412` via `jsr 20(A5)`, then `$10642`).
- Try a step forward (`$93fe` via `jsr (A5)`, then `$10642`). A free cell moves the group and its occupancy bit
  from `15144(A6)`'s cell to the new one (`$10520`-`$10530`).
- Blocked: the group forgets the party unless relentless, its timer goes to period / 2, and it turns left or
  right at random (`$104e8`-`$1051a`).
- Stepping into the party's cell is a contact: bit 4 is set and the return code is `$fb2e` (`$1070a`-`$10730`).
  Types 6 and 8 never turn hostile this way (`$10716`-`$1071e`).

## Formation (`$10534`-`$1063a`)

**Inferred**: `$1053c` ran 0 times in 6M steps from `g16_adj.snap` (`hits`), because nothing set bit 2 there.

When bit 2 is set:
- One member goes to the centre slot.
- Two members stand side by side across the facing (`$1063a`).
- Three to eight members: with probability RNG <= `$afc8` (about 69%), the first free slot in the facing's
  preference list (`$10866`, by facing and size) is filled by a member taken in the order of `$1089e`.
- A full group of nine is left alone.

What sets bit 2 is not found: a member's death is the likely trigger.

## Attacks (`$10da2`-`$10f1e`)

**Proven** (that the branch runs): `hits` over 3M steps from `g16_adj.snap`, with group 16 adjacent to the party:
`$103be` 3, `$10dfa` 3, `$10e4a` 0. The rest is **inferred**.

- Only a hostile group attacks (`$10da2`).
- Each member standing in one of the front slots for the group's facing (`$10d82`) makes its own attack
  (`$10dfa`). It reads its type's descriptor (`$10b6c`) and rolls the second RNG against its skill + 20.
- A hit marks the member attacking (`$10e4a`) and launches through `$f4b0` (`$10f02`), so an attack is an object
  sent at the party, not an instant hit.
- A descriptor whose first byte is negative instead sets `14798(A6)` = 1 and `15608(A6)` (`$10eec`). `$877e`
  counts `14798(A6)` up each frame and branches to `$87d6` once it passes `$28`; what that branch does is not read.

## Cell action (`$10732`)

When the cell ahead holds tile `$22` or `$23`, `$10642` sets bit 5 (`$1068a`-`$106a0`). On the group's next turn
`$10732` lowers the tile by 2 (to `$20`/`$21`, floor) and plays a sound (`$1076a`, `$c5da`): a creature opening
something in its way. **Inferred**.

## Getting into a base

`$8852` (lvl_HandleRequest) reads the request word `14788(A6)` (`$1ef92`) every main frame, clears it, and sets the
map mode `13564(A6)`:

| request | mode |
|---|---|
| 1 | 1 |
| 2 | 2 |
| 3 | 0 |
| 4 and above | 3 |

It then calls `$90be`, which reaches the `fed_MapGen` call at `$b5c2`. Mode 2 is the planet surface, and mode 3 the
base level the creature code checks for (`$10432`). Mode 3 calls the generator with D2 = 0 (`$b584`-`$b58c`), and
D2 = 1 when `14782(A6)` is 0.

**Proven**: `py/ai/enter_base.repl` from `scratchpad/captive/ld_1.snap` pokes the request word to 4 (a labelled
poke; the longword write keeps `14786(A6)` at `$ff00`). It stops at `$b5c2` after 798,539 steps with D2 = 0,
D3 = 0, A0 = `$1d9e8`. The generator returns 3,254,901 steps later with D0 = 3, and 30M steps on the party stands in
a base room at (12,0) facing a grate. A re-run gives a byte-identical `req4.snap`.

The party's own way in is not found. The only direct writer of `14788(A6)` is the clear at `$885e`, so the game sets
it through a pointer.

Moving in the base (**proven**, `keys.py`, `click.py`):
- Keypad `$68` steps forward, `$67`/`$69` turn, `$6a`/`$6c` strafe.
- Clicking the view at (105,110) opened the door south of (14,1), and the party then walked to (14,5).

## Routines

| address | name | role (from its body) |
|---|---|---|
| `$102a0` | cr_UpdateAll | frame RNG step, group list walk, per-group timer |
| `$10304` | cr_GroupThink | decision rule, move, attack dispatch |
| `$105f8` | cr_Rand | RNG step on `15530(A6)` |
| `$10642` | cr_TestCell | may the group enter the cell at A1: returns 0 (free), -1, `$fb2e` (the party) |
| `$10a66` | cr_AnimFlip | random walking-frame bit per member |
| `$10da2` | cr_GroupAttack | front-slot members attack |
| `$10dfa` | cr_MemberAttack | one member's roll and launch |
| `$10732` | cr_CellAction | lower tile `$22`/`$23` ahead by 2, sound |
| `$93fe` | map_StepAhead | the cell one step from (D0,D1) in direction D6, with its pass code in D2 |
| `$adb6` | map_CellAt | the grid cell for (D0,D1) |
| `$ade2` | dir_RotateOffset | rotate an offset (D2,D3) by facing D6 |
| `$8694` | party_MarkSeen | plane-2 bit 7 on the party's cell and its neighbours |
| `$8852` | lvl_HandleRequest | request word to map mode, rebuild |
| `$90be` | lvl_Rebuild | level rebuild through the `fed_MapGen` call |

## Open

- The party's way in: who writes `14788(A6)` (`watch 1ef92 2` while walking the surface).
- The setter of flag bit 2, and a live regroup.
- What the 74 walks that end at the entry cell (12,0) mean.
- Difficulty: the AI code reads no mission or level number. Speed (+7), skill (+5), member word +2 and the hostile
  and relentless flags come from the generator, so any scaling is there. Not compared across levels.
- The level event raised by a negative attack descriptor (`$10eec`, `14798(A6)`).
- The type names: no RAM string scan was done.
- Extending the gate past WANDER, with `cr_TestCell` passability modelled.

# Captive: creature AI

How the groups of creatures inside a base decide to wander, chase, turn and attack, how they are hurt and killed,
and how the base is entered and left, in `federation` (globals A6-relative, A6 = `$1b5ce`; all addresses are runtime
absolute). Scripts and the commands that reproduce every count here are in `py/ai/` (its README holds the table).
Two bases are used. `req4.snap` and its descendants (`p14`, `p2`, `g16_adj`) are mission 1's level request 4,
reached by a labelled poke (section "Getting into a base"), `fed_MapGen` called with D0 = 1, D2 = 0; `base1/in.snap`
is the base of mission 1 target 1 reached by play alone (D0 = 0, D2 = 0). Each result names the state it ran on.

Proof labels: **proven** names the command and the count or observation; **inferred** is from code reading only.

## Summary

Creatures move as groups of up to nine in one map cell. Each group acts on its own timer and decides from four
inputs: its flags, its facing, the party's position, and one byte of the map cell it stands on. Sight is a straight
line: a group "sees" the party only on the same row or column and at most 6 cells away, with no wall test, so it also
sees through the rock between floors. Out of sight, an aware group steers by a direction stored in its own map cell.
That second map plane starts as the level generator's dig tree: each open cell points to its neighbour that was dug
earlier, so the arrows lead back along the digger's path toward the entrance, with "take the lift" (4 or 5) where
that path changed floor. The party overwrites it as it walks: every cell the party leaves records the direction it
went, and nothing fades a mark. Followed from any cell, footprints lead to the party; dig arrows lead to a lift cell,
where a value of 4 or more makes the group forget the party (a hostile one soon becomes aware again and loiters
there), or into the party's footprints. A group is made hostile
and told to tidy its formation whenever the party's view draws it or a shot hits it. Killing a member subtracts from
its hit points; one creature, Trill (type `$1f`, only in the final base), has an "attack" that ends the base. A
normal base ends by explosives on its generators, and the fire that follows runs down the same dig arrows to the
entrance.

## Scheduling

- `$102a0` (cr_UpdateAll) runs once per main frame. It advances the frame RNG, then walks the group list. The main
  frame's length depends on the load: 60,000 steps (5 VBLs) from the poked `req4.snap` (20 calls in 1.2M steps, call
  census `base.evt`), and 68,793 to 87,207 steps, median 72,000 (6 VBLs), over 100 frames in the natural base
  (`sched.py base1/in.snap 100`). **Proven**. A "frame" below is one call of `$102a0`, not a fixed step count.
- The frame RNG is `15530(A6)`: `x = x * $5e5 + $29` mod 65536 (`$102a0`-`$102ac`; the same step in `$105f8`,
  cr_Rand, for each wandering group). A second generator with the same constants at `1770(A6)` drives animation,
  attack and hit rolls (`$10a78`, `$10e24`, `$f9a8`). **Inferred**.
- Each group has a timer at +6 and a period at +7. While timer <= period the timer counts up; when it exceeds the
  period it is cleared and `$10304` (cr_GroupThink) runs for the group, so a group acts every period + 2 frames
  (`$102de`-`$102fa`). **Proven**: `sched.py base1/in.snap 100` (natural base, no pokes) predicts from each frame's
  timer and period which groups call `$10304`: 2400/2400 group-frames over 24 groups. In the poked base,
  `track.py p2.snap 200 7` saw group 16 (period 16) act at frames 4, 22, 40, 58 and 76.
- `$10304` can leave the timer at period / 2 instead of 0 (`$104f6`-`$10500`, on the blocked-step path), so the group
  acts again after period - period / 2 + 2 frames. **Proven** for the value: in the same run, every timer left after
  a think is 0 or period / 2, and every interval is period + 2 minus that timer (group 1, period 9, stands blocked at
  (28,0) and acts every 7 frames). That `$10500` is the writer is **inferred** from the code.

## Data

### Group list

`4532(A6)` = `$1c782` (`$102d4`). Variable-length records chained by their own size word; a negative size ends the
list. The list has a header (size, free, `$88828881`) at `4528(A6)`, and a dead group is removed by compacting it
through `$c2a6` (list_RemoveBytes), which the object list `2412(A6)` shares. **Proven** (layout): `dumplist.py
req4.snap` walks 63 records to the end marker at `$1d152`; `kill_call.py` (section "Damage and death") removes one.

| offset | field | evidence |
|---|---|---|
| +0, +1 | x, y (bytes) | compared with the party's `26(A6)`/`28(A6)` at `$1034a`; written on a move at `$1052e` |
| +2 | record size, 8 + 8 x members (`$10`..`$50`); negative = end | `$102d8`, `$102fe` |
| +4 | flag byte: bit 7 = the group may not enter tile `$1b` (a hand-operated sliding door; the door at (14,2) in `req4.snap`) | `$10648`-`$10652`; groups 0-2 of `req4.snap` have it. Bit 7 is also read at a death: a lone dying member of such a group drops an item from `4464(A6)` (**inferred**) |
| +5 bits 0-1 | facing: 0 N (-y), 1 W (-x), 2 S (+y), 3 E (+x) | direction table `$10372`-`$10394`; party facing `30(A6)` uses the same codes (keypad turns, `keys.py`) |
| +5 bit 2 | seen since its last action: tidy the formation | set with bit 4 by `$d390`, cleared at `$1053c`, read at `$10534` and `$10e50` (section "Seen, hostile and regroup") |
| +5 bit 3 | aware: tracking the party | set `$10480`, cleared `$1045e`, `$104f0` |
| +5 bit 4 | hostile: may become aware and may attack | set by `$d390` (drawn in the view or hit) and `$10726` (contact with the party); tested `$10478`, `$10da2`; set by the generator for some groups |
| +5 bit 5 | cell action pending | set `$106a0`, handled `$10732` |
| +5 bit 6 | relentless: never forgets the party and never uses the trail | `$1043a`, `$1046a`, `$104e8` |
| +6, +7 | timer, period (frames) | section "Scheduling" |
| +8.. | members, 8 bytes each | below |

Meaning of bits 3 and 5, the facing, and bit 6's effect on the trail branch: **proven** by the gate (section
"Decision rule"); bits 2 and 4's writer by `regroup_watch.py`, bit 2's reader by `gate_regroup.py`. The rest of the
table: **inferred**.

### Member

| offset | field | evidence |
|---|---|---|
| +0 | type (`8(A0)` is the lead member's type, the one the decision reads) | `$10328`, `$1065a` |
| +1 bits 0-3 | slot 0-8 in the cell's 3x3 grid; a lone member sits at `$14` (slot 4, the centre, with bit 4) | `$10560`-`$10566`, `$1058c`-`$10592` |
| +1 bit 4 | on the lead member: the group keeps a pair formation (section "Regroup") | `$1054e`; **proven** by `gate_regroup.py` |
| +1 bits 5-6 | bit 6 flips at random while walking (animation); bit 5 = attacking | `$10a8c`-`$10a9c`, `$10e4a` |
| +1 bit 7 | attack pose waiting to be drawn: set at `$10e58` only while the group's +5 bit 2 is set, cleared by the renderer at `$d082` | **proven** that both write (1 and 17 times, `regroup_watch.py` facing the group); the meaning is **inferred** |
| +2 | hit points (word, 72-1013 in `req4.snap`) | `$fa38` subtracts the damage, `$fac4` runs below 0; **proven** by `kill_call.py` |
| +5 | attack skill: the to-hit roll succeeds when (RNG2 >> 3) & `$ff` <= skill + 20 | `$10e34`-`$10e46` |

**Inferred** where no script is named.

### Map planes

- Tile grid `9242(A6)` = `$1d9e8`, 64 x 32 bytes, cell = 64y + x (`$adb6`, map_CellAt; outside the map it
  returns a dummy cell at `$8910`). Bit 7 = occupied by the party or a group (moved at `$10526`-`$1052a`; the party's
  bit at `$88c0`/`$88da`); the low bits are the tile. `$20`/`$60` are floor and 0 is wall (`$945c`-`$9468`; the party
  walks only on `$20` cells in `keys.py`). Tiles `$01`-`$0f` are decorated rock faces (a side mask, `mapgen.md`,
  "Output encoding"). **Inferred** beyond those values.
- Plane 2, `11322(A6)` = `$1e208`, same indexing; the creature code reaches it as `2080(A1)` from a grid cell.
  - Bits 0-2: the generator's dig tree. Each open cell holds the direction (0 N, 1 W, 2 S, 3 E) of its open
    neighbour with the lowest dig-order number, or 4/5 where the lowest is its lift partner up/down. It is written
    by `fed_MapGen` (stage `$24f4c`) and exported by `$23936` as byte | byte << 3, so bits 3-5 start equal to bits
    0-2 (`mapgen.md`, "The flow field": `py/mapgen/flowfield.py` matches 43,832 of 43,832 open cells). **Proven** on
    this side: plane 2 is all zero before the generator call (`req4_mg.snap`), and in `req4.snap` bits 0-2 equal bits
    3-5 in 2026 of 2048 cells. The 22 that differ all have bits 3-5 = 0: 9 are wall (tile 0) and 13 decorated rock
    faces (tiles `$02`, `$04`, `$08`), whose byte the encoder writes unshifted (`mapgen.md`, "Output encoding").
    Counting only tiles above `$1a` as open, bits 0-2 equal bits 3-5 in every open cell of `req4.snap` and of
    `base1/in.snap` (`trailend.py`).
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
| `$10b6c` | word offsets to per-type attack descriptors; a negative first byte goes to `$10eec`. Of the 64 entries only type `$1f`'s is negative; types 6, 8 and `$2a`-`$3f` have none (offset 0) | `$10e0e` |
| `$10d82` | front slots per facing, 8 bytes each | `$10dbc` |
| `$1063a` | slot pair per facing for a pair formation | `$10616` |
| `$10866` | formation table, 128 bytes per facing: 7 preference rows (group size 2-8, row = size - 2), then 9 member-order rows (target slot 0-8, the code's `$1089e`); facing 3's block ends at `$10a66` | `$1059c`, `$105bc` |

The use of `$10b2c` is **proven** by the gate (ATTACK and TURN_ATTACK only for types with a 1), and the layout of
`$1063a` and `$10866` by `gate_regroup.py`. The `$10b6c` scan is a read of all 64 entries. The rest: **inferred**.

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

The sight test reads coordinates only. Floors are blocks of one 64 x 32 grid (`mapgen.md`, "Floors and lifts"), so a
row or column reaches through the rock into a neighbouring floor's block: in `p2.snap` the party's cross holds 4 open
cells of another floor.

**Proven**: `gate_decide.py p2.snap 3000 2` pokes one group record (position, flag byte, lead type), the plane-2
byte at its cell, the party's position and the RNG (all labelled pokes that build the inputs). It calls `$10304` with
interrupts masked and stops at the first decision label reached (`$10732`, `$10464`, `$1045e`, `$103be`, `$10408`,
`$1050e`, `$104c6`, `$104f6`). Result: 3000/3000 match the model in the script (WANDER 1231, TURN 659, FORWARD 422,
BEHIND_TURN 257, FORGET 202, SPECIAL 95, ATTACK 68, TURN_ATTACK 66). In the natural base, `gate_decide.py
base1/in.snap 3000 2` also matches 3000/3000 (FORWARD 415, TURN 666, the other labels the same). The model with the
range 6 changed to 5 and `<= $31e0` changed to `< $31e0` scores 2974/3000 on `p2.snap` and 2975/3000 on
`base1/in.snap`. Of the 630 trials the model sends down the sight branch on `p2.snap`, 282 have a wall cell between
group and party and 82 sit on different floors, so "no wall test" is proven on those (the split by branch is the
model's; the labels are the emulator's).

## The trail

The party writes the trail; creatures only read it.

- **Leaving a cell.** Every frame `$88ac` calls `$88b8`, which clears `1766(A6)`, looks up the party's cell
  (`$88e4`), clears its occupancy bit, copies its tile to `9240(A6)` and its plane-2 byte to `9241(A6)`, and stores
  the plane-2 pointer in `1766(A6)` (`$88c0`-`$88d0`); `$88d6` then sets the occupancy bit again and marks the seen
  bits (`$8694`).
- **The mark.** A step sets `1764(A6)` = facing `30(A6)` + the move's offset D5 (`$92be`-`$92c6`), so the mark is the
  travel direction, including a strafe or a step back. When the step succeeds, `$9314` stores the new position and
  `$9320`-`$9336` writes (`1764(A6)` & 3) << 3 into bits 3-5 of the latched byte (`andi.b #$c7,(A1)` / `or.b
  D6,(A1)`): the cell the party left records the way it went. The cell the party stands on keeps its older value.
  **Proven**: `walk.py` (E, E, S from `req4.snap`) finds the writers `$9332`/`$9336`; after E, E, S (`p14.snap`) the
  cells left read 3, 3, 2, and the party faced S (`30(A6)` = 2) for both E marks, which were strafes; after four more
  steps S (`p2.snap`), (14,1) to (14,4) read 2. The code path is from reading.
- **Lifts.** The party rides a lift from its tile with keypad 1 or the left lattice icon (up, `$902e`) or keypad 3
  or the right one (down, `$906a`); these go to `$90e2` (up) or `$90d0` (down), which find the partner cell through
  the block-floor table `9206(A6)` and the lift offsets (`$863a`, `$8652`/`$867e`) and store the new position. A
  ride writes no footprint. **Proven** (`py/ai/lift/ride.py`; labelled poke: the party placed at (8,0) from
  `req4.snap`, then input only): the ride (8,3) to (24,3) hits `$902e`, `$90e2`, `$8652` once each and `$9332`/`$9336`
  0 times, by key and by icon, and changes bits 3-5 in 0 of 2048 cells; the ordinary steps before it hit
  `$9332`/`$9336` once each, and the step off the arrival lift changes 1 of 2048 ((24,3), 5 to 1). `$9768`/`$977c`,
  which reach the same two routines from tiles `$30`/`$33` and add a `$f884` hit, were not reached (0 hits; a fall
  through a floor, inferred).
- **A follower at the lift.** A lift end keeps its dig value, and only two of this base's four ends hold 4 or 5:
  (24,3) = 5 and (2,4) = 4, against (8,3) = 0 and (18,4) = 3. What a group does at the cell the party rode from
  depends on that value (**proven**, `py/ai/lift/follow.py`, one row per `$10304` action, the gate's rule matching
  every row). At (24,3), party gone down: group 42 forgets on 4 of its 4 actions there and 0 of 10 elsewhere, but
  being hostile it becomes aware again by wander (in the same action on 2 of the 4) and its neighbours' arrows point
  back into the lift, so it loiters around the lift end for the 137 frames watched. At (8,3), party gone up: group
  20 never forgets (aware in 15 of 15 rows) and walks between (8,3), whose arrow points N, and (8,2), whose
  footprint points S, for 254 frames; the rule read from bits 0-2 instead of bits 3-5 matches 11 of those 15. No
  group changed floor in either window; that none can is inferred.
- **No fading.** 0 of 2048 bits-3-5 values change over 200 frames (12M steps) from `p2.snap` with the party standing
  still (`p2.snap` against `g16_adj.snap` and `track.py`'s end state). No code that clears or ages a mark is known.

**Where the trail leads.** Each footprint points to the cell the party entered next on its last visit, so following
footprints moves forward in time and ends at the party: the footprints form a tree rooted at the party's cell.
The walk has to stop on that cell, whose byte is stale; a walk that reads it too finds a 2-cycle where it points
back at the footprint beside it ((14,5) still holds the dig arrow N against the footprint S at (14,4) in `p2.snap`),
which is what `field.py ... trail` reports as `loop`. `trailend.py`, which stops at the party, follows bits 3-5 from
every non-wall cell:

| state | party | ends at the party | lift (24,3), value 5 | lift (2,4), value 4 | wall |
|---|---|---|---|---|---|
| `req4.snap` (no footprints) | (12,0), the entrance | 75 | 433 | 10 | 61 |
| `p14.snap` (after E, E, S) | (14,1) | 75 | 433 | 10 | 61 |
| `p2.snap` (four more S) | (14,5) | 75 | 433 | 10 | 61 |
| `base1/in.snap` | (30,0) | 263 of 300 | - | - | 37 |

The 75 cells are the dig tree's catchment of the entrance (bits 0-2: `field.py req4.snap` ends 74 walks at the
entrance (12,0), whose value 0 points off the top edge, and 449 and 11 at the two lifts). The party starts on the
entrance, and as it walks its footprints carry that whole catchment with it: every cell that drained to the entrance
now drains to the party. The other cells drain to a lift end holding 4 or 5, where a group forgets. In the natural base, with no lift
cell and the party still near the entrance, 263 of 300 cells lead to the party.

**A natural chase**, with no pokes after base entry (**proven**, `track.py p2.snap 200 7`): group 16 (one type-`$e`
member, aware and hostile) stood at (13,4) with the party at (14,5). Over five actions it stepped N to (13,3) (trail
value 0 at (13,4)), turned E (3 at (13,3)), stepped E to (14,3), turned S and stepped S to (14,4), next to the
party, where it stayed for the remaining 124 of 200 frames. Replaying the gate model on each pre-move state gives the
same five labels: the first three are trail moves on dig-tree values unchanged since `req4.snap`, and the last two
are sight moves, both decided at (14,3) with the party 2 cells S (the step leaves it 1 away). This chase follows the
dig tree into the party's catchment; it does not read a footprint.

**A chase that reads footprints**, keypad input only (**proven**, `footchase.py agents/ai/g16_adj.snap 16 12000000
'0:6c;1:6e,6e,6c,6e'`): the party leaves group 16 by (14,5), (13,5), (13,4), (13,3), (12,3), (12,2), out of its row
and column. The group takes 8 trail actions with a move (5 steps, 3 turns) and then 3 sight actions beside the
party; the gate model's label matches all 11. All 8 trail moves follow bits 3-5 of the cell acted from, and 5 of
them are on cells where bits 3-5 differ from bits 0-2. At (14,5), byte `$88` (footprint W over dig arrow N), the
group turns W and steps W; at (13,3), `$8b` (footprint W over dig arrow E), it turns W. Control: the model replayed
with bits 3-5 replaced by bits 0-2 predicts 2 of those 5 moves, against 5 of 5 with the byte as found. The other two
cannot tell the fields apart, because a dig arrow pointing behind a group with the near flag set gives "step
forward" (decision rule, step 4), the same step as the footprint ahead: a chase scored by step direction alone
overstates the evidence.

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

## Seen, hostile and regroup

**`$d376` (cr_LookupCellMark)** finds the group in cell `68(A6)` and, at `$d390`, does `ori.b #$14,1(A3)` with A3 =
record + 4: it sets +5 bit 2 (seen) and bit 4 (hostile) in one write. It also fills the hit struct at `15028(A6)`
(word member count, long record + 8). Its callers are the view renderer `$a92a` (once per visible cell, before
`$cee4` draws the group) and the hit paths `$f95c`, `$c370` and `$10f38`. So any group the party's view draws, or a
shot hits, turns hostile; wander then makes it aware with about 80% per action. A scan for `5(A0)` misses this writer
because its displacement is 1 from record + 4.

**Proven** (`regroup_watch.py`, a write watch over the whole group list `$1c782`-`$1d152`, 63 records, 1.5M steps
from `g16_adj.snap`):
- Party turned to face group 16 (keys `67,67`, facing N): `$d390` wrote group 16's +5 17 times (`$1e`); `$1053c`
  cleared bit 2 once (`$1a`), and `$10560`/`$10566` re-centred the member's slot. Control, the same budget with the
  party facing S: 0 writes by `$d390`. In that run the +5 writers are `$104f0`, `$10514`, `$1051a`, `$10480`,
  `$104bc`, `$104c2`, `$d390` and `$1053c`; only `$d390` sets bit 2.
- With one labelled poke making group 16 not hostile (+5 = `$0a`), facing it turns it to `$1e` and the member then
  attacks (`$10e4a` writes its slot byte). Facing away it stays `$0a`.
- Not observed: a group that the generator left not hostile turning hostile by coming into view in play.

**`$10534` (cr_Regroup)** is the tail of every move, contact and turn (reached from `$103c2`, `$104e4`, `$1051e`,
and by falling through from the move at `$10520`). When bit 2 is set it clears it and moves at most one member:
- One member: to the centre slot (`& $e0 | $14`).
- Nine members: nothing.
- Lead member +1 bit 4 set: a pair takes the side-by-side slots `$1063a[facing]` (across the facing); other sizes do
  nothing.
- Otherwise 2 to 7 members (8 exits without a move) and RNG `15530(A6)` <= `$afc8` (about 69%): the first free slot
  in the facing's preference row of `$10866` is filled by the first occupied slot in that target's member-order row,
  nearest first.

**Proven**: `gate_regroup.py base1/in.snap 2000 2` (labelled pokes build record 0's size, +5, every member's slot byte
and the RNG; `$10534` is called with interrupts masked) matches the model in the script 2000/2000; the control with
`>=` for `>` in the RNG test and the last source slot for the first scores 1559/2000. In play, after one member of
group 18 was killed by a synthetic hit (`kill_call.py g16_adj.snap 18 ff ff 1 3000000`), its next action turned it W
and `$105f0`/`$105f4` moved the member in slot 8 to slot 0: the pair {0, 6}, the W-facing front column.

**Inferred**: the second reader, `$10e50`-`$10e58`, sets an attacking member's +1 bit 7 only while bit 2 is set, and
the renderer clears it after drawing, so a group's formation and attack pose are tidied only while the player can see
it.

## Attacks (`$10da2`-`$10f1e`)

**Proven** (that the branch runs): `hits` over 3M steps from `g16_adj.snap`, with group 16 adjacent to the party:
`$103be` 3, `$10dfa` 3, `$10e4a` 0. In `regroup_watch.py` facing the group, `$10e4a` writes once. The rest is
**inferred**.

- Only a hostile group attacks (`$10da2`).
- Each member standing in one of the front slots for the group's facing (`$10d82`) makes its own attack
  (`$10dfa`). It reads its type's descriptor (`$10b6c`) and rolls the second RNG against its skill + 20.
- A hit marks the member attacking (`$10e4a`) and launches through `$f4b0` (`$10f02`), so an attack is an object
  sent at the party, not an instant hit.
- A descriptor whose first byte is negative (type `$1f` only) instead raises the level event (`$10eec`): section
  "Trill and leaving a base".

## Damage and death (`$f884`-`$fb1e`)

A hit object resolved by `$f884` (hit_Resolve) on a cell other than the party's goes to `$f954` (hit_Group), which
looks the group up through `$d376` (so a hit also sets +5 bits 2 and 4). `$fa38` subtracts the damage (`$fc66`
multiplies the object's bytes 6 and 7) from the member's +2; when the result is negative `$fac4` (cr_MemberDies)
runs. A dead lone member removes its group record (`$c2a6`); a dead member of a larger group is removed from the
record (`$fc46`).

**Proven** (`kill_call.py`, a synthetic hit object at `$7f000` built by labelled pokes, `$f884` called with
interrupts masked, from `g16_adj.snap`):
- Group 16, damage factors `ff ff`: member +2 `$034f` -> `$0327`, +5 `$1a` -> `$1e`.
- Group 18 (three members): one member removed, size `$20` -> `$18`; at `$fc46` A2 = `$1f082` = `15028(A6)`.
- Group 16 with +2 poked to 1 and its type to `$1f`: the member dies, the record is compacted away, and `$fac8`-`$fad6`
  set `14800(A6)` = 4: the screen "TRILL HAS BE KILLED! DROID'S ARE TO BE WASTED!" over a cutscene
  (`ai_trill_killed.png`).

**Inferred**:
- On a hit `$f9a8`-`$f9da` draws RNG2 `1770(A6)`: with `15528(A6)` set (the in-flight object path `$c990`), RNG2 <=
  `$3830` clears aware; otherwise RNG2 <= `$58f0` makes a hostile group aware.
- Death awards experience to the four crew (`$faf2`-`$fb1e`).
- Shooting type 6 or 8 turns it into 7 or 9 (`$fa82`-`$fa92`); 7 and 9 have attack descriptors, 6 and 8 none.
- `$fc4e` `bclr #3,-3(A2)` looks like a bug: with A2 = `15028(A6)` (proven above) it targets `$1f07f`, the low byte of
  the object-list pointer `15022(A6)` (`$0001c03e`, bit 3 set), not a member byte. It runs only when RNG2 <= `$10b8`
  at a death (RNG2 was `$536f` in the run above, and the byte stayed `$3e`), and `$d3a0` rewrites the pointer on each
  lookup, so the damage is limited.

## Trill and leaving a base

Trill, the captive, is creature type `$1f`, the only type whose attack descriptor starts
with a negative byte. The generator places exactly one Trill group in a final (station) base and none in a normal
one: `gen_types.py` on `gen.py` output (`py/mapgen/gen.py final.json 10,0,1,0 0,0,0,0 21,0,1,1`) finds one
single-member type-`$1f` group with flags `$8050` (door-barred, relentless, hostile) and period 50 or 54 in the two
final bases, and no type `$1f` in the normal base. Type `$1f` is also the only creature the game names (the type test
at `$fac8` and the message there); the uppercase text in the game's code files names items, weapons, droid materials,
the shop and messages, no other creature.

**The level event.** `$10eec` sets `14798(A6)` = 1 and `15608(A6)` = `$ffff`. Every frame `$8772`-`$8790` counts
`14798(A6)` up while it is nonzero and re-arms `15608(A6)`; once it passes `$28` (40 frames) `$87d6` (lvl_ExitBase)
runs. It marks the target visited (byte 2 bit 1 of its `14170(A6)` entry, `14794(A6)` + 1). Outside the final base
(`13412(A6)` = 0) it sets mode 1 and rebuilds, putting the party back at the compound entrance. In the final base the
mission `14776(A6)` goes up by one, `14800(A6)` = -1 and the end screen `$134b8` runs. `$134b8` is the end screen;
`14800(A6)` selects its message (table below). **Proven** (`level_event.py`, labelled pokes of what `$10eec` writes,
on `base1/in.snap`): `$87d6` once at step 2,850,672, mode 3 -> 1, `14794` 0 -> 1, then `$8836` and `$90be` (the
rebuild). With `13412(A6)` = 1 also poked: mission 0 -> 1, `14800` = -1, `$134b8` at step 2,850,693, and the screen
"CONGRATULATIONS ... LEGEND OF TRILL ... FREEING THE CREATOR OF EVIL" with CALL IT A DAY / LET BATTLE COMMENCE
(`ai_trill_end.png`). A final base left without the event sets 2 (below).

**The end screen.** `$134b8` takes the text from the word table at `$1378a` (offsets from `$1378a`, index
2·(`14800` + 2)) and an animation sequence from the digit table at `$134b0` (index `14800` + 2, through the word
table `$1372a`). It returns through `$13624`, which clears a negative `14800` and lets the caller go on (-2 from
`$87ac`, back at the ship after a base exit; -1 from `$881a`, on to the next mission). A positive value is only latched:
the main loop's test at `$56ae` shows the screen and, after a click, jumps to `$5608`, whose `$8570` clears the globals
`A6+0`..`14915(A6)` (mission, visited count and base state with them): the game restarts at CAPTIVE MISSION 0001.

| `14800` | written at | text (`py/phoopel/state3/msgs.py`) | after it |
|---|---|---|---|
| -2 | `$87a6` | BASE HAS BEEN DESTROYED! | play continues |
| -1 | `$8814` | TRILL HAS BEEN RESCUED! ... BUT... | next mission |
| 1 | `$876a` | DROID'S HAVE FAILED! | restart |
| 2 | `$87d0`, `$882e` | TRILL HAS BEEN LEFT TO DIE. DROID'S ARE TO BE WASTED | restart |
| 3 | `$bfaa` | BASE HAS BEEN DESTROYED! WITH YOU IN IT!!! | restart |
| 4 | `$fad6` | TRILL HAS BE KILLED! DROID'S ARE TO BE WASTED! | restart |

The texts are read from RAM; the continue/restart split is read from `$13624` and `$56ae`. **Proven** for 3 (below,
"Finishing a base"), for the -1 and 4 screens (`ai_trill_end.png`, `ai_trill_killed.png`), and for -2 and 2:

- **-2 is the return to the ship after a base exit.** `$87de` sets `14880(A6)` at every base exit; the next level
  event outside a base (mode not 3) shows -2. That event comes from `$9064`, which action 24 (`$902e`, the lift-up
  icon) calls when the party stands on the landing pad, tile `$2e`. `14880` doubles as the end screen's frame counter
  (`$13544`, `$13614`). **Proven by play** (`py/ai/ratt/minus2.py`, from `phoopel/revisit/exited.snap`: the
  compound door by its code, a walk to the pad (23,18), the up icon): `$902e`, `$9064`, `$87a6` and `$134b8` once
  each, "BASE HAS BEEN DESTROYED! / PRESS MOUSE TO CONTINUE"; a click returns to the ship map. Control, `14880` poked
  to 0 before the icon: `$87a6` and `$134b8` 0, straight to the ship.
- **2 is a final base left without Trill.** At `$87c0`-`$8834`, a final base (`13412(A6)`, the base call's D2, = 1)
  left at state 2 or more with `14798(A6)` = 0 writes 2 (`$87d0`, `$882e`); with `14798` set, `$8804` writes -1.
  **Proven with one labelled poke** (`py/ai/ratt/value2.py test`, from `phoopel/finish_base1_blast_state2.snap`, party
  on the entrance facing N and `13412` = 1, then the real leave click): `$87d0`, `$882e` and `$134b8` once, `$8804`
  0, "TRILL HAS BEEN LEFT TO DIE. DROID'S ARE TO BE WASTED" over an explosion, and a click restarts at mission 0.
  Control without the `13412` poke: `$87d0`, `$882e` 0, `$8836` 1, the compound rebuilt. A final base reached by play
  and left this way is not driven.

The end screen ignores clicks for a while: a click registered 2.8M steps after it (value 2) and in under 3.0M
(value -2); 150k steps in it never did (`state3.py leave`). The delay is not constant (inferred: it waits on the
animation).

**Trill's attack is the rescue.** `trill_attack.py` pokes only group 16's type to `$1f` in `g16_adj.snap` (group 16
adjacent and facing the party): at period 16 it attacked 6 times in 6M steps, each attack set `14798` back to 1, and
the count never passed 9, so the base was not left. With the period also poked to the generator's 50: one attack at
step 2,216,659 and `$87d6` at 4,555,866, mode 3 -> 1. The event completes only because Trill acts less often (every
52 frames) than the 40-frame count. Killing Trill instead gives the "TRILL HAS BE KILLED" screen (section "Damage and
death").

## Finishing a base

A normal base is finished by blowing up its generators and getting out. The state is the word `13410(A6)`:

| `13410` | meaning | code |
|---|---|---|
| 0 | untouched | - |
| 1 | fuse: `13408(A6)` counts down from 100 main frames | `$beaa` |
| 2 | burning: the fire advances one cell every 14 frames | `$bf88` |
| 3 | the fire has reached the end of its path: `14800(A6)` = 3, game over in the same frame | `$bfa4` |
| 4 | outside after leaving: the entrance explodes, every 8 frames after 90 | `$8840`, `$bf38` |

- **Arming.** A click on the view with a generator tile (`$28`/`$29`) ahead, in mode 3, with EXPLOSIVES (item `$1b`)
  in the hand slot `404(A6)`, stores the cell in `13406(A6)`, sets `13408`/`13410` = 100, 1 and empties the hand
  (`$deb4`-`$deee`). The generators are one 3 × 3 block of `$28` tiles per base (the generator module's feature `$09`).
- **The blast.** When the fuse ends, `$beb0` turns every `$28` tile in the 5 × 5 block around the cell into `$26`,
  the flame tile, and marks the hand doors and four other tile types across the map (`$befa`-`$bf32`).
- **The fire is a fuse along the dig tree.** Every 14 frames `$c036` reads bits 0-2 of the fire cell's plane-2 byte,
  the generator's arrow toward the entrance (4 and 5 take the lift), and moves the fire one cell that way, lighting
  cells as it goes; when there is no next cell the state becomes 3.
- **Leaving.** A click on the view from the entrance cell facing N raises the leave flag (`$dd7e`-`$dd90`). The
  frame test `$87c0` acts on it only when `13410` > 1; then `$87d6` marks the target visited (`14794(A6)` + 1), and
  `$8836` sets mode 1 and rebuilds the compound. An untouched base cannot be left this way. The rebuild `$90be`
  takes several million steps; while it runs the party word reads (0,0) and `13410` reads 0 (the level init clears
  `13408` as a longword at `$c4d4`), and only when it returns do `$8840` set `13410` = 4 and `$884a` put the party on
  the compound's entrance cell `13556(A6)`, inside its walled box behind the shut coded door.
- **The base blows up behind the party.** `$bd5e` runs the state handler `$be94` every frame while `13410` is nonzero,
  in the compound too. State 4 (`$bf38`) counts `13408` up and, past 90 frames, every 8th frame calls the explosion
  `$107cc` on the entrance cell with a power of 1 rising to 17 in `34(A6)` (`$bf4e`-`$bf7e`); it hits the party through
  hit_Resolve `$f884` and the droid-damage entry `$9a9a`, whose deaths (`$e676`-`$e6e8`) clear a droid's energy pair
  +38/+42. When the live-droid count `410(A6)` (`$8714`-`$873c`) reaches 0, `$876a` sets `14800(A6)` = 1: "DROID'S
  HAVE FAILED!". So the party must reopen the compound door by its code and walk away.

**Proven** in the natural base `base1/in.snap` (labelled pokes: the party's cell and facing, and the hand slot =
`$801b0000`; `py/phoopel/finish13.py` with `SNAP=base1/in.snap`, `py/phoopel/leave.py`):
- the click sets `13410` = 1 with `13408` counting from 100; control with an empty hand: `13410` stays 0;
- state 2 after 8.7M steps, 9 of 9 generator tiles now `$26`; the fire then walks (18,9) to the entrance (30,0), 21
  of 21 moves equal to bits 0-2 of the cell it leaves, reaching the entrance 26.5M steps later; state 3 and
  `14800` = 3 at 36.4M steps;
- leaving from the entrance with the same view click: untouched base, `$dd90` 1 and `$87c0` 1 hit but `$87d6` 0,
  mode stays 3; in state 2, `$87d6`, `$87f4` and `$8836` 1 hit each, visited 0 to 1, mode 3 to 1;
- after that exit (`py/phoopel/revisit.py exit`, then `blast`): 3M steps on, mode 1, party (0,0), `13410` 0, its only
  write `$c4d4`; 30M steps on, `13410` 4 and the party on the entrance (22,22). Over 20M steps from the settled
  state, the party left on the entrance: `$107cc` 8, `$9a9a` 18, `$e6dc` 4, `410(A6)` 0, `14800` 1; turned to face the
  door without opening it: `$107cc` 5, `$e6dc` 4, `410(A6)` 0; door code 8 clicked from inside and four steps north to
  (22,18): `$107cc` 42, `$9a9a` 0, `$e6dc` 0, four droids alive.
The same arming in the D0 = 13 base gives states 1 and 2, 9 of 9 generators to `$26`, and a fire that follows the
arrows for 28 of 29 moves in 60M steps, the other being the lift move from (54,11) to (22,27) (`finish13.py`). What state 3

**State 3 is a game over, wherever the party stands.** In the frame where `$bfa4` writes 3, `$bfaa` sets `14800` = 3,
and the main loop's `$56ae` test, which runs after the state handler, calls the end screen before the leave test
`$8772`/`$87c0` runs again: "BASE HAS BEEN DESTROYED! WITH YOU IN IT!!!", then on a click the restart at MISSION 0001.
So a base can be left only while the state is 2; nothing damages the party first. **Proven**
(`py/phoopel/state3/`, from `finish_base1_blast_state2.snap`):
- `state3.py reach`: `$bfa4` after 27,634,127 steps with the party at (18,8); `order.py` from that stop: `$bfaa` at
  step 1, `$56ae` 79,652, `$134b8` 79,656, `$8772` and `$87c0` 0; 3M steps on, `$107cc`, `$9a9a`, `$e6dc` 0 and
  `410(A6)` 4, the screen up (`ai_state3_end.png`);
- `state3.py leave` (labelled pokes: party onto the entrance (30,0) facing N): over 30.18M steps `$134b8` 1 and
  `$87c0`, `$87d6`, `$8836` 0; afterwards mode 3, `14794` 0, `14800` 3;
- `state3.py after`: no click, the screen stays for 30.06M steps (`$13624`, `$5608` 0); a click, then `$13624`,
  `$5608`, `$8570` once each and 30M steps on mode 1, `14776` 0, `14794` 0, `13410` 0 and the map at CAPTIVE MISSION
  0001; `mission.py`, `14776` poked to 4 first: still 0 after the reset.
The earlier sample of a party poked onto the burning entrance in state 3, mode 1 at (0,0) with the target cleared,
fits this reset.

## Cell action (`$10732`)

Tile `$22`/`$23` is a floor trigger, the generator's feature `$24` (`mapgen.md`, "Output encoding"); from its picture,
a small red floor object, inferred to be a mine. When the cell ahead of a group holds it, `$10642` sets +5 bit 5
(`$1068a`-`$106a0`); on the group's next turn `$10732` lowers the tile by 2 to floor (`$1073c`) and plays a sound
(`$10764`, `$c5da`). The party triggers the same code: entering the cell runs `$985a` (cell_EnterMine), then
`$1073c`, `$10764` and `$c570` (unread). **Proven** for the party: `mine_step.py` steps forward onto each of the two
`$22` cells of a D0 = 30 base: `$985a`, `$1073c`, `$10764`, `$c570` 1 call each, 0 on a floor-cell control. What the
trigger does to the party or a group (damage) is not measured.

## Getting into a base

`$8852` (lvl_HandleRequest) reads the request word `14788(A6)` (`$1ef92`) every main frame, clears it, and sets the
map mode `13564(A6)`:

| request | mode |
|---|---|
| 1 | 1 |
| 2 | 2 |
| 3 | 0 |
| 4 and above | 3 |

It then calls `$90be`, which reaches the `fed_MapGen` call at `$b5c2` (D2 per mode: `mapgen.md`, "Call interface and
seeds"). The request word is written only by `fed_MapView` (`$2f61a`, `$2f630`, `$2f676`, `$2f68e`), when the landing
sequence on the body chosen on the map ends (`world.md`, "Targets and landing seeds"). A base takes two levels:

1. **The compound (mode 1).** Landing on a target's site writes request 1. The generator runs with D2 = 2, the
   surface branch reseeded from the body seed D1, and returns two cells: D6 = the party's start (`13560(A6)`, put
   in `26(A6)` by `$888c`) and D5 = the entrance (`13556(A6)`). For mission 1, target 1, the start is (23,18) and
   the entrance (22,22), inside a box of tile `$2c` walls behind a door tile `$44` at (22,21).
2. **The base (mode 3).** Every main frame `$bd6a`-`$bd8a` tests: mode 1, `13410(A6)` not 4, and the party's cell
   `26(A6)` (longword x, y) equal to `13556(A6)`. Then it sets mode 3 and calls `$90be`, which builds the base with
   D2 = 0 (D2 = 1 at the station's final target). Mode 3 is the level the creature code checks for (`$10432`).
   Leaving puts the party back on the entrance cell in mode 1 (`$8836`-`$884a`).

### The coded doors

**The entrance door is a combination lock** (`$e0b8`-`$e356`). A click on a cell ahead with tile `$40`-`$5f` and
low bits 4 reaches `$e270`, which looks the cell (`68(A6)`, x·256 + y) up in the 8-entry coded-door list at
`2330(A6)` = `$1bee8` (4 bytes: x, y, state word; written by the generator at `$24298`, read also by `$a492` and the
die, below). A click inside one of four corner zones of the view (x `$42`-`$4c` or `$82`-`$8c`, y `$4c`-`$55` or
`$8b`-`$97`, the four triangles drawn on the door) gives a corner index c = 2·bottom + right (TL 0, TR 1, BL 2, BR 3).

- The state word: bits 0-3 are the corners pressed (bit c), bits 4-8 the door's code, (state >> 4) & `$1f`, and
  bits 10-15 the first, second and third corner pressed (c << 2n ORed into the high byte, n = the count including this
  press, `$e2e4`-`$e30e`).
- Pressing a corner already pressed clears the sequence at once (`$e2e4`). Otherwise nothing is checked until the
  fourth press, when `$e31a` compares the high byte & `$fc` with each byte & `$fc` of the 24-byte table at `$e358`.
  The door opens through `$c420` (tile `$44` to `$54`) only when the matching index equals the door's code; any other
  order clears the state to its code (`$e348`). The fourth corner is never stored.
- Every in-zone press calls `$e370`, right or wrong (a click sound, **inferred**), and `$a492` draws a marker per
  pressed corner (**inferred**). The lock gives no per-corner feedback, so a wrong order always costs four presses.
- The table: bits 2-7 of each byte hold the first three corners, and the 24 bytes give 24 distinct triples, so
  every order of the four corners occurs once; bits 0-1 hold the fourth corner. Entry 9 is `$6e` (BR, BL, TR, TL),
  whose bits 0-1 say BL, already its second corner (`$6c` would be clean). The lock masks those bits and is
  unaffected; the die below reads them.

The door at (22,21) has code 8, table byte `$63`: TL, BL, TR, BR. **Proven**:
- `die_hint.py` part B (`$e270` called with the click position `15152`/`15154(A6)` and `68(A6)` poked, on
  `base1/outside.snap`): TL, BL, TR, BR gives `$0081`, `$2085`, `$6087`, `$608f` and reaches `$c420`; the wrong orders
  TR BL TL BR, BR TL BL TR and TL TR BR BL build up the same way and clear to `$0080` on the fourth press; TL, TL
  clears on the second.
- The census in `py/infographics/gen_lock.py --emu` (same calls, state word poked to each code): all 256 four-press
  sequences for each of the 24 codes, 6144 sequences and 24,576 presses, match the model's state word on every press;
  the door opens 24 times, each code on its own order. Non-opening sequences clear at press 2 (1536), 3 (2304) or 4
  (2280); all 552 wrong orders of four distinct corners clear on press 4 with nothing cleared before, so an early
  clear means a repeated corner.

The generator fills the list and draws each door's code at random from the base's RNG (`mapgen.md`, "After the flow
field", "Coded doors"). A blind player needs up to 24 x 4 = 96 presses.

### Door hints: the die and Ratt's message

**The DIE item (type `$5f`) reads the code of the door ahead.** `$1207c` normally rolls the LCG at `15218(A6)`
(`$120aa`: x · `$5e5` + `$29`, ror 3, & `$f`, retried while above 11) for one of 12 faces, `$20`-`$2b` (values 1-6 in
two orientations, odd values red). First `$120ca`-`$1213c` checks the cell ahead `15408(A6)`: a closed kind-2 coded
door (tile & `$7f` in `$40`-`$5f`, tile & `$17` = 2) is looked up in the coded-door list (`$120f4`), the corners already
pressed are counted (n, the state's low nibble, not checked against the order), and the face is `$30` + the next
corner, ((`$e358`[code] ror 2(n + 1)) & 3). The hint faces `$30`-`$33` are a four with one red pip in the next
corner's quadrant, drawn by `$12168` (`ai_die_hint_faces.png`: the plain four `$23`, then `$30`-`$33` with the red pip at TL, TR,
BL, BR). A kind-2 tile not in the list gives
face `$20` (inferred, `$1210a`). With the die, a door costs 4 rolls and 4 presses.

**Proven**:
- `die_all.py` on `req4.snap` (three kind-2 doors, codes 12, 8 and 1): the party poked beside each door, facing it from
  each open side, with 0-3 of its corners already pressed: the next correct corner in 2400/2400 calls; the same cells
  facing the other ways give random faces in 6400/6400. These are 24 and 64 distinct conditions repeated 100 times
  each (the `restore` resets the LCG, and the hint does not use it).
- The census in `gen_lock.py --emu` covers every code: 24 codes x 15 pressed sets x 3 calls, 1080/1080 faces equal the
  model, 264 of the 360 sets not a prefix of the order (the die shows the true order's next corner even after a wrong
  press); control with the door left kind 4, 72/72 random.
- The mission 1 compound door is kind 4 (tile `$44`): `die_hint.py` facing it gives random faces in 1200/1200. With
  its tile poked to `$42` (`DIE_TILE=42 die_hint.py`): `$30`, `$32`, `$31`, `$33` in 300/300 calls each for 0-3 pressed,
  TL, BL, TR, BR, its code 8.
- Code 9's slip: after BR, BL, TR the die shows BL (3/3); pressing BL clears the lock to `$0090`, and TL opens it
  (`gen_lock.py` census). The first three hints on a code-9 door are right, the fourth is wrong. Whether `$6e` is a
  typo for `$6c` is inferred.
- `item_names_emu.py req4.snap 5b 5f 62 66` runs the game's `$675c`/`$70b8`: type `$5f` is picture `$4d`, "DIE". The
  draw path `$66fc` calls `$1208e` only for picture `$4d`. That `$1207c` runs when the die is used (`$fe60`-`$fe66`)
  is **inferred**; no use click was driven.

**The MESSAGE FROM RATT (item type `$66`) gives one fixed order.** `$138ae` prints one of three fixed strings, chosen
by `407(A6)` through the offset table `$138d2` and the print routine `$bb4c`; its only caller is the item-description
dispatch `$702c`. **Proven** (`ratt_msg.py base1/in.snap agents/ai/req4.snap agents/curios/base30.snap`): `407(A6)` =
0, 1, 2 reach `$bb4c` with A0 = `$138d8` "YOU WILL NEED THIS TO DESTROY THE GENERATORS.", `$13906` "TOP-LEFT,
BOTTOM-LEFT, TOP-RIGHT, BOTTOM-RIGHT." and `$13936` "PUT PLANET-PROBE IN HOLAMAP.", the same in all three bases
(door codes 8; 12, 8, 1; 19, 4, 19). No pointer or field writer reaches `$13906` (`tools/find_field_writers.py`,
`tools/find_literal_ptr.py` on `base1/in.snap`: 0; the text is reached through the offset table). The corner text is code 8's order, the code of mission 1 target 1's compound door.

The notes are floor items the generator leaves, and only in mission 1's first target: word 1 at (21,20) of base
D0 = 0's compound, beside its door, and words 0 and 2 inside that base (`mapgen.md`, "Feature and item stages"). So
the corner note is that one door's hint, right because it is generated for no other compound. Nothing hands a note
over: the party picks it up with a click on the floor of the cell ahead. **Proven** (`py/ai/ratt/walk_to_note.py`
then `clicks.py`, from `base1/outside.snap`: five key presses to (21,19) facing S, a click at (130,144)): hand
`404(A6)` = `00 66 00 01`, the cell's pile 1 to 0, `$138ae` and `$702c` once, and the tray reads "MESSAGE FROM RATT
12kg / TOP-LEFT, BOTTOM-LEFT, TOP-RIGHT, BOTTOM-RIGHT."; the same click from (22,19), an empty cell ahead, changes
nothing. Word 0 at (30,1), one cell from the base entrance, is picked up the same way and reads "YOU WILL NEED THIS
TO DESTROY THE GENERATORS." (`clicks.py base1/in.snap`).

### Entering by play

**Proven, no poke**: `py/ai/natural_base.repl` from `scratchpad/captive/mission1.snap` (with `--disk-a`: that
snapshot has no sidecar) selects target 1's site, orbits, lands, walks to (22,20), enters the door code and steps
through to (22,22). The landing call has D0 = 0, D1 = 0, D2 = 2 and returns D0 = 48 after 873,002 steps. The base
call has D0 = 0, D1 = 0, D2 = 0, mode 3, and returns D0 = 3 after 3,590,553 steps; 30M steps on, the party stands at
(30,0) in a base room. Two runs give a byte-identical `base1/in.snap`.

`py/ai/enter_base.repl` reaches a base faster by a labelled poke of the request word to 4 from `ld_1.snap` (the
longword write keeps `14786(A6)` at `$ff00`; D2 = 0, D0 = 1, returns D0 = 3 after 3,254,901 steps, party at
(12,0)). Natural play never writes request 4 with `14782(A6)` nonzero, so that level has no compound and its mode
history is not one the game produces; the generator's base output depends on D0 alone (`mapgen.md`), so the
layout is the natural base for seed 1. The decision rule and the scheduler are proven in both bases.

Moving in the base (**proven**, `keys.py`, `click.py`):
- Keypad `$68` steps forward, `$67`/`$69` turn, `$6a`/`$6c` strafe.
- Clicking the view at (105,110) opened the door south of (14,1), and the party then walked to (14,5).

## Routines

| address | name | role (from its body) |
|---|---|---|
| `$902e`, `$906a` | lift_KeyUp, lift_KeyDown | test the party's own tile `15416(A6)` for a lift end and branch to `$90e2` / `$90d0` |
| `$90e2`, `$90d0` | lift_Up, lift_Down | partner cell on the floor above / below (`$8652` / `$867e`), store the new position, `$10f20` |
| `$863a` | map_BlockFloor | floor of a cell's 16 × 8 block from `9206(A6)` |
| `$102a0` | cr_UpdateAll | frame RNG step, group list walk, per-group timer |
| `$10304` | cr_GroupThink | decision rule, move, attack dispatch |
| `$10534` | cr_Regroup | clear +5 bit 2 and move at most one member toward the facing's formation |
| `$1060a` | cr_PairFormation | the two-member slot pair from `$1063a` |
| `$105f8` | cr_Rand | RNG step on `15530(A6)` |
| `$10642` | cr_TestCell | may the group enter the cell at A1: returns 0 (free), -1, `$fb2e` (the party) |
| `$10a66` | cr_AnimFlip | random walking-frame bit per member |
| `$10da2` | cr_GroupAttack | front-slot members attack |
| `$10dfa` | cr_MemberAttack | one member's roll and launch |
| `$10eec` | cr_RaiseLevelEvent | negative descriptor: `14798(A6)` = 1, `15608(A6)` set |
| `$10732` | cr_CellAction | lower tile `$22`/`$23` ahead by 2, sound |
| `$d376` | cr_LookupCellMark | find the group in cell `68(A6)`, set +5 bits 2 and 4, fill the hit struct |
| `$d398` | obj_LookupCell | the same lookup for the object list, `15020(A6)` |
| `$d3a0` | list_FindCell | list search by cell |
| `$c2a6` | list_RemoveBytes | compact a header list over a removed record |
| `$f884` | hit_Resolve | a hit object on a cell: the party's, or `$f954` |
| `$f954` | hit_Group | look up the group, roll awareness, damage a member |
| `$fa38` | cr_DamageMember | subtract the damage from member +2 |
| `$fac4` | cr_MemberDies | Trill test, experience, item drop, remove member or group |
| `$8772` | lvl_ExitRequest | per-frame count of `14798(A6)`, re-arm `15608(A6)` |
| `$87d6` | lvl_ExitBase | mark the target visited; back to the compound, or the end screen |
| `$be94` | lvl_BaseState | dispatch on `13410(A6)`: fuse, fire step, or the state-4 entrance explosion |
| `$bf38` | lvl_EntranceBlast | state 4: count `13408`, and past 90 frames every 8th frame `$107cc` on the entrance cell |
| `$107cc` | fx_Explode | a blast hit object on cell `68(A6)` resolved through `$f884` |
| `$8710` | party_CountLive | count live droids into `410(A6)`; at 0 set `14800(A6)` = 1 |
| `$e676` | droid_Dies | clear the droid's energy +42 and +38, +50 = 2 |
| `$134b8` | end_Screen | message and animation from `14800(A6)`; returns through `$13624` |
| `$13624` | end_Exit | clear a negative `14800`; a positive one is left for `$56ae` |
| `$8570` | game_ClearGlobals | clear `A6+0`..`14915(A6)` before a restart (`$5608`) |
| `$134b8` | msg_BaseEnd | end screen, message chosen by `14800(A6)` |
| `$88b8` | party_LeaveCell | clear the party cell's occupancy bit, latch its tile, plane-2 byte and pointer `1766(A6)` |
| `$88d6` | party_EnterCell | set the party cell's occupancy bit, then `$8694` |
| `$93fe` | map_StepAhead | the cell one step from (D0,D1) in direction D6, with its pass code in D2 |
| `$adb6` | map_CellAt | the grid cell for (D0,D1) |
| `$ade2` | dir_RotateOffset | rotate an offset (D2,D3) by facing D6 |
| `$8694` | party_MarkSeen | plane-2 bit 7 on the party's cell and its neighbours |
| `$985a` | cell_EnterMine | the party enters a `$22`/`$23` cell: tile - 2, sound |
| `$8852` | lvl_HandleRequest | request word to map mode, rebuild |
| `$90be` | lvl_Rebuild | level rebuild through the `fed_MapGen` call |
| `$e270` | door_ComboLock | door-list lookup by the cell ahead, corner-zone click, order check against `$e358` |
| `$1207c` | die_RollToRecord | the die's face into the item record: hint or roll |
| `$120aa` | die_Roll | LCG `15218(A6)`, one of 12 faces |
| `$120ca` | die_DoorHint | kind-2 coded door ahead: `$30` + the next corner |
| `$1208e` | die_ScrollAndDraw | the die's picture draw |
| `$12168` | die_DrawFace | draw one face |
| `$138ae` | item_RattMessageText | one of three fixed strings by `407(A6)` |
| `$675c` | item_Picture | item type to picture number |
| `$70b8` | item_NameByPicture | picture number to name in the list at `$7cd0` |
| `$2f5f4` | mv_LandDone (fed_MapView) | selection to request word `14788(A6)` and seeds when the landing sequence ends |
| `$2fffc` | mv_SiteHit (fed_MapView) | cursor within 4 units of the body's landing site |

## Open

- A lift follower reached by play alone: both lift runs start from a poked party position. In `req4.snap` the route
  to the lift (8,3) is one cell wide, (12,2) to (10,0) and the coded door (9,0). Group 49 is not always on it (19 of
  300 samples on the corridor cells over 60M steps, 80 counting (12,2) and (12,3)), but once group 16 is hostile it
  camps at (13,3), the room's only exit, and a keypad autopilot found no free path in 45M steps (single runs,
  `scratchpad/captive/agents/liftplay/report.md`). Untried: opening the door (14,2) before group 16 has seen the
  party, or outrunning group 49. The lift pair (2,4)-(18,4) and any `$30`/`$33` tile are not driven.
- The `$fc4e` clear, which needs RNG2 <= `$10b8` at a death.
- A final base reached by play and left without Trill (value 2 is driven only with `13412` poked).
- A real use of the die reaching `$1207c`, and the `$e270` branch on D2 bit 4 (`$e312`, `$e34e`, inferred to be the
  open-door case).
- A group the generator left not hostile turning hostile by coming into view in play.
- What the `$22` trigger does to the party or a group; `$c570`.
- Difficulty: the AI code reads no mission or level number. Speed (+7), skill (+5), hit points (+2) and the hostile
  and relentless flags come from the generator, so any scaling is there. Not compared across levels.
- Extending the gate past WANDER, with `cr_TestCell` passability modelled.

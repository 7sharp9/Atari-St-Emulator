# Populous (Atari ST): people, settlements, mana

All addresses are runtime absolute (POPULOUS.GOD TEXT at $ad58). "Verified" means checked against the
emulator with the scripts in `py/`; "inferred" means read from code but not exercised.

## 1. Where it runs

The main loop `$b510` (one iteration per game frame) calls, when neither `$3b274` nor `$3b276` is set
(both non-zero only in the non-simulating paint/setup modes):

- `$12f84` moving hazard effects in entity slots $d1/$d2 (section 7);
- `$db4c` **entity update**: the whole people/settlement/mana simulation, once per frame.

`$3b222` toggles 0/1 every main-loop iteration (`$b6a2`); it drives the half-rate mana tick and the
walker sprite animation phase. `$3c4c8` is the frame counter (incremented at `$db58`).

## 2. Data structures

### 2.1 Entity record, `$3b278 + 0x16*i`

Slots 0..$cf (208) are people/settlements; `$3c4e2` is the high-water count (trimmed at `$dd2e` while the
last slot has str 0). Slots $d1, $d2 (`$3c46e`) are the two hazard effects run by `$12f84`.
A free slot is any with str <= 0.

| off | size | name | meaning |
|---|---|---|---|
| +0 | b | flags | state bits, table below |
| +1 | b | side | 0 = good, 1 = evil |
| +2 | b | range | walker look-ahead in cells for `$f2f4`; a settlement increments it (max 4) each time it emits a walker, and the walker inherits it |
| +3 | b | weapon | combat class = `$3b248[level]` of the settlement that last updated/emitted it (0..10, castle 20); merges keep the max |
| +4 | w | str | population (settlement) or strength (walker); entity is dead/free when <= 0; capped 32000 on merge |
| +6 | w | t6 | settlement: frame it was founded (`$3c4c8`); fighting: index of the opponent; paused (0x20/0x40): pause counter; ruin (0x80): countdown |
| +8 | w | cell | map cell, y*64+x (x = cell&63, y = cell>>6) |
| +10 | w | off | cell offset of the last step (the walker is animating from cell-off to cell) |
| +12 | w | anim | walker: step phase 0..7; settlement: sprite = $20+level, $2a castle; other states own sprite ranges ($55 celebrate, $5d drown, $65 paused, $82/$86/$8a/$46 fight) |
| +14 | l | knight | non-zero = knight; value = pointer to the enemy entity it hunts |
| +18 | w | last | previous cell, cleared when it no longer equals cell-off |
| +20 | b | aiflag | written by the computer-player routines (`$135fc`); set to 1 on a knight; consumed in `$108b8` |
| +21 | b | lastdir | last (or opposite) direction offset used by the magnet walker `$f6b2` to avoid reversing |

Flags (`$db4c` dispatch at `$df76..$edac`; animation by `$101a0`):

| value/bit | state | per-frame handling |
|---|---|---|
| ==1 | settlement | grows, earns mana, emits walkers (section 4) |
| ==2 | walker | animates; every 8th frame takes one step (section 3) |
| bit 3 (8) | fighting; exactly 8 = the attacker, which runs `$1063a` each frame. A settlement under attack is 9 and is frozen |
| bit 2 (4) | celebrating after a win, anim $55..$57, then cleared |
| bit 4 ($10) | in water (set as $12: any entity whose cell becomes water, `$e136`) |
| bits 5/6 ($20/$40) | paused. $40 = no legal move (`$ef4c`, t6=7); $20 = another walker stepped onto its cell while it was starting a step (`$eb8c`, t6=0). Cleared when t6 passes 14 |
| bit 7 ($80) | ruin / corpse, str 1, t6 counts down from 40 then str 0 |

Occupancy: `$37fd4` byte per cell = entity index+1 (0 empty). `$38fd8` word per cell = walker visit
count (incremented when a walker leaves a cell, `$f29e`). Terrain class `$36e78` byte per cell
(0 water, $0f flat unclaimed, $1f/$20 flat claimed by good/evil, $2f..$31 rock, $35 swamp, $42 ruined
ground); building overlay `$3c522` byte per cell ($21..$29 houses, $2a castle, $29..$2c castle walls,
+$15 when burnt). The terrain area owns these maps; here they are only read.

### 2.2 Side record, `$3b226 + 16*side`

| off | addr (side 0 / 1) | meaning |
|---|---|---|
| +0 w | $3b226 / $3b236 | leader = entity index+1, 0 = none |
| +2 w | $3b228 / $3b238 | papal magnet cell (mirrored in `$3c4ca` / `$3d526`) |
| +4 w | $3b22a / $3b23a | command mode: 0 go to magnet, 1 settle, 2 gather, 3 fight |
| +6 w | $3b22c / $3b23c | towns this frame (non-castle settlements) |
| +8 l | $3b22e / $3b23e | population = sum of str of all live entities of the side, rebuilt each frame |
| +12 l | $3b232 / $3b242 | mana |

`$3affe` = the human's side, `$22284` = the other side. `$3c4c6` = entity shown in the query panel (index+1).

### 2.3 Per-side options/AI record, `$21e0c + 0x2e*side` (DATA segment)

Fields used here: +0 b AI request code (1 = raise land at (+1,+2), 2 = at a ruin), +1/+2 b request x/y,
+6 w computer-controlled flag (1), +8 w AI request pending (the AI planners `$13eda`/`$13a44`/`$135fc`/
`$13816` only run while it is 0), +14 w permitted-power mask ("OPTIONS FOR ..." menu): bit 3 earthquake,
4 swamp, 5 knight, 6 volcano, 7 flood, 8 armageddon (bits 0..2 = modify land / attack towns / attack
leader, the "OPTIONS FOR EVIL" items 1-3, `ai.md` section 2), +16 w aggression/rate used in the score.
+34/+38/+42 l are the planner's "biggest town", "oldest town", "a walker" pointers written by `$db4c`.
The AI area documents the rest.

### 2.4 Game options `$219b2` (menu `$1bc0e`, bit = 1 << row/2)

bit 0 water is fatal, bit 1 swamps bottomless, bit 2 cannot build, bit 3 only build up, bit 4 build near
towns. `$219b0` = computer opponent present.

### 2.5 LAND header tables (read by `load_land` `$14be8` from `landN`, values for land 0)

| addr | contents |
|---|---|
| $37eb0 w | 1: strength lost per walker step (drowning costs 2x per frame) |
| $24998 [11] | growth per 8 frames by level: 0 1 1 2 2 3 3 3 4 4 5 |
| $3b20c [11] | mana per 8 frames by level: 0 0 0 0 1 2 3 4 5 6 20 |
| $3b248 [11] | weapon class by level: 0 1 2 3 4 5 6 7 8 10 20 |
| $3c4fe [11] | mana for capturing/destroying a town by level: 50 100 200 ... 900, castle 2000 |
| $3c4e8 [3] | mana for killing a walker: 100, knight 1000, leader 3000 |

Level index = settlement sprite - $20 (0..9 houses, 10 castle).

## 3. Walkers

### 3.1 Step clock
`$101a0` advances anim; a walker (flags 2) returns "step now" when anim wraps from 7, i.e. one step every
8 frames. On a step (`$e98a..$eace`): swamp check, then `$ef4c` (decide+move), then str -= `$37eb0`.
A walker therefore loses 1 strength per cell walked. Verified: 137/138 steps (the one miss was a walker
that absorbed a merge in the same step).

### 3.2 Choosing a direction
`$ef4c` calls `$f6b2` when mode == 0, the walker is a knight, or Armageddon (`$3d524`) is on; otherwise
`$f2f4`.

`$f2f4` (settle/gather/fight modes) scans the own cell then the 8 neighbours (`$22b4e`, start rotated by
`rand&7`), walking up to `range` cells along each ray until blocked, and records the nearest hit in five
categories: (0) flat unclaimed land ($0f) with no building within 2 cells, or its own cell if
`$18206` gives it a non-zero value; (1) a fight in progress; (2) an enemy; (3) a friendly walker;
(4) the least-visited cell (`$38fd8`), not the direction just taken. Mode 3 returns (2) if found, mode 2
returns (3) if found; otherwise the first found in order 0,1,2,3,4; none gives 999.

`$f6b2` (magnet): with no leader, the walker heads for the magnet cell and becomes the leader if it is
standing on it; the leader heads for the magnet; everyone else heads for the leader's cell. A knight
heads for its target, re-acquired by `$fe00` (nearest live enemy by |dx|+|dy|) whenever the target died,
changed side, became a ruin, or was reached. The heading is sign(dx),sign(dy) mapped through `$225c8` to a
direction in `$225a4` (N NE E SE S SW W NW). If that cell is land (`$18198`==0, and a knight does not
walk into swamp) it is taken. Rock ($2f) is passable only in Armageddon. Otherwise the computer side
posts an AI "raise land here" request, and the walker tries the other 7 directions starting one
anticlockwise, skipping the reverse of its last move; if none works it returns 999.

`$18198(cell,off)` returns 0 land, 1 off-map/wraps, 2 rock $2f, 3 water.

### 3.3 After the decision (`$ef4c`)
- 999: flags |= $40, pause 8 frames.
- The entity already registered at the walker's current cell (`$37fd4`) decides an interaction:
  enemy not fighting -> `$10e7e` start a fight (both get bit 3, t6 = each other, and they share one
  cell); same side -> `$feca` merge; entity already fighting -> `$11006` joins the fight by merging into
  whichever of the two combatants is on its side.
- Merge (`$feca`/`$11006`): target str += walker str (cap 32000), knight pointer and leadership move to
  the target, weapon = max, walker str = 0. A knight never merges into a settlement. A walker that walks
  into its own town therefore adds its strength to the town population.
- Direction 0 (settle here) and not a knight: flags = 1, t6 = frame, footprint claimed by `$10366`.
- Otherwise: visit count++ and occupancy set on the cell being left, cell += dir, off = dir.

### 3.4 Water and swamp
- On a step, standing on swamp ($35) kills the walker (`$10068`); the swamp cell reverts to $0f unless
  swamps are bottomless (option bit 1).
- Any entity whose cell becomes water (terrain lowered/flooded) becomes flags $12. Each frame it loses
  2 x `$37eb0`; with "water is fatal" it dies at once. It recovers (bit 4 cleared) if the cell becomes land.
  A settlement caught this way is first un-claimed and turns into a walker.

### 3.5 Combat, `$1063a` (run each frame by the attacker, flags == 8)
With O = entity[t6] (opponent) and S = self, using the game RNG `$16702`
(seed `$3d52e`: s = ((s*$24a1 mod 2^16) + $24df) & $7fff):

    X = (rand%3+1) * O.str        ; first call
    Y = (rand%3+1) * S.str        ; second call
    m = min(X, Y)                 ; (Y if X > Y else X)
    O.str -= (m/100) * S.weapon + 10
    S.str -= (m/100) * O.weapon + 10      ; integer division truncating toward zero

Both <= 0: both die. Otherwise the survivor wins via `$108b8(winner, loser)`.
Verified 18/18 rounds exactly (str of both sides and the RNG seed), 6/6 resolutions consistent.

`$108b8(winner, loser)`: battles won `$3c514[winner.side]`++. Mana transfer amount e:
- loser a walker: 100, knight 1000, the side's leader 3000 (`$3c4e8`).
- loser a settlement: `$3c4fe[level]` (100 if sprite out of range). If the winner is not a knight the
  town is taken over: the old footprint is released, and if `$18206` gives the winner's cell a value
  it becomes a settlement of the winner's side (the old record is discarded); else it stays a walker.
  A knight instead razes it: record becomes a ruin ($80, str 1, 40 frames), claimed cells become $42,
  building overlay +$15 (burnt).

Then winner flags |= 4 (celebrate), mana[winner] += e, mana[loser] -= e floored at -250 (`$21984`).
Observed: leader killed -> +3000 / -3000 clipped to -250.

## 4. Settlements

### 4.1 Land value and building size, `$18206(side, cell)`
Over the 17 cells centre + ring 1 + four ring-2 axis/diagonal cells (`$22b4e[0..16]`):
- off-map: ignored; rock: value -= 15;
- flat (own claimed colour or $0f): value = 50 on the first hit, then += 15 each;
- centre not flat: return 0;
- any other building overlay ($21..$2c) in the 16 surrounding cells: return 0 (a castle's own wall
  pieces are allowed and counted in `$3b002`).
Values below 35 become 0; exactly 305 (all 17 flat) becomes 3050 = castle.

Sprite/level: value < 3050 -> $20 + value*10/305 (levels 0..9), else $2a castle (level 10).
Capacity = value (castle 3050). Value 0 makes the settlement leave as a walker next frame.
Verified: 4122/4122 settlement sprites over 400 frames.

### 4.2 Per-frame settlement update (`$e22e..$e968`)
Every frame: recompute value and sprite; if the value is 0, or the settlement holds a knight, or
Armageddon is on, it becomes a walker (flags 2).
Every 8th frame (`$3c4c8 & 7 == 0`):

    mana[side] += $3b20c[level]
    weapon      = $3b248[level]
    if str > capacity:                 ; emit a walker into the first free slot
        child.str = str - capacity/2 ; parent.str = capacity/2
        child: flags 2, same side/cell/weapon/range, parent.range += 1 (max 4)
        (leader and query selection follow the child if the parent held them)
    str += $24998[level]

A computer-owned castle over 305 in an AI-pending state caps at 305 (`$e5d4`). If the table is full
(208), `$13372(1)` is called once (inferred: a message). Verified: settlement str 4122/4122,
weapon 516/516, emitted walkers 12/12 (str, side, cell).

### 4.3 Claiming land, `$10366(e, release)`
Founding marks the 17 footprint cells that are $0f as side colour ($1f/$20) and writes the sprite into
the overlay at the centre; a castle claims all 25 cells and writes the wall sprites `$225b4`. Release
reverses it.

## 5. Mana

Per side (`$db4c`):
- +1 every other frame (when `$3b222` != 0), both sides;
- +`$3b20c[level]` per settlement every 8 frames (only level >= 4 earns; castle 20);
- +/- combat transfers (section 3.5), floor -250.
Verified: side mana 774/774 frame transitions, population 774/774, town counts 800/800 (26 frames
excluded because a merge/fight changed totals mid-loop).

Power costs = unlock thresholds `$21984[]`, all conditional on mana >= cost, no paint mode, not
Armageddon, and the side's permitted-power bit:

| routine | power | cost | score bonus (`$36cea`, human only) |
|---|---|---|---|
| `$116fa` / `$1186c` | lower / raise land | needs 10; pays 4*points_changed + 10 (`$37f8a`) | - |
| `$111be` | papal magnet (needs a leader) | 200 | - |
| `$12350` | earthquake | 2500 | 25 |
| `$12a14` | swamp (30 tries in 7x7) | 5000 | 50 |
| `$12ba0` | knight (leader becomes knight, magnet moves to it, side loses leader) | 7500 | 150 |
| `$1263c` | volcano | 10000 | 100 |
| `$11f6a` | flood (all heights -1) | 40000 | 250 |
| `$12d26` | armageddon (clears knights, `$3d524`=1) | 80000 | 5000 |

`$21984` = -250 (floor), 10, 200, 2500, 5000, 7500, 10000, 40000, 80000, 160000, 1999999. The mana bar
`$da52` positions the marker between the bracketing thresholds. Raise/lower can drive mana negative
because only 10 is checked before the charge.

Armageddon: every frame both magnets are forced to cell $820 (32,32), settlements empty, all walkers use
the magnet walker, rock is passable, so the populations meet and fight.

## 6. Population, win/lose, score

`$db4c` end (`$ee3c`): if the human side's population is 0 or it surrendered (`$2287e` = side),
`$1c858(1)` (lost); else if the other side's population is 0 (or it surrendered), `$1c858(0)` (won).
Population bar `$d482`: height = pop*31/50000 + 1.

`$1c858(lost)` score screen, per side (you / him):
- BATTLES WON = `$3c514[side]`; KNIGHTS = live entities with knight != 0; TOWNS = settlements with
  sprite != $2a; CASTLES = settlements with sprite $2a.
- YOUR SCORE = `$36cea` (reset at `$bc56`, plus the power bonuses above) + 5000 if you won more battles;
  for each power bit 8..$100: +1000 if you were not allowed it, +1000 if he was; with a computer opponent
  + (10 - his +16 word)*15; on a win x10; clamped to >= 500, and a value above 555555 is replaced by
  515090. On a win in conquest the score feeds `$1d0e6` (next-world selection).

## 7. Other entity-array users
- `$12f84`: slots $d1/$d2 move one cell every 8 frames along a direction bouncing in a range, marking
  cells as trees/rock/swamp by type (`+20`) and killing any entity they cross (`$10068`). Inferred to be
  power effects; the terrain/graphics areas own the detail.
- `$d482`: query panel for the selected entity.
- Anti-tamper: at entity index $14 `$db4c` compares `$3c4c0` with `$21d4c+$14725836`, and at index $12
  a checksum `$15fe2`; a mismatch sets `$3d524` (forced Armageddon).

## 8. Snapshot contents

game_start.snap (frame 285): 8 entities. Good: 3 settlements (0 at (10,3) str 78 level 2, 1 at (6,4) str
63 level 3, 2 at (9,13) str 50 level 2) and walker 7 at (8,4) str 42 just emitted. Evil: 4 settlements
(3 (57,60), 4 (26,59), 5 (56,55), 6 (26,56)). Leaders: good = entity 2, evil = entity 5 (settlements
can hold the leader). Both modes = 1 (settle), magnets at $820. Mana 542 / 42; population 191 / 78.
g90.snap: 13 entities; 5 new walkers/settlements (7..12). Evil mana stays near 0 because the computer
spends it on raising land. late1..4.snap: without input the array barely changes (the 400-frame run
from game_start is the evidence used here).

## 9. Scripts (`py/`)
- `dument.py <snap>`: print the entity array.
- `capframes.py <snap> <n> <out>`: capture RAM at entry/exit of `$db4c` for n frames.
- `people_model.py <capture>`: Python model of section 4/5 rules and the per-field match report.
  Regenerate: `python py/capframes.py $POP_WORK/game_start.snap 400 run400.bin; python py/people_model.py run400.bin`
  (a 21 MB capture; the one used here is kept at `$POP_WORK/agents/people/fr/run400.bin`).
- `fightcheck.py <snap> <n>`: forces Armageddon and checks `$1063a` rounds against the model.
- `repl.py`: interactive REPL driver.

## 10. Open questions
- Entity +20 is the `$135fc` site-flat result cache (`ai.md` 3.3); its other writers are not traced.
- Flag $20 pause trigger semantics beyond the code condition.
- `$f2f4` wander categories were read from code, not exercised in isolation; mode 2/3 not run.
- Knight creation, flood, volcano, earthquake not exercised in the emulator.

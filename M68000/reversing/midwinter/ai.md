# Midwinter: people and the enemy army

Runtime addresses in the cracked build (`README.md`, "Packing"); A6 = `$2c376`. Snapshots are `drive.txt`'s milestones
in `scratchpad/midwinter/`.

The enemy's strategy is not a planner. Its army is 32 unit records walking a fixed road graph of 96 island sites. Each
tick, a unit either steps a fixed distance toward the site it is heading for or, once there, captures that site and
picks the next one at random among the roads that lead to sites it does not hold yet. How fast a unit moves is
recomputed every game hour from the Warehouses and Synthesis Plants the enemy already holds near it, so the advance
speeds up as it takes supply buildings. Before the player's first turn the army gets a 42-tick head start; after
that it moves nine ticks each time the player ends a 2-hour period from The Team screen's clock icon.

Proof: `py/army/gate_army.py` (also `tools/gates.py run midwinter`, about 5 s). It runs the game's own routines in
`stserver` and checks `py/army/army_model.py` against every call:

- the 42 natural calls of the PLAY head start: **42/42** ticks, 104580/104580 bytes;
- 10 natural supply updates: **10/10**; between the 52 calls no other code writes the army or node state (31008/31008 bytes unchanged);
- the 9 natural calls after one situation report, driven from `d_team.snap`: **9/9**, 22410/22410 bytes (4864/4864
  unchanged between the calls);
- 1000 chained ticks from `d_stark.snap`, 5875 arrivals: **1000/1000**;
- 284 chained supply updates: **284/284**.

Two broken models fail the gate: one that drops the trail write gives 157/200 ticks, and one with a supply bias of 2
for 1 gives 5/10 and 10/20.

## 1. Character records `$2b194`

There are 32 records of `$4a` bytes, indexed by the current character `96(A6)` (`mulu #$4a`, as at `$3192`). The bio
screen `$3288` reads them, and Stark is record 14. Names come from three pointer tables indexed by character: title
`$268d2`, first name `$267d2` and surname `$26752`, joined by `$358e`. The occupation is at `$26a52`, the age at
`$26ad2` (`$3642`) and the biography text at `$269d2`.

| offset | what | evidence |
|---|---|---|
| +0 | flags: bit 0 set on the four women (Caygill, Adams, Maddocks, Randles), clear on all 28 men; bit 1 hides the body-status figure in `$366c` | inferred from the names (4/4, 0/28); bit 1's meaning not read |
| +1..+14 | the 14 qualities and skills in the bio's order (Morale, Energy, Alertness, Endurance, Sturdiness, Optimism, Strength, Stamina, Sharpness, Skiing, Gliding, Driving, Sniping, Sabotage). The bio prints `v * 7 / 250` as Abysmal, Poor, Below Par, Average, Fairly Good, Good, Excellent (loop `$3302`) | Stark's 14 bytes against `stark.png`: 14/14 |
| +15 | a condition byte (`$f9` = full) that sets the height of the bio's body figure (`$373c`). Decisions treats a change across `$f854` as costing 5 minutes (`$31a2`) | role inferred |
| +16..+21, +22..+27 | six pairs that `$3704` maps to the six coloured parts of the body figure (+16.. as `v * 3 / 250`, +22.. overriding with colour 1 or 5) | inferred: injuries per body part |
| +32 | the character's own clock in minutes (`$168` = 06:00). The bio draws it beside the game clock `$2c172` (`$33f4`) | read from the code |
| +34, +38 | position, longwords in 1/256 units; `$35d0` names the place under it ("Little Plains") | read from the code |
| +52 | a pointer to a feature record (`$52b2` reads building types through it) | inferred: the site the character is at |

The period end `$ec8c` (section 2, "When it runs") walks the team list `$2b16c` (character numbers ending with a
negative byte). It takes `$24b7c` off each member's Morale (+1, floored at 0); `$ed88` computes that amount from the
rise in four bytes of `$24bb8`, weighted 2, and one byte, weighted 10, since the last report (inferred: enemy gains
shown on the report). It then brings each member's clock up to the game clock, calling `$f854` for the minutes
skipped. On the driven turn Stark's clock went from 06:00 to 08:00 and his Morale stayed 228 (the amount was 0).

Relationships (the bio's "nearest friends", "hatred of") and recruitment are not located yet.

## 2. The enemy army

### Data

| where | what |
|---|---|
| `$2bb96` | 32 units of 16 bytes: +0/+2 x, y (words, in the same units as the node table); +4 bit 7 active, bits 0-6 the node it last reached; +5 bit 7 spread mode (bit 6 is read by the encounter search `$c2f0`); +6 a weight used by the supply sums; +6..+10 copied by `$c2f0` into an encounter; +11 speed; +12 a second supply sum (reader not found); +13 the target node (0 = choose, negative = stationary) |
| `$25b4a` | node coordinates, (x.w, y.w) for 96 nodes; they equal the x, y words of feature record #n at `$2a150` on 93 of 95 nodes; the two that differ, 59 and 81, have no roads |
| `$25cca` | four road bytes per node, 0 = no road. Nodes 59, 60, 70, 76 and 81 have no roads |
| `$2bb36` | a state byte per node: bit 7 enemy held; bits 0-6 the road a unit last left it by (the trail) |
| `$2a150` | the feature list: a kind byte (bit 7 enemy held, bits 0-6 the building count n), a byte, x.w, y.w, then n words whose first byte & `$1f` is a building type. `$14a8` returns record #node |
| `$2624e` | building names by type (read at `$1c06`, `$52c4`): 0 Mountain Hut, 1 Cable Car Station, 2 Pylon, 3 Garage, 4 Bunker, 5 House, 6 Church, 7 Store, 8 Police Station, 9 Magazine, `$a` Heat Mine, `$b` Warehouse, `$c` Synthesis Plant, `$d` Factory, `$e` Radio Station, `$f` Headquarters, `$10` Ruin |

On `d_stark.snap`, 25 units move (+6..+10 = `05 14 0a 0a 0a`) and 7 are stationary (+13 = `$ff`): units 6, 10, 14,
18 and 22 with +6..+10 = `00 00 7f 7f 7e`, and 30 and 31 with `00 00 7f 7f 7f` and +5 bit 6 set. 33 of the 95 nodes are enemy held.

### The tick `$c136`

For units 31 down to 0, skipping a unit when +4 bit 7 is clear or +13 is negative:

```
target t > 0:  d = isqrt(dx^2 + dy^2) to node t           ($198d8, exact floor root)
               if speed < d: x += dx * speed / d, y += dy * speed / d   (muls/divs, truncated toward 0)
               else (arrive): x, y = node t; bset 7 on feature #t and on state[t]; +4 = t | $80; +13 = 0
target 0, spread mode (+5 bit 7):
               free = the roads from node n whose far node is not held (an empty road counts as held)
               if free: +13 = the (rand mod free)-th free road, in road order;
                        if state[n] has no trail yet, state[n] |= that road
               else:    +13 = road (rand mod 3) (it may be 0: choose again next tick); clear that node's trail bits
target 0, otherwise:
               if $2bb2e != 0: flip it, and if state[n] has a trail, follow it
               else +13 = road (rand mod 3)
```

`rand` is `$d598`: s' = (s * k + k) mod 65537 - 1, with s = `$d5d8` and k = `$d5da` (`$7d1` on every snapshot), and
`rand mod n` is `$d57e`. Because "no free road" picks among roads 0 to 2 only, a unit at a node whose fourth road is
its only way out never takes that road from this branch.

All 32 units are in spread mode, so the non-spread branch and its trail-following toggle `$2bb2e` have not run
under the gate (0 of 7381 choices).

### Supply: `$f56e` and `$f5e2`

Every game hour (`$ee30`'s loop), `$f56e` lists the held feature records that contain a Warehouse or a Synthesis
Plant (`$f656`) and sets each unit's speed +11 to the low byte of

```
sum over those sites of (u[6] + 5) * 500 // (|dx| + |dy| + 50)          ($f6fa)
```

`$f5e2` does the same for Warehouses and Factories (`$f6a8`) with bias 1 and writes +12. A unit beside a captured
Warehouse at weight 5 gains 100 a tick from it alone, while one 450 units away gains 10.

### When it runs

- **The head start.** PLAY on the options screen (`$10914`) calls `$ee30`: it marks feature records 81, 70 and 60
  enemy held (`$ee88`; all three are nodes without roads, so no unit ever reaches them), then six times runs the supply update, seven ticks and +60 minutes on the game clock
  `$2c172`. `$1396` follows, then `$eeb4`, which puts Stark (record 14) at the unit with the smallest x + y + rand
  mod 200, and the clock gets another +120. Census over the PLAY click from `d_options.snap`: `$ee30` 1, `$c136` 42,
  `$eeb4` 1, then the team screen `$2d74` 1. The run ends byte-identical to `d_team.snap`.
- **During play** the player ends each period. `$ec8c` is not called from code: it is the `jsr` entry
  (`$8000ec8c`) of icon 2 of The Team's action table `$23e10`, the clock icon at x 288, y 32 (`team.png`), and of
  icon 3 of `$2494e` and icon 7 of `$249be` (`tables/action_tables.txt`). It runs the period end for the team
  (section 1), the supply update, `$f374`, `$f3be`, the end-of-game tests `$118ba`/`$118f6` (`$118d6`: game clock
  `>= $7080`, 20 days, sets an ending message), then the SITUATION REPORT `$ef36` (`situation_report.png`: "Watches
  synchronized! Your team has two hours before the next situation report is due", and the enemy's held Factories,
  Synthesis Plants, Warehouses, Radio Stations, mobile units and vehicles). Dismissing the report runs nine ticks and
  +120 minutes (`$ed7a`), back to The Team. Driven from `d_team.snap` (game clock 08:00): the clock click gives
  `$ec8c` 1, `$f56e` 1, `$f5e2` 1, `$ef36` 1 and no tick; the report's icon (x 0, y 168) gives `$c136` 9 and
  `$2d74` 1; the game clock goes 480 to 600 and held nodes 33 to 39. So the army moves only when the player ends a
  period, not while a character travels.

Unopposed, the model alone takes the army from 33 held nodes to 80 by tick 80 (about 18 game hours, nine reports)
and 90 by tick 400. The five nodes it never takes are the ones with no roads: 60, 70 and 81 are Radio Stations (each
with a Mountain Hut) that `$ee88` marks enemy held at PLAY, which are the 3 Radio Stations of the report's enemy
column; 76 is a fourth Radio Station; 59 is a Mountain Hut. "Never taken by the walk" is all the tick says about
them: whether anything else captures or attacks them (encounters, bombers) is not read. The player's counter-moves
are not modelled either: sabotage ("PLANT EXPLOSIVES", "REMOVE EXPLOSIVES" in the text), freeing a site, the
encounters.

## 3. Encounters `$c2f0` (read, not proven)

`$c2f0` (called from `$149b2` in `travel_3d_main` and from the re-centre `$152d0`) finds the first active unit whose
position lies inside the 200 x 200 window `2 * (target - 50)` around the terrain target `$19cd4/$19cd6`. It copies
that unit's +6..+10 into `$2bb0a..$2bb12` and its position and target node into `$2baee..$2baf8`, then sets up
the object slots at `$2d47e`. `$c4f2` (from `$12a5e` and `$149be`) uses these counts. So the enemy seen in the 3D
view is the army unit nearest the player, with +6..+10 as its make-up (inferred: the 3D object kinds are not
matched).

## Open

- `$f374`, `$f3be` and the end-of-game tests `$118ba`/`$118f6` in the period end; the report's counts against their
  tables (`$ef8c`).
- Who reads unit +12, and what +6..+10 count.
- The non-spread branch and `$2bb2e` (no unit uses it on these snapshots).
- Relationships and recruitment: the bio's friend and enemy text is prose, so the data behind it is elsewhere.
- The encounter `$c2f0`/`$c4f2` against the 3D objects.
- Node names: `$35d0`/`$217a` name a position; map each node to its place name.

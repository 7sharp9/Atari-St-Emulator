# Midwinter: people and the enemy army

Runtime addresses in the cracked build (`README.md`, "Packing"); A6 = `$2c376`. Snapshots are `drive.txt`'s milestones
in `scratchpad/midwinter/`.

The enemy's strategy is not a planner. Its army is 32 unit records walking a fixed road graph of 96 island sites. Each
tick, a unit either steps a fixed distance toward the site it is heading for or, once there, captures that site and
picks the next one at random among the roads that lead to sites it does not hold yet. How fast a unit moves is
recomputed every game hour from the Warehouses and Synthesis Plants the enemy already holds near it, so the advance
speeds up as it takes supply buildings. Before the player's first turn the army gets a 42-tick head start; after
that it moves nine ticks each time the player ends a 2-hour period from The Team screen's clock icon. The player meets
the army one unit at a time: the unit inside a window around the player brings its vehicles into the 3D view, loses
them for good when they are destroyed, and dies when its strength runs out; destroying one of six leaders destroys
its whole group (section 3).

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
| `$2bb96` | 32 units of 16 bytes: +0/+2 x, y (words, in the same units as the node table); +4 bit 7 active, bits 0-6 the node it last reached; +5 bit 7 spread mode, bit 6 set once the unit has no command vehicle of its own, bits 0-5 an index the loss message uses (the unit number on units 0..29); +6..+10 its vehicles: Snow bulls, Tankers, Snow wolves, Snow cats, Snow foxes (section 3), +6 also the weight in the supply sums; +11 speed; +12 a second supply sum (reader not found); +13 the target node (0 = choose, negative = stationary); +14 strength (section 3); +15 its group (section 3) |
| `$25b4a` | node coordinates, (x.w, y.w) for 96 nodes; they equal the x, y words of feature record #n at `$2a150` on 93 of 95 nodes; the two that differ, 59 and 81, have no roads |
| `$25cca` | four road bytes per node, 0 = no road. Nodes 59, 60, 70, 76 and 81 have no roads |
| `$2bb36` | a state byte per node: bit 7 enemy held; bits 0-6 the road a unit last left it by (the trail) |
| `$2a150` | the feature list: a kind byte (bit 7 enemy held, bits 0-6 the building count n), a byte, x.w, y.w, then n words whose first byte & `$1f` is a building type. `$14a8` returns record #node |
| `$2624e` | building names by type (read at `$1c06`, `$52c4`): 0 Mountain Hut, 1 Cable Car Station, 2 Pylon, 3 Garage, 4 Bunker, 5 House, 6 Church, 7 Store, 8 Police Station, 9 Magazine, `$a` Heat Mine, `$b` Warehouse, `$c` Synthesis Plant, `$d` Factory, `$e` Radio Station, `$f` Headquarters, `$10` Ruin |

On `d_stark.snap`, 25 units move, each with 5 Snow bulls, 20 Tankers and 10 each of wolves, cats and foxes, and
strength 36. 7 are stationary (+13 = `$ff`, strength 255): units 6, 10, 14, 18 and 22 with 0, 0, 127, 127 and 126,
and 30 and 31 with 0, 0, 127, 127, 127 and no command vehicle (+5 bit 6 set). 33 of the 95 nodes are enemy held.

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

## 3. Encounters and losses

The army is not drawn unit by unit. When the 3D view is set up, `$c2f0` takes the first active unit (counting down
from 31) inside a 200 x 200 window around the player, and that unit's five vehicle counts become the vehicles that
appear around the player, a few at a time. Only that unit can lose vehicles to the player. Each loss is permanent: it
comes off the unit's own counts and its strength, and a unit whose strength runs out is destroyed. Destroying one of
the six group leaders also destroys the four units of its group, wherever they are.

Proof: `py/army/gate_encounter.py` (also `tools/gates.py run midwinter`, about 40 s) runs the game's routines in
`stserver` and checks `py/army/encounter_model.py` against every call:

- the natural 3D entry, the ski icon clicked on `d_decisions.snap` (in the REPL): `$c2f0` **1/1**, and the 164 frames
  of `$c4f2` after it **164/164**;
- 165 natural frames from `d_ski.snap` (unit 27 in the window), up to the crash of the unsteered skier: **165/165**;
- every active unit put in the window by a poked target at three offsets: `$c2f0` **96/96**, and 100 chained frames
  after each, **9600/9600** (with the natural legs, 1926 objects placed); a window with no unit: **2/2**;
- the kill `$cbbe` for every unit, of its command vehicle and of one vehicle of each kind at strengths 1, 2 and 36,
  up to its radio message: **512/512** (48 leader kills, which take 192 group members with them).

Four broken models fall short: no random turn (92/9600 frames), tankers drawn before bulls (`$c2f0` 40/96, frames
9101/9600), every kind costing 1 strength (384/512), no group cascade (464/512). The gate does not cover a
full slot table, the end of a script for an engaged object, or the radio message `$d048` (it waits for an interrupt).

### The vehicles

Unit +6..+10 count Snow bulls, Tankers, Snow wolves, Snow cats and Snow foxes, in that order. The order comes from
the code, not from the picture: `$ca7e` gives an engaged object the shape `$316e4[kind]`, and `$316e4` is
`$31698 + 4 * $13`, inside the shape table that the identification screen (`$11982`) indexes by type. Its 14-byte
records at `$11ae2` (type word, then a name pointer at +10) name type `$13` Snow bull, `$14` Tanker, `$15` Snow wolf,
`$16` Snow cat and `$17` Snow fox; they also list `$12` Snow witch, `$1a` Spotter, `$1d` Bomber and the 15 building
types. No object was visible in the one 3D frame rendered (`d_ski` plus 120 frames), so which shape is drawn where on
screen is not matched.

A unit whose +5 bit 6 is clear also has a command vehicle of its own (30 of the 32 units). The situation report
names the counters (`situation_report.png`): MOBILE UNITS 32 is `$2bada`, MOBILE VEHICLES 4067 is `$2bade`, and the
player's ENEMY UNITS and ENEMY VEHICLES destroyed are `$2bad8` and `$2badc`. On `d_ski`, `$2bade` equals the unit
table's sum of +6..+10 (4037) plus the 30 command vehicles: **4067/4067**.

### The search `$c2f0`

Called from `$149b2` (entering the 3D view) and the re-centre `$152d0`. The window is `[2(t - 50), 2(t - 50) + 200)` on
each axis, `t` the terrain target `$19cd4/$19cd6` (unit coordinates are twice the terrain's). With no unit inside,
`$2baec` = -1 and nothing else changes. Otherwise the routine:

- copies the unit's position, its target node's position (-1 when stationary or choosing), and its five counts into
  working words `$2bb0a..$2bb12`, with two budgets: bulls plus tankers, and wolves plus cats plus foxes;
- clears the 41 object slots at `$2d47e`, except the one already engaged (`$2bae0`), and puts the command vehicle in
  slot 0;
- allows 38 objects in this encounter (`$d57c`; 39 when nothing is engaged);
- if the unit is moving, writes a route from the unit to its target node into `$2d70e` (`$c730`), one direction
  byte per step through the 100 x 100 blocked-cell grid `$3ddb4` (filled with the terrain, `terrain.md` section 4).
  Each step goes along x or along y with probability in proportion to the distance left on that axis. Headings
  cycle y-1, x+1, y+1, x-1. A blocked cell starts wall-following (advance the heading through the cycle until a cell
  is free, and on the next step try the previous heading first) until a step toward the target is free again. The
  route ends at the target or at the window's edge.

### Each frame: `$c4f2`

Called from the 3D frame (`$12a5e`) while the unit is active. Every fifth frame, while objects are still allowed, one
object is placed: `rand mod` the sum of the five working counts picks a kind in proportion to what is left, and that
count and its budget go down by one. A bull or tanker is placed only when the unit is moving. A bull drawn otherwise
places nothing, and a tanker drawn otherwise falls through to the wolf test. Bulls and tankers start at the unit and
follow the route one step a frame, starting again from the unit at its end: a convoy along the unit's road. Wolves,
cats and foxes start at the unit with a random heading and wander. Each frame each one advances its heading one place in the cycle with
chance 1 in 16 and steps unless the cell ahead is blocked or outside the window.

Slots are 16 bytes: +0 the route pointer (convoy) or the heading word (wanderer), -1 when free; +4/+6 x, y; +8 the
kind; +10 1 for a convoy, -1 for a wanderer; +12 -1 once engaged; +14 a latch the engagement test `$cb2e` uses.
`$ca7e` (from `$12a64`) engages the first slot within 32 units of the camera and builds the object `$1cdaa` from its
shape (read, not gated).

### Losses: `$cbbe` and `$cdd0`

`$cbbe` (from `$14220`) runs when the player destroys the engaged object:

- a vehicle: MOBILE VEHICLES down and ENEMY VEHICLES up by one; the unit's count of that kind down by one, so the
  next encounter with the unit has one fewer; one more object allowed; the unit's strength +14 down by 1, or 2 for a
  Snow cat or Snow fox. At 0 the unit is destroyed. A moving unit (36) dies after 36 bulls, tankers or wolves, or 18
  cats or foxes, or a mix; a stationary one (255) after 255 wolves or 128 cats or foxes.
- the command vehicle (slot 0): the unit is destroyed at once.

`$cdd0` destroys a unit: it is made inactive, its command vehicle and all its remaining vehicles are written off into
the counters, MOBILE UNITS goes down and ENEMY UNITS up, and +15 bit 7 marks it dead. The groups are in +15: units
0..5 hold their group number `g`, units 6..29 hold `8 + g` (four per leader: 6..9 under unit 0, ..., 26..29 under
unit 5), and units 30 and 31 hold `$ff`. Killing a leader destroys every unit of its group, including the stationary
garrisons 6, 10, 14, 18 and 22, and a member already dead is not counted twice (`$d57a`). Killing a member destroys
that unit alone. The radio message `$d048` then reports the losses.

Two oddities. The placement draws its count before it looks for a free slot, so with all 40 slots in use the drawn
vehicle is lost from the encounter (not seen: 38 objects at most). A draw with all five working counts at 0 divides
by zero in `$d57e`; the zero-divide vector is a bare `rte`, so the draw reads 0 and places nothing (read, not
driven).

## Open

- `$f374`, `$f3be` and the end-of-game tests `$118ba`/`$118f6` in the period end; the report's counts against their
  tables (`$ef8c`).
- Who reads unit +12.
- The non-spread branch and `$2bb2e` (no unit uses it on these snapshots).
- Relationships and recruitment: the bio's friend and enemy text is prose, so the data behind it is elsewhere.
- The encounter's objects on screen: match a frame with objects in view against the slots (needs the 3D pipeline),
  and gate the engagement `$ca7e`/`$cb2e` and the radio message `$d048`.
- What else attacks a site: the Bomber, Spotter and Snow witch types and the options' MORTARS/BOMBERS switches. Until
  then, whether a site off the road graph (Radio Station 76, Mountain Hut 59) is safe is not settled.
- Node names: `$35d0`/`$217a` name a position; map each node to its place name.

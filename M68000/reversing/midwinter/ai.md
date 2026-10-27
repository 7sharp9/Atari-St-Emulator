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
its whole group (section 3). The enemy's aircraft (Bomber, Spotter) and the encounter's missiles attack only the
player in the 3D view, never a site (section 4). The player fights back in two ways: by shooting the engaged
vehicle, the only way to destroy a unit (section 6), and by sabotage, which turns buildings into Ruins and so cuts
the enemy's supply and can win the game, but never takes a site back (section 7).

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
| +52 | the feature record of the site the character is at (`$f78e` sets it to the nearest site whose first building is not a Pylon; `$52b2` reads building types through it) | read from the code |
| +63, +64 | the type of the building the character is inside (negative: outside) and which building of the site it is | the seven characters in a Police Station of a held site are the report's PRISONERS 7 (section 5) |
| +60 | explosives (live copy `$2446c`, loaded by `$4f54`, stored by `$4ec4`); a Magazine fills it to 47, a Store adds 12 up to 47 (section 7) | driven |
| +65..+70 | rounds for the sniping rifle, the ski grenades, the glider's weapon, the driving gun, anti-aircraft weapon and rocket, loaded into `$25132..$25146` by `$3e38` and written back by `$3eae` (section 6) | gated |
| +72 | a byte that lowers the odds of air attacks on the character (section 4) and raises the engaged vehicle's odds and wait (section 6); at `$c8` or more the character may enter an enemy-held building (`$517a..$51d0`) and Decisions does not treat it as a prisoner in a held Police Station (`$d0e..$d30`) | name not found |

The period end `$ec8c` (section 2, "When it runs") walks the team list `$2b16c` (character numbers ending with a
negative byte). It takes `$24b7c` off each member's Morale (+1, floored at 0), the amount `$ed88` computes from the
enemy's gains: 2 per Factory, Synthesis Plant, Warehouse or Radio Station and 10 per Heat Mine it holds beyond the
last high mark (section 5). It then brings each member's clock up to the game clock, calling `$f854` for the minutes
skipped. On the driven turn Stark's clock went from 06:00 to 08:00 and his Morale stayed 228 (the amount was 0).

Relationships (the bio's "nearest friends", "hatred of") and recruitment are not located yet.

## 2. The enemy army

### Data

| where | what |
|---|---|
| `$2bb96` | 32 units of 16 bytes: +0/+2 x, y (words, in the same units as the node table); +4 bit 7 active, bits 0-6 the node it last reached; +5 bit 7 spread mode, bit 6 set once the unit has no command vehicle of its own, bits 0-5 an index the loss message uses (the unit number on units 0..29); +6..+10 its vehicles: Snow bulls, Tankers, Snow wolves, Snow cats, Snow foxes (section 3), +6 also the weight in the supply sums; +11 speed; +12 a second supply sum, which divides the engaged vehicle's odds (`$1faa6`, section 6); +13 the target node (0 = choose, negative = stationary); +14 strength (section 3); +15 its group (section 3) |
| `$25b4a` | node coordinates, (x.w, y.w) for 96 nodes; they equal the x, y words of feature record #n at `$2a150` on 93 of 95 nodes; the two that differ, 59 and 81, have no roads |
| `$25cca` | four road bytes per node, 0 = no road. Nodes 59, 60, 70, 76 and 81 have no roads |
| `$2bb36` | a state byte per node: bit 7 enemy held; bits 0-6 the road a unit last left it by (the trail) |
| `$2a150` | the feature list: a kind byte (bit 7 enemy held, bits 0-6 the building count n), a byte, x.w, y.w, then n words whose first byte holds the building: bits 0-4 the type, bit 5 used (a Store or Magazine emptied, a Garage's vehicle taken at `$3f50`, the second station of a cable-car pair), bit 6 a sabotage charge planted, bit 7 ENEMY HELD (named from the ENTER screen's refusal, `$26531`; only a site's key buildings carry it). `$14a8` returns record #node (1-based) |
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
  two more action-table entries whose screens are not identified (`tables/action_tables.txt` lists them under the
  rect lists `$2494e` and `$249be`, which are PLANT EXPLOSIVES' and ENTER's building cells, section 7). It runs the period end for the team
  (section 1), the supply update, the counts and end tests of section 5, then the SITUATION REPORT `$ef36`
  (`situation_report.png`: "Watches synchronized! Your team has two hours before the next situation report is due",
  and the counts of section 5). Dismissing the report runs nine ticks and
  +120 minutes (`$ed7a`), back to The Team. Driven from `d_team.snap` (game clock 08:00): the clock click gives
  `$ec8c` 1, `$f56e` 1, `$f5e2` 1, `$ef36` 1 and no tick; the report's icon (x 0, y 168) gives `$c136` 9 and
  `$2d74` 1; the game clock goes 480 to 600 and held nodes 33 to 39. So the army moves only when the player ends a
  period, not while a character travels.

Unopposed, the model alone takes the army from 33 held nodes to 80 by tick 80 (about 18 game hours, nine reports)
and 90 by tick 400. The five nodes it never takes are the ones with no roads: 60, 70 and 81 are Radio Stations (each
with a Mountain Hut) that `$ee88` marks enemy held at PLAY, which are the 3 Radio Stations of the report's enemy
column; 76 is a fourth Radio Station; 59 is a Mountain Hut. Nothing else captures a site, and nothing during
play releases one: the held bit has no writer outside the walk and the head start but an uncalled reset (section
4), so a site once taken stays taken. The player's counter-moves on the army are the encounters (sections 3 and 6)
and sabotage of its supply buildings (section 7).

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
- 165 natural frames from `d_ski.snap` (unit 27 in the window), up to the missile hit that ends the trip at frame 170 (section 4): **165/165**;
- every active unit put in the window by a poked target at three offsets: `$c2f0` **96/96**, and 100 chained frames
  after each, **9600/9600** (with the natural legs, 1926 objects placed); a window with no unit: **2/2**;
- the kill `$cbbe` for every unit, of its command vehicle and of one vehicle of each kind at strengths 1, 2 and 36,
  up to its radio message: **512/512** (48 leader kills, which take 192 group members with them).

Four broken models fall short: no random turn (92/9600 frames), tankers drawn before bulls (`$c2f0` 40/96, frames
9101/9600), every kind costing 1 strength (384/512), no group cascade (464/512). The gate does not cover a
full slot table or the end of a script for an engaged object; it stops each unit kill before the radio message
`$d048`, which waits for a key (section 6 drives it).

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
`$ca7e` (from `$12a64`, and only while `$2baec` holds a unit) decides which slot the player can fight. It converts the
camera to the 100 x 100 grid (`$1d074`) and scans slots 40 down to 0, skipping free and already-engaged (+12 set)
ones; `$cb2e` puts a slot inside when it lies in the 32 x 32 cells from 16 below the camera's cell on both axes. A
slot inside with its latch +14 clear sets the latch and asks to be engaged; a slot outside clears its latch. A
request when nothing is engaged (`$2bae0` negative) engages the slot: `$2bae0` = slot, `$2bae2` = unit, `$2bb22` =
kind, the object `$1cdaa` built from the shape `$316e4[kind]` and placed through `$1d048`, and +12 = -1. So the
highest-numbered slot to enter the box is the one engaged, each slot at most once, and a slot that entered while
another was engaged has to leave the box and come back. After an engagement D0 still holds kind * 4 instead of the
camera's x cell, so the lower slots of that scan are boxed against the wrong x, fall outside and lose their latches
(a bug). Gated, section 6.

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
that unit alone. The radio message `$d048` then reports the losses and polls the key byte `$2c324` at `$d0f4` until
a key arrives ("PRESS ANY KEY TO CONTINUE"). The game's own text calls a unit a squadron and its command vehicle's
crew its captain: killing unit 27's command vehicle gives "REUBENS'S SQUADRON DESTROYED !", "Captain Reubens has been
killed in action. The rest of the squadron has fled", initial strength 56 vehicles, losses 1, deserted 55
(`radio_kill.png`, section 6).

Two oddities. The placement draws its count before it looks for a free slot, so with all 40 slots in use the drawn
vehicle is lost from the encounter (not seen: 38 objects at most). A draw with all five working counts at 0 divides
by zero in `$d57e`; the zero-divide vector is a bare `rte`, so the draw reads 0 and places nothing (read, not
driven).

## 4. Attacks on the player, and who takes a site

Nothing but the army's walk takes a site. The enemy's aircraft and the encounter's vehicles attack the player in the 3D
view, never a site: a hit ends the trip. The five road-less sites are therefore safe from everything, and the three
of them `$ee88` marks at PLAY are the only ones the enemy holds without having walked there.

**Who changes a site's held bit.** Two censuses of the resident image `$800..$261a2`. Every instruction that sets or
clears bit 7 of a byte in memory (`bset`/`bclr`/`bchg #7`, `ori.b #$80`, `andi.b #$7f`, decoded at every even
address and kept on instruction boundaries of the `--all` listing) gives 24 hits; five touch the feature list, the
tick's arrival (`$c05c`, `$c1fc` in `$c136`) and the head start `$ee88` (`$ee92..$eeae`). The other 19 are the
character records (`$3b12`..`$4eec`: the trip end, below), the unit's +4/+15 (`$cdf8`, `$ce26`), sound flags
`$6a34`/`$6a35`, the 3D clipper's vertex marks (`$1e674..$1e9fc`) and one data word (`$12c52`). The ten literal
loads of `$2a150` cover every routine that walks the list: the record search `$1352` and `$14a8`, the map plot
`$24b6`, the counts `$f374`, the supply sums `$f656`/`$f6a8`, the nearest site `$f78e`, the map markers `$19b50` and
the 3D object list `$1cf1c` only read it; `$ef1c` clears bit 7 on every record through a register (`andi.b #$7f,D0`
/ `move.b D0,(A0)`) and has no caller in the image (no `bsr`/`jsr`, no literal, no displacement-table entry). The
node state bytes `$2bb36` are loaded as a base only by `$bfc8`, the new-game setup PLAY calls (`$1090e`), which
clears them, and by the tick. Neither census sees a write through a record pointer kept elsewhere (the character's
+52); the live check covers that for a ski run. From `d_ski.snap` until the trip ends, 170 frames with the bomber's script running every
frame and five calls of the missile launcher (two launches), the feature list `$2a150..$2b169` sees **0** writes.

**The attackers.** The 3D frame `$14e00` calls `$202c6`, `$200e8`, `$1ffe0` and `$1fa0a`, then `$20d52` runs four
44-byte objects through their script pointers (+40): `$1cd7e` the player's shot, `$1cdaa` the engaged vehicle,
`$1cdd6` the attacking aircraft, `$1ce02` a bomb, missile or mortar shell. Each aircraft and projectile gets its shape
from the table `$31698` by type, the same table the identification screen names (section 3):

| attacker | launched by | switch, mask bit | shape | what it does |
|---|---|---|---|---|
| Bomber (`$1d`) | `$1ffe0` | BOMBERS `$2c17c`, bit 0 | `$3170c` | appears `$4650` ahead of the camera on the player's heading and flies at a point ahead of the player (`$2040e`), dropping a bomb (`$1fd1e`) when its aim distance `$200e2` is 500 and that point is within 700 of it but not within 120 (read, not gated) |
| Spotter (`$1a`) | `$200e8` | MORTARS `$2c17e`, bit 1 | `$31700` | flies in the same way at a point 3000 ahead of the player (`$20524`); within 200 of that point it starts a barrage (`$2040c` = 1): `$202c6` puts five shells at random points around the player's path, one every four frames |
| missile (`$19`) | `$201e0`, from the engaged vehicle's script `$20ce2` | TRAINING `$2c180` off, bit 2 | `$316fc` | leaves the engaged vehicle along the vehicle's own heading (the aim direction `$1f6f8` computes is overwritten) and steers at a point ahead of the player that moves closer each time the missile reaches it (`$20594`) |

The options screen's six labels name the three words (`$10a7a..$10ab4` print MORTARS, BOMBERS, TRAINING over them, and
icons 3 to 5 of `$250d2` flip them, `$10986..$10996`); each has exactly one reader, the launcher above. `$1fa08` is
the vehicle's attack mask, written by each travel mode's setup routine. The icon puts the mode's vehicle record in
`$12d76`; `$12d0e` copies it to `$12d3a`, and `$12eae` calls the setup through the copy's `$12d62`:

| travel mode `$24482` | icon | record | setup | skill category (`$22fda`) | mask |
|---|---|---|---|---|---|
| 0 | `$3dd2` (Decisions, snipe) | `$12e28` | `$13eb4` | Sniping | 7 |
| 1 | `$3a4a` | `$12e62` | `$13c5c` | none (6) | 0 (inferred: the cable car) |
| 2 | `$3d86` (ski) | `$12d7a` | `$1314c` | Skiing | 7 |
| 3 | `$3b5a` | `$12dee` | `$136f8` | Gliding | 3: no missiles |
| 4, 5, 6 | `$3bc8`, `$3c22`, `$3c7c` | `$12db4` | `$1354e` | Driving | 7, left unchanged when `$14774` is negative (role not read) |

The category is the travel mode's `138(A6)`; `$22fda` maps it to a character byte (Sniping +13, Skiing +10, Gliding
+11, Driving +12), whose rating `$4d24` turns into the setup's performance word.

**When an aircraft comes.** Bomber and Spotter share the object `$1cdd6`, so one is in the air at a time. Each frame
the object is free, its launcher draws: with odds n at -1 it first draws new odds with `$20db4`, then launches when
`rand mod n` is 0, and sets n back to -1. So a launch comes on average n frames after the aircraft is free, and n is

```
q = ((2 * (dx^2 + dy^2)) >> 16) * (c[+72] + 50) / v[$12d72]      dx, dy = terrain target - (2688, 2616)
n = rand mod (q + 50) + q / 8 + 20                                   (n = $7d00 if that is negative as a word)
```

with `c[+72]` a byte of the current character's record (Stark 10; 255 for characters 21, 22 and 31; not named) and
`$12d72` a word of the vehicle record (30 on skis). The further from (2688, 2616), the rarer the attacks, and the
higher the character's +72, the rarer too. (2688, 2616) is the Enemy Headquarters' position (feature record 88)
taken in map units, while the terrain target is in half those units (section 3), so the point the code measures from
is off the 1600-cell island, beyond its far corner in x and y; the nearest the player gets is that corner, close to
the headquarters (terrain (1344, 1308)). Inferred: a units slip that keeps "nearer the headquarters, more attacks" in
direction only.

**Hits.** A bomb falls faster each frame (+12 per frame on `$20a50`); on landing (`$209a0`) it hits when it is
within 200 of the point 180 ahead of the camera on both axes. A mortar shell (`$20776`) lands at once and hits within
200 of the camera. A missile (`$20594`) runs out when its range word `$200e2` goes negative and then hits within 90 of
its aim point, and when `$13f28` is set only 1 time in 5 (read, not gated). A hit sets `$14dfc`, which the 3D loop
`$14ac0` tests: the trip ends, and the travel return (`$3b12`, `$4ede`) sets bit 7 of the character's record byte
+0 (meaning not read). When the engaged vehicle fires its missile is section 6.

The unsteered skier of `d_ski.snap` does not crash: at frame 170 a missile from the engaged vehicle hits
(`$14dfc` written by `$2061a`), and the game returns to Decisions with Stark's clock at 06:08 (`ski_crash.png`).

Proof: `py/attack/gate_attack.py` (also `tools/gates.py run midwinter`, about 15 s) runs the routines in `stserver`
and checks `py/attack/attack_model.py` against every call: launches with every switch, mask, object state, odds and
four seeds, `$1ffe0` **768/768** and `$200e8` **768/768**; the odds `$20db4` over 121 positions, four characters and
three divisors, 51 of them overflowing the `divu`, **1452/1452**; the missile `$201e0` poked **128/128** and the
game's own five calls (two launches) **5/5**; the bomb's landing and fall `$209a0` **1494/1494** (484 hits); the shell `$20776`
**361/361** (121 hits); and the natural run above (0 feature-list writes, the trip ended by `$2061a`). Five broken
models fail: launches that ignore the mask (704/768 each), odds without the character's +72 (0/1452), a missile aimed
at the player (112/128, natural 3/5), a hit radius of 180 (bomb 1110/1494, shell 265/361) and a shell aimed 180 ahead
like the bomb (0/361).

## 5. The period end's counts, the report and the endings

At each period end (`$ec8c`, section 2) the game recounts the island and tests for the end of the game, in this order:
the Morale loss `$ed88`, the supply update, the counts `$f374` and `$f3be`, then `$118ba` and, unless the game is
over, `$118f6` and `$f8d8`, then the report `$ef36`.

- **Counts** (`$f374`). Two tables of 20 bytes count the buildings of every site by type: `$24ba4` over the sites the
  enemy does not hold, `$24bb8` over those it holds. A blown-up building is a Ruin (type `$10`) and drops out of its
  type's count.
- **Prisoners** (`$f3be`). A character inside a Police Station (+63 not negative, the building +64 of the site +52
  of type 8) of a site the enemy holds is a prisoner; `$24be6` counts them.
- **Morale loss** (`$ed88`). The held Factories, Synthesis Plants, Warehouses and Radio Stations are summed; a rise
  above the mark `$2c184` costs 2 Morale per building and raises the mark, a fall only lowers the mark. Held Heat
  Mines do the same against `$2c182` at 10 each. It runs before the counts and nothing else calls `$f374`, so it
  reads the counts of the previous period end: a gain costs Morale one period late. The amount `$24b7c` comes off
  every team member (section 1).
- **Endings** (`$118ba`, `$118f6`). The game is over (`$24e8e`) when the Headquarters has been blown up (`$24e8c`,
  set by the sabotage code at `$4234` when the destroyed building is type `$f`): "The enemy HQ has been destroyed and
  General Masters with it!"; or when the game clock reaches `$7080` minutes (20 days): "General Masters' troops are
  tired of fighting and have deserted him!". Otherwise, when no Heat Mine is left outside the enemy's hands,
  `$24e90` is set: "The Free Villages have no heat mines left and have surrendered to General Masters!". The
  Headquarters ending is driven (section 7): dismissing the report shows the win screen `$115ae`, and a key there
  still runs the period's nine ticks before `$2e6e` returns to Game Options. That the 20-day ending is also a win and
  the surrender the loss is inferred from the text; the surrender screen `$1137a` (it sets `$24e90` itself and is the
  action of icon 0 of `$117b6`) is not driven.
- **Radio** (`$f8d8`). Once, when the enemy holds no Radio Station, `$2c186` goes from 0 to 1, every character
  joins the team (the team list `$2b16c` becomes 0..31) and every character's clock is set to the game clock; the
  report then draws the Radio Stations line in another colour, prints "Radio communications restored - You now have a full team !" and sets
  `$2c186` to -1 (`$f25e`, `$f2cc`). Since no site is ever released (section 4), the enemy's Radio Stations can only
  go by sabotage. This is the game's general recruitment: the three Radio Stations held at PLAY sit at sites with no
  roads (section 2), so the player must reach and blow up each one. Driven with the game's own blast on all three
  (section 7): the next period end gives the full team and the message (`rad_report.png`), against a control with
  the same clicks that keeps the team at Stark alone.

**The report** (`$ef8c`) writes the numbers into its text lines: in the FVPF column, HEATMINES is the free Heat
Mines (`$24ba4` + 10) and DESTROYED Factories, Synth Plants, Warehouses and Radio Stations are `$2c188` by type
(the sabotage code counts each blast there), with ENEMY UNITS and ENEMY VEHICLES destroyed (`$2bad8`, `$2badc`); in
the ENEMY column, PRISONERS `$24be6`, then HELD Factories, Synth Plants, Warehouses and Radio Stations (`$24bb8` +
13, 12, 11, 14) and the mobile units and vehicles (`$2bada`, `$2bade`). The 14 numbers of `situation_report.png`
(17; 0, 0, 0, 0, 0, 0; 7; 9, 8, 5, 3, 32, 4067) equal these tables after the driven period end: **14/14**.

Proof: `py/army/gate_period.py` (also `tools/gates.py run midwinter`, about 7 s) clicks The Team's clock on
`d_team.snap` in the REPL, then in `stserver` checks `py/army/period_model.py` against the game's own call of each
of the six routines (**6/6**) and against each routine on 200 poked states (sites' held bits flipped, buildings
turned to Ruins, characters moved into random buildings, the marks, clock and flags set, every held Radio Station
or every Heat Mine's site taken in some): **200/200** each, with every branch taken (the 20-day ending 77 times,
the Headquarters 74, the surrender 34, the radio 40). Three broken models fail: the weights 2 and 10 swapped
(57/200), prisoners at any site (13/200, natural 5/6), the 20-day test as `>` (171/200).

## 6. The player's weapons and the kill

The player can destroy only the engaged vehicle (section 3), and only by hitting it with a weapon of the current
travel mode. Each mode's frame code reads the key through `$12ac6` (scancode `$2c324` to ASCII `$12afc` through the
table `$24846`: Space `$39` is `$20`, `S` `$1f` is `'S'`) and the mouse buttons from `$24fba`:

| mode (frame code) | input | launcher | rounds (record) | shot: script; launch heading; speed; height |
|---|---|---|---|---|
| ski `$131ae` | Space (`$1321e`) | `$1fc6e` | `$25136` (+66) | `$208d6`; heading + `$100`; player's speed + 300; 40 |
| sniping `$13f34` | Space (`$13f7c`) | none: a screen pick | `$25132` (+65) | sets `$14136`; the next frame's pick goes to `$14150` |
| driving `$1359a` | Space | `$1fbbe` | `$25146` (+70) | `$207c4`; + `$100`; + 400; 0 |
| driving | `$24fba` bit 0 | `$1fe56` | `$25142` (+69) | `$20b0a`, aircraft only (read, not gated) |
| driving | bit 1, when bit 0 is clear | `$1fd96` | `$2513e` (+68) | `$20a52`; heading - `$100`; + 200; 20 |
| gliding `$13790` | bit 1 | `$1ff16` | `$2513a` (+67, set to 25 at `$3b76`) | `$20be6` (read, not gated) |

Which mouse button each bit is follows from the IKBD packet layout (inferred). The ski weapon's HUD icon (sprite
`$49`, drawn by `$b7a6`, one per 5 rounds and at most 4) is a hand grenade; the name is from the picture. Stark starts
with 50 sniping and 20 ski rounds and nothing else. Every launcher works the same way: with a round left it clears
the engaged vehicle's fire wait `$1fba0`, even when the shot object is busy; when the shot object `$1cd7e` is free
(+38 negative) it spends the round and places the shot 50 to the side of the camera (radius 200 through `$145b4`).
The shot moves along its heading at speed / 4 a frame.

**Hits.** Each shot script steers toward the engaged vehicle `$1cdaa` while that object's state is not negative, and
tests a box on both axes (`$1f884`, radius in `$1f8bc`):

- the grenade `$208d6` loses 4 height a frame and lands without a hit when the height is exactly 0, so it lives 10
  frames, about 750 units; it steers within 1000 (`$1f808` = 8) and kills within 150;
- the gun shot `$20a52` is freed at 5000 or more from the camera (`$1f71a`), gains 200 speed a frame up to `$640`,
  and within 800 drops to speed 500 and steers at rate `$40`; it kills within 75;
- the rocket `$207c4` is freed at 5000, loses 100 speed a frame down to 450, steers at rate `$10` within 2000 and then
  takes a second step that frame (`$20866`); it kills within 100.

The steering (`$1f756`, rotation `$1f6dc`) snaps onto the aim when the aim is ahead and the sine of the angle left is
below the rate's, and otherwise turns by the rate. A kill sets the flag `$14138` and the shot's state to 0. Sniping
has no projectile: the renderer stores in `$14134` the +0 id of the drawn object whose span straddles the crosshair
column `$17218` (`$19ec4`, read, not gated), and `$14150` acts on it: -2 (the engaged vehicle) sets the kill flag, -3
or -4 zero the aircraft's or the projectile's state, each with the explosion `$1fba4`/`$20728`. The glider's script
`$20be6` zeroes its target's state directly and never sets `$14138`, so a glider hit would not reach `$cbbe` (read,
not gated). `$131c6` tests `$1353c`, whose only other reference in `$800..$261a2` is the clear at `$13210` (inferred
dead).

**The kill.** `$141ce` (called by `$13244` on skis, `$13638` driving, `$14108` sniping) tumbles the vehicle while the
kill flag is set: +18 += `$40` and +20 += `$80` a frame. On the call that finds +18 exactly `$200` it frees the object
(+38 = -1), clears the flag, calls `$cbbe` (`$14220`, its only caller; section 3), sets `$2bae0` = -1 and `$6368` =
`$6ed2`. A +18 that is not a multiple of `$40` never reaches `$200`.

**The engaged vehicle fires back.** On each new engagement `$1fa0a` calls `$1faa6`, with c the character's +72:

```
q    = $12d6c / (unit[+12] + 1)                      (a divu overflow leaves the dividend)
n    = ((((rand mod q) + c) >> 1) + $12d6e + c) >> 2   -> $1fb9e
wait = ($12d70 * c + 100) >> 2                         -> $1fba0
```

then by kind: the command vehicle n = 5 and wait = 30; a bull or tanker n + 10000; a wolf + 5, a cat + 10, a fox +
15; and 1 time in 11 the wait becomes 10. `$20cfe` (the tail of the vehicle's script `$20ce2`) counts the wait down
and then fires the missile `$201e0` (section 4) when `rand mod n` is 0. Since every launch of the player's clears the
wait, firing invites an immediate reply. A unit whose +12 supply sum falls (section 7) gets a larger q and so, on
average, larger odds n: it fires less often (follows from the two gated rules, not driven).

Proof: `py/attack/gate_shot.py` (also `tools/gates.py run midwinter`, about 10 s) pokes `d_ski.snap`'s state and
checks `py/attack/shot_model.py` against one call of the game's routine each: the engagement `$ca7e` **400/400**; the
five launchers **36/36** each (rounds 0, 1 and 20, the shot object free, done or running); the three shot scripts
**798/798** each, at offsets straddling 75, 100, 150, 800, 1000, 2000 and 5000 on both axes, speeds straddling `$1c2`
and `$640`, grenade heights 2 and 6; the tumble `$141ce` **48/48**; the sniping pick **21/21**; the explosion **9/9**;
the odds `$1faa6` **300/300** (107 overflowing); the vehicle's fire `$20cfe` **144/144**. Nine broken models fail:
the engagement without the D0 clobber (157/400) or with a 33-cell box (251/400), a grenade radius of 160 (703/798), a
launch that ignores the rounds (24/36) or keeps the fire wait (12/36), a grenade landing at height <= 0 (655/798), no
steering snap (794, 765 and 790 of 798), a tumble ending at >= `$200` (39/48), and odds that give the command vehicle no fixed n and wait
(254/300).

`py/attack/drive_kill.py` drives a kill. Two arms from `d_ski.snap`, each with the same labelled pokes (the engaged
vehicle moved 300 straight ahead of the camera, TRAINING on so no missile ends the trip) and a 40-frame budget; the
fire arm presses Space at frame 2. Fire arm: the game's own calls match the model (launch 1/1, shot 6/6, tumble
17/17), `$cbbe` and `$cdd0` run once, the command vehicle's loss destroys unit 27 (ENEMY UNITS 0 to 1, MOBILE UNITS
32 to 31, ENEMY VEHICLES 0 to 56, MOBILE VEHICLES 4067 to 4011) and the run stops at the radio message's key wait
after 18 frames. Control: 40 frames, no call of `$cbbe`, every counter unchanged. `py/attack/radio_after_kill.py`
renders the message (`radio_kill.png`) and, after a key, the ski view again with 19 rounds left.

## 7. Sabotage

**Where it is offered.** Decisions builds its icon list on every visit: `$ca8` runs 17 tests and `$de2` appends icon
`$245fe[k]` and action `$24284[k]` to the live table `$24238`. It offers nothing when the character's clock +32 has
reached the game clock (`$cf6..$d00`), the condition byte +15 is 0 (`$d08`), or the character sits in a Police
Station of a held site with +72 below `$c8` (`$d0e..$d30`). Three of the actions matter here:

- k = 9, ENTER `$5062`: choose a building of the site; 1 minute, sets +63/+64. A held site's building with bit 7
  (ENEMY HELD) refuses a character whose +72 is below `$c8` (`$517a..$51d0`, "ENEMY HELD" `$26531`).
- k = 4, resupply `$563a`, offered inside a Magazine or inside a Store whose bit 5 is clear (`$10ca`): a Magazine sets
  the explosives +60 to 47, a Store adds 12 up to 47 and sets its bit 5; 5 minutes. It also sets +65 = 50 and +66 =
  20, the sniping and ski rounds.
- k = 1, sabotage `$3f98`, offered (`$fe4`) when the character is fit enough (bit 1 of 264(A6) and one of bits 2/3
  and one of bits 4/5, each set by `$1296` when its body-part byte +16..+21 is at least 84), stands at a site (+52)
  whose first building is not a Pylon (`$100e`), and carries explosives. It need not be inside a building.

**PLANT EXPLOSIVES** `$3f98` shows the site's buildings in ten cells and a plunger (rect list `$2494e`, the plunger
at (256,53)-(292,111); the building count `$24470` is the site's kind & `$f`); its one icon is the back icon `$482e`.
On entry `$44fc` works out the charges each type needs from the Sabotage skill +14 (category 0 of `$22fda`, through
`$4d6e`/`$4dee` into 136(A6)):

```
charges[t] = weight[t] / (perf + 70) + 1          weight $2490a, minutes $248c6
```

| type | Hut | Cable | Pylon | Garage | Bunker | House | Church | Store | Police | Magazine | Heat Mine | Warehouse | Synth | Factory | Radio | HQ | Ruin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| weight | 0 | 400 | 0 | 50 | 300 | 100 | 300 | 100 | 250 | 0 | 500 | 300 | 200 | 400 | 200 | 400 | 0 |
| minutes | 15 | 60 | 15 | 15 | 30 | 15 | 45 | 15 | 30 | 15 | 120 | 75 | 60 | 90 | 45 | 120 | 15 |

Stark's performance is 61, so a Warehouse costs him 3 charges. A click on a cell (`$404e..$40cc`) flips the
building's bit 6: planting adds one to `$24468`, the minutes to the clock `$2446a` and takes the charges from the
explosives, undoing the plant at once (`$40a8`) if that leaves them negative (exactly 0 is allowed); removing refunds
both. Any building can be planted, a Heat Mine, Hut, Pylon or Ruin included. The back icon `$482e` takes every
planted charge back, refunding charges and minutes. The "REMOVE EXPLOSIVES." title (`$4808`/`$481a`, `$26550`) and its
flag `$24466` are unused: no caller in a raw scan of the image and no reader of the flag.

**The blast.** The plunger `$4106` (with `$24468` above 0) blows every planted building at once; there is no timer.
For each, `$41f6..$4272`:

1. Morale `$2553c` += 5, + 5 more at a held site, + 5 more for a Warehouse, Synthesis Plant, Factory or Radio Station
   (`$4340`), capped at (Optimism + 500) / 3 (`$5816`);
2. `$2c188[type]` += 1, the report's DESTROYED counts;
3. the Headquarters sets `$24e8c` = -1 (`$4234`), the win at the next period end (section 5);
4. a Cable Car Station also ruins its pair (`(b & $20) | $10`): the next 8-byte record, or the previous one when bit 5
   marks it the second of the pair (cable-car records come in pairs, nodes 273..300);
5. the building byte becomes `(b & $60) | $10`: a Ruin, ENEMY HELD dropped.

Then `$437a` redraws it, `$42be` clears bit 6, and `$42d4` stores the character back. The blast touches no kind byte,
no unit `$2bb96`, no node state `$2bb36` and not the random seed `$d5d8`: sabotage never changes a site's owner and
never harms a unit.

**What it changes.** The supply sums (section 2) list held sites by their Warehouse or Synthesis Plant (`$f656`) and
Warehouse or Factory (`$f6a8`), so a Ruin drops out: from the next period end, ruining a held site's last Warehouse
or Synthesis Plant lowers every unit's speed +11, and its last Warehouse or Factory lowers +12 (section 6). Ruining a
free site's buildings changes neither. The counts `$f374` move the building to the Ruin column, so a held Radio
Station ruined counts toward the radio reward and the HQ toward the win (section 5). Inferred, not driven: a free Heat
Mine ruined is one fewer for the surrender test `$118f6`; a ruined Cable Car Station no longer passes `$fc6`'s
cable-car icon test (+63 = 1), at either end of the pair.

Proof, driven through the REPL with a same-snapshot, same-budget control for every leg
(`py/sabotage/drive_sabotage.sh`, about 15 minutes, writes `scratchpad/midwinter/sabotage/`):

- **Node 74 (Little Plains), natural from `d_decisions.snap`:** ENTER the Store, resupply (explosives 0 to 12, the
  Store `$07` to `$27`), sabotage, plant the Church and the House, plunger. The Church `$46ae` and House `$455f`
  become `$10ae` and `$105f`, `$2c188` +5 and +6 become 1, the clock goes 366 to 426, the explosives 12 to 8 (Morale
  stays 228, at its cap). The control (no plants) changes nothing, and a diff of the data range finds only those
  bytes, Stark's +32/+60 and their live copies: units, node states and the seed are identical.
- **Node 48 (Otter Valley), a held Warehouse,** after a labelled poke of Stark's position, +52 and 47 explosives on
  `d_stark.snap`: the Warehouse `$8b76` becomes `$1076`; then The Team's clock. At the report all 32 units are slower
  (+11 lower by 1 to 14) and +12 is lower by 0 to 8; after the nine ticks 17 of 32 units stand elsewhere, both arms
  holding the same 39 nodes; the report reads DESTROYED WAREHOUSES 1, HELD WAREHOUSES 4 against the control's 5.
- **Node 88, the Headquarters,** the same pokes: `$24e8c` = -1, the report's "The enemy HQ has been destroyed and
  General Masters with it!", the win screen `$115ae` (`hq_win.png`), then Game Options.
- **The three held Radio Stations** (nodes 60, 70, 81), blown up by the game's own blast and clear in `stserver`
  (`py/sabotage/radio_setup.py`, then a REPL period end): `$2c186` = -1, the team 0..31, DESTROYED RADIO STATIONS 3,
  HELD 0 and the full-team message (`rad_report.png`); the control from `d_team.snap` keeps the team at Stark.

`py/sabotage/gate_sabotage.py` (also `tools/gates.py run midwinter`, about 20 s, on the driven snapshots) checks
`py/sabotage/sabotage_model.py` and `army_model.supply` against the game's routines: the natural toggles **3/3**,
blasts **4/4**, clears **4/4**, cancel **1/1** and untouched units and nodes **4/4**; poked, the charges `$4516`
**400/400**, clicks `$404e` **1500/1500**, the blast **100/100** for each of the 17 types, the clear **1700/1700**,
units, nodes and kind bytes untouched **1700/1700**, cancels **300/300**, and the supply update after blowing up each
Warehouse, Synthesis Plant and Factory at held and free sites **110/110**. Eight broken models fail: no cable-car
pair (0/100), a Ruin keeping ENEMY HELD (2/4, 902/1700), no held-site Morale bonus (1312/1700), no Morale cap (0/4,
867/1700), explosives at exactly 0 counted short (1223/1500), charges without the + 1 (0/400), a cancel that refunds
no minutes (0/1, 123/300), and a Ruin still counted as supply (56/110).

## Open

- The non-spread branch and `$2bb2e` (no unit uses it on these snapshots).
- Relationships and recruitment: the bio's friend and enemy text is prose, so the data behind it is elsewhere.
- The encounter's objects on screen: match a frame with objects in view against the slots (needs the 3D pipeline).
- The attacks' loose ends (section 4): the name of the character byte +72, the missile's 1-in-5 flag `$13f28`, the
  driving setup's `$14774`, record byte +0 bit 7 after a hit, and the Bomber's drop and the missile's detonation
  (read, not gated).
- The player's weapons (section 6): the anti-aircraft and glider scripts `$20b0a`/`$20be6` and the glider hit that
  never reaches `$cbbe`; the renderer's pick `$19ec4` and a driven sniping kill (`S` at speed 0, `$131d8`, then
  Space); `$1fa0a`'s object setup, `$1f8be` and the vehicle's re-aim `$1f852`; a driven kill of an ordinary vehicle,
  and one with no position poke (on `d_ski.snap` the vehicle stays about 5700 away); the names of the projectile
  shapes `$18`, `$19`, `$1b`.
- Sabotage (section 7): the surrender screen `$1137a` and The Team's `$11712` path; a ruined cable car's travel
  (`$fc6`) and a free Heat Mine ruined hastening the surrender (both inferred); the blast animation `$4498`; a
  whole-image census of the exits that could leave bit 6 set, of the other readers of bit 7, and of Ruin writers
  (the `ori.b #$10` scan used the `--all` listing, which loses sync).
- `morale_to_cap` `$57fe`, called on entering a Church (`$5208`; read, not driven).
- Node names: `$35d0`/`$217a` name a position; map each node to its place name.

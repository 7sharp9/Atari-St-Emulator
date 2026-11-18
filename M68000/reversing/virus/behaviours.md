# virus: the actor pool, its behaviours, and how waves scale

The question: what are the records in the pool `$31d54` that the flight, the particle gate and the autopilot all see,
what does each behaviour pointer at record `+16` do, what decides when a wave ends and how a later wave is harder, and
is there any state that makes the attract-mode pilot better from one game to the next.

**Answer, as far as the evidence goes.** The pool `$31d54` is not a particle pool: it holds every enemy of the wave
(and the player's rockets). Each wave starts by appending a fixed list of waiting records from a 16-entry table at
`$20e34`; each waiting record counts its life word down to zero and then switches to its live behaviour. There are seven
spawned enemy kinds, two derived ones and the player's rocket: 23 distinct behaviour pointers, every one stored by one of
three kinds of writer (below). A wave ends when every record left in the pool is an unhatched chaser (`$21ae2`), that is when the player has
destroyed everything else, not on a timer. Later waves have more of the dangerous kinds, hatch their chasers sooner and
raise the gravity word. Nothing in this code reads the demo flag `$62a5f` except the input selector and three
human-only steps after a game over, and the six RAM blocks that stepped up over 24 attract games are stale records in
the depth-bucket draw lists, which no code reads past the current list end: filling them with zeros or `$ff` leaves a
game identical on 500 of 500 samples. So the demo does not learn; the wave it reaches measures how fast that game's
pilot happened to kill the wave.

Evidence labels as in `demo.md`: **gated** (a command with a count and a control), **census** (a `hits` count from one
unpoked run: it shows that an entry runs and how often, not what it does), **read** (from the listing only). Listings
are `scratchpad/overseer/aha/code.lst` (`tools/disassemble.py --snap <snap> --all c000 28000`, a linear sweep); the
negatives below also use a raw scan of every aligned long in RAM. Scripts are in `py/scan/` (table at the end). The
runs start from the 24-game chain's game starts `main_gNNN.snap` (`main_g001` is the first game, `$62a5f = $ff`; paths at the end).

## Two pools

| pool | base | record | count, end pointer | append | walker | contents |
|---|---|---|---|---|---|---|
| actors | `$31d54` | 20 bytes: x, y, z, vx, vy, vz, life, pad (words), behaviour (long) | `$32a3e` (max 128), `$27082` | `$21722` (D0..D2 pos, A0..A2 vel, A3 life word, A4 behaviour) | `$2157c` | enemies and player rockets |
| objects | `$302f6` | 18 bytes: life, then position, velocity and a handler | `$32a3c` (max `$177`), `$2707e` | `$1fd14` | `$1fa72` | shots, debris, falling infection, bombs, score pop-ups |

Read: the append routines and walkers are named from their bodies (`$1fa72` loads `$302f6` and compares its index with
`$32a3c`; `$1fd14` refuses at 375 records). The README's seeder gate follows wave 0's three seeders (below).

The actor walker `$2157c` loads a record into D0..D6, reads the ground height under it (D7, `$24754`), or-s `$a000` into
the life word when the ground is at or above y, and `jmp`s to the behaviour. Bit 15 of the life word is "hit", bit 13
"hit the ground"; a behaviour that sees bit 15 takes its kill path. Most behaviours end at the common tail `$215ea`: if the
record is inside the view box and within `$c0` of the ship point (the words at `$270bc`) on all three axes and the ship is
not already crashing (`$62a5e`), it flags the record and sets `$62a5d` (the ship is hit); then it appends a draw record to the depth bucket. The kill path `$216d6` adds the
award in A0 to the score through the pop-up `$20798` (which formats the number and spawns a floating score object; the
award is not scaled), runs the explosion `$202a4` and removes the record by copying the last one into its slot. `$216e8`
is the same without the award (the rocket).

## Who writes `+16` (whole image)

A raw scan of the code region for `move.l #imm,16(An)` (opcode `$217c | An << 9`, displacement `$0010`) finds one site,
and the listing has no other store to `16(An)` in game code (`move.w D3,16(A1)` at `$1f6c8` is the matrix builder). So
the behaviour pointer is written by exactly three kinds of code (read):

1. `$21722` (`Pool_Append`) stores A4. Its three callers: the wave start `$20f18` (A4 from the wave table), the
   mothership `$22722` (A4 = `$2279a`) and the rocket launch `$25368` (A4 = `$228de`).
2. A behaviour replaces its own pointer with `lea <next>,A3 / move.l A3,-4(A6)` (A6 is the record's end): 16 sites,
   `$2178a` to `$226a0`. A raw scan of the code region for `move.l <Dn/An/#imm>,-4(A6)` finds the same 16 and no other (the
   listing is a linear sweep and misaligns in places, `$2529a` among them, so the raw scan is the negative); the listing's
   one other `-4(A6)` store, `and.w D0,-4(A6)` at `$21550`, is a word in another routine (`$2153c`, not a pool walk).
3. `$20206` (`move.l #$21f00,16(A0)`) in `$201b4` (below).

## The behaviour table

Every pointer value the three writers can store, grouped by enemy kind, with the record's life word use, the kill
award (A0 at the entry, in points) and the census from game 1 of the chain (`py/scan/census.sh`: one `hits` run of 600M
steps from `main_g001`, which covers game 1 to its game over and the start of game 2; 42 awarded kills at `$216d6`).
Named from the bodies (read); the census column only shows that the entry runs.

| entry | name | body | award | census |
|---|---|---|---|---|
| `$21776` | `Seeder_Wait` | counts the life word down (bit 15 cleared each tick: cannot be hit), then `$21792` | | 615 |
| `$21792` | `Seeder_Fly` | pos += vel; a spring toward 640 (`$280`) above the ground with vy drag 1/16, clamp ±`$60`; every fourth tick a distance sound within `$2300` of the ship; over land every tick `$20702` (drop infection); when its life is 0 and the ground word is at most `$320`, `$21894` | 100 | 18,763 |
| `$21894` | `Seeder_Descend` | drag 1/16 on vx and vz, no spring; at `$86` above the ground it snaps y to the sum-of-sines height minus `$86`, vy 0, life `$200`, `$21976` | 100 | 548 |
| `$21976` | `Seeder_Landed` | life countdown; every tick `$20702` from `$5c` above the record (A1 = `-$40`); at 0: life `$64`, vy `-$10`, `$219de` | 50 | 3,444 |
| `$219de` | `Seeder_TakeOff` | rises; at `$1c0` above the ground, random vx and vz (an RNG byte halved) and back to `$21792` | 100 | 121 |
| `$21ae2` | `Chaser_Wait` | life countdown, cannot be hit; then life `$1ff`, `$21afe` | | 20,349 |
| `$21afe` | `Chaser` | every `$1ff` ticks reverses its velocity; pushed up below `$100` above the ground; velocity += (ship - pos) >> 7, drag 1/64, clamp ±`$80`; every other tick a sound within `$3c00` and a debris spark (`$204d4`) within `$2300` | 400 | 1,949 |
| `$21c42` | `Patrol_Wait` | life countdown; then life byte `$40` with bit 14 set ("provokable", below), `$21c64` | | 2,814 |
| `$21c64` | `Patrol_Cruise` | within `$2800` of the ship: `$21df6`; otherwise moves in x and z only, kept at least `$400` above the ground, not drawn and not collided (it returns past the common tail); after `$40` ticks `$21d08` | 300 | 2,221 |
| `$21d08` | `Patrol_HomeOnQueue` | gravity and drag 1/32; every fourth tick steers (`$22c1e`) toward entry 0 of the infection queue `$27134` and, within `$a00` of it, fires (`$22e38`); other ticks hold the turn (`$22d04`); thrust (`$22d5e`) unless the steer bit 11 is set, and again within `$300` of the ground; after 64 ticks back to `$21c64`, which then cruises 5 ticks before homing again | 300 | 15,232 |
| `$21df6` | `Patrol_AttackShip` | as `$21d08` with the ship as the target; fires every fourth tick within `$900`; beyond `$2300` of the ship back to `$21c64` | 300 | 1,263 |
| `$21f00` | `Pursuer` | steers at the ship every tick, thrust (double near the ground), velocity += (ship - pos) >> 13, or >> 9 within `$1900`; fires every other tick within `$900`; drawn flashing | 500 | 3,880 |
| `$2200c` | `Pursuer2_Wait` | life countdown, then `$2202c` | | 1,034 |
| `$2202c` | `Pursuer2` | as `$21f00` but fires every tick within `$900`; on a hit: if it hit the ground (bit 13) it dies for 900, else 200 points now and `$221ac` | 900 | 3,760 |
| `$22164` | (first-hit path of `$2202c`, a branch target, not a stored pointer) | award 200, sound 3, stun count 5, `$221ac` | | 4 |
| `$221ac` | `Pursuer2_Damaged` | for 5 ticks drifts under gravity and drag and ignores hits; then pursues as `$2202c` (pull >> 10 within `$1900`); the next hit kills it | 700 | 596 |
| `$222dc` | `Bomber_Wait` | life countdown, then a random heading byte, `$22316` | | 544 |
| `$22316` | `Bomber` | flies its heading at the matrix row's speed, a spring toward `$700` above the ground; within `$2d00` of the ship a sound and a bomb (`$2086a`) every 8th tick within `$a00` or every 16th tick over land; farther away, on 15 of every 16 ticks over land, 21 infection plants at once (`$2010a`) | 800 | 6,938 |
| `$22486` | `Attractor_Wait` | life countdown, then 5 hits to kill, `$224a6` | | 101 |
| `$224a6` | `Attractor` | the seeder's spring (`$280` above the ground); within `$b00` of the ship it pulls the ship's velocity toward itself by >> 6 (`$22ebe` with the ship as A3); within `$700`, unless the ship is crashing, a beam draw record (`$22a64`) and fuel `$32a2e` minus 25 a tick, empty fuel sets `$62a5d`; each hit costs one of 5, a ground hit kills | 1000 | 2,686 |
| `$22688` | `Mothership_Wait` | life countdown, then count `$1e`, y `$f101`, `$226ac` | | 0 |
| `$226ac` | `Mothership` | moves in x and z only at its fixed height; within `$b00` of the ship, every 32nd tick while its count is at least 10, launches a `$2279a` and decrements the count; each hit decrements it too; at 0 it dies | 2000 | 0 |
| `$2279a` | `Mothership_Chaser` | the chaser's body with clamp ±`$70`, reversal every `$a9` ticks | 150 | 0 |
| `$228de` | `Rocket` | the player's rocket: counts down its life byte; steers at the record `$2709e` (`$22ee2`), clamp ±`$a0`; within `$240` of it sets the target's bits 15 and 13 (a ground hit, which kills a multi-hit enemy at once) and explodes with no award | | 0 |
| `$21f00` from `$20206` | (see `$201b4`) | | | 8 writes |

The waiting records are appended with y = `$f100` (the autopilot's `$2529a` skips those) and with velocity
`(random >> D7, 0, random >> D7)`; a waiting behaviour writes only its life word, so the record does not move until it
hatches (read). The pilot census in `demo.md` counts `$21ae2` among the chosen records although `$2529a` skips y = `$f100`:
`$2529a` starts with A0 = `$31d54` (`lea` at `$2529a`) and replaces it only with a record nearer than `$7fff`, so when no
record qualifies it returns record 0, which at a wave start is a waiting record (read; the census rows were not split by
this case). In game 1 the census reached every kind of waves 0 to 2 and the attractor (wave index 3); the mothership
(wave index 5 and later) and the rocket (`$25306` 0 hits) were not reached: the rocket is launched only from the bound
key at `$1f7ea` (`$25798..$257be`), which the demo never presses, so the autopilot's `$228de` skip never fires in a demo.

The seeder is what README's seeder gate follows (447/447 on `$21792`): wave 0 appends three `$21776` records, and the
three stage-1 records of `fl/f1.snap` are those.

**The helpers** (read): `$22c1e` is the autopilot's steering routine, shared (`demo.md`); `$22d04` holds the last turn
(turn byte ±2, pitch ±`$700` by the sign bits); `$22d5e` thrusts along the record's attitude matrix (velocity minus 3/32
of one column and 1/32 of another) and, within `$1700` of the ship, adds two exhaust particles and a sound; `$22e38`
fires: unless the ship is crashing, it spawns an enemy shot (`$203f0`) at the record with the record's velocity plus the
heading >> 7; `$22ebe` adds (target - pos) >> D4 to a velocity; `$20310`, the enemy shot's handler, costs the ship `$333`
fuel on a hit within `$60` (empty fuel sets `$62a5d`) and, on reaching the ground over an object cell, damages it.

**Infection** (read, census): `$20702` (`Infection_Drop`) plants with jitter (`$206b8`) when the dropper is farther
than `$2300` from the ship and otherwise spawns a falling object (`$205be`) that plants where it lands (`$205f6`,
`Infection_Plant`, which also feeds the queue `$27134` when the cell holds an object of type 1 to 3). `$2010a` is 21
jittered plants; the bomb `$207d6` costs `$333` fuel within `$400` of the ship and on landing releases 51 or 31 drops
(`$2012c`). Census of game 1: `$20702` 16,784 calls, `$206b8` 81,050, `$205f6` 82,915, `$2010a` 3,155 (the bomber's
bursts are most of the plants), bombs `$2086a` 72, enemy shots `$22e38` 255.

**Provoking** (read, census): the paths `$1ffbc`, `$2004a` and `$20092`, reached when a shot lands on an infected ground
object of type 0 to 3 (from the player's shot handler `$1feb0` at `$1ff78` and from the enemy shot `$20310` at `$203cc` and
`$203da`; the two sources were not separated), award 40 points, call `$20702` 71, 71 or 41 times at the spot (so the code
sprays infection from a destroyed infected object; not checked on screen) and call `$201b4`, which scans the actor pool and turns every record with life bit 14 (a
patrol: `$21c64`, `$21d08`, `$21df6`) within `$800` on all three axes into a `Pursuer` (`$21f00`). Census: `$201b4` 7
calls, the `$20206` store 8 times, and `$21f00` first ran 4,600 steps after the first `$201b4` call.

## The player's shot, the targets and the ship box (gated)

`py/mpc/shot.py` holds these as functions; gate `mpc_shot` (`bash reversing/virus/py/mpc/gate_shot.sh`) checks them against
four fresh captures of demo flight 1 from `demo/S1b.snap`, each stopping at every `$255d4` arrival through `stserver`: the
autopilot untouched (1,190 ticks), its fire bit forced on (1,190), its aim wobbled with fire forced (1,050), and its fire
bit cleared (1,500).

**Order within a frame** (read, main loop `$231a8`; every count below depends on it): the object walker `$1fa72`, the ship
tick, the actor walker `$2157c`. So a shot fired in tick k is appended at the ship's position before that tick's move,
with the ship's velocity after drag and thrust and before gravity; the actors then move; and in the next frame the object
walker moves the shot once and tests it against the pool as arrival k + 1 reads it. A hit shows as life bit 15 at arrival
k + 1, the award and the removal at arrival k + 2.

**Spawn** (`$25720..$25794`, `$202fc`, `$1fc90`, `$1fd14`): with D2 bit 0 set and fuel at least 1 after the thrust's 3, fuel
and score each lose 1 and the record is position = ship + n, velocity = ship velocity + n, life `$16`, handler `$1feb0`,
where n is the signed high bytes of the ship's matrix words 0, 6 and 12 (the nose, at most 127 an axis). One random word
`asr #14` per axis (-2 to 1) is added to that axis's position and its velocity. A thrust tick first makes 20 draws for its
five exhaust particles (`$1fdca`), so the draws a shot gets depend on the thrust bit. Predicted record == appended record
2,354/2,354, from the RNG read at the arrival; with the shift 13, 19/2,354; without the exhaust draws, 1,371/2,354 (the
agent's run; not in the gate script). Fuel and score 4,926/4,926 ticks.

**Flight and expiry**: each walker pass decrements the life and removes the record when it goes negative, then pos += vel,
then vy += g. The shot moves 22 times. Shot set at arrival k + 1 == survivors plus the new shot 4,926/4,926 ticks, 1,384
expiries; with gravity added before the move 2,523/4,926.

**Hit**: after its move the shot is tested against every pool record in pool order, x then z then y, as -`$a0` <= actor -
shot < `$a0` (`sub`, `addi #$a0`, `cmp #$140`, `bcc`); the first record inside gets life bit 15 and the shot is removed. No
record is skipped (read): a record still waiting at y = `$f100` stops a shot and clears the bit itself. Predicted record ==
the `$1ff06` stop on 15/15 real hits and 43,488/43,488 shot-ticks with none; with a half-width of `$80`, 6/15. A hit was
seen at +159 and the nearest miss was 3 outside. The 15 hits: 10 on a flying seeder, 3 on a landed one, 2 on an attacking
patrol; 6 of them in the wobbled run, off the autopilot's own firing pattern. Pool order was never decisive (no shot had
two records in its box).

**Ground**: the shot uses the sum-of-sines ground `$245b8`, not the cell height map `$24754` the actor walker uses. Removal
by ground, water, object or wreck 891/891, and 42,597/42,597 shot-ticks that fly on.

**Kill**: the award runs at `$216d6` one actor pass after the hit, 15/15; score and pool count at k + 2, 13/13 (two patrol
kills end their run first). Seen: a flying seeder 100, a landed one 50, a patrol 300, each on the first hit. A shot's speed
is the ship's plus the nose, so its reach in 22 moves grows with the ship's speed v along the nose: 22 x (v + 127), about
2,800 units from a hover and 9,400 at v = 300. The autopilot fires inside `$900` (`demo.md`): 117 shots, 5 hits and 4 kills in wave 0.

**Targets in wave 0**: three seeders (leaving `Seeder_Wait` at ticks 10, 60 and 110), one patrol (tick 200) and one chaser
that waits 3,000 ticks, cannot be killed while waiting and does not hold the wave open. `shot.actor_step` gives a record's
next state, all nine fields: seeder wait 732/732, fly 7,701/7,701 (spring constant `$2c0` for `$280`: 520/7,701), descend
199/199, landed 821/821, take-off 21/21 plus the one tick that draws its new vx and vz from the RNG; patrol wait 804/804,
cruise 615/615, homing 3,013/3,014, attack 309/309; chaser wait 4,926/4,926. The one homing miss is the patrol turned into
a pursuer (`$21f00`), which is not modelled. A seeder is therefore predictable exactly until it takes off (positions equal
for 1,499, 1,032 and 1,499 ticks from tick 0 in the no-fire run; the agent's run). A patrol's steering reads the ship's
position after the tick's move and the tick counter plus its pool index, so `shot.predict` needs the ship's future path:
given it, position after 10, 20 and 40 ticks is exact on 281/281, 251/251, 220/220 attack starts and 2,943/2,951,
2,885/2,901, 2,732/2,765 homing starts.

**The ship box** (poked): the common tail `$215ea` flags the ship when -`$c0` <= ship - actor < `$c0` on x, y and z, both
positions after the tick's moves; the ship dies in the next tick. `py/mpc/gate_danger.py` pokes the ship to an actor's
next position plus an offset with zero velocity: 90/90 trials agree, 36 of them hits; with the box taken as -`$c0` < d <=
`$c0`, 62/90. A record still waiting does not collide (18/18); one that hatches that tick does. The patrol's own shots were
not gated.

## When a wave ends

`$20f82` (`Wave_CheckComplete`, once a tick from the main loop, skipped while the ship is hit or crashing) walks the pool
from the end and returns as soon as it finds a record whose behaviour is not `$21ae2`; when every record left is an
unhatched chaser (or the pool is empty) it falls into `$20fb4`: a sound, the wave counter `$32a50` plus 1, a count of
the object-map cells with bit 5 (infected), a bonus from it, then `$20e74(wave)` and a restart at `$2310c` (read). The
bonus is `max(0, base - 2 x infected) >> 2`, shifted right again by `4 - wave` while the wave is below 4, with base
`$9000`, `$64ba` or `$cb89` on landscape 0, 1 or 2, paid in steps of 8 points (read).

So a wave is cleared by destroying every hatched enemy and every waiting record of the other kinds, and the chasers'
hatch delays (3000 ticks on wave 0) are the penalty for being slow, not the wave's length.

**Gated (a `bp` with the rule's prediction):** `py/scan/waveend.sh` stops on `$20fb4` four times from `main_g001`. Game 1
completes wave 0 at tick 1190, wave 1 at 4790 and wave 2 at 9298, and game 2 completes its wave 0 at tick 1385 (the tick
counter `$32a44` is cleared at game start and also counts the 50 frames of each crash). At the first stop the pool holds
one record and the registers show the scan ran to the pool start with A4 = `$21ae2`; a pool dump at tick 1093 of the same
run shows two records, the waiting chaser (life `$774`, that is 3000 - 1092) and a patrol, so the wave ended when the
patrol died, with 1,900 ticks left on the chaser. A timer rule predicts tick 3001 for the first stop and is refuted.

So the reload of `$62a60` at pilot call 1191 of `demo.md`'s corpus is the restart after wave 0 was cleared, not a life
loss (inferred from the tick: the pilot is called once a tick).

## How later waves are harder

`$20e74(n)` resets the actor pool and appends the groups of block `$20e34[n & 15]` (read; the movem at `$20e92` loads
count, first life, life step, a velocity shift and the behaviour, then the loop gives the k-th record life
`first + k x step` and a random position anywhere on the map). The blocks, as records per kind:

| wave index | chaser (first hatch, step) | seeder | patrol | bomber | pursuer2 | attractor | mothership |
|---|---|---|---|---|---|---|---|
| 0 | 1 (3000) | 3 | 1 | | | | |
| 1 | 2 (2000, 500) | 4 | 3 | 1 | | | |
| 2 | 3 (1750, 400) | 5 | 5 | 1 | 1 | | |
| 3 | 4 (1600, 300) | 3 | 5 | 2 | 3 | 1 | |
| 4 | 5 (1500, 300) | 1 | 4 | 2 | 4 | 2 | |
| 5 | 6 (1200, 200) | 1 | 2 | 3 | 4 | 2 | 1 |
| 6 | 8 (1000, 200) | 1 | 1 | 3 | 5 | 3 | 1 |
| 7 to 9 | 9 (800, 150) | 1 | 1 | 4 | 5 | 3 | 2 |
| 10 to 15 | 9 (600, 100) | 1 | 1 | 4 | 7 | 4 | 3 |

(entries 7, 8, 9 point at one block and 10 to 15 at another; the HUD shows the index plus 1.) The tail of `$20e74` sets
the gravity `$32a3a` to 3 for n below 2, 4 below 4, 5 below 6 and 6 from 6 on, and builds landscape 1 at n = 4 and 2 at
n = 9 (README). Because the table index is `n & 15`, wave 16 would get wave 0's enemies with gravity 6 (read, not run).
No code reads the wave counter elsewhere for difficulty: its readers are this routine, the HUD and the bonus (read).

Some spawns depend on how full the object pool is, not on the wave: `$204d4` and `$20474` pick other spawn parameters
above `$bb`, `$119` and `$148` records, and the bomb's landing releases 31 drops instead of 51 above `$bb` (read).

## The demo flag and the carried queue

A raw scan of every aligned long in RAM for the absolute address `$00062a5f` finds eight, all in code, the same eight the
listing shows (and no base-plus-offset use: the only base near it, `$62a58`, is used by the tile filler as a byte flag).
Writers: `$23274` (key `$20` toggles it), `$24cfc` (0, SPACE in the attract loop), `$24d14` (`$ff`, the attract timer),
`$26050` (0, a key at the game-over wait). Readers: `$255c2` (autopilot or mouse), `$25f04` (skip the high-score word
`$2709a`), `$25f3c` (skip the name entry) and `$260f4` (skip the score-code line). So the demo changes nothing in the
enemies, the collision, the fuel, the waves or the scoring; it changes who flies and what happens after a game over (read;
`demo.md` "HUD and game-state fields" has the post-game steps).

`$260f4`, for a human game with a score of at least 12345, prints two numbers mixed from the score, the tick counter and
`$32a52` (the wave reached at game over), which looks like a verification code (inferred). It is the one reader of
`$32a52` (`$26152`; a raw scan for `$00032a52` finds only it and the writer `$25bdc`), and a demo skips it.

The queue `$27134..$2714b`: a raw scan finds six references, the same as `demo.md` lists: `$206b0` (`Infection_Plant`
writes the last entry), `$21d64` (`Patrol_HomeOnQueue` reads entry 0) and `$232e8`, `$23320`, `$2332e`, `$2333c`
(`InfectionQueue_Advance`). So the carried queue reaches play only as the patrols' homing target: in a new game they fly
to the previous game's last infected objects until `$232e6` flushes the entries.

## The blocks that stepped up across 24 games

The six blocks the 24-game chain flagged (`$27ce9..$27d11`, `$289c2..$28a02`, `$29703..$29769`, `$2b591`,
`$2ca81..$2cbcb`, `$2e2c3..$2e2d3`) all lie in `$276fc..$2f6f4`, the ten depth-bucket draw lists of `$ccc` bytes each
(bucket k from `$276fc + k x $ccc`; README "Depth sorting"). Their bytes are 8-byte draw records: a draw routine long
(`$16fb4`, `$16ff4`, `$1735c`, ...) and the projected x and y words.

- **Read.** `$23c8c` (`Buckets_Reset`, from the main loop at `$231bc` and the crash loop at `$25b34`) copies the ten start
  pointers from `$23cfa` over the ten end pointers at `$23caa`. Every append (twelve sites: `$1fae8`, `$1fb56`, `$1fb8c`,
  `$1fbfe`, `$2167a`, `$225ac`, `$23d88`, `$23e00`, `$23e76`, `$23ec0`, `$23f64`, `$258dc`) writes at the end pointer
  after a check against the bucket's limit and advances it; the painter `$243ec..$24474` calls the records from the start
  pointer while it is below the end pointer. No code addresses the area otherwise (a listing search for absolute
  addresses in `$276fc..$2f6f4` finds only `lea $276fc.l,A3` at `$2416e`, whose stores go downward into the vertex-type
  array below it). So a byte past a bucket's current end is never read: it is whatever the fullest frame so far left
  there, and it can only change on a frame that fills the bucket at least that far. That is why it moves by steps and
  only ever away from 0 after the first game; its rising values are a selection effect of picking monotone bytes from a
  million.
- **Gated (a watch with its positive control).** `py/scan/watch_deep.sh`: `watch 29703 $6e` over 600M steps of game 1 prints
  53 writes, all from the object appends `$1fb68`/`$1fb6e` and `$1fb9e`/`$1fba0`, all within 1,893 steps (one frame), and
  the block ends equal to `main_g002`'s copy.
- **Gated (the residue has no effect).** `py/scan/residue.sh`: from `main_g002` (game 2, with game 1's residue), 500
  samples of 200,000 steps of tick, ship position and velocity and the flag: unpoked against the whole area
  `$276fc..$2f6f3` zeroed, 500/500 identical; against it filled with `$ffffffff` (which would crash the painter if a stale
  record were ever called), 500/500 identical. The pokes were checked to land and persist (`m 29700` after 2M steps). The
  determinism control of `demo.md` (the same snapshot flown twice, 40/40) stands for the unpoked side, and `demo.md`'s
  RNG poke is the positive control that this measure sees a real change.

## What this means for "better between plays"

The carried state is now complete for the code read: the high-score table, `$32a52` (read only by a human game's score
line), the RNG, the infection queue (a homing target for patrols) and the draw-list residue (never read). None of it is a
parameter the pilot or the enemies adapt. A game reaches a higher wave by clearing waves faster, and with seven kinds
spawned at random places by an RNG that is never reseeded, that varies from game to game: waves 2 to 4 at game over in
24 unpoked games with no trend (`demo.md`, the chain). A memory of the demo reaching higher waves on repeats is
consistent with that spread, or with the Archimedes original, which is not this code.

## What the radar shows (gated)

The HUD routine `$23a2c` copies the 64 x 64 minimap `$2f6f6` to the screen (the pointer `$2705e`), appends the ship to a dot
list and plots the list over the copy, then draws the fuel and height bars. The list starts at `$2fef6` and holds three words
a dot: x, z and a type; the pointer `$27076` is its end and is put back to `$2fef6` after the plot. A dot is one pixel at
`((x + $8000) >> 10, (-(z + $8000)) >> 10)`, so a pixel is `$400` units on a side and the 64 pixels cover the whole wrapped
world; the height is not shown. The type indexes the plot table `$239ec`, which sets the pixel to that colour number, and only
where the screen under it is not colour 0 (read).

Each live behaviour appends its own dot with the record's x and z (16 sites, `$21800..$22a46`, read). No `_Wait` body has a
site, so an enemy that has not hatched is not on the radar. The types: every seeder state 5 (cyan `077`); chaser `$d` (pink
`736`); the patrol's three states `$b` (orange `641`), and the cruise state appends although it skips the 3D draw (next section); pursuer `$b`
and 3 (red `711`) on alternate ticks; `$2202c`, `$221ac` and the bomber 0 on even ticks (the table's default routine `$23750`,
which clears the pixel: the dot flashes) and 7, 7 and 5; attractor 0 and 3, mothership 0 and 6; the mothership's chaser 3; the
player's rocket and the ship `$f` (white). The infection is in the minimap itself: a plant recolours its cell there (`demo.md`).

`py/scan/radar_check.py` stops after the plot loop (`$23aa6`) on every frame of the autopilot's wave 0 from `demo/S1b.snap`:
the dot list equals the pool's hatched records in pool order, then the ship, on 1,100/1,100 frames (x, z and type; every
frame also holds a waiting record, which never has a dot). The pixel read back from the screen buffer is the dot's colour for
900 of 900 patrol and 1,100 of 1,100 ship dots and 1,356 of 1,550 seeder dots; the other 194 seeder dots read white,
the ship's dot plotted after them on the same pixel. That run reaches the seeder's and the patrol's states only; the other
kinds' types are read.

So the radar gives a player each hatched enemy's kind and its x and z to `$400` units, every frame, and nothing about height,
velocity, state, or the enemies still to hatch. A shot's box is `$a0` a side, so the radar is enough to fly to a target and not
enough to aim at it.

## What the 3D view shows (gated)

Every behaviour that draws its record ends by jumping to the tail `$215ea` of the actor loop `$2157c`. The tail queues the
record for the painter only when it is inside a window around the camera, tested unsigned so that it wraps with the world:

```
(x - (camx - $680)) & $ffff < $d00        (z - (camz - $600)) & $ffff < $c00
```

The window's corner is put in `$270e6` once a tick. There is no test on height. A record that passes gets the depth
`z - camz + $e00` (`$800..$13ff`), which picks its bucket (`README.md`, "The renderer"); one that fails goes straight to the
next record (`$216c2`) and is not drawn at all. The ship-contact test (within `$c0` on each axis: "The ship box") is inside the same branch, so only
a record in the window can hit the ship. The patrol's cruise state `$21c64` ends at `$216c2` and not at the tail: it is
on the radar and never in the 3D view.

`py/scan/view_check.py` stops at `$215ea`, `$2165c` (past the window test) and `$216c2` over the autopilot's wave 0 from
`demo/S1b.snap`: the test above, on D0, D2 and `$270e6`, says which records reach `$2165c` on 2,346 of 2,346 arrivals
(404 reach it, 1,942 do not), and the records queued in a frame are the pool's hatched records inside the window of that
frame's camera on 1,100 of 1,100 frames. The camera's x and z (`$270ce`) equal the ship's on every frame, so the window is
`$680` either side of the ship and `$600` ahead and behind: 13 by 12 cells of a 256 by 256 world, about three radar pixels
a side. The patrol's records arrive 796 times in the 900 frames it is on the radar; the other 104 are taken to be the cruise state (inferred from the count; that state's body is read).
In that run an enemy is in the window on 397 of the 1,090 frames that have a hatched one (404 of 2,450 enemy-frames:
384 seeder, 20 patrol), with the autopilot flying at them.

Inferred from the projection (`sx = (dx << 8) / depth + $a0`, read): over the measured depths 2,053 to 5,095 a screen
pixel is 8 to 20 units across, an eighth of a shot's `$a0` box or less. So an enemy in the window can be placed well
enough to aim at, and one outside it is known only as a radar pixel, `$400` units.

## Open

1. Drive the mothership and the rocket: a played or poked run to wave index 5 (`wb 32a50 05` before a wave end, labelled
   poke) with `hits` on `$226ac`, `$22722` and `$2279a`; a rocket key press (`$1f7ea` points at the bound key) with `bp
   25306` and a `watch` on the target's life word for the bits 15 and 13.
2. The attractor's tractor and fuel drain (`$225d6`: 0 hits in game 1): drive the ship to within `$700` of an attractor
   and `watch 32a2e 2` for the 25-a-tick drain.
3. The two-hit pursuer: `$22164` ran 4 times and `$221ac` 596: check with `bp 22164` that the score rises by 200 and the
   same record later dies for 700.
4. Provoking: a `bp 20206` stop, then show that the converted record's `+16` is `$21f00` and that it was a patrol within
   `$800` of the impact.
5. Gate one enemy model the way the seeder was gated: `$21afe` (the chaser) is closed-form (pull >> 7, drag 1/64, clamp),
   so a `bp 2157c` capture over its hatched ticks would give a match count.
6. A census on other seeds and waves (one game here, 600M steps), and the infection rate per kind measured from the object
   map (bit 5 cells per tick) with the bomber removed by a poke, to test the reading that its bursts plant most.
7. The bonus formula and the table index wrap at wave 16 are read only.

## Scripts (`py/scan/`)

| script | what | output | expected |
|---|---|---|---|
| `census.sh` | `hits` on every behaviour entry and helper over game 1 (600M steps from `main_g001`) | `scratchpad/virus/scan/census.out` | the census column above |
| `waveend.sh` | four `bp 20fb4` stops with tick, wave and pool count | `scratchpad/virus/scan/waveend.out` | ticks `$04a6`, `$12b6`, `$2452`, `$0569`; waves 0, 1, 2, 0 |
| `watch_deep.sh` | `watch 29703 $6e` over game 1 | `scratchpad/virus/scan/watch_deep.err` | 53 `WATCH` lines from `$1fb68`, `$1fb6e`, `$1fb9e`, `$1fba0` |
| `radar_check.py` | the radar's dot list against the pool, and the dots' pixels, on 1,100 frames from `demo/S1b.snap` (through `stserver`) | stdout; the server's log in `scratchpad/virus/radar/` | `1100 / 1100`; screen colours 5, 11 and 15 only |
| `view_check.py` | the 3D view's window test at `$215ea` record by record, and the records queued per frame against the pool, on 1,100 frames from `demo/S1b.snap` (through `stserver`) | stdout; optional JSON | `2346 / 2346`; `1100 / 1100` |
| `residue.sh` | game 2 flown unpoked, with the bucket area zeroed, and filled with `$ff` | `scratchpad/virus/scan/res_*.txt` | `zero 500 of 500 identical`, `ff 500 of 500 identical` |

They read the chain's start snapshots from `scratchpad/virus/chain/long/starts/` (`py/chain/gate_chain.sh long 24`) or, when that
is absent, the overseer copy `scratchpad/overseer/virus_long/work/main/starts/` that produced these numbers, and take about 1, 2.5, 2.5
and 1.5 minutes.

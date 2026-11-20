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
| objects | `$302f6` | 18 bytes: x, y, z, vx, vy, vz, life (words), handler (long) | `$32a3c` (max `$177`), `$2707e` | `$1fd14` | `$1fa72` | shots, sparks, droplets, fragments, smoke, contrails, falling infection, bombs, score pop-ups |

Read: the append routines and walkers are named from their bodies (`$1fa72` loads `$302f6` and compares its index with
`$32a3c`; `$1fd14` refuses at 375 records). The README's seeder gate follows wave 0's three seeders (below).

**The object walker.** For each record `$1fa72` loads x, y, z, vx, vy, vz, life into D0..D6, takes `life - 1` (negative
removes the record), adds the velocity to the position and jumps to the handler. A handler adds gravity `$32a3a` to vy if it
uses it, stores the record back, tests the ground (`$24754`; type 8 is water) and draws through `$1faa8` (a dot sprite),
`$1fb18` (dot plus shadow) or `$1fbbc` (a model); `$1fc58` removes it by copying the last record over it and walking that
slot again. The spawn entries take D0..D2 position, D3 a jitter shift applied to position and velocity together, A3 life, D4
a life-jitter shift and A4 the handler: `$1fc8a` clears all three velocities, `$1fc8c` keeps vy, `$1fc90` keeps all three. The
handlers (read from their bodies; census of the 1190 frames of `S1b`, record-frames, by `py/objects/pool_capture.py`):

| handler | name | behaviour | census |
|---|---|---|---|
| `$1fd78` | `Spark` | gravity, bounces with halving damping, splash on water; dot colour 15, then 7, then 3 as life falls. Spawned by `$1fdca` (thrust exhaust: `$22e18`, `$256ee..$25716`) and `$1fdde` (explosion bursts) | 23,639 |
| `$1fe02` | `WaterDroplet` | gravity, dot colour cycling 5, 15, 1, 6 by `vy`, removed on the ground. Spawned by `$1fe84` from the splashes `$1fe36` (16), `$1fe5c` (3) and `$1fe9c` (ship wake) | 5,474 |
| `$1feb0` | `PlayerShot` | gated above | 1,437 |
| `$20310` | `EnemyShot` | `$333` fuel within `$60` of the ship; objects as the player's shot | 106 |
| `$20424` | `Fragment` | gravity, bounces, colour by `vy`, splash on water. Spawned by `$20474` (`Fragment_SpawnLong`) and `$20496` | 10,472 |
| `$204be` | `Smoke` | no gravity, no ground test, dot by `vx`; spawned by `$204d4` (`Smoke_Spawn`, four variants by pool fill) from damaged objects, explosions and actors | 9,848 |
| `$20592` | `Contrail` | no gravity, colour by life, life 30; spawned by `$25972` via `$205aa` when the ship's y is below `$f300` (`$25930..$2596a`) | 60,736 |
| `$205be` | `Infection_DropFall` | gravity; on the ground `$205f6` plants, on water a small splash; gated below | 8,611 |
| `$20766` | `ScorePopUp` | the number as text (`$173b4`), colour from `$2074c`, life `$10`; spawned by `$20798` | 33 |
| `$207d6` | `Bomb_Fall` | no gravity or drag; `$333` fuel within `$400` of the ship, burst `$2012c` on that or when ground - y <= `$80`; else drawn only (gated) | 6,447 passes in the bomber gate's 15 captures |
| `$20882` | `DebrisChunk` | tumbling model (`$aa72`), bounces, splash on water; two per explosion via `$208dc` | 303 |
| `$208f4`, `$2097a` | `SprayPlumeA`, `SprayPlumeB` | mirrored wake plumes (models `$cce2`/`$cd50`, `$cdbe`/`$ce2c` by `$32a45` bit 0), spawned by `$20958`, `$209de` when the ship skims water (`$259de..$25a6a`) | 150, 434 |

The ten dot routines `$16ff4..$1735c` set one colour index each (the or/and plane ops are read: `$16ff4` 15, `$17044` 7,
`$1709c` 11, `$170f4` 3, `$1714c` 5, `$171a4` 12, `$171fc` 9, `$17254` 4, `$172ac` 14, `$17304` 6, `$1735c` 1); `$16fb4` erases.

**Falling infection (gated).** `py/objects/gate_infection_fall.py` models one walker pass of `$205be` records (life - 1,
position + velocity, vy + gravity, ground `byte * 8 + $fd68` or `$420` on the pad, landing when ground - y is negative,
then `$205f6`'s rule: plant at cell `((x + $80) >> 8, (z + $80) >> 8)` unless the ground at the next cell corner is
above `$510` or `$420`) against the capture: records predicted to survive are in the next frame's pool byte for byte
8319/8319; predicted landings are gone 292/292 (32 on water); predicted plants have bit 5 set 213/213 (132 newly set,
132/132) and predicted non-plants leave the cell 47/47. Controls: gravity + 1 gives survivors 0/8319, ground + `$20` 8319/8431,
the cell one column over 77/213 plants and 0/136 newly set. The spawn state is not modelled.

The actor walker `$2157c` loads a record into D0..D6, reads the ground height under it (D7, `$24754`), or-s `$a000` into
the life word when the ground is at or above y, and `jmp`s to the behaviour. Bit 15 of the life word is "hit", bit 13
"hit the ground"; a behaviour that sees bit 15 takes its kill path. Most behaviours end at the common tail `$215ea`: if the
record is inside the view box and within `$c0` of the ship point (the words at `$270bc`) on all three axes and the ship is
not already crashing (`$62a5e`), it sets bits 15 and 13 of the record's life word (`$21648..$21650`, read), so a collision
takes the same kill path as a ground hit and kills a multi-hit enemy at once, and sets `$62a5d` (the ship is hit); then it appends a draw record to the depth bucket. The kill path `$216d6` adds the
award in A0 to the score through the pop-up `$20798` (which formats the number and spawns a floating score object; the
award is not scaled), runs the explosion `$202a4` and removes the record by copying the last one into its slot. `$216e8`
is the same without the award (the rocket).

## Who writes `+16` (whole image)

A raw scan of the code region for `move.l #imm,16(An)` (opcode `$217c | An << 9`, displacement `$0010`) finds one site,
and the listing has no other store to `16(An)` in game code (`move.w D3,16(A1)` at `$1f6c8` is the matrix builder). So
the behaviour pointer is written by exactly three kinds of code (read):

1. `$21722` (`Pool_Append`) stores A4. Its three callers: the wave start `$20f18` (A4 from the wave table), the
   mothership's launch call at `$22722` inside `$226ac` (A4 = `$2279a`) and the rocket launch `$25368` (A4 = `$228de`).
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
| `$21afe` | `Chaser` (gated, below) | every `$1ff` ticks reverses its velocity; pushed up below `$100` above the ground; velocity += (ship - pos) >> 7, drag 1/64, clamp ±`$80`; every other tick a sound within `$3c00` and a smoke puff (`Smoke_Spawn`, `$204d4`) within `$2300` | 400 | 1,949 |
| `$21c42` | `Patrol_Wait` | life countdown; then life byte `$40` with bit 14 set ("provokable", below), `$21c64` | | 2,814 |
| `$21c64` | `Patrol_Cruise` | within `$2800` of the ship: `$21df6`; otherwise moves in x and z only, kept at least `$400` above the ground, not drawn and not collided (it returns past the common tail); after `$40` ticks `$21d08` | 300 | 2,221 |
| `$21d08` | `Patrol_HomeOnQueue` | gravity and drag 1/32; every fourth tick steers (`$22c1e`) toward entry 0 of the infection queue `$27134` and, within `$a00` of it, fires (`$22e38`); other ticks hold the turn (`$22d04`); thrust (`$22d5e`) unless the steer bit 11 is set, and again within `$300` of the ground; after 64 ticks back to `$21c64`, which then cruises 5 ticks before homing again | 300 | 15,232 |
| `$21df6` | `Patrol_AttackShip` | as `$21d08` with the ship as the target; fires every fourth tick within `$900`; beyond `$2300` of the ship back to `$21c64` | 300 | 1,263 |
| `$21f00` | `Pursuer` | steers at the ship every tick, thrust (double near the ground), velocity += (ship - pos) >> 13, or >> 9 within `$1900`; fires every other tick within `$900`; drawn flashing | 500 | 3,880 |
| `$2200c` | `Pursuer2_Wait` | life countdown, then `$2202c` | | 1,034 |
| `$2202c` | `Pursuer2` | as `$21f00` but fires every tick within `$900`; on a hit: if bit 13 is set (the ground at or above y, or the ship-contact tail `$21648`) it dies for 900, else 200 points now and `$221ac` | 900 | 3,760 |
| `$22164` | `Pursuer2_FirstHit` (first-hit path of `$2202c`, a branch target, not a stored pointer) | A0 = `$384` and the kill path `$216d6` when bit 13 is set, else 200 points, sound 3, bit 15 cleared, stun count 5, pad `$ffff`, behaviour `$221ac`, and the same pass falls into `$221ac`, so at the next arrival the record has count 4 and has made one stunned move ("The two-hit pursuer's hit paths"); seen 4, 5, 12 and 8 times in games 14, 45, 50, 93 | 200 | 4 |
| `$221ac` | `Pursuer2_Damaged` | A0 = `$2bc`; counts 4 to 0 are stunned passes (position += velocity, vy += g, drag; no steer, thrust, pull or fire), and a hit with a non-zero stored count is ignored (`$22128`: reload, `tst.b` of the count, `beq` to the kill at `$22130`, else `$221b8`); the pass that finds count 0 pursues as `$2202c` with the near-ground test `$300` and pull >> 10 within `$1900` (>> 13 beyond); a hit or ground contact at count 0 kills it for 700 | 700 | 596 |
| `$222dc` | `Bomber_Wait` | life countdown (bit 15 cleared, life - 1, stored while not negative); at expiry one RNG draw gives the heading byte, stored as the life word, and the same pass runs `$22316` (gated, "The bomber and its bombs") | | 544 |
| `$22316` | `Bomber` | every tick replaces vx and vz by the heading's matrix words 0 and 6 (`$1f646`) and moves by them; a spring toward `$700` above the ground; within `$2d00` of the ship a sound and a bomb (`$2086a`) every 8th tick, skipped only beyond `$a00` over water level (the 16th-tick test at `$22408` never filters); farther away, on 15 of every 16 ticks over land, 21 infection plants at once (`$2010a`) (gated, "The bomber and its bombs") | 800 | 6,938 |
| `$22486` | `Attractor_Wait` | life word counted down with bits 15 and 13 cleared (cannot be hit, no move, no draw); when it goes negative the behaviour becomes `$224a6` with life word 5 and the same pass runs it (gated, "The attractor") | | 101 |
| `$224a6` | `Attractor` (gated, "The attractor") | the seeder's spring (`$280` above the ground) with no vx or vz drag; within `$b00` of the ship it adds (record - ship) >> 6 to the ship's velocity (`$22ebe`, A3 = ship); within `$700`, unless the ship is crashing, a sound, a beam draw record (`$22a64`) and fuel `$32a2e` minus 25 a tick, empty fuel sets `$62a5d`; the life word is a hit counter from 5 (the fifth hit kills, `$22460`), a ground hit kills at once | 1000 | 2,686 |
| `$22688` | `Mothership_Wait` | life countdown (30 ticks from `$1e`; bits 15 and 13 cleared, so it cannot be hit), then count `$1e`, y `$f101`, `$226ac` in the same pass | | 0 in games 1, 14, 45, 93; 31 in game 50 (wave 5) |
| `$226ac` | `Mothership` | moves in x and z only, y fixed at `$f101` (900/900 ticks); within `$b00` of the ship, on every tick with `$32a48 & $1f` = 0 while its count byte is at least 10, launches a `$2279a` (the call is `$22722`). The launch does not cost a count: the count is stored at `$226b8`, before the `subq.b` at `$2270c`, and the life word stayed `$1e` through 27 launches. Each hit (`Mothership_Hit` `$22666`) costs one; at 0, or on any ground-bit hit, `Mothership_Kill` `$2264e` | 2000 | 4,056 ticks in game 50 |
| `$2279a` | `Mothership_Chaser` | the chaser's body with clamp ±`$70` and reversal every `$a9` ticks, no wait state; launched with velocity 0, `$80`, 0 and life `$1ff` (the first reversal 512 ticks on); the kill path `$22784` pays 150 for a hit or the ground | 150 | 0 (the ship was never in range) |
| `$228de` | `Rocket` | the player's rocket: counts down its life byte; steers at the record `$2709e` (`$22ee2`), clamp ±`$a0`; within `$240` of it sets the target's bits 15 and 13 (a ground hit, which kills a multi-hit enemy at once) and explodes with no award | | 0 |
| `$21f00` from `$20206` | (see `$201b4`) | | | 8 writes in game 1; 7, 9, 11, 10 in games 50, 14, 45, 93 |

The waiting records are appended with y = `$f100` (the autopilot's `$2529a` skips those) and with velocity
`(random >> D7, 0, random >> D7)`; a waiting behaviour writes only its life word, so the record does not move until it
hatches (read). The pilot census in `demo.md` counts `$21ae2` among the chosen records although `$2529a` skips y = `$f100`:
`$2529a` starts with A0 = `$31d54` (`lea` at `$2529a`) and replaces it only with a record nearer than `$7fff`, so when no
record qualifies it returns record 0, which at a wave start is a waiting record (read; the census rows were not split by
this case). In game 1 the census reached every kind of waves 0 to 2 and the attractor (wave index 3); the mothership
(wave index 5 and later; reached in game 50 only, see "The mothership and the gated chasers") and the rocket (`$25306` 0 hits in all four games) were not reached: the rocket is launched only from the bound
key at `$1f7ea` (`$25798..$257be`), which the demo never presses, so the autopilot's `$228de` skip never fires in a demo.

The seeder is what README's seeder gate follows (447/447 on `$21792`): wave 0 appends three `$21776` records, and the
three stage-1 records of `fl/f1.snap` are those.

**The helpers** (read): `$22c1e` is the autopilot's steering routine, shared (`demo.md`); `$22d04` holds the last turn
(turn byte ±2, pitch ±`$700` by the sign bits); `$22d5e` thrusts along the record's attitude matrix (velocity minus 3/32
of one column and 1/32 of another) and, within `$1700` of the ship, adds two exhaust particles and a sound; `$22e38`
fires: unless the ship is crashing, it spawns an enemy shot (`$203f0`) in the object pool at the record's position and velocity
plus the matrix nose word >> 7, jittered by three RNG draws ("The enemy shot"); `$22ebe` adds (target - pos) >> D4 to a velocity; `$20310`, the enemy shot's handler, costs the ship `$333`
fuel on a hit within `$60` (empty fuel sets `$62a5d`) and, on reaching the ground over an object cell, damages it.

**Infection** (read, census): `$20702` (`Infection_Drop`) plants with jitter (`$206b8`) when the dropper is farther
than `$2300` from the ship and otherwise spawns a falling object (`$205be`) that plants where it lands (`$205f6`,
`Infection_Plant`, which also feeds the queue `$27134` when the cell holds an object of type 1 to 3). `$2010a` is 21
jittered plants; the bomb `$207d6` costs `$333` fuel within `$400` of the ship and bursts there or on landing (`$2012c`: 31
drops when within `$2300` of the ship with more than `$bb` records in the object pool, else 51; gated, "The bomber and its bombs"). Census of game 1: `$20702` 16,784 calls, `$206b8` 81,050, `$205f6` 82,915, `$2010a` 3,155 (the bomber's
bursts are most of the plants), bombs `$2086a` 72, enemy shots `$22e38` 255.

**Provoking** (scan gated, rest read; census): the paths `$1ffbc`, `$2004a` and `$20092`, reached when a shot lands on an infected ground
object of type 0 to 3 (from the player's shot handler `$1feb0` at `$1ff78` and from the enemy shot `$20310` at `$203cc` and
`$203da`; the two sources were not separated), award 40 points, call `$20702` 71, 71 or 41 times at the spot (so the code
sprays infection from a destroyed infected object; not checked on screen) and call `$201b4`, which scans the actor pool and turns every record with life bit 14 (a
patrol: `$21c64`, `$21d08`, `$21df6`) within `$800` on all three axes into a `Pursuer` (`$21f00`). Census: `$201b4` 7
calls, the `$20206` store 8 times, and `$21f00` first ran 4,600 steps after the first `$201b4` call. The scan itself is gated:
`py/behaviours/provoke_check.py` stops at `$201b4` (impact D0 x, D2 z, the shot's y at -16(A6), and the whole pool) and at
`$20206`, and on 6 scans of game 50 with 7 conversions every converted record was a patrol (`$21c64` once, `$21d08` six times) with life bit 14, lay
inside -`$800` <= record - impact < `$800` on all three axes (largest offsets seen: y -1,334, x 756) and had `+16` = `$21f00`
after the store; the converted set equals the set the window predicts on 6/6 scans, and 9 other bit-14 patrols outside the
window were left alone (the control). Which of the three provoking paths fired was not recorded.

## The mothership and the gated chasers

Wave index 5 appends the mothership last (record 18 of 19, `Mothership_Wait` with life `$1e`, y `$f100`, velocity -23, 0, -2 in game 50),
so, by the wave-end rule above (inferred; no natural run killed it), it holds the wave open until it is shot 30 times or rammed. Gate `behaviours`
(`bash reversing/virus/py/behaviours/gate_behaviours.sh`, about 6 minutes) builds the wave-5 start of game 50 of the 100-game chain
(`py/behaviours/build_snaps.py`) and drives it with `py/behaviours/mothership_drive.py`. The drive is poked (labelled): at every `$255d4`
arrival the ship is placed at the mothership position minus three nose vectors with velocity 0, and `$62a5d` is cleared, so the
ship is inside `$b00`, outside the `$c0` ship box, and its chasers cannot end the run. In 900 ticks the mothership
launched 27 times (the 27 launches, ticks 36 and then every 32nd) with its y and life word unchanged. Each launched record equals
`chaser_step` of `[mx, my, mz, 0, $80, 0, $1ff, 0, $2279a]` with the ship as read at the next arrival, 27/27 (`gate_launch.py`;
launch vy 0: 0/27, life `$1fe`: 0/27). The control run without the poke ends with the ship crashing at tick 668, 0 launches and a
closest approach of 9,128 against the `$b00` range: a natural pilot does not provoke a launch, which is why `$22722` has 0 hits in
the census. Firing (`autofire`, 600 ticks): 30 consecutive hits, `$22666` 30 times, then `$2264e` once and the award 2000 (score +2,000
less the shot's 1). A hit tick is not a dead tick: the hit path clears bit 15, falls into the move and the launch test, and a ship box
collision sets bits 15 and 13 (`$21648..$21650`), so ramming it takes the ground path and kills it at once (seen once, with the earlier
version of the drive; read for the rule).

The chaser gate `py/behaviours/gate_chaser.py` predicts a record at arrival k+1 from arrival k, all nine fields, with the ship at k+1 and
the ground from the capture's own height map. `$2279a`: 2,818/2,818 (135 passes at the clamp, 8 at a reversal, 13 swap-walked records compared in the killed slot; the reversal and the
clamp are reached only through labelled poke C, which sets velocities and life words at four ticks, because these chasers die on the
ship within about 100 ticks); controls: drag >> 5 346, pull >> 6 28, clamp `$6f` 2,685, reversal `$a8` 2,810, ship before the move 1,020.
`$21afe` and `$21ae2` on a natural capture of game 50 wave 5: 1,069/1,069 and 1,896/1,896 waiting records; drag 416, pull 329, clamp `$7f` 72,
ship before the move 837. With a life poke (3 at three ticks) the reversal is reached: 782/782 and 3 reversal passes, 779/782 with the
period one short. The model is `chaser_step`: life - 1 and a negated velocity at 0, move, vy += gh - y - `$100` when that is negative (gh at
the pre-move x, z), velocity += (ship - pos) >> 7, minus 1/64, then the clamp.

The two-hit pursuer (natural captures with `capture_events.py`, which adds `$22164` as the event `p2_hit1`; observed on
captures of game 50 from `$W/g050` snapshots at 820M and 1065M steps, not a line of the gate, whose natural capture holds two first hits and no complete chain): the first hit on a `$2202c` record raises the score by
200 (less the shot's 1), the next hits for five ticks are ignored, and the first hit after them pays 700 at `$216d6` and removes
the record. Four complete chains in game 50 (first hit to kill 7, 5, 5 and 5 ticks; the same pool slot throughout, no other kill between);
the ground-bit path for 900 was not seen. Rocket and `$25306` are still unobserved.

**Census on four games** (`py/behaviours/census_chunks.py <game> <steps>`, 20M-step chunks of `hits` on every entry, with the wave word read
after each chunk and `summarize.py` splitting the sums by wave; not a gate, about 15 minutes for the four; games 14, 45, 93 are run to
their game over at wave index 4, game 50 to wave 5, from `chain/long100/starts/main_gNNN.snap`). Hits in games 14, 45, 50, 93: `$21792` 12,428,
18,850, 21,107, 10,346; `$21afe` 2,945, 2,515, 4,257, 2,887; `$21d08` 24,029, 22,950, 28,494, 21,582; `$21f00` 4,197, 7,633, 7,411,
5,930; `$2202c` 14,827, 9,758, 15,913, 5,813; `$221ac` 24, 1,147, 9,363, 1,753; `$22316` 14,852, 14,560, 32,945, 12,656; `$224a6` 6,883, 6,564, 21,122,
8,305; `$225d6` (the attractor's tractor) 31, 42, 99, 137; `$228de`, `$25306`, `$22722`, `$2279a` 0 in all four. Every entry the table lists
except the rocket runs in some game, and the mothership only in game 50, the one game that reaches wave 5; the by-wave split puts `$21f00`
from wave 1, `$2202c` from wave 2, the attractor from wave 3 and the mothership in wave 5 only.

## The pursuers and the patrol (gated)

`Pursuer` `$21f00` (award `$1f4`, 500) and `Pursuer2` `$2202c` share one body. Per tick, as `pursuer_step` in
`py/behaviours/gate_pursuer.py`: life bit 15 set takes the kill path `$216d6` and no move; otherwise position += velocity,
vy += gravity `$32a3a`, drag v -= v >> 5; the steer `$22c1e` at the ship `$270b0` every tick; the thrust `$22d5e` once when
the steer left bit 11 clear and a second time when the ground is within `$280` below the record (`$380` for `$2202c`); then
the pull v += (ship - pos) >> 9 when the saturating |dx| + |dy| + |dz| is at most `$1900`, else >> 13. Firing (every other
tick within `$900`, every tick for `$2202c`) spawns one enemy shot (three RNG draws, "The enemy shot") and does not change the pursuer's record; the patrol states keep steering after their fire. The
patrol states (`$21c42`, `$21c64`, `$21d08`, `$21df6`) are `shot.actor_step`'s, already gated on wave 0 by `mpc_shot`
("The player's shot, the targets and the ship box"); the attack state steers only when `$32a48 & 3` is 0 and thrusts once
near the ground. The conversion `$201b4` runs after the record's own pass in the same tick: it clears life bit 14 and
stores `$21f00`, and every other field is the pass's result.

One walker rule the gate found: when a record is killed, the last pool record is swap-removed into its slot and walked
there in the same pass, with the tick phase of that slot (counter `tick44 + slot + 2`). Gating it with its old index gives
one `patrol/home` miss in 53,992. `py/mpc/gate_actor.py` and `py/behaviours/gate_chaser.py` follow the same rule (the old
index is their `--control noswap`): on the wave-0 shot captures no swapped record uses the phase and nothing moves, while
`gate_actor.py` on the pursuer corpus gains 4 swapped `patrol/home` records (53,990 against 53,986 of 54,022; the other 32 are
conversions and hit ticks it does not skip), and `gate_chaser.py` checks the 13 swap-walked mothership chasers of `ms_trials`
in the killed slot on all nine fields, 13/13. Their captures (`py/mpc/shot_capture.py`, also used by `capture_events.py`,
`mothership_drive.py` and `cap_nat.py`) treat a `stserver` stop at the same PC within 2,000 steps of the last as an interrupt
re-stop only when D0 to D7 and A0 to A6 also equal the last stop's: a step bound alone drops a real second visit (two actors
through `$21654` in one tick), and the earlier 64-step bound left a spurious tick row in `ms_trials` that shifted its poke ticks
by one.

Gate `pursuer` (`py/behaviours/gate_pursuer.sh`, about a minute): one fresh natural capture (chain game 45 at 300M steps,
2,500 ticks, wave 2) gives the pursuer 1,793/1,793 and the patrol home state 2,279/2,279; the 25 saved natural captures
of waves 1 to 4 (games 14, 45, 93 at 100M-step marks, game 50 from `p135..p495`) give, the record at k+1 equal to the model
on all nine fields:

| state | match |
|---|---|
| `$21f00` pursuer | 24,653/24,653 |
| `$2202c` pursuer2 (normal pass) | 22,805/22,807 |
| patrol home `$21d08` | 53,992/53,992 |
| patrol attack `$21df6` | 6,317/6,317 |
| patrol cruise `$21c64` | 5,877/5,877 |
| patrol wait `$21c42` | 2,213/2,213 |
| conversion `$201b4` | 34/34 |

The two `$2202c` misses are first hits (`p2_hit1`, the record becomes `$221ac`), which the model leaves out; 72 passes with
a shot hit that tick and 25 death or crash ticks are skipped. Branches exercised: 42,616 far pulls, 4,855 near, 22,787
thrusts, 55 near-ground double thrusts (thin). Controls, pursuer out of 24,653: no pull 643, far pull >> 12 3,982, steer
every fourth tick 7,184, the ship before its move 21,292, one thrust near the ground 24,598 (exactly the 55); conversion
keeping bit 14 0/34; the patrol phase off by one, attack 3,883/6,317 and home 33,856/53,992. The two-hit pursuer's
hit paths, the attractor, the enemy shot and the bomber are gated in the next four sections.

## The two-hit pursuer's hit paths (gated)

Models `first_hit_step`, `damaged_step` and `kill_step` in `py/pursuer2/pursuer2.py`, built on `pursuer_step`. Record words are
[x y z vx vy vz life pad behaviour]. The walker `$2157c` or-s `$a000` into the register D6 when the ground is at or above y and
does not store it, so the damaged routine's reload of the life word from memory (`$22128`, `$221b8`) drops the ground bits.

First hit (`$22164`, from `$2202c` when D6 has bit 15): with bit 13 set it takes the kill path with A0 = `$384` and does not move;
otherwise 200 points, bit 15 cleared, stun count 5, pad `$ffff` (on all 16 natural first hits; the cause, D6's high word left
over, is inferred), behaviour `$221ac`, and the same pass falls into `$221ac`: bit 15 is now clear, so the hit is not ignored,
the count goes from 5 to 4 and the stunned move runs, and the record at the next arrival has count 4. The score rises by the
award less one per shot fired that tick (`fire_post`), 13/13.

Damaged (`$221ac`): the shot handler sets the hit bit after the walker pass, so it is read on the next tick. A hit with a stored
count of 0 kills for 700; with a non-zero count the hit is ignored, the hit and ground bits are dropped, and the pass is stunned.
The count then goes down by one; the pass that finds 0 stores 0 and pursues as `$2202c` with the near-ground test `$300` and
pull >> 10 within `$1900`, >> 13 beyond. Ground contact with a non-zero count is ignored the same way and leaves no bit 13 in memory.

Kill (`$216d6`): the award goes to the score long `$2708e`, the pool count `$32a3e` drops by 1, and the last record is copied into
the killed slot and walked there (a killed last record is dropped). The draw, the explosion `$202a4` and the pop-up `$20798` are
not modelled.

Gate `pursuer2` (`py/pursuer2/gate_pursuer2.sh`, about 2 minutes), the record at k+1 against the model on all nine fields over the
25 saved captures and two fresh game-50 captures (`c1065`, `w5`) the model was not derived from: 16/16 first hits, 64/64 stunned
passes, 10,128/10,128 far and 4,861/4,861 near pursuit passes, 12/12 kills of 700 (slot and award; pool count 13/13, score 13/13,
pool behaviours 12/12, the last record in the killed slot 9/9 by behaviour and 3/3 on nine fields), and one natural kill of 900
from a ship contact (bit 13 set by `$21648`). Labelled pokes on `pursuer/snaps/g014_500.snap` (y of a live record set to the ground
height under it, against the same snapshot unpoked): `$2202c` on the ground dies for 900 (kill event, pool count and score 1/1); a
stunned `$221ac` on the ground with no shot ignores it, life `$0002` (3/3); with count 0 it dies for 700. Controls: stun count 4 at
the first hit 0/13, no fall into `$221ac` 0/13, pad kept 0/13, award 100 0/13, stunned count one short 12/48, every hit kills
11/45, near pull >> 9 4/721, far pull >> 12 130/4,722, no shot hit bit 2/13, ground bits kept in memory 47/48, ground bit ignored
on a first hit 13/14.

The steer's tilt in `$22c1e` (and `$22d04`) is a signed byte on the way up (`addi.b #2; cmp.b #$3f; ble`: `$ff` + 2 = 1, no clamp)
and an unsigned one on the way down (`subi.b #2; bcc`, floor 0). `py/mpc/shot.py`'s `_tilt` clamps the unsigned byte and agrees
below `$7e`, where every pursuer and patrol stays; a damaged pursuer starts at `$ff` (the pad `$ffff`), and
`pursuer2.use_signed_tilt()` installs the signed version on import (the unsigned one fails 31 passes of about 15,000).

## The attractor (gated)

`Attractor_Wait` `$22486` and `Attractor` `$224a6` (award `$3e8`, 1000), as `attractor_step` in
`py/attractor/gate_attractor.py`, one actor-walker pass. The wait state clears life bits 15 and 13, takes one off the life
word and stores it; while the result is not negative the record is unchanged (no move, no common tail); when it goes negative
the behaviour becomes `$224a6`, the life word 5, and the fly body runs in the same pass. The fly body: when the life word has
bit 15 (a shot's hit, or the walker's ground-at-or-above-y test), bit 13 kills at once (sound `$26`, kill path `$216d6`),
else the life byte loses one, a zero kills (`$22460`), and otherwise bit 15 is cleared and the pass goes on. Then pos += vel;
D1 = y - ground + `$280` (the walker's pre-move ground word D7), vy -= D1 >> 5, vy -= vy >> 4, vy clamped to [-`$60`, `$60`);
vx and vz are unchanged (the seeder `$21792`'s spring without its sound and infection). D3 is the saturating |dx| + |dy| + |dz|
from the record after its move to the ship `$270b0` after this tick's flight. D3 <= `$b00`: `Vel_PullToward` `$22ebe` adds
(record - ship) >> 6 to the ship's three velocity words. D3 <= `$700` and `$62a5e` clear: a sound, a beam draw record (`$22a64`,
not modelled) and `subi.w #$19,$32a2e` at `$225d6`; a negative result clears fuel and sets `$62a5d`. The common tail `$215ea`
ORs `$a000` into a record that touches the ship, which kills it on the next pass through bit 13. A player's shot that lands in
tick k sets bit 15 after that tick's actor pass: the stored record carries it and the next pass takes the hit path.

Gate `attractor` (`py/attractor/gate_attractor.sh`, about 6 minutes): three fresh natural captures of 4,500 ticks through a wave
change (games 14, 93 and 45 from the `pursuer/snaps` 400 and 300 marks, `py/attractor/cap_poke.py none`) and the 25 saved
pursuer captures, rows seen twice gated once. The record at k+1 equals the model on all nine fields: wait 550/550, wait expiring
into the fly body 5/5, fly 20,670/20,670, fly with a hit pending 19/19, kills on the fifth hit 5/5. The ship (pos, vel, att,
fuel from the flight tick `exact.step_full`, then the pulls and drains) equals the next arrival on velocity and fuel: pull only
59/59, pull and drain 204/204, fuel emptied (flag `$62a5d`) 1/1, no attractor effect 15,947/15,947, plus 9 ticks where an enemy
shot's `$333` fuel cost (`$20310`) is the only difference. A CPU watch on `$32a2e` in the three fresh captures saw 93 writes by
the instruction at `$225d6`, and the model's predicted drains equal the watch's count on 5,091/5,091 ticks. Natural play reaches
the pull (263 ticks) and the drain (204 ticks) in games 14, 45, 93 and 50; game 1's 0 hits at `$225d6` is a property of that game.
Controls on the natural set: pull >> 5 or >> 7 give 0/204 and 0/59 velocity matches, the ship before its move 3/204, drain 24
or 26 give 1/204, drain range `$800` 34/59 pull-only fuel matches, spring `$2c0` 224/20,670, vy drag >> 3 18,984/20,670, clamp
`$a0` 20,446/20,670, hit cost two 0/20, the shot bit not stored 5/19, no fuel clamp 203/204.
Labelled pokes (`cap_poke.py`, `pursuer/snaps/g014_500.snap`, 90 ticks, one poke of the ship position `$270b0..$270b4` or the
attractor's y at tick 10; the tick before it is skipped): the ship moved to within `$200`, `$100`, `$100` of an attractor gives
drain ticks 10/10, with the watch showing `$225d6` writes only after the poke and none in the unpoked control (89 ticks; the only
fuel writes there are the ship's own thrust at `$2569c`); the ship placed at D3 `$800` gives 12/12 pull-only ticks and 28/28
drain ticks once it drifted inside; the attractor's y moved below the ground gives the grounded kill 1/1; the ship placed inside
the tail's box stores `$a000` into the record 1/1. Not gated: a natural ground kill (the spring holds it up), the attractor's
death by ship contact end to end (the contact tick is the ship's death tick, skipped), the wait state's bit clearing (no waiting
record ever had bit 15 set, so the `waitkeep` control does not fail), the beam draw record and the sounds.

## The enemy shot (gated)

`Enemy_Fire` `$22e38` is called by the pursuers (`$21fc2`, `$220de`), the patrol (`$21da2` home, `$21ec8` attack) and from
`$2227c`, a call site in the two-hit pursuer's code identified by its return address only. Per call, as `fire_step` in
`py/eshot/eshot.py`: with the ship crashing (`$62a5e`) nothing happens and no random number is drawn. Otherwise the muzzle
m = (words +0, +6, +12 of the attitude matrix at A1) >> 7 each; position = the actor record's x, y, z + m, velocity = its
vx, vy, vz + m, from the record as it is at the call (already moved, thrusted and pulled). `EnemyShot_Spawn` `$203f0` sets
jitter shift 14, life `$16` (22), no life jitter and handler `$20310` and enters `$1fc90`, which draws three words from the
shared RNG (`$2706e/$27072`, `py/mpc/shot.rng_draw`), one per axis in order x, y, z; each is `asr.w #14` of the drawn word
(-2..1) and is added to both the position and the velocity of that axis. `$1fd14` appends x y z vx vy vz life handler to the
object pool (`$302f6`, at most `$177` records; with the pool full the record is dropped and the three draws are still made).
The sound `$1790c` at the end (Manhattan distance to the ship at most `$3700`) draws none. The actor walker runs before the
object walker, so a new shot is walked in the tick it is fired (life 22 becomes 21, one step of flight). A pursuer's record
is unchanged by its fire; a patrol's is not, since it steers and thrusts after.

`EnemyShot` `$20310` per walker pass, as `handler_step`: the walker takes life - 1 (negative removes the record without calling
the handler) and adds the velocity to the position; the handler adds gravity `$32a3a` to vy and stores the record. Unless
`$62a5e` is set, a ship within [-`$60`, `$60`) of the shot on all three axes is a hit: fuel `$32a2e` -= `$333`, on a borrow
fuel := 0 and `$62a5d` := `$ff`, and the record is removed. Otherwise the ground height D1 and type D3 come from `$245b8` and
d6 = D1 - y: d6 >= `$170` flies on; d6 < 0 is the ground (D3 = 8: the water splash `$1fe36`, else the explosion `$1ff8a`) and
removes it; 0 <= d6 < `$170` reads the object-map byte of the cell ((x + `$80`) >> 8, (z + `$80`) & `$ff00`): type 0 flies
on, bit 4 set (already destroyed) explodes `$1ff8a` and removes it, otherwise bit 4 is set and the shot is removed through
`$20092` when bit 5 (infected) is set, else `$20218`. A shot lives 22 passes.

Gate `eshot` (`py/eshot/gate_eshot.sh`, about nine minutes): 16 natural captures of waves 1 to 4 (2,500 ticks each from the
pursuer-corpus snapshots, games 14, 45, 93 and 50), 1,225 `$22e38` calls (128 with the ship crashing and no spawn, 1,097
spawns; callers `$21da2` 452, `$21ec8` 53, `$21fc2` 292, `$220de` 265, `$2227c` 35) and 15,497 handler passes, model against
the emulator on 334,647 of 334,647 checks:

| piece | match |
|---|---|
| spawn: inputs and jittered position, each axis; RNG after (64 bits); no draw after the spawn | 1,097/1,097 each |
| appended record x y z vx vy vz life handler; walked in the same tick | 1,096/1,096 each |
| pursuer record unchanged after its fire (x y z v); patrol position unchanged (6 provoked ones became `$21f00`) | 551/551; 537/537 |
| walker flight, 7 fields; outcome class | 15,497/15,497 each |
| stored record, 7 fields | 15,483/15,483 each |
| classes: fly 14,992, ground 418, water 35, fresh object hit 34 (30 infected branch, 4 plain), wreck 4, hit 14 | all predicted |
| hit: fuel after, `$62a5d` (3 borrows) | 14/14, 14/14 |
| fresh hit: map byte after (bit 4 set) | 34/34 |
| successor present iff predicted to fly | 14,389/14,389 (removed classes 413, 35, 30, 4, 4, 11 all absent) |
| life: life >= 1 gets one entry; life 0 gets none and is gone | 13,843/13,843; 547/547, 546/546 |

Controls: muzzle >> 6 fails 15 groups, no muzzle 15, jitter shift 13 nine, a fourth draw one (RNG 0/1,097), life 21 one
(0/1,096), hit box `$50` five (hit class 7/14), cost `$332` one (fuel 3/14), no gravity two (stored vy 0/15,483), far limit
`$180` three. 56 multi-frame rows (a ship death and respawn between two arrivals) are skipped by the pool checks. Not reached in
play: the pool full (at most 372 objects), so that branch is read; the effects after a removal (the explosion's draws and
spawns, the `$20092` provoke and award, `$20218`'s types, `$23c08`) are gated only as classes (of the 34 fresh hits, infected
cells of type nibble 1 to 3 are 24, of 4, 6 and 7 are 6; plain cells of type 5, 9 and `$b` 4). The ground height is a gate
input (D1, D3 as captured): the landscape-0 formula `exact.ground` equals it on waves 1 to 3 (14,688/14,688) and not on wave 4
(90/795), which is landscape 1 (README, "Landscape selection by wave").

## The bomber and its bombs (gated)

Model `py/bomber/bomber.py`, gate `py/bomber/gate_bomber.sh` (about 12 minutes; gate `bomber`; captures by
`py/bomber/capture_all.sh`, which stamps the bomber's own code with the RNG state and the registers).

**Bomber `$22316`**, per actor-walker pass (the walker hands the behaviour x, y, z, v, life and the ground height, and sets life
bits 15 and 13 when the ground is at or above y): bit 15 set kills it (sound, 800). Otherwise the heading is the life word's low
byte; `$1f646` (D0 = 0, D1 = heading << 8; it also rebuilds the matrix scratch `$270d4`, which the ship tick rewrites) gives vx
and vz as the sign-extended high bytes of matrix words 0 and 6, replacing the stored ones; position += (vx, vy, vz) (the walker
does not move this record); vy has a spring toward `$700` above the ground (vy -= (y - ground + `$700`) >> 5, then vy -= vy >> 4,
clamp ±`$60`). The distance is the saturating |dx| + |dy| + |dz| from the new position to the ship `$270b0`. Within `$2d00`: a
sound, and a bomb `$2086a` when `$32a48 & 7` = 0, unless the distance is above `$a00` and the ground word is `$560` (water
level). The 16th-tick test there never filters: `andi.w #$7,D4` at `$223f6` and its `bne` leave D4 = 0, so the `andi.w #$f,D4`
at `$22408` cannot branch, and over land beyond `$a00` the bomb also falls every 8th tick (a model with a real 16th-tick rule
fails 35,890/35,970). Beyond `$2d00`: 21 plants (`Infection_Burst21` `$2010a`) when `$32a48 & $f` is not 0 and the ground word
is not `$560`. `Bomber_Wait` `$222dc` clears bit 15 and counts the life word down, stored while not negative; at expiry one RNG
draw gives the heading byte (bits 16 to 23 of the old state), stored as the life word, and the same pass runs `$22316`.

**Bomb `$2086a` and `$207d6`.** The spawn is `$1fc8c` with jitter shift 13 (three draws): position += j, velocity (j0, `$30` + j1,
j2), life `$fa`, appended unless the object pool holds `$177`. The actor walker runs before the object walker, so the bomb is
walked once in its spawn tick. `Bomb_Fall` `$207d6` adds no gravity or drag. A bomb bursts when ground - y <= `$80` or within
`$400` of the ship (then fuel -= `$333`, a borrow sets fuel 0 and `$62a5d`); otherwise it is drawn only.

**Burst `$2012c`.** 31 drops when within `$2300` of the ship and the object pool holds more than `$bb` records, else 51; both
paths exit at `$20198` (the 31-drop path joins the 51-drop loop with D5 = 30), so the count shows only in the RNG draws. Each
drop `$20702`: beyond `$2300` a jittered plant `$206b8` (two draws, asr 4 on x then z, then `$205f6`), nearer a falling infection
`$205be` (three draws, asr 10, velocity (j0, -`$2a` + j1, j2), life `$80`); D0 to D2 keep the near-drop jitter from one drop to
the next (`$1fc8c` changes them and `$20702` does not restore them).

Gate, over 15 natural captures (ten of 2,500 ticks from chain games 014, 045, 093 and game 050's `p255`, `p415`; five of 800
ticks from the wave-start `landscape/gate/natural/built_N` snapshots) and the 25 pursuer captures:

| check | match |
|---|---|
| bomber record, nine fields, fly | 35,960/35,960 |
| bomber record, hatch then fly; RNG at body entry one draw from the wait | 10/10; 10/10 |
| RNG at body end (bomb 3 draws, plants 42, else 0) | 35,970/35,970 |
| bomb and plants call present iff predicted | 35,970/35,970 each |
| every predicted plant is a write to its map byte (containment) | 14,851/14,851 |
| appended bomb record | 183/183 |
| bomb outcome (fly, land, prox) from the stamps | 6,447/6,447 |
| flying bomb in the next frame's pool | 6,261/6,261 |
| burst RNG at exit (148 of 51 drops, 38 of 31) | 186/186 |
| burst pool growth (5,232 near drops); far-drop plant writes | 186/186 each |
| proximity burst fuel | 3/3 |
| bomber predicted killed | 6/6 |
| corpus: bomber fly; wait; kills; fresh bombs per tick | 46,203/46,203; 155/155; 13/13; 47,694/47,694 |

Controls: axes swapped 0/35,960 (corpus 0/46,203); spring `$6c0` 312/35,960 (corpus 73/46,203); spring shift 4 7,785/35,960; a
real 16th-tick rule 35,890/35,970; spawn jitter 12 0/183; plant jitter 5 162/14,851; always 51 drops 148/186. Thin: 3 proximity
bursts (the fuel borrow branch never ran), 12 hatches, no pool-full bomb spawn. Not modelled: the `$2f6f6` bitmap and the queue
slot `$27146` written by `$205f6`, the kill path and the contact tail; the burst's falling drops are checked by count and RNG,
not by their records after the walk.

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
the object-map cells with bit 5 (infected), a bonus from it, then `$20e74(wave)` and a restart at `$2310c` (read). With
n the counter after the increment, `inf` the infected count and `base` `$9000`, `$64ba` or `$cb89` on landscape 0, 1 or 2
(`$32a4e`), the code (`$21030..$210e6`) computes `X = max(0, max(0, base - inf) - inf) >> 2`, shifts it right by `4 - n`
when n is at most 4, and pays `8 x (floor(X / 8) + 1)` points: the loop at `$210c2` adds 8 to the score, subtracts 8 from
X and repeats while X is not negative, so even a zero X pays 8. **Gated** (`py/landscape/gate_landscape.sh`, the score read
from snapshots stopped at `$20fb4` and `$210e8`): 5 of 5 natural wave ends of game 050 match (n = 1 to 5: 1120, 1640, 1688,
8, 1336, with 595 to 31,201 infected cells; n = 5 is on landscape 1's base), and on landscape 2, poked, 13,032 at n = 10, 15
and 16 (infected 0) and 11,528 with 3000 poked infected cells; controls: infected subtracted once fails 5/5 and the poked
case, no `4 - n` shift fails 3/5 (the two it passes have n of 4 and 5, where the shift is 0).

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

`$20e74(n)` resets the actor pool and appends the groups of block `$20e34[n & 15]` (the movem at `$20e92` loads
count, first life, life step, a velocity shift and the behaviour, then the loop gives the k-th record life
`first + k x step`, y `$f100` and a random position anywhere on the map; a count of 0 ends a block). **Gated**
(`py/landscape/pool_check.py`, run by `gate_landscape.sh` on the pool right after each build): the table decodes to 16 blocks
(9 distinct), and the pool matches it record by record (behaviour, life, y) and in gravity at 5 of 5 natural builds
(counters 1 to 5, 10, 15, 18, 18, 19 records) and 4 of 4 poked builds (counters 9, 10, 15, 16: 25, 29, 29, 5 records); games
014 and 045's counters 1 to 4 match too (`chain_waves.sh`, outside the gate). Control: counter 2's pool checked as counter 3
matches 0/18. The velocity shift is 8 for chasers and 10 for every other kind. The blocks, as records per kind:

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
n = 9 (README), comparing the unmasked n. Because the table index is `n & 15`, counter 16 gets wave 0's block with gravity 6
and landscape 2 unchanged (poked, 5 of 5 records match; the landscape switch fires only at exactly 4 and 9).
No code reads the wave counter elsewhere for difficulty: its readers are this routine, the HUD and the bonus (read).

Some spawns depend on how full the object pool is, not on the wave: `$204d4` (`Smoke_Spawn`) and `$20474` (`Fragment_SpawnLong`) pick other spawn parameters
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
(bucket k from `$276fc + k x $ccc`; README "The renderer", "Depth buckets and paint order"). Their bytes are draw records of
several sizes: mostly 8-byte dots (a dot routine long, `$16fb4`, `$16ff4`, `$1735c`, ..., and the projected x and y words),
with 32-byte model records (`$26222`) for the ship, actors and model objects, and 14-, 16- and 4-byte records from the
landscape cells and the beam (the table is in the README).

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

1. The rocket: a key press (`$1f7ea` points at the bound key) with `bp 25306` and a `watch` on the target's life word for the
   bits 15 and 13 (the mothership's `Mothership_Hit` takes bit 13 as an instant kill). Whether the autopilot can ever reach and
   kill the mothership, that is what ends wave 5 in a natural game.
2. The attractor's ship contact and ground kill: a natural ground kill never occurred (the poke is the only evidence) and the
   contact tick is the ship's death tick, so the attractor's death by contact is not gated end to end ("The attractor").
3. The two-hit pursuer's ground-hit kill (900 through bit 13) has not been seen from the walker's own ground test in play (27,212
   `$2202c` record-ticks in 54,253 rows of 27 natural captures); it is gated only through a labelled poke ("The two-hit pursuer's hit paths").
4. Provoking: which of the paths `$1ffbc`, `$2004a`, `$20092` called each of the 6 gated scans.
5. The enemy shot's removal paths
   (explosion `$1ff8a`, `$20092`, `$20218`) are gated only as classes, and the pool-full drop (`$177` objects) never happened in play
   ("The enemy shot").
6. The infection rate per kind measured from the object map (bit 5 cells per tick) with the bomber removed by a poke, to test
   the reading that its bursts plant most. (The four-game census is in "The mothership and the gated chasers".)
7. Counters 9 and above (landscape 2, the mothership-heavy blocks) are reached only by a labelled poke; the bonus formula and
   the wrap at counter 16 are gated on those pokes (README Open 5 asks for a natural game that gets there).

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

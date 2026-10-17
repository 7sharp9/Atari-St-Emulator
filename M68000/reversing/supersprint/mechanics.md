# Super Sprint: race mechanics

How a race works, reconstructed from `\AUTO\SSPRINT.PRG` and proved against the emulator. Every
number below is checked by a script under `py/` (the proof table at the end lists script, what it
compares and the count). Claims marked *inferred* are read from code only.

The program is compiled C (263 `LINK A6` frames), so a Ghidra decompile exists (README, "Decompile"),
but the decompile shows A4/A5-relative globals as `unaff_A4 + N`; this doc uses the game's own
register convention:

- **`A4`** = global-state base, `$1eb44` in every race snapshot. Globals are `-N(A4)`.
- **`A5`** = thunk table base `$a304`: `jsr d(A5)` is `jsr $a304+d`, each thunk a `jmp target.l`
  (`supersprint.sym` names the ones that matter).
- Per-car arrays are word arrays indexed `car*2`. **Slots** 0, 1, 2 are the blue, red and yellow cars
  (keyboard, joystick 0, joystick 1) and can be human; slot 3 (the green car, colour from its sprite) is
  always a drone. `-3914(A4)[slot]` is the drone flag (nonzero = computer-driven).

## Architecture in one page

- `$13816` is `main`: setup, then a loop that runs the title/attract phases through the wait routine
  `$1399e` (it polls the F-keys and the joystick fire bit), and on a fire press the session flow
  `$13a5e` (select track `$19164`, join screen `$18024`, race `$be40`/`$df18`, winner's circle
  `$1a4ca`, shop `$19984`). The next track after a race comes from the permutation `-8542(A4)` =
  `[2,4,6,0,7,1,5,3]`, not from the wheel.
- The race itself is **one 320x200 screen, no scrolling**. `$be40` initialises the race (caps,
  upgrades, collision planes via `$15884`), then `$df18` runs once per frame (`$1464a` flips the
  buffers and waits for Vsync). One frame is about 11,800 emulator steps, about 8,100 of them game work.
- Per-frame order (graphics.md lists the step offsets): restore dirty rects, bonus/animation state
  (`$aa60 $abd4 $ae0e`), drone control `$eaea` for each drone slot, human control `$d4fa`, input
  `$105a0`, engine sound, HUD, `$df18` (integrate, clamp), car-car `$e8e6` (six pairs), depth sort
  `$e84c`, render `$149b8` (which also builds the collision window), obstacle test `$bda4`, surface
  sample `$b798`, smoke `$afc6`.

## Units, headings and the direction tables

Positions are fixed point. The accumulators `Q` (`-3738/-3746(A4)`, y/x) hold 1/8 pixel; the screen
position (`-3698/-3690`) is `Q/8` with truncating `divs`. `P` (`-3786/-3794`) is the previous position.
There are 16 headings; heading 0 is up, 4 right, 8 down, 12 left. The direction vectors are
**hand-tuned integer tables from INIT.DAT**, not computed:

```
dirX (-4118(A4)) = [ 0, 3, 6, 7, 8, 7, 6, 3, 0,-3,-6,-7,-8,-7,-6,-3]
dirY (-4150(A4)) = [-7,-6,-6,-3, 0, 3, 6, 6, 7, 6, 6, 3, 0,-3,-6,-6]
```

Their length runs from 6.71 to 8.49, so **speed depends on heading**: at the same speed value a car
moves 19 units/frame north/south, 22 east/west, 22.6 on the diagonals and 17.9 to 20.6 on the others
(diagonals about 19% faster than vertical; `physics/speed_vs_heading.py`, 16/16 headings). No sine,
cosine or square-root table exists anywhere in the program.

## Motion model (one car, one frame)

```
Vt = speed * dir[TGT]                 # target velocity (per axis)
V  = (V + Vt) / 2                     # one-frame lag: a turning car slides
Q += V / D                            # D = -3882(A4): 40 at upgrade level 0, 40 - 5*lvl for a human
screen = Q / 8                        # then clamp to the screen edges (x 0..302, y 0..186)
```

Every division truncates toward zero (`divs`); replacing them with floor division breaks the model
(the differential tests drop to 48/200 and 39/200). Human and drone cars use the same struct and the
same integrator; the control routines differ.

| field (off A4, word per car) | name |
|---|---|
| `-3690` / `-3698` | screen X / Y |
| `-3706` | current heading `HEAD` |
| `-3714` | target heading `TGT` (the movement direction) |
| `-3730` | speed |
| `-3738` / `-3746` | `Q` accumulators |
| `-3778` | `FLAG`: 1 = off-screen-edge/scripted flight end, 2 = crashed |
| `-3802` | waypoint index (drones) |
| `-3810` | `STUN`: control-lock / crash timer |
| `-3866` | `TURN`: spin-out rotation counter |
| `-3874` | speed cap |
| `-3882` | divisor `D` |
| `-3914` | drone flag |
| `-3954` | wrench count |
| `-4074 + 8*car + 2*item` | upgrade level of each item |

**Human car (`$d4fa`).** Only left (`0x04`), right (`0x08`) and fire (`0x80`) are read; joystick up
and down do nothing and there is no brake. Fire adds 2 speed per frame up to the cap (110 at level
0). Without fire the speed drops by `1` per frame at level 0 (more slowly with upgrades, below) and the
car keeps moving along `TGT`. Steering is a hysteresis counter `-3722`: the heading steps one of 16
directions every `thr+1` frames, where `thr = 5 - speed/40` below the minimum speed and
`speed/40 + 3` above it, floor 1; each step also costs `thr` speed while fire is held. A spin-out sets
`TURN`; while `TURN > 0` the heading rotates +1 every second frame (oil sets 32, one full turn).
`$d4fa` sets `P = Q` before integrating.

**Drone car (`$eaea`).** No steering model: see the next section. `$eaea` sets `P = Q` after
integrating, so the wall bounce (below), which restores `Q = P`, reverts a human car but does nothing
to a drone. A drone's stun lasts 5 frames, a human's 10.

## Drone AI: a racing line in a table

The line is a per-track table of **8-byte records** `(x, y, len, hd)` in world units (1 px = 8
units), base pointer `-4084(A4)`, record count `-4076(A4)` (84 slots on Track 1). `len` is the segment
length in steps of the heading's direction vector: a segment starts at `(x,y)` and ends at
`start + len*(dirX[hd], dirY[hd])`, which is exactly the next record's start (the lines close within
1 px on every track, both lanes). A drone does not steer; each frame:

1. `TGT = rec.hd & 15`, and `HEAD` snaps to `TGT` at once (unless `TURN > 0`).
2. Speed rises by 2 while below the cap; velocity is `speed*dir[TGT] + drift/20`, low-passed
   with the same `(V+Vt)/2` filter; position advances by `V/D` with `D = 40`.
3. `$f2dc`/`$f32e` tests whether the car crossed the plane at the segment's end, computed when the
   record was loaded as `(X + len*dirX, Y + len*dirY)` on the dominant axis.
4. On a crossing `wp = (wp + 2) mod count` and `$f3c2` snaps the car to the new record's exact
   `(x, y)`, zeroes the drift and computes the next crossing plane. **Drones ride on rails**: position
   is re-seeded at every waypoint, so drift cannot accumulate (live residual at most 14 units, one
   frame of travel).

Because movement is `speed*dir/D` and a segment is `len*dir` long, a segment takes `40*len/cap` frames
whatever its heading; that is why `len` is not a speed hint (the earlier reading).

The heading word of the next record doubles as a small **control language**, checked after each
advance:

| heading-word bits | effect on `wp` |
|---|---|
| `0x100` fork | odd car index `+= 2`, even car index `+= 3` (the two lanes) |
| `0x200` gate branch | `wp += -1832(A4)[hd & 3]`: 2 stays in the same-parity lane (the road that avoids the gate), 3 hops to the other lane, which runs through the gate. The value is 3 from the moment the gate starts opening until 5 ticks before it starts closing, and 2 otherwise (`$aa60`) |
| `0x400` merge/skip | `wp += hd & 0xff` |

On Track 1 slots 0 and 2 take the odd lane at record 10 (38 real records per lap), slots 1 and 3 the
even lane (34 per lap); slot 3 is the only drone on the even lane. The 4-lap race times come out of
this model exactly (`sim_lap.py`: 506/612/535 frames for three drones' laps 2-4, matching the game's
own stamps, 9 of 9). Tracks 3, 5 and 8 carry the gates (`-1294(A4)` = 0,0,1,0,3,0,0,1). Live, 40 natural
branch events on those tracks all follow `n + route[g]` (route 3 only with the gate open or opening, 2 only with it
closed or closing), and a same-snapshot A/B that flips or holds the gate state changes the lane taken in 7 of 7 events
while the null poke changes nothing (`livetests/gate_nat.py`, `gate_ab.py`). The route is latched when the branch
record is crossed: a drone that chose the gate lane just before the gate closes drives into the barrier and bounces
(5-frame stuns) until it reopens (Track 5, gate 1: 267 frames, `gate_ab.py 4 1271 2 5 220`: 84 stun frames, none with
the gate flipped or held), so lap times on gate tracks are not a pure function of the table.

## Difficulty, speed caps and the race counter

There is **no rubber-banding inside a race**. Every write to a car's cap (`-3874`), divisor (`-3882`),
turn counter and stun timer was enumerated across the whole listing (`ai_econ/acc.py`, `refs.py`), and
a live 25M-step watch from the race-start initialiser shows the cap written 7 times in the first ~1300
steps and never again. In a same-snapshot A/B (human idle vs holding fire and crashing, 14M steps, 4667
samples) two of the three drones are bit-identical for every sample; the third differs only after
physical contact. With the human leading (counters set to the pack leader's value 1000 frames ahead, optionally also
moved there and holding fire, same snapshot, frame-aligned samples) no cap or divisor is written in 1000 frames and all
three drones equal the control in 3000/3000 drone-frames per arm; no reader of the lap, sector or tile counters lies
in the drone control path (`livetests/lead_ab.py`, `lead_cmp.py`).

Caps are set once per race by `$be40` (the attract-demo initialiser `$caa8` writes the only other caps, `110 - 4*T + 4*slot`
at D = 40 for all four slots, with the drone flags 0; `livetests/demo_caps.py`) from the track `T` (0..7), the race counter `R`
(`-1748(A4)`), the slot and the car's upgrade levels `u0 u1 u2`:

```
human:  cap = trunc(11*D/4) + trunc(u1*5*D/40)            # 110 at level 0 (D = 40)
drone:  cap = 60 - 4*T + 4*slot + R                        # D = 40
```

(`ai_econ/upgrade_diff.py`, 96/96; track-by-track `select_track.py` for T = 0..7.)

**The one catch-up is across races.** `R` is cleared at session start (`$13a86`), incremented after each
race (`$13b00`, unconditional, cap 50) and decremented in the winner's circle if a drone won (`$1a7d2`), so it rises by 1
after a human win and a drone win nets 0 (live at R = 0, 5, 49, 50 each way, 8/8; 0 passes through 65535;
`livetests/r_inc.py`). It raises every drone cap by 1 and gates the hazards (below).

The four select-screen labels are **track tiers**, not AI settings: a 16-position dial, `dial >> 1` is the
track and `dial >> 2` the tier: easy (Tracks 1, 2; 0 starting wrenches), "medium 1 wrench" (3, 4),
"hard 2 wrenches" (5, 6), "v.hard 3 wrenches" (7, 8) (`ai_econ/select_track.py`, tracks/`drive_track.py`).

## Upgrades and the shop

Each human starts with the tier's wrench count and picks more up on the track. After the winner's
circle, `$19984` runs the shop for every human with more than 3 wrenches; one purchase costs 4 wrenches
and `$199de` raises an item's level (max 5). Items (carousel order `-8794` = 1,3,2,0):

| item | effect (from the `$be40` initialiser) |
|---|---|
| 0 traction | turn-delay threshold `-3890` = `trunc(cap*8/11) + trunc(4*u0*D/40)`; slower coast-down |
| 1 top speed | `cap += trunc(u1*5*D/40)`; top velocity 22 + u1 units/frame vs 12-14 for an R=0 drone |
| 2 turbo acceleration | `D = 40 - 5*u2`: same top velocity in `D/40` of the time (u2 = 5 is about 2.7x); coast rule |
| 3 "increase score level taken" | the level has no consumer: over a 1500-frame race and the winner's circle the whole global area differs from a level-0 control only in the level word, against 18, 102 and 90 words for items 0, 1, 2 (`livetests/items_ab.py`). The purchase itself pays: each of the 4 wrenches spent calls `$16084` with 750, so +3000 score, whatever the level |

Throttle released, each frame: `speed -= 1` if `row[u2][phase] == 0` and `speed -= 1` if `row[u0][phase]
!= 0` (rows at `-8476(A4)`, 6 rows x 7 words), so the net coast-down is `(7 - u2 + u0)/7` per frame
(`coast_diff.py`, 60/60 each mode). The upgrade formulas are proved against the initialiser on random
configurations; only level-0 values were confirmed in a live race.

## Collision and surface response

The collision world is built at race start (tracks.md, "Collision planes"); this is how cars use it.

**Walls.** The car blitter `$14a4a` stores, for each of the car's 12 sprite rows, `(opaque sprite pixels)
AND (wall plane at that spot)`, rotated by `x & 15`, into a 48-byte inline window at `-3682(A4)`
(`$1dce2`; **not a pointer**). `$bda4` then reads the window using a per-heading table at
`-4406(A4)` (two row offsets, two column masks) and returns 4 bits: north edge, south edge, west
column, east column. `-4438` maps the code to a push heading (1→8, 2→0, 4→4, 8→12, 5→6, 6→2, 9→10,
10→14); every other non-zero code (3, 7, 11..15: opposite sides or three edges) is `$80`, a crash.
Airborne cars (`F1 & 0x400`) leave the window zero. So collision is a by-product of drawing the car, and
the compass code selects the bounce.

**Wall bounce** (below the cap, live `wall_hit_trace.py`): `Q = P`, `TGT` = push heading, speed becomes
`speed/4 + D/2` (50 → 32), `V = 2*(speed+10)*dir`, `STUN` = 10 (5 for a drone), joystick ignored for those
frames. The heading is unchanged, so a human holding the stick drives back into the wall.

**Crash (`FLAG = 2`).** Head-on at exactly the cap speed (code == `(heading+8)&15` and speed == cap), code
`$80`, or flag 1. `$b3fc` sets the flag and a `STUN` of about the distance to the nearest screen edge, starts
the pickup-vehicle (helicopter) animation and the 26-frame explosion; `$e5d6` then respawns the car at the
last safe position (`-3754/-3762/-3770`) with zero speed. Drones always run at their cap, so head-on drone
hits crash. Flag 1 is set only at screen x <= 1 or >= 302, y <= 1 or >= 186, or at the end of a scripted
flight.

**Car-car** (`$e8e6/$e940`, six pairs): within 7 px in x and y, same level (`F1` bit 0), different
headings. Headings 7-9 apart with both speeds >= 60: both `TURN = 0x20` and they spin through each other.
Identical headings never collide. Otherwise both get a `BUMP` (25-frame cooldown): velocity `11*D/2*dir[other
heading]`, speed x3/4, `Q` reverted.

**Surface map** (`$b798`, tracks.md for the map). Two probe points per heading (`-4566`) index the 40x25
attribute map at `x/8 + (y & ~7)*5`; the cell value splits into kind (`& 3`) and payload (`>> 2 & 0x1f`),
bit 7 marks a checkpoint gate:

- kind 2: ordered lap sectors. Track 1: `0x06` (column 9), `0x0a|0x80` (31), `0x0e` (row 12), `0x12`
  (column 21, the start line). A lap counts only when the sector counter `-3850` has passed 1, 2, 3, 4 in
  order; the lap stamp goes to `-3946`.
- kind 1: payload 0 (`0x01`) halves the speed once; payloads 1 (`0x05`) and 2 (`0x09`) start a spin
  (`TURN = 0x20`, speed floored at 10); payloads 3 and 4 are pickups (`0x0d` is the wrench: `-3954[car]++`,
  cell cleared); payloads 5-8 zero the speed (the cones, `0x15..0x21`).
- kind 0 and kind 3 cells toggle the level/flag bits `F1`/`F2` (bit 0 level, bit 2 scripted flight/ramp,
  bit 10 airborne; the names are inferred).

There is no grip or grass model: off the road is the wall plane.

## Race rules, lap counting, end and scoring

- A race is **4 laps** (`-3906(A4)[car]` is the lap counter, 4 = finished). The race loop in `$be40` (`$c6f6..$ca02`) works as
  follows. A car at lap 3 whose HUD digit `-4822` is not yet 3 triggers the final-lap banner once (`$b34c(1)`: `-1802 := 1`, banner frame
  12, 180 frames animated by `$b36a`). The first car at lap 4 whose HUD digit is not yet 4 sets the finish latch (`$b34c(2)`, the three
  PSG channels silenced, `-8072` saved). Then **170 further passes** run; the control routines (`$d4fa` human, `$eaea` drone) run in
  only 5 passes (the latch pass and the first four), so the cars coast. At the end the frame counter is restored, every other car at lap 4
  is demoted to (laps 3, checkpoint `-3850` = 5, tiles `-3842` = 99) for the ranking, and the loop returns 0 (F10 returns 1 and skips the
  session tail). Live: one finisher gave 171 loop passes after the latch pass included, `$d4fa` 5 and `$eaea` 15 calls; two finishers
  demoted the second to (3, 5, 99) (`residual/live_raceend.py one|two`). The loop never tests whether a human is still racing.
- Lap counting is the ordered four-sector check above, which is why a human cannot shortcut (the human lap
  counter stays 0 until the sectors are hit in order).
- **Winner's circle (`$1a4ca`).** Rank key = `laps*100000 + checkpoint*10000 + tile count`
  (`-3906/-3850/-3842`), bubble-sorted descending; on an exact tie a human beats a drone. Lap times come from
  the stamps by descending subtraction; best and average use the first `n` laps (`n = 1` with the race timer
  if no lap was completed). A human best beats the session record `-8066(A4)[T]`. The par time is
  `(T + 15)*50` ticks; the two bars show `par - average` and `par - best` (0 if negative), rounded down to
  10. The prizes 1000/500/250/0 by rank count up into the car's persistent score (next item).
- **Score.** Each car has a 6-digit decimal score (digit bytes, `$80` = leading blank; staging `-4846(A4)`, shown via `-4870(A4)`; the same
  digit-byte form as the `SSPRINT.HSC` records), added by `$16084(car, amount)`. It gains +10 (`-4876(A4)` = `80 80 80 80 01 00`) for every
  car on each 64th frame while no car has finished, pickups add the amount at `-4900(A4) + 6*kind` (`$abd4`), and the winner's circle adds
  +10 per bar step. Live: 130/130/380 became 150/150/550 over 125 frames with `$16084` called 9 times (8 time ticks and one 150 pickup).
  Whether it feeds the high-score table is inferred from the shared format and the entry screen's "non-zero score" test.
- **Protection flags.** `-150(A4)` (failed) and `-148(A4)` (check ran) belong to the removed `BOOT.DAT` check: the patched `$101bc` leaves
  `-150 = 0`, `-148 = 1` (and a stray `D5 = 8` nothing reads). `$1000e` forces `-150 = 1` if `-148` is 0 and writes the high-score file
  only when `-150 == 0`; the session loop `$13a5e` ends after one race when `-150 != 0`. Live A/B, human finishing first: `-150 = 0` starts
  the next race, `-150 = 1` ends the session through `$13b2c`/`$1000e` with no second `$be40` (`residual/live_raceend.py tail0|tail1`).
  The campaign end is the AND of the drone flags `-3914..-3910`; `-1748` is the race counter `R`, capped at 50.
- **Elimination.** Scan ranks 0..2; the first drone and every lower rank become drones; every drone slot
  0..2 then gets wrenches = 0 and all four upgrade levels = 0. A human keeps playing only by finishing ahead
  of every drone; the session ends when slots 0..2 are all drones. If rank 0 is a drone, `R` drops by 1.
- F5 at this screen (secrets.md): forces prize animation 3 and shortens two of its frame holds.

## Hazards and pickups

All keyed on the race counter `R` (tracks.md lists the placement tables):

| hazard | appears when | effect |
|---|---|---|
| oil-class cells | from `R = 6`, `rand(R/6 + 1)` capped at 3 | blue puddle and yellow slick: speed 40 → 19; black oil: no speed change, spin set from code (not observed) |
| roaming tornado | `R > 3`, `rand(2) != 0` | random-walk roam; hit box ±7 px in x, ±8 in y around `(x, y+12)`; contact sets the spin flag `0x10` |
| cones | from `R = 16`, 50% | four cones; speed to 0, cell cleared |
| flashing 3-sign group | every third race, `(R+1) % 3 == 0` | three white discs on the road, one lit at a time by `$b24e`; `$1432e` writes each disc's pixels into the solid plane 1 (and plane 2), so a car on a lit disc bounces (T1 blob at x 22-26, y 92-95; `collide/sign_solid.py`: bounce only with the bits set) |
| gates | fixed per track (3, 5, 8) | 48x16 sliding barrier (a 5-row wall strip, 190 px, when closed); cycle 216 frames (gate 0), 396 and 576 (Track 5 gates 1, 2); `$aa60` animates gate `(R % 6) >> 1` once per frame before the control phase, re-blits the gate into planes 0-2 and sets the drone route value `-1832(A4)` read by the 0x200 waypoint records (port `collide/gateanim.py`; without it Track 3 diverges at frame 46) |
| wrench | one at a time, respawn 275-524 ticks after a pickup | cell `0x0d`, one of 20 candidate cells per track |
| bonus | first 15 candidate cells, appears 250 ticks in | worth 100/150/200/250 by growth stage; live: score 30 → 180 |

The roaming hazard's code (`$b094/$b100/$ea56`) has a scratch-register bug: the sound call in its per-car
loop clobbers A0, so with sound on it spins at most one car per frame (found by a 2-in-600 fuzz mismatch).
The hazard counts follow the rules above under varying RNG seeds: 7 values of R x 50 seeds poked into the Random seed at `$29b8`,
every roving, tile-count and blocking decision equals the rule applied to its own logged `$a666` call, 1400/1400
(`livetests/hazard_seeds.py`). With 50 seeds: roving 28 of 50, tiles at R = 12 split 16/18/16, at R = 50 29 of 50 reach the cap of 3,
blocking tiles 26 and 21 of 50 at R = 17 and 50.

## Is any of this novel?

Evidence-based, judged against the other ST games in this repo:

1. **Geometry and art are separate layers.** Walls are a vector layer of about 40 segments per track,
   rasterised and flood-filled at race start into a 1-bpp plane; the visible track is tile art.
2. **The collision test is a by-product of the blitter** (sprite mask AND wall plane, per heading, yielding a
   compass code), costing no extra pass.
3. **Drones are rail-followers** whose path table carries its own control language (fork, gate, jump).
4. **Difficulty escalates across races, not within one**: a session counter drives drone caps and hazards.
5. **Lap counting is an ordered four-sector validation** on a mutable 40x25 byte map into which pickups and
   hazards are also written and erased.

Ordinary for 1986: 16 headings, integer arithmetic, bitplane-mask collision. The heading-dependent speed
(diagonals +19%) looks accidental (a hand-tuned table that is not a circle), *inferred*.

## Proof table

All scripts live under `py/<area>/` (run from `M68000/`; `py/README.md` has the commands and the work
directory). Counts are N matching of N.

| claim | script | count |
|---|---|---|
| whole car model, natural play, 35 fields x 4 cars | `physics/test_trajectory.py 700 3` | 700/700 frames |
| `$df18` frame | `physics/test_df18.py`, `fuzz_df18.py` | 700/700, 1000/1000 |
| human `$d4fa`, drone `$eaea` control | `physics/test_ctl.py` | 300/300, 900/900 (fuzz 700/700 each) |
| `$bda4`, `$b798`, `$14a4a` window, `$e8e6`, `$e84c` | `physics/test_samplers.py` | 1800/1800 (234 and 1151 distinct inputs), 450/450, fuzz 400 x 3 seeds each |
| drone AI (`$eaea`, `$f2dc`, `$f3c2`) | `ai_econ/drone_diff.py --samples 24 --variants 012345` | 576/576 |
| drone lap times | `ai_econ/sim_lap.py` | 9/9 laps exact |
| upgrade initialiser | `ai_econ/upgrade_diff.py 24` | 96/96 |
| human coast/accelerate | `ai_econ/coast_diff.py` | 60/60 each |
| winner's circle ranking and elimination | `ai_econ/winner_diff.py 40 6` | 46/46 |
| caps written only at race start | `ai_econ/watch_caps.py fire|idle` | 7 writes in first ~1300 steps, none after |
| drone transitions on all 8 tracks | `tracks/check_lap.py T` | every transition in the decoded set |
| speed vs heading | `physics/speed_vs_heading.py` | 16/16 |

## Open

- The leading-human test pokes counters and position rather than driving a lead with a steering bot.
- The tripwire strips (bit-7 cells) are counted into `-3842(A4)`, a per-car progress counter reset at each sector crossing and read only by the HUD leader function `$13b34` and the winner's-circle key (tracks.md); they are not a hit zone.

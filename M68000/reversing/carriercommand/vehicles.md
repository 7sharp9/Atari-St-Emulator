# Carrier Command: the player's carrier, craft, repair and countermeasures

The carrier is a point mass with a heading, a speed that eases toward a target speed, and a straight-line
autopilot that turns almost in place before accelerating. Repair is a priority scheduler that shares one
capacity equally among the damaged systems at the highest priority level. An incoming missile is decoyed by
whichever flare its scan meets last within 6000 units, not by the nearest.

Proof labels as in `ai.md`. Gate: `py/units/gate_units.sh` (`gates.toml` "units"); every run resumes `c_s30.snap`
with pokes (REPL, or `stserver` for the take-off).

| Proof | Script | Count |
|---|---|---|
| carrier state per tick (x, z, heading, speed, target speed, yaw, fuel, island proximity, flags, lock counter), manual rudder with one grounding | `carrier_proof.py` | 150/150 |
| the same, autopilot across open sea (gate: first 600 ticks) | `carrier_proof.py` | 600/600 (1950/1950 in the full run) |
| arctangent `$aae6` over a 23 x 23 input grid | `atan_grid.py` | 529/529 |
| repair calls, three systems at HIGH while the repair system itself is repaired | `repair_proof.py` | 10/10 |
| repair calls, HIGH finishing and repair moving to MEDIUM | `repair_proof.py` | 12/12 |
| flare capture: 6000 captures, 6001 does not, the later slot wins, no flare keeps the carrier | `flare_test.py` | 5/5 cases |
| Manta take-off per tick (phase, speed, altitude, pitch, heading, deck offset, world x and z, the hand-off to flight), carrier at rest and carrier turning; eleven of thirteen constants break when nudged in the turning run | `takeoff_proof.py` | 42/42 and 42/42, controls 11/13 |

## 1. Carrier motion `$1e4a0`

Called once per main frame from `$1ca7c`. The control block is `$640..$65e` and the carrier entity `$5e95a`
(+6 heading, 65536 to the turn, so bearing 005 is 1000; +10 x; +14 altitude; +18 z; +60 the island it is near).

| Field | Meaning |
|---|---|
| `$642` | flags: bit 0 autopilot, bit 1 course set, bit 7 braking |
| `$643` | autopilot phase (0 after a grounding) |
| `$644` | yaw rate, +/-255 |
| `$646`, `$648` | speed, target speed |
| `$64c` | island proximity |
| `$64e` | control lock counter after a grounding |
| `$650`, `$654` | destination x, z |
| `$658` | cruise speed |
| `$cf8` | fuel (long) |

Per tick (proven by the 150, 600 and 1950-tick matches):

```
speed   += max(1, (target - speed) >> 5) toward target
heading += yaw / 6;  if braking: yaw -= yaw >> 3
velocity = rotate((0, speed), heading)            # $19e0a, through the sine table
velocity *= 2 when not near an island (+60 == 0), no own craft nearby ($65c) and $65e clear
every 16th tick: fuel -= 4 * |speed|;  no fuel forces target speed 0
```

Engine damage caps the speed (`$1e774`): forward at most `min(engine effect >> 1, $70)`, `$3c` near an island,
reverse at most `-(effect >> 3)`; with the engine effect at 214 the speed held at 107 (the engine run, 600/600).

**Autopilot** (`$1e6ca`). Each tick the steering error is `atan2(dx, dz)` to the destination minus the heading.
If it exceeds `$100` (1.4 degrees) the target speed drops to `$10`, so the carrier turns nearly on the spot and
then accelerates. The yaw demand is error / 4 clamped to +/-255, and the actual yaw moves toward it by at most
32 per tick (`$19e54`). Within Chebyshev distance 2000 the cruise speed is capped at `$20`; below 1000 it has
arrived: course bits cleared, brake set. The 1950-tick run arrived and coasted to (+302385, +201558) for a
destination of (+300000, +200000).

**There is no obstacle avoidance** (inferred from code: the autopilot reads only its destination and heading).
Islands are handled after the move: the proximity is the Chebyshev distance to the island's box (half-extents
at +48/+50) minus 10000, over 256 (`$1e5e0`). A negative value grounds the carrier: speed zeroed, reverse
thrust of 32, controls locked for 50 ticks (`$64e`), autopilot phase cleared. The manual run grounded once, at
tick 71, and matched through it.

## 2. The arctangent `$aae6`

`$aae6` returns `atan2(D0 = dx, D1 = dz)` with 0 along +z and 65536 to the turn; `$aae2` first halves both
inputs until they fit in a signed word. It folds the vector into one octant, forms the ratio r = min/max in Q15
with `divs`, and divides `r << 8` by an entry of the 128-word table at `$3864`, which holds about
`4096 pi r / atan(r)` (inferred by fitting; within -45/+28 of the stored values). So the angle is the ratio
divided by a tabulated ratio-to-angle factor: no polynomial and no CORDIC. Proven 529/529 over a grid; within
0.15 degrees of the exact angle over 200,000 random inputs. The final `lsl #4` makes every result a multiple of
16, so the angle has 4096 steps to the turn (0.088 degrees each). Of the worst error, 27 units at radius 30000,
up to 16 is that rounding and at most 13.7 the table: one factor serves each 1/128 of the ratio range
(`py/infographics/gen_atan.py` computes both from the port). About twenty routines call it, including the
autopilot and missile guidance.

A game bug falls out of the 68000: `neg.w` of -32768 is still -32768, so when either input is exactly -32768 the
fold goes wrong and the result is pinned at `$6000`, `$a000` or `$e000` whatever the other input, or `$8000` and
`$c000` when the other is 0. The error is up to 45 degrees off the axes and 90 degrees on them: 27 of the grid's
529 cases, each matched by the port.

## 3. Repair `$1713c`

The ten carrier systems have 8-byte records at `$af0`, in the order of the strings at `$b51e..$b5a4`: ENGINES,
RADAR, COMMUNICATIONS, OBSERVATION TURRET, LASER CANNON, FLARE LAUNCHER, SURFACE TO SURFACE MISSILES, LIFT,
AUTOMATIC REPAIR SYSTEMS, SUPERSTRUCTURE. Fields: +0 level, +2 maximum (4000; turret 3000, laser 2000, repair
systems 1500), +4 priority (0 HIGH, 1 MEDIUM, 2 LOW), +6 effect.

Every 10th economy pass (about every 6M steps):

```
level = highest priority with any damaged system          -> $b58 ("CURRENT REPAIR LEVEL = ...")
n     = number of damaged systems at that level            -> $b5c
rate  = (150 * repair-system effect $b36 >> 8) / n         -> $b5a
each damaged system at that level: level += rate, capped at its maximum
lower priorities get nothing until this level is complete
```

Damage to the Automatic Repair Systems slows every repair, and repairing them speeds it up: in the 10-call run
the rate rose 43, 45, 46, 48, 49 while the repair system mended, then became 75 when it finished and three
damaged systems became two; the 12-call run moved from HIGH to MEDIUM while LOW stayed untouched (proven).

The effects are recomputed every frame by `$171d4` through the table at `$171ee`: ENGINES and LASER give
`256 (2 level / max - 1)` (nothing below half health, `$100` at full; `$17216`); the systems read as switches
give `$ff` above half health (`$1723c`); the repair systems and superstructure are linear, `level * 256 / max`
(`$1724e`). Proven within the same 22 calls. RADAR `$afe`, COMMS `$b06`, FLARE `$b1e`, SSM `$b26` and LIFT `$b2e`
are the effect words other code reads.

The craft hangars use the same equal share (inferred): `$17278` (Mantas) and `$1730e` (Walruses) give 400
points per call split among the slots being repaired, hull capped at `$fa0`.

## 4. Missiles and flares

A homing missile (type 17, handler `$1a3b2`) in state 2 re-targets every 5 calls. It scans flare slot 17
(`$5f21a`) and then slot 18 (`$5f35a`); any active flare (byte +1 bit 0) within Chebyshev horizontal distance
6000 of the missile becomes its target (+30). The carrier's own distance is never compared, and the later slot
overrides the earlier.

Proven with the carrier 600,000 away: a flare at 6000 is taken at the first scan, one at 6001 only at a later
scan once the missile has closed, one at 7000 at the third; with flares at 3000 and 5000, or 7000 and 5000, the
missile takes slot 18; with none it keeps the carrier.

Inferred from code: capture is sticky (only another flare in range replaces it); a dead target sends the
missile back to state 1, flying straight for up to 100 calls; guidance is two arctangents (yaw, then pitch after
rotating by -yaw) with both slewing at most `$800` (11.25 degrees) per call, speed `$fa` per call, life 100
calls. A flare (`$12f06`) needs stock `$c7e`, the reload timer `$114c` at 0 and a working FLARE LAUNCHER
("Flare launcher too damaged" otherwise); it takes slot 17 or 18, so at most two are aloft, and starts at the
carrier at altitude 500 on a random heading.

## 5. Craft

After the carrier, `$1ca7c` updates the Mantas (`$1cab4`: 4 slots of 52 bytes at `$498`, paired with entities
`$5df5a + 320 i`), the Walruses (`$1da24`: 4 slots at `$572`, paired with `$5e45a + 320 i`) and the flares
(`$1ef5c`). The pairing is proven by the cheat teleport at `$3ec2..$3f48`, which moves each craft whose slot
says autopilot and destination to its slot destination, and by the launch below.

Manta slot fields: +0 flags (bit 0 autopilot, bit 1 destination set, the carrier's convention), +1 state (0 in the
hangar, 3 on the lift, 8 from the deck on, observed), +2 and +4 the roll and pitch stick (+/-255), +6 speed, +8 the
speed demand, +10 fuel (`$7fff` at start), +20 hull (`$fa0`), +28 deck state, +29 its phase, +30/+38 destination x
and z, +34 target altitude, +42 cruise speed. Manta entity fields: +4 pitch, +6 heading, +8 roll, +10/+14/+18 x,
altitude and z (longs), +60 the island block it is near (below). The Manta update dispatches on +28 at `$1cf94`: 0 the
idle value in the hangar and on the lift, and under autopilot the deck landing (`$1cfc2`), 1 on deck (`$1d200`), 2
take-off (`$1d22c`), 3 airborne (`$1d354`), 4 runway taxi (`$1d4ac`), 5 parked on a runway (`$1d5f8`), 6 runway
take-off (`$1d6a8`); the table was decoded from the raw bytes, which the listing shows as data. `$dcc` is the
Manta on the deck (negative when empty) and `$dca` the lift's state.

**Lift and launch (proven by driving them).** The lift command `$11386` (Manta index from `$dc8`) needs a working
LIFT, an idle slot, an empty deck and the lift at rest; it sets +1 to 3 and starts the lift. From `c_s30` the Manta
rose from altitude 20 to 180 and was on deck with the lift stopped after 21 main ticks. The launch command `$11af6`
refuses while the lift is moving (`$dca` nonzero, "No aircraft available for launch"). With no destination set it
gives one (`$11b74`): 6000 units behind the carrier along its heading, at target altitude `300 (i + 1) + 500`
(computed (-570, -5973) from the carrier for heading `$3e8`, as the snapshot holds). It then sets +28 to 2.

**Take-off `$1d22c` (proven, `takeoff_proof.py`).** While on the deck and taking off, the Manta's position is a
deck offset (+28/+30 of the entity) rotated by the carrier's heading and added to the carrier's position
(`$1d908`, the inverse rotation of `render.md` section 2), and its heading is the carrier's. Per tick:

```
phase 0: altitude += 2;  at altitude >= 200: phase 1, speed = 0           # rise off the lift
phase 1: speed = min(speed + 8, 60);  deck z += speed;  at deck z >= 650: phase 2     # roll
phase 2: pitch = max(pitch - 240, -1655);  altitude += 10;  deck z += speed            # rotate and climb
         at deck z >= 2000: airborne (+28 = 3), slot pitch = pitch / -14, speed += carrier speed,
                            deck freed ($dcc), entity +1 bit 2 cleared, flag bit 0 cleared if +51 is set
```

From `c_s30` the take-off takes 43 ticks from the launch command (10 rising, 10 rolling, 23 climbing off the bow;
`scratchpad/carrier/manta/manta_snaps.log`, `launch` to `T42`) and leaves the deck at
altitude 430, pitch -1655 and speed 60 plus the carrier's. The model matches the 42 ticks `takeoff_proof.py` checks, which start
after the first update, 42/42 with the carrier at rest and 42/42 with it turning and accelerating (speed 48 at take-off, so the Manta leaves at 108). In the turning run each
constant nudged by one breaks at least one tick, except the two deck thresholds (at rest 9 of 13 break: the
carrier-speed and carrier-heading terms cannot): the Manta moves 60 a tick, so the data pins 650 to
(594, 654] and 2000 to (1974, 2034], and the values are read from code.

**Airborne flight `$1d354` (proven, `flight_proof.py`).** Under autopilot the state handler sets the stick and the
speed demand, then joins the shared flight code at `$1ccb0` (the ground checks below, which do nothing at altitude 150
or more), fuel at `$1ce56`, speed at `$1d880`, attitude at `$1d940` and integration at `$1cf58`. Per tick, with
`toward(v, t, n)` moving v toward t by at most n (`$19e54`) and `decay(v)` = v - v/8, at least 1 (`$1e490`):

```
destination set (+0 bit 1):
    dalt = target altitude - altitude;  pitch stick toward (0 if |dalt| < 20 else clamp(dalt, +/-150)) by 10
    d = max(|dx|, |dz|) to the destination;  demand = cruise (+42), or 50 within 2000
    d >= 600:  roll stick toward clamp((atan2(dx, dz) - heading) / 10, +/-255) by 32        # $aae6, section 2
    d <  600:  clear the destination flag and circle from this tick
circling ($1d35c):
    pitch stick: decay above altitude 500, else toward 150 by 20;  demand 70;  roll stick toward 128 by 16
speed ($1d880):  demand clamped to [50, min(hull / 16 + 50, 250)]  (lower bound 0 under the invulnerability
                 cheat or in the landing states);  speed toward demand by 4 up, 16 down
attitude ($1d940): roll = -25 * roll stick;  pitch = -14 * pitch stick;  heading += 16 * roll stick / 6
move ($19e2e):   (vy, h) = rotate (0, speed) by pitch ($a16c);  (vx, vz) = rotate (0, h) by heading ($a12c)
                 x += vx;  altitude = min(altitude + vy, 3500);  z += vz
```

The roll stick is therefore also the turn rate: a full 255 turns the heading by 680 a tick, so the circle at 128
takes about 192 ticks. Three runs from `m_takeoff.snap` match every field of slot 0 and its entity on every tick:
the launch flight 300/300 (climb from 430 to 781 against the target 800, turn back to the point behind the carrier,
destination cleared at tick 185, then circling), cruise 200 with a target of 4000 400/400 (the 3500 ceiling and
deceleration at the destination), and hull 256 with a target of 300 400/400 (the hull speed limit, descent, circling
below 500). Nudging each constant by one breaks a tick in at least one run for 22 of 26; the four left are thresholds
the runs never sit on (2000, 600, 500 and the 250 speed cap), and their values are read from code.

**Fuel (proven, `fuel_proof.py`).** The main frame counts `$8e8` modulo 16 and sets `$8fb` when it wraps
(`seq $8fb` at `$1ca6e`, the only writer in a whole-image scan for the word `$08fb`; the readers are `$1ce56`,
`$1d200`, `$1dcda`, `$1e560`). On those frames, `$1ce56` takes `(speed << 4) / 50` (word shift, `divu`), plus 256 when
the hull is 500 or less, from the fuel, floored at 0: about 1.2 a tick at speed 60 with a sound hull, 17 with a
damaged one. 300/300 ticks with a full hull and 300/300 at hull 256; the same rule applied every frame matches 18/300.
At zero fuel the Manta drops out of autopilot and falls (`$1cea6`, not driven).

**Ground contact and runways (read from code, not yet driven).** Entity +60 points at an island block (`$62cda` or
`$63cec`), which `$1b424` attaches when the craft is within 130,000 of an island and re-checks every 24 to 31 ticks
(live in `m_takeoff.snap`: the Manta and the carrier both hold `$62cda`). From `$1ccb0`, at altitude 35 or less the
craft loses 2000 hull a tick (`$1d968`, which destroys it at 0 through `$1c788` and `$18e30`). Between 36 and 149,
inside the island's box: if the block's record 1 is an airstrip (type `$24`, "has landed on runway"), the position
in the runway's frame within 200 across and -4000 to 2000 along, both sticks within 120 and 80, heading within 4000
of the runway's and speed at most 100, the Manta lands (+0 = 1, +28 = 4); a wrong place costs 500 and a bad approach
100, with the altitude floored at 145 and the pitch stick pulled toward 100 by 30 and the roll stick shaken by the
RNG. Over open sea between 36 and 149 nothing happens.

**Landing (read from code, not yet driven).** The land command `$11bf6` (within 16,384 of the carrier, lift at
rest, deck empty) sets +28 = 0 with autopilot. State 0 then flies in at altitude 570, speed 65 (200 beyond 3500),
steering at a tenth of the heading error; within 600 of the carrier it matches the carrier's velocity, turns to its
heading, slides to deck offset (0, 250) and descends by 10 to 180, giving +28 = 1 with pitch -694; the lift
(`$11f3c`, `$1e838`) then stows it (+28 = 0, +1 = 0). The abort command `$11e76` returns it to state 3 while the
phase is 3 or less. On an island airstrip, a touchdown (above) gives state 4, which taxis in the runway's frame to
(0, 2650) at speed 64 and altitude 120, then to a bay by slot (x = 600 i - 900, z 3270 or 3720) at speed 8, turns
round and settles to altitude 100: state 5, parked, refuelling 64 a tick and destroyed if more than 260,000 from
the carrier. A launch request (slot +0 bit 5, set from the UI at `$12ecc`) gives state 6 if the airstrip still
stands ("Runway damaged - cannot take off" otherwise): it taxis to (0, 2700) at speed 12, climbs toward 155 while
rolling to (0, -3000), throttles to 200 once lined up, and becomes airborne (+28 = 3) with a holding point 6000
along the runway if it has no destination. Speed has no minimum in states 4 to 6. Every craft in states 4 to 6
reads entity +60 without a null check.

Inferred from code:

- Manual flight takes the stick from the mouse deltas `$1262`/`$1264`, clamped to +/-255; the throttle keys
  change +8 by 16.
- A Manta more than 200,000 from the carrier, and not within 200,000 of the relay drone `$ddc` while COMMS
  works, raises the radio messages at `$1d859` (and `$1d870` beyond 260,000). A Manta within range sets `$65c`,
  which stops the carrier's open-sea speed doubling.
- Hits (`$1bc1c` Walrus, `$1bc5e` Manta) subtract `$752` from the hull, skipped while cheat invulnerability
  `$1186` is set.
- Entities are created by `$18f9a` (type at +2, collision half-extents at +48..+54 from the 4-word table at
  `$19092`); the Walrus launch (`$1201a`) uses type 6. Walrus slot +28 is its destination.

## 6. Open

- Drive the landing: the land command `$11bf6` from `m_air.snap` through state 0 to the deck and the lift, and a
  runway touchdown on an airstrip island (states 4 to 6), each per tick as `flight_proof.py` does; then the ground
  contact damage below altitude 150. The lift's own motion.
- The Walrus launch and driving.
- An autopilot run with an island across the course, to show the carrier grounding instead of steering round.
- Walrus fuel (+8) and the "Fuel Transfer" / "Set Fuel Priorities" screens (the Manta's burn is proven, section 5).

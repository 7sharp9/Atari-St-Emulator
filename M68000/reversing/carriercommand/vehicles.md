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
hangar, 3 on the lift, 8 from the deck on, observed), +6 speed, +10 probably fuel (`$7fff` at start; it fell 12 on the
one tick on deck and 356 over the first 300 airborne ticks, unmodelled), +20 hull (`$fa0`), +28 deck state, +29 its
phase, +30/+38 destination x and z, +34 target altitude. The Manta update dispatches on +28 at `$1cf94`: 0 hangar
and lift, 1 on deck (`$1d200`), 2 take-off (`$1d22c`), 3 airborne (`$1d354`), 4 to 6 not yet seen. `$dcc` is the
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
(594, 654] and 2000 to (1974, 2034], and the values are read from code. In the observed flight the Manta then climbed
to 781, turned back to the point behind the carrier, cleared its destination flag about 200 ticks after take-off and
circled (one run of `py/units/manta_snaps.py`, not modelled).

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

- The Manta's airborne flight (`$1d354`, +28 = 3) and terrain following: `scratchpad/carrier/manta/m_takeoff.snap`
  is the first airborne tick. The landing states 4 to 6, and the lift's own motion.
- The Walrus launch and driving.
- An autopilot run with an island across the course, to show the carrier grounding instead of steering round.
- Craft fuel (Manta +10, Walrus +8) and the "Fuel Transfer" / "Set Fuel Priorities" screens.

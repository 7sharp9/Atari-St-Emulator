# takeoff.svg: facts and sources

Figure: `gen_takeoff.py` writes `scratchpad/carrier/infographics/takeoff.svg` (PNG: `rsvg-convert -z 2 takeoff.svg -o takeoff.png`).
It drives the two runs of `py/units/takeoff_proof.py` through `stserver` from `c_s30.snap` (at rest; turning with
`$644 = $40`, `$648 = $30`), reads slot 0 (`$498`) and entity `$5df5a` at every entry of `$1cab4`, and also the state
just after the launch call. It checks `takeoff_proof.step` against every tick and exits without drawing if one differs.
Every dot is a captured game value; the only model output drawn is the red frozen-heading variant in panel B. Doc:
`vehicles.md` section 5 (take-off), section 1 (carrier motion), section 2 (angle convention).

| fact in the figure | source |
|---|---|
| take-off in three phases on slot +29: rise +2 to 200, roll +8 to 60 until deck z 650, pitch -240 to -1655 and altitude +10 until deck z 2000 | vehicles.md 5; `takeoff_proof.step`; matched per tick here |
| position = carrier + deck offset rotated by the carrier heading (`$1d908`); Manta heading = carrier heading | vehicles.md 5; `deck_to_world` |
| hand-off: speed += carrier speed, slot pitch = pitch / -14 (118), state 3 | vehicles.md 5; captured `s4` = 118, `v` = 60 / 108 |
| 43 ticks from launch: 10 rise, 10 roll, 23 rotate and climb | counted from the captured phases (launch state included) |
| 42/42 per tick in both runs from the first update entry | `takeoff_proof.py` (rerun: 42/42 and 42/42); same count recomputed here |
| 43/43 in both runs including the launch tick (alt 180 to 182) | computed here: `step(launch state)` equals the first entry |
| the carrier-frame values (phase, deck x and z, altitude, pitch; speed before hand-off) are identical in both runs | compared here, asserted |
| deck x offset stays 0; deck z 250 at launch, 2034 when airborne; altitude 180 to 430 | captured |
| pitch -694 on the lift and through the roll; floor -1655 reached at deck z 954 | captured |
| -1655 = 9.1 degrees, -694 = 3.8 degrees; strokes drawn nose-up for negative pitch | inferred: pitch read as 65536 to the turn like heading (vehicles.md 1); nose-up from the climb |
| climb path atan(10/60) = 9.5 degrees | computed |
| turning run: carrier heading +10 a tick, 1210 to 1640 (2.4 degrees); carrier speed 21 to 48 | captured; +10 = 64 / 6 per vehicles.md 1 |
| Manta heading equals the carrier heading of the previous entry, every tick | captured, checked here |
| panel B axes: along / across the carrier heading at launch, origin the carrier at launch; across drawn 6.5 times the along scale | presentational transform; forward = (sin h, cos h), 0 along +z (vehicles.md 2), confirmed by the at-rest track (across within -2.2..-0.2 over 1784 along) |
| turning: Manta leaves the deck 3668 along, +98 across; carrier moved 1684 along, +21 across; at rest 2033 along | computed from captured positions |
| frozen-heading variant: 81 units from the game at the last tick (across 17 vs 98) | model variant (`deck_to_world` with the launch heading), labelled "not the game" |
| constants nudged by one break a tick: 11 of 13 (turning), 9 of 13 at rest; unbroken: 650 and 2000 | recomputed here with `takeoff_proof.P0`; same as `takeoff_proof.py` output |
| thresholds pinned by the data to (594, 654] and (1974, 2034] | recomputed here |
| last on-deck tick moved 107.2 over the sea (carrier 47.5); hand-off speed 108 = 60 + 48 | computed from captured positions; hand-off captured |

### Prose added for readers new to the game (lead, captions, "How we know")

| claim | source |
|---|---|
| the player's carrier launches craft; the Manta is an aircraft that comes up a lift, rolls along the deck and climbs off the bow | vehicles.md 5 (lift, launch, take-off; the launch refusal message "No aircraft available for launch") |
| until it leaves the deck the Manta is a deck offset rotated by the carrier's current heading and added to its position | vehicles.md 5 |
| a tick is one main-loop update; headings 65536 to the turn | vehicles.md 5 ("main ticks"), 2 |
| the two runs give identical carrier-frame values, all 43 ticks | table above (asserted by the script) |
| 98 across, frozen heading 81 away, hand-off 60 + 48 = 108 | table above |
| slot +28 deck state (2 = taking off), +29 phase | vehicles.md 5 (slot fields) |
| nudged-constant method and the threshold intervals | vehicles.md 5; table above |
| both runs from c_s30 (carrier at Vulcan) with the game's own lift `$11386` and launch `$11af6`; turning run pokes yaw `$644` and target speed `$648` | `gen_takeoff.py` docstring; README.md snapshot table |
| pitch units and sign inferred | table above |

## Flags

- Tick count (now settled: `vehicles.md` 5 gives 43 ticks, 10 rising, 10 rolling, 23 climbing, as this figure does).
  It said "the take-off takes 42 ticks (9 rising, 10 rolling, 23 climbing)". From the launch
  command it takes 43 updates with 10 rising: `takeoff_proof.py` starts at the first `$1cab4` entry after the launch,
  when the first update (altitude 180 to 182) has already run. `manta_snaps.log` shows the same (`launch` at 180,
  `T0` at 182, `T42` airborne), and the model matches that tick too (43/43 here). The "42/42" proof count is right as
  a count of checked transitions; the phase breakdown and "takes 42 ticks" are off by the uncounted first tick.
- "Eleven of thirteen constants break when nudged" holds for the turning run only; at rest it is 9 of 13
  (`add_carrier` and `follow_heading` cannot break with a still carrier). The doc's sentence does not say which run.
- The doc does not give the starting pitch: the Manta sits on the lift and rolls at pitch -694 (3.8 degrees), so the
  rotate phase takes 5 ticks to reach -1655 (-694 - 4 x 240 = -1654, then the floor). Where -694 is set (lift or entity creation) is not
  traced.
- Pitch units and sign (65536 to the turn, negative nose-up) are inferred, not proven; the figure says so.
- Turning-run carrier speed at the launch is 21 (state read just after the launch call); the first update entry reads
  22. Both are captured values; the figure quotes 21.

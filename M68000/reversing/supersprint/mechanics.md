# Super Sprint — race mechanics and drone-car AI

Reverse-engineered from a live Track-1 race (66th pass). Every address below is a
RAM address in the loaded `\AUTO\SSPRINT.PRG` image; register `A4` is the game's
global-state base pointer (`$1eb44` in the traced race — the `-NNNN(A4)` offsets
are stable, the absolute addresses shift with each load). All per-object arrays
are indexed by `car_index * 2` (word arrays), 4 slots: the 3 on-track cars plus
one spare.

Method: reach a race (`ss_attract.snap` → `kbd fe 80` → SELECT TRACK →
`kbd 2a aa` + `kbd fe 80` join → countdown → race), snapshot, then
`watch <addr>` each candidate field for one frame and read back the writing PC,
plus `trace_cfg.py` over a 200-frame window for the per-frame call tree.

## Per-frame update — `$df18`

`$df18` is the race main loop, called once per VBL. Per frame it runs:

| call | addr | times/frame | what |
|------|------|-------------|------|
| `jsr $ea56` | | 0–1 | proximity check, only when `-1776(A4)` set |
| `jsr $e8e6` → `$e940` | | 1 | **car-to-car collision** — every pair, `|dX|≤7 && |dY|` small → set touch flag |
| `jsr $e84c` | | 1 | **sprite depth sort** — `exg`-network sorts the 4 cars by screen Y for back-to-front draw |
| per car ×4: `jsr $eaea` (via thunk `348(A5)`→`$149b8` render is separate) | | 4 | **per-car control** (below) |
| per car ×4: `jsr $b3fc` | | 4 | off-viewport wrap / respawn (`-3754`/`-3762(A4)` world pos vs `$a0`/`$140`, `$64`/`$c8` bounds) |
| per car ×4: `jsr $bda4` | | 4 | **obstacle collision** vs the collision map |
| per car ×4: `jsr $b798` | | 4 | **track-surface sample** at the car's position |

`$df18` itself integrates motion: `pos += vel/8` — `move.w -3794(A4)[i],D0 / divs #8 /
add to -3690(A4)[i]` for screen X, same with `-3786`/`-3698` for Y (`$e02c`–`$e084`).

## The per-car state struct (word arrays off A4)

| offset | addr (this race) | meaning |
|--------|------------------|---------|
| `-3690(A4)` | `$1dcda` | **screen X** (0…302, clamped in `$df18` at `$df60`) |
| `-3698(A4)` | `$1dcd2` | **screen Y** (0…186, clamped at `$dfb0`) |
| `-3706(A4)` | `$1dcca` | **current heading** (0…15, 16 directions) |
| `-3714(A4)` | `$1dcc2` | **target heading** — the AI/input output |
| `-3730(A4)` | `$1dcb2` | **current speed** (ramps +2/frame toward the cap) |
| `-3746(A4)` / `-3738(A4)` | | fixed-point world-position accumulators (X/Y), integrated at `$f0a0`+ |
| `-3754(A4)` / `-3762(A4)` | | world position >> 3 (used for the viewport-wrap test in `$b3fc`) |
| `-3778(A4)` | `$1dc82` | **edge / wall-hit flag** (1 = clamped to a bound this frame; render + physics skipped) |
| `-3802(A4)` | `$1dc6a` | **current waypoint index** (drone AI) |
| `-3810(A4)` | | **stun / spin-out timer** (>0 → recovery path in `$eaea`) |
| `-3866(A4)` | | heading-turn-rate accumulator (`$ee..`; snaps heading to target when it runs out) |
| `-3874(A4)` | `$1dc22` | **per-car target/max speed cap** (`$3c/$6e/$44/$48` in the traced race) |
| `-3882(A4)` | | per-car motion divisor (`divs` at `$f0b2` — a drag / speed-scale term) |
| lap counters | `$1dc02` / `$1dc06` / `$1dc08` | drones' lap counts; player `$1dc04` stays 0 (checkpoint-enforced) |

## Drone AI — waypoint / racing-line follower

Per-car control is `$eaea` (reached from `$df18` via the `348(A5)` thunk chain →
`$a460` → `$149b8` is the *renderer*; `$eaea` is called for the control step).

```
$eaea:  if -3810(A4)[car] (stun timer) > 0:
            decrement it, run spin-out recovery ($eb32+: perturb heading/speed
            through the -4118(A4) direction table), return
        else fall through to $ec52  ── the waypoint follower
```

### `$ec52` — steer toward the current waypoint

```
$ec52:  wp   = -3802(A4)[car]                 ; current waypoint index
        rec  = [-4084(A4)] + wp*8             ; -4084(A4) = waypoint table base ($55c3c)
        -3714(A4)[car] = rec.word[3] & 0x0F   ; TARGET HEADING = waypoint's stored heading
        jsr $f2dc  →  D0                      ; "have we crossed this waypoint?" (2 = yes)
        if -3730(A4)[car] < -3874(A4)[car]:   ; speed below the per-car cap
            -3730(A4)[car] += 2               ; accelerate
        if reached (D0 == 2):
            -3802(A4)[car] = (wp + 2) mod [-4076(A4)]   ; advance (step 2!) and wrap
```

- **`-4084(A4)`** = pointer to the waypoint table (`$55c3c` this load).
- **`-4076(A4)`** = waypoint slot count = **`$54` (84)**; the index steps by **2**, so
  **42 active waypoints** for Track 1 (the odd slots are zero-filled padding).
- Waypoint record — 16 bytes (`wp*8` addressing, index stepped by 2):
  | offset | meaning |
  |--------|---------|
  | +0 word | world X target |
  | +2 word | world Y target |
  | +4 word | segment speed hint (9…110) |
  | +6 word | low nibble = heading (0…15) to steer while approaching this waypoint |
  | +8…+15 | zero |

  First few Track-1 waypoints (world units, ~800 × ~1400 track):
  `(1299,326 spd110 h12) (419,326 s9 h11) (356,353 s9 h10) (302,407 s9 h9)
   (275,461 s12 h8) (275,545 s20 h7) (335,665 s61 h8) (275,965 s18 h7)
   (329,1073 s3 h8) (329,1094 s16 h8) (329,1206 s9 h7) (356,1260 s9 h6)
   (410,1314 s9 h5) (473,1341 s9 h4) (545,1341 s9 h3) (608,1314 s13 h2) …`
  — a closed loop of position + heading + speed samples tracing the racing line.

### `$f2dc` — "reached the current waypoint?"

```
q = (target_heading + 2) & 0xF, then >> 2           ; travel quadrant 0..3
D6 = -3738(A4)[car], D7 = -3746(A4)[car]            ; world-position accumulators
wpx = -3962(A4)[car], wpy = -3970(A4)[car]          ; this waypoint's X / Y target
$f32e: by quadrant, compare the car's position against wpx or wpy on the
       dominant axis of travel; return 1 (→ caller returns 2) once it has
       crossed that waypoint's plane.
```

### Heading turn — `$ee86`…`$ef12`

Current heading `-3706(A4)[car]` is turned toward the target `-3714(A4)[car]`
one step at a time, rate-limited by the `-3866(A4)[car]` accumulator (`+= 2` per
frame; when it saturates the heading snaps to the target — `$eeea`/`$ef12`).
Speed → velocity uses `-4118(A4)` (a per-heading direction-vector table) at
`$eb32`+ and the `$f0a0` integrator; screen coords are `world >> 3` (`divs #8`).

### Collision / surface response

- **`$b798`** — samples the track-surface map `[-1910(A4)]` at the car's
  position (offset from `-4566(A4)` per-heading table): road vs grass vs wall,
  feeds grip / off-track handling.
- **`$bda4`** — tests the car's footprint against the flood-filled collision
  bitmap at `-3682(A4)` using per-heading masks from `-4406(A4)`; returns a
  4-bit "blocked on this side" code.
- Car-to-car: `$e8e6`→`$e940`, `|ΔX| ≤ 7` and small `|ΔY|` → both cars flagged.
- A wall/edge hit sets `-3778(A4)[car] = 1` and (for a real crash) `$b3fc` sets
  it to 2 and seeds the `-3810(A4)` spin timer, routing `$eaea` to recovery.

## Rubber-band catch-up?

**Not found on the speed path.** `-3874(A4)` (the per-car speed cap) took **zero
writes across 250k steps of racing** — it is set once (at race start / per lap)
and then fixed. In the traced race the four caps were `$3c $6e $44 $48`
(60 / 110 / 68 / 72), i.e. genuinely per-car constants, not a function of race
position or elapsed time. The drones' difficulty on Track 1 therefore comes from
the fixed racing line + fixed per-car caps, matching the "fixed stored path,
difficulty ramps by track number" model of the arcade original — but the arcade
speed rubber-band does **not** appear in this ST build's per-frame speed update.
(Open: whether the race-start init derives `-3874(A4)` from something dynamic —
needs a countdown-phase trace.)

## Can the mechanics be recovered?

Yes, fully. The racing line is a plain 42-entry array (`$55c3c`, 16-byte records,
count at `-4076(A4)`), the AI is four short routines (`$eaea` control, `$ec52`
follow, `$f2dc` waypoint test, `$ee86` turn), and collision is two samplers
(`$b798` surface, `$bda4` obstacle). Everything is table-driven and located.

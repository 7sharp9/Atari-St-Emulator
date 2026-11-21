# Starglider objects: the pool, the types, the AI dispatch and the RNG

The world is one fixed pool of 64-byte object records filled from a per-level list. Each frame the game:
1. puts the records near the player on a near list;
2. rotates the near records into view space and splits them into an active list and a view list;
3. tests the player against the active list;
4. runs a per-type behaviour handler through a longword jump table.

Enemies steer by turning a sixteenth of the way toward the player's bearing each pass. Addresses are runtime
absolute; `N(A6)` is the global block at `$5bf00`.

Proof scripts are in `py/objects/` (run from `M68000/` with `python3`). Each gate feeds the Python model only the
base RAM plus the labelled pokes, compares it with `callcap`, and has a `--break` control (one wrong constant) that
fails.

## 1. The pool and the record

**The pool.** The pool starts at `4762(A6)` = `$5d19a`, with stride `$40`. Its count is `472(A6)`, which is 107 on
level 1. A record is live when its type word is non-zero.
- Slots 0 to 9 are spares for missiles. The pointers at `$94c..$974` form a free list, with its top at `156(A6)` and
  its count at `604(A6)`.
- While docked, two records outside the pool stand in for the scene: `$1218` (type 22, the docking bay) and `$1258`
  (type 24). `168(A6)` points at the silo record.

**The record.**

| offset | field |
|---|---|
| 0 w | type (0 = free) |
| 2 b | flags; bit 7 = indestructible |
| 4/6/8 w | world x, y, z (16-bit, the world wraps at 65536; y negative up) |
| 10/12/14 w | pitch, heading (4096 per turn), roll / spin |
| 16 w | speed |
| 20, 22, 24 w | timer, second timer or y velocity, timer reload |
| 28/30/32 w | velocity x / - / z |
| 34, 35, 36 b | in view, active, exploding |
| 38 w | explosion tick |
| 40/42/44 w | position relative to the player, in view space |
| 46 b | laser-immune |
| 48 w | hit points (the object dies when 48 − 1 < 0) |

**The census.** `census.py [snap]` decodes every record and draws a top-down map. On level 1 at `g_game1` the pool
holds:
- type 3 ×27, type 26 ×7;
- type 4 ×9, type 24 ×9 (live missiles);
- types 8 and 9 ×6 each;
- types 13, 14 and 20 ×5 each;
- type 6 ×4;
- types 7, 11, 21 and 23 ×3 each;
- types 2, 5, 16 and 17 ×2 each;
- types 1, 15 and 27 once each.

`census.py` also writes a top-down map, `$STARGLIDER_WORK/objects/map_<snap>.png`, with one dot per record coloured
by type. It has no legend yet, so it is not committed.

## 2. Types and their names

The names come from the game's own database screen, the "I" (interrogate) screen at `$d5d0`, which is reached while
docked:
- It takes entry `506(A6)` (1 to 17) of the type table `$d724`, the name from the pointer table `$d7d8`, and the two
  description lines from `$d748` and `$d790`.
- It draws the model with `$f6a8`, with D0 = type. Live objects are drawn with the same call, with D0 = the type word.

| type | name | type | name |
|---|---|---|---|
| 1 | Walker | 15 | Stomper |
| 2 | Pyramid mine | 16 | Skim fighter |
| 4 | Energy Tower | 20 | Juno cannon |
| 7 | Starglider drone | 21 | Lotus Starfighter |
| 8 | Armoured Transport Vehicle | 23 | Tri-launcher |
| 9 | Egron Battle Tank | 24 | Egron Neutron Missile |
| 13 | Bute fighter | 25 | Egron Homing Missile |
| 14 | Diamond Proximity Mine | 26 | Pyramid Launcher |
| | | 27 | StarGlider One |

These types have no database entry; their roles are read from their handlers and the names are inferred:
- **3:** fires lasers, 1 chance in 32 per pass while in view (a gun emplacement, inferred).
- **5 and 17:** static, random heading, indestructible.
- **6:** the silo (dock and launch, `flight.md` section 5).
- **11:** the refuel hub at the centre of each tower complex (section 6).
- **12:** missile code, never spawned.
- **22:** the docking bay.

**Proof.** `names_gate.py` pokes the docked flag `714(A6)`, presses I, then SPACE 16 times, with a breakpoint on
`$f6a8`. At every stop D0 equals the table's type and A3 the name pointer: names 17/17. In flight the view list of
`g_game1` holds types `[7, 8, 8, 3]`, and the first four `$f6a8` calls carry exactly those: view 4/4.

## 3. Behaviour dispatch

`$125e0` runs once per pass over the pool.

**Exploding records.** A record with `36` set is not dispatched. Instead `38` counts up to `$1f`. Then the record is
freed: its type and both fields are cleared, `604` is incremented, and the record goes back on the free list.

**Live records.** A live record jumps through the longword table `$12dde`, indexed by type × 4
(`movea.l 0(A5,D1.w),A4` / `jmp (A4)`). Every handler returns to `$1262c`.

| handler | types | handler | types |
|---|---|---|---|
| `$12780` fighters | 1, 10, 13, 15, 16, 18, 21, 27 | `$12d00` Juno cannon | 20 |
| `$12652` mines | 2, 14 | `$12d36` Pyramid Launcher | 26 |
| `$1263a` silo | 6 | `$12d80` Tri-launcher | 23 |
| `$12830` flyers | 7, 8, 19 | `$12da6` | 3 |
| `$12c64` tank | 9 | `$12dbe` refuel hub | 11 |
| `$1291a` missile | 12, 24 | `$1295e` homing missile | 25 |

Types 4, 5, 17 and 22 do nothing. Types 28 to 30 point at `$12ed6`, which flashes the palette. The table also routes
types 10, 12, 18, 19, 32 and 33. No level list holds any of these types, and no other spawner writes them
(section 5), so their handler entries are never used.

**Steering.** Handlers turn toward the player with `heading += (bearing − heading) >> 4`, where the bearing comes from
`$12f1c` (`graphics.md` section 7). There is no wrap handling, so an enemy facing just across the 0/4096 seam turns
the long way round. Velocity is `28 = −(speed·sin)` and `32 = speed·cos`, each `(muls) << 1 >> 16`.

**Weapons.**
- **Enemy laser, `$129a4`.** It costs the shield `608` 100 on level 1, otherwise `$159ea[type]` (300 for every type).
  It also makes one RNG draw for the bolt, sets the flash colour `578` to `$20`, and counts `196(A6)` ("hits on
  AGAV" on the rating screen).
- **Missile launch, `$12a7e`.** It pops a spare record and makes it type `$19` (homing) when `726(A6)` is set and the
  level is not 1, otherwise type `$18`. Speed and lifetime come from the tables `$12b80` (−350, −350, −300, −250,
  −200, −200) and `$12be2` (65 five times, then 55), indexed by level.
- **Proximity mine, `$126b4`.** It arms when the relative z is below `$800`, does nothing during the level banner
  (`664` non-zero) or while docked, and explodes below `$600`. Outside missile view the explosion kicks the bank
  `640` and costs the shield `$3a98`.

**Proof.** `objpass_gate.py 30`:
- Poked: 25 types × 30 states, each with one record in slot 0 and the free list and RNG rejection-sampled so the
  branches fire. 750/750.
- Natural: whole passes on `g_game1` and `g_game2` with 0 mismatches, and 11 captured natural hits 11/11.
- Control: poked 513/750 and natural 0/11.
- Coverage: the poked run reaches 66 branch labels, every handler included. The homing missile hitting the ground was
  not reached.
- The natural corpus is made with `python3 tools/capture_hits.py scratchpad/starglider/drive/g_game1.snap 125e0
  1,2,3,5,8,13,21,34,55,89,144 scratchpad/starglider/objects/nat --name o125`.

## 4. Lists, collision, the laser and scoring

**Near list, `$102dc`.** A record goes on the near list `144(A6)` when its relative z (a wrapping word) is within
±`$2020`, or, when it is further behind, when its |x| is within `$2020`. While docked, `$101a8` replaces the list
with the two bay records.

**Projection, `$10344`.**
- It rotates each near record's relative position by the view matrix (`$ec1e`) into `40/42/44`.
- It marks the record active (`35`) and pushes it on the active list `152(A6)` unless it is exploding.
- It marks it in view (`34`) and pushes it on the view list `148(A6)` when z ≤ `$2000`, z > −`$15842[type]` and
  |x|, |y| ≤ 2z.

**Player collision, `$12fa2`.** It walks the active list and tests |x|, |z| < `$15842[type]` and |y| <
`$1587e[type]`. On contact:
- **Type 11:** refuels (section 6).
- **Type 6:** docks (`flight.md` section 5).
- **Types 1 and 15:** cost the shield `$1f40` unless in missile view.
- **Type 27:** takes 5 hits, and only in missile view.
- **Anything else:** dies (`36 = $ff`, unless indestructible), sets the collision flag `703(A6)` and records itself
  in `172(A6)`.

**The consequences, `$cbb4..$cc42`, inline in the main loop.** With `703` set:
- the screen flashes (`578 = $555`);
- an exploding victim that is not indestructible scores `$15a62[type]`;
- outside missile view the bank kick `640` gets `(rng & $3e) − $20` and the shield loses `$159aa[level][type]`
  (1000, 3000, 5000, 7500 for levels 0 to 3 and the same 7500 table to level 15; type 6 always 1000). The pointer
  table has only 16 entries, and the level runs to 34 (section 5), so from level 16 the "pointer" is whatever follows
  it (below);
- a shield that would go negative ends the game (`300 = 2`, "SHIELD DEPLETED").

**The shield table overrun.** `$159aa` holds 16 longword pointers. The longwords after it are the start of the
enemy-laser table `$159ea` (300, 300, ...) and what follows that, so a level of 16 or more reads a wild pointer:

| level (score) | `$159aa[level]` | collision cost |
|---|---|---|
| 1 to 15 (to 149,999) | `$158ba`..`$1596e` | 1000 to 7500 |
| 16 to 30 (150,000 to 299,999) | `$012c012c`, the words 300, 300 | 0 here: the emulator reads 0 at `$2c012c`; a real ST's value is not checked |
| 31 (300,000) | 0 | a word from the exception vectors: 3324 for a missile |
| 32 to 34 (310,000 on) | `$500050`, `$500500` | a bus error: the first collision crashes the game |

The colliding types in the probes were the Egron missiles (types 24 and 25), so on levels 16 to 30 an enemy missile
hit kicks the bank and costs no shield. At level 32 the load at `$ccc0` takes vector 2 into TOS's bomb handler and
the machine ends at the Zuul boot sector's banner; addresses `$400000..$f9ffff` bus-error in this emulator as in
Hatari's ST map. Driven:
- `py/curios/shield_level.py`: levels 3, 16, 20 and 31 poked into `662`, three collisions each from `g_game1`: shield
  −7500 at level 3, unchanged at 16 and 20, −3324 at 31.
- `py/curios/shield_crash.py`: levels 32 and 34 step from `$ccc0` to `$02fc0a1a`, the TOS bus-error stub; level 3
  steps to `$ccc4`.
- `py/curios/level_from_score.py 8 --crash`: no level poke. The practice-mode N key alone takes the score to
  310,000 and the level to 32, and the next collision bus-errors at `$ccc0` (27M steps later).

**The player's laser, `$131f8`** (hit part `$13294..$13386`).
- It projects each active record's box to the screen with the same `(v << 530) / z + centre` as the renderer and
  tests it against the aim point `588/590`. The first record whose box holds the aim point is hit.
- Indestructible and laser-immune records only make the sound, and type 11 is skipped.
- Otherwise the hit costs one hit point. A kill explodes the record, scores `$15a26[type]` and flashes `$222`.

**Scores.** Scores are BCD: `$b91a` adds the pending score `212(A6)` with `abcd` into the score at `$c09c`. Laser-kill
values include type 7 → 500, type 9 → 200, type 8 → 100 and type 24 → 5. Ramming kills are worth more (`$15a62`,
type 1 → 1500, type 27 → 7500).

**Proof.**

| gate | match | control |
|---|---|---|
| `collide.py 600` (outcomes: none 257, flag/kill 86, flag 200, refuel 29, dock 28) | 600/600 | 589/600 |
| `laser.py 600` (hit 144, kill 115, none 341) | 600/600 | 485/600 |
| `project.py 200` | 200/200 | 61/200 |
| `nearlist.py 40` | 40/40 | 27/40 |
| `impact.py 30` (compares 608, 212, 640, 300, 578; `196` not compared) | 30/30 | 21/30 |

## 5. Levels and spawning

**Level lists.** `$1523a` initialises a level from the list pointed to by `$22814[662]`. The table has 36 entries:
0 and 1 point at the same list, and 4 to 35 all point at a fourth. Levels 1 to 4 therefore each have their own list,
and every later level replays level 4's. Each entry is four words: type, x grid, z grid (position = grid × `$290`),
and hit points.

**Level progression.** A level is a score band. `$fbb8`, in the frame, compares the score's ten-thousands byte `$c099`
with the copy in `725(A6)`. On a change it adds 1 to the level `662`, sets the banner timer `664`, and sets `727`,
which sends the main loop back through `$ca92` to `$1523a`: the pool is rebuilt from the new level's list wherever the
player is. So the level is 1 + score / 10,000, and it stops at 34 (a 35 is set back to 34). The per-level tables are
sized for different ranges:
- the missile speed and lifetime tables `$12b80`/`$12be2` hold real values to level 34 (speed −350 on level 1, −200
  from level 4, −50 from level 25);
- the collision-cost table `$159aa` has 16 entries, which is the overrun in section 4.

Driven by `py/curios/level_from_score.py`: in practice mode each N adds 5000 points (`flight.md` section 2), and the
level steps 1, 2, 2, 2, 3, 3, 4, 4 over eight taps (one tap did not register); the control with `717` clear stays at
level 1 and score 0.

A type 4 entry expands into a six-record tower complex: three Energy Towers, a refuel hub (type 11) and two Egron
Battle Tanks (type 9). That is why the type 4 count is three per list while the pool holds nine type 4 records.

The lists grow with the level. Counts are from `py/objects/levels.py`:

| level | entries | type 20 | type 26 | type 21 | type 14 |
|---|---|---|---|---|---|
| 1 | 82 | 5 | 7 | 3 | 5 |
| 2 | 89 | 10 | 9 | 4 | 7 |
| 3 | 97 | 10 | 10 | 5 | 7 |
| 4 | 114 | 12 | 11 | 8 | 8 |

Every list holds four silos (type 6), three tower complexes and one StarGlider One (type 27). Type 3 drops from 27 on
level 1 to 20 on levels 2 to 4. Level 4's list also holds one type 24 (Egron Neutron Missile).

**Proof.** `levelinit.py` runs levels 1 to 5: 5/5, control 0/5.

**Type writes.** A raw scan finds type words written only by:
- the level initialiser;
- the two missile sites `$12aca` and `$12ad2`;
- `$12dd4` (a hub vanishing);
- the hub toggle `$13432`;
- the free step `$1261a`.

So nothing spawns mid-level except enemy missiles.

**Hub toggle (inferred).** A laser hit on an Energy Tower with `24(A4)` non-zero, off level 1, executes
`eori.w #$b,192(A4)` on the record three slots on. That switches its hub between type 11 and type 0. The laser gate
compares the pool bytes it changes but does not single this case out.

## 6. The refuel hub

The refuelling contact is `$130a8`. It needs the craft to fly into the hub at the centre of a tower complex in line
with it:
- relative z in [`$79e`, `$7d0`);
- |x| < `$2bc`;
- `(hub heading + yaw) & $fff` in [`$60c`, `$9f4`).

Each pass in contact sets `707(A6)` and adds `$190` to the energy `606(A6)`, saturating at `$ffff`; while `707` is
set the game prints "ENERGY CELLS REFUELLING". The database calls type 4, not type 11, the Energy Tower; "refuel hub"
for type 11 is a descriptive name.

**Proof.** `collide.py` (refuel cases) and the flight gate `gate_energy.py` refuel 16/16 (`flight.md` section 5).

## 7. Random numbers

The game has two generators, and both mix in the stick x accumulator `$c3ce`, so a run is deterministic only for a
fixed input stream.

- **`$f21e`** is the main generator, about 31 calls per frame.
  - Its state is `100(A6)`, seeded to `$314159` at `$f214`.
  - Each step shifts the state left one bit and XORs it with `$1d872b41` when the bit shifted out was 1 or the result
    is 0. It then adds the stick x word and the long at `92(A6)`, and returns the high word.
- **`$f23e`** is a lagged additive generator over the bytes `92..97(A6)`, called about 22 times in 68 frames.
  - It first adds the caller's D0 word plus the stick x word to the word at `92`, then runs two additive steps with a
    carry chain. It writes the two result bytes to `538/539` and returns the word.
  - `$f1e6` seeds it from `536/537`, which the game-start code sets to `$1357` (`$f4c6`, called from `$1382c`).
  - Because the caller's leftover D0 feeds the state, a multi-object pass that reaches it after another handler
    depends on register history. No natural state in the corpus exercised that.
- `$f2be` is a 32-bit LFSR step with no caller in a raw scan, so it is unused (inferred).

**Proof.** `rng_gate.py`: `$f21e` 200/200 and `$f23e` 200/200, controls 107/200 and 0/200.

## Open

- Not gated: the laser draw `$10192`, sound `$ac9c`, the docked and launch branches of `$101a8`, and the hub toggle
  as a case of its own.
- Inferred names: types 3, 5, 11, 12, 17, 22 and the purpose of `$ef7a`, which advances cyclic index/limit/list tables
  and writes into model and palette slots such as `$15b50`.
- Open questions:
  - What the fourth level-list word means for type 3 (values 1 to 21).
  - What `$f2dc` draws (40 `$f23e` calls).
  - Where the restart routine `$13830` is entered.
  - Whether `$12f1c`'s divide by zero at x = 0 can happen in play.

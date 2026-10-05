# Crude Buster: pool A objects of levels 0 to 2 (ENEMIES1)

Scope: the pool A types (enemies, bosses, their helpers) that the level scripts of levels 0, 1 and 2 use (`$80046` = 0..2: ruined city street, bridge/highway, construction site),
set `cbuster` (World FX), decrypted program image `scratchpad/crudebuster/rom/cbuster_main.bin`. Addresses are 68000 addresses of that image.

Evidence labels. **lab** = measured in a controlled MAME run (`lua/lab.lua`: loads a saved state of level 0 with nothing alive, spawns records exactly as the script spawner `$f388`
does, pins P1 and keeps it alive); **nat** = measured in a natural bot run of a whole level (`lua/enemylog.lua`); **read** = read from the disassembly, not run; **inferred** = guessed.
Counts are given with the script that reproduces them (`README.md` lists all scripts). The game prints no enemy names (the only text near the fights is `ENEMY`, `DOCTOR:` and
`CRUDE BUSTER:` in the dialogue boxes), so the names below are descriptions of the sprites (portraits: `portraits_l0.png`, `portraits_l1.png`, `portraits_l2.png`,
`enemies_sheet_ground.png`), not the developers' words.

## 1. What the scripts place

List A (`$6c000`, enemies) and list B (`$6d000`, props and items), counts per type and variant (`py/census_static.py`, same numbers as `architecture.md`: 42/33/59 and 26/57/25):

| type / var | L0 | L1 | L2 | type / var | L0 | L1 | L2 |
|---|---|---|---|---|---|---|---|
| 0 / 0 | 5 | 1 | 3 | 9 / 0 | 1 | | |
| 1 / 1 | 13 | 5 | 6 | 10 / 0 | | 1 | |
| 2 / 2 | 7 | 5 | 4 | 11 / 0 | | | 1 |
| 3 / 0 | | 10 | 4 | 14 / 0 | 1 | | |
| 4 / 0 | 4 | | | 15 / 0 | | 1 | |
| 4 / 1 | 6 | | | 20 / 0 | | 2 | 2 |
| 5 / 0 | | 3 | 16 | 20 / 1 | 1 | 2 | 1 |
| 6 / 0 | | | 8 | 21 / 1 | | | 1 |
| 6 / 1 | | 2 | 4 | 23 / 2 | | | 1 |
| 7 / 0 | 4 | | | 28 / 0 | | 1 | |
| 8 / 0 | | | 7 | 28 / 1 | | | 1 |

The variant of types 0, 1 and 2 is always equal to the type in levels 0-2 (variants 3-6 of these types exist only as spawned helpers, section 4). List B (props) holds 38 type/variant
combinations (`out/census_static.md`); types 152-159 carry bit 7 of the type byte, which makes the list-B spawner search the records from 24 instead of 0 (read, `architecture.md`). Pool B types
are outside this document except the two thrown objects the enemies use (section 3).

Observed order (nat, `py/census.py`): in level 0 a bot run saw **42 of 42** list A entries spawn, in script order, one per frame, in the frame the scroll counter `$8040a` reached the entry's trigger
(example: entry 0, trigger `$180`, spawned at frame 1216 with `$8040a` = `$180`; entries sharing a trigger spawn on consecutive frames). `out/census_l0.txt` has the full table. Level 1 run: 25 of 33 seen
(the run did not get past the camera position `$600`); level 2 run: 50 of 59 (the camera stopped at `$864`; the 9 unseen are entries with triggers above that plus entries 2, 35 and 44 below the reached camera position that the matcher did not find, probably moved before the first logged frame or
skipped when no free record existed, see 6.3). Records that appear without a script entry: type 27 (wreck of a rider, 2 per kill of types 20/21), types 54, 55, 56 and type 5 var 1 (boss helpers of level 0),
types 32, 33, 34 (level 2 mid-boss), types 45 to 50 and type 0 var 5 (helicopter of level 2).

## 2. The engine contract every pool A type shares

### 2.1 The record (`$40` bytes, A6)

| offset | meaning | evidence |
|---|---|---|
| +0 | bit 7 active, bit 6 "hittable" (checked by every hit routine), bit 3 invulnerable (set while a boss waits for the camera, and for 16 frames after a special hit, `$24022`), bit 0 "this state's init has run" (cleared by `$22c2c` on every state change), bit 1 holds/held (inferred) | read |
| +1 | bit 7 "animation cycle finished" (set by `$22612`), bit 4 walking animation, bit 3 target is P2 (`$22b48` picks the player each time: random bit 0 of `$ea44` unless one player is inactive), bit 2 loop animation, bit 0 | read |
| +2 type, +3 state, +4 direction (0 faces right, 1 left), +5 **health**, +16 variant | lab: first frame of 15 type/variants matched the init constants (section 3) |
| +6 incoming event byte: bit 7 pending, bit 6 from P2, bit 4 "I touched a player" (`$90`), bit 3 heavy (thrown object), bits 0-1 hit strength | written by `$f82e` (`$80 | {0,1,2,4}[player's +25]`, `$40` for P2, `$88`.. for a pool B object) and by `$f700` (`$90`) |
| +8 x, +12 y (16.16 fixed longs), +22 x velocity, +26 y velocity (16.16 px per frame, added by `$22664`) | lab: measured speeds equal the code constants (2.3) |
| +17 bit 0 "bounded by the camera window", +17 bits 1,2 held/thrown, bit 4, bits 6,7 special-hit flags | read |
| +18..+21 animation counters, +30 timer, +36/+37 jump arc parameters (`$22856`: y = table[+37] * +36 / 256), +38 saved ground y, +42/+44/+46/+47/+50 copy of the target player's x, y, action, sub-action, flag byte (`$22bd0`) | read |
| +52 last state (animation reset detection), +53 flags (bit 3 "tough", bit 4 airborne or heavy-hit marker, bits 0-2 hurt-sequence progress, bit 7), +60 link to the object it spawned or the parent | read |

Camera window rule (`$2242c`, read): with +17 bit 0 clear a record is erased when it leaves x in [sx-`$40`, sx+`$140`] or y in [sy-`$80`, sy+`$140`]; with the bit set it is clamped into the window instead and re-targets
its player. The animation and sprite tables are `$30000[type][state]`, body boxes `$6b000[type][state]`, vulnerability boxes `$68000`, attack boxes per animation frame `$69000[C type][state][dir][frame]`.

The random source is `$ea44` (read): two words at `$81e0e`, seeded `$7fff8001` at every level start (`$16fe`), advanced on every call; in attract mode (`$80040` bit 7 clear) it returns the frame counter `$80042`.

### 2.2 Shared states (the 24-entry state tables at the start of every handler, `py/states.py`, `out/state_tables.txt`)

Every handler starts with the same eleven-call skeleton: sound/assets, `$24022` (invulnerability blink), a hit routine (`$22c56`, `$22ce4` or the type's own), `$22dac` (special hits), the state dispatch
(`lea table / movea.l 0(A0,D0.w)`, state byte in +3), `$22540` (animation step), `$2331c` (hit tests against players), `$2242c` (camera window). State numbers 1 to 5, `$a`, `$17` always point to shared code:

| state | shared routine | behaviour (lab where counted) |
|---|---|---|
| 0 | type's own init (state 0 handler) | runs once, 1 frame (all 15 lab type/variants) |
| 1 | `$234e6` hurt | stun: slides 0.5 px/frame away from its facing for 15 frames then returns to state 6 (**56 of 56** frames of state 1 for types 0/1/2, lab `expD.py`), or a knock-down arc (x 2.0 px/frame, y arc) if +53 bit 4 is set (airborne or heavy hit) or, for "tough" types (+53 bit 3: types 3 and 5), a 1 in 4 draw when the hit has strength bits (+6 and 3 non-zero) (read) |
| 2 | `$2397e` (`$23cf2` for bosses) death | flies backwards at 3.0 px/frame (x) with a y arc (dy 5, 6 or 1 per frame), ground contact then erased about 56 to 59 frames later (lab: 12 deaths); bosses stay down `$40` frames, then clear `$80040` bit 2 and `$80400` bit 5 and erase themselves |
| 3 | `$22ecc` grabbed by a player (positions it relative to the player) | read |
| 4, 5 | `$23ac0`, `$23748` knock-down flight (x 1.5 px/frame, +4.0 px/frame fall) | read |
| `$a` | `$23248` fall: x 0.5, y +4.0 per frame until the terrain probe says ground | lab: 12 frames to drop 48 px (types 0-3, 4, 6, 7, 20: all `r90u` runs) |
| `$17` | `$22e30` thrown | read |
| 6 | type's own idle/decide | |
| 7.. | type's own | |

### 2.3 Damage the enemies take

`$22c56` (types 0, 1, 2, 5, 9, 11, 14, 20...), `$22ce4` (type 3) or an inline copy (types 4, 6, 10, 15, 21...) all do the same arithmetic when `+6` bit 7 is set and the record is hittable and not held (+17 bit 1):
`+5 -= 1` for strength 0 to 3 hits and `-= 4` when +6 bit 3 is set (thrown object); `+5` reaching 0 (or wrapping) sets state 2, otherwise state 1; `$248bc` is called (score, below).

- lab (`expB.py`, 15 type/variants x 5 hit values x 6 cycles x 5 pokes): **every** accepted light hit (values `$80, $81, $82, $84`) took exactly 1 hp and every `$88` hit took 4 (types 3 and 5: hp 8 to 4, 6 to 2); hits poked while the record was in state 1, 2 or an invulnerable state were ignored (hp unchanged).
- A hit while airborne (types 5, 6, 20: states 9, e, 10..) is a knock-down; on the ground the first hit stuns (types 0, 1, 2, 3, 7: 26 of 26 ground stuns of type 3 with strength 0 or 4; knock-down not seen for them). Type 5 var 0 hit on the ground with strength bits (`$81`, `$82`) knocked down in 3 of 7 hits, with `$80` or `$84` in 0 of 4 (`py/expB_kd.py`; small sample, the 1 in 4 draw is *read*).
- **An enemy loses 1 hp when it touches a player.** The touch test `$f4f4`/`$f690`/`$f700` (body box against the player's body box) removes 1 hp from the player (table `$f78e`: 1 for every pool A type except types 61 and 77) and writes `+6 = $90` into the *enemy*; the shared hit routine then treats that as a hit on the enemy. Result: contact costs the enemy 1 hp and scores the hurt points for P1. lab (`expF_contact.py`): **62 contact events** (P1 loses exactly 1 hp while +6 has bit 4), of which every one of types 0, 1, 2, 3, 20, 21 (8, 8, 8, 13, 13, 7 events) also cost the enemy 1 hp within 3 frames; types 4 and 6 use their own hit routines (the grab ticks) and are exempt. A type 0 (hp 2) dies after two touches without being attacked and P1's score rose 0 to 50 and 50 to 150 at those frames.

### 2.4 Damage the enemies deal, and how an attack works

Attacks are one-frame **hit objects** in pool C. A state that attacks calls `$21e72` (`D6` = C type, `D7` = direction) on every frame of the attack animation; the C handler (`$22040`, shared by 40 of 44 C types)
copies direction and animation frame from its parent, tests the parent's attack box `$69000[C type][0][dir][frame]` against the players' body boxes (`$fa10` / `$fb8c`), applies damage, and erases itself (`$22526`).
So the attack is active only on the animation frames whose box is non-zero (`py/cboxes.py`), and a C record is never alive at the end of a frame (lab: 0 of 600+ logged frames show one).

Damage per C type is `table[C type] * 4` hp with the table chosen by the difficulty bits of `$80054` (`$fcba`: pointers `$fd2a, $fcca, $fd5a, $fd8a` for Normal, Easy, Hard, Hardest).
P1 has `$38` = 56 hp (the bar routine `$3d66` draws 7 segments of 8; a value of `$40` or more makes it write 65,535 words into the tilemap RAM). Normal damage of the C types used here:

| C type | 0, 1, 2, 3, 5, 11 | 4 | 6 | 7 | 10 | 12 | 13 | 17 | 19 | 20 | 21 | 22 | 29 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Normal / Easy / Hard / Hardest | 12 / 8 / 16 / 20 | 20 / 16 / 24 / 28 | 12 / 8 / 16 / 20 | 24 / 20 / 32 / 36 | 16 / 12 / 20 / 24 | 16 / 12 / 20 / 24 | 20 / 16 / 28 / 32 | 16 / 12 / 24 / 28 | 12 / 8 / 16 / 20 | 16 / 12 / 20 / 24 | 20 / 16 / 24 / 28 | 16 / 8 / 20 / 24 | 20 / 16 / 24 / 28 |

(all 44 entries: `py/cdamage.py`). Measured on Normal (lab `expA_agg.py`): C0 12 (**12 of 12** hits of type 1), C1 12 (28 of 28, type 2), C2 12 (6 of 6, type 4 var 0), C12 16 (11 of 11) and C13 20 (7 of 7) for type 3, C19/C20/C21 12/16/20 for type 5 (91 of 92 state-10 hits were 12), the C-type 4 beam and the rest below. Pool B objects hurt for `table $10122[type]` hp: 1 for almost all, 10 for types 4 and 5, 3 for type 82 (read, lab 1 for the type-1 projectile).
Multi-hit: in the lab P1 stays hittable between the 8-frame spacing of the hit stun, so one attack animation delivered **3 hits** (types 1, 2; 12 of 12 attacks) or 2 hits (type 4 var 0, type 9) before the animation ended.

### 2.5 Scores

`$248bc` (called on every accepted hit) adds to the player named by +6 bit 6 the points `BCD[$4012 + 4*i]` with `i` = byte `$24952[type*4 + k]`: k = 0 when the hit puts the record in state 1, 1 for state 5, 2 for states 2 and 4; byte 3 is the voice (0 = one of sounds `$64, $65, $67` at random, `$ff` none). Lab (`expE.py`, hit poke `$80`): P1's score rose by exactly the table value in **every** accepted hit of types 0 to 8 and 20 (about 130, `out/expE.txt`, no mismatch), for example type 0: 50 per stun, 100 for the kill (6 and 6 hits); type 3: 200 (20 hits); type 5: 100 (25 hits); type 2: 100 (12). The score longword is at `$8013c` (P1) and `$801bc` (P2), not at +64.

| type | hurt | knock-down | kill | | type | hurt | knock-down | kill |
|---|---|---|---|---|---|---|---|---|
| 0, 1, 4 | 50 | 100 | 100 | | 9 | 200 | 400 | 1000 |
| 2 | 100 | 100 | 100 | | 10 | 200 | 500 | 1000 |
| 3 | 200 | 300 | 500 | | 11 | 200 | 500 | 2000 |
| 5 | 100 | 200 | 300 | | 15 | 200 | 300 | 10000 |
| 6, 7 | 100 | 200 | 200 | | 20 | 200 | 400 | 400 |
| 8 | 100 | 300 | 300 | | 21 | 100 | 300 | 300 |
| 28 | 0 | 0 | 3000 | | 32 | 300 | 500 | 2000 |
| 54 | 200 | 300 | 10000 | | 14, 23, 56 | 0 | 0 | 0 |

(Index to points: 2 = 50, 3 and 4 = 100, 5 and 6 = 200, 7 and 8 = 300, 9 and 10 = 400, 11 = 500, 12 = 600, 13 = 800, 14 to 16 = 1000, 17 and 18 = 2000, 19 and 20 = 3000, 23 = 10000. Rows for types 0 to 8 and 20 are lab-verified, the others are *read* from the table; the points go to the player that hit, bit 6 of +6 picks P2.)

### 2.6 The brain `$2438a` (types 3, 5, 9 to 11, 14, 15, 28... 40 call sites)

Called at the end of idle and walking states (read). It loads the target (`$22bd0`) and chooses a table by the vertical relation: A when my y is in (py-`$20`, py+`$60`] (three-level table `$24508[type]`), B when I am more than `$60` below (`$24644`), C when I am above (`$24780`). Facing is corrected with hysteresis (`$10`, or `$30` in B and C). Distance `dx >= $100` forces state 7 (approach). Otherwise `[type][dx >> 4]` selects a row; in case A the row is indexed by the player's action `+46 & 15` and then by the player's sub-action `+47` (groups of four).
The leaves are small routines (`$24c9e`, `$24cc0`, `$24ce2`, `$24d04`, `$24d26`...) that wait for the end of the current animation (+1 bit 7) and then pick one of four next states with `random & 3` from 16-byte lists (`$24d2e..`): idle 6 (`$24d6e`), walk 7 (`$24d80`), jump to the player's lane 9 or 10 (`$24d92`), drop `a` (`$24dce`), grab attempt `b` (`$24de6`, only if the player is on the ground and not already held), jump attack `e` (`$24e74`), `f` (`$24e8e`), `$10` (`$24ea0`). The effect: the chance of each attack depends on the distance band and is zero when the player is in an action 5 to 15 (attacking, hurt, jumping): the default leaf `$24d26` just idles. `py/brain.py` dumps the tables. The rate was not tabulated per type (open item 8.3); the lab shows the resulting cadence (3.3).

## 3. The regular types

Walking speeds are `|dx|` per frame at 58 Hz measured in the lab (`expD.py`, e.g. type 1 var 1 state 7: 182 of 182 frames at 1.000, `out/expD.txt`); every one equals the constant in the code. "d" below is the forward distance (target x minus my x if facing right, else my x minus target x, as unsigned words).

### 3.1 Types 0, 1, 2: the street thugs (one pipeline, `$10778`)

Three palette variants of one long-haired fighter: green (type 0, var 0), blue (type 1, var 1), magenta (type 2, var 2). hp 2, score 50/100/100 (type 2: 100/100/100).

State 0 sets hp 2, state 6, facing left and the camera clamp bit; variants 3 to 6 reposition for the helper roles (3.1.1). State 6 waits for the animation end then goes to 7 unless the target's action is `$d` or more. State 7 walks toward the player at **1.0 px/frame** (turn hysteresis `$10`) and each frame evaluates, in this order: target lane more than `$20` above me -> state 9 (jump, 0.5 px/frame arc); lane below -> state `a` (drop, 12 frames for 48 px, lab 4 of 4); then the attack by variant:

| type (var) | trigger on d (read) | lab entries | state | attack | damage (Normal) |
|---|---|---|---|---|---|
| 1 (1) | `$24 <= d < $28` | state b at d = 39 in **4 of 4** runs | b | C0, reach 36 px, active on animation frame 2 | 12, 3 hits per attack |
| 2 (2) | `d < $24` | state c at d = 35 in 12 entries (35 down to 21) | c | C1, reach 32 px | 12, 3 hits |
| 0 (0) | `$28 <= d < $40` | state 8 at d = 63 (49 when spawned at 50) in 4 of 4 | 8 | no hit object: a charge at 1.0 px/frame for up to 128 frames; the damage is the body touch | 1 per touch (4 of 4), and it costs the thug 1 hp |

After an attack the thug goes to state 8 (walk forward, up to 128 frames, 1.0 px/frame) and then 7 again. The thug with the narrow 4 px band (type 1) attacks reliably against a stationary player (lab 4 of 4) but can step over the band when the player advances at more than 1 px per frame (read), in which case it only touches. Terrain: state 7 and 8 call `$226e4` (probe 16 px ahead, 32 below): a wall turns it around (state 8 with direction flipped), no floor drops it (`$a`).
Lab death: contact twice (type 0: both touches by itself at 1090 and 1121 after spawn at 1006: hp 2, 1, 0) or two hits. Reaction to a hit: stun 15 frames (24 of 24 pokes on the ground), airborne hit kills the arc; hits while a thug is in state 1 or 2 are ignored (12 of 12).

#### 3.1.1 Variants used as helpers (read; observed in the L1 final boss and L2 helicopter)
`var 3` type 1 appears at (`$920`, `$150`) and type 2 at (`$7e0`, `$1c0`) (the two screen edges at camera `$800`), `var 4` type 0 at (`$7e0`, `$150`) runs right until x >= `$880` (states d, e, f, 10, 11), `var 5/6` type 0 enter in state `a` after a drop of `$10`/`$18` px (helicopter soldiers). Their hp is 2 like the others.

### 3.2 Type 3: the bruiser (levels 1, 2; `$10f60`)

Large man in a green tank top and white boots. hp 8, "tough" (+53 bit 3), carries the landing-dust flag (+35 bit 2: its knock-down spawns pool B effect `$51` and sound 24). State 7 walks at **0.5 px/frame** (124 of 124 frames), the brain picks the next move. Attacks (lab, one bruiser, 4 runs, 24 attack cycles):

| state | what | damage on P1 (Normal) | lab |
|---|---|---|---|
| f | shuffle at 0.25 px/frame (600 of 609 frames) with hit object C12 (reach 32 px, 4 boxes) | 16 | 11 of 11 hits 16 |
| e | jump lunge (1.0 px/frame, arc) with C13 (reach 32) | 20 | 7 of 7 |
| b, c, d | grab prelude, grab, squeeze: it forces P1's action to `$b` and sets P1's +0x58 bit 7 | 4 per squeeze | 24 of 24 |
| 10 | recover, 32 frames | | |

Reaction: stun on the ground, 8 hits to kill with strength 0 (hp 8, lab `3_0_80`: 8 of 8 hits -1), 2 hits with a heavy hit. Score 200 per hit, 300 knock, 500 kill. Cadence from the lab: the brain's choices come every 24 to 100 frames.

### 3.3 Type 4: the khaki thugs (level 0; `$11322`, own hit routine)

Stocky men in olive jackets. hp 1 (one hit or one touch kills it: lab `4_0_l90` dies at its first touch), own hit routine `$113bc` that also reacts to `+6` bit 4 (it hit the player) in state 9. State 7 walks at 0.5 px/frame, state 8 runs at **1.5 px/frame**. var 0: charges when far and punches with C2 (reach 32) at d < `$20` (31 in 3 of 3 entries): 12 damage, 2 hits. var 1: leaps (state 9, 1.5 px/frame, arc) at the player from d about 63 and on contact enters **state c, the grab**: it attaches to P1 (P1 action 7 held, `$80158` bit 4, pointer in `$80164`) and deals **1 hp every 16 frames** until released (lab: 263 ticks in 3 grabs; the lab P1 never escaped, so the release is not observed). Score 50/100/100.

### 3.4 Type 5: the jet-pack cyborg (levels 1, 2, and as a helper in level 0; `$11938`)

Blue armour, hovers: states 7, 8, 9 and c use `$227e6` (no terrain collision). hp 6, tough. var 0 enters in state c (hover), var 1 falls in (state b then 15, 16). Attacks (lab):

| state | what | damage | lab |
|---|---|---|---|
| 10 | swing with C19 (reach 32) from the ground, cycle 24 + 10 frames | 12 | 91 of 92 hits 12 |
| 11 | C20 swing, 50 frames | 16 | 1 of 1 |
| 13 | dive 1.5 px/frame, y +4..6 per frame, C21 | 20 | 5 of 5 |
| e, f, 9 | hover/approach 1.25 and 0.5 px/frame | | |

Reaction: airborne hits knock it down; on the ground `$81`/`$82` hits knocked down 3 of 7. The level-2 enemies parked on the girders (y `$100`-`$140`) are var 0 hoverers: they cannot be reached from the street (the first bot run got stuck on one for 17000 frames because it never walked right). Score 100/200/300.

### 3.5 Type 6: the dog (`$121a4`)

Orange dog, hp 1. var 0 (level 2) runs at 1.5 px/frame (state 7/8) and **latches** in state d at d = 30: **1 hp every 16 frames** (358 ticks in 4 latches in the lab; a dog on P1 is not released by the lab's idle P1). var 1 leaps (state 9, 2.0 px/frame, arc) and passes over the player landing 65 px behind (lab `6_1_l90`: 5 leaps without a hit); it bites only when the leap ends on P1 (1 hit in 54 leaps) and then latches. Score 100/200/200 and the voice id 106 (dog bark).

### 3.6 Type 7: the brawler thrower (level 0; `$1280a`)

Bare-chested man in jeans, hp 3. Stands still and throws a pool B type 1 object (state c, 24 frames, every **62 frames**: 83 throws in 5 runs): the object (`$2810c`) flies 3.0 px/frame horizontally in its direction until it leaves [sx-`$10`, sx+`$110`] or hits; damage 1 (81 hp-1 events in 83 throws at P1 pinned in the same lane 48 to 89 px away). State b (melee C3, reach 40) is chosen when the player is near. Score 100/200/200.

### 3.7 Type 8: the khaki thrower (level 2; `$12c5e`)

hp 3. Alternates state b (throw pool B type 2 var 1, 24 frames) and d (wait 64 frames), cycle **88 frames** (51 throws, lab); state c throws pool B type 3 var 1. The thrown objects did no damage in 51 lab throws at 50 and 90 px (read: pool B damage is 1). Score 100/300/300.

### 3.8 Types 20, 21: the scooter riders (levels 0-2; `$179ca`, `$17fb6`)

A fighter on a spiked machine, hp 2. Run at **2.0 px/frame** (state 8, 114 of 114 frames) and hit with C11 (reach 48, 12 damage: 4 of 4 charges); var 0 and var 1 differ in the hop (state c/d, 1.0 and 1.5 px/frame). Killing one leaves **two type 27 wreck records** (var 0/1) that explode on contact: lab P1 lost **10 hp in each of the 8 rider deaths** that happened next to it (the two wrecks overlap P1 within 9 frames of the death, `-10` events in `expA_agg.py`). Contact costs the rider 1 hp (13 and 7 events). Score 200/400/400 (type 21: 100/300/300).

## 4. Bosses and their helpers

Common boss traits (read, lab for the numbers): state 0 sets `$80040` bit 2 (event running), the lock bit `$80400` bit 5, +0 bit 3 (invulnerable until the camera arrives: `cmpi.w #$500,$8040a` for types 9 and 10), `bset #7,$80041` for the **last** boss of a level only (types 14, 15), loads an asset set through `$1c8a` (this routine is a palette/tile copier, not a spawner: `architecture.md` and the first fingerprint call it "spawn"), and writes its hp to `$8005c` every frame (the "ENEMY" bar). Death (`$23cf2`/`$23e66`): state 2 or 4 arc, then `+30` counts `$40` frames, then `bclr #2,$80040`, `bclr #5,$80400`, load asset set 57, and if `$80041` bit 7 was set clear it and **set `$80040` bit 3**.

### 4.1 Level 0

**Type 9, the armoured cyborg** (silver armour; trigger `$500`, lock cell). hp 16, spawns off screen in state 0 and jumps in (state c, 3.0 px/frame) when `$8040a >= $500`. Moves 1.0 px/frame (state 7), hops 2.0 (8), melee C5 (state b, reach 40, 12 damage, 2 hits: 10 of 10 hits 12) at d about 25 to 57, and a long beam C4 (states d, e, f, 10: reach 80 px, box 8 px high, 64 animation frames, 20 damage on Normal, *read*; the lab entered these states at d = 135 to 167, outside the 80 px reach, so no beam hit was observed) with a cycle of about 90 to 130 frames. Every light hit put it into state 1 (16 pokes, hp -1 each; the 16th put it in state 2 at frame 2697 and the flags changed 129 frames later: `$80040` `$84` -> `$80`, lab `9_0_h`). Score 200/400/1000. nat0: fight from frame 4675 (camera `$502`) to 6803, 2128 frames with assist hits.

**Type 14 + 56 + 54 + 55: the statue boss.** Phase 1 type 14 (hanging figure on a green cable, spawned at (`$8dc`, `$140`) when the camera reaches `$7c0`, hp 24, last boss: sets `$80041` bit 7): waits in state b until the player is within `$70` px to its left, drops (state 9 arc 2.0 px/frame, lands 66 px from P1 in the lab), and its child type 56 (the cable) grabs: **20 damage every ~160 frames** (hit object C29 by the child; lab 14_0_n: 4 events 20 at 1135, 1295, 1456, 1616 = spacing 160 or 161). Natural run: 9 grabs in 1500 frames until the assist hit. The first hit (hp 24 -> 23) makes it spawn type 55 var 0 (hp 1 minion) and **transform into type 54** (hp 23): the silver boss body, 1.5 px/frame walk, C attacks of 16 (state b) and 12 (c) plus a charge (state f), brain-driven, and it spawns type 55 var 1 (hp 1, 1.5 px/frame, latch for 1 hp per 16 frames) at intervals (3 times in the natural run). The state-b hit of type 54 took 16 hp in 4 of 4 observations (`nat0` frames 12219 to 12282); the 1-hp ticks of type 55 came every 16 frames. Death of type 54: `$80040` 84 -> 88 (nat0, frame 14626), the players enter action `$f` (victory pose) and bit 4 comes 256 frames later (frame 14882). Score of type 54: 200/300/10000 (read).

### 4.2 Level 1

**Type 10, the spiked roller** (orange spiked ball; trigger `$500`, lock cell). hp 16 (maximum), enters rolling (state 7 -> 8) at **2.0 px/frame**; the roll (state 8, up to 128 frames) damages P1 by contact (**-1**, 5 of 5 rams) and **costs the roller 1 hp each ram** (lab `10_0_n`: hp 16 -> 15, 14, 13, 12, 11, 10 at 1069, 1392, 1726, 2387, 2721, 3055 with P1 standing still; the armour flag +51 bit 1 turns a ram into a knock-back, state e). It also fires hit object C6 (state 12 -> 13, 64 frames, reach 56: -1 in 4 of 4) and jumps (states 9, 14: 1.5 to 3.0 px/frame). So the boss kills itself on a passive player in about 16 rams. Light hits cost it 1 hp each. Its own hit routine `$136b8` does not stop at 0 when the armour flag is set (health wrapped to 254 in the assisted run: **open**, the assisted poke path differs from a natural hit, see 8.4). Score 200/500/1000.

**Type 28 + 45 to 50: the helicopter** (trigger `$700`, var 0, at (`$700`, `$80`); level 2 has it with var 1 at `$800`). The body (type 28) spawns six part records: 45 (hp 0, rotor/door), 46, 47 and 48 (hp 32, 32...), 49 (hp 48), 50 (hp 16, the pilot or cannon). It carries `$80400` bit 5, lowers into the arena (y `$80` -> `$164`) and drops type 0 var 5 soldiers (hp 2) and hurts P1 for 1 by contact of the parts (lab 28_0_n: 3 events of 1 within 50 frames). Parts die with their own hp; the level continues after all of them are gone (open).

**Type 15, the gang leader** (last boss of level 1, trigger `$7e0`, at (`$920`, `$1c0`)): hp 24, +35 bit 2. Stands in state f and every **64 frames** (lab: waves at 1071, 1135, 1199, 1263...) spawns a wave of 3: type 1 var 3 at the right edge (`$150` lane), type 2 var 3 at the left edge and type 0 var 4 at the left edge (the throttle of 5 live does not apply to these spawns). It attacks with C7 (reach 48, 24 damage on Normal, *read*; the lab showed only 1-hp contact events from the soldiers). Score 200/300/10000.

### 4.3 Level 2

**Type 11 -> 32 (+33, 34): the strongman** (bald, red trousers, green vest; trigger `$500`, lock cell). Type 11: hp 32, brain driven, hits with C (state b, c: 12), a lunge with C17 (state d, 16 damage), jump attack (e). When hp <= 16 and in state 6 it **replaces itself by type 32** (`$1438c`: spawns a record of type `$20`, copies direction, erases itself): type 32, hp 16, 2.0 px/frame, throws type 33 and 34 objects: type 34 (hp 1, vx +-4.0, vy 2.0) flies like a knife (1 damage per hit; 32 spawned in the natural run) and touches for 1. Total 16 + 16 = 32 hits. Score 200/500/2000, then 300/500/2000. (C32, 48 damage on Normal, the largest entry of the table, is not referenced by these types.)

**Type 28 var 1 + parts, soldiers type 0 var 5/6** (trigger `$800`): as 4.2. The level script's last entry is type 23 var 2 at (`$b40`, `$160`) with trigger `$a00`; in the lab type 23 spawns type 16 (hp 32), 52 and 37 effects and hits for 20; the scroll map blocks the camera at `$a00` (always-locked cell) so the bot never triggered it (**open**: how the camera passes `$864`, section 6).

## 5. Naming table

| type (var) | what it looks like | role | evidence of the name |
|---|---|---|---|
| 0 (0) | long-haired thug, olive/green clothes | charger, touch damage only | sprite crop `portraits_l0.png` + code |
| 1 (1) | same, blue | weapon swing C0 | same |
| 2 (2) | same, magenta | weapon swing C1 | same |
| 3 | fat man, green tank top, white boots | bruiser, grab, 8 hp | sprite |
| 4 (0/1) | stocky, olive jacket | puncher / grappler | sprite |
| 5 (0/1) | blue armour, jet pack | hovering swordsman | sprite |
| 6 (0/1) | orange dog | runner / leaper, latches | sprite |
| 7 | bare chest, jeans | thrower | sprite |
| 8 | khaki fatigues, crouching | thrower | sprite |
| 9 | silver armour | mid-boss L0 | sprite |
| 10 | orange spiked ball | mid-boss L1 | sprite |
| 11 / 32 | bald man, red trousers, vest; then chain | mid-boss L2 | sprite |
| 14 / 54 / 55 / 56 | cable on the statue; silver boss; silver minions; the cable | boss L0 | sprite + code |
| 15 | not seen on screen in a clean crop | boss L1 | code only |
| 20 / 21 | rider on a spiked machine | charger | sprite |
| 28 / 45-50 | helicopter and its parts | event L1/L2 | sprite |
| 23 / 16 / 52 / 37 | intro object, boss (hp 32), effects | end of L2 | code + lab |

## 6. Camera, lock, level end

### 6.1 The rule (read, lab, nat; this replaces the first brief's "scroll stops while enemies of the script group live")

1. The camera is driven by the players: a player whose x reaches `sx + $90` (with a 4 px hysteresis) sets `$80400` bit 1 (scroll right, `$a792`) **unless `$81e03` bit 7 is set**. That flag is set by the pool A dispatcher every frame in which 5 or more pool A records are active (`$10254`) and by a few handlers of levels 3-5. nat (`enemylog.lua`, level 2, lane-filter bot, frames 2900 to 7500): `$81e02/03` read `0580` (5 alive, flag) in the sampled frames 3400, 5150 and 5400 where `$8040a` had stopped (`$270`, `$381`, `$382`) and the camera moved again once the count fell (`$02aa` at 3650, `$0419` at 5650). A group of fewer than 5 live enemies does not stop the camera by itself.
2. `$8876` reads a scroll map per level (`$8908[level]`, 16 words per row, index `((sy_hi-1)*16 + (sx_hi-1))*2`; `py/scrollmap.py`): low nibble = allowed directions, `$20` bit = lock cell (locks only while `$80400` bit 5 is set), `$80` bit = always locked. A boss sets `$80400` bit 5 in state 0 and clears it when it finishes dying (`$23e36`/`$23f86`). Lock cells in row 1 (column c is camera `(c+1)*$100`): level 0 columns 1, 4 (`$500`), 10, 12, 14, wall at column 7 (`$800`); level 1 columns 2, 4 (`$500`), 6 (`$700`), 10, 12, 15, wall at 7; level 2 columns 2, 4 (`$500`), 7 (`$800`), 15, wall at 9 (`$a00`). The wall columns are `800f`, the lock columns `200d`.
3. Consequence for the fights: the arena locks (nat: `$80400` = `a2` at the level-2 mid-boss, `$8040a` frozen at `$501`) exactly in the cells the bosses sit in; bosses 9 and 10 (cells `$500`) and 11 (`$500`) hold the lock until they have been dead for `$40` frames.
4. "The camera does not move" in the bot runs was mostly the bot (it stood next to an unreachable hover enemy at y `$140`, the first level-2 run: 17000 frames; the lane filter of `enemylog.lua` fixed it).

### 6.2 Level end (read + nat0)

`$80040` bit 3 (set when a boss that raised `$80041` bit 7 finishes dying) makes each player enter action `$f` (victory pose). The pose routine (`$c6d8`..) counts 16 ticks x 15 (levels 0, 2, 5: `$c83a`..`$c86a`) or 16 x 12 (`$ca3e`..`$ca6e`) and then sets `$80040` bit 4: nat0 boss death at frame 14626 (`f40` `88`), P1 action `$f` at 14627, bit 4 at 14882 (255 frames). The main loop sees bit 4 at `$6f4` and runs `$71c`. `$20bd4` belongs to pool A type 72 (levels 3-5), `$c86a` and `$ca6e` are in the **player** handler, not objects: a correction to the brief.

### 6.3 Spawn ordering notes
List A entries are processed strictly in list order, one per frame; an entry whose trigger is above the counter blocks the later ones (level 2 contains `0680`, `06e0`, `06c0`: the `06c0` entry waits for `06e0`). The 16-record pool and the 5-alive flag mean an entry can be skipped when `$f388` finds no record (3 level-2 entries below the reached camera position were not matched in the log, e.g. entry 2, type 5 at `$120`; whether the spawner skipped them or the matcher lost them after the record moved is open).

## 7. Proven items

| claim | count | script |
|---|---|---|
| level 0: 42 of 42 list A entries spawn in order at their trigger | 42/42 | `census.py` |
| walking and attack speeds equal the code constants | 80+ (type,state) cells | `expD.py` |
| every light hit costs 1 hp, `$88` costs 4, hits in states 1, 2 ignored | 15 type/variants, 450 pokes | `expB.py`, `expB_kd.py` |
| score table (hurt, kill) | 130 hits | `expE.py` |
| attack damage per hit object (Normal) | C0 12/12, C1 28/28, C2 6/6, C12 11/11, C13 7/7 | `expA_agg.py` |
| contact: 1 hp to P1, 1 hp to the enemy, score to P1 | 62 events, types 0-3, 20, 21 all | `expF_contact.py` |
| attack trigger distances of types 0, 1, 2, 4 | 4/4, 4/4, 12/12, 3/3 | `expA_agg.py` |
| statue boss cable: 20 damage every ~160 frames | 4 intervals of 160/161 | `expC.py`, `bosslog.py` |
| roller rams cost itself 1 hp | 6 of 6 | `expC.py` |
| leader waves every 64 frames | 4 waves | `expC2.py`, `bosslog.py` |

## 8. Open items and corrections

1. Level 1 and 2 ends were not played through: the bot did not pass the L1 roller fight (the assisted poke path does not reproduce a natural kill, 8.4) and stuck in L2 at x `$342` after a jump (an artifact: P1 stays in action 7 with +0x39 bit 7). The helicopter and the type 23 sequence are lab-only.
2. Type 15 has no clean portrait; type 23, 16, 52, 37 are only fingerprinted.
3. The per-distance probabilities of `$2438a` are not tabulated (`py/brain.py` dumps the structure).
4. Type 10's `$136b8` hit path: health went to 254 under assisted hits while its armour flag was set; not resolved.
5. Hit-strength dependence of the knock-down chance: read but only 7 lab hits per cell; run `expB.py` with more cycles to firm up.
6. P1's escape from the type 4 grab and the dog latch is not observed (the lab P1 never presses buttons).
7. Pool B props (list B) are only counted.
8. Errors in the brief: `$1c8a` is not a spawn function; `$c86a`, `$ca6e` are player code; the screen lock is not "while enemies of the script group live" (6.1); P1's score is at `$8013c`.

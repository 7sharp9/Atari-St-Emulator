# Crude Buster: the grunts of levels 3-5 (pool A types 0x35, 0x39, 0x3f, 0x40, 0x44)

Group GRUNTS of ENEMIES2. Addresses are 68000 addresses of the decrypted `cbuster` image. Level numbers are `CB_LEVEL` / `$80046` (0-5), so "level 3" is the fourth stage.
Every claim carries a count and the script that reproduces it (scripts in `py/` and `lua/`, runs in `out/<run>/`, see `README.md`), or is labelled *read* (from the listing, not run) or *inferred*.
Run lengths and counts below come from `lua/probe.lua` runs (isolated enemy, `CB_NOSCRIPT=1`, P1 health kept high by a heal that is applied after the damage is logged).

Descriptive names (from the sprite in `out/sheet_types.png` / `out/sheet_attacks.png` and the body of the handler; not the developers' words):

| type | handler | working name | what it draws and does |
|---|---|---|---|
| 0x35 | `$1c4f4` | heavy brute, "ledge fighter" | bald bare-chested wrestler. Variant 0 is a stationary sentry (state `$11`) with a long strike box; once hit it becomes a mobile grab/jump fighter |
| 0x39 | `$1d494` | clinger | lean fighter in brown shorts. Walks at the player, two-punch combo; a body bump makes it leap onto the player and drain health until shaken off |
| 0x3f | `$1e9f4` | flamethrower trooper | grey armoured soldier. Stab, back-flip, forward leap, and an 88-frame flame jet (pool C type 4, reach 80 px) |
| 0x40 | `$1ec1c` | kickboxer | white-haired man in black trousers. Four kicks/punches (boxes `$25 $26 $27 $28`), a dash |
| 0x44 | `$1faac` | whip man | muscular man in red vest, yellow whip. Four attacks (boxes `$0f $10 $11 $12`), a jump attack; only runs while the vertical scroll `$80406 >= $200` |

## 1. Machinery these five types share

### 1.1 The handler frame (read, confirmed by the live state traces)
Each handler is `[type specific hit reaction] / $22dac / state dispatch on +3 through a 24-entry longword table / $23fc8 / $22540 / $2331c / $2242c`.
Hit reaction: 0x35 `$24022, $22ce4` (like `$22c56` but a hit during the grab states b/c/d is ignored), 0x39 own `$1d534` (no `$24022`, so no 16-frame immunity: `py/immune.py` finds no window in `out/a39_0`), 0x3f/0x40/0x44 `$24022, $22c56`.
The 0x44 handler returns at its first instruction while `$80406 < $200` (`cmpi.w #$200,$80406 / bcs $1fae6`): in a level whose vertical scroll counter stays at `$100` (all of level 3) a 0x44 record is never processed
(live: `out/s_441`, 61 frames, state 0, health 0, nothing initialised; with `SY=200` in level 4 it initialises and fights: `out/p44_l4`).

### 1.2 Shared state routines (cited by address in the per-type tables)
| state | routine | role (read; the first three confirmed live) |
|---|---|---|
| 1 | `$234e6` | stagger. Weak: pushed back 0.5 px/frame for 16 frames (state 1 lasts 15 logged frames), then state 6 with `+17` bit 3 set (starts the 16-frame immunity of `$24022`, below). Roll (knock-back flight): two arcs of 2.0 px/frame and 66 frames in all (state 1 lasts 65-73 frames). The roll starts always on a strong hit (`+6` bit 3, health -4) and otherwise, when the hit kind `+6 & 3` is non-zero, when `$ea44 & 3 == 3` (*read*: 1 in 4) |
| 2 | `$2397e` | death: arc backwards (param `$40`, or `$80` when `+6` bit 1), vx +-3.0 px/frame (+-8.0 when `+6 & 3` is non-zero), then falls at 5.0 px/frame until `$2242c` removes the record off the screen. 56-64 logged frames (71 after a throw kill, state 4) |
| 3 | `$22ecc` | held by a player (follows the player); `+17` bit 1/2 set: hits are ignored |
| 4 / 5 | `$23ac0` / `$23748` | thrown, died (4) or alive (5): flight and landing, `$233cc` / `$2436a` spawn the landing dust |
| a | `$23248` | fall: 4.0 px/frame down, 0.5 px/frame sideways, landing probe `$22a4a` |
| b c d | `$2409a` `$24126` `$24286` | the grab sequence: b checks the target (player y within `$10`, player state < `$a`), c seizes the player (writes player `+1 = $20`, `+4 = $b`, flag `$80158` bit 7, link `$80160`), d throws (`$80158` bit 6). Used by 0x35 only |
| 6 | `$1453e` (0x40 0x44) | ready/idle: `$226e4` probe; on an animation wrap, target state < `$d` -> chooser `$2438a`, else stay |
| 7 | `$145ae` (0x40 0x44) | walk toward the target at 0.5 px/frame, chooser every frame |
| 8 | `$14624` (0x40 0x44) | walk away from the target at 0.5 px/frame for `$80` frames (counter `+30`), then chooser |
| 9 | `$146a0` | jump: 0.5 px/frame sideways, arc via `$22856` with the jump parameter `+36` (`$2280c`: `$20` + height difference to the target, or `$22844`: literal), lands with `$228f4`/`$2297a` -> state 6 or 7 |
| `$17` | `$22e30` | held variant |

Observed per-frame steps (`py/speeds.py`, 16.16 position longs): walk state 7: 0x35 +-0.5, 0x39 +-1.5, 0x3f +-1.0, 0x40 and 0x44 +-0.5 px/frame; state 8: 0x39 -1.0, 0x44 +0.5, 0x3f backflip +-2.0 with dy up to 7 px/frame;
0x3f state c leap +-3.0; 0x44 state d jump +-1.25; 0x35 state e jump +-1.0, state f +-0.25, state 9 -0.5; 0x40 state d dash +-2.0 (*read*, `$16456`).

### 1.3 Hit, damage and score rules (corrections to the brief)
* **Damage to the player is indexed by the pool C box type, not by the owner's pool A type** (`$fc80`: `move.b 2(A6),D0` with A6 the pool C record). The aliasing caveat of the brief does not apply (pool C types are < `$2c`).
  Damage = byte x 4 health points from the table chosen by `$80054 & $c`. MAME's default dip is `$80054 = $80` (`I 800 dip=8000` in `out/dd39/probe.txt`), so the first column applies. `py/dmg.py` prints the whole table (`out/dmg.txt`).
  Measured 13 of 15 box types equal the table (not observed: `$10`, `$27`; e.g. `D 796 38 -> 24` = 20 for box `$24`; 0x40 boxes 16; 0x44 boxes 12/12/16/12; 0x3f box 5 = 12 and box 4 = 20; 0x39 boxes 0 and 1 = 12).
* **Contact damage**: `$2331c` calls `$f4f4` for every enemy whose `+17` bit 2 is clear. When the enemy body (`$6b000[type][state]`) overlaps a player body, `$f700` subtracts `$f78e[type]` (1 for all five types, no x4) from the player, spawns a hit spark (pool B `$2b`), and writes `+6 = $90` into the *enemy*:
  the enemy takes the ordinary hit reaction (health -1, state 1, **and the player is paid the "hit" score**). Live: every `D ... pc 00f76e` line is a 1 point drop (`py/stats.py`: 7 of 7 for 0x3f, 6 of 6 for 0x35 var 2) and the matching enemy health drops all show `flags6=90` (`py/hpdrops.py`).
  In the clinger the same bump is what starts the cling (below). A contact never starts a knock-back roll (0 of 23, `py/stagger.py`), because the hit kind bits are 0.
* **Player attack**: a normal punch is `+6 = $81/$82` (kind 1/2): health -1, state 1. A strong hit (`+6` bit 3) is health -4 and rolls (poke `+6 |= $88` in `out/r39 r3f r40 r35`, 4 of 4 -4 steps). Throw: `+17` bit 6 (poked `$40`) = health -4, state 5 (health left) or 4 (dead): `out/r3f`
  (8 -> 4 -> 0 = state 4, score `$1000`), `out/r35` (state 5, +100). Every one of the 32 enemy health decrements logged in the four bot runs `out/a39_0 a3f_0 a40_0 a35_2` was -1 (`py/hpdrops.py`; 29 punches and 3 contact bumps (`flags6=90`)). How a real player produces a throw I did not reproduce (open, section 5).
* **Score** (`$248bc`, called from every hit reaction): `$24952[type*4]` = (hit, thrown-alive, death, sound), BCD long added to P1 `$8013c` by `$3fae` (P2 `$801bc`). The score is added on **every** hit that lands, not only on the kill. The hi score `$80010` (1,000,000 at start) did not move (scores < 1,000,000).
  Verified on the live score steps (`out/a39_0 a3f_0 a40_0 a35_2 p44_l4`): 0x35 50 per hit, 500 on death (12 steps of 50 then 500 = 1050 BCD); 0x39 200 per hit, 400 on death (3 x 200 + 400 = 1000); 0x3f 200 / 1000 (7 x 200 + 1000 = 2400); 0x40 200 / 3000 (7 x 200 + 3000 = 4400); 0x44 400 per hit (steps of 400, `out/p44_l4`; kill not reached in that run, death 3000 from the table).
  Thrown-alive: 0x35 100 (verified `out/r35`), 0x39 400, 0x3f 400, 0x40 300, 0x44 600 (table only). The sound byte is 0 = a random hit voice (100/101/103).
* **Immunity after a stagger**: `$24022`: `+17` bit 3 (set when the stagger ends) -> `+0` bit 3 for 16 frames; `$22c56`/`$22ce4` discard hits while `+0` bit 3 is set. Measured run lengths of `+0` bit 3: 15 frames for 0x3f (3 of 3), 0x40 (7 of 7), 0x44 (5 of 5); 6-7 frames for 0x35 var 2 (8 of 8, cause not traced, `py/immune.py`).
  The riders (var 1/2/3 states) also hold `+0` bit 3 from init until they jump off, so they cannot be hit while riding (*read*).
* **Drops**: none. After 6 of 6 kills (`out/k39 k3f k40 k35 k44 k35s`) no pool B record other than the hit spark `$2b` and, for 0x35 only, the landing dust `$51` (`+35` bit 2, sound `$18`) appeared (log lines `B`). The grunts give no items; the items of level 3-5 come from the list B props.
* **Chooser `$2438a`** (correction to the brief): it is called *every frame* in the walk state 7 (and from state 6 on an animation wrap, and from state 8 after 128 frames), not only on an animation wrap. The randomised leaf routines gate on `+1` bit 7 (animation wrapped), the plain leaves do not.
  `py/chooser.py <type> [target state] [sub-state]` expands it (outputs in `out/chooser_*_sub{0,4}.txt`). dx is the horizontal distance to the target, the row index is `dx >> 4`, dx >= 256 -> state 7.
  Table T1 (same lane) is also keyed by the target's state `+46 & $f` and sub-state `+47` (0-3 = the printed column, 4-7 = the next column); T2 = enemy more than `$60` below the target (`$24644`), T3 = enemy at least `$20` above (`$24780`).
  Only 0x35 and 0x3f vary with the target state; 0x40 and 0x44 have flat T1 tables. 0x39 never calls the chooser (own logic).

## 2. Usage in the level scripts (`py/usage.py`, `out/usage.txt`)

| level | 0x35 var 0 | 0x39 | 0x3f var 0 | 0x40 var 0 | 0x44 | carriers (0x1a, 0x17) |
|---|---|---|---|---|---|---|
| 3 | 7 | 6 (var 0) | 3 | 1 | - | 0x17 var `$12`, var `$22` |
| 4 | 3 | 9 (var 0) | 9 | 2 | 1 (var 0) | 0x1a var 0 x4, var 1 x1, var 2 x1 |
| 5 | 2 | 6 (var 0) + 9 (var 3) | 6 | 2 | 2 (var 0) + 2 (var 1) | - |

Only variants that the script uses are in the table; riders (var 1/2) are created by carrier objects:

| spawner | spawns | evidence |
|---|---|---|
| type 0x1a (`$19344`, init `$1946e`; moves +2.0 px/frame, health 1) var 0 | 0x39 var 1 and 0x39 var 2 | `out/c1a_0` |
| 0x1a var 1 | 0x35 var 1 and 0x39 var 2 | `out/c1a_1` |
| 0x1a var 2 | 0x3f var 1 and 0x39 var 2 | `out/c1a_2` |
| type 0x17 var `$22` (`$18906`) | boss type `$11`, 0x40 var 1 and var 2, 0x34 var 1 | `out/v17_22` |
| type 0x1f (`$1a2c6`) | random 0x3b-0x3e only (table `$1a818`), not these types | read |

(`py/spawners.py` lists every `$21eb6` caller: these five types are spawned only by the scripts, 0x1a and 0x17.)
In `out/c1a_*` (player at x `$240`, carrier from `$1c0`) the riders stay on the carrier (state e / `$12` / `$11`, 22-38 frames) and jump off when the player is within `$40` px (state 9, 64 frames, then a fall of 4 frames, then 6): 3 of 3.
A rider that is not near the player vanishes with the carrier when it leaves the screen (`out/c1a_*` with the player far: both riders gone at frame 827-839).

## 3. The types

### 3.1 Type 0x35, heavy brute / ledge fighter (`$1c4f4`)

**Init `$1c59a`**: health `$0c` (12; live 12 in 12 of 12 spawns), `+35` bit 2 (heavy: landing dust), `+0` bit 6 (hittable), `+53` bit 3, chooses a target (`$22b48`).
Variants (read, 0/1/2 confirmed live): var 0 (and any other) `+7 = 1`, state `$11`; var 1 `+0` bit 3, `+7 = 6`, state `$12` (rider); var 2 facing left, jump parameter `$20`, state 9 (jump in; `out/p35_2`: `9x64` then 6).

| state | routine | role |
|---|---|---|
| 0 | `$1c59a` | init |
| 1 2 3 4 5 a `$17` | shared | see 1.2 |
| 6 | `$1c63a` | ready: probe `$226e4`, on an animation wrap and target state < `$d` the chooser |
| 7 | `$110c4` | walk toward the target at 0.5 px/frame, chooser every frame |
| 8 | `$1104e` | wall turn-around idle: the chooser is only called when the state is 6, so nothing leaves state 8. **Observed stuck for 784, 1654 and 1729 frames** (`out/t4`, `out/led_L1`, `led_L2`) |
| 9 | `$1114a` | jump (0.5 px/frame, arc) |
| b c d | `$2409a $24126 $24286` | grab, seize, throw. Observed 5 of 5 sequences 16 + 48 + 16 frames; each throw costs the player 4 (`pc $d442`, 5 of 5, `out/p35_2`) |
| e | `$111cc` | jump attack: vx 1.0, 64 frames, **box `$0d` every frame, 20 damage** (22 hits in 8 attacks) |
| f | `$11254` | advance at 0.25 px/frame, **box `$0c`, 16 damage** (7 hits in 9 attacks), then chooser |
| `$10` | `$112ee` | wait for the animation end (32 frames), then 6 |
| `$11` | `$1c6c0` | **sentry**: turns toward the target (only when |dx| >= `$10`), probe `$226e4`, and spawns **box `$24` every frame** |
| `$12` | `$1c73a` | rider: x = owner + 8, y = owner - `$10`; leaves (state 9, param `$40`) when |dx| < `$40` |
| 13-16 | `$1104e` | |

*Sentry (state `$11`)*. The strike box `$24` exists in the owner's animation frame 3 only: right-facing x +32..+80 from the owner, y 0..+16 (`out/boxes.txt`; left-facing mirrored). The animation is 4 frames of 12 ticks (period 48): the box is live for 12 frames of every 48.
Live (`out/p35_0`, enemy and player on the street lane y `$1c0`, player at dx `$40`): hits at frames 786, 834, 882 (period 48, 3 of 3), each 20 health points (`D ... fc9e 24 ... 35 11`), `ctype 24` spawned on 1750 of 1750 frames. The first hit throws the player out of range, so there are no more hits.
At dx `$80` (outside the box) 0 hits in 1750 frames (`out/p35_0b`).
It is not tied to a ledge: at street level (script positions (`$2f0,$1c0`), (`$5b0,$1c0`), (`$7f0,$1c0`), (`$9c0,$1c0`), (`$3f8,$190`)) it is the same stationary sentry; the two script entries on a ledge are (`$280,$160`) in level 3 and (`$9c0,$150`).
A player on the ledge (y `$160`, x `$250`) is hit (`out/t4`: `D 796 38 -> 24`, `ctype 24 owner 35 state 11`), a player in the street lane under the ledge is not (dy `$60` is outside the box: 0 hits in 1500 frames, `out/t3`).
Whether the player can reach the ledge and how: the lead's bot jumps onto the wall; I did not verify the jump.
*Does it jump down?* Not by itself. A hit leaves state `$11`: after the stagger the state is 6 (the sentry code is not re-entered; the 0x35 never returns to `$11`), the chooser then runs as for a normal fighter.
From the ledge (enemy above the target by >= `$20`, table T3, target idle): dx < 16 stay in 6, 16-63 -> 7 (walk), **64-127 -> state a (it falls/drops to the lane)**, 128-255 -> 7. Live (`out/led_L1..L4`, one weak hit poked at frame 800, `+6 |= $82`): in 3 of 4 runs it drops to the lane (state a, 24 frames, from y `$160` to `$1c0`; player at (`$230,$1c0`), (`$200,$1c0`) and on the ledge (`$250,$160`));
afterwards it fights (L4) or sticks in state 8 at x `$26f` (L1, L2). In the fourth run (player at (`$2b0,$1c0`), dx `$54`) it stays on the ledge, state 6 for 1691 frames and x `$25c` (the chooser should give state a for dx 64-127; the player's own state may have blocked it, not traced).
A knock-back roll along the ledge (`out/t4`: strong hit, 66 frames in state 1, moves +2.0 px/frame to x `$2f7`, y unchanged) leaves it on the ledge, then state 8 for 784 frames.

*Chooser* (target idle, sub-state 0; `out/chooser_35_sub0.txt`): same lane (T1): dx 0-31 -> 6 (0.5), b (0.25), f (0.25); 32-47 -> 6, b, e, f (0.25 each); 48-79 -> `$10`, 6, e, f; 80-255 -> `$10` (0.25), 7 (0.75). Enemy below the target (T2): dx < 16 -> 6, 16-63 -> 7, 64-127 -> jump 9, else 7. Enemy above (T3): as T2 but 64-127 -> a.
Measured transitions out of state 6 (`py/trans.py 35` over 3 runs, 65 events): -> e 15, f 18, `$10` 13, b 5, 7 4, hit 9, death 1.
Frequencies (`out/p35_2`, 2751 frames, passive player): b/c/d 5, e 8, f 9, `$10` 3 = 25 attacks in 2751 frames (9 per 1000 frames). Damage taken by the player in that run: box `$0d` 440 points (22 hits), box `$0c` 112 (7), throws 20 (5 x 4), bumps 6.
*Reactions*: weak punch -1 -> state 1 (15 frames) -> 6 (7 frame immunity window); strong hit 12 -> 8 -> 4 (`out/r35`); throw +100 and health 8 -> 4 in state 5. Death after 12 punches (`out/a35_2`: states end `... 10x9 2x15`), score 500, no drop but dust (`B 840 4 51`).

### 3.2 Type 0x39, clinger (`$1d494`)

**Init `$1d61e`**: health 4 (live 4 of 4), `+0` bit 6, `+53` bit 3. Variants (0/1/2/3 live):
var 0 `+7 = 2`, state 6; var 1 and var 2 `+0` bit 3 (immune), `+7 = 6`, state `e` (rider; var 2 sits at owner x - 8, var 1 at owner x + `$18`, both y - `$10`; leaves with state 9, param `$40`, when |dx| < `$40`);
var 3 `+0` bit 3, facing left, jump parameter `$40`, state `f`.

| state | routine | role |
|---|---|---|
| 6 `$10`-`$16` | `$1d6ba` | idle 8 frames, probe, then 7 when the target state < `$d` |
| 7 | `$1d74c` | **walk toward the target at 1.5 px/frame** and decide each frame (below) |
| 8 | `$10b92` | walk 1.0 px/frame in the current facing for `$80` frames, then 7 (after a wall bump; 128 frames live) |
| 9 | `$10c0a` | jump: 0.5 px/frame sideways, arc (param `$20`), 64 frames |
| a | `$23248` | fall |
| b | `$1d8cc` | **punch 1**: box `$00` every frame, 36 frames, then c (13 of 13 b -> c) |
| c | `$1d916` | **punch 2**: box `$01` every frame, 36 frames, then 7 (13 of 14) |
| d | `$1d960` | **cling**: see below |
| e | `$1dab4` | rider |
| f | `$1db42` | jump in: vx 2.0 px/frame toward the facing, arc param `$40`, 63 frames (live: `out/v39_3`, level 5, state f for 63 frames, then 6, 7, a), lands with `$2297a` |

*Decision in state 7* (read, `$1d7b2-$1d8c4`; confirmed by the attack counts): the enemy steps toward the target; it attacks only if |dx| < `$50`, the target's `+50` bit 7 is clear, and the heights fit:
target above by more than `$20` (enemy y > py + `$20`) -> jump (state 9, param `$20`); enemy more than 8 above the target and `+1` bit 0 clear -> fall (state a); otherwise punch (state b) when the horizontal gap is in `[$20, $28)` in front (right-facing: target x - enemy x), else keep walking.
So the punch happens in an 8 px window; with 1.5 px/frame it passes through the window and attacks (14 of 14 state 7 -> b in `py/trans.py 39`).
The player takes 12 per punch hit: box `$00` 16 hits in 13 attacks, box `$01` 4 hits in 13 attacks (`out/p39_0`).

*Cling (state d)*. The reaction `$1d534`: if the hit has `+6` bit 4 (the contact bump `$90`) and the enemy is in state 7 and the target is not in a state that forbids it (player `+0` bit 5 / `$80158` bit 4) the enemy goes to state d, **without losing health and without score** (the generic hit code is skipped).
Live: the single contact of `out/p39_0` (frame 1022, `D ... f76e`) puts the enemy into state d on the next frame and it stays 1616 frames; the poke `+6 |= $90` in state 7 (frame 770) does the same, state d for 630 and 171 frames (`out/shake39 shake39b`).
In state d the enemy glues itself to the player's position (x -`$19` / +`$18`, same y, facing flipped), sets `$80158` bit 4 and the link `$80164`; the player is in state `$13`/`$14` and loses **1 health point every 16 frames** (`pc $d75c`: 100 drops in 1616 frames = 1 per 16.2, `out/p39_0`; 36 drops in 630 frames, `shake39`).
Release: the player mashes a button: b1 at an 8 frame period released the player after about 110 frames (`out/shake39b`: state d x171, player back to state 0 at frame 960) and b2 as well (`shake39c`); left/right wiggling 42 times did not (630 frames, `shake39`). The `d` enemy then dies by its own state 2 (`$1da8a`) **with no score** (no score step in the shake runs).
Player code involved: `$d6da-$d76c` (counts 3 input pulses per 32 frames), the player agent's subject.
The cling also ends if the player's state leaves the range (`$1da8a` again).

*Reactions*: hit -1 -> state 1 (15 frames) -> 6; 4 punches kill (`out/a39_0`: 4 steps of -1, score 200, 200, 200, 400 = 1000); a strong hit kills from 4 (`out/r39`: 4 -> 0, +400); no roll was seen (3 kind-1/2 hits, all weak, small sample).

### 3.3 Type 0x3f, flamethrower trooper (`$1e9f4`)

**Init `$1ea9a`**: health 8 (live 8 of 8), facing right, `+17` bit 0. Variants: var 1 `+0` bit 3, `+7 = 6`, state `$11` (rider; x = owner + `$18`, y = owner - `$10`, jumps off when |dx| < `$40`, state 9 param `$40`); any other: `+7 = 2`, state 6.

| state | routine | role |
|---|---|---|
| 1 | `$13280` | stagger (`$234e6`), then a random next state: if `+17` bit 4 is clear {6, 8, b, c} (table `$132ea`), if set {6, c, d, c} (`$132ee`). Live: 1 -> 8 x8, c x8, b x3, 6 x1 (`py/trans.py 3f`) |
| 6 | `$1eb1a` | ready, 8 frames, then 7 (target state < `$d`) |
| 7 | `$132f2` | walk toward the target at 1.0 px/frame (stops turning inside `$20` px), chooser every frame |
| 8 | `$13378` | **back-flip**: vx 2.0 px/frame *away* from the facing, arc param `$60`, 43 frames, then state d (16 of 16 8 -> d) |
| 9 | `$146a0` | jump |
| a | `$23248` | fall |
| b | `$13426` | **stab**: box `$05` every frame (24 frames), 12 damage (4 hits in 4 attacks, `out/p3f_0`) |
| c | `$13476` | **forward leap**: vx 3.0 px/frame, arc param `$80`, 64 frames, facing flipped at the landing; no box (`+17` bit 2 set: no contact damage either) |
| d e f | `$13520` | **flame jet**: spawns pool C box `$04` once and holds the owner `+51` bit 0 until the animation ends (88 frames), then 6; if the target `+50` bit 7 is set -> `$10` |
| `$10` | `$135a6` | like d, ends at the animation wrap (120 frames), then 6 |
| `$11` | `$1ebb2` | rider |
| `$12-$16` | `$132f2` | |

Flame jet: box `$04` is the visible flame (pool C handler `$220ac`, not `$22040`, it has its own animation `$7f000`); it reaches 48..80 px in front at y -8..0 for frames 1-22 of its own animation, then other ranges (`out/boxes.txt`). Damage 20 (3 hits in 11 attacks; the player usually stands outside the thin box).
`out/sheet_attacks.png` row 2 shows the jet crossing the screen from the trooper at the left edge. The attacker shoots at long range: chooser T1 dx 128-255 (`out/chooser_3f_sub0.txt`).
*Chooser* (target idle, sub 0): T1 dx 0-47 -> 6 (0.5), b (0.25), c (0.25) (only on an animation wrap); 48-63 -> 7 (0.5), b (0.5); 64-127 -> 7; **128-255 -> `$10` (0.125), 7 (0.5), d (0.125), e (0.125), f (0.125)**. T2: dx < 16 and 64-127 -> jump 9, else 7. T3: dx < 16 and 64-127 -> a, else 7. dx >= 256 -> 7. Sub-state >= 4 of the target moves every row one column (closer).
When the target's state is `$d` or more the long-range row (64-255) is absent.
Frequencies (`out/p3f_0`, 2751 frames): b 4, d 11 (+ 1 `$10`), c 2 attacks and 11 back-flips (all after a hit). Player damage: box 5 4 hits = 48, box 4 3 hits = 60, bumps 7.
*Reactions*: -1 per punch -> state 1; 8 punches kill (`out/a3f_0`: 8 steps, score 200 x 7 + 1000; also `out/b3f_2` with b2 only = jump/flying kicks, 6 steps of -1, all `flags6=90`, i.e. contact bumps). Strong hit 8 -> 4 -> state 1; throw at health <= 4 -> state 4, +1000 (`out/r3f`).
Player b3 near the enemy **holds** it: state `$17` (19 frames) then state 3 held, observed 941 frames until the end of the run (`out/b3f_3`, `t3f_throw`); the player returned to its idle state after about 40 frames while the enemy stayed in 3. A throw input was not found (open, 5).

### 3.4 Type 0x40, kickboxer (`$1ec1c`)

**Init `$1ecc2`**: health 8 (live 8 of 8), facing left (`+4 = 1`), `+17` bit 0, `+7 = 0`. Variants: var 0 state 6. Var 1/2: riders of the boss `$11` created by type 0x17 var `$22` (`out/v17_22`): `+0` bit 3, facing right, attached to the owner at x - `$40` (var 1) / x - `$28` (var 2), y - `$28`,
**stay in state 0 until the owner's x >= `$a80` (var 1) / `$a90` (var 2)**, then state a (fall) and a normal fight; live: state 0 for 191 and 207 frames, then a x34, 6 (the script has only var 0, 1 of 1 in level 3, 2 in level 4, 2 in level 5).

| state | routine | role |
|---|---|---|
| 1 | `$163b8` | stagger, then random: `+17` bit 4 clear {b, c, d, e} (`$16436`), set {6, 6, d, d} (`$1643a`); d sets the jump parameter `$20` first. Live from 1: b 2, c 1, d 3, e 1, 6 1 |
| 6 / 7 / 8 / 9 | `$1453e / $145ae / $14624 / $146a0` | shared, 1.2 |
| b | `$1643e` | box `$25` via `$24056` (24 frames), 16 damage (21 hits in 14 attacks, `out/p40_0`) |
| c | `$1644a` | box `$26` (24 frames), 16 (17 hits in 11 attacks) |
| d | `$16456` | **dash/leap**: vx 2.0 px/frame; `+37` runs 0..`$fa` in steps of 4 (63 frames): an arc while < `$7f`, then a run on the ground; **box `$27` every frame** (20 damage); after the arc `$2434a` spawns a trail object (pool B `$37`) every 4th frame (*read*) |
| e | `$16540` | **four-hit combo**: box `$28` via `$24056` (72 frames), 16 per hit, active in 8 animation frames (`out/boxes.txt`): 17 hits in 7 attacks |
| f-16 | `$1453e` | |

*Chooser* (flat in the target state): T1 dx 0-31 -> 6, b, c, e (0.25 each); 32-47 -> 7, b, c, e; 48-95 -> 7; 96-111 -> 7 (0.25), d (0.75); 112-143 -> 7; 144-175 -> d (0.75), 7; 176-255 -> 7. T2: dx < 16 -> jump 9, 16-63 -> 7 (`out/chooser_40_sub0.txt`).
Frequencies (`out/p40_0`, 2751 frames): b 14, c 11, e 7 (32 attacks, 11.6 per 1000 frames); measured transitions from state 6: -> b 14, 7 9, c 9, e 7 (no d from 6 at dx < 32, as the table says; d comes after a stagger and at dx 96+).
Player damage in that run: boxes `$25` 21 x 16, `$26` 17 x 16, `$28` 17 x 16, bump 1 (heals applied); the player has 56 points, so 4 kickboxer hits kill.
*Reactions*: -1 per punch (8 punches kill, `out/a40_0`, 200 each, then 3000); strong hit/throw as for 3f (`out/r40`: 8 -> 4 -> 0, +3000).

### 3.5 Type 0x44, whip man (`$1faac`)

**Gate**: the handler body only runs when `$80406 >= $200`. **Init `$1fb5c`**: health 8 (live 8 of 8), facing left, `+17` bit 0, `+7 = 2`. Variants: var 0 waits in state 0 *until the horizontal scroll counter `$8040a` reaches `$500`* (the check is repeated every frame), var 1 goes to state 6 at once, any other variant (>= 2) goes to state `a` (falls into the scene).
Level 4 has one var 0 at (`$4e8,$250`) triggered at `$500`: it starts fighting immediately (the counter has just reached `$500`). Level 5 has two var 0 at the very start (triggers `$140`, `$160`, positions (`$260,$7c0`) and (`$280,$760`)) and two var 1.
In state 0 the enemy is already hittable (`+0` bit 6 set in the init; in the level-5 bot run `out/l5bot` the first one was hit and left state 0 after 199 frames; the second stayed in state 0 for 3684 frames with health 8): the two var 0 whip men of level 5 stand idle (`out/shot_l5_1250.png`) until hit or until the scroll counter passes `$500` (state 0 observed 3684 of 3684 frames when not hit).
Whether they hold the scroll lock while idle is the lead's subject (they are counted among the live records; with 4 alive nothing scrolled in that run).

| state | routine | role |
|---|---|---|
| 1 | `$144b8` | stagger, random: `+17` bit 4 clear {6, 6, d, e} (`$14536`), set {6, 6, 6, d} (`$1453a`); d sets jump parameter `$40`. Live from 1: 6 x2, d 1, e 2 |
| 6 / 7 / 8 / 9 | shared | |
| b | `$14722` | box `$0f` via `$24056` (16 frames), 12 (3 hits in 3) |
| c | `$1472e` | box `$10` (16 frames), 12 |
| d | `$1473a` | **jump attack**: vx 1.25 px/frame, arc up to `$40`, 43 frames, **box `$11` every frame**, 16 damage (13 hits in 7 attacks) |
| e | `$147d8` | **whip**: vx 0.25 px/frame, box `$12` via `$24056`, multi-frame (alternating high/low boxes in `out/boxes.txt`), 12 per hit (4 hits in 4 attacks), 64 frames |
| f-16 | `$1453e` | |

*Chooser*: T1 dx 0-15 -> 6 (0.5), b, c; 16-31 -> 6, 8, b, e; 32-47 -> 6 (0.5), c, d; 48-95 -> 7 (0.75), d (0.25); 96+ -> 7. T2: dx < 16 -> 6, 16-63 -> 7, 64-127 -> jump 9, 128+ -> 7 (`out/chooser_44_sub0.txt`).
Frequencies (`out/p44_l4`, 1751 frames, level 4 at scroll y `$200`): b 3, c 2, d 7, e 4 (16 attacks, 9 per 1000 frames). Scores 400 per hit (steps of 400 at frames 1476, 1509, 1683, ...).

## 4. Variants and what they change (summary)

| type / var | start state | what changes |
|---|---|---|
| 0x35 var 0 | `$11` sentry | stationary, box `$24` (20) in animation frame 3 (12 of 48 frames), turns toward the target; first hit makes it a normal fighter |
| 0x35 var 1 | `$12` rider | carried by a 0x1a, invulnerable until it jumps off (state 9) |
| 0x35 var 2 | 9 | jumps in (64 frames), then a normal fighter (not in any script) |
| 0x39 var 0 | 6 | walks in |
| 0x39 var 1 / 2 | e | riders at owner x + `$18` (var 1) / x - 8 (var 2) of a 0x1a |
| 0x39 var 3 | f | **staircase of level 5**: nine entries (trigger `$800`..`$a00`, 0x40 px apart in x and y, y `$440` falling to `$240`), each starts facing left and jumps -2.0 px/frame for 63 frames on an arc of height `$40`, then walks/fights (`out/v39_3`). They do not form a sequence in the code: each is an independent jump-in staggered only by its script trigger |
| 0x3f var 0 / 1 | 6 / `$11` | var 1 is a rider (x + `$18`) |
| 0x40 var 0 / 1 / 2 | 6 / 0 / 0 | var 1 and 2 are riders of the `$11` boss, released at owner x `$a80` / `$a90` |
| 0x44 var 0 / 1 / >=2 | 0 / 6 / `a` | var 0 waits for `$8040a >= $500`; the handler needs `$80406 >= $200` |

## 5. Open items

* **Throw**: I found how the player holds an enemy (b3 within reach: state `$17` then 3) but no input that throws it. State 4/5 behaviour was verified by poking `+17` bit 6 (and `+6` bit 3 for a strong hit), not by a real throw.
* **Ledge reach**: not verified that the player can jump onto the level 3 ledge (the lead's bot does).
* 0x35's 6-7 frame immunity window (against 15 for the others) is measured, not explained.
* **State 8 of 0x35 is terminal**: observed in 3 runs (784, 1654, 1729 frames, `out/t4 led_L1 led_L2`), all next to the building wall of level 3 (x `$26f` on the street, `$2f7` on the ledge), never in the open-street runs (`out/p35_2`, `a35_*`); the exit (if any) is not known. It could keep the level 3 scroll lock closed; test with the real script before relying on it.
* 0x3f state `$10` vs d: the condition (target `+50` bit 7, i.e. player `+$139`) was read, not exercised.
* Second player (target selection `$22b48`, `+35` bit 7, P2 addresses) was read, not run.
* The exact "roll" rate (code 1 in 4): measured 13 of 34 kind-1/2 hits (38%), small sample.
* Level 5 (0x39 var 3, 0x44 var 0/1) was driven by pokes in an isolated probe plus one natural run (`out/l5bot`), not through a complete natural level.

# L5B: the end of level 5 (final sequence, final boss, ending)

All frame numbers are screen frames of MAME `cbuster` (World FX) with `lua/objlog.lua` (teleport bot, `CB_LEVEL=5`); addresses are 68000 addresses of the
decrypted image. *Proven* = a live run with the count and script named; *read* = from the listing only; *inferred* = neither. Fight lengths depend on the bot;
structural intervals (state lengths, ending offsets) do not. Default dip: `$80054` = `$80`, so `$80054 & $c` = 0 and every damage below is the dip-0 column.

Reproduce everything: `export M68000_ROOT=<M68000>; py/full.sh full` (one cold-boot run to the attract restart, about 2 min; logs in `out/full/`), then the scripts in `py/` (README).

## 1. Who ends a level (the three `$80040` bit 4 setters)

| setter | what it is | used by |
|---|---|---|
| `$c86a` | **player record** routine `$c6d8` (called from the player update `$a368` while `$80040` bit 3 is set): the victory pose of one player. State `+24` = `$f`, 16 animation steps of 16 frames, sound `$4e` at step 15, bit 4 at step 16 = **256 frames** after the pose starts | every level when the player has no live partner, and levels 1, 3, 4 always (`$c70a..$c726` jumps straight to the solo path for those levels) |
| `$ca6e` | same routine, **pair** variant (`+5` = 2 after the two players walked together, `$c87a`/`$ca3e`): 12 steps of 16 frames | levels 0, 2 and 5 when both players are alive (`$c70a` lists exactly these levels) |
| `$20bd4` | pool A type `$48` (final boss), state `$1d` | level 5, the only way it ends in a normal run |

Bit 3 (the trigger of the player routine) is set at `$1725a` (type `$12`, level 4's boss, own code) and at `$23e5c`/`$23fac` (the shared boss death states `$23cf2`/`$23e66`, used by types `$9 $a $c $d $e $f $1f $20 $24 $36 $3a`), and only if `$80041` bit 7 is set.

*Proven* (`py/levelend.sh <level> <P2>`, `py/wdedupe.py`): poke `$80040 = $88` at frame 1500 (the state a boss kill leaves) in each level and log the writer of bit 4 (`CB_TAP`):

| level | one player | two players (P2 joins at frame 900) |
|---|---|---|
| 0 | `$c86a` f1756 | `$ca6e` f1741 |
| 1 | `$c86a` f1756 | `$c86a` f1756 |
| 2 | `$c86a` f1756 | `$ca6e` f1747 |
| 3 | `$c86a` f1756 | `$c86a` f1756 |
| 4 | `$c86a` f1756 | `$c86a` f1756 |
| 5 | `$c86a` f1756 | `$ca6e` f1747 |

12 of 12 as the code predicts (solo 256 frames, pair 241 to 247). **In level 5 the player routine is never used in play**: `$80040` runs `$80 -> $84` (f9224) `-> $80` (f17181) `-> $d0` (f18062) in the full run, bit 3 is never set, bit 4 comes from `$20bd4` (tap, 1 of 1 per run, 3 runs). Both level-5 calls of `$c71e`/`$7fee..` are leftovers of an earlier design (*inferred*).

Event-flag setters (`py/setters.py`, whole linear listing; the lead's `out/flag_setters.txt` attributes `$23e2e/$23f7e/$23e54/$23fa4/$23e5c/$23fac` to type `$4f` only because it is the last handler below them in address order: they are the shared death states).
Bit 2 of `$80040` (set together with `$80041` bit 7 where marked *): `$13208` t`$09` (script: level 0), `$13882` t`$0a` (1), `$14438` t`$0b` (2), `$148da` t`$0c`, `$14bf4` t`$0d`, `$150a4*` t`$0e` (0), `$15666*` t`$0f` (1), `$15c90*` t`$10`, `$162f0*` t`$11`, `$16552*` t`$12` (level 4; own clear `$17238`/`$17252`, bit 3 at `$1725a`), `$1a24e` t`$1e` (4), `$1a376` t`$1f` (3), `$1a8e2` t`$20`, `$1b122` t`$24`, `$1c858*` t`$36`, `$1dd38` t`$3a`, **`$201c2*` t`$48` (level 5, spawned by `$13`)**. Clears: `$17238` t`$12`, **`$20426` t`$48`**, `$23e2e`/`$23f7e` (shared death, bit 3 set right after at `$23e5c`/`$23fac` and `$80041` bit 7 cleared `$23e54`/`$23fa4`), `$20bdc` t`$48` (`$80041` bit 7). Types with an empty level list are spawned by other handlers (the level-0 to 2 bosses by ENEMIES1, `$1f` by SPECIAL34).
Level 4's script contains `$12` and `$1e`, level 3's `$1f`; level 5's script has no boss-flag type at all: its flag comes from `$48`, which no script spawns.

## 2. The final sequence of level 5 (pool A)

Script entries (list A level 5, `$6c82c`): `$4d` x1 (trig `$e20`, x `$ed8`), `$4f` (trig `$e80`, x `$f30`), `$4e` (trig `$ee0`, x `$f90`); pool B list: `$46` (`$be0`, x `$cf0`), `$c7` = `$47` with bit 7 (`$ce0`, x `$df0`), three `$48` (x `$ed0 $f30 $f90`, trig `$db0 $e10 $e70`), `$4a` (`$eb0`, x `$fd8`). Their x match the three glass tubes in the background: tube 1 holds `$4d`, tube 2 `$4f`, tube 3 `$4e`.

Chain (proven in `out/full`, frames of that run): barrier `$46` destroyed f3656, `$47` f4027; `$4f` spawns f4776 (scroll `$e80`), dies f7016; `$4e` spawns f7209 (scroll `$ee0`), retreats and spawns `$13` at f7478; `$13` dies f9082-ish, becomes `$48` at f9223; `$80040 = $84` f9224; `$48` death f17052 (score +1,000,000); bit 2 cleared f17181; bit 4 f18062; ending to f22472.
Scroll holds: `$81e03` bit 7 is set every frame by pool B `$46/$47` while on screen (`$2b238`), by `$4e`/`$4f` handlers and by `$13`'s successor; `$f3b4` stops the script spawner while it is set and `$a788` refuses the scroll request. The final camera cell is the frozen block `$f00` (`$89a8` map, `$800f`); `$13` state 0 waits for scroll x >= `$f00` (`$173f2`) before it starts.

### 2.1 Pool B props used here (read; handlers via `$10558`)

| type | handler | what it is |
|---|---|---|
| `$46`, `$47` | `$2b1ca` | breakable machine/crate (box `$2c116`): `+5` 0 = hittable (`$101d2`), 1 = 32-frame flash, 2 = destroyed; 5 hits (`+23`) then sound `$6e`, 6 pool B type 5 variant 1 (pickups) stacked 32 px apart (`$2b2b0`), despawn. While on screen `$81e03` bit 7 is set: **it holds the camera**. Proven: scroll stayed `$c01`/`$d01` (`$81e03` = `$80`) until it was hit, then moved (bot, `out/full`, f3505..3655 and f3879..4026) |
| `$48` x3 | `$2b308` | glass tube: waits until x = scroll x + `$b0`, sound `$6f`, animates, at animation step 3 spawns 14 pool B type `$49` (debris; `$2b44e`, start speed table `$2b4b8` by variant), despawns after step 8 |
| `$4a` | `$2b4f0` | machine prop at the right edge (x `$fd8`); states by `+3`: reacts to `+17` bit 7 (grabbed) / bit 6 (thrown), follows the player while carried (copies x, y-`$3c`). It stayed in state 0 for all 19,000 frames of the run (never touched): role *inferred* (throwable console), not exercised |

### 2.2 Types

All six pool A types here use the fighter engine (`+5` health, `+3` state, `$22c56` hit reaction: -1 per hit, -4 when `+6` bit 3, `$24022` flash, tail `$22540 $2331c $2242c`).
Damage values: pool C hit box `$fa10 -> $fc34`: `byte[box type] * 4` (table `$fcba`, dip 0) from `py/tables_decode.py`, each confirmed by a drop of `$80113` (`CB_HPTAP`, 65 and 65 events in two runs): box `$22` (4f swipe) 12, `$1e` 20, `$1f` 20, `$20` 48, `$29` 20 (table values 3, 5, 5, 12, 5). Body contact `$f4f4 -> $f700`: 1 per touch (byte table `$f78e`, 1 for all types here), at most one per 8 frames. P1 starts at `$38` = 56.

**`$4f` tube mutant (purple brute), handler `$21448`** (own code, not the state-table engine). Drawn from tube 2 with two overlay layers `$42`/`$43`. +16 is a phase: 0 spawns `$42`, `$43` (`$21eb6`) and sets 1; 1 falls from y `$1a0` to `$1c0` (f4776 -> f4855); 2 = the fight; 3 = death. Health `$14` = 20 (log: `hp=14` at f4856, 1 per hit, 20 hits to f7015 incl. thrown-hit cases), score 0 (never calls `$248bc`; the table row for `$4f` is aliased garbage, unused: P1 score unchanged over f4776-7111), no drop.
Phase 2 action byte `+18` (table `$215ac`, 14 entries, read) with `+3` the animation state (`$30000`):
`0` choose every 40 frames by distance dx to the nearer player: dx < `$40` -> 2, `$40..$5f` -> 1, >= `$60` -> 3 (read); `1` walk toward (24 steps); `2` bash: moves toward, spawns box `$22` every frame, the animation yields 5 hits of 12 spaced 8 frames (H log 24 + 6 rows); if it touches (`$f4f4` contact) the player it grabs (player state `$d`) -> `4`; `3` ranged: spawns pool B `$52` (projectile) at animation step 2, three rounds (poked: 112 frames, 56 frames of pool B `$52` alive; natural occurrence not seen because the bot stands next to it); `4` grab wind-up 32 frames -> `5` squeeze: every 32 frames player health -4 (`$21ad8`), 128 frames -> `6` release (player thrown, flag bit 6) 32 frames -> 0; `7` carried by a player (`+17` bit 7); `8` hit stagger 16 frames, health -1, then `0xd` or `2` by `$ea44 & 1` (bytes `0d 02` at `$21c36`); `9` thrown away, lands y `$1d0`, pool B `$51` shockwave, sound `$18`; `$a..$c` thrown bounce (health -4 on landing `$21da4`, read); `$d` walk away 24..230 frames (proven).
Counts (`py/actions.py out/e/objlog.txt 4f 18 02`, run e, 18 action-2 runs): `0>2` 6, `0>8` 16, `2>0` 11, `2>4` 3, `2>8` 4, `4>5` 3, `5>6` 3, `6>0` 3, `8>2` 12, `8>d` 7, `d>0` 7; run lengths 4 = 32, 5 = 128, 6 = 32 (all 3 of 3 equal), 8 = 16 (20 of 20). Death: health 0 -> phase 3, animation state 8 for 96 frames (3 x 32, y +16 at the second), then `bclr #5,$80400` (camera released) and despawn (`$21e24`; f7016..7111 in `out/full`).

**`$42` / `$43` overlays, `$1f490` / `$1f7a6`** (read, 4f children proven by the spawn log): no logic. Each copies state, facing, animation variant (`$42`: owner's -1, `$43`: +1), x, y, variant, frame from the owner (`+60`), draws through its own animation table and despawns when the owner's variant is 3. Same pair is spawned by type `$12` (`$16574`, level 4 boss).

**`$4e` brown beast (white mane), handler `$2120a`**, level 5 only, from tube 3. Engine: **the same state routines as type `$3a`** (`$1dbbc`: states 1, 6-8 `$1ddae $1de32 $1de7a`, 9 `$1df0e`, `$b` `$1df90`, `$c/$d/$11` hold `$1e020`, `$e` `$1e1d6`, `$f` `$1e242`, `$10` `$1e24e`, `$12` `$1e282`), own init (`$212da`: health `$20` = 32, sets `$80400` bit 5 only, **no `$80040` bit 2**: not a boss) and own states `$13` (`$21360`, walk to x `$fa0`) and `$14` (`$213fe`). Roles (read): 6 ready, 7 walk + chooser `$2438a`, 9 leap at the target, `$b` leap-grab (`+51` bit 0 when it connects -> `$c/$d/$11` hold: the player is pinned, flags `$80157`/`$80158`), `$e` retreat leap (speed 2.5, can leave the screen: x `$100d` seen at f8450 in run m, beyond the right edge `$fd8`), `$f` ranged: spawns box `$29` (20 damage, 8 H events at 161-frame intervals) from off-screen, `$12` jump-in.
**Rule (`$21242`, proven):** in state 6 with health < `$10` it does not die: it goes to `$13` -> `$14`, spawns `$13` (the scientist) and despawns `$80` frames after `+51` bit 1 (set by the scientist's state `$e`). Poke test (`CB_POKES=8130:81005:11`, `out/n`): hits at f8265 (`$11 -> $10`), f8353 (`$10 -> $0f`), `$13` at f8368, `$14` at f8369, scientist at f8393. Hits needed from 32: 17 (hp `$20 -> $0f`). Score +200 per hit (idx 6; `$8013c` 30000 -> 30200 -> 30400, 2 of 2), no death score. Contact 1; box `$29` 20.

**`$13` mad scientist (white coat), handler `$17296`** (spawned by `$4e` at `$21418`, `+60` = `$4e`). Health 8. State 0 waits for scroll x >= `$f00`, sets `$80015` bit 4, goes to `$b` and spawns `$47`; invulnerable (`+0` bit 3) in `$b $c $d $e`: a scene of **256 + 128 + 97 + 192 = 673 frames** (proven, `out/full`: `$b` 256, `$c` 128, `$d` 97, `$e` 192; `$b` descends on the hover pad `$47` from y `$c0` to `$1c0` at x `$fe0`, `$c` lands, `$d` turn, `$e` walks left to x `$f7f`, then `$80015` bit 4 cleared and `$4e` told). Then `7` walk toward the player, `$f` stand next to him (`$20` px) and `6/9/..` wander (`$17700`); he has **no attack** (no pool C spawn, no contact test; no `$80113` drop attributable to him in 7 hits). 7 hits (-1 each, stagger state 1 for 66 frames after each) then state 2 (`$1744e`: a hop away, 66 frames, sets `+51` bit 0), `$10` 63-64 frames, and at the end of `$10` `$172c2` spawns `$48` (with his facing) and despawns him. Score 10,000 per hit and for the death (idx 23; 8 events of 10,000 in `out/full` between f8170 and f8962, 8 of 8).

**`$47` hover pad / follower, `$1ff04`** (read, spawn proven): 3 states: copies the owner's x and y; stays while the owner is in state `$b` (`$13`) or `$1c/$1d` (`$48`) and despawns otherwise. First spawned by `$13` (pad under the scientist, f7487), second by `$48` at its death state `$1b` (f17278..18061, the rising figure during the dialogue). No health, no hit test.

**`$48` final boss, green tentacled mutant, handler `$1ffbc`** (30 states, table `$2013c`). Not in any script. Health `$27` = 39 (`$201ec`; log `hp=27`), also copied to `$8005c` each frame (the "ENEMY" bar), score +1000 per hit (idx 14: `$8013c` +`$1000`, 29 events), **+1,000,000 at death** (idx 24; `$8013c` 128000 -> 1148000 across f13294..17052, jump of `$1000000` at f17052). Hit rule `$1fffe`: only when `+0` bit 6, not bit 3 (invulnerable states); -1 per hit (also strong: it adds `+53` bit 4 stagger flag); health 0 -> state 2; during its grab states `$b/$c/$d` a hit instead sets the player's break-free bit (`$80158`/`$801d8` bit 6). x is clamped to `$f10..$fef`.
States (read; counts and lengths from `out/full`, `py/actions.py out/full/objlog.txt 48 3`):
`0` init (sound `$0b`, `$80040` bit 2, `$80041` bit 7, `$80400` bit 5, `$1c8a(56)` bar on, f9223-9224), ~80 frames hanging, then `6`; `1` stagger (`$234e6`, 15-66 frames) then random `$ea44 & 7` into bytes `08 10 10 11 11 12 12 14` (22 samples: `8` 5, `$10` 6, `$11` 6, `$12` 4, `$14` 1: matches 1:2:2:2:1); `2/4` death/knocked down (own code `$202d4`: arc, 64 frames, `bclr` bit 2 `$20426`, `bclr` `$80400` bit 5, `$1c8a(57)`, -> `$1b`); `6` ready: chooser `$2438a` with the attack tables (`py/ai_tables.py 48`): start routines `$27f60..$28076` pick, by `$ea44 & 3`, among state 6, 7, 8, 9, grab `$b` (only if the player is on the ground and not held), `$10`, `$11`, `$12` (observed from 6: 18 `1`, 18 grab, 8 `$11`, 5 `$12`); `7` walk toward + chooser; `8` slow walk 32 frames; `9` leap arc; `$a` landing/idle; `$b $c $d` grab: `$b` wind-up 16, `$c` hold **48 frames** (player state `$b`, -4 health once per hold at `$d442`; 12 of 12 holds), `$d` throw 16 (the shared `$24286`); `$e/$f` lift and throw (`$206e6`); `$10` charge: speed 2 px/frame, box `$1e` (20) at animation steps 0,1,3 (observed 30 frames each, 9 runs); `$11` slam: box `$1f` (20) (8..42 frames); `$12` jump up (21 frames, invulnerable) -> `$13` flying dash: speed 8 px/frame, sound `$2c`, box `$20` **48 damage** every frame (13 of 13 runs; 9 hits of 48 logged) -> `$a`; `$14` rise to y < `$110` (18 frames) -> `$18` (40) -> `$19` (192 frames) **spawns five `$49` at animation steps 1, 3, 5, 7** (observed: 4-8 alive at once) -> `$1a` (40) -> `$15` (128) -> `$16` (42, tracks the player, lands, box `$21` = 32 damage and pool B `$51` shockwave: not hit in the run, *read*) -> `6`; after death `$1b`: waits for the animation, fade (`$80041` bit 5 around `$70c2(D0=$60)`, one frame f17277), music 3, spawns `$47`, `$1c8a(58)`; `$1c` rises 0.5 px/frame with the text box 10 (`$5878`) for >= 64 frames after it ends; `$1d` text box 11, `$28fa(68)`, `$1c8a(59)`; when y < `$c0`, animation finished and 64 frames passed: `$28fa(68)`, **`bset #4,$80040` at `$20bd4`**, `bclr` `$80041` bit 7, despawn. Death to bit 4: 17052 -> 18062 = **1010 frames** (state 2 + 64 frames to `$20426` f17181; `$1b` f17277; `$1c` 576 frames; `$1d` 208 frames).
Texts (ROM `$5cec`, `$5d96`, read from `py` of the WORLD agent): box 10 is the boss's farewell (he wishes to experiment on the heroes and says he will return), box 11 the heroes' reply.
Damage summary (65 H events, `out/full`): swipe-type none; box `$1e` 11 events x 20, `$1f` 14 x 20, `$20` 9 x 48, grab 12 x 4, contact 1 (24 events, with `$49`), `$4f` box `$22` 30 x 12. A full-health player (56) dies to two flying dashes (96).

**`$49` crawler minion, handler `$20bec`** (spawned by `$48` state `$19`): health 1 (one hit kills, score idx 9 = 400 per hit: part of the +4096 steps seen), falls from the boss's x with state `$a` (shared fall `$23248`) from y `$168`, lands `6`, chases in state 7 (`$20cfe`, 2 px/frame toward the target), contact 1 damage per 8 frames; they do not respawn by themselves, `$48` makes 5 per `$19` (observed 4 or 8 alive).

**`$45`/`$46`/`$19`** (read; live only in the lead's level-3 census `out/l3/objlog.txt`, `py/milestones.py ... 19,45,46`): level 3's mounted gun. `$19` (`$18c0e`, pool A script type at x `$8d1`) spawns `$45` (`$1fbe0`, mount layer) at init (`$18c1c`) and holds `$81e03`; `$45` spawns `$46` (`$1fbec`); `$46` (`$1fd16`) is the gun: health 2, rides at owner y-`$30`, fires pool B `$53` every 16 frames after a 96-frame wait, on death spawns pool B type 5 variant 1 (`$1fe3e`) and clears `$80400` bit 5. In the census: `$19` and `$45` alive f4862..5040, `$46` f4862..5209. Level 5 does not use them.

## 3. From the boss kill to the attract screen (proven, `out/full`, T0 = f18062)

| frame | offset | event (writer) |
|---|---|---|
| 17052 | | `$48` health 0, +1,000,000 |
| 17181 | | `$80040` bit 2 cleared (`$20426`) |
| 17277..17278 | | `$80041` bit 5 (fade, `$20ab8` / `$20ace`) |
| 18062 | T0 | `$80040` bit 4 (`$20bd4`), `$80041` bit 7 cleared (`$20bdc`), bit 6 (`$746`), `$80016 = 0` (`$5fc0`): level+1 = 6 > 5 so `$5fba` runs the ending |
| 18317 | +255 | `$80016 = 1` (`$6112`) |
| 18350 | +288 | 2 (`$615a`): the heroes with the loot, speech boxes 12, 13, 14 |
| 19251 | +1189 | 3 (`$628e`) |
| 19284 | +1222 | 4 (`$62b0`): "THANKS TO CRUDE BUSTER", text 15, over the skyline |
| 19943 | +1881 | 5 (`$6314`): staff roll (Japanese and romanised names) |
| 21954 | +3892 | 6 (`$64ae`): "THE END" picture |
| 22471 | +4409 | 7 (`$66a2`) |
| 22472 | +4410 | `$80040` cleared (`$758`); attract loop: `$80016 = 0` f22541 (`$4ad2`), the story crawl |

The same offsets (+255, +288, +1189, +1222, +1881, +3892, +4409, +4410) appeared in three runs from different states (`out/h`, `out/i`, `out/full`): 3 of 3. Shots: `out/sheet_end1.png`, `out/sheet_end2.png` (ending), `out/sheet_4f.png` (4f), `out/sheet_13.png` (4e, scientist, boss entrance), `out/sheet_48a.png` (boss fight).

## 4. Errors and corrections to BRIEF2

- `$c86a` and `$ca6e` are not objects: the player routine (as the lead already found); `$20bd4` is a state of `$48`, not of `$49`.
- `$4e` and `$4f` are not "the end boss and a spawner": `$4f` is a tube mutant with its own phase machine and spawns only `$42` and `$43`; `$13` is spawned by `$4e`, not by `$4f`; `$13` is the scientist who becomes `$48`; the boss flag comes only from `$48`.
- `$42/$43` are overlay layers (also used by `$12`); `$45/$46/$47` are not one chain with `$48`: `$45/$46` belong to `$19` (level 3 gun), `$47` is the follower sprite of `$13`/`$48`.
- `$80040`/`$80041` setter list: the shared death states are used by 11 types (section 1), not by `$4f`.
- Pool B `$46/$47` hold the camera (`$81e03`); `$48` pool B are the tubes; `$49` pool B are tube debris, not the pool A `$49`.
- Score table `$24952` is read past its end for types >= `$4f` (row `$4f` decodes to code bytes); `$4f` never uses it.

## 5. Open

- `$4f` actions `3`, `4` only by poke (action 4 stuck 301 frames when poked: the sub-counter did not advance without the real grab; the natural chain was seen 3 of 3 in `out/e`), `7`/`9`/`$a-$c` (thrown/carried) not exercised.
- `$48` box `$21` (landing 32) and states `$e/$f` (`$206e6`) not seen hitting; `$4a` not touched; box `$29`'s source frame count for `$4e`.
- `$4e`'s unclamped fight to the end was not played (the bot cannot reach it once it retreats off screen); rule proven by poke instead.
- The full run used health clamps (`CB_EHP=1` for `$4c $4d $4e`) and a teleport bot; `$13` and `$48` and `$4f` were fought unclamped.

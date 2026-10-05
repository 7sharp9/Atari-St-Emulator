# Crude Buster, level 5 pool A enemies (group L5A): types $4a, $4b, $4c, $4d and the objects they spawn ($41, $37, $25)

Addresses are 68000 addresses of the decrypted `cbuster` image. Every claim carries a count and the script that reproduces it (scripts in `py/` and `lua/`, commands in `README.md`),
or is labelled *read* (from the linear listing, not run) or *inferred*. Logs are in `out/<job>/objlog.txt` (gitignored scratchpad). "frame" = one logic step (VBL).

## 0. Summary for the lead

| type | handler | what it is (named from its drawing and body) | script (level 5, list A) | hp | kill score | boss flags |
|---|---|---|---|---|---|---|
| `$4a` | `$20d84` | cyborg mutant with metal claw arms: a non-boss clone of the level 2/3 boss type `$0c` (`$14824`); variant has no effect | 5: var 0 at trig `$280` x2, `$290` x2; var 1 at trig `$700` (x `$820`, y `$480`) | 16 | `$2000` (hit `$300`) | none |
| `$4b` | `$20eac` | skeletal android whose skull head detaches and flies (head = type `$41`): clone of the boss type `$0d` (`$14b18`) | 6: trig `$1c0` x2 (y `$7c0`), trig `$c00` x4 (y `$c0`) | 8 | `$200` (hit `$200`) | none |
| `$4c` | `$20fca` | tall grey-suited fighter with a green snake draped over his shoulder; kicks, summons snakes (pool A type `$37`); clone of the boss type `$36` (`$1c7a2`) | 4: trig `$cc0`, `$ce0`, `$d00`, `$e20` (x `$df0`/`$e10`/`$cd0`/`$df0`, y `$1c0`) | 16 | `$10000` (hit `$200`) | none (sound `$61` is a hit/death voice) |
| `$4d` | `$210cc` | huge tusked, horned brute that leaps and grabs and throws: clone of the level 3 boss type `$10` (`$15b3a`) | 1: trig `$e20`, x `$ed8`, y `$1a0` | 24 | `$10000` (hit `$200`) | `$80400` bit 5 while alive; forces `$81e03` bit 7 (blocks list A spawns) |
| `$41` | `$1eda4` | the detachable skull head of `$4b` (and `$0d`); a slave object mirroring its owner | spawned by `$4b` state 0 at `$20f9e` (and `$0d` at `$14c4c`) | `$80` | none | none |
| `$37` | `$1cce8` | green snake (hp 1, hops, death score `$50`); spawned by `$4c`'s stagger code `$1d2ee` | handler spawn only | 1 | `$50` | none |
| `$25` | `$1b5e4` | small effect object attached in front of `$4d` while it idles (identity of the sprite not determined) | spawned by `$4d` state 6 at `$15e6c` | none | none | none |

Findings that change the lead's picture:

1. **The four types are clones of the boss handlers with the boss logic stripped**: same state routines (the 24-entry tables of `$4a`/`$4b`/`$4c`/`$4d` reuse the states of `$0c`/`$0d`/`$36`/`$10` entry for entry, `out/tables_all.txt`), different state 0, hp and tables. `$4c` and `$4d` are mini-bosses only in score (`$10000`) and, for `$4d`, in the scroll lock and spawn block; `$4c` sets no flag at all.
2. **The damage byte table is indexed by the hit box type, not by the owner's pool A type.** `tables_decode.py`'s `dmg` column (indexed by pool A type) is wrong for this purpose: `$fc34` reads `table[ctype] * 4` where `ctype` = byte `+2` of the pool C hit box = `D6` of the `$21e72` call. See section 3.
3. **A second damage path exists: body contact** (`$f4f4` called from `$2331c`, boxes from `$6b000`): 1 health point to the player per contact, and the enemy itself takes 1 hp and a stagger (47 of 47 for `$4a`, 35 of 35 for `$4c`). `$4d` has contact damage 0 (`$f78e[$4d] = 0`).
4. **Immunity windows**: a landed hit makes the enemy immune for 15 frames of stagger (`+17` bit 1 set by `$2356e`) and then ignoring hits for 16 more frames (`+17` bit 3 -> `+0` bit 3 flash, `$24022`): consecutive scoring hits are at least 32 frames apart (`kill_4a`: spacings 48, 48, 32, 32, ... from the score log).
5. `$4b` and `$4d` use `$22ce4` instead of `$22c56`: during their grab states `$b/$c/$d` they are immune and a hit sets the player's break-free flag (`$80158` bit 6).
6. Final-area spawn chain (link to L5B): after `$4d` dies its record clears one frame later and `$80400` bit 5 drops; the next script entry `$4f` (x `$f30`) spawned 3 frames after (`nat4`: `$4d` last row frame 4336, `$4f` first row 4339), and `$4e` (x `$f90`) 3 frames after `$4f`'s last row (6487 -> 6490). While `$4d`/`$4f` live `$81e03` stays `$80`.

## 1. How the types were identified

* Handler addresses: `$10418` table. `$4a` `$20d84`, `$4b` `$20eac`, `$4c` `$20fca`, `$4d` `$210cc`, `$41` `$1eda4` (`py/handler_tables.py`, lead's output).
* State tables (`out/tables_all.txt`, entries equal to the originals): `$4a` table `$20dca` = `$0c` table `$14874` except [00] `$20e2a` (own init), [02] `$2397e` (normal death, boss `$23cf2` in `$0c`), [04] `$23ac0` (normal, boss `$23e66`); `$4b` `$20efe` = `$0d` `$14b8e` with [00] `$20f5e`, [02]/[04] normal; `$4c` `$21010` = `$36` `$1c7f2`; `$4d` `$21122` = `$10` `$15c22`.
* What `$4a-$4d` lack compared with the originals (*read*, `$14b18`, `$14824`, `$1c7a2`, `$15b3a`): the boss voice/health pre-step `$23480` and the boss health bar byte `$8005c`; `$80040` bit 2 and `$80041` bit 7 are never set by any of the four; `$4a`, `$4b`, `$4c` do not set `$80400` bit 5.
* Names come from drawings (`out/sheet_4a.png`, `sheet_4b.png`, `sheet_41.png`, `sheet_4c.png`, `sheet_nat3.png`, `sheet_4d.png`: contact sheets of live frames from `lua/drive5.lua` with `CB_SHOTS`), not from numbers. Descriptive names only.

## 2. Test harness

`lua/drive5.lua` (derived from the lead's `objlog.lua`): starts level 5 (`CB_LEVEL=5`), writes pool A records itself (`CB_SPAWN`, same field writes as `$f388`: `+0=$80`, `+2` type, `+16` variant, `+8` x, `+12` y), sets scroll counters, pokes the list pointers (`$81e06` list A, `$81e0a` list B), places P1 beside the nearest enemy (bots 2 and 5), injects player hits, and logs one `F` line and one `A` line per live record per frame plus taps: `H` (every write to P1/P2 health, with the writer PC, the hit box type and the owner's type/state), `S` (every pool C hit box spawn with its owner), `Z` (every write to the sound latch `$bc002`). `CB_HP=1` restores P1's health every frame, so each `H` line shows exactly one hit.
Scroll: `$8040a`/`$80406` are 16.16 longs whose integer word is what the script compares; poking the word works (level 5 triggers are all horizontal: 47 of 47 list A entries are bit-15-clear in `out/scripts.txt`).
Determinism: two runs with identical environment gave identical logs (`kill_4a` and `kill_4a_v1` differ only in the variant byte: 764 of 764 rows equal ignoring `+16`).

## 3. Common facts (all four types)

* Record init facts, from the four state-0 routines and the live first rows: all set `+0` bits 6 (hittable) and 3 (paused until the init finishes), `+1` bit 0, `+53` bit 6; `+7` (animation index) 0 for `$4a`, 2 for `$4b`, `$4c`, `$4d`.
  Leave-screen (`$2242c`): a record with `+17` bit 0 clear is **removed** when it is outside x in [scroll-`$40`, scroll+`$140`] or y in [scroll_y-`$80`, scroll_y+`$140`]; with the bit set it is clamped inside. `$4a`, `$4b`, `$4c` have the bit clear (the three non-boss clones: their init does not set it), `$4d` sets it (`$211be`): so a `$4a`/`$4c` spawned at the left of the camera (entries x `$250`/`$260` at trig `$280`/`$290`, `$cd0` at trig `$d00`: x = trigger - `$30`) is removed as soon as the camera has moved 16 px to the right. Live: `nat1` first rows `$4a` x `$250` lived 6 frames (frames 2281-2286, the camera moved), entry x `$260` was never seen; `nat4`: the x `$cd0` `$4c` entry had no row at all with the scroll held at `$e20`. In `nat3` (camera not held) the same `$4c` entry lived 2 frames.
* Hit reaction: `$22c56` (`$4a`, `$4c`) / `$22ce4` (`$4b`, `$4d`): player hit flag `+6` bit 7: health -1 (-4 if `+6` bit 3, strong; confirmed live, `injx_4a_s88`: 5 of 5 drops of 4 with `+6=$88`, and `+53` bit 4 set after the strong stagger), health <= 0 -> state 2, else state 1 (stagger). Throw/ground hit `+17` bit 6 via `$22dac`: -4 and state 5 (state 4 if lethal), score index 2 (state 5): confirmed live (`injx_4a_t17`: 6 of 6 injections: health -4, next state 5 or 4; score +`$500` each, +`$2000` on the lethal one).
* Immunity (synthetic player hits `+6 |= $80` injected 3 frames into a state, logs `inj_*`, `inj2_*`, `inj3_*`; flag-based prediction vs live outcome, `py/inject_check.py`: **0 wrong** in 88 (`$4a`), 174 (`$4b`), 95 (`$4c`), 110 (`$4d`) injections made outside the flash window; a hit is accepted only if `+0` bit 6 set, `+0` bit 3 clear, `+17` bit 1 clear, and for `$4b`/`$4d` the state not in `$b/$c/$d`):
  state 1 (stagger, 15 frames) immune, then 16 frames of flash (`+0` bit 3, `$24022` timer `+48`); death states immune. Per type below.
* **Contact damage** (`$f4f4`/`$f700`): while the body box of the current state overlaps the player's hurt box and `+17` bit 2 is clear, the player loses `$f78e[type]` = 1 health point and the player's reaction code `$f7de[type]` is stored; the enemy gets `+6 = $90` (it counts as hit by P1: -1 hp, stagger, and P1 scores the hit amount). `$f78e[$4d]` = 0. Body boxes (`py/bodybox.py`): `$4a` states 6-f `[16,-16,32,-32]`, state 5 `[16,-16,16,0]`; `$4b` states 6,7,8,b-f `[7,-8,31,-32]`, 9,a `[7,-8,16,-32]`; `$4c` 6,7,8,b,c,d `[16,-16,28,-40]`, 9,a,e,f `[16,-16,28,-28]`; (x1,x2,y1,y2 relative to the record). Live counts, contact events with the enemy hurt next frame: `$4a` 47/47, `$4c` 35/35, `$4b` 2 of 4 (the other two in its immune states), `$4d` 0 events, `$41` 43 events (the head takes the strong branch, `+6` bit 4, and bounces: state `$12`).
* **Hit box damage** = `table[$fcba index by dip $80054&$c][hit box type] * 4`. Live dip `$80054` = `$8000` (index 0, table `$fd2a`). All 9 hit box types used by these enemies matched the formula (counts are hits with a `fc9e` health write, all logs): `$0e` 20 (2), `$17` 20 (73), `$19` 12 (21), `$1a` 16 (38), `$1b` 24 (5), `$1c` 12 (1), `$23` 20 (43), `$2a` 16 (28), `$2b` 16 (40) (`py/dmg_check.py`, all `out/*/objlog.txt`). The player has 56 health points (`$38`), so 12-24 is 1/5 to 3/7 of a life.
* **Throw landing damage** (grab state `$d` = `$24286`, then the player's fall code): thrown by `$4b` -4 (pc `$d442`, 8 of 8), thrown by `$4d` -8 (pc `$d544`, 8 of 8 in `wander_4d2`; `$4b` in the `$4d` arena still -4: 2 of 2, `wander_4b_arena`). Cause (*read*, `$242e2`-`$242fc`): only owner types `$10`, `$24` and `$4d` set the player's `$80157` bit 1 (heavy throw); other throwers do not.
* Score (`$248bc`, indexed `$24952 + 4*type`: hit idx, thrown idx, death idx, sound; BCD table `$4016`): `$4a` `$300`/`$500`/`$2000`, `$4b` `$200`/`$300`/`$200`, `$4c` and `$4d` `$200`/`$300`/`$10000`. Live (P1 score `$8013c` per frame, `py/summ.py`): `$4a` 15 x `$300` + `$2000` at death; `$4b` 7 x `$200` + `$200`; `$4c` 15 x `$200` + `$10000`; `$4d` 23 x `$200` + `$10000`; the thrown state 5 amount `$500` confirmed for `$4a`. The score goes to P1 unless `+6` bit 6 (P2).
* Sound byte (4th byte of the score entry): `$4a`, `$4b` 0 = a random voice `$64`/`$65`/`$67` per scoring event (`Z` lines: `$4a` 8+4+4 in `kill_4a`); `$4c` `$61` (16 events in `kill_4c` = 15 hits + death), `$4d` `$63` (24 events in `kill_4d2` = 23 hits + death). They are voices, not boss markers.
* Drops: **none** from any of the four (pool B logs `kill_*`: only hit sparks `$2b`, `$51` ground-impact puffs from `$4c`'s armor flag, and for `$4b` pool B `$05` variant 1 = the head's removal puff `$23fb6` at the frame the record clears). The corpse (state 2, `$2397e`, 59-79 frames: `$4a` 61, `$4b` 59, `$4c` 79, `$4d` 59) falls in an arc and the record then disappears (`$2242c`).
* `+35` bit 2 (armor flag, set by `$4c` and `$4d` init): the shared knockdown landings call `$2436a`, which spawns pool B `$51` and plays sound `$18` (`kill_4c`: 4 `$51` records in 4 landings; 12 sound `$18` writes; `$4d` 18 in `kill_4d2`).

## 4. Type `$4a` (cyborg mutant, `$20d84`)

Pre-step order (handler body, *read*): `$24022` flash, `$22c56` hit, `$22dac` throw hit, state dispatch (`$20db6`), `$23fc8`, `$22540`, `$2331c` (hit test and contact), `$2242c`. No `$23480`, no `$8005c`. Init (`$20e2a`): hp `$10`, facing 0, `+7`=0, `$22b48` picks the target; the record is hittable and unpaused from the next frame. (`cmpi.b #1,3(A6)` -> state 9 branch inside the routine is not reachable by my reading: bit 6 is set only here.)
Variants: **0 and 1 are identical**: `kill_4a` (var 0) vs `kill_4a_v1` (var 1): 764 of 764 rows equal ignoring `+16`, 5 of 5 screenshots pixel-identical (`sv_4a_*`); no handler code reads `+16` for this type (state routines `$1453e..$14ae4` contain no `16(A6)` read).

| state | routine | role | measured |
|---|---|---|---|
| 0 | `$20e2a` | init, then state 6 next frame | 1 frame |
| 1 | `$1499a` | stagger (`$234e6`: knock-back 0.5 px/frame, 15 frames, immune), then picks next: normal {6,b,c,d}, if `+17` bit 4 set {6,6,d,d} (table bytes `06 0b 0c 0d` / `06 06 0d 0d`) | 15 frames each (225 frames / 15 runs in `kill_4a`); 1>6 4, 1>b 3, 1>c 5, 1>d 3 |
| 2 | `$2397e` | death fall (arc), immune | 61 frames |
| 3, 4, 5, `$a`, `$17` | `$22ecc`, `$23ac0`, `$23748`, `$23248`, `$22e30` | held, knocked down, thrown away, falling, held variant | 4/5 verified by injection (state 5); others not exercised |
| 6 | `$1453e` | idle facing the target, terrain probe `$226e4`; calls the chooser `$2438a` when its animation wraps | 8-723 frames |
| 7 | `$145ae` | walk toward the target x, 0.5 px/frame (`+22 = $8000`) | dx 0.503/frame, runs of 48..181 frames (`wander_4a`) |
| 8 | `$14624` | walk away from the target 0.5 px/frame for `$80` frames, then chooser | not observed live (chosen only by leaf `$25d76` when P1's sub-state `+47` is 4..7: the idle bot never reaches it) |
| 9 | `$146a0` | jump toward the target: horizontal 0.5 px/frame, arc `$22856` (`+36` = `$20` + height difference), `+37` += 2 per frame, 64 frames, `+17` bit 2 (no contact) and `+53` bit 4 (airborne), lands with `$2297a` | 64 frames, y excursion 141 (`wander_4a`, 1 run) |
| b | `$14a0e` | attack A: hit box `$2a` spawned every frame while the animation runs, then state 6 (`$24056`) | 24 frames; damage 16 (28 hits) |
| c | `$14a1a` | attack B: hit box `$2b`, then state 6 | 20-24 frames; damage 16 (40 hits) |
| d | `$14a26` | attack C (hit box `$23` each frame until `+35` bit 6 or animation end), then state f | 12-32 frames; damage 20 (43 hits) |
| e | `$14ab0` | wait for the animation end, then state f | never entered (nothing sets state e for this type) |
| f | `$14ae4` | recovery until the animation wraps, then 6 | 8-32 frames |
| `$10`-`$12` | `$2409a`, `$24126`, `$24286` | grab, hold, throw | never entered (the chooser has no grab leaf for `$4a`) |
| `$13`-`$16` | `$1453e` | aliases of state 6 | never entered |

Chooser (`py/chooser.py 4a`, tables T1 `$25b94`, T2 `$25bd4`, T3 `$25c14`; leaf = `4-way random by $ea44&3` or a fixed state):
* T1 (same lane, enemy y within -`$20`..+`$60` of the target): index by |dx|>>4, then by P1 state (`+46`&f) and sub-state (`+47`): leaf `$25d54` (dx>>4 0..4, sub-state 0..3): {6, b, b, c}; `$25d76` (sub-state 4..7): {8, b, c, c}; `$25d98` (dx>>4 0..a, sub 8..b): {7, 7, d, d}; `$25dba` (sub 12..15, and dx>>4 >= b): 7.
* T2 (enemy more than `$60` below the target, y larger): dx>>4 in {0,4..7}: state 9 (jump) else 7. T3 (enemy above): dx>>4 {0,4..7}: state a (drop), else 7. dx >= `$100`: 7 at once.
* Validation against the live log (`py/chooser_check.py`, each transition out of 6/7/8/9 not caused by a hit is predicted from the enemy and player positions and P1's state/sub-state): `$4a` 145 of 145 in the predicted set (kill 9, wander 47, inj3 89; 1 natural end of a jump not counted). Wander transition counts: 6>7 10, 6>b 11, 6>c 6, 6>d 11, 7>b 2, 7>c 1, 7>d 5, 7>9 1 (`wander_4a`, 4300 frames idle player).
* Facing: the chooser turns the enemy toward the player when |dx| >= 16 (T1) or 48 (T2/T3).

## 5. Type `$4b` (skeletal android with detachable head, `$20eac`)

Pre-step: `$14b60` (if the record is not in state 0 and the head `+56` is no longer active, clear `+51` bit 1), `$24022`, **`$22ce4`**, `$22dac`, dispatch, `$23fc8`, `$22540`, `bset #1,35(A6)`, `$2331c`, `$2242c`. Init `$20f5e`: hp 8, facing 0, `+7`=2, spawns the head `$41` var 0 (`$21eb6`, link: `+60` of both, then `+56 = +60`, `+51` bit 1 set = "head attached").

| state | routine | role | measured |
|---|---|---|---|
| 0 | `$20f5e` | init + spawn head | 1 frame |
| 1 | `$14c96` | stagger; then {6,e,e,e} (or {6,6,6,6} if `+17` bit 4) | 15 frames, 105 frames / 7 runs in `kill_4b` |
| 6 | `$14d08` | idle, probes `$10,$18` / `0,$20`, chooser on anim wrap | 8-15 frames per visit |
| 7, 9, `$12`-`$16` | `$14d5a` | walk toward the target, **0.125 px/frame** (`+22 = $2000`), chooser every pass, state 8 if `+53` bit 5 (outside the screen margin) | dx 0.124/frame (`wander_4b`: 32 runs, 1..114 frames) |
| 8 | `$14df0` | run in the facing direction 2 px/frame for `$60` frames then chooser | never entered |
| b, c, d | `$2409a`, `$24126`, `$24286` | grab, hold (48 frames), throw (16 frames); immune (`$22ce4` ignores hits, sets P1 break-free `$80158` bit 6); needs P1 within y +`$10`, P1 state < `$a`, `$8013a & $18` = 0 | b 16, c 48, d 16 frames (3 sequences in `wander_4b`, 2 in the arena run); thrown landing -4 |
| e | `$14e62` | attack: hit box `$e` spawned while animation index (`+20`) is 1, abort to f if `+47` is 1 or 2, else back to 6 at the animation end | 32 frames; damage 20 (2 hits) |
| f | `$14ee8` | pause until the animation ends (immune, `+17` bit 1), then 6 | 8 frames |
| `$10` | `$14f28` | throw the head: at animation index 2 sets `+51` bit 0 and the head's state to `$11`; immune; then 6 | 48 frames (25 runs in `wander_4b`) |
| `$11` | `$14f8a` | catch the head: immune; clears `+51` bit 0; then 6. **Entered from the head** (`$1f2e4` sets the owner's state to `$11` when the head returns), not by the chooser | 33 frames (24 runs) |
| 2, 3, 4, 5, `$a`, `$17` | shared | as `$4a` | |

Chooser (`py/chooser.py 4b`): T1 leaf `$26090` (dx>>4 0..1): {6, b+6, 6, b+6}; `$260b2` (0..3): {6, e, 6, e}; `$260ec` (0..3): f; `$260d4` (to f): 7; `$260dc`: state `$10` (via `$26212`: only if the head is attached, `+51` bit 1 set and bit 0 clear, else 7). T2/T3: dx>>4 4..7: head launch (`$26212`), 2..3 (T3): state a, else 7; T3 dx>>4 0..1: 6. Validated: 179 of 179 chooser transitions in the predicted set (kill 10, wander 65, arena 104), plus 41 transitions to state `$11` that the head sets (`$1f2e4`), 0 misses.
Immunity (live injections, `inj3_4b`): hits accepted in 6, 7, e; ignored in b, c, d, `$10`, `$11` (60 and 62 injections in the last two, 0 wrong). State f: immune by flags (`+17` bit 1 set in 105 of 120 rows of `kill_4b`, the 15 clear rows are the first frame of each visit, before the routine's `bset`); no injection landed in it.
Score hit `$200`, death `$200` (the lowest value of the four); the head's removal puff (pool B `$05` variant 1) appears when the record clears.

### Head `$41` (`$1eda4`)

hp `$80`; `$1ef7c` (first step): if the owner is no longer active, clear the owner's `+51` bits 0-1 and remove itself with `$23fb6` (pool B `$05` var 1). Own hit handling `$1edd6` (not the shared one): `+6` bit 7: strong (`+6` bit 4, which includes the contact flag `$90`) -> state `$12`; else hp-1, hp 0 -> removed, else state `$14` (knocked arc).
States (`out/shot_4b`, `py/loglib.py`): all but `$11..$14` mirror the owner each frame (x, y, facing, state copied at `$1eec8..$1ef10`: 100% of its rows in `kill_4b` show the owner's state); `$11` ($1f01c): launched from the owner (x +-`$10`, y -`$23`), flies toward the target with speed 2 px/frame (vector by `divu`), `$40` frames max, then `$12`; `$12` ($1f176): returns to the owner (x +-7, y -`$23`); on arrival, if the owner is in 6/7/8 it sets the owner's state to `$11` and its own to `$13` (re-attach, waits for the animation end then mirrors again), else it hovers (`$11`); `$13` $1f31e; `$14` `$1f33e`: hurt, thrown away in an arc (`+36` = `$40`), falls, then `$12`. Poking the owner's state to `$10` at frame 850 (`shot_4b`): owner `$10` frames 850-897, head `$10`(mirror) 851-881, `$11` 882-890 x 562..578, y 1951..1967, `$12` 891-901, `$13` 902-933; contact damage 1 (43 events, strong branch each time).
Name: *inferred* flying skull head from the sprite (`out/sheet_41.png`, `zoom_41.png`).

## 6. Type `$4c` (grey fighter with a green snake, `$20fca`)

Pre-step like `$4a` (`$22c56`). Init `$21070`: hp `$10`, facing 1 (left), `+7`=2, `+35` bit 2 (armor flag), `$22b48`. The stagger routine `$1c8d4` (shared with the original `$36`) calls `$1d2ee` when it ends in state 6: **summons a snake**: if `+54` < 1: `rand&7`: 0 -> pool A type `$37` variant 2 (1/8), 3 -> `$37` variant 1 (1/8), else nothing; `+54` is incremented, so at most one snake per `$4c` (*read*; live: `nat3` has two `$37` records with `+60` = `$81000` / `$81040` (the owners' addresses), variants 2 and 1; the isolated kill runs happened to roll none in 10 and 15 staggers).

| state | routine | role | measured (`wander_4c`, 4300 frames idle player, and kills) |
|---|---|---|---|
| 0 | `$21070` | init | 1 frame |
| 1 | `$1c8d4` | stagger (+snake summon check); then {6,6,b,8} (`$1c982`) or {6,6,e,f} if `+17` bit 4; strong hits slide it back (`kill_4c`: 70 frames, 124 px) | 15..87 frames |
| 6 | `$1c98a` | idle, probe `$20,$18 / 0,$20`, chooser on anim wrap | 1-19 frames |
| 7 | `$1c9ce` | hop-walk toward the target: 1.5 px/frame, arc `+37` += 4 (32-frame hops), chooser at the end of each hop, back to 6 | 32 frames, dx 1.39/frame |
| 8 | `$1ca4e` | back-jump: 2.0 px/frame away, arc `+37` += 3, hit box none, `+17` bit 2, lands with `$228f4` | 43 frames, y excursion 96 |
| 9 | `$1cad0` | jump on the spot: 0.5 px/frame, arc +2/frame, 64 frames | 46-64 frames, y excursion 100 |
| a | `$23248` | fall to the lane below (chooser T3 leaf `$278b0` for any dx when the enemy is above the player) | flickers 1 frame at a time in the wander test (463 runs: the player stood 48 px below the enemy for 360 frames) |
| b | `$1cb52` | attack A: hit box `$1a` | 20-24 frames; damage 16 (38 hits) |
| c | `$1cb5e` | attack B: hit box `$19` | 24 frames; damage 12 (21 hits) |
| d | `$1cb6a` | attack C: hit box `$1c` | up to 56 frames; damage 12 (1 hit) |
| e | `$1cb76` | dash kick: 2.5 px/frame in the facing direction up to 63 frames (`+37` += 4 until `$fa`), hit box `$1b` every frame past arc frame `$40`, `$2434a` spawns a pool B `$37` dust trail every 4 frames, can stop on a wall | 28-63 frames; damage 24 (5 hits) |
| f | `$1cc60` | flying kick: 2.0 px/frame, arc +2, 64 frames, hit box `$1b` every frame, **immune** (`+17` bits 1 and 2), lands with `$2297a` | 64 frames; 1269 of 1280 rows immune; injections ignored 11 of 11 |
| `$10`-`$16` | `$1c98a` | aliases of state 6 | never entered |
| 2, 3, 4, 5, `$17` | shared | | |

Chooser (`py/chooser.py 4c`, T1 `$274c8`, T2 `$27508`, T3 `$27548`): T1 leaves by sub-state index (0..3, 4..7, 8..11, 12..15): `$27768` (dx>>4 = 0): {6, d, 6, b}; `$2778a` (0..1): {c, 6, d, 6}; `$277ac` (0..3): {6, 6, b, c}; `$277ce` (0..6): {f, 7, 7, 7}; `$277f0` (1..9): {7, e, e, f}; `$27812` (2..f): 7. T2: dx>>4 0: 6; 1..3: 7; 4..7: 9 (jump); else 7. T3: dx>>4 0..7: a; 8..f: 7. Validation: `$4c` 1804 of 1867 transitions in the predicted set (kill 10, wander 537, inj3 1257), 59 natural ends of a hop or jump (7/8/9 -> 6) and 4 misses (9 -> a, 8 -> a, 6 -> a: landing probes that find no ground; and 6 -> e at frame 4307 of `wander_4c`, not explained).
Immunity: state f only (and stagger/death); injections accepted in 7, 9, a, b, c, d, e, 8, 6 (>= 71 events, 0 wrong). Boss flags: none (`kill_4c`: `$80040` `$80`, `$80041` 0, `$80400` 0 for the whole fight, `py/flags.py`). Score hit `$200`, death `$10000` (10,000 points, verified: P1 `$00003000 -> $00013000` at the death frame).
Name: green snake on the shoulder from the sprite (`out/sheet_nat3.png`: the same frames show a green snake on the floor = type `$37`), *inferred* from the picture.

### Snake `$37` (`$1cce8`) (*read* plus live rows in `nat3`)

hp 1, death score `$50`; states [0] `$1ce38`, 1 stagger `$234e6`, 2 death `$2397e`, 6 `$1cec2`, 7 `$1cef4`, 8 `$1d022`, 9 `$1d09a`, a `$23248`, b-d `$1d106`. Live: spawn at the owner's position, states 6, 7 (walk 1 px/frame: 38 frames x 3788 -> 3732), 9 (arc jump, 64 frames), death by the player (state 2) 25 frames after its second jump. Damage as an attacker: not measured (no `H` line with owner type `$37` in the logs).

## 7. Type `$4d` (tusked brute, `$210cc`)

Handler head (`$210cc`, *read*): every frame `move.b #$80,$81e03` (blocks the script's list A spawner: `$f388` tests the bit, `$10254` clears it per frame), then the usual pre-steps (`$22ce4`), and after the dispatch `$2331c`/`$2242c`: **if the record is no longer active (`+0` bit 7 clear) it clears `$80400` bit 5**. Init (`$21182`): sound `$0c` (`moveq #12,D7; jsr $e1c`), `bset #5,$80400`, `+35` bit 2, facing 1, hp `$18`, `+17` bit 0, `+7`=2, `$22b48`; a 64-frame intro with `+0` bit 3 (paused: no hit accepted, no action; counter `+30` byte `$40`), then `$2280c` with D7 = `$80` (jump amplitude) and state 9 (a leap toward the player).
Flags (`kill_4d2`, `py/flags.py`): `$80400` 0 -> `$20` at frame 801, back to 0 at frame 4204 (the frame the record is gone, 1 frame after the end of the death state); `$80040` stayed `$80` and `$80041` `0` throughout: **bit 5 of `$80400` only**; no `$80040` bit 2, no `$80041` bit 7, no health bar byte `$8005c`. `$81e03`: `128` in every F line of `nat4` while any of `$4d`/`$4f` was alive (list A progress stopped until frame 4339).
The state routines are those of the level 3 boss `$10`, which hard-codes the ground lane `move.w #$1c0,12(A6)` in states 6-9, e, f and the arena x `$ae0` in state `$10`: the level 5 entry (y `$1a0`, scroll y `$100`) is a lane-`$1c0` fight; in an isolation run at y `$7c0` `$4d` snaps to y `$80` and misbehaves, so isolate it only at the script position (`CB_SCROLL`/`CB_HOLDSCROLL` `e20:100`, spawn y `$1a0`).

| state | routine | role | measured (`wander_4d2`, `kill_4d2`, `inj3_4d`) |
|---|---|---|---|
| 0 | `$21182` | init, 64-frame intro, then leap (state 9) | 64 frames |
| 1 | `$15d64` | stagger; then {6,9,f,9} (`$15df6`), same table after a knockdown; for 9 and f the jump amplitude is `$a0` (`$2280c`) | 15..105 frames; `1>9` 14, `1>f` 7, `1>6` 6 in `kill_4d2` |
| 6 | `$15dfe` | idle at y `$1c0`: chooser on anim wrap; spawns the attached effect object `$25` (while `+51` bit 0 clear); after `$80` frames in 6 (byte `+30`) goes to 8 | 16-143 frames; 18 timeout transitions 6 -> 8 (byte `+30` = `$7f` before) |
| 7 | `$15e92` | run toward the target 2.5 px/frame at y `$1c0`, chooser **every frame**, hit box `$17` every frame while still in state 7 | dx 2.52/frame |
| 8 | `$15f0c` | charge in the facing direction 2.5 px/frame for `$80` frames then chooser each frame; hit box `$17` every frame | 4-144 frames, dx 2.0; damage 20 (73 hits, spawned 9129 frames in state 8, 1844 in state 7 over all logs) |
| 9 | `$15f84` | leap toward the target: 2.5 px/frame, arc `+37` += 2 (65 frames), `+17` bit 2, lands at y `$1c0`, then 6 | 65 frames, y excursion 207 |
| a | `$15ff6` | fall (used after the jump bounce), returns to 1 if `+17` bit 5 (hit while falling) else 6 | never entered |
| b, c, d | `$2409a`, `$24126`, `$24286` | grab, hold (12 frames), throw (16 frames), immune; heavy throw (sets P1 `$80157` bit 1): landing -8 | b <= 16, c 12, d 16 frames; 8 sequences in `wander_4d2`; 8 of 8 landings -8 |
| e | `$16090` | slow shuffle 0.5 px/frame until the animation wraps, then 8 | 16 frames |
| f | `$160ec` | leap (`+17` bit 2, 2.5 px/frame, arc +2, amplitude `$a0` set by the chooser), lands at y `$1c0` | 65 frames, y excursion 160 |
| `$10` | `$1615e` | level 3 only: run to x `$ae0`, spawns `$24` | never entered |
| `$11`-`$16` | `$15dfe` | aliases of state 6 | never |

Chooser (`py/chooser.py 4d`, T1 `$26a2e`, T2 `$26a6e`, T3 `$26aae`): T1 leaves by P1 sub-state: `$26c8e` (dx>>4 0..3, sub 0..3): {b, b, b, b} (grab, then `$2280c` with D7 `$a0`, then f: the grab check can fail and the enemy falls to 6 or leaps); `$26cb0`: 8; `$26cb8` (0..5): e; `$26cc0`: 7; `$26cc8`: 6; `$26cd0`: {9, f, 9, f}. T2: dx>>4 0..2: 6, else 8. T3: 0..7: 6, 8..f: 8. Validation: 164 of 164 chooser transitions in the predicted set (kill 28, wander 34, inj3 102), 28 natural ends of a leap and 18 idle timeouts (6 -> 8 with byte `+30` = `$7f` the frame before, 18 of 18). The chooser runs after the state's own movement step, so the prediction uses the record position of the new row (a first version using the previous row's position mispredicted 14 of the 7 -> 8 transitions).
Immunity: states b, c, d (286, 228, 304 of the rows set), stagger, death; state f is hittable (`+17` bit 1 set in 9 of 584 rows); injections accepted in 6, 7, 8, 9, e (>= 22 events in `inj2_4d`/`inj3_4d`), ignored in b, c, d (57 of 57). Contact damage 0. Score hit `$200`, death `$10000` (`$00004600 -> $00014600` at the death frame 4145 of `kill_4d2`).

### Attached object `$25` (`$1b5e4`)

Spawned by `$4d` state 6 (`$15e6c`), 51 records in `wander_4d2`, 18 in `kill_4d2`. State 0 (`$1b610`): `+6`/`+53` bits, owner's `+51` bit 0 set, placed at owner x -`$18` (facing 1) or +`$19` (facing 0), y -8; var 0 -> state 1; states 1/2 (`$1b686`) wait until the owner leaves state 6 or the animation ends, then clear the owner's `+51` bit 0 and remove themselves; 32-frame life in the logs. No damage, no hit box, no score. *inferred*: a small attached effect (not identified on screen: the sprites in `out/sheet_25.png` show the thrown player instead).

## 8. 0x44 variant 1 (level 5)

Handler `$1faac` (clone of the type `$0b` states, normal enemy, hp 8; the GRUNTS agent covers the type). Variant byte read in state 0 (`$1fb9c`), verified live (`v44_0`, `v44_1`, `v44_2`, spawn at frame 800, scroll x `$100`, scroll poke `$500` at frame 1000): **variant 0 stays in state 0 (stands, hittable) until the scroll x reaches `$500`** (state 0 for frames 800-1000, state 6 at 1001), **variant 1 starts at once** (state 6 at frame 801, then walks), **variant >= 2 starts in state `$a`** (falls first; state 6 at 802). The handler does nothing at all (not even drawing) while scroll y < `$200` (`cmpi.w #$200,$80406`). In the level 5 script: var 0 at trig `$140` x `$260` and trig `$160` x `$280` (guards that wait), var 1 at trig `$300` x `$2e8`/`$2c8` (start walking).

## 9. Spawn verification from the script

`py/spawn_check.py` against `nat1`-`nat4` (pool B and A both logged): list A entries of my types seen as first rows of records with the same type, variant and position (+-8 px): `$4b` trig `$1c0` x2 (frames 800, 1183 of `nat1`), `$4a` var 0 x `$250`, `$3b0`, `$3c0` (3 of 4; the x `$260` entry never produced a row, see section 3), `$4a` var 1 (`nat1` frame 3878 at x `$821`, y `$47f`; `nat2` at frame 800: x `$821`, y `$480`), `$4b` trig `$c00` x4 (`nat3` frames 800, 881, 882, 1302; scroll `$c00`; the stage's pool B props block the spawner between, see below), `$4c` x `$df0`/`$e10` (`nat4` frames 800, 801, scroll held `$e20`), the third `$4c` (x `$cd0`) spawns behind the camera and has no row, the fourth `$4c` and `$4d` (`nat4` frames 803, 804), `$4e` after `$4f` after `$4d` (see 0, finding 6). Spawn writes match `$f388` (type, variant, x, y copy) in every row.
Spawn blocking by props (outside my types, found while testing): pool B types `$45-$47` (handler `$2b1ca`) set `$81e03` bit 7 every frame while their x is less than scroll x + `$f0` (`$2b226..$2b238`): in level 5 list B puts `$46` at x `$cf0` and `$47` at x `$df0`, so list A entries are held back while those props are on screen (`nat3`: the second `$4b` waited from 1 frame to 80; with `CB_PTRB` to the list B terminator `$6d5a2` all four `$4c`/`$4d` entries spawned within 5 frames).

## 10. Open items

* `$4a` state 8, `$4b` state 8/f/9, `$4c` states 8/9 under natural play: leaves chosen only with certain P1 sub-states (`+47`); the idle P1 of `wander_*` never produced them for `$4a`/`$4b`.
* `$4d` arena at its real camera: all tests used a held scroll (`$e20,$100`); the real camera lock cell `$200d` (lead's note) was not exercised.
* Throw hit (`+17` bit 6) on `$4b`/`$4c`/`$4d` not injected (tested on `$4a` only).
* Pool B `$4a` (list B entry at trig `$eb0`, x `$fd8`, y `$1d0`), `$47`/`$49` (spawned by `$48` at `$20a4c`/`$20ae6`) belong to L5B.
* The `$37` snake's attack (damage) and the `$25` object's sprite were not identified.

## 11. Errors and corrections to `BRIEF2.md`

1. `tables_decode.py` damage column is indexed by the owner's pool A type; the game indexes by the pool C hit box type (`$fc34` reads `[2(A6)]` of the hit box; `$21e72` stores `D6` there). Real values in section 3.
2. The brief lists only the pool C hit box damage; body contact (`$f4f4`, `$2331c`) is a second path (1 hp, enemy staggers, P1 scores).
3. `+17`: bit 1 = immune to player hits (set in stagger/death/grab states; `$22c56` and `$2331c` test it), bit 2 = no contact damage (suppresses `$f4f4`, set in jump/attack states), bit 3 = post-stagger flash timer (`$24022`, 16 frames, shows as `+0` bit 3), bit 0 = clamp to screen instead of despawn (`$2242c`). The flash follows the stagger, so the total re-hit gap is 15+16 frames.
4. "walk states call the chooser when the animation wraps": `$4d` state 7 and 8 call it every frame.
5. The brief's "`$20f9e` spawns `$41`" is the init of `$4b`; `$020a4c`/`$020ae6` are inside `$48`'s handler (`$1ffbc`-`$20bec`): not my group.
6. The scripts for level 5 are all horizontal triggers (47 of 47 bit-15-clear); the vertical movement is camera-only.
7. Types `$4c` and `$4d` are not both boss-flag setters: `$4c` sets nothing, `$4d` sets `$80400` bit 5 and `$81e03`, never `$80040` bit 2 / `$80041` bit 7.

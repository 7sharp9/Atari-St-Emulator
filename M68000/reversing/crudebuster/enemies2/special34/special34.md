# SPECIAL34: pool A types of levels 3 and 4 that are not plain grunts

Level numbers are the level byte `$80046` (0-5; "level 3" and "level 4" are the 4th and 5th stages: level 3 ends at the 0x11/0x3a boss, level 4 ends at the 0x12 claw/horned boss and shows "STAGE 5 CLEAR").
Everything marked *read* is from the linear listing (`py/lst.py`), *proven* has a count and a script (`py/README.md` lists them), *inferred* is a guess. Names are descriptive, taken from what the
object draws (screenshot sheets in `out/*_sheet.png`) and does. All frame numbers are from `lua/objlog.lua` runs (MAME, `cbuster`, default dip).

## 0. Summary

| type | handler | name (descriptive) | where | health | hits to kill | score | what ends it |
|---|---|---|---|---|---|---|---|
| 0x1f | `$1a2c6` | Santa Claus boss (throws grenades) | L3 trig `$800` x `$910` y `$1c0`, 1x | `$10` | 16 (proven) | 50 per hit, 10000 on death | death: `$80040` bit 2 cleared, level continues |
| 0x1a | `$19344` | mine cart carrying two grunts | L4 trig `$240..$3c0`, 6x (var 0 x4, 1 x1, 2 x1) | 1 (never decremented) | no hit handler | none | leaves screen at x > sx+`$140` |
| 0x17 | `$18906` | hover platform that delivers a boss/grunts | L3 var `$12` trig `$5f0`, var `$22` trig `$a00`; L2 var 2 (ENEMIES1) | 0 | not hittable | none | flies off the top |
| 0x16 | `$184a2` | hover-bike gunner (rider 0x34) dropping/firing pool B `$3a` | L4 trig `$3f0,$400,$420`, 3x | 0 (dies at once when hit) | 1 (*read*; not proven) | `$11` index = 2000 on hit (*read*) | leaves screen |
| 0x19 | `$18c0e` | small tank with driver 0x45 and gunner 0x46 | L3 trig `$900` x `$8d0`, 1x | 3 (never changed) | not killable by punches (proven 0 of 3 runs) | none | disappears when the driver dies |
| 0x1d | `$19dc4` | motorbike with rider 0x33 | L3 var 1 trig `$400`,`$440`, 2x | 3 (never changed) | see section 5 | none | leaves screen / thrown |
| 0x1e | `$1a14c` | level 4 mid boss, becomes 0x0d at health < `$21` | L4 trig `$500` x `$4c8` y `$2c0`, 1x | `$30` | 16 hits then morph; 0x0d needs 32 more | 50 per hit (idx 2, *read*) | morph, then 0x0d dies |
| 0x12 | `$1654c` | claw machine (var 1) then horned mutant hanging from the cable (var 2) | L4 trig `$8f0` x `$980`, 1x | var 2: `$1e` | 30 (proven) | 300 per hit, 4000 on death | death sets `$80040` bit 3: level 4 clears |
| 0x0c | `$14824` | claw-armed brawler delivered by 0x17 var `$12` | L3 only (spawned) | `$20` | 32 at 1 per hit (3 hits seen) | hit idx 3 (100, read) | death clears `$80040` bit 2 only |
| 0x11 | `$16200` | big boss delivered by 0x17 var `$22`, becomes 0x3a at health < `$21` | L3 only (spawned) | `$30` | 16 hits then morph | 200 per hit (proven) | morph |
| 0x3a | `$1dbbc` | white-maned ape boss, the level 3 end boss | L3 only (spawned by 0x11) | `$20` | 32 | 400 per hit (proven), 3000-class death | death: `$80040` bit 3, then bit 4 |
| type 5 var 1 | `$11938` | grunt that hops in (immune) | L3 x1 (trig `$300`), L4 x6 | 6 | like var 0 | 100 hit idx 3, kills 200/300 (read) | |

Children (named by body, role and spawner, not in depth): 0x34 rider (`$1c410`), 0x33 rider (`$1c312`), 0x42/0x43 claw jaws (`$1f490`, `$1f7a6`), 0x45 driver (`$1fbe0`), 0x46 gunner (`$1fd16`),
0x41 sidekick of 0x0d (`$1eda4`, health `$80`), 0x40 var 1/2 grunts dropped by 0x17 var `$22` (`$1ec1c`, health 8), 0x3b-0x3e grenades (`$1e2c8`, `$1e4a0`, `$1e706`, `$1e922`, health 1), 0x1b (`$194e2`, not analysed, section 11).
Plain grunts of levels 3-4 (0x35, 0x39, 0x3f, 0x40 var 0, 0x44) are not covered here.

## 1. Corrections to BRIEF2 (code wins)

1. **Damage is indexed by the pool C box type, not by the pool A type.** `$fc34` (the pool C hit) reads `2(A6)` = the box record's type (D6 given to `$21e72` / `$24056`), takes the byte `[dip&c][box type]`, multiplies by 4 and subtracts it from the player's `+19`.
   `tables_decode.py`'s per-pool-A-type damage column is therefore the wrong table for every type. Proven: P1 health `$38` fell by exactly 12 (= 3x4, dip column 0) in 50 of 50 hits of the 0x12 boss's box `$22` (`py/hpdrops.py out/t12/objlog.txt`).
   Default dip gives column 0 (first value of each quadruple below).
   Box types used by my types (from the spawner scan `py/spawners.py C` and `S`, hex): 0x0c: `$23` (`$14a68`), `$2a` and `$2b` (via `$24056`); 0x0d: `$0e`; the 0x0b family states b/c/d/e (0x1e, 0x0d share them): `$0f`, `$10`, `$11`, `$12`;
   0x12 var 2: `$22`; 0x11: `$25`, `$26`, `$28` (via `$24056`), `$27`; 0x3a: `$29`; type 5: `$13..$16`. Damage per box at dip column 0 (health points of 56): `$0e` 20, `$0f` 12, `$10` 12, `$11` 16, `$12` 12, `$13` 12, `$14` 16, `$15` 20, `$16` 16,
   `$22` 12, `$23` 20, `$25` 16, `$26` 16, `$28` 16, `$29` 20, `$2a` 16, `$2b` 16 (`py/boxdmg.py`).
2. **Pool B projectiles/explosions use a different damage rule.** `$100b2`/`$f96c` take the byte `[pool B type]` at `$10122` with no multiplication: pool B `$3a` (the hover-bike bullets) does 1, types 4 and 5 (explosions) do 10 (proven: -10 in 2 of 2 explosions, `out/t19c`, `out/b1f`).
3. **`$f4f4` / `$f82e` are two different tests**: `$f82e` tests the pool A record's hurtbox (`$6b000[type][state]`) against the player's *attack* rectangle (`+72..+78`, only while the player's `+28` attack id is non-zero) and sets the record's `+6` (bit 7 = hit, `$90` P1, `$d0` P2); `$f4f4` tests the
   hurtbox against the player's *body* rectangle (`+64..+70`), i.e. touch contact, and `$f700` then also subtracts 1 from the player's health: the tank and the motorbike hurt by touch (-1 every 8 frames, proven 4 of 4 at `out/t19c` f979..f1003 with an idle player). Every handler tail `$2331c` calls both (unless immune bits +17 bit 1 / bit 2).
4. **`+0` bit 3 is "invulnerable"**, not only a hit flash: `$22c56`/`$22ce4` skip a record whose `+0` bit 3 is set; bosses set it in their intro, attack-start and knock-back states and clear it in walk states.
5. The score of a hit/kill (`$248bc`, `$3fae`): the byte is an index into the BCD table at `$4016` (4 bytes each): 1:10, 2:50, 3:100, 4:100, 5:200, 6:200, 7:300, 8:300, 9:400, 10:400, 11:500, 12:600, 13:800, 14:1000, 15:1000, 16:1000, 17:2000, 18:2000, 19:3000, 20:3000, 21:4000, 22:5000, 23:10000, 24:1000000.
   Hand-written handlers call `$3fae` directly with an index (0x16 hit `$11` = 2000, 0x12 body `$08` = 300 per hit and `$15` = 4000 on death, 0x19/0x1d none).
6. BRIEF2 says "bit 3 of `$80040` is set by the boss death if `$80041` bit 7 is set": proven (0x12: f4390 `$80040` 84 -> 88 and `$80041` 80 -> 00 in the same frame; 0x3a: f1818). The boss that sets `$80041` bit 7 at init is the one that ends the level (0x11 and 0x12, not 0x1f, 0x0c, 0x0d, 0x1e).
7. `ai_tables.py` prints the final routines but not what they do: `py/ai_summary.py <type>` expands each routine into the distribution of states it starts (a routine is one start routine `move.b #N,3(A6)` or a 4-way `$ea44&3` chooser) and merges equal dx buckets. All `s?` entries are unresolved routines.

## 2. Type 0x1f: Santa boss (level 3, trig `$800`)

Name from the screenshots (`out/b1f_sheet.png`: white beard, red suit, sack, snow falling). Handler `$1a2c6` = `$24022; $22c56; $22dac; state dispatch (table $1a310); $22540; $2331c; $2242c`, then copies `+5` to `$8005c` (the boss health bar).
Script: one entry (`$6c50e`: trig `$800`, x `$910`, y `$1c0`, var 0). It spawns the moment the scroll counter reaches `$800`.

State table (`py/typestates.py 1f`, read, live sequence counts below):

| state | routine | role |
|---|---|---|
| 0 | `$1a370` | init (first frame): `$80040` bit 2, `+0` bits 3 and 6, `$80400` bit 5 (scroll lock), facing left, **health `$10`**, `+7`=2, banner `$1c8a(56)`, target `$22b48`; waits for `$8040a >= $800`, then state 7 and music id 92 |
| 1 | `$1a3f6` | hit reaction (own, not `$234e6`): if `+53` bit 5 (at the screen edge) a walk step then state `$c` (+sound 96); else the shared knock-back `$235fa` and, if `+17` bit 4, state `$b` |
| 2 / 4 | `$23cf2` / `$23e66` | shared boss death / knocked-down (see below) |
| 3 | `$22ecc` | held by a player |
| 5 | `$1a47a` | thrown-away fall (`$23748`), then state `$b` |
| 6 | `$1a4ae` | walk step (`$226e4`); if the walk ended in state 6 and `+53` bit 5 is clear: state `$c` (throw) + sound 96, else state 7 |
| 7 | `$1a530` | hop toward the target: arc (`$22856`, height `$10`, +37 += 4, 32 frames), x velocity +1.5 or -1.5 toward the player, turns at 0x80 distance; on landing (`$2297a`): compares own y with the target's: higher lane target -> state 9 (high jump, height `$80`), no ground -> `$a`, else 6/7 |
| 8 | `$1a692` | 0x40 frames of walking away from the target at 2.0, then 7 (reached from state `$b`) |
| 9 | `$010c0a` | jump (code shared with type 1) |
| `$a` | `$23248` | thrown/falling away |
| `$b` | `$1a726` | immune (+17 bits 1,2, `+0` bit 3) until the animation ends, then state 8 |
| `$c` | `$1a764` | **throw**: immune; when the animation ends it spawns five pool A records (`$21eb6`, D7 = 0..4) whose type is chosen at random from the five 4-entry lists at `$1a818` (`3b 3c 3e 3b`, `3b 3c 3c 3e`, `3b 3c 3d 3e`, `3b 3c 3e 3e`, `3b 3e 3c 3b`, picked by `$ea44 & 3`), then state 7 |
| `$d..$16` | `$1a4ae` | = state 6 |
| `$17` | `$22e30` | held variant |

Live (`py/run.sh b1f`, injection at frame 802, teleport bot, `out/b1f/objlog.txt`):

- sequence 7 -> 9 -> 1 -> `$a` -> 6 -> `$c` -> 7 ..., `$c` entered at f898, 1014, 1128, 1237 (interval about 115 frames), five minions per throw.
- **16 hits to kill** (health `$10` -> 0; the bot's hits came at `+5` = `$0f,$0e,$0d,$0c,$0b,$0a,$09,$08` then seven consecutive frames `$07..$00` while the boss was in state `$a`: a boss in the knock-back state `$a` is hittable every frame).
- score +50 for each of 15 hits and +10000 at the killing blow (`py/scores.py out/b1f/objlog.txt`: 15 lines of +50 then +10000 at f1359). Matches `$24952[1f]` = idx 2/23/23.
- death (shared `$23cf2`): knock back arc, bounce, then `+0` bits 4,5 and a 64-frame counter; at the end `$80040` bit 2 and `$80400` bit 5 cleared, banner `$1c8a(57)`, record cleared. Proven: `$80040` 84 -> 80 at f1495 (136 frames after the last hit at f1359), `$80041` stays 00 (bit 7 was never set by this type), **so `$80040` bit 3 is not set: the level does not end**. Bit 4 is not set either; the scroll lock (`$80400` bit 5) is released and the script continues (next entries 0x39/0x35/0x3f/0x40 and the 0x17 var `$22` delivery).
- damage dealt by the boss itself: none measured. 600 frames of fight cost P1 one hit of 10 (`py/hpdrops.py out/b1f/objlog.txt`: f1347, -10, no box). The -10 is a pool B type 4 explosion (two more type 4 records appear at f1335 at the grenade landing points). The boss has no pool C box (spawner scan: no `$21e72`/`$24056` call in `$1a2c6..$1a82c`).
- the grenades 0x3b/0x3c/0x3d/0x3e: health 1 (`$22c56`), spawned at the boss's x, y-16 on the facing side, variant 0..4 = slot; state 9 arcs them with x velocity -2, -1, 0, +1, +2 (variant 0..4: `$1a418` and the compares at `$1a3f8..$1a43c`), `$a` hangs them at y `$1aa`, 0x3c/0x3d/0x3e add states b (`$1e5fe`, `$1e884`) and 6 (`$1e794`, `$1e9aa`) that drop them (y `$1e0`). Each lands as a pool B type 4 explosion (10 damage). *read for the exact per-type difference.*
- the five-entry table at `$1a804` is a table of pointers to four-byte type lists (above), not a state table.

Phases: one phase only (no morph); the hop distance and the throw interval are the only patterns.

## 3. Type 0x1a: mine cart (level 4)

Handler `$19344` has no hit reaction (`$22c56`/`$22ce4`/`$22dac` are not called): `jsr state dispatch; $22540; $2242c`. Table `$1936c`: state 0 `$193cc` (init), 7/8 `$19432`, 6/9/b/c/d... `$19418` (immune markers), 1 `$234e6`, 2/4 `$23fb6`, 5 `$1bf80`, `$a` `$1c15c`, `$d` `$1c2a4`.
- init: `+0` bits 6 (hittable), 3; `+53` bit 6; health 1; facing right (`+4`=0); state 7; then by variant spawns two passengers (`$21eb6`, linked through `+60`): var 0: 0x39 var 1 and 0x39 var 2; var 1: 0x35 var 1 and 0x39 var 2; var 2: 0x3f var 1 and 0x39 var 2 (`$1946e..$194e0`, read).
- state 7: x velocity +2.0 (the facing is always right), leaves the screen when `x > sx + $140` (`$2242c`, `+17` bit 0 clear). Proven: 188 of 189 frame steps advanced exactly 2 px (the other step is the init frame), x `$0c8` -> `$240` = sx + `$140`, record cleared at f990 (`out/t1a/objlog.txt`, script in `py/README.md`).
- the passengers jump off in the middle of the screen (screenshot `out/t1a_sheet.png`: two grunts leave the cart at about x `$11e`/`$114`, f833/f844) and are ordinary 0x39 grunts (score 200/400 per hit/kill, seen in `out/t1a/objlog.txt`: +200, +400, ...).
- states 2/4 (`$23fb6`): spawn pool B type 5 variant 1 (explosion/drop) and clear the record; reachable only if some other code sets state 2/4 on it (nothing in its own handler does).
- damage to the player: none measured (the cart passed through the player at `hp` hold off in `out/t1a`: not separately proven, labelled *inferred* from the absence of any `$f4f4`/box call in the handler).
- usage: level 4 entries `$6c5c0` (var 0, trig `$240`, x `$210`), `$6c5d0` (var 0 `$280`), `$6c5d8` (var 1 `$300`), `$6c5e0` (var 0 `$390`), `$6c600` (var 0 `$3c0`), `$6c620` (var 2 `$400`).

## 4. Types 0x17 and its deliveries (level 3)

Handler `$18906`, variant byte `+16`: **the low nibble selects the handler (all three entries of the table at `$189ca` are `$189d6`: variants 0, 1, 2 behave alike), the high nibble selects what it carries.**

| variant | where | carries | sub-state at start (`+18`) |
|---|---|---|---|
| 2 (hi 0) | level 2 (ENEMIES1) | pool A 0x10 | 0 (moves left, x -1 per frame until the x low byte is `$80`) |
| `$12` (hi 1) | level 3 trig `$5f0` x `$5b0` y `$160` | **0x0c** | 2 (enters from the left at +1 px/frame until x = scroll + `$d0`) |
| `$22` (hi 2) | level 3 trig `$a00` x `$9c0` y `$160` | **0x11 + 0x40 var 1 + 0x40 var 2** | 2 |

State 0 (first frame, `+0` bit 6 clear): sound `$2f`, `+7`=2, `+53` bit 6, `+0` bit 6, the carried spawns above, then for every variant a rider pool A 0x34 var 1 (`$1899c`). Sub-states (`+18`, table `$189f2`, *read*): 0 `$189fe` x -1, anim; 1 `$18a4e` y -1 until y low byte `$e0`, then the rider (`+60`) gets state 4 and the record clears (the rider spawns a 0x1b); 2 `$18a86` x +1 until x = `$8040a + $d0`, then sub-state 1.
The passengers hang at (x-`$20`, y-`$28`) and are released when the platform's x reaches `$6a0` (0x0c: `$14954`, state `$a` + sound 87). Proven: `out/t17/objlog.txt`: platform x `$5b0` -> `$6c4` (f803..f1078, +1 per frame), 0x0c fell from y `$138` (state `$a` at f1042) to y `$1c0`
(state 6 at f1076); 0x17 state 2 / `+31`=3 at f1078, record cleared at f1201 (the ascent is 123 frames of y -1). Screenshot: green hover platform with a rider (`out/t17_sheet.png`).
Variant `$22` (`out/e3/objlog.txt`, trig `$a00`, 5 pool A records at once): 0x11 and the two 0x40 fell at f993..f1025 and the 0x17 left at f1073 (state 2) / f1201 (gone).
Score, health, damage: none (health 0, no `$22c56`); the platform is not hittable by the player (the hit routines `$f4f4`/`$f82e` are called in no sub-state *read*).

## 5. Types 0x19 (tank), 0x1d (motorbike), 0x16 (hover bike)

**0x19 tank** (`$18c0e`, level 3 trig `$900`, x `$8d0`, y `$1c0`). `+0`/`+16` is used as a mode: +16 = 0/2 normal (`+18` sub-states, table `$18cfc`, 9 entries), 1 (`$190a6` another table: stunned/exploding), 3 (`$1906c`: spawns three pool B 5/1 at (x, y+8), (x-`$18`,..), (x+`$18`,..), clears the record and `$80400` bit 5).
First frame: `$80400` bit 5 (scroll lock), spawns 0x45 (driver) at y+`$10` (`$18c22`), `+5`=3, plays sound `$33`; +17 bit 7 (grabbed) is checked each frame (the player can climb/grab it: `+88(A0)` bit 2 etc., *read*).
Sub-states (read): 0 `$18d20` drives in from the left (x +1) until x = scroll + `$30`, 1 `$18d72` idle (a hit with `$f82e` takes health -1 with a 32-frame cooldown, health 0 -> sub 2/state 1), 2 `$18dc8` idle, 3 `$18dd4` drives right to scroll + `$80` then sub 4, 4 `$18e5a` drives left to scroll + `$30` and back
(a counter in `+23` makes every third pass sub 5), 5 `$18ef2` fast right (x +2), 6 `$18f66` **run-over**: sets the player into a flattened state (`+88` bit, `+23 = $80` kill flag after 64 frames), 7 `$19002`, 8 `$1903e`. A shared tail `$19328` plays sound `$33` every 128 frames (engine).
Live (`out/t19b`, `out/t19c`): the tank drove in at +1 px/frame to x `$931`, then shuttled between x `$931` and `$981` (sub 3/4 alternating every about 80 frames: `rectrace.py out/t19c/objlog.txt 19 800 3000 30 3,5,16,18`), health stayed 3 in all runs (the bot attacked the children),
**contact: P1 lost 1 health every 8 frames while overlapping (4 of 4, f979..f1003, idle player)**; the tank disappeared in the same frame the driver 0x45 was killed (f1643/f1644). Children: 0x45 driver health 5 (observed `+5`=5, 4, 3, 2, 1: -1 per hit, cleared at f1643), 0x46 gunner health 2 (fires a pool B missile: **-10 on hit**, 2 of 2 in `out/t19c` f922, f1250).
Attack the player: contact (-1/8 frames), the gunner's missile (-10), the run-over sub-state 6 (*read*: kills).

**0x1d motorbike** (`$19dc4`, level 3 var 1, trig `$400`/`$440`, x `$530`/`$570`, y `$1c0`). Variant = direction (`+4` = 1 left); spawns the rider 0x33 (`$19dd6`), health 3. Mode state `+3`: 0 rides, 1 held by a player (`+17` bit 7 set when grabbed: position follows the player, `$1a072`), 2 thrown (`$1a0e2`: flies and falls, then the rider gets state 3, pool B 5/0, record cleared).
Sub-states `+18` (table `$19eb6`): 0 `$19ec6` drives at `+32` (per variant, `$19e82`: -2 left / +2 right) with terrain probes (`$ebb0`), 1 `$19fbe` recoil after a hit (x += `+36`, 16 frames, `+22` grows 0 -> 6 -> 4), 2 `$19f..` no ground -> falls (y +3 until ground, `$a99a` dust), 3 `$1a054` leaves: rider state 3, pool B 5/0, record cleared.
Live (`out/t1d`, level 3 injection, idle bot): the bike drove left at -2 px/frame (x `$530` -> `$4bc` in 57 frames), each player hit (3 of 3) knocked it back by 0x20 (x `$4bc` -> `$4dc` etc.), **each of the three hits also cost the attacker 1 health** (`hpdrops.py out/t1d/objlog.txt`: 3 of 3 -1, with the 0x1d at contact), health `+5` stayed 3, and after the third hit the bike left (f927-f928: sub-state 3). No score (`$24952[1d]` has idx 0).

**0x16 hover bike** (`$184a2`, level 4 trig `$3f0,$400,$420`, x `$520/$520/$550`, y `$140/$180/$180`): first frame spawns the rider 0x34 var 0 and music `$2f`; `+16` selects the flight program: 0 `$18504` (sub-states: 0 `$18528` fly left x -2 with wheel animation while dropping/firing pool B `$3a` var 5 (left) or 3 (right) every 8 animation cycles; becomes sub 1 `$1867c` when x < scroll - `$40`: flies right x +2 until x > scroll + `$140`, then removes itself and the rider; a hit (`$f82e`) gives score index `$11` = 2000 and sub 2 `$1874e`: flies off along the hit direction 16 frames, then pool B 5/0 and rider state 2), 1 `$18788` (enters from the top, y +2 to scroll-y + `$b0`, then left, then up: a 4-sub-state loop), 2 `$188c0` (stationary dropper: a pool B `$3a` every 32 frames, variant = projectile variant). Level 4 uses variant 0 only.
Live (`out/t16`, `out/k16`): the bike flew left at -2 px/frame from x `$51e` to `$3b0` (f801..f984), fired pool B `$3a` bullets variant 5 and 3 diagonally down (`out/t16/objlog.txt` pool B lines: v05 at f832/864/896, v03 at f992/1024/1056), one bullet hit P1 for **1** (f1061, `$10122[3a]` = 1), then sub 1 at f984 (x `$3b0`, flying back right) and gone at f1180. Not killed by the bot in either run (a teleported punch at the bike's height did not register in about 390 attack frames, 0 hits: open).

## 6. Type 0x1e (level 4 mid boss) and type 0x0d

`$1a14c` is an own prelude + the **type 0x0b state set**: `$24022; $22c56; $22dac; state table $1a1e8`, prelude `$1a154` sets `$80015` bit 3 on every frame, `$80400` bit 5 and does nothing else while `$80406 < $200` (the `bset` come first, the handler returns before the body).
Table: 0 `$1a248` (own init: `$80040` bit 2, `+0` bits 3, 6, health **`$30`**, `$1c8a(56)`, waits for scroll x >= `$500`, then state 6 and music 93), 1 `$0144b8`, 6 `$01453e` (walk, AI `$2438a`), 7 `$0145ae` (walk toward), 8 `$014624` (walk away 0x80 frames), 9 `$0146a0` (jump), b..e `$014722/$01472e/$01473a/$0147d8` (attacks with boxes `$0f`, `$10`, `$11` (a jump attack), `$12`), 2/4 `$23cf2/$23e66`.
These states are type 0x0b's (level 2, ENEMIES1); 0x0c, 0x0d, 0x11 reuse parts of them.
**Morph**: `$1a1a2` (each frame after the dispatch): when health < `$21` and state == 6 it spawns a pool A 0x0d, copies its facing (`+4`) to it through `+60` and clears itself. Proven (`out/t1e2`, health poked to `$20` at f1100): 0x1e cleared at f1228 and a 0x0d with health `$20` plus its sidekick 0x41 (health `$80`) appeared in the same frame.
Without the poke the bot needs 16 hits (health `$30` -> `$20`; seen `$30,$2f,$2e,...,$28` after 9 hits in `out/t1e`).

**0x0d** (`$14b18`, health `$20`, only spawned): own states, table `$14b8e`: 0 `$14bee` (init: `$80040` bit 2, `$80400` bit 5, `$1c8a(56)`, spawns pool A 0x41 at the same place and pool B 5/0, `+51` bit 1 links the sidekick), 1 `$14c96` (hit: `$234e6`, then random next state from the 4 bytes `0e 0d? ...`), 6 `$14d08`, 7 `$14d5a`, 8 `$14df0` (walk away), e `$14e62` (attack: pool C box `$0e` when the animation reaches frame 1; if the target is in sub-state 1 or 2 it goes to f instead), f `$14ee8`, `$10` `$14f28` (commands the sidekick: `3(A0)=$11`), `$11` `$14f8a`.
The AI distribution (`py/ai_summary.py 0d`): at dx < `$20` the next state is 6 or e or f (target's state dependent), at medium range `$10` (the command state) and walk 7, beyond `$a0` walk 7.
Live (`out/t1e2`): 0x0d states cycle 6 -> b -> c -> d -> 6 (with b, c, d from `$02409a/$024126/$024286`, the "grab the player" states: P1 went to states `$0a`, `$13` and `$0c`...) and 6 -> `$10` -> `$11` -> ...; sidekick 0x41 mirrors the state. Damage: box `$0e` 20, the grab states change P1 state (not a health box).
0x0d's death: shared `$23cf2` (clears `$80040` bit 2, `$80400` bit 5, banner `$1c8a(57)`); `$80041` bit 7 is not set by 0x1e/0x0d, so `$80040` bit 3 is not set (the level continues to the 0x12 end boss) *read*.

**Level 4 camera (lead's question)**: the 0x1e handler's first two instructions (`bset #5,$80400`, `bset #3,$80015`) run every frame, even when its body is gated. In my injection (scroll x `$500`, y `$100`, script pointer at the `$500` entries, four records alive: 3f, 40, 44, 1e) the camera did scroll down from y `$100` to `$200` at +1 per frame between f802 and f1059 (`out/t1e/objlog.txt`), starting when the bot had put P1 on the lower floor (P1 at (`$592`,`$233`) at f802): `$81e02` was **4**, not 2, during the whole descent; `$80400` read `$20` and then `$a6` once `$81e13` had counted `$e0`. So in this run the descent did not need `$81e02 == 2`. When P1 stayed at y `$1c0` (`out/t1e` first variant, bot idle) the camera did not move in 800 frames and 0x1e stayed in state 0 (`+5` = 0). The `$1948` rule (count == 2 plus the `$8053c` counter) is therefore not what lets the camera pass in my runs; *open*: which phase of `$81e12` makes `$8040a/$80406` follow. The boss only starts when `$80406 >= $200` (read, proven: 0x1e `+5` becomes `$30` at f1059 exactly when `sy` reaches `$200`).
What the boss does in the lower area: the fight above (states 6/7/e, `+0` bit 6, boss bar `$8005c` = `+5`), 16 hits -> 0x0d.

## 7. Type 0x12: claw machine and horned boss (level 4 end)

Handler `$1654c`: `+16` is the mode (table `$165b4`): 0 `$165c4` (stub), 1 `$165ee` (claw), 2 `$168cc` (boss body), 3 `$171f8` (death). First frame (`+0` bit 6 clear): `$80040` bit 2 and `$80041` bit 7 (**event on, this one ends the level**), `$80400` bit 5, `+7`=1, pool B `$50` (the cable, variant 0), **pool A 0x42 and 0x43** (the two claw jaws) and `+0` bit 6.
Level 4: trig `$8f0`, x `$980`, y `$1c0`.

- **mode 0**: waits until `$8040b == 0` (the scroll counter's low byte; entry triggers at `$8f0`, so the scroll must reach `$900`), then mode 1, x = scroll + `$30`, music id 12. (Live: with the counter at `$8f0` the stub waited forever, 1 of 1.)
- **mode 1, the claw** (y descends from `$1c0` to `$200`; sub-states `+18`, table `$16626`, read): 0 `$16646` descend (y +4 until `$200` -> 5), 5 `$167ae` hunt: three 64-frame phases (`+23` 0..3) in which x follows the nearest living player at 1 px/frame, then at x equal -> 1, 1 `$1665a` lower (y +4 to `$2a0` -> 2 (or 7 if the 0x500-frame timer `+26` has expired)), 2 `$16718` retract (y -4 to `$200` -> 5), 3 `$1674a` **carrying the grabbed player** (y -2, the player's position = claw x, y + `$30`), 4 `$16778` rise, 6 `$16878` hold (0x80 frames, then the player is released **and `clr.b 19(A0)`: P1 health set to 0**), 7 `$168a8` leaves down to y `$2c0` -> mode 2.
  A grab happens when the claw touches the player (`$f4f4` body hit, `+6` bit 7): player flags `+88` bit 4, `+90` bits 1, 7, player state `$d`, link `+96`. The jaws 0x42/0x43 are drawn open/closed by `+18`.
  Live (`out/t12` first runs, natural): claw descended to `$200` at f817, hunted, lowered at f1009, **touched P1 at f1042 (health -1) and grabbed at f1042**, carried it up (`ps` = `$17`, y `$1be`..`$16e`) and released at f1269 with **health 56 -> 0 in one frame (proven: the harness refill saw `hp=00` at f1269, 1 of 1)**, P1 dead; with the bot idle the player died at about f1900 (game over screen, `out/nat12_sheet.png`).
  The mode lasts 0x500 = 1280 frames (`+26` incremented once per frame, `$165ee`), then sub-state 7 and mode 2. Measured: mode 1 from f801 to f2093 in the run where the player survived (`$2c0` reached at f2093, 1292 frames).
- **mode 2, the horned mutant** (screenshot `out/t12_sheet.png`: purple armoured creature hanging from the cable) at (`$910`, `$2c0`): init at `$168cc`: `+7`=2, state 1, **health `$1e`**, `$8005c` = health, `$1c8a(56)`, sub-state 0. Position limited to x `$908..$9f8`. Sub-states (table `$1696e`, read):
  0 `$169a6` choose by the distance to the nearest living player (`+28`): >= `$60` -> 3, >= `$40` -> 1, else 2, every 40 frames; the `$f4f4`/`$f82e` tests (when `+32 == 0`) send a hit to sub 8;
  1 `$16b3e` walk x ±1 (24 frames), 3 `$16be2` walk (other animation), 2 `$16c54` **attack: x ±1 for 50 frames, spawning pool C box `$22` every frame (12 damage, proven 50 of 50)**, a hit on it ends in sub 4 (grab);
  4 `$16e0e` and 5 `$16e4c` (the boss holds the player: -4 health every two animation cycles `$16e78`), 6 `$16ede` (squeeze), 7 `$16f1c` (follows the player), 8 `$16f78` hurt: after 16 frames health -1, score index 8 (300) and sound `$62`, next sub-state 2 or 3 at random (bytes at `$16ffe`), 9 `$17000` throw: moves ±4 and y +3 until y `$2d0`, spawns pool B `$51` and index `$09` = 400, a `$1708c` (jump arc), b `$17138`, c `$171a4` (health -4: `subq.b #4,5`), d `$16be2` shared with 3.
  Live (`out/t12`, teleport bot to the boss's side): 30 hits kill it (`+5` `$1e` -> `$00`, each hit -1: 30 steps in `py/rectrace.py out/t12/objlog.txt 12 800 7000 60 5,16`), each hit +300 (30 of 30, `scores.py`), the killing hit moves `+16` to 3 (f4294), +4000 at f4390.
  Boss attack damage: box `$22` = -12 in 50 of 50 hp drops (the other 3 drops were -1 contact). The claw-grab kill is instant.
- **death** (mode 3, `$171f8`): state 8, counts 0x20 frames per step (`+20` 0..2); at the third step: `$80040` bit 2 cleared, `$80400` bit 5 cleared, banner `$1c8a(57)`, `$80041` bit 7 cleared, **`$80040` bit 3 set**, score index `$15` (4000) to the killer, `+0` bit 3.
  Proven: f4294 killing hit, f4390 `$80040` 84 -> 88 and `$80041` 80 -> 00, +4000. **`$80040` bit 4 is not set by this handler**: it is set 256 frames later by the end-of-level routine at `$c83a..$c86a` (a counter object: `+22` to `$10`, `+21` to `$10` = 16 x 16 frames; read, and measured f4390 -> f4646: 98 -> exactly 256 frames), then the level changes (f4748: level 5 starts, `$80046` = 5).

## 8. Types 0x0c, 0x11, 0x3a (delivered bosses)

All three share the type 0x0b state set for 6-9 (`$1453e`, `$1459e`...); own init, hit and attack states.

- **0x0c** (`$14824`, spawned by 0x17 var `$12`; level 3 trig `$5f0`): health `$20` (live: `+5`=`$20`), `$80040` bit 2 and `$80400` bit 5 at init, hangs at the platform (x-`$20`, y-`$28`) until the platform's x >= `$6a0`, then state `$a` (falls, sound 87), then the walk/AI states 6/7/8/9 and attacks b (`$14a0e`: box `$2a`), c (`$14a1a`: box `$2b`), d (`$14a26`: box `$23` every frame, then f), e `$14ab0`, f `$14ae4`. Hit state 1 `$1499a` (stagger `$234e6`, then 6 or the random attack `06 0b 0c 0d` / `06 06 0d 0d` from `$14a06`/`$14a0a`).
  Death: shared `$23cf2` (bit 2 and `$80400` bit 5 cleared; `$80041` bit 7 not set, so no level end). The AI table: `py/ai_summary.py 0c`: near (dx < `$50`) a mix of 6, b, c, 8, 7, d by the target's sub-state; far: walk.
  Live: spawned and fell at x `$680` (`out/t17`: state `$a` f1042..1057 y `$138` -> `$174`, state 6 at f1076), took hits in the same run (health `$20` -> `$1d` after three hits: `+5` = `$1f`, `$1e`, `$1d`, f1083..f1147).
- **0x11** (`$16200`, spawned by 0x17 var `$22`; level 3 trig `$a00`): init `$162e2` (music 12, `$80040` bit 2, **`$80041` bit 7**), health `$30` (live), hit +200 each (proven 4 of 4 scores of +200/+400 in `out/e3`: +200 per 0x11 hit, +400 per 0x40 kill), prelude `$1623c`: when health < `$21` in state 6 it spawns 0x3a (copying facing) and clears itself (proven f3334 in `out/e3`: 0x11 `+5` = `$1f` at f3197 and replaced at f3334, 137 frames later, by 0x3a with health `$20`).
  Attacks: boxes `$25`, `$26`, `$28` (via `$24056`, 16 damage each) and `$27` (pool C, 20); AI distribution `py/ai_summary.py 11`. Health bar `$8005c`.
- **0x3a** (`$1dbbc`, the level 3 end boss; screenshot `out/p_3a_sheet.png`: white-maned ape): health `$20` (live), hit +400 (4 of 4, `out/e3`), attack box `$29` (20 damage) via `$24056`, chooser distribution `py/ai_summary.py 3a` (near: 6/f/b/10, far: 7), shared 0x0b walk states, own `$1dd38` init (`$80040` bit 2), spawns pool B `$51` (shock wave: P1 -16 in `out/e3c` f1427) and pool B `$37` var 1 (rolling objects, 5 in a row at x `$b38`..`$b18`, y `$1d8`) at f1464-1480.
  **Death proven (`out/e3c`)**: health poked to 3, after the last hit `$80040` 84 -> 88 at f1818 and `$80041` 81/80 -> 00 (the 0x11 set bit 7 at its init): bit 3 set; bit 4 set 265 frames later (f2083, `$c83a` object), level 4 starts at f2185 (`lvl=4`). Each hit of 0x3a: +400; total 0x11 hits 200 each.

## 9. Type 5 variant 1 (levels 3 and 4)

Handler `$11938` (a fighter: `$24022; $22c56; $22dac; states; $22540; $2331c; $2242c`), health 6 (state 0 `$119d8`). The variant is read once, at the end of state 0 (`$11a0c`):
- var 0: state `$c` (`$11cba`: walk into position with `$227e6`, `+51` bit 0, then AI `$2438a`). Observed (`out/t5v0`): states `$c` (1 frame) -> 9 (jump forward, 71 frames) -> 6 ...
- var 1: `+36` = `$40`, `+38` = y, state `$b` (`$11c5c`): **immune hop in place** (`+0` bit 3, `+17` bits 1, 2; arc height `$40`, +37 += 4, 32 frames) then state `$15` (`$120b0`, landing) and `$16` (2 frames), then the normal AI. Observed (`out/t5v1`): state b f803..f834 (y reaches `$1ba` at the top of the arc), `$15` f835, `$16` f837, then 6/8/9/e as var 0. So var 1 is the "drops in from above / jumps in" version: invulnerable for 32 frames after spawning. Uses in script: level 3 trig `$300` x `$3b0` y `$1c0` (1x); level 4: six at x `$638` y `$290` (trig `$550,$570,$590,$5a0,$5b0` and `$800` x `$828`).
- Attacks (both): boxes `$13`..`$16` (12, 16, 20, 16 damage at dip column 0); AI table `py/ai_summary.py 05`: near (dx < `$30`): 6, e (`$11d98`), `$10`, `$11`, `$12`, `$13` according to the target's sub-state; mid: walk (7/e); far: walk. Hit score `$24952[05]` = 100, state 5 = 200, death 300 (read). Types 1, 4, 6, 8, `$14`: handler addresses only (ENEMIES1): `$010778`, `$011322`, `$0121a4`, `$012c5e`, `$0179ca`.

## 10. Flags, camera locks and level end (levels 3 and 4)

| event | `$80040` | `$80041` | `$80400` | measured |
|---|---|---|---|---|
| 0x1f spawn | bit 2 set | unchanged | bit 5 set | f801: `$80` -> `$84` |
| 0x1f death | bit 2 cleared | unchanged (bit 7 never set) | bit 5 cleared | `$84` -> `$80` at f1495; no bit 3, no bit 4 |
| 0x11 init | bit 2 | bit 7 set | | `out/e3` f801 `$84`/`$81` |
| 0x3a death | bit 2 -> bit 3 | bit 7 cleared | bit 5 cleared | f1818: `$88`/`$00`, bit 4 at f2083 (+265 frames), level 4 at f2185 |
| 0x12 init | bit 2 | bit 7 set | bit 5 set | f801 `$84`/`$81` (the lower bit 0 is the scene-card flag) |
| 0x12 death | bit 2 -> bit 3 | bit 7 cleared | bit 5 cleared | f4390: `$88`/`$00`, bit 4 at f4646 (+256), level 5 at f4748 |

`$80040` bit 4 (level cleared) is never set by a pool A handler of my types: it is the end-of-level object's counter at `$c83a/$c86a` (16 x 16 frames after bit 3) (*read* plus the two measured delays).
0x1e/0x0d, 0x0c and 0x1f set bit 2 / `$80400` bit 5 only; they never set `$80041` bit 7, so their deaths unlock the scroll but do not end the level.
Extra: `$80015` bit 3 (set by `$1a154` every frame once a 0x1e record exists) is the flag read by the level 4 camera rule at `$1980`.

## 11. Children and spawned types (role by body, address)

| type | handler | what | health | spawned by |
|---|---|---|---|---|
| 0x34 | `$1c410` | rider on a vehicle: copies the owner's `+31` as its state, facing, position (x by facing/variant table `$1c494`, y-8); state 4 -> spawns 0x1b and clears; no hit logic | 0 | 0x16 (var 0), 0x17 (var 1) |
| 0x33 | `$1c312` | rider of the motorbike, same structure (state 3/5 -> 0x1b) | 0 | 0x1d |
| 0x42, 0x43 | `$1f490`, `$1f7a6` | the two jaws of the claw (state follows the claw's `+18`) | 0 | 0x12 mode 0 |
| 0x45 | `$1fbe0` | tank driver | 5 | 0x19 |
| 0x46 | `$1fd16` | tank gunner, fires a pool B missile (-10) | 2 | 0x45 (`$1fbec`: D6 = `$46`, but `$18` when the level byte is 4; the 0x19 only appears in level 3) |
| 0x41 | `$1eda4` | sidekick that mimics 0x0d (command states `$10/$11`) | `$80` | 0x0d |
| 0x40 var 1/2 | `$1ec1c` | grunts delivered by the platform; hit 200, kill 400 each (3 events of +400 in `out/e3`) | 8 | 0x17 var `$22` |
| 0x3b..0x3e | see section 2 | grenades | 1 | 0x1f |
| 0x1b | `$194e2` | falling dead rider / debris (spawned by 0x34, 0x33; dynamic in level 3 at x `$4fc`, lead's note); not analysed | | |
| pool B 5/0, 5/1 | `$28d60` | explosion / drop effect spawned by the platforms, tank (x3 var 1), bike (var 0), 0x0d | | |
| pool B `$3a` | `$2aff6` | diagonal bullet (variants 3, 5: dx/dy from `$2b08c`), -1 on hit | | 0x16 |

## 12. Open items

- 0x16 hit/kill and score `$11` are *read* only (the bot's teleported punches at the bike's height registered 0 hits in 390 frames; hurtbox is +-32 x +-16 at state 1, `$6bb0c`).
- 0x1a damage to the player and its states 2/4 (cart destruction) not reached; 0x1a var 1/2 passenger pairs read only.
- 0x19 tank sub-states 5-8 (run-over, `$18f66`) read, not triggered live; the tank's own hit (health 3) never connected (the bot hit the children).
- 0x1d throw path (states 1/2) read only.
- Level 4 camera descent: see section 6 (my run did not need `$81e02 == 2`; the reason the camera followed is open).
- 0x0c/0x0d/0x11/0x3a attack-pattern frequencies from the chooser tables are read; only the sequences in the traces were run.
- 0x1e's 16 hits to morph were extrapolated from the poke at f1100 (9 hits seen unpoked).

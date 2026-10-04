# Black Tiger: mechanics (level data, hero, items, shop, collision, progression)

Runtime absolute addresses: COMMAND.PRG text at `$c470`, globals `$17000..$20000`, tables in the PRG data area. Every claim carries an
address and a proof (script and match count) or is labelled INFERRED. Scripts live in `py/mechanics/` (index in `py/mechanics/README.md`) and
start from `scratchpad/black_tiger/play_start.snap` (level 1 just started) unless stated. The enemy actor record, the spawn/activation window and the
AI step are in `ai.md` (sections 1 to 5); the boot chain, frame order, `trap #3` services and file roles are in `system.md`. "Map object" is the
10-byte record of table `$1fb60` (urns, coins, chests, doors, triggers); "actor" is the 16-byte record of table `$1f010` (hero at record 0, creatures after it).

## 1. Level files `0`..`7`

File `n` is the map of level `n+1`. The level index is `$17846` (0..7); `$cc8c` builds the file name from the digit string at `$175d0`
and loads it to `$201c8` with `trap #3` service 9. Layout (big-endian words):

    +0  width in tiles    -> $201c8       128 for levels 1,2,4..8; 64 for level 3
    +2  height in tiles   -> $201ca       50, 64, 160, 67, 64, 65, 64, 65
    +4  width*height words, row-major     -> $201cc (the loader's A5)
        word = (marker << 10) | tile id   (tile ids are 9 bits in practice, maximum $15f over all eight files)

| file | tiles | pixels | tileset (letter from `$175fb` = "00234567") |
|---|---|---|---|
| 0 | 128x50 | 2048x800 | T0 |
| 1 | 128x64 | 2048x1024 | T0 (the tileset reload at `$cce0` is skipped when the level index is 1) |
| 2 | 64x160 | 1024x2560 (a vertical tower) | T2 |
| 3 | 128x67 | 2048x1072 | T3 |
| 4 | 128x64 | 2048x1024 | T4 |
| 5 | 128x65 | 2048x1040 | T5 |
| 6 | 128x64 | 2048x1024 | T6 |
| 7 | 128x65 | 2048x1040 | T7 |

The world is a horizontal ring: `$ec7c` wraps x by `$1effe` (= width*16, set at `$ccb2`) and the camera does the same (`$ecca`); there are no x scroll limits.
The vertical camera is a baseline `$1eff0` rewritten only when the hero lands, grabs a ladder or falls below it; `camera_y = baseline - $78`
(`$ecca..$ed1e`), so jumps do not move the screen. `BT4` is overwritten by the map load at `$201cc` (system.md); nothing here reads it.

## 2. The marker scanner `$cd58` (map objects, actors, anchors)

Called once per level start (`$c562`). It walks every map word, strips the marker in place (`andi.w #$3ff,(A1)+`, so the live map has no markers) and builds:

| marker (word >> 10) | result | proof |
|---|---|---|
| 0 | nothing | |
| 1..`$27` | map object, table `$1fb60` (164 slots x 10 bytes): `+0` kind word = marker, `+2` x = col*16+8, `+4` y = row*16+16, `+6`,`+7` timers cleared (`+7` non-zero marks a dropped coin) | gate_loader 8/8 |
| `$28`..`$3c` | actor record, table from `$1f030` (pointer `$1ee96`, 16 bytes): `+0` type = marker-`$27`, `+1` = 6 (dormant), `+4` x, `+6` y as above, `+8` = `byte[$171f4 + type]`, `+12`,`+13` = 0; type `$d` is stored twice and `$f` three times (copy routine `$ceae`) | gate_loader 8/8 |
| `$3f` | anchor A at (col*16, row*16+16) -> `$1eff2/4`: the hero's start and respawn point (`$c850`); checkpoints rewrite it | |
| `$3e` | anchor B -> `$1eff6/8`: the bonus-room interior (door-in target) | |
| `$3d` | anchor C -> `$1effa/c`: the boss spawn point | |

`py/mechanics/gate_loader.py` pokes each original level file over `$201c8` (the live map has no markers left), runs `callcap $cd58` and compares the
changed-byte set with `levelmap.scan`: **8/8 levels byte-identical** (81, 679, 723, 678, 609, 631, 670, 735 bytes). The marker census per level is `census.py`;
the positions of the special objects (chests, shop man, old men, doors, checkpoints, exits) are `py/mechanics/special_items.txt`. A second, independent transcription
of the scanner and the urn burst is in `ai.md` sections 2 and 6 (`gate_spawn` 9/9, `gate_urn` 96/96); they agree with the table above.

Per level (`census.py`): exactly one exit (kind `$20`), 2 to 10 chests, 27 to 38 urns (kind 1), a door-in/door-out pair on levels 1 to 6 only, and 1, 1, 3, 3, 3, 3, 3, 4 shop men (kind `$11`).

## 3. Collision: the tile class table

`$00ec7c(D2 = x, D3 = y) -> D1.b = class, D0.w = tile word` (`player_model.tile_class`):

    x wrapped into 0..width*16 by $1effe
    word  = word[$201cc + 2 * ((y >> 4) * width + (x >> 4))]
    class = byte[$25fcc + (word & $3ff)]        ; $25fcc = tileset file base $25f8c + $40

The class table is bytes `$40..$23f` of the tileset file (512 entries, one per 9-bit tile id; the bytes from `$240` are tile graphics, `$1efe0 = $25f8c + $240`, `$f1b8`;
the first `$40` bytes are palettes). Classes, from their consumers (feet-class jump table `$d8c8`, `$d89c`, `$d838`):

| class | meaning | consumer |
|---|---|---|
| 0 | air | falls through to the vertical step |
| 1 | solid | landing (`$d958`), head bump (`$d838` zeroes the rise counter), air side-block (`$d8e4`) |
| 2 | climbable (rope, chain or ladder) | `$d89c` -> `$d9a4`: grab, x snapped to the cell centre (`& $fff0 | 8`) |
| 3 | kills the hero | feet in class 3: `$d990` calls `$d44a` |

Level 1 class census: 4820 air, 1477 solid, 75 climbable, 28 killing; per-level counts are printed by `collision_maps.py`. Independent proof of the
level-to-tileset mapping: at all 8 anchors A the head and chest cells are class 0 and the feet cell class 1 (**8/8**). `img/mechanics/levels_collision.png`
draws the eight maps (grey solid, green climbable, red killing; cyan, orange, magenta outlines = map object, actor, anchor markers). Class 3 forms the lava floor of
level 7, the pits of level 5 and short strips under platforms in levels 1, 2 and 4; levels 3 and 8 have none.

`BTCLIPS` and `BTOBJ` are picture banks, not collision data: `BTCLIPS` (`$1efe4`, loaded at `$f1da`) is the HUD, shop and bonus-screen picture bank drawn by
`$f2a4(index, x, y, flag)` through `trap #3` service 8; `BTOBJ` (`$1efe8`, read at `$d514`) is the map-object picture bank indexed by kind.

## 4. State block and HUD

    $1f000 w  hero ground mode: 0 ground, 1 ladder, 2/3 airborne
    $1f002 w  money (zenny), 200 at a new game                    $1f004 w keys        $1f006 w armour (hits absorbed)
    $1f008 w  potions         $1f00a w weapon level 0..4 (HUD shows +1)       $1f00c w lives (5)      $1f00e w vitality cells
    $1eec0 w  continue credits (3)     $1eebc l score     $1783c l high score
    $1f010..  hero actor record: +0 type $ff (0 = dead), +1 state, +2 animation frame, +3 facing (1 = left), +4 x, +6 y (feet), +9 cooldown,
              +14 ($1f01e) rest state
    $1eeb2 w  invulnerability ticks     $1eedc w TIME in 50 Hz ticks     $17844 w ticks per second (50)     $17846 w level index
    $17820 w  poison flag    $17822 w reverse-controls flag    $17824 w screen-clear ticks    $1eeb8 w boss-fight flag

HUD slots (x column in the draw calls `$ffbe`, `$100f6`, `$1008e`, `$10026`): key 6, weapon 15, armour 22, potion 30; lives `$fe60`, money `$feb2`, time
`$ff1a` (`$1eedc / $17844` as m:ss), vitality bar `$10160` (`$1f00e` cells of tile `$1c` from x = 10 step 2).

`$1f01e` (actor record `+14`) is the state the hero returns to when a one-shot animation (attack, hit) ends: `$e50e` copies `14(A3)` to `1(A3)`. `$d7b0` rewrites it every
tick, 0 when the feet stand on solid ground (`$d964`) and 2 on a ladder (`$d9b0`); live: the state sequence after a fire press on the ground is `$0a` then `0`.
`$17824` is the screen-clear timer of map object kind `$10` (section 8); `$1eeb8` is the boss-fight flag (section 13).

Starting values: `$c4c4` (new game, continue): lives 5, credits 3, money 200, keys 0, weapon 0, potions 0, score 0. `$c850` (every level start and every life): hero to anchor A,
`$1f010 = $ff`, **TIME = 180 s** (`$b4 * 50` ticks), **armour 2**, **vitality 3** (+1 on levels 2 to 8, +1 more on level 8: 3,4,4,4,4,4,4,5; `$c8c2..$c8e6`).
Bought armour therefore does not survive a death or the next level; weapon, keys, potions and money do.

## 5. Input decode `$f358`

Joystick 1 arrives through the IKBD joystick vector `$a624` (joy0 byte `$c2fc`, joy1 byte `$c2fd`); `trap #3` service 12 (`$b0d2`) returns the word. `$f358`, once per tick
(low byte = joystick 1, bit 0 up, 1 down, 2 left, 3 right, 7 fire):

    $1eed2 l = long[$17670 + 4*(b & 15)]           dx.w:dy.w in {-1,0,1} (left+right and up+down combinations are junk entries)
    $1eece w = 1 if left set, 0 if only right set (sticky when neither); xor 1 while $17822 (reverse controls); $1eecf is its low byte = facing (1 = left)
    $1eed6 b = (b & $83) | 4 if left or right | 8 if fire         bit 7 = fire
    $1eed0 w = byte[$176ac + (b' & 15)]            action: 0 idle, 1 up, 2 up+move, 3 move, 4 down+move, 5 down

With `$1783a != 0` the byte comes from the 512-byte recorded stream at `$1784e` (index `$1784c`): the attract demo (`$eac6` sets the flag; the stream is initialised PRG
data; `ai.md` section 8). The keyboard (BIOS service 10) is read only at the continue prompt, the disk prompt and name entry; no dependence on ACIA data-register retention
exists in the paths exercised here (a plain `kbd 15` / `kbd 95` answered the continue prompt, `kbd 39` / `kbd b9` the disk prompt).

## 6. Hero movement

### 6.1 Vertical step `$d7b0` (jump, fall, ladder, landing, state byte)

Transcribed in `py/mechanics/player_model.py::step_vertical`. **`gate_vertical.py`: 1180/1180 random states byte-identical to `callcap $d7b0`** (seeds 7, 11, 23, 400 cases
each; ground modes, counters, actions, fire bits, level-1 map) and 20/20 class-3 states where the emulator clears the alive flag.

    rise:  while $17830 != 0: y -= byte[$176f2 + $17830]; $17830 -= 1        table $176f2 = 0,1,2,4,7,11,15,15
    fall:  when $17830 == 0 and not on a ladder: y += byte[$176f2 + $17832]; $17832 += 1 while bit 3 is clear   (terminal speed 15 px per tick)
    jump start (state-table byte bit 7): $17832 = 0, $17830 = 6   (4 from a ladder)
    head cell class 1: rise stops, $17832 = 4;   feet cell class 1: land, y &= $fff0, $17832 = 3, $1eff0 := y
    air dx $1782e = +-8 px per tick when the jump started with up+move (state 5), or when "move" is pressed while rising with dx = 0 (the rise counter gains one tick: a one-tick hover)

Live (`jump_trace.py`, one tick = the `$e544` / `$e61c` write pair): a straight jump gives dy = -15,-11,-7,-4,-2,-1 (apex 40 px; the first fall step adds 0 in the tick of the last rise step),
then +1,+2,+4,+7,+11,+15, 12 ticks in all, **equal to the table sequence**; up+right moves x by +8 on all 12 ticks; up, release, right three ticks later gives one extra hover tick
(-7,-7) and then +8 per tick. Ground walking is +8 px per tick (x = `$c0`,`$c8`,...,`$f0`); the per-tick dx comes from the hero's animation data (`$1eec8`), so it is measured, not derived.
A tick is 60,000 emulator steps when idle (5 VBL of 12,000) and 66,000 to 89,000 while walking; TIME runs per VBL (section 12).

State byte `$1f011` (set at `$daa2` from `byte[$176bc..]` selected by ground mode and action; bit 7 of the table byte starts a jump):

    ground (ptr $176bc): idle 0, up $84 (jump, state 4), up+move $85 (jump, state 5), move 1, down+move 8, down 8
    ladder (ptr $176c2): idle 2, up 6, up+move $85 (jump off), move 2, down+move 2, down 7
    air    (ptr $176c8): 3 for every action
    fire (bit 7): byte[$176ce + mode] = $0a ground, $0c ladder, $0d air; on the ground with a down action (>= 4) state $0b (crouching attack)

### 6.2 Weapon, knives, reach

* Melee/weapon hit on an actor `$e930`: `hp -= 2*weaponLevel + 1` (1,3,5,7,9 for `$1f00a` = 0..4) on the actor's hp byte (`+8`); a negative result sets hp 0 and state 4 (dying), exactly 0 stays alive until the
  next hit. **`gate_weapon.py`: 25/25** (5 weapon levels x 5 hp values, state byte included). Reach `$1781e` x 16 px in front of the hero (`$e8be`: 4 units, 5 above weapon level 0), set on the swing's animation frame 1.
* Thrown knives: `$d6b6` has three cooldown counters `$17834/36/38` (10 ticks each); each free counter lets one volley of three projectiles through `$10838` (live: 9 calls in 400k steps of held fire = 3 volleys x 3).
  Spawn height `byte[$17702 + hero state]`: 15 px, 11 px when ducking (states 8, `$b`). No volley while poisoned (`$d6b6` returns when `$17820 != 0`). Knife records and their flight: `ai.md` section 1.
* Map objects that are hit by the hero's attack: `$e9f2` (same reach test, used by urns).

## 7. Damage, vitality, death

* Contact `$e016` (actor within 16 px in x and 24 px in y, not state 7, `$1eeb2 == 0`): sets `$1eeb2 = $14` (20 ticks, decremented once per tick at `$e1ae`; live: `$14,$13,...,0`), then actor type 7 or `$10` poisons
  (`$e144`: `$17820 = 1`; a potion in stock is used up instead and the poison cleared); otherwise **armour first** (`$1f006 -= 1`; reaching 0 plays the four shield-break effects and sound 3), and only with armour 0
  **vitality** (`$e0b6`): `tst.w $1f00e; beq $e138` (a hit at vitality 0 does nothing), `subq.w #1,$1f00e; bne $e138` and **only the decrement that lands on 0 calls `$d44a` (death)**.
  Enemy shots (`$110e0`, `$11136..$1115c`) apply the same armour, then vitality, rule and the same `$1eeb2`.
  Live (`drive_vitality0.py`, armour 0, an actor poked onto the hero, 3M steps): start vitality 3 -> dies after the third hit, 2 -> dies, 1 -> dies at the first hit, **0 -> never dies** (lives stay 5, alive flag `$ff`).
  `$1f00e` is tested for a decision only at `$e0b6` and `$11140` (both inside a hit); `$10160` draws it and the other writers (`$c8c2..$c8e6`, `$d3ea`, `$fde2`) set or increment it. Vitality 0 is not reachable in play (every decrement to 0 is a death); it is
  reachable only by a poke, which is why a poked 0 leaves the hero immortal. This settles the conflict between "vitality 0 kills" (first mechanics report, wrong) and the poke result in `system.md`.
* Armour 2 -> 1 -> 0 and vitality 3 -> 2 -> 1 observed with an actor of type 3 poked on the hero, hits 20 ticks apart.
* Death `$d44a` (spawns the death effects, clears `$1f010`) is called from: vitality reaching 0, a class-3 feet tile (`$d990`), TIME below 0 (`$cc26`, tested every tick). The main loop (`$c574..$c5de`) then
  decrements lives; at lives 0 with credits left it takes a credit and shows "Continue ? Y / N :" (`$17566`); Y (`$c612..$c628`) gives lives 5, **clears the score** (`$c61a`) and replays the same level; N, or no credits
  (`$c632`), goes to game over and the high-score entry (`$10386`). Live: lives 1 + `$1eedc` negative -> prompt, credits 3 -> 2, `kbd 15` -> lives 5, score `$1234` -> 0, money kept (`img/mechanics/continue_prompt.png`).
  There is no extra-life rule: `$1f00c` is written only at `$c4f2`, `$c620` and `$c5d8`.
* Kill score `$e4a4`: `score += word[$1775c + 2*type]` for actor types 1..`$13` = 100,200,200,0,(1000),100,100,500,500,2000,1000,100,100,50,100,1000,10000,10000,200. **`killscore_check.py`: 18/19**; the
  19th, type 5, is excluded by `cmpi.b #5,(A3)` at `$e488` (it is never killed). Kill drops: a dying actor leaves a map object of kind `byte[$1771c + type]` (coins; 0 = none) with timers `6(A0) = 9`,
  `7(A0) = $41` (a dropped coin gives no pick-up score): types 1,6,7,8 -> kind 6 (50 zenny), 2 -> 3 (1), 3,4,`$10` -> 5 (10), 9,10,12 -> 8 (500), 11 -> 9 (1000), `$11` -> 7 (100), others none, suppressed
  while `$1eeb8` is set (`$e4bc`). **`killdrop_check.py`: 18/18.**

## 8. Map objects (kinds 1..`$27`)

`$ceec` dispatches by kind through the 33 longs at `$cf20` (kinds 0..2 -> `$d404` nothing, 3..15 -> `$d2b4`, 16 -> `$d16c`, 17..22 -> `$d194`, 23..26 -> `$d2b4` (class code 0: nothing), 27 `$d05c`, 28 `$d0d0`,
29 `$d12e`, 30 `$d218`, 31 `$d27e`, 32 `$cfa4`). `$d2b4` indexes `byte[$177bd + kind]` into the class table at `$d2de`. `pickup_check.py` pokes one object of each kind at the hero's feet and diffs the HUD
fields against a no-object control run:

| kind | what | measured effect |
|---|---|---|
| 1 | urn (27..38 per level) | breaks on a melee hit (`$e9f2`) or after two knife hits (kind 1 -> 2 -> 3, `$10a10`); contents in section 9 |
| 2 | urn with one hit left | no map places it |
| 3..9 | coins | zenny +1, +5, +10, +50, +100, +500, +1000 (`word[$177de + 2*kind]`), score +50 once (not for dropped coins), sound 7 |
| `$a` | treasure chest | needs a key (`$d38c`); contents in section 9 |
| `$b` | opened chest | inert |
| `$c` | chest content | vitality +1, becomes `$b` |
| `$d` | chest content | zenny +50, becomes `$b` |
| `$e` | key | keys +1 |
| `$f` | hourglass | TIME +1500 ticks (30 s) |
| `$10` | screen clear | sets `$17824 = 2`, sound 5; while it is non-zero (decremented per tick at `$d4b8`) every actor in the window is forced to state 4 (`$e34e`) and scored. Live: two type-3 actors at the hero went to state 4 and the score rose (600) with kind `$10`, nothing without |
| `$11` | shop man | `$d1f8` -> `$ea7c` -> shop screen (section 10) |
| `$12`..`$16` | old men | `$fca6(kind - $12)` (section 10) |
| `$17`..`$1a` | no handler | no map places them |
| `$1b` | door in (invisible, within 8 px) | hero to anchor B inside the same level, "WELCOME TO DUNGEON" (`$1732b`), `$17842 |= 2`, palette B; the record is consumed (live: x +80, y -480 on level 1; `secrets.md`) |
| `$1c` | door out (invisible, within 8 px) | hero to anchor A (the last checkpoint), `$17842 &= 1`, palette A restored |
| `$1d` | spawns a type-6 hostile shot at the top of the camera (`$10e0c`) | INFERRED: fire column trap |
| `$1e` | periodic hostile shot aimed at the hero while within 64 x 16 px | INFERRED: rock trap |
| `$1f` | checkpoint | hero within 32 px in x and 0..80 px above the marker: anchor A := marker |
| `$20` | level exit | section 13 |
| `$21`..`$27` | no handler | |

## 9. Urns, chests, kill drops

**Urns** (`$d4ae`, `$d5ea..$d60c`): on the break `seed = lcg(seed)`, `idx = seed mod (4*level + 16)`, `v = byte[$17784 + idx]`; `v < $80`: the slot becomes map object kind `v` (0 = nothing); `v >= $80`:
an actor of type `v & $7f` spawns instead (three for type `$f`): "containers that hold either treasures or villains". Table `$17784` (49 bytes): `00 05 05 05 05 0f 0f 8f | 07 0e 0e 0e 04 04 8f 04 | 07 86 07 86 05 05 05 91 | 91 07 07 81 81 07 81 06 |
06 86 07 07 86 06 06 06 | 06 06 07 07 07 07 07 07 | 07`; a deeper level widens the range, so it holds more 100/50 zenny coins and more villains (types 6, 1, `$11`, `$f`). **`gate_urn.py`: 160/160**
(callcap of `$d4ae` with an urn in front of the hero, 120 seeds on level 1, 40 on level 8, spawned actor types included). RNG `$cb6a` -> `$fe1c(n)`: `seed' = lo16(lo16(s*s)*$c2 + s*$6eb + $3619)` at `$3195c`, result
`seed' mod n`; **`gate_rng.py` 300/300**.

**Chests** (`$d38c`, kind `$a`): with no key nothing happens. With a key: keys -1, the chest is cleared, an effect of kind `6 + rnd(3)` is spawned by `$10b28` at the chest (`$d39e..$d3c0`; effect table `$31612`, handler
table `$10bf0`), and when its animation reaches frame 3 (kind 8: frame 4) it creates a map object (`$d490` allocates the slot, `$10ce6` places it at the chest, y + 16):

| effect kind | handler | creates | outcome |
|---|---|---|---|
| 6 | `$10cc0` | kind `$b` (empty open chest) | plus four fire-column shots from `$d40a` (`$10e0c` kind 3), which cost an armour point when the hero stands on the chest |
| 7 | `$10d02` | kind `$c` | vitality +1 |
| 8 | `$10d26` | kind `$d` | zenny +50 |

**`chest_check.py`: 30/30** seeds (kind from the lcg model; keys 1 -> 0; zenny +50 for kind 8, vitality +1 for kind 7, armour 2 -> 1 for kind 6; every chest ends as kind `$b`). The manual's "hourglass, a lantern
or gold, some contain fire columns" maps to: the hourglass is the separate map object `$f` (urn drops and map markers), the gold and the fire columns are chest outcomes, and the vitality item `$c` is INFERRED to be the manual's lantern. Kinds `$c` and `$d` exist
only as chest contents (no map marker).

## 10. Shop and old men

The shop man (kind `$11`) is entered through `$d194` -> `$d1f8` -> `$ea7c` -> `$f690`: a 5 x 2 grid (columns x = 6,11,16,21,26 in units of 8 px from `$17ab2`, rows y = `$76`, `$96` from `$17ac8`), price strings from text pointers 0 and 1,
"EXIT" (text 2) at the right. `$f44a` reads the stick: it waits for fire to be released, then polls every 7 VBL, so a short press can be lost (hold fire 100,000 steps and repeat). Purchase `$00fa9c(i)`, price words at `$17a8e`:

| i | price | effect |
|---|---|---|
| 0..3 | 100, 1000, 2400, 9600 | weapon level := i+1 only if higher than the current level, otherwise nothing is charged |
| 4 | 15 | keys +1 |
| 5..8 | 80, 300, 800, 1600 | armour := (i-4)*2 (2, 4, 6, 8 hits) only if higher than the current value, otherwise free no-op |
| 9 | 150 | potion: clears poison if poisoned, else potions +1 |

Not enough money: "Sorry, you don't have enough Zenny for that item." (text 10). **`gate_shop.py`: 200/200** random inventories against callcap of `$fa9c` (stack argument poked at `$1ee50`; the inventory words are
compared; 84 of the 200 calls returned within the cap, the others waited in the dialog after the effect was applied). **Real interaction** (`drive_shop.py`, `img/mechanics/shop_refusal_live.png`,
`shop_scene_live.png`): money poked to 5000, hero poked onto the shop man of level 1 (1256,224); entry at `$f690` after 1.44M steps; fire on item 0 -> money 5000 -> 4900, weapon 0 -> 1; item 2 (2400) -> money 2500, weapon 3 (HUD
shows 4); item 3 (9600) -> refusal text, no change. The shop timer is `$17844*20` ticks (20 s, `$f77c`).

Old men (kinds `$12`..`$16`, `$fca6(kind - $12)`, jump table `$17b06` = `$fcea,$fd28,$fd6a,$fd28,$fdb2`): +100 zenny (texts 4, 5); +30 s (texts 4, 6; `$17844*30` ticks); advice (texts 11, 12: the Spinning Skull cannot be destroyed;
text 13 is the other tip); +30 s again; "Please accept this potion of Vitality" (text 14, `$1f00e += 1`). Text table `$17a4e` (16 pointers): 0/1 price rows, 2 EXIT, 3 "Maybe I can sell you something....", 4 "Thank you, I am in debt to you!",
5 "Please accept some Zenny coins.", 6 "Please accept more time.", 7/8 HUD blanks, 9 "GOOD LUCK!", 10 refusal, 11 "Here is some advice", 12 "Spinning Skull can't be destroyed", 13 "To increase your earnings seek hidden symbols",
14 "Please accept this potion of Vitality", 15 "Bonus Zenny".

## 11. Score and money tables

| table | address | content |
|---|---|---|
| kill score by actor type | `$1775c` (words) | section 7 |
| kill drop by actor type | `$1771c` (bytes) | section 7 |
| coin value by kind | `$177de` (words) | 0,0,0,1,5,10,50,100,500,1000 |
| shop prices | `$17a8e` (words) | section 10 |
| level-clear bonus | `$17aa2 + 2*level` (words) | 300, 500, 800, 1200, 1600, 2400, 4800, 0 |
| urn contents | `$17784` | section 9 |
| initial actor byte `+8` | `$171f4` | per type (hit points; bosses get `(level+1)*16` at spawn, `$d040`) |

`$1025c(level)` adds the level-clear bonus to money and prints "Bonus Zenny" (`img/mechanics/level_clear_bonus_prompt.png`). **`gate_bonus.py`: 8/8** (callcap, stack argument at `$1ee50`).

## 12. TIME

`$1eedc` is a signed word in 50 Hz VBL ticks: the VBL handler `$a53a` runs `addq/addq/subq/addq` on the four words at `$1eed8` (pointer `$bb76`, installed by service 13), so the timer at `+4` falls by one per VBL, not per game
tick (live: `$2196,$2195,...` once per 12,000 steps). It is set to 9000 (3:00) at every life and level start; kind `$f` and two old men add 1500; below 0 `$cc26` calls `$d44a`.

## 13. Level exit, boss, level clear, next level

* Exit (map object kind `$20`, one per level, handler `$cfa4`): hero within 32 px in x and y, `$1eeb8 == 0`. It sets `$1eeb8 = 1` (boss fight), clears all 179 actor records from `$1f020`, optionally loads the boss bank
  (letter at `+2` of `$17226 + 4*level`, 'a' = `bta`, 'b' = `btb`, trap #3 service 9) and spawns `count` copies of actor type `+1` at anchor C through `$d678`, with hp `(level+1)*16`. Table `$17226` (count, type, letter):
  level 1 2 x type 1; 2 4 x type 1; 3 1 x `$12` (`bta`); 4 1 x `$c`; 5 1 x `$13` (`btb`); 6 `$12` (`bta`); 7 `$13` (`btb`); 8 `$12` (`bta`). While `$1eeb8` is set: ambient spawns stop (`$c972`), kill drops stop (`$e4bc`),
  and `$ca48` fires hostile shots from the boss (`ai.md` section 5).
* Clear: `$c642` tests `$1eeb8 != 0 && $1f020 == 0` (boss slot empty), then fades, `$1025c` pays the bonus and, after level 1 only (`$c688`), `$cb2c('B')` draws "Please insert Disk  B" and blocks on a key (`$ec74`, service 15,
  GEMDOS Crawcin). `$17846 = (level+1) & 7`, back to `$c50e`; a restart that begins at another level than 1 asks for disk 'A' with the same routine (`$c4ac..$c4be`); after level 8 the game wraps to level 1.
* **Live** (`drive_exit.py`, labelled pokes: hero to the exit cell (1864,304), both boss records to state 4 / animation `$30`, one key press): exit flag 1 and a boss of type 1 with hp 16 at (2032,304) (anchor C); kills pay
  100 each; money 200 -> 500 (the level-1 bonus 300) with the disk prompt on screen (`img/mechanics/level_clear_bonus_prompt.png`); after `kbd 39` / `kbd b9`: level index 1, map 128x64 (file `1`), hero at (160,944) = level 2 anchor A.
  The boss was killed by the state poke, not by weapon hits; the clear logic after the kill is the code's own.

## 14. Ambient hazards `$c972`

Level flags `byte[$177b5 + level]` = 00 01 01 11 10 10 11 00. Low nibble (`$17842`, OR 2 inside a bonus room): 2.1% per tick an actor of type 2 near the hero while it is idle or walking. High nibble (`$17840`, levels 4..7): 0.8% per tick an actor
of type 9 (75%) or 10 (25%) (`ai.md` section 5, gate 800/800, identifies 9 and 10 as the two Grim Reaper Hags; they are the ambient flyers, not "birds"). `$17822` (reverse controls) is the blue frost column effect, INFERRED from the manual.

## 15. Copy-protection residue

`$f52e` is `moveq #0,D0; rts` (the crack); the original body behind it (`$f532..$f5a0`) drives the WD1772 (`$8604`/`$8606`) and compares a track read with `$1784`; it is dead. Its only call site is the demo start `$eafc`, which stores the result
in `$f68e`; `$c506` returns to the title when it is non-zero. With the crack the check always passes (`system.md` section 10).

## 16. Corrections to earlier statements

* `BTCLIPS` is not collision; there is no collision file (class byte per tile, section 3). File `2` is 64 tiles wide.
* The first mechanics report listed "vitality 0" as a death source; the code kills only on the decrement that reaches 0 (section 7).
* The ambient high-nibble spawns are the Hags (types 9/10), not birds. The chest does not drop an hourglass (section 9).
* The `$cf20` table dispatches map-object kinds, not creatures; kind `$20` is the level exit (`$cfa4`), kinds 0..2 do nothing.

## 17. Open items

* The names "fire column trap" (`$1d`) and "rock trap" (`$1e`) are INFERRED from the hostile-shot kinds they spawn; the manual's lantern for kind `$c` is INFERRED.
* Ground-walking dx and the animation tables `$1eec2..$1eec8` (graphics/AI).
* Free fall past the last map row reads outside the map (not modelled; the gates stay inside it).
* What the HUD `$17842 |= 2` bonus-room state changes besides the rock rate.

## 18. Not exercised

A boss killed by weapon hits (the state poke was used), the ending after level 8, the old-men dialogs on screen (the effect tables were read from code, the type-`$11` shop was driven), the name-entry screen, a
real second-disk prompt answer on a physical disk change, the ladder grab with a live ladder (covered by the callcap gate only), poison and reverse controls from the real actors, and any level above 2 for the movement
measurements.

## Files

| path | what |
|---|---|
| `py/mechanics/README.md` | every script, expected output and runtime |
| `img/mechanics/levels_collision.png` | the eight collision/marker maps |
| `img/mechanics/shop_scene_live.png`, `shop_refusal_live.png` | the shop scene as entered live; the refusal after item 3 with 2500 zenny |
| `img/mechanics/level_clear_bonus_prompt.png` | bonus screen with the disk-B prompt after a level clear |
| `img/mechanics/continue_prompt.png` | the continue prompt |

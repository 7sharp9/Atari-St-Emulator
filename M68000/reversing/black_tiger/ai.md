# Black Tiger: enemies, bosses, spawner and the attract-demo player

Scope: the actor table and its AI, the three shot tables, the spawner, bosses, drops, the demo stream.
The map/marker/object-record layout and the item kinds are in `mechanics.md`; frame banks and pixel
formats are in `graphics.md`; the boot/state machine and trap #3 services are in `system.md`. Addresses
are runtime absolute (COMMAND.PRG text, static listing `bt_c470.asm`). "Gate" = a Python transcription in
`py/ai/btai.py` diffed byte-for-byte against `callcap` from a snapshot with labelled pokes (the
transcription never sees the callcap output); counts are in section 13, scripts in `py/ai/README.md`.
Anything not marked gate / live / code-read is INFERRED.

## 1. Object tables

| table | base | records | role | update loop |
|---|---|---|---|---|
| actors | `$1f010` (record 0 = the HERO, type `$ff`); enemies from `$1f020`; 180 x 16 bytes | hero, creatures, bosses | `$e19e` (update + draw) |
| map objects | `$1fb60`, 164 x 10 | urns, pickups, doors, exit, shop man | `$d4ae`, kind dispatch `$ceec` through the 33-long table `$cf20` (`mechanics.md`) |
| H shots | `$31592`, 9 x 14 | the hero's thrown weapons | `$10894`; spawn `$10838`, free slot `$1087a` |
| E effects | `$31612`, 30 x 14 | sparks, debris, boss fireballs (13 types, table `$10bf0`) | `$10b84`; spawn `$10b28`, free slot `$10b6a` |
| P shots | `$317b8`, 30 x 14 (ends at the RNG seed `$3195c`) | hostile projectiles and columns (9 types, table `$10f0c`) | `$10e94`; spawn `$10e0c`, free slot `$10e56` |

Actor record (16 bytes; fields confirmed by `$cd58`, `$d678`, `$e19e` and the gated AI): `+0` type (0 free),
`+1` state, `+2` animation frame, `+3` facing (0 hero to the right / actor faces right, 1 left; `$dab0`),
`+4` x.w, `+6` y.w (feet), `+8` hit points, `+9` stun / cooldown (decremented every frame at `$e1c4`; the
AI is skipped while non-zero), `+12` deferred state, `+13` deferred cooldown or the flyers' heading nibble
(bit3 right, bit2 left, bit1 down, bit0 up), `+14` state to fall back to after a non-looping animation
(`$e50e`). States, from the AI and the death code: 0 idle, 1 walk, 2 hop / turn, 3 attack, 4 dying, 5 falling
(the bank entry has dy = 16), 6 dormant (spawn state), 7 waking, 8 second attack (type `$11` only). Each
state is an animation entry of the bank (`graphics.md`): frame count, dx, dy per frame, width code, event
frame (byte 6; `$e7e2` runs when the frame counter equals it, via `cmp.b 6(A0,D1.w),D0` at `$e452`).
The three shot tables share a 14-byte record: `+0` word type (low byte), `$8000` free, `$2000` flipped, `$40`
skip one frame (`bclr #6`); `+2` x, `+4` y, `+6` vx, `+8` vy, `+10` age, `+12` timer: positive = life
countdown, then re-armed from `$18608` (E/H) or `$1116c` (P) by type; negative = sound id (`$f51e`).

## 2. Spawn at level load, `$cd58` (gate 9/9)

The scan of the whole map is specified in `mechanics.md` (map word = `(code<<10)|tile`; marker codes
`$3f/$3e/$3d`; map objects `$01..$27`). The actor half: code `$28..$3c` creates an actor of type
`code-$27` (types 1..21) at x*16+8, y*16+16 in the next free record from `$1f030`, state 6, hit points from
`$171f4[type]`; type `$d` is written twice and `$f` three times at the same coordinates (`$ceae` copies the
record). The code bits are stripped from the map in place. The actor table is not cleared by `$cd58`; the
caller clears `$1f010..$1fb5f` first (`$f422`, from `$c53a`). Gate `py/ai/gate_spawn.py`: each of the eight
level files poked over `$201c8`, `callcap cd58`: changed-byte sets equal in 9/9 states (the live, already
stripped level as negative control). Independent cross-check: file `0` gives the 36 actor records of the
live `play_start.snap` exactly (types `3:12 6:2 7:1 13:6 15:12 16:3`). Census of all levels:
`py/ai/census.py` (spawn_census.txt): e.g. file 1 has 61 actor records, file 2 (64x160) 48.

## 3. Activation, despawn, no respawn (gate 160/160)

`$e19e` visits every record each frame; a record is updated and drawn only when
`0 <= (x - scrollx [+ level width if negative]) + $40 <= $1a0` and `0 <= y - scrolly <= $c8` (signed word
compares, `$e1e6..$e220`; `$1efec/$1efee` scroll, `$1effe` level width in pixels; x wraps, so every level is
a horizontal cylinder and `$ec7c` wraps x the same way). Outside the window nothing runs for the record; if
it is also not in state 6/7 and of type 2, `$d` or `$f` it is deleted (`$e224..$e252`). Nothing re-creates
map actors inside a level. Gate `py/ai/gate_window.py`: all other actors cleared, one type 3 in state 0 on
and around the window edges (including the two wrap cases), `callcap e19e`; "the AI wrote `$1eeae`" matched
the prediction in 160/160 states (49 inside, 111 outside).

## 4. The AI step `$dbde` (gate 2500/2500)

Called from `$e34a` for every in-window actor. Skipped when `+9 != 0`, when the hero is dead
(`$1f010 == 0`) or when the state is not 0 or 6. If `+12 != 0` the deferred state is applied (`+1 := +12`,
`+9 := +13`, both cleared). Otherwise dispatch on `type-1` through `$dc46`:

| types | handler | behaviour |
|---|---|---|
| 1, 14 | `$dc92` | wake check `$db84`; 69 %: turn to a random side, state 2; 31 %: floor probe, then engage |
| 2, 3, 4, 19 | `$dcd6` | floor probe `$db50` (no solid tile under the feet: state 5), then engage |
| 5 | `$dce4` | engage (sine wobble in `$e26a`) |
| 6 | `$dce8` | wake check; hero within the bank's reach: aimed shot `$df12`, state 3, state 1 after 8..15 frames |
| 7, 8 | `$ddb8` | dormant: wake check; awake: engage |
| 9, 10, 11 | `$de2e` | no AI (animation script only) |
| 12, 13, 18 | `$de04`/`$ddd4` | dormant: wake check and also wake the NEXT record (`+17 := 7`, `+19 := 1`); awake: random heading `$dfbc`, then engage; the heading selects a velocity from `$17670` in `$e2d0` |
| 15, 17 | `$dd7c` | wake check, floor probe, 80 % engage / 20 % state 2 |
| 16 | `$dd46` | stationary: state 3 if the hero is to its left, 1 when within reach |

Wake check `$db84`: a state-6 actor wakes (state 7) when |hero.x - x| <= `$40` (type `$d` also needs
|hero.y - y| <= `$40`). Engage `$de32`: with the bank's reach `10(bank)` and engage offset `12(bank)` (bank =
`$1eea2` pointer table, record `type-1`): far -> state 1; inside the band -> state 3 (type `$11` rolls 50 %
for state 8); a middle band hops (state 2, `+9 := 6`) when x/16 > 3; finally `$dab0` turns toward the hero.
The RNG `$fe1c` is `seed' = lo16(lo16(seed^2)*$c2 + seed*$6eb + $3619)`, result `seed' mod n`
(wrapper `$cb6a`; seed `$3195c`). The 2500-state corpus (`gate_dbde.py`) draws type 1..19, hero and actor
positions over the whole level width, each type's own reach thresholds, random seeds, states and cooldowns;
memory delta, D0 and A3 matched in all of them, every instrumented branch was hit (cooldown 268, db50
stand 104 / fall 311, wake 127, far-x 227, dc92 turn 51, fire 42, dd46 near 12, dd7c state 2 14, sibling
wake 25, de32 far 156 / middle 83 / hop 42, attack 100, type-17 state 8 3, deferred state 115).

## 5. Type table (live tables; bank offsets from the BTSPR long table; sprite crops `img/ai/actor_types.png`)

`py/ai/type_table.py` reads `$171f4` (hit points), `$1775c` (score, words), `$1771c` (drop pickup kind) and
`$dc46` from `play_start.snap` and the BTSPR table; types 18 and 19 have no BTSPR bank (table entries are 0)
because their bank is BTA / BTB loaded over BTSPR at the boss trigger.

| type | bank (BTSPR+) | H | AI | hp | score | drop | levels (file:count) | name |
|---|---|---|---|---|---|---|---|---|
| 1 | `$50` | 27 | dc92 | 5 | 100 | 6 | 3:5 7:1 | Block Head (stone face; boss of files 0 and 1) |
| 2 | `$602` | 32 | dcd6 | 0 | 200 | 3 | ambient only (`$c972`) | Skeleton (rises from the ground: state 7 has 5 frames) |
| 3 | `$20a8` | 32 | dcd6 | 3 | 200 | 5 | files 0..7: 12/11/6/7/3/8/2/7 | Blue Goblin (axe, shield; attack overlay) |
| 4 | `$20a8` (alias) | 32 | dcd6 | 3 | 0 | 5 | 2:1 | goblin variant |
| 5 | `$3ea0` | 32 | dce4 | 100 | 1000 | 0 | 2:4 3:2 4:4 5:4 6:1 7:8 | Spinning Skull (hp 100) |
| 6 | `$4f38` | 32 | dce8 | 5 | 100 | 6 | all levels (2..9) | Fire Demon (stationary, aimed fireballs) |
| 7 | `$65d6` | 32 | ddb8 | 5 | 100 | 6 | all levels (1..7) | Audrey III (contact sets the poison flag) |
| 8 | `$65d6` (alias) | 32 | ddb8 | 5 | 500 | 6 | 3:1 | Audrey II (no poison) |
| 9 | `$8080` | 32 | none | 5 | 500 | 8 | ambient (`$c972`) | Grim Reaper Hag, red fire columns (P type 3) |
| 10 | `$8080` (alias) | 32 | none | 5 | 2000 | 8 | ambient | Grim Reaper Hag, blue frost columns (P type 7: reverses the joystick) |
| 11 | `$8080` (alias) | 32 | none | 10 | 1000 | 9 | none | third hag variant, no event attack |
| 12 | `$8f48` | 32 | de04 | 10 | 100 | 8 | 4:5 5:4 6:7 7:4 | Spear Throwing Demon (horned flyer, aimed shot; boss of file 3) |
| 13 | `$adf6` | 16 | ddd4 | 0 | 100 | 0 | pairs (4..12 per level) | Bird / bat (touch kills it and hurts the hero) |
| 14 | `$b21c` | 27 | dc92 | 5 | 50 | 0 | none | Block Head variant |
| 15 | `$bb20` | 16 | dd7c | 0 | 100 | 0 | triples (3..27 per level) | Vile Vial (small blue blob) |
| 16 | `$c3d2` | 32 | dd46 | 3 | 1000 | 5 | 0:3 1:3 2:2 3:1 5:2 7:8 | stationary coil, poison on contact (name not established) |
| 17 | `$dd1a` | 32 | dd7c | 4 | 10000 | 7 | 1:4 2:6 3:3 4:12 6:9 | Fire Mummy (spits a horizontal fire shot, P type 4) |
| 18 | BTA | 64 | de04 | 16*(L+1) | 10000 | 0 | boss, files 2, 5, 7 | dragon boss |
| 19 | BTB | 64 | dcd6 | 16*(L+1) | 200 | 0 | boss, files 4, 6 | scimitar demon boss |

Names are matched against `BTIGER.DOC` and the sprite crops. Strongest matches (a code effect the manual
also states): types 9/10 = the two Grim Reaper Hags (red fire columns, blue frost columns that reverse
left/right, `$f3c6`), both spawned out of the air by `$c972`; type 2 = Skeleton ("appears out of the ground":
spawned by `$c972` in the 5-frame wake state and the crop is a skeleton); type 5 = Spinning Skull ("can't be
killed": hp 100); types 7/16 = poisonous plants / poison (`$e144`); type 8 shares type 7's bank without the
poison (Audrey II); type 17 = Fire Mummy (spits fire, mummy crop); type 6 = Fire Demon ("doesn't move, throws
fireballs"). Weaker (sprite and behaviour only): 3/4 Blue Goblin, 12 Spear Throwing Demon, 13 Birds, 15 Vile
Vials, 1/14 Block Head. Types 4, 11, 16 have no creature name assigned (types 1, 4 and 8 do occur in level maps, files 3/7, 2 and 3, and all have `$dc46` handlers). The score of type 17 (10000) and of the hags is
as read from `$1775c`; I did not check what unit `$1eebc` counts in. The crops use the level-1 palette, so
colours of creatures that live in other levels are approximate.

Image index: `img/ai/actor_types.png` (2x crops, first frame of state 0 and of state 3 for every BTSPR type 1..17; level-1 palette) is the visual proof of the name column.

## 6. Attacks and the P / E shots

Event-frame attacks `$e7e2` (gate 600/600, `gate_events.py`, types 9, 10, `$c`, `$11`, `$12`, `$13` plus 3 and
5 as nulls): type `$11` spits a horizontal P type 4 (`+$40` px in front when facing left, state 8 shoots 5
lower); types 9 and 10 call `$d40a`: four P shots (type 3 / type 7) around hero.x +- 32, lifetimes 5, 10, 15,
20, stepping `+-$20` px (this staggered growth is the column); types `$c` and `$13` fire one aimed shot
(`$df12`); type `$12` fires two aimed shots with a +-2 px/frame spread (`$df26`), goes to state 1 and sets
the stun `+9 := 8`. Aimed shots: velocity `(dx,dy) / (sqrt((dx^2+dy^2)>>7) + 1)` (`$db1c` Newton loop starting at
8, `$df74`), about 11 px per frame toward the hero, spawned 16 px above the actor (gated through the 42
`dce8_fire` states of the AI corpus and the `$e7e2` corpus).

P shot types (`$10f0c`, code-read, not gated): 0 `$10f66` aimed shot (bank `$111aa`; destroyed into type 1 when
a hero shot overlaps), 1 `$10fe0` explosion (28 frames, `$1138a`), 2 `$10ffc` (8 frames, `$1241a`), 3 `$11034`
fire column (10, `$130da`), 4 `$11018` horizontal shot (10, `$13b9e`), 5 `$10f4a` (15, `$159f2`), 6 `$10f30`
static (`$15dca`), 7 `$11050` frost column (10, `$16612`; a hit toggles `$17822`, which flips the left/right
joystick read at `$f3c6..$f3d0`), 8 `$1107e` (`$1117e`). Contact `$110e0`: |hero.x - x| < frame width*8 + 8,
|hero.y - 16 - y| < 16, `$1eeb2 == 0`. E types (`$10bf0`) and H types (`$1091a`) are code-read only.

## 7. Damage, death, score, drops, urns

- Actor hit by a hero shot (`$e6b0` -> `$10a10` rectangle overlap against the live H shots; the shot is
  consumed and an E type 1 spark spawns): `+8 -= 1`; the actor dies (state 4) when the byte goes negative, i.e.
  after `hp+1` hits. Hit points in section 5; the first boss record gets `16*(level+1)` (`$d040`), its escorts
  the table value.
- Death (state-4 animation ends, `$e47e..$e508`): `$1eebc += $1775c[type]`, the record is cleared and
  `$1771c[type]` (section 5) is dropped as a map-object pickup (`$d490` takes a free `$1fb60` slot;
  `+6 := 9`, `+7 := $41`) unless `$1eeb8` (boss fight) is set. Code-read.
- Contact damage `$e016`: |hero.x - x| <= `$10`, |hero.y - y| <= `$18`, state not 7, `$1eeb2 == 0`: `$1eeb2 :=
  $14` (20 frames of invulnerability), then `$1f006` (armour) is decremented if non-zero, otherwise `$1f00e`
  (3 at start) and the hero dies at 0 (`$d44a`). Types 7 and `$10` also set `$17820` (poison; `$d6b6`
  throws nothing while set; `$1f008` antidotes clear it); type `$d` goes to state 4 on contact. Code-read;
  `mechanics.md` owns the vitality / death question.
- Urns (gate 96/96, `gate_urn.py`): map kinds 1 (intact) and 2 (cracked) are containers (`$d4ae`); touch or a
  shot increments the kind and at 3 they burst (four E type 3 debris, record cleared) and roll
  `b = $17784[rng(level*4+16)]`: `b < $80` -> the record becomes pickup kind `b` (0 = empty), `b >= $80` ->
  villains of type `b & $7f` appear at the urn (three for type `$f`). Observed outcomes over 8 levels x 12
  seeds: items 5, 4, 14, 0, 7, 15, 6; villains 15 (x3), 6, 17, 1. Later levels draw from a longer prefix of
  the table, hence more villain entries. The same burst is gated independently in `mechanics.md`.

## 8. Ambient spawners (gate 800/800)

`$c972` (frame list entry `$c948`; skipped while `$1eeb8` is set): `$17840` (high nibble of `$177b5[level]`)
enables the flyers: 0.8 %/frame (`rng(1000) <= 7`) a type 9 (75 %) or 10 (25 %) at hero.x +- 40, hero.y - 40 -
rng(50), state 7, `+12 := 3`. `$17842` (low nibble) enables type 2: 2.1 %/frame, only while the hero action
byte `$1f011` is 0 or 1, at hero.x + rng(`$118`) - `$8c`, hero.y, state 7. Latent bug (reproduced by the gate's
full-table states): when the table is full `$d65a` leaves A6 unchanged and the caller still writes `+1`/`+12`
through the stale A6. `$ca48`: while `$1eeb8` is set and record `$1f020` (the boss slot) is a type >= `$12`,
1.1 %/frame it spawns an E type `$c` shot at the boss (`vx = +-15` toward the hero). `gate_amb.py` 800 states,
800/800 (spawned: type 9 x77, 2 x28, 10 x16 over the run; 81 `$ca48` states spawning).

## 9. Bosses (live snapshots; gates: section 4 and `$e7e2` / `$ca48`)

Trigger and spawn. Touching the level-exit object (kind `$20`, hero within 32 px, `$cfa4`; `system.md`) sets
`$1eeb8`, clears the actors, loads the boss bank (BTA / BTB letter from `$17226[level*4 + 2]`) and creates the
boss group at `$1f020`: `count` records of type `type` from `$17226[level*4 + {0,1}]` at the marker `$1effa/c`,
each next record 16 px higher; the first record gets `hp = 16*(level+1)`. Measured on `drive_boss.py`
snapshots (run from the lvl snapshots with a labelled hero + camera poke onto the exit cell): hit points
16, 32, 48, 64, 80, 96, 112, 128 for level index 0..7, the boss at the marker (2032,304), (1120,240),
(976,224), (1120,256), (1472,272), (1952,256), (1888,240), (1936,384), escorts (hp 5) of file 0/1 at 16 px
steps above. A teleport without moving the camera lets the rule `y >= scrolly+$21` (`$e7b4..$e7c0`) push the
boss to the old camera, hence the camera poke.

Behaviour (60,000-step samples, 70 frames per boss, hero kept alive by re-poking `$1f006/$1f00e`; tables
`$BT_WORK/agents/ai/boss/watch<N>.txt`): every boss is the ordinary AI step plus event attack, not a scripted phase
machine; "phases" are only the state cycle.
- Files 0 and 1, type 1 (Block Head x2, x4): dormant until the hero is within `$40` px, then the hop cycle
  state 2 (8 frames, dx 8 px, y arc from `$176e9` = -16 -12 -6 -2 0 2 6 12), short walks (state 1), idle; the
  copies run out of phase and wrap around x. No projectiles; contact damage only.
- File 3, type 12 (Spear Throwing Demon): wakes (6 -> 7), then cycles walk / attack: state 3 (5 frames, event
  frame 2) fires one aimed P type 0 every 8 frames, drifting in x and bobbing in y (`$e2d0` heading).
- Files 2, 5, 7, type 18 (BTA dragon): flies (heading from `$dfbc`), state 3 attack fires two aimed P type 0
  shots with spread (`$df26`) and sets the 8-frame stun; additionally E type `$c` fireballs at 1.1 %/frame
  (`$ca48`); y follows the hero but never above `scrolly+$41`.
- Files 4, 6, type 19 (BTB demon): stands (floor probe, `$dcd6`), walks to ~48 px from the hero then repeats
  state 3 every ~7 frames, one aimed P type 0 per cycle (up to 7 shots alive); P type 1 = the shot exploding.
Not exercised: killing a boss, the level-clear sequence, the boss HP bar (`$101b0`, called with `hp>>4`).

## 10. The attract-demo player is a recorded joystick stream (live check)

`$eac6` (demo loop: `$1f002 := $c8`, `$1f006 := 2`, `$1784c := 0`, `$1783a := 1`, load level file `0`, run
`$c900` frames until FIRE (`$ebbe`..`$ebc8`), until `$1784c == $200` or the hero dies, then restart). `$f358`
replaces the joystick byte read by trap #3 function `$c` with `$1784e[$1784c++]` when `$1783a != 0`: 512 bytes,
one per frame, standard layout (bit0 up, 1 down, 2 left, 3 right, 7 fire). From `$f358`: `$1eed2 =
$17670[dir]`, `$1eed6` (bit7 fire, bit2 horizontal move, bit3 fire pressed, bits 0-1 up/down), `$1eece`
(facing), `$1eed0 = $176ac[bits]`. Live check: from `tl/t25.snap` over 600,000 steps `hits` gives 6 calls of
`$f358` and `$c900` and `$1784c` goes `$46 -> $4c`. The 512 bytes are static data in COMMAND.PRG (file offset
`$b626`; `agents/ai/demo_stream.bin`); 211 zeros, `$08`/`$80` bursts, `$0a`/`$8a`, `$04`, `$01`/`$09`; 35
bytes are `$20`, a bit nothing reads (idle). It is a replay: no code reads the enemies.

## 11. Per-frame order `$c900` (call counts from a 50-frame event log)

`$cb6a(D0=$80)` (advance the RNG), `$ecca` camera (writes `$1efec/$1efee` from the hero), `$f358` input, `$ed26`
background draw, `$e168` poison flicker, `$d7b0` hero vertical motion, `$d6b6` hero shot spawner, `$e19e`
ACTOR LOOP, `$d4ae` map objects, `$10e94` P, `$10894` H, `$10b84` E, `$ff1a`, `$feb2`, `$10160` HUD counters,
`$cc26` death check, `$cb78` score line, `$c972` ambient spawner, `$ca48` boss fire, then trap #3 D0 = 1
(frame sync) and the deferred sound id `$17848`. About 60,000 steps per frame in the level, 100,000 in the
demo.

## 12. Latent bugs and oddities

- `$c972` writes through a stale A6 when the actor table is full (section 8).
- `$e7e2` / `$df12` save and restore D0..D4 with `movem.w`, which sign-extends the restored words; nothing
  downstream reads the upper words (the gates compare memory and D0 only).
- `$e224`: despawn applies to types 2, `$d`, `$f` only; other creatures simply freeze outside the window.

## 13. Gates (all re-run from `py/ai/` with fresh callcaps)

| gate | result |
|---|---|
| `gate_dbde.py 2500 11` (`$dbde`) | 2500 / 2500 |
| `gate_spawn.py` (`$cd58`, 8 level files + live) | 9 / 9 |
| `gate_amb.py 800 5` (`$c972`, `$ca48`) | 800 / 800 |
| `gate_window.py 2` (activation window, `$e19e`) | 160 / 160 |
| `gate_urn.py 12` (`$d4ae` drop roll) | 96 / 96 |
| `gate_events.py 600 4` (`$e7e2`, `$d40a`, `$df26`) | 600 / 600 |

## 14. Open items, not exercised

- The P / E / H shot update handlers (`$10e94`, `$10b84`, `$10894`) and the animation engine inside `$e19e`
  (draw, hit-box overlays, state transitions at animation end) are code-read, not gated; they call the
  sprite blitter, which a pure-memory gate would have to stub.
- Boss death, the level-clear sequence and boss HP bar; the boss names by level are INFERRED from the manual's
  order (Block Head, Blue Dragons, Spear Throwing Demons, Blue Samurai Dragons, Red Dragons, Gold Samurai
  Dragons, Black Dragons) against files 0/1 = type 1, 2 = BTA, 3 = type 12, 4 = BTB, 5 = BTA, 6 = BTB, 7 = BTA.
- Names of types 4, 11 and 16; the unit of the score counter; the exact start timing of each hop (the
  hero-relative turn in `$dab0` caps at 400 px).
- `py/ai/boss_watch.py` and `drive_boss.py` use labelled pokes (hero position, camera, armour / hits) and were
  run only on the eight lvl snapshots; no controllable hero fought any boss.

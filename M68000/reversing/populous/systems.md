# Populous (Atari ST): trail effects, key checks, pause, save games, sound

All addresses are runtime absolute (TEXT at $ad58). Scripts are in `py/systems/` (data and
snapshots in `$POP_WORK/systems/`); each result names the script that reproduces its count.

## 1. Trail effects (entity slots $d1/$d2)

Two special entities, slots $d1 and $d2 (`$3c46e`, `$3c484`), cross the map one cell every 8 frames
and mark the cells beside their path. They are drawn as 32x32 sprites (graphics.md: entity >= $d1,
frame = +6). The SPR_320 frames of the three types show a wizard trailing bubbles (type 0, trees,
frames 0-4), a slime monster (type 1, swamp, 5-8) and a grey rock monster (type 2, rock, 9-12)
(identified by eye from the sprite sheet, not from a rendered game frame). Their triggers make
them a sudden-death device: one spawns at frame $1000 of every game, and a swamp monster once when
the entity table is full (208), killing everything on the cells it marks.

### 1.1 Records

The trail reuses the entity record with its own meaning for some fields:

| off | trail meaning |
|---|---|
| +0 b | 2 |
| +2 b | upper frame bound (table +4) |
| +3 b | lower frame bound (table +2) |
| +4 w | 1 while alive, 0 = free (the spawn only takes a slot whose +4 is exactly 0) |
| +6 w | sprite frame, starts at the lower bound, +21 added every frame |
| +8 w | cell |
| +10 w | step offset (table +0; re-read if 0) |
| +12 w | frame counter 0..8; a step is taken when it passes 7 |
| +20 b | type (index into the table, signed) |
| +21 b | frame delta, 1 at spawn, negated at either bound |

Step table `trail_type_table` `$21e7c`, 12 bytes per type (DATA):

| type | +0 step | +2 lower | +4 upper | +6, +8, +10 side offsets | marks | travels |
|---|---|---|---|---|---|---|
| 0 | -64 (north) | 0 | 4 | 0, -1, +1 | trees: feature `$3c522` = $32+i unless class is 0 (water) or $10 | from the south edge |
| 1 | -65 (north-west) | 5 | 8 | 0, -64, -1 | swamp: class `$36e78` = $35 when it is $0f/$1f/$20/$42 | from the south or east edge |
| 2 | +65 (south-east) | 9 | 12 | 0, +64, +1 | rock: class = $2f+i unless 0 or $10, plus a minimap dot `$166b2(c, $21ea0[class])` | from the north or west edge |

i is the side-offset index 0..2, so offset 0 (the cell just entered) gets $32 / $2f and the two
flanking cells $33,$34 / $30,$31. The rock path writes the class byte directly: no `$c0ee` refresh
and no check for a building on the cell.

### 1.2 Per frame, `trail_effects_tick` `$12f84` (from `$b7c2`, skipped while paused)

```
for slot in $d1, $d2:  e = entity[slot]; if e.str == 0: continue
    e.t12 += 1
    e.frame += e.delta
    if e.frame >= e.upper or e.frame <= e.lower: e.delta = -e.delta      ; unsigned compares
    if e.t12 <= 7: continue
    e.t12 = 0
    if occ[e.cell] == slot+1: occ[e.cell] = 0
    if e.step == 0: e.step = table[e.type].step
    if cell_step_check(e.cell, e.step) == 1: e.str = 0; continue       ; off the map: gone, occupancy stays clear
    e.cell += e.step
    for i in 0..2:
        so = table[e.type].side[i]
        if cell_step_check(e.cell, so) == 1: continue                  ; off the map / across the x edge
        c = e.cell + so;  mark c by type (table above)
        if occ[c]: entity_kill(entity[occ[c]-1], occ[c]-1)            ; $10068: any entity, either side
    occ[e.cell] = slot+1
```

`cell_step_check` `$18198(cell, off)` returns 0 for off = 0; 1 when cell+off leaves 0..$fff or the
x coordinate leaves 0..63 (the low 6 bits of off, sign-extended from 4..63, are dx); 2 when the target
class is $2f; 3 when it is water (0); else 0. Only the value 1 matters here, so a trail crosses water
and rock.

### 1.3 Spawn, `spawn_trail_effect` `$13372(type, edge)`

```
if type > 2 (signed): return
for slot in $d1, $d2: if entity[slot].str != 0: continue
    str = 1; flags = 2
    edge 0: cell = (rand()%125 >> 1) + $fc0                   ; south row y=63, x 0..62
    edge 1: rand()&1 ? cell = (20 + rand()%43)*64 + 63        ; east column x=63, y 20..62
                     : cell = (20 + rand()%43)*64 + $fc0      ; 5312..7999: off the map (bug, see below)
    edge 2: rand()&1 ? cell = (rand()%43)*64 : cell = rand()%43   ; west column / north row
    other edge: cell unchanged (the slot's previous cell)
    occ[cell] = slot+1
    step = table.step; upper = table.upper; lower = table.lower; delta = 1; frame = lower; type
    (the +12 counter is not reset)
    key check C (section 2)
    return                                                    ; only one slot per call
```

Both callers push only the type word, so `edge` is whatever the caller has in the next stack word:

- `$b8e8` (main loop, after `$db4c`): when the frame counter `$3c4c8` equals $1000,
  `$13372($37ec2 & 3)`. The word above the argument is the high word of the D7 that `$b510` saved
  on entry, 0 in the run below. So the tick spawn always enters on the south edge. Type 0 (trees,
  north) and type 1 (swamp, north-west) then cross the map; **type 2 (rock, south-east) steps off the
  map on its first move and dies after 8 frames without marking anything**, and type 3 spawns
  nothing. GENESIS has `$37ec2` = $6302, type 2.
- `$e89c` (in `$db4c`, the walker-emission scan): when the scan finds no free slot below $d0 and
  `$3c4c4` is 0, `$13372(1)` once and `$3c4c4` = 1 (reset only at a new game, `$bc50`). The edge is the
  uninitialised local -146(A6) of `$db4c` (*inferred*: not run; needs 208 live entities).

The edge-1 south branch computes `(20+r)*64 + $fc0` where `(20+r) + $fc0` was evidently meant; the
cell is 5312..7999, so `occ[cell]` writes into the walker visit-count map `$38fd8`, and the first
step fails `cell_step_check` (cell+step >= $1000). Code-read; reached only through the stack-garbage
edge.

### 1.4 Proof

- `py/systems/trail_diff.py 400`: callcap on a randomized corpus from `spawn.snap`, full memory delta over
  $ad58..$3d550 against `trail_ref.py`. **$12f84 400/400** (355 steps, 34 deaths off the map, 612
  cells re-marked, 423 victims killed, walkers incl. fighting ones and the query entity; settlements
  and leaders on marked cells are excluded because `$10366`/`$129d6` are not modelled). **$13372
  400/400** (types -1..3, edges 0..3 and garbage, full/partial/free slots, key pass and fail: 222
  spawns, 94 of them with the penalty, incl. the write through the uninitialised local).
- `py/systems/trailrun.py`: natural run `late4.snap` -> frame $1000 (`spawn.snap`, 335M steps): the spawn
  from `$b8f4` with type 2, edge 0 lands at cell $fcd (x 13, y 63) and matches the model (17182
  bytes compared); the next 30 frames match every byte of the captured regions (**30/30**); the
  trail lives 8 frames and dies on its first step, marking nothing.
- `py/systems/trailrun.py 220 0` / `200 1` (POKED: the pushed type word set to 0 / 1 at the same breakpoint,
  edge still 0): spawn MATCH, then **195/195** frames for type 0 (24 steps north, 48 cells given
  trees, 1 entity killed) and **169/169** for type 1 (14 steps north-west, dies at the west edge; its
  path held no flat cells, so no swamp was made: the swamp marking is proven by the corpus only).
  Both runs end when the computer wipes out the idle human side (population 0 at frame 4291 / 4264,
  score screen), which `trailrun.py` detects and stops at.

## 2. The key checks ("checksums")

None of the three is a checksum over code or data. All three compare a stored key with a constant
built from a DATA long, and all three constants equal **$54ac0842**, the immediate the crack's loader
writes into the two Supexec routines `$16014` and `$17a1c` (README: "remnants of the original
trace-mode protection"). Each routine is `move.l #imm,D0; move.l D0,$24`: it points the trace vector
at the key and returns it.

| check | where | condition | on mismatch |
|---|---|---|---|
| A | `$db4c` at entity index 20 (`$e182`) | `$3c4c0 == $21d4c + $14725836` ($4039b00c) | `$3d524` = 1 (armageddon), both god_rec ctrl = 1 |
| B | `$db4c` at entity index 18 (`$edae`) | `super_peek_long($24)` (`$15fe2`: Supexec read of the trace vector) `== 2 * $21d54` ($2a560421) | both ctrl = 1, `$3d524` = 1 |
| C | `$13372` after a spawn | `$3c4b4 == $21d58 + $12312378` ($427ae4ca) | ctrl of both sides = 1, word 1 written through the uninitialised local -14(A6), `$3c4c8` -= 1 |

The key: `$16004` (called once from `main`, `$af40`) stores the returned value in `$3c4c0`; each new
game copies it to `$3c4b4` (`$be12`); `$14b72` calls the second routine `$17a0c` and stores the result
in `$3c4b0`, which nothing reads. Check B reads the trace vector itself, so it also fails if anything
else rewrites `$24`.

With the crack all three pass: every anchor snapshot holds $54ac0842 in `$3c4c0`, `$3c4b4`, `$3c4b0`
and `$24`, and `py/systems/protect.py` over 20 frames of `late4` (58 entities) executes A and B 23 times each
with 0 failures. Forced (`py/systems/protect.py`): poking `$3c4c0` = 0 or `$24` = 0 into `late4` gives
armageddon 1 and ctrl 1/1 within 2 frames; poking `$3c4b4` = 0 at the tick spawn gives ctrl 1/1,
frame $fff, and the next frame spawns the second slot and fails again (both slots live, frame 4097
after 3 frames). "ctrl = 1 on both sides" is ATARI VS ATARI: the player's own side is handed to the
computer. The penalty for C costs one frame of counter per spawn; it cannot repeat once both slots
are used. Check C's stray write lands wherever the stack word holds a pointer: in `spawn.snap` it is
$0003bb52, the flags/side word of entity 103.

Anchors: GENESIS reaches frame $1000 at 335M steps after `late4` (`spawn.snap`).

## 3. `$3b274` is PAUSE

`$1f428` (cmd 14/6, the top-right pause icon) toggles `$3b274` and redraws the icon (`$16b26`). While it
is set, the main loop skips `$12f84` and `$db4c` (`$b7b2`: the `$b7e2` loop only replots the minimap
dots), `$119e6` (land input) returns at once, and the powers, the magnet (`$129da`) and the knight
refuse. Tutorial mode (`$37ebc` = 3) starts paused (`$1c7de`); `$19f82` clears it at a new game; the
two-player message box `$19504` toggles it (*inferred* for the last).

`py/systems/pause.py`: click the pause icon on `game_start`, run 40 frames: counter, all 211 entity records
and both side records unchanged in **40/40** frames; a second click clears it and the counter runs
(288 -> 293..298).

## 4. Power-word bits 1 and 2

god_rec +14 bit 1 = ATTACK TOWNS, bit 2 = ATTACK LEADER (the OPTIONS FOR EVIL items 2 and 3, ai.md
section 2). Census of reads of +14 with a mask: bit 1 only at `$1421a` and bit 2 only at `$1416c`,
both in `ai_think` `$13eda`; bit 0 (MODIFY LAND) at `$1362c` (`$135fc`) and `$1387e` (`$13816`); bit 4
at `$c98a` (swamp arming), bit 7 at `$11fc0` (flood); the score screen loops over all bits
(`$1cca2`/`$1ccd8`). They only matter for a computer-controlled side. Their behaviour is already
covered by `py/ai_diff.py` (4800/4800), which randomizes the whole mask.

## 5. Save games

### 5.1 Format (`save_game` `$1db98`, `load_game` `$1e146`)

The file name gets ".GAM" appended unless it ends in it. Fcreate, then one Fwrite per field; every
write's count is checked and the first short one aborts (Fclose, return 1, "ERROR IN SAVING").

| off | bytes | source |
|---|---|---|
| 0 | 4 | magic $ffffb615 |
| 4 | 8450 | heights `$34be4` |
| 8454 | 4096 | cell altitude `$33be4` |
| 12550 | 4096 | terrain class `$36e78` |
| 16646 | 4096 | feature `$3c522` |
| 20742 | 4096 | occupancy `$37fd4` |
| 24838 | 32 | side records `$3b226` |
| 24870 | 4642 | entity records `$3b278` (211 x $16) |
| 29512 | 46 + 46 | god_rec 0, 1 |
| 29604 | 2 each | `$21d50`, seed `$3d52e`, `$37ec2`, human side `$3affe`, landscape `$3b246`, armageddon `$3d524`, frame `$3c4c8` |
| 29618 | 10 | level record `$22ad8` |
| 29628 | 2, 2, 4, 2, 2, 4 | `$21d5e`, paint mode `$3b276`, battles won `$3c514`, options `$219b2`, `$3c51a`, score `$36cea` |
| 29644 | 2 | checksum: 16-bit sum of the words of heights, altitude, class, feature, occupancy, plus the low word of pop0+pop1; also kept in `$3d52c` |

Total 29646 bytes. `load_game` checks the magic, then Freads the same list **without checking any
count**, loads the landscape (`$14be8`), recounts the entity high-water mark, rebuilds knight
targets (`$fe00`) and redraws. It does not verify the checksum; `$3d52c` is only packed into the
two-player setup record at `$1a1b8` (*inferred*: a link consistency value).

### 5.2 LOLO1.GAM

LOLO1.GAM is this format cut off after 1786 bytes of the terrain class: magic, heights, altitude
(4095/4096 equal to `$c0ee` applied to its heights; the odd cell, 535, is rock ($2f), whose
altitude `$c0ee` derives differently, and `lolo.py` runs it with an empty class map), and the first 1786 class bytes (1364 equal to the derived
shape, 380 flat cells claimed $1f/$20, 42 rock). `py/systems/lolo.py`.

It is a failed save on this disk, reproduced: `py/systems/savegame.py` saves over LOLO1 from `game_start`
(GAME SETUP -> SAVE A GAME -> LOLO1 -> SAVE). TOS 1.00's Fwrite returns 4, 8450, 4096, then **1786**
of 4096, the game prints ERROR IN SAVING, and the file is 14336 bytes: the size of LOLO1.GAM. The
disk is full: with LOLO1.GAM's 14 clusters released GEMDOS writes exactly 14, and the two free
clusters 391/392 at the end of the disk are not used (observed on both the original image and
`pop_auto.st`; why GEMDOS leaves them is not investigated). The directory entry is dated 1985-11-20,
the TOS 1.00 default date, i.e. written on a machine with no clock set, unlike the 1986 dates of the
game files.

Loading it (`py/systems/loadgame.py`: GAME SETUP -> LOAD A GAME -> LOLO1 -> LOAD, stopped at the return
of `$1e146`): Fread returns $6fa for the class and 0 for every later field; RAM holds **14332/14332**
bytes from the file, and **15308/15310** bytes of the fields past its end are unchanged (the two
others are god_rec 0 +0/+2, the cmd 14/8 of the menu itself, cleared by `$1e712`). So loading
LOLO1.GAM keeps the current game's entities, features, occupancy, the rest of the class map and all
settings, on LOLO1's heights: a hybrid, not an older format.

## 6. Sound: GMUSIC1, GWORDS and the sample player

There is no music. GMUSIC1 is a bank of 12 sampled sound effects; `$21ffc` (the note icon right of the land view, graphics.md "Mouse input") has no reader besides its toggle and the
save/restore around the deity screen (`$1d18e`/`$1d5c8`).

### 6.1 File format (`load_sound_bank` `$afd8(name)`)

`[w n][n x 10-byte records -> $37ec4][l L][L bytes -> $249b0]`; each record's +6 is then relocated
by adding `$249b0`. Record: +0 b priority, +1 b repeat count, +2 w rate (Hz), +4 w length (bytes),
+6 l offset. Samples are unsigned 8-bit.

| k | request `$36d02` | set by | prio | rep | rate | len |
|---|---|---|---|---|---|---|
| 0 | $42 | `$e9ba` walker dies in a swamp | $40 | 0 | 5473 | 4682 |
| 1, 2 | $43/$44 | `$df0c` ($43 + `$3b222`), when `$37e78` & 8 (same sample, two rates) | $40 | 0 | 4804 / 5204 | 1500 |
| 3 | $45 | `$12d1a` (knight) | $40 | 0 | 5013 | 4192 |
| 4 | $46 | `$df2a` when `$37e78` & $80 | $13 | 0 | 7457 | 12976 |
| 5, 6 | $47/$48 | *not found as literals* | $40 | 0 | 10000 | 1334 |
| 7 | $49 | `$12df2` (armageddon) | $40 | 0 | 1063 | 2528 |
| 8 | $4a | `$12006`.. (flood) | $36 | 0 | 5013 | 12470 |
| 9 | $4b | `$126f8` (volcano), `$129ca` | $33 | 0 | 2100 | 5928 |
| 10 | $4c | `$12400` (earthquake) | $33 | 5 | 10026 | 6890 |
| 11 | $4d | `$111fa` (papal magnet, cmd 5) | $14 | 0 | 3760 | 8456 |

`$37e78` is not decoded.

GWORDS uses the same header (10 records, the speech words of the deity screen) but `$afd8` skips the
data read for a name whose second letter is 'w'; instead, when `$21ffe` is set, it reads 12 tracks
(40..51, side 1, sectors 1-10) with Floprd into `$249b0 + i*$1400`. `$21ffe` is set by `$b2ac` when
side 1's boot sector starts with $39, i.e. the digitised speech lives raw on side 1 of the original
double-sided disk. The deity screen (`$1d0e6`, which loads GWORDS at `$1d1ce` and GMUSIC1 back at
`$1d5aa`) plays the words through `$16f14` only when `$21ffe` is set. The single-sided crack has
no side 1: `$21ffe` = 0 in every anchor, so there is no speech.

### 6.2 Player

- Request: game code writes `$36d02` = $42+k; the VBL handler `$16d32` (when `sfx_enable` `$21920`
  is set) takes it, clears it, and calls `$16f30` if k < 12. `$16f14(k)` is the direct call (deity
  screen), `$16f24` returns non-zero while idle.
- `$16f40` (Supexec): a request plays only if its priority >= the current one (`$24953`). It
  stores the repeat count (`$24952`), then `$16f80`: stop a running sample, reset the YM
  (`$1703a`: mixer all tone/noise off, channel volumes 12/11/9), and program MFP Timer A: prescaler
  /4 with data $94700/rate when rate >= $950, else /10 with data $3b600/rate (so about the nominal
  rate: 5473 -> 5535 Hz); vector `$134` = `$17140`, IERA/IMRA bit 5 on.
- ISR `$17140`: one sample per interrupt. The byte indexes an 8-byte entry of the 256-entry table
  `$171ba`, `08 vA 09 vB 0a vC 00 00`, written with `movep.l D1,$ff8800` + `movep.w D2,$ff8800`: the
  three YM channel volumes that approximate the sample level. At the end it restarts while repeats
  remain, else `$170dc` disables Timer A, restores the volumes and clears the playing/priority
  bytes.

`py/systems/sfx.py`: each of the 12 sounds, requested through `$36d02` on `game_start`, runs the ISR
exactly length x (repeat+1) times with one start and one stop: **12/12** (e.g. the earthquake:
41340 = 6890 x 6).

The emulator does not reproduce the rates: its Timer A ignores TACR/TADR and fires 64 times per
frame (`Program.fs` `timerAPeriod`, a documented stub), so every sound plays at about 3200 Hz
(measured over the start-to-stop VBL count for all 12). The rates above come from the code.


## 7. Open

- The pop-208 spawn `$e89c` was not run (needs 208 live entities); its edge is `$db4c`'s
  uninitialised local -146(A6).
- Why TOS 1.00 GEMDOS leaves clusters 391/392 unused.
- `$36d02` requests $47/$48 (sounds 5, 6) and the `$37e78` bits behind sounds 1, 2, 4.
- `$3d52c` in the two-player setup record `$1a1b8`: the serial handshake was not run.
- The emulator's Timer A stub (64 per frame): sample playback speed is wrong in the emulator.

## 8. Scripts and snapshots

| script | what |
|---|---|
| `trail_ref.py` | model of `$12f84`, `$13372`, `$18198`, `$10068` (walkers) |
| `trail_diff.py [N] [seed]` | callcap corpus, 400/400 + 400/400 |
| `trailrun.py [frames] [type]` | live spawn + per-frame diff from `spawn.snap` |
| `protect.py` | key checks, natural and forced |
| `pause.py` | pause, 40/40 |
| `lolo.py`, `fat12.py` | save layout vs LOLO1.GAM; FAT12 lister |
| `loadgame.py`, `savegame.py` | LOAD / SAVE through the UI |
| `sfx.py [--no-timing]` | GMUSIC1 decode, ISR sample counts 12/12, the emulator's playback rate |

Snapshots: `tick.snap` (late4 + 260M steps, frame $e78), `spawn.snap` (frame $1000, at `$13372`
entry from `$b8f4`), `pause_on.snap`, `setup.snap` (GAME SETUP menu), `loaddlg.snap` / `loadsel.snap`
(LOAD GAME dialog, LOLO1 selected), `loaded_ret.snap` (after `load_game` returns), `sdlg0..2.snap`,
`saved.snap` (ERROR IN SAVING).

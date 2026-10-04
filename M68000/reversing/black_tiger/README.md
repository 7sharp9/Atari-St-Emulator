# Black Tiger (Capcom 1989, US Gold; Atari ST conversion by Clipper Computer Products)

Side-scrolling fantasy platformer: a barbarian with a flail/knives, eight levels each ending in a boss,
zenny, a shop, keys, chests, urns, armour and potions. Hand-written 68000 assembly (20 LINK frames in
the whole game), loaded by a resident graphics/file/input library; no compiled-C decompile route.
Reversed with the trace + callcap method of the other games here; every claim in the topic docs carries
a script and a match count, or is labelled INFERRED.

## Provenance

| item | value |
|---|---|
| archive | `Black Tiger (1989)(Capcom)[cr Replicants][m The Best][t].zip` (Dropbox, "ST games"), 358,890 bytes, sha256 `aad0dae21d92134017d5d54ed641d4c431af3ffb2364a8475010a217911e863a` |
| image | one `.st`, 819,200 bytes (80 tracks x 2 sides x 10 spt, FAT12, 2 sectors/cluster), sha256 `9442c54492a0cd0eb266205877f9f6f7c2a3f786b6b9d7f0929ea19e0f22fcf4`; not bootable (boot sum `$9dae`), launched from the desktop |
| crack | Replicants, "The Best"; trainer menu (T = 1000 lives and 14336 zenny at game start, not unlimited; SPACE = normal); the copy-protection check is already neutralised (`system.md` 10) |
| files | `BL_TIGER.PRG` (6,506 bytes, JEK-packed loader), `COMMAND.PRG` (77,350 bytes: a 556-byte trainer stub + the game), 8 level maps `0`..`7`, 7 tilesets `T0 T2..T7`, `BTSPR BTMAN BTA BTB BTCLIPS BTOBJ BT4 BT5 BTSND`, two Degas pictures, `BTIGER.DOC` (scenario text), `DESKTOP.INF` |

The disk image and the cracked archive are not committed.

## Documents

| document | what it covers | proof |
|---|---|---|
| [system.md](system.md) | boot chain, the 556-byte trainer wrapper, role of every file, memory map, frame structure (main loop `$c574`, 5 VBL per frame), state machine, the 32 `trap #3` services of the resident part, input, boss/shop/ending drives, copy protection | `py/systems/gates.py all`: frame gaps 49/49, Timer A 5348=5348=5348, demo stream 65/65/65, container windows 52/60 |
| [graphics.md](graphics.md) | drawing engine (software scroll, full tile redraw per frame), tilesets, maps, actor sprite banks, boss banks, picture banks, shop/intro/ending screens, palettes and fades | tiles 94.5-96.3% of 40,960 playfield pixels on 15 snapshots over all 8 levels; hero attack frames 100%; 10 pictures at 100%; bosses 71/132 instances exact; title 64000/64000 |
| [mechanics.md](mechanics.md) | level file format and marker scanner `$cd58`, collision (per-tile class table), hero movement, damage/vitality/death, map-object kinds, urns/chests/drops, shop and old men, score and money tables, level exit, boss, level clear | scanner 8/8, vertical step 393/393 + 391/391 + 396/396, weapon 25/25, urn 160/160, shop 200/200, bonus 8/8, rng 300/300, chest 30/30, drops 18/18 |
| [ai.md](ai.md) | object tables, spawner, activation window (the level is a horizontal ring), AI step `$dbde` for all 19 types, P/E/H shot tables, ambient hazards, bosses, the attract-demo player (a recorded joystick stream) | `$dbde` 2500/2500, spawner 9/9, window 160/160, ambient+boss fire 800/800, urn 96/96, events 600/600 |
| [sound.md](sound.md) | the sound system: no sequencer, every sound is an 8-bit sample played through the PSG volume registers by Timer A; the BTSND container, volume table, request path, which event requests which id, rendering | PSG writes 23,813/23,813 (8 sounds) and 52,887/52,887 (natural attract run); WAV numeric checks |
| [secrets.md](secrets.md) | cheats, hidden features, input census, dead code: level skip, pause, invisible dungeon doors, checkpoint, ending, trainer, immortal Spinning Skull, no extra life | `py/secrets/run_all.py`: 9 drives, each run twice, snapshots identical 9/9 |

`black_tiger.sym` is the merged name list (runtime absolute addresses, 372 names from six agents;
the clashes between agents were settled from routine bodies, not by vote: for example the three HUD
routines `$10026/$1008e/$100f6` are potions/armour/weapon).

## What it needed from the emulator

No instruction or addressing-mode wall. One fidelity divergence, not fixed (needs the full regression
net and a coordinated `MMU.fs` change):

| wall | where | status |
|---|---|---|
| The keyboard ACIA data register returns 0 when its FIFO is empty and pops the FIFO on read; a real 6850 keeps the last received byte in its data register. TOS's keyboard ISR consumes a SPACE press before the loader's two polling loops (`cmpi.b #$39,$fc02.w` at `$a562` and the trainer menu `$c658/$c662`) read it, so they never match | `MMU.fs` ~913 (read) and ~295 (status) | bypassed with two labelled pokes in `drive.txt`: `w a568 4e714e75` (nop the `bne`) and `w c65e 601e0c38` (`beq` -> `bra`: choose NORMAL). The game proper reads keys through TOS (`system.md` 8) and the joystick through the IKBD joystick vector, so nothing else depends on retention |

Also: an `\AUTO\` entry needs a valid 8.3 name. `AUTO_BL_TIGER.PRG` is silently not found by TOS 1.00
(the AUTO scan runs, finds nothing, boots the desktop).

## How it was run

From `M68000/`, `export ATARI_NOTRACE=1` (the raw binary otherwise traces every instruction).

```
mkdir -p scratchpad/black_tiger && cp "<Dropbox>/Black Tiger ... [t].zip" scratchpad/black_tiger/bt.zip
cd scratchpad/black_tiger && unzip bt.zip && mv "Black Tiger"*.st bt.st && cd ../..
python tools/extract_disk.py scratchpad/black_tiger/bt.st scratchpad/black_tiger/files
python tools/add_file_to_disk.py scratchpad/black_tiger/bt.st --from-disk BL_TIGER.PRG --name BLTIGER.PRG --auto --out scratchpad/black_tiger/bt_auto.st
dotnet exec bin/Debug/net8.0/M68000.dll 20000000 snapshot scratchpad/black_tiger/boot20M.snap --disk-a scratchpad/black_tiger/bt_auto.st   # PC=$a562, cracktro text screen
dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/black_tiger/boot20M.snap repl --disk-a scratchpad/black_tiger/bt_auto.st < reversing/black_tiger/drive.txt
```

`drive.txt` runs the two pokes, lets the attract mode reach the title screen (240M steps after the
trainer menu), presses joystick-1 fire (`kbd ff 80`, 100,000 steps, `kbd ff 00`) and writes
`scratchpad/black_tiger/play_start.snap`: a fresh game, level 1, 5 lives, score 0, hero controllable. The scripted run is
byte-identical (`cmp`) to the snapshot first reached by hand-driven steps. Joystick 1 is `kbd ff <state>`: bit 0 up, 1 down, 2 left, 3 right, 7 fire; hold
every packet at least 30,000 steps. Later levels: the game's own level skip (hold up+left+fire on joystick
1, press ClrHome, then Return per level; `py/systems/drive_levels.py`). Boss, shop and ending states:
`py/systems/drive_boss.py`, `drive_shop.py`, `drive_ending.py` (each poke is labelled in the script).

## Method notes worth keeping

- The frame driver is the game's own main loop (`$c574`), not the VBL-queue entry; the VBL entry only
  ticks counters. A frame is 5 VBLs (10 fps).
- Seven areas were read by parallel agents from one `BRIEF.md`; where two agents transcribed the same
  routine (`$cd58` spawner, `$d4ae` urn burst) both scripts were kept and both gates re-run: a free
  cross-check. Several first-round readings were corrected by the others (BTCLIPS/BTOBJ are picture
  banks, not collision data; `$cf20` is the map-object kind table and kind `$20`, not kinds 0..2, is
  the level exit; vitality 0 is not a death condition; Timer A is a sample player, not music).
- Scripts under `py/<area>/` derive the repo root from `__file__` (`M68000_ROOT` override) and keep
  their data under `scratchpad/black_tiger/agents/<area>/` (`BT_WORK` override); each directory has a
  README table of script / what it proves / expected output / runtime.

## Files

| path | what |
|---|---|
| `drive.txt` | cold-boot REPL drive to a controllable level-1 game |
| `black_tiger.sym` | merged names |
| `system.md graphics.md mechanics.md ai.md sound.md` | topic documents |
| `py/systems py/graphics py/mechanics py/ai py/sound` | gates, drives, decoders, renderers |
| `img/<area>/` | committed proofs: title/attract/boss/shop/ending screens, level sheets, 8 whole-level renders, tileset and sprite-bank atlases, picture banks, collision map, actor-type crops, sound sheet |

## Not exercised

No level was played through naturally (levels 2-8, every boss and the shop were reached by the built-in
level skip plus a labelled hero-position poke); no boss was killed by weapon hits (state poked); the
old men's dialogues were not driven on screen; the hostile-projectile handlers `$10e94 $10b84 $10894`
are read, not gated; the real Timer A rate and the real-hardware moment the title sample's tail is
overwritten are not observable in the emulator; boss names by level are inferred from the order in
`BTIGER.DOC`; nothing was listened to.

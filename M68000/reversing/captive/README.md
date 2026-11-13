# Captive

Captive (Antony Crowther, Mindscape, 1990; the in-game banner reads "COPYRIGHT RATT 1990 CAPTIVE A
MINDSCAPE PRODUCT") is a real-time dungeon crawler: four droids, run by remote control from a cell, raid
procedurally generated bases on a series of planets. The ST version is an Amiga port: every program
file on the disk is an Amiga hunk executable, loaded by the game's own file system and OS (`trap #9`).
The reason to reverse it is the base generator, which the game keeps as its own module, `fed_MapGen`.

## Topic docs

| doc | what it holds |
|---|---|
| `mapgen.md` | the base generator, ported whole: floors packed into one 64x32 grid as 16x8-cell blocks, lifts that join floors by a fixed block offset, a turtle digger under the perfect-maze rule, rooms, caves and shafts, the field of arrows back along the dig order, dead ends, features and what each is in play, locked doors with keys placed earlier in the dig order, coded doors, item and creature placement, seeds and output encoding |
| `ai.md` | the creatures: groups scheduled by timer, a decision rule with sight along a row or column only, tracking by breadcrumbs the party writes into the map, the generator's dig-order arrows where the party has not been, 3x3 formations tidied while the group is in view, hit points and death, Trill and the end of a base; getting into a base, the combination lock and the DIE that shows a door's next corner |
| `world.md` | the universe (50 planets, 100 moons and a station from one 16-bit LCG seeded by the mission number, a coordinate table that keeps dots off the map grid, syllable names, targets and landing sites), the main loop and raster list, the first-person view cone of pre-drawn mirrored pieces, the picture sheets, `Case.pic` |
| `system.md` | the `trap #9` OS in the low-RAM loader (files, heap, per-unit RLE), the volume block, the module launcher, the resident monitor, the Copylock in `fed_MapGen`, the Medway Boys crack, the READ TRACK emulator gap |

Every generator in the game uses the same LCG, `x = x*$5e5 + $29` mod 65536, with its own state and output
rotation: the universe (`world.md` section 1), the bases (`mapgen.md`) and the creatures (`ai.md`).

`py/infographics/` draws one explanatory figure per algorithm (the creature trail, the digger, the universe, the
combination lock) from the proven models and the game's own captured values; its README gives each script and the
evidence it re-runs.

## Provenance

| item | value |
|---|---|
| source | `The Medway Boys #97.zip` (Dave's Dropbox `ST games/`), compilation menu "Medway Boys Menu 97" with **1. Captive**, **2. Docs** |
| zip member | `TMB097.MSA`, 665,748 bytes, sha256 `f3b00f869dd6b07cb79bd26513c9f08ad2622c54c321815995064ec9330bc043` |
| disk image | `tools/msa2st.py` -> 819,200 bytes (80 tracks, 2 sides, 10 sectors), sha256 `2b19c735165ffac43661173af5187c446ea54e6c07b3b52beed722ffb03debf5` |
| working copy | `scratchpad/captive/tmb097.st` (untracked) |

The disk has no usable FAT. The boot sector is the Medway Boys loader: it reads tracks 64-68 side 1 to
`$10000` and runs the menu, which reads track 79 side 0 and track 0 side 0 to `$20000` and starts
Captive's own boot code. That code copies the loader into low RAM (`$206`-`$1200`, from track 0 sectors
2-5 and 7-10) and from then on reads the disk through the FDC directly, in the game's own format.

## Milestones

| milestone | how | screenshot |
|---|---|---|
| compilation menu | cold boot, 40M steps | `menu.png` |
| Captive intro ("Federation") | `1` at the menu, released after 30,000 steps | `intro.png` |
| planet screen, "CAPTIVE MISSION 0001" | Space during the intro | `mission1.png` |
| in orbit of planet 14 (PLANET-PAICKOT) | click the planet on the map, then ORBIT | - |
| on the planet surface | LAND | `landed.png` |
| inside a base | target 1's landing site selected at zoom 2, ORBIT, LAND, walk to the compound door, enter its corner code, step to the entrance cell (`py/ai/natural_base.repl`; `ai.md`, "Getting into a base") | `base1.png` |
| a base finished, and the mission's end screen | the level event a Trill attack raises, set by labelled pokes from inside the base: the party returns to the compound entrance; at the final base the mission number advances and the end screen shows (`py/ai/level_event.py`; `ai.md`) | `ai_trill_end.png` |
| a base blown up with the party inside | EXPLOSIVES on a generator, then stay until the fire reaches the entrance: "BASE HAS BEEN DESTROYED! WITH YOU IN IT!!!" in the same frame, and a click restarts at MISSION 0001 (`py/phoopel/state3/`; `ai.md`, "Finishing a base") | `ai_state3_end.png` |

`drive.txt` does the first three from a cold boot (about 300M steps) and writes `scratchpad/captive/mission1.snap`;
two runs give byte-identical snapshots.

```
cd M68000
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 1 repl --disk-a scratchpad/captive/tmb097.st < reversing/captive/drive.txt
```

Release the menu key early. The menu reads the key, loads Captive's boot code and jumps into it; that code
overwrites the IKBD vector `$118` (it reads `$30107601` there), so a key break that arrives after the
jump raises an ACIA interrupt into junk and TOS bombs. Releasing 30,000 steps after the make (the menu
reads the key 11,545 steps after it) is safe.

## What it needed from the emulator

| wall | fix |
|---|---|
| the loader's Restore (`$03`) then Step-in with update (`$53`) left the head on track 0, so every read of track 1 returned track 0, the loader's checksum failed five times, it tried drive B (Record Not Found), and its error path returned through a wrong stack slot into a filename string (address error, then a `Pterm0` loop through a junk `etv_term`) | `MMU.fs` Type I decode: Step-in (`%010u`) and Step-out (`%011u`) are told apart under mask `$E0`; the old `$F0` match could never see the update bit |

Separately, `ATARI_TRACE_GEMDOS=1` crashed the emulator itself (a .NET `BusError` from its Pexec
detector reading the word at a junk A7 during TOS's bomb loop): a tracing bug, not a game wall. The tracer's reads
can no longer fault (`tools/tests/repl_ergonomics/t5_gemdos_junk_a7.sh`); not yet re-run on Captive.

## Disk format

`py/fedfs.py <disk.st> list|extract <dir>` decodes it; all 31 files pass every unit checksum and every
packed file depacks to exactly its directory length.

- A **unit** is one track side, unit = 2 x track + side, 1280 longs: a header long stored inverted, 1278
  data longs each stored as value + k, with k starting at `$eff478ed` and advancing by `$bffb7e5e`, and a
  checksum long that makes the 32-bit sum zero. Keys and loop are the loader's (`$26a`/`$26e`, `$8cc`-`$90c`).
- A **file** runs along consecutive tracks of one side (units u, u+2, ...). In its last unit the
  checksum follows the file's last long. Side 0 holds the program modules and level pictures, side 1
  the credits, demo, main program, sounds and animation pictures.
- **Unit 1** is the volume block: its length in longs (`$15b`), the volume-name hash `1ce2 0047`
  (`hash("FED1")`), the name `fed1`, six type words and a 164-unit allocation map, and from byte 188 the
  directory, 20-byte entries of name[12], start unit, unit count, file type and length (`system.md` section 3).
- A unit whose data starts `PACK` is also run-length decoded as the loader copies it, a second packer below
  the file-level one (`system.md` section 1).
- **Packing.** Files start `RNC\x01` but are not Rob Northen ProPack: the header is only magic, unpacked
  length and packed length, and the data is a byte-oriented LZ read backwards and unpacked in place.
  `fedfs.depack` transcribes the game's depacker (`$303c`-`$31c2`, inside `fed_BootFile`).

The depack is checked independently by `py/hunks.py <file> <snap>`, which aligns each executable's code
hunk against RAM at mission 1:

| file | role (from where it runs) | loaded at | bytes equal to RAM |
|---|---|---|---|
| `fed_BootFile` | module launcher, depacker, resident monitor | `$1236` | 9,261 / 9,264 |
| `federation` | main program | `$369a` | 97,619 / 97,808 (its variables, and the 12 bytes at `$b514` the crack patches) |
| `fed_MapView` | planet map screen and universe generator | `$2f3f0` | 10,180 / 10,180 |
| `fed_MapGen` | base and surface generator (`mapgen.md`) | not loaded by mission 1 | - |

All are single position-independent code hunks with no relocations. The `trap #9` OS itself is not in
`fed_BootFile`: it is in the low-RAM loader at `$206`-`$1180`, decoded from track 0 (`system.md` section 1).

`Case.pic` is also a hunk executable, but not a picture: a 388-byte player and nine full-screen frames of the
briefcase opening, run as a program between `Fed_Demo` and `federation` (`world.md` section 5, `system.md`
section 2). The `.pic` files proper are four separate 8,000-byte bitplanes, Amiga layout, not ST screen format
(`world.md` section 4).

## The base generator, `fed_MapGen`

`federation` loads it at `$b510` (into the buffer at `15770(A6)`) and calls it at `$b5c2` with
`jsr 32(A4)`: offset 32 skips the 32-byte hunk header, so the call enters code offset 0. Arguments:
A0 = `9242(A6)` (the 64x32 tile layer; the second layer is at +2080), A1 = `$b532` (a table of output
pointers in `federation`), D0 = `32(A6)` = mission x 11 + target number - 1, D1 = `14790(A6)` = (mission & `$1ff`)
x 150 + object number, or `$ffff` for none (`$2f636`-`$2f65a`, read), D2 from the mode word `13564(A6)`: 0, 1,
2, 6 or 14, D3 = `14776(A6)`, D4 = -1. D2 = 0 or 1 builds a base, seeded by D0 alone; 2, 6 and 14 build a
planet surface, seeded by D1; D2 = 2 is a target's compound, whose entrance cell (returned in D5) leads into the
base (`ai.md`, "Getting into a base"). It returns in D0 the mask of creature sheets `fed6-A`..`G` to load, and the
entry column in `9238(A6)`; the base path returns D5 = D6 = 0. The same arguments give byte-identical output.
The algorithm is in `mapgen.md`.

The base path runs entirely in Python from (D0, D2): every stage from the blocks and the digger through the doors,
locks, item and creature placement to the output encoding is ported and chained, and the result matches the
emulator's returned output (the whole module block, the federation tables and layers, and D0, D5, D6) in 400/400
cases, D2 = 0 and 1 with D0 = 0..99 and the out-of-sample D0 = 300..399. The gates, controls and the chain's start
state are in `mapgen.md`.

Code offset 0 is a Rob Northen Copylock (`system.md` section 5). It reads the disk, adds its key into
`15538(A6)`, and feeds the generator nothing: calling the plain entry `$20054` with the caller's registers
reproduces the natural landing call on every output region (`mapgen.md`). On landing (`go_1.snap`, LAND) it is
called once with D1 = `$ffff` and builds a uniform surface, every cell `$1e`, in 841,721 steps.

## Not yet exercised

- What the six `15538(A6)` tests in `federation` gate on an uncracked copy (`system.md` section 5).
- The intro's top band and smeared figures (`intro.png`): intended animation or a rendering fault, unchecked.

## Files

| file | what |
|---|---|
| `drive.txt` | REPL drive from cold boot to the mission 1 planet screen |
| `menu.png`, `intro.png`, `mission1.png`, `landed.png`, `base1.png` | milestone screenshots |
| `infographic_trail.png`, `infographic_digger.png`, `infographic_universe.png`, `infographic_lock.png` | explanatory figures: creature pursuit along the trail and the dig-order arrows (`ai.md`), the digger and its flow field (`mapgen.md`), the universe from the mission number (`world.md` section 1), the combination lock and the DIE (`ai.md`); made by `py/infographics/` |
| `ai_*.png` | figures for `ai.md` (the DIE's hint faces, the Trill screens, the state-3 game-over screen) |
| `py/fedfs.py` | disk decode, directory, extract, depack |
| `py/hunks.py` | hunk parser and RAM alignment |
| `mapgen.md`, `ai.md`, `world.md`, `system.md` | topic docs (table at the top) |
| `mapgen_*.png` | generated bases, one colour per floor, and the decorated wall pictures (`mapgen.md`) |
| `world_case_strip.png`, `world_sheets_surface.png`, `world_fed7E_walls.png`, `world_map_fit.png` | the briefcase frames, the surface picture sheets, the wall sheet, the generated planets over the map screen (`world.md`) |
| `py/mapgen/`, `py/ai/`, `py/world/`, `py/system/` | the scripts behind each topic doc, each with a README table of command and expected output |
| `py/phoopel/` | the sealed-key bug behind the Phoopel hint: keys the generator drops on their own door cell, the clipboard number, the census over missions 1..100, the lock panel driven by clicks, explosives on a generator and leaving (`mapgen.md` "Sealed keys", `ai.md` "Finishing a base") |
| `mapgen_lock_panel.png` | a lock's wall panel in play: cover, 16-segment grid with the lock's number, the code lit |
| `mapgen_panel_kinds.png`, `mapgen_door_kinds.png` | the four key kinds' panels (cover, opened, code set) and the three door kinds shut and open (`py/phoopel/panels/`) |
| `py/infographics/` | the four figure scripts, a facts file per figure mapping each drawn fact to its source, and a README |

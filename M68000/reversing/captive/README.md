# Captive

Captive (Antony Crowther, Mindscape, 1990; the in-game banner reads "COPYRIGHT RATT 1990 CAPTIVE A
MINDSCAPE PRODUCT") is a real-time dungeon crawler: four droids, run by remote control from a cell, raid
procedurally generated bases on a series of planets. The ST version is an Amiga port: every program
file on the disk is an Amiga hunk executable, loaded by the game's own file system and OS (`trap #9`).
The reason to reverse it is the base generator, which the game keeps as its own module, `fed_MapGen`.

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
| in orbit of star 14 | click the star on the map, then ORBIT | - |
| on the planet surface | LAND | `landed.png` |

`drive.txt` does all three from a cold boot (about 300M steps) and writes `scratchpad/captive/mission1.snap`;
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
detector reading the word at a junk A7 during TOS's bomb loop): a tracing bug, not a game wall, and not
fixed.

## Disk format

`py/fedfs.py <disk.st> list|extract <dir>` decodes it; all 31 files pass every unit checksum and every
packed file depacks to exactly its directory length.

- A **unit** is one track side, unit = 2 x track + side, 1280 longs: a header long stored inverted, 1278
  data longs each stored as value + k, with k starting at `$eff478ed` and advancing by `$bffb7e5e`, and a
  checksum long that makes the 32-bit sum zero. Keys and loop are the loader's (`$26a`/`$26e`, `$8cc`-`$90c`).
- A **file** runs along consecutive tracks of one side (units u, u+2, ...). In its last unit the
  checksum follows the file's last long. Side 0 holds the program modules and level pictures, side 1
  the credits, demo, main program, sounds and animation pictures.
- **Unit 1** is the volume block: its length in longs (`$15b`), `1ce2 0047`, the name `fed1`, a 176-byte
  table (role not known) and from byte 188 the directory, 20-byte entries of name[12], start unit,
  unit count, pad and length.
- **Packing.** Files start `RNC\x01` but are not Rob Northen ProPack: the header is only magic, unpacked
  length and packed length, and the data is a byte-oriented LZ read backwards and unpacked in place.
  `fedfs.depack` transcribes the game's depacker (`$303c`-`$31c2`, inside `fed_BootFile`).

The depack is checked independently by `py/hunks.py <file> <snap>`, which aligns each executable's code
hunk against RAM at mission 1:

| file | role (from where it runs) | loaded at | bytes equal to RAM |
|---|---|---|---|
| `fed_BootFile` | loader, `trap #9` OS, depacker | `$1236` | 9,261 / 9,264 |
| `federation` | main program | `$369a` | 97,619 / 97,808 (the rest are its variables) |
| `fed_MapView` | planet map screen | `$2f3f0` | 10,180 / 10,180 |
| `Case.pic` | code hunk, 288 KB, role unknown | `$1f62c` | 132,973 / 288,388 |
| `fed_MapGen` | base generator (below) | not loaded by mission 1 | - |

All are single position-independent code hunks with no relocations.

## The base generator, `fed_MapGen`

`federation` loads it at `$b510` (into the buffer at `15770(A6)`) and calls it at `$b5c2` with
`jsr 32(A4)`: offset 32 skips the 32-byte hunk header, so the call enters code offset 0. Arguments:
A0 = `9242(A6)`, A1 = `$b532` (a table in `federation`), D0 = `32(A6)`, D1 = `14790(A6)`,
D2 = 1, 2, 6 or 14 from the mode word `13564(A6)`, D3 = `14776(A6)`, D4 = -1. It returns D0
(`13402(A6)`), D5 and D6 (`13556(A6)`, `13560(A6)`), and the callers copy D5 or D6 to the position
`26(A6)`. The callers (`$8836`, `$8852`-`$88a0`, `$bd6a`) set the mode from a request word `14788(A6)`
and re-run it when the position equals the returned entry position, and `$8804` steps `14776(A6)`:
inferred to be entering, moving between and leaving a base's levels.

It runs on landing: from `scratchpad/captive/go_1.snap` (in orbit), LAND calls it once from `$b5c2` (module at
`$1f7b0`, entry `$1f7d0`) with D0 = 1, D1 = `$ffff`, D2 = 14, D3 = 0, A0 = `$1d9e8`, A2 = `$303c` (the
depacker), and it returns after 841,721 steps with D0 = 48, D1 = 30, D2 = 20. `callcap $1f7d0` from the call
matches that natural return on every returned register and on all 4,096 changed bytes callcap prints (of 8,919;
the natural run changes 8,949, the difference starting with interrupt-side counters). Its output from `$1d9e8`
is one value, `$1e`, repeated: the landing call builds a uniform planet surface, not a base. It also changes
the loader's state block (`$117c`-`$11b3`), so it reads the disk itself.

Code offset 0 is not the generator: it calls `trap #9` (functions 60 and 96), points the illegal
instruction vector `$10` at itself, executes `illegal` and then `movec` (`$4e7a`), the opening of a Rob
Northen Copylock. `$0`-`$1000` holds that prologue and a high-entropy (encrypted) block, `$1000`-`$4000` is
zeros, and `$4000`-`$719c` is plain code. The call returns normally under the emulator; what the prologue
checks, and whether the Medway crack disarmed it, is not read yet.

## Not yet exercised

- Entering a base, so `fed_MapGen` building one. Its protection prologue runs to completion on landing.
- The intro's top band and smeared figures (`intro.png`): intended animation or a rendering fault, unchecked.
- Everything in `federation` beyond the generator's callers.

## Files

| file | what |
|---|---|
| `drive.txt` | REPL drive from cold boot to the mission 1 planet screen |
| `menu.png`, `intro.png`, `mission1.png`, `landed.png` | milestone screenshots |
| `py/fedfs.py` | disk decode, directory, extract, depack |
| `py/hunks.py` | hunk parser and RAM alignment |

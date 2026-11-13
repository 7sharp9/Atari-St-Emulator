# populous2: booted to gameplay, first program map

*Populous II: Trials of the Olympian Gods* (© 1991 Bullfrog Productions / Electronic Arts),
Atari ST, from the WILD! compilation disk #29 ("CRACKED BY SPIKE OF WILD!"). It runs from a cold
boot through the compilation menu, the crack's AUTO chain and the game's own depacker to the title
menu (CREATE YOUR DEITY / CONQUEST GAME / CUSTOM GAME / LOAD GAME), the conquest briefing, the
manual-lookup question the crack disables, and into the isometric game against the computer god
Epimetheus. No emulator change was needed.

The game is hand-written assembly, not compiled C like Populous (1): 5 `LINK` words in the
220 KB image against 404 `RTS` and 181 `MOVEM` pushes, so there is no decompile route and the
work goes through traces and `callcap`. It still shares Populous's world model in places; each
point below says whether it matches `reversing/populous/` and how that was checked.

Evidence labels: **verified** (an emulator check with a match count, script named), **traced**
(seen in an emulator trace or FDC/GEMDOS log), **read** (read from the code, not yet driven).

## Provenance

**Disks and binaries are commercial and not committed.** Reproduce from the archive:

```
WILD! #29.zip            (Dropbox "ST games")  holds one file:
  WILD29.MSA   780865 bytes   sha256 f2e18041f15e4a11f836b6102f8f8ef627f264109699005a1641cd5753943dba
  -> tools/msa2st.py -> wild29.st   819200 bytes   sha256 e56c3944ee680cda0dad160099bfdf91f1f73473cad0e4a047246945072232d5
```

819200 bytes is 80 tracks x 2 sides x 10 sectors. The disk boots through `\AUTO\` (no GEM desktop
step). Populous II is the whole disk apart from the two other menu entries, `BUGBASH.WLD` (154672,
a `$601a` program, menu key 2 "BUG BASH") and `ZAP.WLD` (8894, key 3 "ZAP").

| file | bytes | sha256 (prefix) | what |
|---|---|---|---|
| `AUTO\CD29PACK.PRG` | 100298 | `014f33aa` | the WILD! #29 menu (`compilation_menu.png`); key 1 picks Populous II |
| `AUTO\AUTORUN4.PRG` | 554 | `2e0c556b` | "AUTORUN Version 4.4 (C) 1991 Boris & Mac Sys Data", runs after the menu |
| `AUTO\POPII.PRG` | 1410 | `d0662f03` | crack stub (clears the trace vector `$24`, prints an obfuscated text); not analysed |
| `AUTO\POP2LOAD.PRG` | 157 | `a707e114` | `Pexec(0,"credits.tos")` (absent: returns -33) then `Pexec(0,"pop2.tos")` |
| `POP2.TOS` | 94660 | `716e2fe7` | the game: a `$601a` header around a packed image (text `$17118`, no data or BSS, a 144-byte packer symbol table: `depak`, `_decrunc`, `reloc_st`, `the_prog`) |
| `BLOCK0..3.PAK` | 26-28 K | | landscape block graphics, one per landscape type (traced: `BLOCK0` and `BLOCK1` load to `$47d28`) |
| `LAND0..3.DAT` | 556 each | | per-landscape table, loaded raw to `$36cc2` (traced); content not decoded |
| `S16-0.PAK`, `S32-0.PAK` | 34224 / 14788 | | 16x16 and 32x32 sprite banks (names only; load to `$6f2b0` / `$69450`, traced) |
| `S16-n.DIF`, `S32-n.DIF` | 10 .. 14760 | | per-landscape sprite differences; the 10-byte ones are all `$ff` (read raw to `$a000`, traced) |
| `QAZ.PAK` | 32000 | | the in-game backdrop screen (32000 = one ST screen; loads to `$54c80`) |
| `TITLE.PAK`, `CONQUEST.PAK`, `PANEL.PAK`, `FACES.PAK`, `FX.DAT` | | | title picture, briefing screen, panel, deity faces, sound effects (from the names and the screens they load before; not decoded) |
| `JUDGE`, `AWARDS`, `HANDS`, `ELEMENTS`, `END.PAK` | | | in the game's file table, not loaded on the path to gameplay |
| `TITLELI.PAK` | 8094 | | starts `ICE!` (Pack-Ice); not in the game's file table |

`QAZ.PAK` carries the packed flag (below) but is exactly 32000 bytes, a raw screen's size; how
the decrunch treats it is open.

## Boot path

Traced with `ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1` and `ATARI_TRACE_FDC=1`:

1. TOS runs `\AUTO\CD29PACK.PRG` (text `$a304`), the compilation menu, by step 7.0M. Key 1
   (`kbd 02` / `kbd 82`) makes it exit; TOS then runs `AUTORUN4.PRG`, `POPII.PRG` and
   `POP2LOAD.PRG` in directory order.
2. `POP2LOAD` Pexecs `pop2.tos` at basepage `$a3c4`, text `$a4c4`. Its stub (traced and read,
   `$a4c4..$a516`) enters supervisor mode, blacks the palette, masks interrupts, copies a
   `$f2`-byte mover to `$167e` and jumps there. The mover copies `$16ff0` packed bytes to `$1770`
   and decrunches them in place (a backwards bit-stream cruncher: last long the unpacked length,
   an EOR checksum, LZ copies and literal runs), then `jmp $600`.
3. `$600` is the crack's patch: `move.l #$4e714e71,$14a88` / `jmp $1770`. In the image as
   decrunched (read at `bp 600`), `$14a86` is `cmp.w D1,D2` and `$14a88` is `bne.w $1494a`, the
   jump back after a wrong answer to the "Zeus asks" manual question; the two NOPs remove it, so
   any answer is accepted (the drive's OK with the default `0000` reaches the game, traced).
4. `$1770` (entry) sets SP = `$12522`, clears `$392c2..$65ae4` and `$2022..$12522`, so the image
   has a 64 KB hole in the middle that holds the two screens (`$2300` and `$a000`, pointers
   `$392e0`/`$392dc`, set that way at entry and found swapped in the play anchors) and the stack;
   then IKBD and MFP setup (below), a video check (`btst #1,$ff820a`: at 60 Hz it prints "SORRY
   PAL MACHINES ONLY" and spins at `$1850`), and `jsr $12524`, the game. When that returns it restores the screen,
   VBL and IKBD vectors and `Pterm0`s.
5. From here the game loads only through its own FDC code (no GEMDOS call after `Super`); the
   loader is below.

| step (cold boot) | event |
|---|---|
| 4.08M | `Pexec("\AUTO\CD29PACK.PRG")` |
| 7.0M | menu screen (`Setscreen` `$f8000`) |
| 80M + key 1 | `AUTORUN4` → `POPII` → `POP2LOAD` → `pop2.tos` |
| 120M | title menu (`title.png`) |

## Drive recipe: cold boot to gameplay

Run from `M68000/` (the snapshots are written to the current directory; the anchors below are
this script's output moved to `scratchpad/populous2/anchors/`):

```
uv run python tools/msa2st.py scratchpad/populous2/src/WILD29.MSA scratchpad/populous2/wild29.st
dotnet exec bin/Debug/net8.0/M68000.dll 80000000 repl --disk-a scratchpad/populous2/wild29.st \
    < reversing/populous2/drive.txt
```

`drive.txt`: key 1 at the menu, 40M steps to the title menu (`p2_title`); pointer to (140,98)
and a left click on CONQUEST GAME, 20M (`p2_briefing`); pointer to (50,192) and PROCEED, 30M
(`p2_zeus`, the manual question); pointer to (150,180) and OK, 40M (`p2_game_start`, step
211.28M); 60M more with no input (`p2_game_60m`). The mouse is in absolute mode, so `mouse move`
moves only the IKBD cursor and the game reads it through its `$0D` interrogation; the pointer
words are `$393fa`/`$393fc`. Two cold-boot runs gave byte-identical snapshots at all five points,
and `p2_game_start` is byte-identical to the one reached interactively with GEMDOS tracing on.
Each snapshot has a provenance sidecar, so `resume` remounts `wild29.st` by itself.

## The program (first map)

Addresses are runtime absolute; the image is not relocated (it is built for `$1770`). Names are in
`populous2.sym`.

### Interrupts and input (read; IKBD traced)

| vector | handler | what |
|---|---|---|
| `$70` VBL | `$18fa` | if `$18f8` is set, only flags the frame. Otherwise: tick counters `$392d8`, `$392d0`, `$392d4`; sound hook `$2b29a` while `$2cade` is set; a mouse-button state machine on the report's button byte `$2023` (jump table `$1936`, latches in `$39402..$39408`; on a new press it copies the pointer long `$393fa` to `$393f6` and `$3979a` to `$3940a`); sends IKBD `$0d`; unless the hide count `$2246` is set, restores the 16-row background saved at `$2032` and redraws the pointer at (`$393fa`,`$393fc`) into the screen at `$392dc` (`$2300`, the displayed one in both play anchors) from sprite data `$682d0 + [$11d50]`, rows clipped when y > 184 and the right word dropped when x > 304; sets the frame flag `$392cc` |
| `$118` IKBD | `$1c42` | `$f7` absolute-mouse reports (6 bytes, count in `$2022`) into `$2025..$2029`, then button `$2023` and x/y `$393fa`/`$393fc`; key make/break into the 128-byte key map `$392f4` (`st`/`sf`), the held-key count `$393f4` and `$392ec` (the make code, 0 after a break) |
| `$134` Timer A | `$2aa4e` | not read (sound, by analogy with Populous's sample player) |
| `$128`, `$130` | `$1e20`, `$1e40` | MFP receive/transmit buffer, presumably the two-player serial link; not read |
| `$100..$120` (except `$118`), `$124`, `$12c`, `$138`, `$13c` | `$1de0` `rte`; `$1de2`/`$1dea` clear an in-service bit; `$1df2`/`$1dfa` set the background colour | an MFP source routed to the `rte` fires 800 times in 200 VBLs (traced), 4 per VBL, which is Timer C's 200 Hz (inferred) |

IKBD setup `$1bac` sends `$15` (joystick interrogation mode), `$09 01 3f 00 c7` (absolute mouse,
320 x 200) and `$0c 01 01` (scale 1). This is the Populous scheme: absolute mode, a `$0d`
interrogation every VBL, a 6-byte `$f7` report and the same pointer clip constants (184, 304) as
Populous's VBL routine `$16d32` (`reversing/populous/graphics.md` "Mouse pointer"); the code is a
rewrite, not a copy.

### Main loop `$12524` (traced)

`jsr $12524` from the entry runs the whole game. It loops back from `$13340` to `$1252a` and
returns on the quit word `$39604`. `$39766` is the screen mode: 8 is the play screen, which calls
`$1e7b2`, `$14158`, `$136ba`, `$13574`, `$16836` (unless `$39768`), `$1df44`; other modes go
through `$1e75e` and the mode dispatch `$1e300`. Then the land cursor and panel code (read: the cursor
cell (`$3e7a6`,`$3e7a8`) is compared with the view origin (`$3e79e`,`$3e7a0`) against a bound of 8
cells, which suggests Populous's 8x8 close-up view), then `$1334a`, `$2309a`, `$25652`, `$26644` (skipped while `$39798`),
`$27faa`, `$1fcce`, `$29c7e`, `$2a0b2`, `$1bfe`, `$2d4c8`, `$29226`, and the key handling on
`$392f4`. An event trace of 2.4M steps (200 VBLs) from `p2_game_60m` runs the loop **29 times**,
one game tick per about 7 VBLs: every routine named here is called exactly 29 times, among 23 call
targets at that count (`tools/call_census.py ev60.bin`; the census is
`scratchpad/populous2/calls60.txt`). None of them is named yet.

### The landscape (verified)

The world is 64x64 cells, as in Populous. Populous II keeps **one 4-byte record per cell** at
`$3979e` (`$4000` bytes, index `(y*64 + x)*4`) and **no corner-height grid**: byte 0 & 7 is the
cell altitude, byte 1 the shape code, and a corner height is read off the cell.
`corner_height` `$1f176(D0=x, D1=y) -> D2` returns `(cell.b0 & 7) + bit k of $36b7a[cell.b1]`,
where `$36b7a` maps a shape code to its corner mask and k picks the corner (the far edge x = 64 or
y = 64 reads the neighbour cell's other bit). Populous 1 stored the 65x65 corner heights and
derived the cells from them (`reversing/populous/terrain.md` section 1); Populous II keeps only the
derived pair, and the corners follow from it.

`py/corners.py` checks this on a snapshot:

| check | `p2_game_start` | `p2_game_60m` |
|---|---|---|
| each of the 65x65 corners reads the same height from every cell that touches it | 4225/4225 | 4225/4225 |
| Populous 1's `$c0ee` derivation applied to that corner grid gives back b0 & 7 and b1 (rock `$2f`/`$3f` excluded) | **4071/4071** | **4055/4055** |
| control: the same with Populous 1's shore rule (+`$10` on a slope at sea level) | 3334/4071 | 3318/4055 |
| `$1f176` under `callcap` at every non-zero corner, 100 sea corners and 3 edge corners | **915/915** | **920/920** |
| control: an altitude-only model (b0 & 7) | 357/915 | 356/920 |

So the cell derivation is Populous 1's, minus the shore codes: byte 1 holds slopes 1..`$0e`, flat
`$0f`, rock `$2f` and a further `$3f`, and no `$11..$1e`. `py/find_corner_grid.py` searches RAM
for a separate 65x65 grid (byte or word, every even base `$2000..$80000`) that derives the cells:
the best real candidate matches 2875 of 4086 cells, the all-sea baseline, while a planted copy of
the true grid (`--control`) matches 4071.

At `p2_game_start` byte 2 is zero on 4078 cells (1, 2, `$70` or `$f5` on the rest) and byte 3 is
non-zero on 21 cells with 19 distinct even values, which looks like an index (an occupant, by
analogy with Populous's `$37fd4`); both are unnamed. Byte 0 also carries bit 3 or 4 on 57 cells,
unexplained.

### World generator `$1ebee` (read)

`gen_land` clears the cell map and walks a hill table at `$30664` of 4-word records (`y range,
y base, x range, x base`, giving `y = rand() mod range + base` and the same for x; the snapshot
holds four, one per quadrant (ranges 6..34 and 35..57), ended by `$ff9d`). For each, `hill_walk`
`$1ec38` seeds two LCG states from those two `rand` results and steps them as
`s = (s*$24a1 + $24df) & $7fff`, the constants of Populous's PRNG `$16702` (`terrain.md`
section 3), moving x and y by `s mod 7 - 3` and calling `raise_point` `$1ec8c` until it returns
negative or a D4 it leaves is 8 or more (not yet pinned down). `raise_point` counts calls in
`$39788`, reads the corner through `$1f176`, stops at height 8, and recurses into a neighbour
that would end more than one below the raised corner: Populous's neighbour-difference raise, not
yet compared with it. Populous 1 had three walks stopping at height 6. Not yet driven or
callcapped.

### Random numbers (verified)

`rand` `$215dc` is not Populous's: seed long `$47382` (0 is replaced by `$bc614e`),
`seed = seed * $bb40e62d mod 2^32` (multiply `$21608`), result `(seed >> 8) & $7fff`.
`py/rand_gate.py` pokes 50 seeds and callcaps: **50/50** seed and D0; dropping the zero-seed
rule fails one (49/50).

### Loader (traced and read)

`load_file` `$2cc98(D0 = index)` indexes a 48-byte file table at `$2cdb6` (29 records, BLOCK0 to
`panel.pak`): +0 load address, +4 the files whose residency a load ends (their buffers overlap),
+8 `$fffff` in every record (passed to the read in D1, a size limit), +16 the packed flag,
+18 the 8.3 name. A file whose bit is set in the
residency mask `$39606` is not read again (returns 2). Otherwise `$36efc(A0 = name, A1 = address, D1)` reads it with the
FDC directly (the register code at `$37734`); on a failure it calls `$14b1a` and retries; the
record's +4 files are cleared from `$39606` and its own bit set, and a packed file is decrunched in
place by `decrunch` `$2246a`, the same algorithm as the POP2.TOS stub's (not compared byte for
byte). The packed flag is set on exactly the `.PAK` records (29 of 29). In the FDC trace of the drive
(`py/fdc_files.py`), 11 of the 13 files read land at their record's +0 address; the two `.DIF`
files go to `$a000` (the second screen) instead.

## How it was analysed

- `tools/msa2st.py`, `tools/extract_disk.py`; first bytes of every file.
- The depacked image read from a snapshot (`$1770..$392c2`); `tools/disassemble.py --snap <snap>
  --all 1770 392c2` as the whole-image listing (`scratchpad/populous2/pop2_all.asm`, 71077 lines,
  ends at `$392c0`).
- `ATARI_TRACE_EVENTS` over 200 VBLs of play and a call/interrupt census.
- `ATARI_TRACE_FDC=1` over the whole drive, mapped to files by `py/fdc_files.py`.

## Not yet exercised

Only the conquest start against Epimetheus has run. Not driven: any click in play (raise/lower,
powers, the panel), the custom game and deity creation, save/load, the two-player link, the end of
a battle. Unread: every routine of the main loop by name, Timer A, the sprite and block formats,
`LANDn.DAT`, the entity records, the computer god.

## Files

| file | what |
|---|---|
| `drive.txt` | REPL script, cold boot to `p2_game_60m` (deterministic, two runs byte-identical) |
| `populous2.sym` | names used here |
| `py/corners.py` | the corner-height model, its re-derivation and the `$1f176` callcap gate |
| `py/find_corner_grid.py` | the RAM search for a separate corner grid, with a planted control |
| `py/rand_gate.py` | `rand` `$215dc` against its model, 50 callcaps |
| `py/fdc_files.py` | names the file behind each sector of an `ATARI_TRACE_FDC` log |
| `compilation_menu.png`, `title.png`, `briefing.png`, `zeus.png`, `game_start.png`, `game_60m.png` | the milestones (`tools/snap_render.py` of the boot and the five anchors) |

Working data (`scratchpad/populous2/`, gitignored): `src/WILD29.MSA` (the archive's content),
`wild29.st`, `files/` (extracted), `anchors/` (`scratchpad/ANCHORS.md`), `pop2_1770.bin`
(the depacked image), `pop2_all.asm`, `fdc.log`, `ev60.bin`, `calls60.txt`.

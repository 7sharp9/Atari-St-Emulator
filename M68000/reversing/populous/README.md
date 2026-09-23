# populous — booted to gameplay, then taken apart

*Populous* (© 1989 Bullfrog Productions / Electronic Arts), Atari ST, from the
[cr Replicants] scene crack ("CRACKED BY DOM"). It runs from a cold boot through the
crack's loader, the intro (`DEMO.GOD`) and its TUTORIAL / CONQUEST / CUSTOM title menu,
the "World to conquer: GENESIS" briefing, and into the isometric game with the book
minimap, the command panel and a computer opponent terraforming its corner. **Reaching
gameplay needed no emulator changes**; driving its mouse UI exposed one IKBD bug (below).

The game program is compiled C (Alcyon / DRI), uncompressed, with LINK/UNLK frames on
every function, so most of the analysis is a headless Ghidra decompile checked against the
running game. The results are in five topic documents, each backed by a Python
reproduction diffed against the real code:

| document | covers | proof |
|---|---|---|
| [`graphics.md`](graphics.md) | asset formats (LZ packer, blocks, sprites, font, pictures), palette, 8x8 isometric block renderer, walls, water, sprite list, minimap, panels, mouse pointer, double buffering | `py/pop_render.py` rebuilds the frame from RAM + asset files: **64000/64000 pixels on 12/12 frames**, draw list identical |
| [`terrain.md`](terrain.md) | 65x65 corner heights and the per-cell maps, raise/lower (neighbour-difference recursion, cost 4n+10), world generator (PRNG, three random-walk hills, rock/tree scatter), world names, `LEVEL.DAT`, conquest progression, the terrain powers | `py/verify_gen.py`: heights + 3 derived maps + final seed **byte-identical for 3 worlds**; `py/verify_cmd.py`: raise at a peak **134/134 corners**; `py/powers/`: the six powers, `$fe00`/`$feca`/`$108b8` vs `callcap` **2305/2305**, 8/8 casts through the UI identical on all 37824 state bytes; `py/endgame/`: next world `$1d0e6` **65/65** and 3/3 through the UI, typed world names round-tripped through the briefing **45/45**, the three start paths **35/35**, starting walkers **28/28** |
| [`mechanics.md`](mechanics.md) | entity record, walker stepping/merging/drowning, combat, settlement land value and building size, growth and walker emission, mana, power costs, win/lose, score | `py/people_model.py` over 400 frames: settlements **4122/4122**, mana **774/774**, spawns **12/12**; combat **18/18** rounds; `py/walker/`: direction choice `$f2f4`/`$f6b2` **2400/2400** callcaps, gather and fight played through the UI with every decision (**8000/8000**) and every walker cell per frame (**51863/51863**) predicted; knight target/merge/raze **720/720** callcaps and **154/154** live calls; `py/endgame/`: score screen `$1c858` **200/200** callcaps and **56/56** fields over 7 real end states |
| [`systems.md`](systems.md) | trail effects, the three key checks (the crack's $54ac0842), pause, the save-game format and LOLO1.GAM, sound effects and speech | `py/systems/`: trails **400/400 + 400/400** callcaps and **394/394** live frames; pause 40/40; LOLO1 reproduced by a real save; 12/12 sounds |
| [`ai.md`](ai.md) | the computer god: per-side god record, reaction-rate limiting, magnet/mode strategy, power casting thresholds and targeting, site levelling, how conquest levels and the custom "OPTIONS FOR EVIL" set it up; strategy notes | `py/ai_diff.py`: 4 decision routines vs `callcap`, **4800/4800** full memory deltas; `py/ai/`: a rating-1, reaction-1, all-powers opponent set up through the menus, every AI command in two natural runs predicted (**1854/1854** vs an idle human, **2766/2766** Atari vs Atari; every AI call in them matched under `callcap`), walker land edits **2400/2400** |

`populous.sym` (302 names) is the shared symbol file; `level_table.txt` decodes all 99
`LEVEL.DAT` records.

## The program

**Disks and binaries are commercial and not committed.** Reproduce from the archive:

```
Populous (1989)(Bullfrog)[cr Replicants].zip   sha256 b6488c29010e0ebc10d92134f08e41b12c8237e2effc99c182db778d6acad7ee
  -> Populous (1989)(Bullfrog)[cr Replicants].st  sha256 da85d94bd6ad50b046946fc1c88078765e3692cf04d3877ca685a85ee7ea6d4d  409600 bytes
POPULOUS.GOD  sha256 e2f46c08727a8358b7056b6591ba0ecaf7e01c9ffadb3083870e576f9c680343
DEMO.GOD      sha256 2ab8465d32bbed0a81eecf5ef7bad0f3126750ced9ed8875d930a66757a1ae59
LOADER.TOS    sha256 c488ccff12b5e76d49823aaac493f86ce040fff09cdc4de47ee95cb6e83ec969
```

400 KB single-sided FAT12 (80 tracks x 10 sectors), boot sector not executable, no
`\AUTO\`. `DESKTOP.INF` sets up the GEM desktop ("THE" / "REPLICANTS" drive icons); the
user is expected to double-click `LOADER.TOS`. The disk is full.

| file | bytes | what |
|---|---|---|
| `LOADER.TOS` | 1406 | crack loader: banner, key wait, runs `demo.god`, then loads `populous.god`, patches it, runs it with the menu choice as argv |
| `DEMO.GOD` | 25530 | the intro: iso-view credits sequence alternating with the `LOAD.PIC` title menu |
| `POPULOUS.GOD` | 104137 | the game. GEMDOS PRG, text $1670c / data $1eec / bss $1a200, 4206 relocations, no symbols |
| `LAND0`..`LAND3` | ~19-21 K each | per-landscape block graphics + a $72-byte table header (grass, desert, snow/ice, rock) |
| `SPRITES0.DAT`, `SPR_320.DAT`, `FONT.DAT` | 14094 / 5198 / 2171 | 16x16 sprites, 32x32 sprites, 8x8 font (all LZ-packed) |
| `QAZ.PIC`, `LORD.PIC`, `MOUTHS.PIC` | | in-game screen backdrop, the deity screen, its mouth animation |
| `LOAD.PIC`, `DEMOBACK.NEO` | | intro title menu and intro backdrop (DEMO.GOD only) |
| `LEVEL.DAT` | 990 | 99 conquest level records, one per 25 worlds |
| `GWORDS`, `GMUSIC1` | 107 / 61082 | speech-sample index (samples on side 1 of the original disk), bank of 12 sampled sound effects; there is no music |
| `LOLO1.GAM` | 14336 | a save cut short by a full disk: the `$1db98` layout (29646 bytes) truncated in the terrain-class map (`systems.md` 5.2) |
| `ONE-BACK.EXT`, `ONE-WYCH.EXT`, `LOLA.WCP` | 0 | zero-length entries, unreferenced by the game's strings |

Every data file except `LEVEL.DAT`, `GWORDS` and `GMUSIC1` uses one LZ format:
`[u32 packed length incl. header][u32 unpacked length][stream]`, the stream a sequence of
big-endian control words (`w >= 0`: copy `w+1` literal bytes; `w < 0`: copy `1-w` bytes from
the absolute output offset in the next word). The depacker is `$2019a` (`lz_depack`); the
Python port is `py/popdepack.py`.

### How it starts

1. TOS runs `\AUTO\LOADER.PRG` (on the prepared disk, below). It prints the crack banner
   (Cconws) and waits for a key (Crawcin).
2. Pexec(0, `demo.god`). DEMO.GOD loads `load.pic` and shows the **title menu** for up to
   500 frames (`$b3e8`, DEMO.GOD basepage `$ac58`): a left click at x > 220 picks by y band
   (y > 184 CUSTOM = 1, y > 168 CONQUEST = 2, y > 152 TUTORIAL = 3), which becomes its
   Pterm code. Otherwise it plays the iso-view credits sequence and loops.
3. Pexec(3, `populous.god`) into basepage `$ac58` (TEXT `$ad58`). The loader overwrites
   two immediates, at text+`$b2be` and text+`$ccc6` (runtime `$16016`, `$17a1e`), with
   `$54ac0842`. Both sit in Supexec'd routines (`$16014`, `$17a1c`) that originally did
   `move.l #<text base>,d0 / move.l d0,$24`, pointing the **trace vector** into the
   program: remnants of the original trace-mode protection. It then Pexec(4)s the program
   with `" <code>"` as the command line; `main` stores `atoi(argv[1])` in `$37ebc` (game mode:
   1 custom, 2 conquest, 3 tutorial; 1 when there is no argument, `$ae38`). What each mode
   sets up is in `terrain.md` 3, "Start paths".
4. POPULOUS.GOD reads track 0 sector 1 of side 1 then side 0 (Floprd, `$b2ac`: a first byte of
   `$39` from side 1 sets `$21ffe`, which enables the digitised speech read raw from side 1 of the
   original double-sided disk; the single-sided crack has none, `systems.md` 6.1), loads `gmusic1`, `qaz.pic`, `font.dat`,
   `sprites0.dat`, `spr_320.dat`, installs its own IKBD (MFP 6, `$1ff8a`) and serial
   (MFP 10/12) handlers, and in conquest mode shows the GENESIS briefing. START GAME builds
   the world (`$b316` new_world) and loads `land0`.

OS-call timeline of the drive recipe below (`ATARI_TRACE_OS=1`, absolute steps):

```
OS    900425   Pexec(mode=0, "\AUTO\LOADER.PRG")        basepage $a204
OS   2795308     Crawcin()                               <- kbd 39 b9
OS   3000432     Pexec(mode=0, "demo.god")               basepage $ac58
OS   5100195       Fopen("load.pic") ...                 title menu at step ~5.33M (u b410)
OS   6349679     Pexec(mode=3, "populous.god")           basepage $ac58, text $ad58+$1670c
OS   8094679     Pexec(mode=4)                           game starts
OS   8097572       Floprd(track 0, side 1, sect 1)  then side 0
OS   8613409       Fopen("gmusic1") ... Fopen("qaz.pic"), "font.dat", "sprites0.dat", "spr_320.dat"
OS   9384675       Mfpint(6, $1ff8a)  Mfpint(10, $1fd88)  Mfpint(12, $1fda0)
OS   9385612       Fopen("land0")   OS 11308845 Fopen("level.dat")   conquest briefing (GENESIS)
OS  46757783       Fopen("land0")                        <- START GAME: world built, gameplay
```

## What it needed from the emulator

No instruction wall and no peripheral gap from cold boot to gameplay. Two fixes came later:

| symptom | fix |
|---|---|
| `mouse move` in the REPL (and the live window) sent relative `$F8 dx dy` packets although the game had put the IKBD in absolute mode; Populous's handler (`$20048`) stored the dx/dy bytes as key presses, so a text field opened after a move started with a stray character and keypad-scroll codes could reach the game | `MMU.MoveMouse` / `Video.sendMousePacket`: in absolute mode only the 6301's cursor moves, as on real hardware |
| `ATARI_TRACE_GEMDOS` reported the parent's basepage for a Pexec mode-0 child (`demo.god` showed the loader's `$a204`) | the Pexec hook waits until `act_pd` moves off the caller's basepage; `demo.god` now reports `$ac58` |

Both passed the regression net (verify, 30M-step snapshot byte-identical, selftest 0 wrong), and
PowerMonger's click-driven drives (also absolute mode) gave byte-identical snapshots before and
after the mouse fix.

One tool fix: `tools/disassemble.py` decoded PEA as SWAP (the `$4840` mask covered PEA's
whole EA space), which garbles every Alcyon-compiled call that passes a pointer. Commit
`936f6d9` adds PEA, ADDX/SUBX, CMPM, ABCD/SBCD/NBCD, CHK and MOVE USP, each mask taken from
`Instructions.fs` / `68k.fs`.

## Drive recipe: cold boot to gameplay

```
python tools/add_file_to_disk.py "<...>[cr Replicants].st" --from-disk LOADER.TOS --name LOADER.PRG \
    --remove LOADER.TOS --remove DESKTOP.INF --auto --out scratchpad/pop/pop_auto.st
dotnet exec bin/Debug/net8.0/M68000.dll 3000000 repl --disk-a scratchpad/pop/pop_auto.st \
    < reversing/populous/drive.txt            # writes pop_game_start.snap in the cwd
```

The disk is full, so the loader move first frees the `LOADER.TOS` and `DESKTOP.INF` entries,
then re-adds the loader as `\AUTO\LOADER.PRG`; nothing else changes. `drive.txt`:
SPACE at the banner, run to the title menu's wait loop (`u b410`), move the pointer to
(250,176) and click CONQUEST, run 40M steps to the briefing, move 165 left and click START
GAME, run 30M steps. Always pass `--disk-a` again on `resume` (the mount is not
snapshotted). The recipe is deterministic: two cold-boot runs produced byte-identical
snapshots.

## Driving play

`py/popdrive.py` plays the game through its own mouse UI. It reads the pointer (`$24748`), the
view origin and the corner heights from a snapshot and turns "raise corner (x,y)", "click icon
NAME" or "show corner (x,y)" into exact `mouse move`/`down`/`up` REPL lines, using the hit tests
of `$c3e2` (panel, minimap) and `$119e6` (land cursor) documented in `graphics.md`, "Mouse
input". `run(snap_in, lines, snap_out)` feeds them to a resumed REPL.

```
python py/popdrive.py <snap> raise 11 16     # minimap click to show the corner, then the land click
python py/popdrive.py <snap> icon mode_fight
python py/panelmap.py <snap> panel_regions.png
```

`py/verify_drive.py` proves the model from `game_start.snap` (**17/17** checks): the minimap
click sets the predicted view; a left click on corner (11,16) changes the same 134 corners as the
injected command and `popgen.raise_pt`; a right click lowers as `popgen.lower_pt`; the magnet icon
plus a land click moves the papal magnet; and 13 icon clicks change exactly the state the code
predicts.

## Working data (`$POP_WORK`)

The scripts in `py/` read their inputs from `$POP_WORK`, default `M68000/scratchpad/pop/`
(gitignored, `py/popcfg.py`): `files/` (the extracted disk files), `pop_ad58.img` (the
program relocated to `$ad58`, `tools/prg2img.py files/POPULOUS.GOD pop_ad58.img ad58`),
`pop_auto.st`, and the snapshots. Anchors, all from the recipe path:

| snapshot | state |
|---|---|
| `game_start.snap` / `repro.snap` | first gameplay frame, conquest world 0 GENESIS, frame 285 (repro = the committed recipe's exact output) |
| `g90.snap` | 190 frames later |
| `late1..late4.snap` | +60M..+240M steps from `repro` with no input (frames 835..2161): the computer levels its south-east corner (207 corners changed by late4) and banks mana (7485) |
| `agents/graphics/*_pre/_post.snap` | the 12 renderer test frames (scrolled views, selections) |
| `agents/terrain/cmd_*.snap`, `cc_b316_*.json` | raise/lower commands and the three new-world callcaps |
| `agents/people/fr/run400.bin` | 400 frames of RAM captured at entry/exit of `$db4c` |

## How it was analysed

**Decompile.** `tools/ghidra/DecompileAll.java` runs under Ghidra 12.1 `analyzeHeadless` on
the relocated image (raw binary, `68000:BE:32:default`, base `$ad58`), seeds functions at
every LINK A6 and every `jsr`/`jmp abs.l` target, and writes one C file (run from `M68000/`):

```
analyzeHeadless <projdir> popproj -import scratchpad/pop/pop_ad58.img -overwrite \
  -processor 68000:BE:32:default -loader BinaryLoader -loader-baseAddr 0xad58 \
  -scriptPath tools/ghidra -postScript DecompileAll.java 0x1670c scratchpad/pop/pop_ad58.c \
  reversing/populous/populous.sym reversing/populous/py/ghidra/purge.txt reversing/populous/py/ghidra/traps.txt
```

Alcyon's `lmul`/`ldiv` helpers return through their stack argument slots, so the script sets
their stack purge (`py/ghidra/purge.txt`) and marks the GEMDOS/XBIOS trap wrappers varargs
(`py/ghidra/traps.txt`). With `populous.sym` applied, 108 functions and the named globals
carry their names in the output. 227 of 231 functions decompile cleanly; the four largest (`$b510`, `$bbd4`,
`$f2f4`, `$113ce`) lose stack tracking and were read from the disassembly. Trap-call
argument lists are unreliable in the decompile, so those were read from the disassembly too.

**Trace.** `ATARI_TRACE_EVENTS` over 20M steps of gameplay (191 frames) from
`game_start.snap`, then

```
python tools/trace_cfg.py scratchpad/pop/game.evt --range ad58 21464 \
    --names reversing/populous/populous.sym --callgraph callgraph.dot --blocks blocks.txt
dot -Tsvg callgraph.dot -o callgraph.svg
```

found the once-per-frame routines (`main_loop` `$b510` → `entity_update` `$db4c`,
`draw_terrain_window` `$14364`, `exec_player_commands` `$1e712`, ...) that seeded the four
topic studies. The hottest edges are `land_value` → `cell_step_check` (29649 calls: every
settlement rescans its 17-cell footprint each frame) and the terrain block blitter (12368).

**Verification.** Every claim in the topic documents is either a Python reproduction diffed
against the real code (callcap, frame captures, or the frame buffer; counts in the table at
the top) or explicitly marked "inferred"/"code-read". Not exercised in the emulator:
flood and armageddon cast by the computer, the population-208 trail spawn, the serial link.
The emulator's Timer A is a stub (64 interrupts per frame), so sampled sounds play at the wrong
rate; the rates in `systems.md` 6 come from the code.

## Files

| file | what |
|---|---|
| `graphics.md`, `terrain.md`, `mechanics.md`, `ai.md`, `systems.md` | the topic references |
| `populous.sym` | `addr<TAB>name`, runtime addresses (feeds `trace_cfg.py --names` and the Ghidra script) |
| `level_table.txt` | all 99 `LEVEL.DAT` records decoded |
| `drive.txt` | cold-boot-to-gameplay REPL script |
| `callgraph.dot` / `.svg`, `blocks.txt` | named call graph and executed-block map of 191 gameplay frames |
| `panel_regions.png` | the `$c3e2` click regions of every command icon and the minimap, over a game frame |
| `py/` | `popcfg.py` (paths), `popdepack.py`, `snapram.py`, `planar.py`; driving `popdrive.py`, `panelmap.py`, `verify_drive.py`; graphics `pop_assets.py`, `pop_render.py`; terrain `popgen.py`, `popworld.py`, `popmem.py`, `verify_gen.py`, `verify_cmd.py`, `maps_png.py`; people `people_model.py`, `capframes.py`, `fightcheck.py`, `dument.py`, `repl.py`; AI `ai_ref.py`, `ai_diff.py`, `hx.py`, `fieldxref.py`; `ghidra/` overrides for `tools/ghidra/DecompileAll.java`; per-area subdirectories `walker/`, `powers/`, `endgame/`, `ai/`, `systems/` (listed in `mechanics.md` 9), their snapshots and captures under `$POP_WORK/<area>/` |
| `intro.png`, `title_menu.png`, `conquest_briefing.png`, `gameplay.png` | milestones: intro credits, the LOAD.PIC title menu, the GENESIS briefing, the first gameplay frame |
| `real_game_start.png`, `mine_v5547.png`, `mine_v5547_diff.png` | emulator frame vs `pop_render.py` output and their (empty) diff |
| `land0..3_blocks.png`, `sprites0.png`, `spr_320.png`, `font.png`, `icons_150e2.png` | decoded block/sprite/font/icon sheets |
| `qaz.png`, `lord_pic.png`, `mouths_lordpal.png`, `load_pic.png`, `demoback_gamepal.png` | decoded pictures |
| `h_game_start.png`, `shape_game_start.png`, `h_gen_w1235.png`, `shape_gen_w1235.png`, `raise_11_16_delta.png` | height and terrain-code maps (GENESIS; generated world 1235 SADINDON), the corners changed by one raise |

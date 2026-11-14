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
`scratchpad/populous2/calls60.txt`). Named so far: `$2309a` `update_entities` and `$1fcce`
`update_scenery` ("Objects and entities"), `$29226` `run_commands` ("Raise and lower"), `$25652`
`ai_run_sides` and the rest of the list ("The computer god"); `$26644` walks the `$4505a` array.

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
| Populous 1's `$c0ee` derivation applied to that corner grid gives back b0 & 7 and b1 (settlement codes `$2f`/`$3f` excluded) | **4071/4071** | **4055/4055** |
| control: the same with Populous 1's shore rule (+`$10` on a slope at sea level) | 3334/4071 | 3318/4055 |
| `$1f176` under `callcap` at every non-zero corner, 100 sea corners and 3 edge corners | **915/915** | **920/920** |
| control: an altitude-only model (b0 & 7) | 357/915 | 356/920 |

So the cell derivation is Populous 1's, minus the shore codes: byte 1 holds slopes 1..`$0e`, flat
`$0f`, `$2f` and `$3f` (flat land held by a settlement of side 1 or side 2, "Objects and
entities"), and no `$11..$1e`. `py/find_corner_grid.py` searches RAM
for a separate 65x65 grid (byte or word, every even base `$2000..$80000`) that derives the cells:
the best real candidate matches 2875 of 4086 cells, the all-sea baseline, while a planted copy of
the true grid (`--control`) matches 4071.

Bytes 2-3 are one word, the head of the cell's occupant list, and byte 0's bits 3-7 are a count
of entities that have stepped onto the cell ("Objects and entities" below).

### Objects and entities (layout verified; states counted, handlers read)

Everything that stands on a cell is a record in one heap of four arrays that share a header:
+0 type, +2 next and +4 prev (signed word offsets from `$3ff1a`, 0 for none), +6 and +8 the x and
y position words (high byte the cell, low byte the fraction of a cell), +12 the side (0 = free).

| array | records | live at `p2_game_start` / `p2_game_60m` | what |
|---|---|---|---|
| `$3f42a` | 200 x 14 bytes | 11 / 11 (type `$16`, side 3) | scenery, updated by `$1fcce` |
| `$3ff1a` | 400 x `$34` bytes, record 0 the null sentinel | 9 / 18 (sides 1 and 2) | entities, updated by `$2309a` |
| `$4505a` | 250 x 32 bytes | 0 / 0 | updated by `$26644` (state byte +22, table at `$26668`); not yet seen live |
| `$46f9a` | 3 x 14 bytes | 2 / 2 (type `$14`, sides 1 and 2, both on cell 32,32) | one per side; by Populous's analogy the papal magnets (inferred) |

Each cell's word 2 heads a doubly linked list of the records on it. `move_entity` `$2436e(A0,
D6=x, D7=y)` writes the new position, unlinks the record from its old cell's list, pushes it on
the new cell's and adds 8 to the new cell's byte 0 (the old cell's count is left alone).
`py/walkers.py` checks the lists on a snapshot: every live record of all four arrays is in
exactly one list, its own cell's, and every list node is a record whose prev link is the node
before it: **22/22** at `p2_game_start`, **31/31** at `p2_game_60m` and at 2.4M steps after it,
0 list faults each; taking the cell from the low bytes 7/9 instead breaks 22, 31 and 31 lists. A
`watch` over the cell map for 2.4M steps from `p2_game_60m` sees 55 writes, 54 of them `$2436e`'s
three per move (18 cell changes). The byte-0 count only grows: non-zero on 57 cells at
`p2_game_start`, 187 at `p2_game_60m`, 203 after 2.4M more steps, almost all 1 or 2 and only 18 of
them under a current occupant. What reads it is not found yet; a footfall count is the obvious
reading (inferred).

**Entity records** (`$34` bytes). Two types are live in play: type 4, positioned on a cell centre
(`$xx80`), in state 6; and type 2, at fractional positions, in state 4. Byte 1 of a type-4 record
runs 1..`$0c` (unnamed; a settlement size is the Populous reading). +14 and +16 are signed
velocity words (±`$14`, a twentieth of a cell per tick); +20 a step countdown; +22 the state and
+23 the state to take next; the long +26 is halved when a record over `$14` is split into a copy
(`$26522` copies all `$34` bytes into a free slot and sets the copy's state to `$24`), which makes
it a strength or population (inferred). `$2622a` scans the array for the nearest record of another
side with +26 > 0 (read).

`update_entities` `$2309a` first resets the per-tick fields of the side records 1 and 2
(`$470fe`, `$47238`; the side records are `$46fc4 + side * $13a`, also indexed by the current
player `$4739c` in `$136ba` and `$14158`), then for each live entity calls `$24a92` and dispatches
on +22 through the word table at `$2311c` (20 entries, states 0..`$26`). State 4 (`$233b4`)
advances the animation index +10 through `$32902` and counts +20 down; at expiry (`$233d8`) it
loads +23 into +22 and re-dispatches through `$23100`, otherwise (`$233e2`) it adds the velocity to
the position and calls `$2436e` when the cell changes. State 2 (`$23164`) calls `$24f3a`, which
re-dispatches when it returns non-zero; otherwise it goes on and, on the path taken here, branches
back into `$233b4` (`$2328a` or `$233ae`). State 6 is `$23580`; it calls `$25168` once per tick (377 = 13 x 29 below). `hits` over the 2.4M-step window
(`py/entity_states.sh`), with 18 live entities throughout:

| point | calls | accounted for |
|---|---|---|
| `$2309a` | 29 | one per tick |
| `$230fa` (first dispatch of a live record) | 522 | 18 x 29 |
| `$23100` = `$24a92` = `$2310e` (dispatch) | 535 | 522 + 13 re-dispatches |
| state 4 expiry `$233d8` | 13 | the 13 re-dispatches, all into state 2 |
| state 2 `$23164`; `$24f3a` returning zero (`$23180`) | 13; 13 | |
| state 6 `$23580` | 377 | 13 settled records x 29 |
| state 4 `$233b4` | 158 | 535 − 377 − 13 = 145 dispatched + 13 from state 2 |
| state 4 move path `$233e2` | 145 | 158 − 13 expiries |

So in this window a walker's step countdown expires 13 times, each time into state 2, whose test
`$24f3a` (unread) fails every time and sends it straight back to walking.

**Settlement land, codes `$2f` and `$3f`.** The two cell shape codes above the slopes mark flat
land held by side 1 (`$2f`) or side 2 (`$3f`). Every settled entity sits on its own side's code:
4/4 at `p2_zeus`, 8/8 at `p2_game_start`, 13/13 at `p2_game_60m`, and 0 of them on the other
side's code (control). Every `$2f`/`$3f` cell without a settlement on it lies within 2 cells
(Chebyshev) of a settlement of the side its code names: 6/6, 17/17, 28/28 (`py/owned_cells.py`).
The writer is `$25298` in `$25168`, the routine state 6 calls each tick: a `watch` on cell (8,32)
after the world build catches it writing `$2f` there, and the one on the whole map from
`p2_game_60m` caught it writing `$3f` at (48,54). How far a settlement claims, and from what, is
not read yet (the counts suggest a radius that grows with byte 1).

`update_scenery` `$1fcce` walks the 200 scenery records. Byte 1 is a counter: positive values
count down every tick in which `$3979c & $30e86` is 0; when the record's cell has shape 0 (flag
`$88` in the shape table `$3697a`, set for shape 0 only) a live record's counter is negated and
then counts toward `$30e89` (`$18`), where the record is freed and unlinked (`$24430`). So scenery
on a cell lowered into the sea dies after `$18` ticks (read; not yet driven). Type `$1e` records
take a separate path through the animation table `$32902`.

### World generator `$1ebee` (verified)

The conquest world is built by `$22942` after the briefing's OK: `$2d326`, then `$1ebe4` (copies
the seed `$47382` to `$4737e` and falls into `gen_land`), then `$1f870` and `$1fa6c`, `$22986`,
the load of file `$e` and the redraw (read). `gen_land` `$1ebee` clears the cell map and, for
each 4-word record of the hill table `$30664` (`y range, y base, x range, x base`, ended by
`$ff9d`), draws `r1 = rand()`, `y = r1 mod yrange + ybase`, `r2 = rand()`,
`x = r2 mod xrange + xbase`, and runs `hill_walk` `$1ec38` from there. The table holds four
records: (29,6,29,6), (23,35,23,35), (29,6,23,35), (23,35,29,6), one hill per quadrant.

`hill_walk` keeps two 15-bit LCG states seeded with `r1` and `r2` and steps them as
`s = (s*$24a1 + $24df) & $7fff`, the constants of Populous's PRNG `$16702` (`terrain.md`
section 3). Each step moves x by `s1 mod 7 - 3` and y by `s2 mod 7 - 3`, then calls `raise_point`
(so the start point itself is never raised). The walk ends at the first corner `raise_point`
rejects (off the map, or already at 8; it returns D4 = −1 and the N flag) or raises to 8 (D4 is the
new height). Populous 1 ran three walks that stopped at height 6. `raise_point` writes the corner
into the four cells that share it: corner bit 4 of cell (x−1,y−1), 8 of (x,y−1), 2 of (x−1,y),
1 of (x,y) in the mask `$36b7a[b1]`. A clear bit is added; a set bit means the corner is already
one above the cell's base, so the base b0 goes up by one and the cell's other corner bits are
cleared. Every write also clears byte 0 bits 3-7, the footfall count.

`py/gen_gate.py` pokes 30 seeds (the natural `$10d7`, 0, 1, `$ffffffff` and 26 random) into
`p2_gen_entry` (stopped at `$1ebee`, `py/gen_entry.sh`) and callcaps `gen_land`:

| check | seeds |
|---|---|
| all `$4000` bytes of the cell map equal to the model | **30/30** |
| the same, plus the final seed, `$39788` and `$3962c` | **30/30** |
| control: the walk stops at height 6 (Populous 1) | 16/30 |
| control: the corner written before the recursion (Populous 1's `raise_point`) | 0/30 |

Worlds range from 475 to 1964 non-sea cells over the 30 seeds. With the natural seed, the
model's corner heights are still those of `p2_zeus` (the Zeus question, before play): the 10 cells
whose (b0 & 7, b1) differ are flat cells recoded `$2f` or `$3f` by the settlements' first ticks
after the build (`$25298`, "Objects and entities").

**Scenery scatter `$1f870` and `$1fa6c` (verified).** The next two passes scatter scenery records
in clusters. `$1f870` draws `rand() mod N + N/2 + 1` clusters (N = `$30e8c`, 9). Each cluster has
a random centre cell (`rand() & $3f3f`) and, from one more `rand()`, a frame index (mod 8) and an
attempt count (mod M = `$30e8a`, 14, plus a bonus, + 1). Each attempt adds a random entry of the
45-offset table `$30e96`, a diamond up to 4 cells out, to the centre. It places a type-`$16`
record (side 3, counter `$18`, frame from `$30e8e`, or that table's first frame when a further
`rand() mod $5a` is 0) on the cell unless the cell is off the map, sea, flagged `$40` in
`$3697a`, or already occupied. A full array ends the cluster. The bonus is meant to come from a
side record when D2 is a side. At this call D2 still holds `$ff9d`, the hill table's terminator,
so the code reads byte `$3f6a9`, which is inside the scenery array (record 45, byte 9): once 46
trees exist, each later cluster gets `$80 >> 4` = 8 more attempts. `$1fa6c` is the same scatter
for type-`$18` records with its own tables (`$1fc65..$1fc72`), no bonus, and a full array skipping
one attempt. On the natural seed it places nothing: all 29 of its on-map attempts land on sea
(`hits` from `b_1fa6c`).

`py/scatter_gate.py` callcaps each pass from the snapshot before it (`py/build_passes.sh`) with
30 poked seeds and compares the scenery array, the cell map and the seed:

| pass | equal to the model | control: occupied cells allowed | control: no bonus |
|---|---|---|---|
| `$1f870` | **30/30** | 10/30 | 30/30 |
| `$1f870`, `$3f6a9` poked `$80` at entry | **30/30** | 2/30 | **0/30** |
| `$1fa6c` (11 trees already placed) | **30/30** | 9/30 | n/a |

On unpoked seeds the bonus never fired (at most 46 trees). The poked half proves the stale-D2
read: with record 45 still free, the first clusters run with 8 extra attempts until a tree
overwrites the byte. Then `$22986` places the entities and the two `$46f9a` records and fills the
side records (writes listed from the snapshots, not yet modelled).

### Raise and lower (verified, from a click to the cell map)

**The click.** With the raise/lower power selected (`$47372` = 2, as it is in play), the main
loop turns a left click on the land into command 2 and a right click into command 4. It writes
the command and the cursor corner (`$3e7a6`,`$3e7a8`) into the local player's command record
(`$473c4` points at `$473b0`, side 1) at `$13208` (left) or `$1332e` (right), one tick after the
button goes down. `py/click_ab.py` moves the pointer from `p2_game_60m` to screen (200,110),
cursor corner (11,30), then runs the same 660,000 steps with no click, a left click and a right
click:

| run | command written | corners changed vs the no-click run | model at the cursor corner | models at the 3 neighbouring corners | mana below control |
|---|---|---|---|---|---|
| left | 2 at (11,30) | 16 | equal | 0/3 equal | 322 (16 x 20 = 320) |
| right | 4 at (11,30) | 1 | equal | 0/3 equal | 20 |

The extra 2 mana on the left run accrued over the ticks after the raise and was not traced
further.

**The command records.** `$29226` (once per tick) walks the two 10-byte records `$473b0` and
`$473ba` (+0 side, +1 command, +2 x, +3 y, +8 a mode: 2 and 4 run the command directly, 6 and 8 first call `$1f16`/`$1eaa`, presumably the
serial link, read only), runs the command through the word table at `$29300` (`$292dc`), then
clears +1..+3. Command 2 (`$2937e`) calls
`cmd_raise` `$1f6ce(D0=x, D1=y)`. Command 4 (`$293f6`) calls `$24de0`, which first walks the
occupant list of cell (x,y): if it holds a settled entity (type 4) of the commanding side, it
sets bit 2 of that entity's byte +13 and lowers nothing; otherwise it calls `cmd_lower`
`$1f6a0`. Both command routines clear the corner count `$3962c`, seed the dirty box
(D6 = `$01000100`, D7 = 0), call the point routine and, when the box grew, redraw it (`$1f6fa`, read). Back in the handler the
side pays `power_cost(0, side) * $3962c * 4` from its mana (long +0 of the side record
`$46fc4 + side*$13a`), floored at 0.

**The point routines.** `raise_point` `$1ec8c(D0=x, D1=y)` counts the call in `$39788`, rejects
a corner outside 0..64, stops at height 8, otherwise visits the eight neighbours in the order N,
NE, E, SE, S, SW, W, NW and recurses into each one lower than the corner, then writes the corner
at height + 1 into the four cells that share it. `lower_point` `$1eed4` is the mirror: it stops at
0 and recurses into each neighbour higher than the corner. This is Populous's rule (a difference of
at most 1 between neighbours, heights 0..8, `reversing/populous/terrain.md` section 2), with a
different neighbour order and the corner written after the recursion rather than before.

`py/raise_gate.py` checks the whole command path under `callcap`: for 35 corners (20 land, 10
sea, 4 on the map's edges and corners, the highest corner) it pokes a raise and a lower into side
1's record, plus raises for side 2 at 6 of them, and callcaps `$292dc`:

| check | `p2_game_start` | `p2_game_60m` |
|---|---|---|
| corner grid after the call equals the model (own-settlement redirect included) | **76/76** | **76/76** |
| control: only the clicked corner moves | 40/76 | 42/76 |
| mana charged = 20 x corners changed (20 x the old `$3962c` when redirected) | **76/76** | **76/76** |
| every cell outside the settlement codes re-derives from the new corner grid by the rule of "The landscape" | 76/76 | 76/76 |

Without the redirect rule the grid check is 75/76 on each anchor: lowering corner (12,33) under
side 1's settlement `$01d4` changes no corner and sets its flag (`$400fb`, 0 to 4). The charge
in that case is 20 times whatever `$3962c` the previous terrain command left (1 at `p2_game_60m`,
3 at `p2_game_start`). Poking `$3962c` to 7 before the same command charges 140, so the charge
comes from the stale count, not from this command. What the flag does to the settlement is
unread. 228 and 231 corners changed over the corpus; the largest single raise, at the highest
corner of `p2_game_60m` (height 4), moved 40.

**The cost.** `power_cost` `$2657e(D0=power, D1=side)` (read) takes the base cost from the
36-word table `$310d0` (raise and lower are power 0 at 5; `$ffff` marks a power that cannot be
bought). The powers fall in six groups of six (`$265d2` maps a power to its group). The cost is
reduced by `base / d`, where `d` comes from `$30ef6` (0, 0, 10, 9, 8, 7, 6, 5) indexed by the
side's experience byte for that group (side record +82+group) shifted right by 5. Experience was
0 in both anchors, so the discount has not run. Mana is kept at four times the shown value
(`$136ba` reads it shifted right by 2; that this is the display is inferred), so a raised corner costs 5 shown mana. Populous 1
charged `4n + 10`.

### The computer god `$25652` (read; the controller word driven)

`ai_run_sides` `$25652` runs once a tick, after `update_entities`, and plays a side through the same command record
the mouse writes: it posts at most one command a tick into the side's record (`$473b0` for side 1, `$473ba` for side
2), and `run_commands` `$29226` then executes it like a click. It loops the two side records (`$470fe`, `$47238`,
stride `$13a`) and branches on the **controller word, side record +26**: 2 is a human and the side is skipped, 4 is the
computer, `$12` runs the land stages below every tick and skips the last two (the options screen `$15e7c` toggles +26
between these values beside the strings "COMPUTER V HUMAN", "COMPUTER V COMPUTER" and "HUMAN V HUMAN"; that `$12` is a
human side with land help is inferred, not driven).

For a computer side: `subi #1,76(A1)`, then `ai_flush_mailbox` `$256d6`, then nothing more until the countdown +76
reaches 0, when it reloads from +104 (30 on battle 0, so the cascade runs every 31 ticks) and, if the command record
is free, runs a cascade in which the first stage to post a command ends the side's turn:

| stage | posts | when (read) |
|---|---|---|
| `$25770` `ai_level_settlement` | command 4 (lower) on a neighbour cell higher than the settlement, 2 (raise) on a lower one | +46 names a settlement whose size byte +1 differs from +19; mana above 4 x the raise cost + 2; own countdown +44 |
| `$259ba` `ai_release_settlement` | command 4 on its own strongest settlement (+30) | that settlement's strength long +26 is above a threshold from `$36d0e` (200 on this battle); mana; countdown +48 |
| `$25a32` `ai_cast_power` | a power command | tick long `$3979a` at least 250 and the enemy has a settlement; draws `rand % 148(A1)` into the side's plan list of (power, kind) pairs at +152 (slot 0 is no power); the kind picks the target: the enemy's strongest settlement, the nearest land within 2 or 6 cells of it, queued in +56/+58 for the next flush, or only with a leader of strength `$1000`; mana above 4 x the power's cost |
| `$25bf4` `ai_magnet_and_mode` | command 8 (papal magnet) to the enemy's oldest settlement, or a walker mode `$0e`/`$10`/`$12`/`$14` | only with more own settlements than `$30722` (30) does it move the magnet; below that it only leaves mode `$10` |

**The mailboxes.** The stages do not search the map. `update_entities` zeroes side-record words 28, 36, 46, 50 and 54
(and sets 32 to `$ffff`) each tick (`$230c6`), and the entity handlers refill them: a settlement in state 6 writes
+46 (a settlement that wants its land changed), +28/+30 (the strongest own settlement), +32/+34 (the oldest, by the
birth tick in entity +46) and counts itself in +36; a walker about to step into water or against an obstacle posts
its cell in +50/+52/+53, and one needing a raise under itself posts in +54. `ai_flush_mailbox` turns +54, the queued
power and +52/+53 into commands, the last two regardless of the countdown. A human side's mailboxes are filled and
never read.

**Driven: the controller word** (`py/god_census.sh`, three arms of 12,000,000 steps from `p2_game_60m`, `hits`):

| arm | ticks `$29226` | computer branch `$25670` | cascade `$25690` | posts (mailbox + level + release) | commands executed `$292e4` |
|---|---|---|---|---|---|
| unpoked (side 2 is the computer) | 143 | 143 | 4 | 2 + 2 + 1 | 5 |
| side 2's +26 poked to 2 (`ww 47252 2`) | 143 | 0 | 0 | 0 | 0 |
| side 1's +26 poked to 4 (`ww 47118 4`) | 134 | 268 | 122 | 18 + 61 + 12 | 91 |

Every command executed is one of the three posts in each arm. With side 1 poked the cascade runs on almost every
tick, not every 31st: side 1's reload word +104 is the likely cause and was not read. Over 120,000,000 unpoked steps
(1424 ticks; an agent's run, `scratchpad/populous2/agents/god/h3.log`) the cascade ran 46 times and all 49 executed
commands were raises and lowers from those three sites (20 + 23 + 6); `$25a32` and `$25bf4` ran 17 times each and
posted nothing, because on battle 0 side 2's plan list is empty (+148 = 1) and it has 6 settlements against the
magnet's 30. The power and magnet stages have run only under pokes of the plan list and of `$30722`.

**The release.** Command 4 on a side's own settlement sets bit 2 of entity +13 and lowers nothing ("Raise and
lower"). Seen once after `$259ba` posted it: at the settlement's next state-6 expiry it took the branch at `$236b8`
that allocates a walker group, +13 went back to 0 and its strength fell from 411 to 293. So lowering your own
settlement sends its people out, as lowering a castle does in Populous; the share that leaves (`114(A2)`) is read only.

**Against Populous** (`reversing/populous/ai.md`, `ai_think $13eda`): the same design, one command through the
human's path with the human skipped by a controller word. Populous II replaces the reaction-frame `busy` flag with a
countdown and a free-record test, replaces the walk over the walkers with mailboxes the entity update fills, keys
the settlement release on a strength threshold instead of an option bit, and draws powers from a per-battle plan
list in which each entry carries its own targeting rule.

**The other once-a-tick routines** (read to their end or first data): `$29c7e` `run_scripted_commands` replays a
per-battle table at `$39638` (6-byte entries: tick, a command byte at +3, x/y at +4) through `do_command` as side 3,
empty on battle 0; `$27faa` expires and animates a 200-record array at `$3e7aa`, empty in every run; `$2a0b2`
services 10-byte request records at `$2a396` (sound requests, inferred); `$2d4c8` is a bare `rts`; `$136ba` draws the
current player's mana bar and power icons and `$14158` the highlight of the side's mode word +12. None of them makes
a decision.

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

Only the conquest start against Epimetheus has run. Driven: raise and lower by a click. Not driven:
the other powers and the panel, the custom game and deity creation, save/load, the two-player link, the end of
a battle, the computer god's power and magnet stages in natural play (a later battle), the `$12` controller from the
options screen. Unread: `$26644`, `$1334a` and `$1bfe` of the main loop, the entity states other
than 2, 4 and 6 (and `$24f3a`, `$24a92`), the `$4505a` array, the reader of the cell footfall
count, the settlement flag bit 2 of entity +13, the experience discount of `power_cost`, Timer A, the sprite and block formats, `LANDn.DAT`.

## Files

| file | what |
|---|---|
| `drive.txt` | REPL script, cold boot to `p2_game_60m` (deterministic, two runs byte-identical) |
| `populous2.sym` | names used here |
| `py/corners.py` | the corner-height model, its re-derivation and the `$1f176` callcap gate |
| `py/find_corner_grid.py` | the RAM search for a separate corner grid, with a planted control |
| `py/walkers.py` | the object heap and the per-cell occupant lists, with a low-byte control |
| `py/entity_states.sh` | per-state call counts of `update_entities` over 29 ticks, and the list check after them |
| `py/raise_gate.py` | raise and lower through the command handler under callcap against the point-routine model, mana and re-derivation |
| `py/click_ab.py` | a left and a right click on the land against a no-click control |
| `gates.toml` | the promoted gates for `tools/gates.py run populous2` |
| `py/gen_gate.py` | `gen_land` under callcap for 30 seeds against the literal model, byte for byte, with two controls |
| `py/gen_entry.sh` | rebuilds `p2_gen_entry` (stopped at `gen_land`'s entry) from `p2_briefing` |
| `py/owned_cells.py` | settlements against the `$2f`/`$3f` cell codes, with a swapped-code control |
| `py/build_passes.sh` | snapshots between the passes of the world build, from `p2_gen_entry` |
| `py/scatter_gate.py` | the scenery scatters `$1f870` and `$1fa6c` under callcap against the model, with the stale-D2 bonus forced |
| `py/rand_gate.py` | `rand` `$215dc` against its model, 50 callcaps |
| `py/god_census.sh` | the computer god `$25652` against its controller word: three poked arms under `hits` |
| `py/fdc_files.py` | names the file behind each sector of an `ATARI_TRACE_FDC` log |
| `compilation_menu.png`, `title.png`, `briefing.png`, `zeus.png`, `game_start.png`, `game_60m.png` | the milestones (`tools/snap_render.py` of the boot and the five anchors) |

Working data (`scratchpad/populous2/`, gitignored): `src/WILD29.MSA` (the archive's content),
`wild29.st`, `files/` (extracted), `anchors/` (`scratchpad/ANCHORS.md`), `pop2_1770.bin`
(the depacked image), `pop2_all.asm`, `fdc.log`, `ev60.bin`, `calls60.txt`.

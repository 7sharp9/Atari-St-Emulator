# archipelagos: Archipelagos (Astral Software, 1989), first look

Archipelagos is an Atari ST game (the game's text credits Paul Carruthers and Ian Downend) played in first person on
islands, with an archipelago map screen as well. Its own messages show a timed, dangerous game: "SOLVED IN", and "YOU
WERE KILLED BY" a lost soul, running out of time, a twisted necromancer, a pod, quicksand and others (the full list
is under Provenance). The copy analysed is "Archipelagos+" on The Medway Boys compilation disk #58, cracked and
trained by The Mighty Clog, original supplied by Jobil.

**What this doc set has established.** This directory reaches the title, the archipelago map and first-person play,
locates the island generator and proves it: a Python model rebuilds the game's 256 x 256 island map cell for cell on
seven procedural islands and three of the twenty picture islands, from the island number and the disk alone. One creature's step and its blood footprint are modelled and gated; the other object kinds are not
decoded. The program is one hand-written 68000 image (a 50,774-byte PRG, text only, no symbol table, 0 LINK frames)
with dead instructions interleaved with the live code, so the `disassemble.py --all` listing mis-syncs in places.
Trust a live trace (`ATARI_TRACE=1` for a few hundred steps) or `callcap` over a static read.

**Where to find what.**

- How is an island's height map built? "The island generator"; which island is shown? "Island number". What are
  the picture islands? "Picture islands" (`picture_islands.png`).
- Do later islands get bigger or more joined? Can a stamp write outside the map? "Over all island numbers".
- What does the creature do and what is its blood footprint? "The creature and its blood".
- Why did the disk need two patches on this emulator, and why does it no longer? "The emulator gap and the two pokes".
- How does the game load from disk? "Disk layout, and why `extract_disk.py` is wrong for it", "Load chain".
- How do I reproduce a run? "Running it". Where is each thing in RAM? "Memory map".
- What is not yet known? "Open".

Terms used here are defined in `../GLOSSARY.md`.

Evidence is of three kinds. **Gated from this directory** (`uv run python tools/gates.py run archipelagos`, one gate,
15 s after the drive): the island model, the picture islands and disk blocks, `$16166`, the RNG. **Observed once, not gated:** the boot drive, the loader
chain, the FDC trace, the watch on the map during play. **Read from code only:** marked "(read)" or "inferred".

## Provenance

- Zip: `The Medway Boys #58.zip` (Dropbox "Daves/ST games"), 476,965 bytes, sha256
  `90b18a04e3c40df4b3a407d08b2e01f2396fb68f8d4ca57efa4579bc0e47700c`.
- It holds `TMB058.MSA`, 587,596 bytes, sha256 `fbec77b6b93cb4b3a3c8478cc2eba187b82497b1547d2a0286f9e615fcce5f3f`
  (MSA header: 10 sectors per track, 2 sides, tracks 0 to 79). `tools/msa2st.py` gives `tmb58.st`, 819,200 bytes,
  sha256 `a89528c6b5d8e28ff8437c71c6ec7c63ea4cb35e9681ee1bdda4b64025ca9b6f`. Neither is committed; both sit in
  `scratchpad/archipelagos/`.
- The disk holds four programs, not two. The menu (`AUTO\MENU58.PRG`, Automation packer v2.3r, loaded at `$a304`)
  runs on key `1` `worldcup.boy` (Trophy Soccer, from the menu text), `2` `arch.boy` (Archipelagos+), `3` `mouth.boy`
  (the menu text reads "MOUTH TRA..."; a Mouth Trap, inferred from the screenshot only) and `4` FCopy 3.0; `0` toggles
  50/60 Hz and `+`/`-` set a speed variable at `$b9b8` (menu code `$a79a..$a8be`). **Virus is not on this disk.**
- Game credits and messages (strings in RAM at `$1b580..`): "BY PAUL CARRUTHERS AND IAN DOWNEND", "CRACKED BY THE
  MEDWAY BOYS", "DEMONSTRATION VERSION", "THIS DISC IS WRITE PROTECTED", "A DISC ERROR HAS OCCURED", "SOLVED IN",
  "YOU WERE KILLED BY": a lost soul, running out of time, an arboreal tree, a twisted necromancer, a pod, a poisoned
  egg, a palm tree, your own stupidity, the quicksand, the blood of the ancients. The adjustable variables are named
  STARTING ANGLE, POISON EAT, EGG COUNTDOWN, WISP DISTANCE, POD FREQUENCY, POD OWE FREQUENCY, INITIAL PODS OWED,
  INITIAL LAND ENERGY, OVERALL TIME DELAY.

## Disk layout, and why `extract_disk.py` is wrong for it

The boot sector carries a FastCopy III BPB that claims a single-sided disk (512-byte sectors, 2 sectors per cluster,
1 reserved sector, 2 FATs of 2 sectors, 64 root entries, 800 sectors). The disk is double-sided, 80 tracks of 10
sectors. **`tools/extract_disk.py` trusts that BPB**: its file list is the directory names read through the wrong FAT
geometry, and files such as `MOUTH.BOY` come out as noise. Only `ARCH.BOY` (`601a` header, 658 bytes at image offset
`$1200`) is right. The programs are found by their `601a` headers; the ones named here are at these image offsets
(`tmb58.st`, sector-aligned):

| offset | what | size read from its header |
|---|---|---|
| `$1200` | `arch.boy`, the Archipelagos launcher | 658 |
| `$2e00` | `AUTO\MENU58.PRG` (directory entry at `$2a40`, cluster 4, 53,318 bytes) | 53,314 |
| `$1e200` | PRG, probably `mouth.boy` | 93,352 |
| `$4ba00` | PRG, probably `worldcup.boy` | 53,888 |
| `$66a00`, `$6ba00` | PRGs of 1,548 and 23,438 bytes, the second probably FCOPY_3.PRG | |
| `$7e400` | the Archipelagos game image: track 50 side 1 sector 1, `$d000` bytes read, 50,774 of them the PRG | |

Only the last two rows are used by the load chain below; the rest are identified by size and are inferred.

## Running it

From `M68000/`:

```
uv run python -I tools/msa2st.py scratchpad/archipelagos/disk/TMB058.MSA scratchpad/archipelagos/tmb58.st
bash reversing/archipelagos/py/run_drive.sh        # cold boot to gameplay, about a minute
```

`drive.txt` is the REPL script it feeds (cold boot 30,000,000 steps as the first argument, then the steps below). It
writes `boot30m`, `menu`, `k2`, `at1301c`, `p2`, `p3`, `n0`, `n2` and `m2` snapshots under `scratchpad/archipelagos/`;
the one-process drive gives snapshots byte-identical (`cmp`) to the chain of separate resumes it was first made from,
for `k2`, `at1301c`, `n0`, `n2` and `m2`. Keys are `kbd` scancodes held at least 40,000 steps (the game polls the
ACIA through its own handler `$171dc`).

| step | drive | state |
|---|---|---|
| menu splash | 20M + 20M steps from the cold boot, `kbd 3b` (any key) | menu, Crawio poll at `$a79a` |
| key `2` | `kbd 03`, 60,000 steps, `kbd 83`, 30M steps | `arch.boy` text screen, waiting for a key (`k2`) |
| any key | `kbd 39`, 60,000 steps, `kbd b9`, 100,000 steps | loader running |
| **POKE 1** | `ww 7047a 4e71`, `ww 7047c 4e71` | see "The emulator gap" |
| game entry | `bp 1301c` (1,238,371 steps) | `at1301c` |
| **POKE 2** | `ww 13578 4e71`, `ww 1357a 4e71` | the game's own loader copy |
| credits, title | 30M, 15M steps | the obelisk title, PC `$1bc6c` (`title.png`) |
| code-word screen | space, 3M steps | `n0` |
| island 1 | `kbd 02`, `kbd 1c` (a character, Return), 3M + 10M steps | the archipelago map (`n2`, `map_screen.png`) |
| play | space, 4M + 15M steps | first-person landscape, PC `$1c53e` (`m2`, `gameplay.png`) |

On the current FDC model the two pokes are no longer needed: without them the run reaches the same `at1301c` and `m2`
states (see below), and the game entry comes at 4,735,885 steps.

## Load chain

1. The menu `Pexec`s `arch.boy` (a 658-byte PRG). It prints its text screen, waits for a key (Cnecin), writes
   `bra.s $60066` over `$60046` and jumps to `$6001e`.
2. Its text screen has loaded the boot sector of track 0 side 1 to `$60000` and track 1 side 1 (10 sectors) to
   `$70000`. `$6001e` writes the marker `$98765432` at `$70000` and jumps to it (the marker decodes as a harmless
   `sub.w`); the code behind it is a raw FDC loader: `$70506` dispatches commands, `$7040c` loads file *k* from the
   table at `$703fc`, `$70374` is a PRG relocator, `$7029a` reads a track and tests it (a protection probe whose result
   only clears `$43e`).
3. The table holds two files: index 1 = track 39 side 1, `$7d00` bytes, to `$3000` (the obelisk title picture);
   index 0 = track 50 side 1, `$d000` bytes, to `$13000` (the game). The relocator patches it and the loader jumps to
   `$1301c`, which sets `A7 = $2ff0` and jumps to `$1b9ea`.
4. The game then loads more files through its own copy of the loader (`$13506`, called from `$1d0d8`): the pictures and
   data, and later the island files (`$1b142`, below).

## The emulator gap and the two pokes

**What the loaders do.** Each read command programs the DMA sector count to 12 (`move.w #$c,D7` at `$705e2`) on a track of
10 sectors, starts a multi-record Read Sector, and waits until the DMA address has advanced by the byte count it
wants, then writes Force Interrupt (`$d0`). It then reads the status register and tests it with `cmpi.b #$80,D0 /
bne` (`$70476`, and the same pair in the game's copy at `$13574`): a good transfer must read back exactly `$80`. Any
other status takes a retry path (five tries) and then gives up with the file partly read.

**What the emulator returns.** The FDC models the WD1772's search past the last sector and its motor-on bit
(`DEVELOPING.md`, "Busy search and the motor-on bit"): the ten sectors transfer at once, the command then stays busy
for 5 revolutions looking for sector 11, and the loader's Force Interrupt inside that window ends it with busy cleared
and no error, so the status reads `$80` (FDC trace: `READ-SECTOR multi=true count=12 transferred=10 status=$01`, then
`FORCE-INTERRUPT busy=true status=$00`, once per track from 39 on, 35 in all to the game's entry, no retry). The
loader's `$70790` (and the game's `$13a36`) waits for the motor-on bit to drop, so the load to `bp 1301c` takes
4,735,885 steps where the poked run on the older FDC took 1,238,371.

**The pokes are no longer needed.** Proven with `drive.txt` run twice on the same build, once as written and once with
its four `ww` lines removed: both reach `bp 1301c` after 4,735,885 steps, the title (`p3`) and the first-person view
(`m2`, PC `$1c534`). `at1301c` differs only in the four POKE 1 bytes at `$7047a`; `m2` differs only in the four
POKE 2 bytes at `$13578` and five bytes in `$2f43..$2f49`, below the stack pointer (`$2fdc`): RAM differences inside
those ranges 4/4 and 9/9 (`py/gate_unpoked.py`, gate `unpoked`). Before this FDC model
the unpoked run ended in an `ILLEGAL` opcode `$2e7d` at `$1301c` (the PRG partly read, the relocator patching the
wrong bytes, a double bus fault), and the pokes below were what got past it. The snapshots under
`scratchpad/archipelagos/` were made with the pokes on the older FDC.

**The pokes** (`ww` is a word write; each replaces a 4-byte `bne` with two NOPs, so the retry path is never taken):

- POKE 1: `ww 7047a 4e71` and `ww 7047c 4e71` once the track-1 code is in RAM (100,000 steps after the key release).
- POKE 2: `ww 13578 4e71` and `ww 1357a 4e71` at the game's entry (`bp 1301c`), after the relocator has run.

**Not explained:** text on the code-word screen and the map screen still renders as coloured noise in the PNGs, with
both pokes in place. The glyph routine `$18c68` is correct on the credits screen. The cause is open (the font source is
not at `$78000`: that address is zero when the game starts, and the `$78000 + $3c00` copy in `$1ba8e` that an earlier
read suggested is not established).

## Memory map (read, from the loader chain and the code)

| address | content |
|---|---|
| `$3000..$12fff` | the island map, 256 x 256 bytes, index `y*256 + x`; also the title picture at load (the map build clears it) |
| `$13000..$1f656` | the game image (`$1301c` entry; relocated, with live code at `$1b9ea` and the data tables above it) |
| `$16978..$169a3` | island parameter block (21 words) and RNG seed; `$1697a..$16988` counts and thresholds, `$1698a` build seed |
| `$1698c`, `$16a32..$16a36`, `$16a42` | per-iteration range table (four 6-byte entries), range state, the eight neighbour offsets |
| `$16a58` | special-island table (20 rows `N, track, sector`; an island whose number is in it is a picture, "Picture islands") |
| `$1d566` | island number N |
| `$1db28..$1db36` | eight object-kind count words; `$1db28` is the kind-8 creature count ("The creature and its blood") |
| `$1db3e`, `$1db7e`, `$1dbbe` | the creature block, 32 words each: phase, position, envelope output |
| `$1dbfe` | the visible-cell list the renderer uses |
| `$1defe` | an island's parameter file as loaded from the disk |
| `$1e0fe` | the ring queue of the fill (1,024 bytes) |
| `$70000`, `$78000`, `$3000`/`$b000` | screens (the title uses `$3000` and `$b000`; the other screens `$78000`) |

## The island generator

**Heightfield.** One island at a time, in the 64K at `$3000`: sea 4, coast 5, interior 6 or 7 as a checkerboard.
`$15a20` builds it. Entry: if N (`$1d566`) is in the special table `$16a58` the island is a picture ("Picture
islands"). Otherwise (`$15a82`) the map is cleared to 4, then for `P[$1697a]` iterations:

1. `$16062` finds the iteration in the four-entry range table at `$1698c` and sets the start ranges.
2. A start position and a size come from the RNG: position `((rand * W34 / 255) << 8) | (rand * W32 / 255)` plus the word
   `W36`; size `D4 = ((rand * P_c / 255) << 8) | (rand * P_e / 255)`, with `P_c = [$1697c]`, `P_e = [$1697e]`.
3. `$15b90` draws a percentage and compares it with `[$16988]` to set a flag (when it is set, a stamp ignores the
   neighbour test), draws a second one, and chooses a stamp: below `[$16980]` the walk, below `[$16982]` the wander,
   below `[$16984]` the circle, else the rectangle.
   - Walk `$15c00`: `D4 >> 8` random walks of `D4 & $ff` steps from the same start (steps left, right, up, down chosen
     by the seed's range), each cell set to 6; a walk stops when the new cell touches finished land.
   - Wander `$15cb8`: `(((D4 & $ff) + (D4 >> 8)) & $ff) * 8 + 300` stamps along a walk that never repeats its previous direction.
   - Circle `$15d94`: a midpoint-circle outline with the radius from `D4` clamped to 4..25, outline bit `$40`, then the fill.
   - Rectangle `$15eee`: an outline of the half-sizes of `D4`, then the fill.
   - The fill `$15e3a` floods the interior (ring queue `$1e0fe`, cardinal neighbours, bit `$20` visited) and sets a cell
     to `v | 6` only if no neighbour has bit 7.
   - A finished walk or wander sets bit 7 on every non-sea cell; a finished circle or rectangle first clears bits 5 to 7
     over the whole map, then sets bit 7 again.
4. The final pass `$15b16..$15b8e` keeps `value & 7`, turns a 6 with a sea neighbour (left, right, above, below) into
   5, and gives every other 6 the checkerboard value 6 or 7.

**RNG** `$16622`: `s = 5s + 1 (mod 65536)`, the seed at `$16978`; `$16050` scales the seed's low byte, `(s & $ff) * m /
255`.

**Proof.** `py/island_model.py` takes the parameter block from a snapshot at the `$15a20` entry and compares the model's
map with the game's at the `$15b8e` return. `bash reversing/archipelagos/py/run_gate.sh` re-captures and prints:

| island | cells matched | control (RNG step + 1) |
|---|---|---|
| island 1, from the disk | 65536/65536 | 64370/65536 |
| parameter block poked to the "ADJUST VARIABLES" defaults (`001e 006e 0037 001e 0041 005a 0064 0032 04d2`; poke) | 65536/65536 | 62996/65536 |
| block poked to `0019 0096 0040 0014 0040 005a 0064 0028 1234` (poke) | 65536/65536 | 62371/65536 |
| N = 150, computed (number poked, see below) | 65536/65536 | 58982/65536 |
| N = 4321, computed (number poked) | 65536/65536 | 61646/65536 |

Two more islands take their block from the disk with the number poked at the loader `$1b142` ("Island number"):
N = 6 and N = 99, 65536/65536 each (`py/gate_pictures.py`). Stamp coverage over the seven islands: all four stamp
shapes occur (island 1 only the walk; the defaults run walk 7, wander 16, circle 5, rect 2; N = 150 walk 9, wander 13,
circle 9, rect 4; N = 99 walk 26, wander 38, circle 2, rect 4). A model gate compares only what the build writes (`$3000..$12fff`), not the registers.

**RNG gate** (`py/gate_rng.py` on the `watch 16978` log of island 1's build): 11792/11792 successive seeds obey
`s = 5s + 1` (11791 pairs between the `$16632` writes plus the seed load at `$15a96`); the control `s = 5s + 2` gives
0/11792.

**What the large cell values are.** The builder writes only 4, 5, 6 and 7. In the running game a cell also carries flag
bits: `$1c576` clears bit 7 of each visible cell and records it in the list at `$1dbfe`, and `$1c2c2` toggles it back
(4,072 and 4,071 writes in 60M idle steps, from the `watch 3000 65536` run); `$19faa` writes `D1 | $a0`, an object
marker (inferred). So values such as 130, 166, 198, 199, 242, 243 are a low 3 bits value of 2, 3, 6 or 7 with bit 7 and
the marker bits set.

## Picture islands

The special table `$16a58` holds 20 six-byte rows, `N, track, sector`, for N = 5, 10, 15, ..., 100 (read from the
table in RAM), from track 13 sector 1 to track 20 sector 7, four sectors apiece. For such an N, `$15a38` reads `$800`
bytes from there through the game's loader `$134f8` into the buffer at `[$1d55e] ^ $8000` (`$70000`, a screen).
`$160c8` clears the map to 4 and draws the buffer as a 128 x 128 one-bit picture, most significant bit first, in the
centre of the map (row 64, column 64; a set bit is 6, a clear bit 4); a failed read takes `$160b4` instead and leaves
the map all sea. Then the procedural path's final pass `$15b16` adds the coast and the checkerboard. So the pictures
are drawn land masks, not parameter sets, and nothing random touches them.

The game's track T is cylinder T, side 1, of `tmb58.st` (the load chain reads its files from side 1 the same way):
island 1's parameter block, track 2 sector 1, is image sector 50. The twenty pictures are, by eye, a wheel (5),
a map captioned "East Enders" (10), Great Britain (15), a pig marked out in "bacon cuts" (20), Europe (25), a
home computer with a smiling screen, joystick and mouse (30), a turtle (35, the Logotron logo the reviews name), a
winding track (40), a coat of arms (45), the Americas (50), a portrait under "ПЭРЭСТРОИКА" (55), roses (60), a
diamond lattice (65), five land masses joined by dotted lines (70), concentric rings (75), a speckled streak (80),
"WANTED DEAD OR ALIVE ... TONY'S BARBER" (85), a square maze (90), an X of islets (95) and a figure of islets (100).
`picture_islands.png` draws them as the model builds them (`py/render_pictures.py`, the centre 150 x 150 cells).

Each picture island also has a parameter-block slot on the disk (it loads one like any N up to 100; the builder
does not use its stamp fields). All 20 blocks that equal an earlier island's are in these slots or copy one (for
example 10's equals 1's, 99's equals 95's slot); the 80 procedural islands' blocks are all different.

**Gate** (`py/capture_pictures.sh`, then `py/gate_pictures.py`, from `n0.snap` with N poked at `$1b142`):

| island | map cells | buffer bytes vs the side-1 read | control: next picture / side 0 |
|---|---|---|---|
| 15 | 65536/65536 | 2048/2048 | 60012 / 56331 |
| 25 | 65536/65536 | 2048/2048 | 55989 / 53983 |
| 85 | 65536/65536 | 2048/2048 | 56880 / 57195 |

and for the disk blocks: N = 6 and N = 99 load 21 of 21 words equal to `disk_block` (control, the block of N - 1: 5
and 15 of 21), and the model run on the block read from the disk gives 65536/65536 on both.

## Island number

`$1b33a: cmpi.w #$64,$1d566 / ble $1b34e`: islands 1 to 100 load their parameter block from the disk (`$1b142`: track
`(N-1)/10 + 2`, sector `(N-1)%10 + 1`, `$200` bytes to `$1defe`; `$1c700` copies the 21 words, byte-swapped, into
`$1697a`). Above 100, `$1611e` calls `$16166`, which computes the block from N alone: seed `4N + $1388`, then draws
through the same `s = 5s + 1` for the count `rand * 40 / 255 + 20`, `P_c = rand * 100 / 255 + 100`, `P_e = P_c / 2`,
thresholds `rand * 32 / 255 + 15` accumulated three times (the last capped at 100), `[$16986] = 100`, `[$16988] = rand *
80 / 255 + 10`, and `[$1698a] = 4N + $3039`. It then writes the range table (`$16222..$16272`, read): one entry, keyed
to iteration 1, whose x and y ranges are both `3 * count - 20` and whose offsets are `(255 - range) / 2`, so every
stamp of an island above 100 starts in a centred square of side 40 to 160 (the other three keys are 0 and never
match). The range state left from the previous island is overwritten at iteration 1, so the island is a function of
N alone.

**Gate** (`py/gate_params.sh`, `island_params.py`): the model gives 9 of 9 fields for N = 150 and 9 of 9 for N = 4321;
control (seed + 1) 2 of 9 for each. N is reached by a poke of `$1d566` on the map screen (`ww 1d566 0096`, `ww 1d566
10e1`), then space, not by a played selection; how a played game changes N on the map screen is not driven. That
poke is too late for N up to 100: `$1b142` has already loaded island 1's block into `$1defe`, and `$1c700` copies
that one (a map-screen poke of 6 rebuilds island 1). `py/capture_pictures.sh` pokes N at the entry of `$1b142`
instead, after the code-word screen.

## Over all island numbers (model census, checked live on 42 islands)

`py/census.py` runs the model for every N from 1 to 9,999 from the disk image and `isl/ent1.snap` alone (about 6 min
on 10 cores; `--summary` reprints from `scratchpad/archipelagos/census/census.json`). The census is a model result.
`py/gate_census_live.py` checks its three findings in the emulator: the game builds 42 islands under `stserver`
(N > 100 poked at `$1d566` on the map screen, `n2.snap`; N up to 100 poked at the `$1b142` entry from `n0.snap`),
each from the `$15a20` entry to the `$15b8e` breakpoint, 42 of 42 reached, and the model runs on each entry
snapshot. Its output is in `scratchpad/archipelagos/census_live/gate.log`; it runs in the `islands` gate (about 2 min).

- **No writes outside the map.** The circle and rectangle stamps address the map with 16-bit signed offsets that can
  leave it, but in the model none of the 9,979 procedural islands changes a byte outside `$3000..$12fff`: by the
  range tables every stamp starts at least 31 cells from an edge (island 81's table; 32 in the stamps it draws;
  above 100 the range square keeps them 49 or more from it; `census.py --edges`), and the largest stamp has radius 25.
  **Live, 11 of 11 islands**: 150, 4321, the largest stamp counts above 100 (145 and 132, 59 stamps, which also
  gives the largest start squares), the largest stamp sizes `P_c` (140 and 163, 199 and 198), 119, and the disk
  islands whose stamps start nearest an edge in the model (81, 93, 28 at 32, 37 and 49 cells; 79, a circle at 59;
  `census.py --edges`), each under write watches on
  `$1700..$2fff` and `$13000..$148ff` (no event dropped). The builder's code is `$15a20..$1663f`: its procedural
  path calls nothing outside it (read; the two calls out, `bsr $134f8` and `jsr (A0)`, are on the picture path). On
  none of the 11 does it make a byte write in either range; all its writes there (71,130 to 329,543 per island) are
  word pushes into its own stack below the entry SP (`$2fce..$2fe3`; `$2fd2..$2fe7` on the disk islands, whose SP is
  `$2fe8`). Its other state (the seed `$16978`, the work words `$16a30..$16a52`, the ring queue `$1e0fe`) lies
  outside both ranges. The remaining writes in the ranges come from 65 to 68 PCs outside the builder, every one of
  which also writes there in an idle window as long as the longest build (14,883,706 steps, no input) on the map
  screen or the code-word screen; each (PC, address) pair the idle windows lack is a stack address (`$2f82..$2fde`).
  That is interrupt-time code pushing onto the builder's deeper stack. Control, the same harness: island 150 with
  the range table `$1698c` poked to `03 ff 00 00` and the thresholds `$16980/2/4` to 0, 0, 100 at the `$15a20` entry
  (stamps on rows 0..3, all circles; poke). The builder then makes 361 byte writes outside the map at 355 addresses,
  `$17d6..$130fd`, from the circle outline (`$15e0c..$15e34`) and the fill (`$15e90`). The first 71 equal the
  model's out-of-map writes in order. Write 72 (`$2fd6`, the fill) is the first into the builder's own pushes, so from
  there the flood follows the live stack, which the model's entry copy does not hold, and the game halts on a double
  bus fault after 8,329,623 steps, before `$15b8e`. The model, run to the end, makes 1,820 writes outside the map
  (from `census.py`'s RAM it changes 1,503 bytes, `$1708..$130fd`).
- **64 parameter sets above 100.** `$16050` scales only the seed's low byte, and the low byte of `s = 5s + 1 mod
  65536` depends only on the low byte before it; the seed `4N + $1388` therefore gives the same nine fields for N and
  N + 64, and islands 101 to 9,999 have 64 distinct parameter sets (model). The islands still differ: the build seed
  `4N + $3039` differs, and the walks take their directions from the seed's top two bits. **Live, 4 pairs**
  (150/214, 4321/4385, 9000/9064, 1000/1064): the 21 words at `$1697a` at the `$15a20` entry agree in 20 of 21,
  differing only in `$1698a`, the build seed; the game's maps agree in 58,923, 62,272, 51,494 and 52,953 of 65,536
  cells; the model matches all eight maps 65536/65536. Land overlap (cells land in both over cells land in either,
  model) is 0.36 to 0.46 for N against N + 64k (1000/1064, 1000/1128, 1000/1192, 5000/5064), against a median of
  0.36 (maximum 0.56) for N against N + 1 over 1000..1062.
- **No progression after 100.** Medians over the procedural islands (model):

| islands | stamps | land cells | land pieces (4-connected) | largest piece |
|---|---|---|---|---|
| 1-20 | 10 | 1,542 | 1.5 | 1,287 |
| 21-40 | 21 | 3,285 | 14 | 788 |
| 41-60 | 35 | 4,141 | 23.5 | 730 |
| 61-80 | 35 | 4,465 | 22 | 796 |
| 81-100 | 30.5 | 4,618 | 24.5 | 918 |
| 101-1,000 | 40 | 7,361 | 27 | 1,648 |
| 1,001-3,000 | 39.5 | 7,264 | 26 | 1,629 |
| 3,001-6,000 | 39 | 7,284 | 26 | 1,652 |
| 6,001-9,999 | 40 | 7,256 | 27 | 1,635 |

  The hand-set blocks of 1 to 100 ramp from one small island to about 25 pieces; island 101 steps to about 11% of
  the map as land, and from there the figures are flat. The share of stamps allowed to touch finished land
  (`[$16988]`) has a median of 80% over islands 1 to 20 and about 50% over the later disk islands; above 100 it is
  10% to 89% by N with no trend. What else grows with N in play (creatures, timers) is not decoded.
  **Live sample, 25 of 25** islands match the game's map 65536/65536: five per range above 100 (213, 270, 358, 545,
  682; 1590, 2126, 2445, 2688, 2871; 3323, 4065, 4255, 5113, 5965; 6497, 8764, 9238, 9459, 9845; drawn with seed
  1989) and five disk islands that are not pictures (23, 47, 48, 78, 89). With the islands of the two findings above,
  42 of 42 live builds match (stamps over them: walk 640, wander 586, circle 369, rect 123). The medians themselves
  are model figures over all 9,999.

## The code-word screen

After the title, space leads to a screen that reads typed text (a field limited to 12 characters by `cmp.w #$c,D7` at `$1bdb4`; read) and compares it
with a word (`$1bdda..$1bf1a`); on a pass `$1bf32` writes `1` into `$1d566` and the game moves on to the map. Typing
`1`, `2` or `3` then Return all give N = 1 (the parameter blocks of the three captures are identical): the screen is not an
island-number prompt. What it compares against, and whether any text passes, is not established. The screen's text
renders as noise (see the emulator gap).

## The creature and its blood (modelled and gated; the 300 states are poked)

`$1a4e0` (`object_step_loop`, called from the main loop at `$1bf3e`, about every 91,000 to 120,000 steps) is a creature's
per-call tick. The creature leaves the red ground (the blood) behind it as a footprint; the object itself is not the
blood. Object block, one word per object (32 slots): `$1db3e+2i` the phase, `$1db7e+2i` the position (high byte y, low
byte x, cell address `$b000 + sext16(pos)`, so map index `$8000 + pos`), `$1dbbe+2i` an envelope output; `[$1db28]` is the
count (1 in `m2`), the first of eight count words `$1db28..$1db36` that the eight kind handlers at `$1c99a` fill from the
level block `$1df3e` (read: the other kinds are not decoded).

- **Phase tick** (`$1a4f8`): the word at `128(A2)` is set to `[$1d2a0 + phase]` (`$1d2a0` is a 168-word envelope, 0 up to
  `$ffff` and back to 0), the phase advances by 2, and only at `$150` does the object step and the phase return to 0.
  That is 168 calls per step, about 16.1M steps, and the three events in the earlier 60M idle run (16.13M apart) are
  that period.
- **Cell choice** (`$1a50a`): for shift k = 3, 4, 5 the candidate moves toward the player (the bytes `$1d698` y and `$1d696`
  x) by `-((byte difference) >> k)` per axis, an arithmetic byte shift, so a small positive difference gives no move and a
  negative one gives 1. The first cell passing `(v ^ $80) & $82 == $82` (bit 1 set, bit 7 clear) is taken: the candidate
  itself, then its neighbours in the order -257, -256, -255, +1, +257, +256, +255, -1. If all three rounds fail the
  creature stays. From the second round the x difference register D4 is the cell test's scratch, so the x shift uses
  `(cell(-1) ^ $80) & $82` of the last cell tested, not the difference.
- **Move** (`$1a630`): the old cell becomes `v & 7`, the new cell `(v & $0f) | $80`, the position word is stored.
- **Sound** (`$1a64a`, inferred from the call, not driven): within |dx| + |dy| < 15 of the player it calls `$13b2e` with
  `[$1b994 + dist]`.
- **Footprint** (`$1a692`, `$1a6c4`): the new cell and its four cardinal neighbours each lose 4 when `v & 7 > 4`
  (5, 6, 7 become 1, 2, 3). One step writes 8 bytes (old cell, new cell twice, five footprint writes) to 6 distinct cells.

Proof, both against the emulator and with the model in `py/creature/creature_model.py` (`bash py/creature/run_gate.sh`,
gate `creature`; each script captures `scratchpad/archipelagos/creature/entry.snap`, `m2` stopped at its first `$1a4e0`
call):

- `gate_creature.py 300`: 300 of 300 states match. Each state is **poked**: the whole object block (1 to 32 objects, phases
  mostly `$14e`, random land positions), the player bytes and often random map cells, then `callcap 1a4e0`; the model sees
  only the poked RAM and the compared bytes are the map and the object block. 2,434 stepping events, 7,351 changed map
  bytes; every neighbour offset in all three rounds and the stay case occur. Controls (last argument): `order` 184/300,
  `shift` 58/300, `lim5` 86/300, `nofoot` 12/300, `noclobber` 179/300.
- `gate_creature_idle.py 40`: ordered 8-write sequences from a `watch 3000 65536` log against the model fed the snapshot
  at the call entry. **Only 2 natural events** occur in 40M unpoked steps (steps 217,748,727 and 233,879,051), model 2 of
  2, and the controls also pass those two (they cannot tell a wrong model apart); 40 of 40 events with the phase and the
  position **poked** before each call (the creature reaches the player after about 5 natural steps and the loop then
  stops being called: after the 40th poked event the game was in the island builder, cause not investigated). Controls:
  `order` 38/40, `lim5` 27/40, `shift` 7/40. A poke changes the rate (one step per call against one per 168), not the
  8-write pattern.

The red ground is the footprint: the `m2` map holds 64,471 cells of 4, 1,045 of 5 to 7 and exactly 10 of 2 or 3 (two
footprints); poking those 10 back to 6 and 7 removes the red patch from the frame after 1.5M steps (one same-snapshot pair,
not a counted gate; 120k steps shows no change). A frame diff of `m2`'s first call with and without the poke
`ww 1db3e 014e` differs only in an 18 x 13 pixel box holding the creature sprite, 136 pixels. Read only: the spawn handler
`$1c7e8` stores `$1db7e[i]`, sets bit 7 and clears bit 2 on the cell and its four neighbours; `$19532` recomputes bit 7 of
every cell as `(v & $70) != 0` and then sets it at every object's cell, which is why an occupied cell is refused as a
target. Not established: that the sprite is drawn from `$1db7e` (poking `$1db7e` replaces it with a black pillar, poking
the count to 0 changes nothing within 120k steps), what reads the envelope `$1dbbe`, what the other seven kinds are, and
what happens to the player when the creature arrives.

## Open

- The garbled text on the code-word and map screens, and what the code word is.
- How the map screen sets N in play.
- The other seven object kinds (counts `$1db2a..$1db36`, handlers `$1c99a`: trees, pods and the necromancer are
  candidates, not matched), what reads the creature's envelope `$1dbbe`, and the sprite's link to `$1db7e`.
- The land generator of the 3D view (how the landscape patchwork is drawn from the map).

## Files

| file | what |
|---|---|
| `drive.txt`, `py/run_drive.sh` | the cold boot to gameplay drive and its runner (both pokes) |
| `py/gate_unpoked.py` | `drive.txt` with and without its pokes from a cold boot; RAM differences of `at1301c` and `m2` against the poke ranges; output under `scratchpad/archipelagos/gate_unpoked/` |
| `py/island_model.py` | the island builder model (map out; parameter block, or the picture read from the disk image, in); `disk_read`, `disk_block`, `picture_bits` |
| `py/island_params.py` | the `$16166` parameter model |
| `py/capture_islands.sh` | fresh entry and exit snapshots and the RNG watch log (pokes: parameter sets, `$1d566`) |
| `py/gate_islands_only.sh`, `py/gate_params.sh`, `py/gate_rng.py`, `py/run_gate.sh` | the gates; `run_gate.sh` runs all |
| `py/creature/creature_model.py` | model of the creature tick `$1a4e0` and its footprint, plus `capture_entry()` |
| `py/creature/gate_creature.py`, `py/creature/gate_creature_idle.py`, `py/creature/run_gate.sh` | the callcap gate (300 poked states) and the watch-log gate (2 natural, 40 poked events); `run_gate.sh` runs both |
| `py/capture_pictures.sh`, `py/gate_pictures.py` | captures of islands 15, 25, 85, 6, 99 (N poked at `$1b142`) and their gate: picture path, buffer, disk blocks |
| `py/census.py` | the model over N = 1 to 9,999: out-of-map writes (with an edge control), parameter sets, N vs N + 64, medians by range; `--edges`, how near an edge the stamps start |
| `py/gate_census_live.py` | the census findings in the emulator (`stserver`): write watches outside the map on 11 islands plus the poked edge control, the `$1697a` block and maps of 4 N / N + 64 pairs, and the model against 42 live maps; output under `scratchpad/archipelagos/census_live/` |
| `py/render_pictures.py` | draws `picture_islands.png` from the model and the disk image |
| `picture_islands.png` | the 20 picture islands as the game builds them |
| `py/render_buf.py` | render a 320 x 200 screen at an explicit buffer base |
| `gates.toml` | the gates for `tools/gates.py` (`islands`, `creature`, `unpoked`; PASS 134 s, 14 s and about 70 s) |
| `archipelagos.sym` | names, one per line |
| `title.png` | the title screen (obelisk, berry trees) |
| `map_screen.png` | the archipelago map after the code-word screen (text noisy) |
| `gameplay.png` | first-person play: obelisk, palm tree, blood at the right, crosshair |
| `island_defaults_model.png` | the model's island for the "ADJUST VARIABLES" defaults (poked block), identical to the game's |

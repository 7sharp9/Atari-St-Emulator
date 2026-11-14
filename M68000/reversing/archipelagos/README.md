# archipelagos: Archipelagos (Astral Software, 1989), first look

Archipelagos is on The Medway Boys compilation disk #58 as "Archipelagos+", cracked and trained by The Mighty Clog,
original supplied by Jobil. The game's text credits Paul Carruthers and Ian Downend. This directory reaches the title,
the archipelago map and first-person play, locates the island generator and proves it: a Python model rebuilds the
game's 256 x 256 island map cell for cell on five islands (see "The island generator"). The blood and the moving
creatures are read, not modelled.

The engine is one hand-written 68000 image (a 50,774-byte PRG, text only, no symbol table, 0 LINK frames) with dead
instructions interleaved with the live code, so the `disassemble.py --all` listing mis-syncs in places. Trust a live
trace (`ATARI_TRACE=1` for a few hundred steps) or `callcap` over a static read.

Evidence is of three kinds. **Gated from this directory** (`uv run python tools/gates.py run archipelagos`, one gate,
15 s after the drive): the island model, `$16166`, the RNG. **Observed once, not gated:** the boot drive, the loader
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

Without the two pokes the run does not get past the loader (see below).

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

**What the emulator returns.** `MMU.fs` runs a read command to completion in one write: ten sectors transfer, the
eleventh finds no sector and the status is `$10` (Record Not Found), with no motor-on bit 7 ever set; Force Interrupt
then sets status 0 (FDC trace: `READ-SECTOR multi=true count=12 transferred=10 status=$10`, then `$d0`, over and over
for track 39 and then track 50). The test fails, the loader retries and gives up, the PRG is partly read, the
relocator patches the wrong bytes and the game dies on an `ILLEGAL` opcode `$2e7d` at `$1301c` (vector 4, TOS bombs,
double bus fault). Without POKE 2 only the credits screen is clean text: the font and later pictures never load.

**Real-hardware behaviour (inferred, not checked):** the controller is still reading when the loader's Force Interrupt
arrives about 10 sectors in, well before the roughly second-long Record Not Found timeout, so the status the loader
reads is `$80` (motor on, no error). The loader relies on that timing.

**The pokes** (`ww` is a word write; each replaces a 4-byte `bne` with two NOPs, so the retry path is never taken):

- POKE 1: `ww 7047a 4e71` and `ww 7047c 4e71` once the track-1 code is in RAM (100,000 steps after the key release).
  Controlled by the same snapshot with and without the poke: unpatched the run ends in the double bus fault, patched it
  reaches the title.
- POKE 2: `ww 13578 4e71` and `ww 1357a 4e71` at the game's entry (`bp 1301c`), after the relocator has run. Same
  snapshot (`at1301c`) with and without: the credits text is readable with it (`p2` shows "ARCHIPELAGOS / BY PAUL
  CARRUTHERS / AND IAN DOWNEND / PLEASE WAIT / CRACKED BY THE MEDWAY BOYS") and garbled without it.

Nothing in this directory that follows the title is a played result in the sense that it needs these pokes. An emulator
change that ends such a read at `$80` would make both unnecessary; it is not made here.

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
| `$16a58` | special-island table (word keys, six bytes apiece; an island whose number is in it takes a picture path, not modelled) |
| `$1d566` | island number N |
| `$1db28`, `$1db3e` | object count and table (the moving creatures, below) |
| `$1dbfe` | the visible-cell list the renderer uses |
| `$1defe` | an island's parameter file as loaded from the disk |
| `$1e0fe` | the ring queue of the fill (1,024 bytes) |
| `$70000`, `$78000`, `$3000`/`$b000` | screens (the title uses `$3000` and `$b000`; the other screens `$78000`) |

## The island generator

**Heightfield.** One island at a time, in the 64K at `$3000`: sea 4, coast 5, interior 6 or 7 as a checkerboard.
`$15a20` builds it. Entry: if N (`$1d566`) is in the special table the island comes from a picture. Otherwise
(`$15a82`) the map is cleared to 4, then for `P[$1697a]` iterations:

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

Stamp coverage over the five islands: all four stamp shapes occur (island 1 only the walk; the defaults run walk 7,
wander 16, circle 5, rect 2; N = 150 walk 9, wander 13, circle 9, rect 4). The model does not cover the special-island
picture path. A model gate compares only what the build writes (`$3000..$12fff`), not the registers.

**RNG gate** (`py/gate_rng.py` on the `watch 16978` log of island 1's build): 11792/11792 successive seeds obey
`s = 5s + 1` (11791 pairs between the `$16632` writes plus the seed load at `$15a96`); the control `s = 5s + 2` gives
0/11792.

**What the large cell values are.** The builder writes only 4, 5, 6 and 7. In the running game a cell also carries flag
bits: `$1c576` clears bit 7 of each visible cell and records it in the list at `$1dbfe`, and `$1c2c2` toggles it back
(4,072 and 4,071 writes in 60M idle steps, from the `watch 3000 65536` run); `$19faa` writes `D1 | $a0`, an object
marker (inferred). So values such as 130, 166, 198, 199, 242, 243 are a low 3 bits value of 2, 3, 6 or 7 with bit 7 and
the marker bits set.

## Island number

`$1b33a: cmpi.w #$64,$1d566 / ble $1b34e`: islands 1 to 100 load their parameter block from the disk (`$1b142`: track
`(N-1)/10 + 2`, sector `(N-1)%10 + 1`, `$200` bytes to `$1defe`; `$1c700` copies the 21 words, byte-swapped, into
`$1697a`). Above 100, `$1611e` calls `$16166`, which computes the block from N alone: seed `4N + $1388`, then draws
through the same `s = 5s + 1` for the count `rand * 40 / 255 + 20`, `P_c = rand * 100 / 255 + 100`, `P_e = P_c / 2`,
thresholds `rand * 32 / 255 + 15` accumulated three times (the last capped at 100), `[$16986] = 100`, `[$16988] = rand *
80 / 255 + 10`, and `[$1698a] = 4N + $3039`.

**Gate** (`py/gate_params.sh`, `island_params.py`): the model gives 9 of 9 fields for N = 150 and 9 of 9 for N = 4321;
control (seed + 1) 2 of 9 for each. N is reached by a poke of `$1d566` on the map screen (`ww 1d566 0096`, `ww 1d566
10e1`), then space, not by a played selection; how a played game changes N on the map screen is not driven.

## The code-word screen

After the title, space leads to a screen that reads typed text (a field limited to 12 characters by `cmp.w #$c,D7` at `$1bdb4`; read) and compares it
with a word (`$1bdda..$1bf1a`); on a pass `$1bf32` writes `1` into `$1d566` and the game moves on to the map. Typing
`1`, `2` or `3` then Return all give N = 1 (the parameter blocks of the three captures are identical): the screen is not an
island-number prompt. What it compares against, and whether any text passes, is not established. The screen's text
renders as noise (see the emulator gap).

## The blood (read, not modelled; inferred)

From `m2` with the game left alone for 60M steps, `watch 3000 65536` logged 8,172 writes: 4,072 and 4,071 render
toggles (`$1c576`, `$1c2c2`), 5 `$19faa` marks, and three events from `$1a634..$1a6de` at steps 217,748,727,
233,879,051 and 250,006,081 (16.13M steps apart; whether that is a timer is not checked). Reading `$1a4e0..$1a6be` and
`$1a6c4`: a loop over `[$1db28]` objects (table `$1db3e`, a position byte pair per object at 64(A2) and 65(A2)) steps each
toward the player (`$1d696`, `$1d698`) by a shift-and-subtract, trying neighbour cells in the order -257, -256, -255, +1,
+257, +256, +255, -1 and taking the first whose value passes `(v ^ $80) & $82 == $82` (land with bit 1 set and bit 7
clear). The old cell becomes `v & 7`, the new cell `(v & $0f) | $80`, and the new cell and its four cardinal
neighbours each lose 4 when `v & 7 > 4` (land 6, 7 or 5 becomes 2, 3 or 1: the red blood). Each of the three events wrote
the old cell `3`, the new cell `7 -> $87 -> $83` and four neighbours `2`, and the position moved by `+$101` each time
(`$a085 -> $a186 -> $a287 -> $a388`): 3 of 3 fit. In the 60M snapshot the map holds 11 cells of 2 and 8 of 3. Not
established: the direction choice, the timer, and whether these objects are the blood itself or another creature.

## Open

- The garbled text on the code-word and map screens, and what the code word is.
- The emulator gap: an FDC read that a Force Interrupt ends at status `$80` would remove both pokes.
- The special-island table at `$16a58` and its picture path; how the map screen sets N in play.
- A model of one blood step (direction choice, timer), gated by a watch log; then the trees, pods and the necromancer
  (object table `$1db3e`, per-tick routine `$1a4e0`; their records and kinds are not decoded).
- The land generator of the 3D view (how the landscape patchwork is drawn from the map).

## Files

| file | what |
|---|---|
| `drive.txt`, `py/run_drive.sh` | the cold boot to gameplay drive and its runner (both pokes) |
| `py/island_model.py` | the island builder model (map out, parameter block in) |
| `py/island_params.py` | the `$16166` parameter model |
| `py/capture_islands.sh` | fresh entry and exit snapshots and the RNG watch log (pokes: parameter sets, `$1d566`) |
| `py/gate_islands_only.sh`, `py/gate_params.sh`, `py/gate_rng.py`, `py/run_gate.sh` | the gates; `run_gate.sh` runs all |
| `py/render_buf.py` | render a 320 x 200 screen at an explicit buffer base |
| `gates.toml` | the one gate for `tools/gates.py` (PASS 15 s) |
| `archipelagos.sym` | names, one per line |
| `title.png` | the title screen (obelisk, berry trees) |
| `map_screen.png` | the archipelago map after the code-word screen (text noisy) |
| `gameplay.png` | first-person play: obelisk, palm tree, blood at the right, crosshair |
| `island_defaults_model.png` | the model's island for the "ADJUST VARIABLES" defaults (poked block), identical to the game's |

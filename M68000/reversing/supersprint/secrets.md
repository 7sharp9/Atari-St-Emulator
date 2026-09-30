# Super Sprint: input, secrets and dead code

**Verdict: the game has no cheat codes, no cheat-name hooks in the high-score entry, no hidden tracks and no hidden modes.**
It has one undocumented developer-style hook (F5 on the winner's circle), three undocumented conveniences (F8 pause, F10
abort, ESC), and a quantity of vestigial code and unreferenced data: a removed copy-protection check with a cracker tag,
a debug number tuner, a 59.5-second tune nobody plays and an old credits text. How thoroughly this was searched:

- input side: a static grep of every A4 offset in the key-table range plus a 117-scancode A/B scan (`%01..%75`) on seven
  screens, each scan deterministic and same-snapshot/same-step-budget;
- code side: a whole-image reachability analysis over 351 nodes (263 `LINK A6` frames) and an instruction-level orphan scan;
- data side: cold-boot and runtime "poison" A/B over all three data files (flip a 256-byte block, see what RAM changes).

Scripts are under `py/secrets/` (`run_all.py` re-runs the quick proofs).

## Input

The IKBD interrupt `$104b6` (vector `$118`, installed by `$1048a` through `Mfpint(6)`) handles one byte at a time with a
state byte at `$10544`. The game sends only the IKBD command `$14` (joystick event mode). State 0: `$FE`/`$FF` selects
joystick 0/1 and the next byte is stored at `-4804/-4803(A4)`; any other byte is a scancode: `& $7F >= $76` is ignored, a
make stores `$03` into `table[sc]` (`-4802(A4) + sc`) and a break clears bit 0 (cell `$02`). The complete reader list of
the key table is `$105a0` (the channel reader), `$10658` (the F-key poll), `$18626` (ESC), `$d4d0` (writes the F1 cell) and
the dead routine `$e74a`; nothing else reads the stick or key bytes (`isr_proof.py`, every cell matched).

**Channel reader `$105a0`.** Channel 0 (keyboard) is the OR of three key sets: left = A `$1e` | Z `$2c` | L `$26`; right = D
`$20` | X `$2d` | `'` `$28`; fire = LShift `$2a` | RShift `$36` | Alt `$38`. Channels 2 and 3 are the raw joystick 0 and 1
bytes; channel 1 (the mouse) and any other value return 0. Joystick up and down (`0x01`, `0x02`) are read nowhere
(`race_input.py`: up+fire and down+fire behave exactly like fire). The per-player channel words `-4810/-4808/-4806(A4)`
(blue, red, yellow) default to `[0, 2, 3]`. LShift starts a session as slot 0 (blue), `fe 80` as slot 1 (red) and `ff 80` as
slot 2 (yellow); `fe 01` and `ff 06` start nothing (`fire_sources.py`).

| scancode | reader | effect (same-snapshot A/B, keys held at least 30000 steps) |
|---|---|---|
| `$3B` F1 | `$10658` from the attract wait loop `$1399e` | opens the options screen `$18b54`; in the demo race it also exits the demo first; consumed and ignored in race, options, winner's circle |
| `$3C $3D $3E` F2 F3 F4 | options | cycle the channel of blue/red/yellow 0 -> 2 -> 3 -> 0 (channel 1 is skipped) |
| `$43` F9 | options | toggles sound `-8068(A4)` |
| `$44` F10 | options | with duplicate controls shows "can't have two controls the same" (`$18ffa`) and stays; otherwise returns to the main loop |
| `$42` F8 | in a race | pause / unpause (`$c996`, then the `$c9c8` poll loop) |
| `$44` F10 | in a race | silences the PSG, `$be40` returns 1: **the race is aborted and the session tail `$13b2c` (the high-score save) is skipped**; back to attract in about 1M steps |
| `$3F` F5 | winner's circle `$1ad40` | forces prize animation 3 (next section) |
| `$01` ESC | the PREPARE-TO-RACE join countdown in `$18024` | zeroes the countdown word: the race loop was entered 6.22M steps after the snapshot with ESC held vs 9.74M without (but see Known traps in `sessions/supersprint.md`: the prepare screen is fragile) |
| `$2A $36 $38` | everywhere | fire: start (slot 0), join, accelerate, accept a letter |
| A/Z/L, D/X/`'` | race, keyboard slot | steer left/right (identical result per set) |
| `$4E $4A` keypad +/- | only `$e74a` | dead code (below) |
| every other scancode | - | no effect |

The scan found, in the attract phase, only `2a 36 38` (session start) and `3b` (options) change anything; the demo race the
same four; F2-F10 are consumed silently by `$10658`. Arrow keys and joystick packets do not drive a keyboard slot. The attract
loop polls input only in the title/wait phases and the demo race, never in the lap-records phase.

**A bug, not a cheat: mouse packets ghost-press keys.** Every IKBD packet header other than `$FE`/`$FF` (mouse `$F8..`, status,
`$FD`) is ignored, but its *data bytes* are stored as scancodes. `kbd f8 3b 00` opens the options screen, `f8 2a 00` starts a
session, `f8 05 3b` also F1, `f8 7f 7f` does nothing (`mouse_ghost.py`, 5/5). The game never switches relative-mouse reporting off, so
moving the mouse on a real ST would press keys (from the code; not tested on hardware).

## F5 on the winner's circle: the one hidden hook

`$1ad40` polls `$10658` once after the rank and score animations. With F5 (`D0 = 5`) it sets the duration words
`-9062/-9064(A4)` to 10 and the prize-animation index `-2(A6)` to 3; any other result sets both words to 30 and the index to
`rnd(16) & 3`. Those two words are frames 1 and 2 of animation 3 in the 4 x 26-byte duration table at `-9144(A4)` (frame
images at `-9040(A4)`, 13 frames each, terminators -1 loop / -2 step back). So F5 forces the longest prize animation (seven
images, sprite ids 9..15: the mechanic stands up and sparks fly; its frame 0 lasts 100 ticks) and shortens frames 1 and 2 from
30 to 10 ticks. Proof (`f5_winner.py`, `f5_frames.py`): no key D0 = 0, animation 1, 30/30; F5 held D0 = 5, animation 3, 10/10;
F6 or F4 held D0 = 6 or 4, animation 1, 30/30; F5 tapped and released before the poll D0 = 0. Animation 3 is also reachable
randomly, so the F5-specific facts are the forced choice and the shorter holds. Verdict: a developer test hook, undocumented;
the intent is inferred. The on-screen cadence of the 10-tick frames was not measured (the table values are).

## High scores and `SSPRINT.HSC`

The file is 295 bytes = `$ba + $5d + $10`: **31 records of 6 score-digit bytes** (record 0 is a zero sentinel, 1..30 descending;
the shipped top score is 106050 and #30 is 028730; the last digit is always 0 and the compare ignores bit 7) into `-7956(A4)`;
**31 x 3 initials** into `-8050(A4)`; **8 words of lap records** (per track, /5 = seconds) into `-8066(A4)`, all 0 as shipped. The reader
is `$100a4` (via `$10002`, from main); the writer `$1000e` (guard `-148 == 0` sets `-150 = 1`; if `-150 == 0` it does
`Fcreate` + three `Fwrite` + `Fclose`) is called only from the session tail `$13b2c`, so an F10 abort never saves. A stored
initial is the letter index + `$0b` (A = `$0c` ... Z = `$25`, blank = `$26`). The shipped table decodes (checked against the rendered
attract screen) to placeholder initials (DDN DDU DDX DDJ ... AAA ...), no meaningful text. The entry screen `$172f0` (called
at the end of every `$18024`) is only for players who are not drones and have a non-zero score; left/right change the letter
(auto-repeat, A..Z, blank), fire accepts, three letters, **no name or word checks**. Live with a poked score the new row appears at
rank 1 and the others shift (`hiscore_entry.py`). Unproved: a save at the end of a real session (the emulator did not persist
writes to the host image in these runs).

## Dead and unreferenced code

`py/secrets/reach.py`: 351 nodes, 340 reachable, **11 unreached routines (1540 bytes)**; no direct, PC-relative, A5-thunk,
immediate, absolute or pointer-table reference, and no `jmp (Dn)` tables (the only indirect `jsr` is the C-library signal table
at `-10806(A4)`).

| where | verdict |
|---|---|
| `$e74a` + `$e790` | **debug tuner, dead.** Reads the cells `-4728` (keypad `-`, `$4a`) and `-4724` (keypad `+`, `$4e`); `+` increments and `-` decrements (guarded > 0) the word `-8300(A4)` and draws it as four decimal digits at the top-left via `$e790` -> thunk 600 (`$16528`). Nothing references it; `-8300` is touched only inside `$e74a` (a watch over 27M attract and 20M race steps saw 0 writes). Poking the keypad-+ cell takes `-8300` from 0 to 1 and influences nothing |
| `$101d2-$10204` (+ string at `$10206`, "(b)1987 by Mr.?" at `$10210`, patch at `$10226`) | **a removed copy-protection check and a cracker tag.** `$101d4` does `Fopen("BOOT.DAT")`, reads 512 bytes into `-90(A4)`, closes. The patched head `$101bc` (thunk 156, called from main `$13868`) clears `-150(A4)`, sets `-148(A4) = 1` and returns early. The disk has no `BOOT.DAT`. Had the check failed (`-150 = 1`), the session would not save the high-score file and would end after the first race (`$13b16`). Fourteen NOPs at `$103fc` and two at `$10428` are more patched-out code; a NOPed `trap #14` at `$f632` kills the splash raster code |
| `$f1dc` (256 B) | superseded waypoint-reached test (`abs()` comparisons, returns 2 or 0); the live one is `$f2dc` |
| `$129bc`, `$12ac2`, `$12d64` | three sound starters no one calls: unused sound data (`sound.md`) |
| `$155ce` | unreferenced debug dump of the 40x25 surface map into the back screen (callcap wrote 10,786 screen bytes; `png/secrets/dead_155ce_map.png`) |
| `$128d4`, `$10a32`, `$10a8c`, thunk 0 | an empty stub, C-library junk, and crt0's duplicate thunk (100 of 101 thunks are used) |
| the **mouse channel** | strings "mouse" and "can't have the mouse and joystick 0 at the same time" exist, but F2-F4 skip channel 1 and `$105a0` returns 0 for it; forcing channel 1 by poke makes the car unresponsive: a dead feature |

**Not dead: the reset hook.** Main installs, through `Supexec($103e6)`, the reset-survival magic `$31415926` at `$426`
and the vector `$10430` at `$42a`. The ROM calls the vector (A6 = return) only if the magic matches and the vector is even with
a zero high byte. `$10430` switches to a stack at `-94(A4) + $3a98`, calls the RLE picture decoder `$10236` (credits picture plus a
7-step fade), delays about 5M `dbf`, clears the magic and returns: **a reset shows the credits picture**. The decoder is ported
to Python (`reset_picture.py`, 20039/20039 screen bytes equal to callcap; `png/secrets/reset_picture.png`). The credits
read: "Electric Dreams presents Super Sprint ... created for the Atari ST by State of the Art. Programming: Nalin Sharma, Martin
Green, Jon Steele. Graphics: Chris Gibbs. Sound: Mark Tisdale. A Software Studios production." The reset path itself was never
fired in the emulator (no reset button in this harness).

## Data files

Every DATA string has a user (`data_strings.txt`, 97 strings) except `CON:`, `AUX:`, `PRT:` and `%d` (C runtime). There is no
ASCII text anywhere except `BOOT.DAT`, the "(b)1987 by Mr.?" tag and those strings; a dictionary hunt across 232 glyph offsets
found only one real text, below.

- `INIT.DAT` (5139 B): all 21/21 256-byte blocks are consumed at boot (each poisoned block changes exactly 256 RAM bytes elsewhere
  in the A4 frame; two blocks drive boot-time work). Begins with the eight-track start table. Nothing unreferenced.
- `SUPER1.DAT` (17024 B): 47 of 67 blocks consumed at boot. **The range `[0x2e60, 0x4280)` (5152 bytes) is never read** (poison gives 0
  differing bytes across boot and attract up to step 18M; a control poison of a consumed block gives 63,042). It holds an old
  **credits text** in glyph indices (A = 0 .. Z = 25) at `0x3a9a`: "SUPER SPRINT WAS CREATED FOR THE ATARI ST BY STATE OF THE ART ...
  PROGRAMMING BY NALIN SHARMA, MARTIN GREEN, JON STEELE ... GRAPHICS BY CHRIS GIBBS ... SOUND BY MARK TISDALE ... SEE YOU NEXT SUMMER FOR
  SOMETHING EVEN MORE BREATHTAKING ....... S.O.A." plus 16x16 one-bit cells from `0x2ee0`. The credits page that is shown is a
  pre-rendered RLE picture in `SUPER.DAT` (no "WAS", no "SEE YOU NEXT SUMMER"). Never displayed.
- `SUPER.DAT` (212,650 B): the tail `0x30800..0x33e2a` is consumed verbatim at boot. Only **seven 4 KB blocks (28,672 bytes) are never
  consumed in any tested flow**: file offsets `+0x3000-0x3fff`, `+0xf000-0xffff`, `+0x1b000-0x1bfff`, `+0x23000-0x25fff`, `+0x2b000-0x2bfff`.
  They contain graphics-looking data. The flows tested were the full attract cycle (27M steps), a race on each of the eight tracks
  plus the winner's circle (20M), menus and prepare (18M), options, select, shop and hi-score entry; "unused in the tested flows" is not
  proof of "unused".
- The disk: FAT12 360K, no deleted, hidden or volume entries, zero unreferenced non-zero clusters, zero slack, FAT copies equal. Not
  bootable; no protection routine remains (no `Floprd`/`Rwabs`; only GEMDOS `Fopen/Fread/Fcreate/Fwrite/Fseek/Fclose/Malloc` and
  XBIOS `Random/Setpalette/Vsync/Getrez/Supexec/Mfpint/Xbtimer/Setscreen`).

## Debug leftovers and globals

`$ffff8240` is written only at `$f67c` (a one-shot grey while the raster ISR is installed), in the ISRs `$f706 $f75e $fa1c $fa7e` and in
the reset hook: no colour-flash debugging. No permanently disabled test flag exists. `-8068(A4)` is the sound flag (read at about 25
places), `-8070` the leave-attract flag, `-3914..-3910` the per-slot drone flags (the session loop ends when all three are 1), `-3954[slot]`
the wrench counter. Tracks: every table has 8 entries; the dial wraps both ways.

## Open

- Identify the seven never-consumed `SUPER.DAT` blocks and the `SUPER1.DAT` tail cells by rendering them; finer 1 KB poison on them;
  test the remaining triggers (hazards, spin-out, pickups, all player counts, game-over and hi-score screens) before calling them unused.
- Decode the unused tune at script offset 906 through the driver, or add Timer D to the emulator.
- A screen-level proof of the F5 animation (count the ticks of frames 1 and 2 with and without F5), and a positive proof of the
  high-score save at the end of a session.
- The prepare-screen fragility (next paragraph) decides how far the ESC finding can be trusted.

The scans found that in the prepare snapshot a held make of almost any key, or an ESC tap, ends with the game dying in race-start
initialisation (a Line-F exception through a wild jump, then the ROM bomb loop): see `sessions/supersprint.md`, Known traps. It looks
like dependence on the IKBD delivery phase rather than a key function, possibly an emulator artefact, and is unresolved.

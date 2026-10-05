# Final Fight in-level frame (phase 6, `$4e3a`) and the object array

What runs each frame once the stage is under way, and where the players, enemies, TIME and the sprite
list live. Evidence tags as in `kernel.md`: **[R]** read in the ROM listing, **[L]** checked against a
write-tap log of the scripted drive (`lua/kernel_log.lua`, `FF_KLOG_EXTRA` taps; per-address writer
histograms), **[S]** read from the saved state `ff_gameplay` (end of frame 2200), **[I]** inferred.
`A5 = $ff8000`.

## Who calls it

Task slot 1 (`$4c16`, `kernel.md`) sleeps one frame at a time and calls `$4cc2`, which dispatches on the
word `0(A5)`. Phase 6 (`$4e3a`) is the in-level frame [R]; it was entered at frame 1313 and was still
current at frame 2200 [L]. Its body, in order:

| call | what it is | evidence |
|---|---|---|
| `tst.b 21416(A5)` | non-zero (all players out) jumps to `$5da78` instead of the pipeline | [R] |
| `bsr $5326` | **difficulty counter** (below) | [R] [L] |
| `bsr $5238` | **TIME countdown** (below) | [R] [L] [S] HUD |
| `jsr $5668` | per-frame update of the two player records and the world around them, ending in `bra $90fa` (calls `$5acdc`, `$5764`, `$5b1cc`, `$5aea`, `$57f2`, `$5a1a`, `$5fc6`, `$5962`, `$59a4`, `$5848`, `$5a72`, `$5ff4`, none read yet). `$56b4` and `$570e` are two shorter variants of the same sequence, entered from elsewhere or not at all (callers not searched) | [R] |
| `jsr $6396` | **hit resolution**: `bsr $6f6c`, `bra $7766` (below) | [R] |
| `jsr $6026` | `A6 = $ffb1a8` (`12712(A5)`, the last record of the array), dispatches on byte `2(A6)` (table `$604a`), then `jmp $27fc4`; skipped while `299(A5)` is set | [R] |
| `jsr $61e24` | stores the active-player mask (bit 0 of each player record's first byte) in `21610(A5)`, then updates the two player objects at `1036(A5)` and `1164(A5)` by their state byte `2(A6)` (dispatch table `$61e5a` for the first, a routine at `$6241e` for the second) | [R] |
| `jsr $16600` | **sprite list builder** (below) | [R] [L] |
| `tst.b 297(A5)` ... | `297(A5)` negative and `140(A5)` zero: `jsr $2636`, phase := 8 (stage over); otherwise `$4e9c` sets `21416(A5)` when both player records' first byte is zero | [R] |

The three `jsr $50e` calls with `D0 = $43, $53, $54` between the stages are not game logic: `$50e` fills 32
palette words at `$908500` with `D0 + $4400` only when `142(A5) = 0`, Service Mode (`132(A5)`) is on and bit 6
of `100(A5)` is held (`lua/specs/validate_50e.lua`, README "callcap"). They are the CPU-load colour bar of
the test mode, one colour change per stage of the frame, and do nothing in normal play [R].

## TIME

`175(A5)` (`$ff80af`) is the on-screen TIME in packed BCD. At frame 1316 `$51ec` loads it from a byte table
at `$5210` indexed by `190(A5) * 4 + 191(A5)` (`190(A5)` and `191(A5)` are 0 and 0 here, probably stage and area **[I]**): entry 0 is `$30` and the
tap saw `$ff80ae <- $0030` at that frame [L]. The table is `30 30 50 99 | 50 70 30 70 | 50 50 50 99 | 70 50 99 99 | 99 99 99 99 | 60 70 70 99 | 30 99 99 99 | 20 99 99 99 | ...`
in rows of four (`$5210`, 40 bytes read, `$99` in many entries); it was not mapped to the game's actual stages and areas.
From frame 1677, when the scripted intro has ended, `$5238` increments `176(A5)` once per frame and at
`$1e0` (480 frames, about 8.05 s at 59.63 Hz) clears it and decrements `175(A5)` with `sbcd` (`$5266`) and
redraws through `$559a`. The tap saw the single decrement at frame 2156 (`$ff80ae <- $2929`), 1677 + 479, and
the saved state holds `175(A5) = $29` with `176(A5) = 43 = 2200 - 1677 - 480`. The HUD of that frame shows
"TIME 29" (`gameplay.png`): 1 of 1 [L] [S]. `$559a` writes the two digits as tile words at `$909014` (the
second digit 256 bytes lower, 8 KB higher for player 2's HUD when `21417(A5)` is set) from a tile table at
`$55f4` with attribute `$186` [R]. A second countdown, `$52b6`, uses a 60-frame period and on reaching zero
sets `297(A5) = 1` and phase 6; phase 6 does not call it, and its caller was not searched [R].

`$5238` skips the count while `298(A5)`, `297(A5)` or `291(A5)` is non-zero, and at TIME 0 calls `$51de`
(reload `174(A5)` from `186(A5)`, redraw) and `$5298` for each player record [R], so the end-of-time
behaviour is a reload at that call site, not obviously "time over"; unproven.

## Difficulty counter

`$5326` (`168(A5)`, `172(A5)`, `176`, `276(A5)`, `180(A5)`, `188(A5)`): initialised at `$5464` from a byte
table at `$54ac` indexed by `134(A5)` (168, 170 and 188 all take the value, 4 here) and `172(A5) := 135(A5)`
(1 here) [L, frame 1200]. Each frame without the flags `290/291/297/298(A5)` it adds 1 to `276(A5)` and,
when that reaches a limit from the table at `$536a` indexed by `172(A5)`, resets it and raises `168(A5)`
by one up to a ceiling from `$5372`; other entry points subtract table amounts (`$5386`, `$53b2`, `$53dc`)
down to a floor `188(A5)`. In Service Mode `$554e` prints `168`, `172` and `276` on the screen. A value
that rises with elapsed play time and falls on events: a dynamic-difficulty rank **[I]**; `134/135(A5)`
are probably the difficulty DIP bytes (not checked against `hardware.md`).

## The object array

One array of 192-byte (`$c0`) records starts at `$ff8568` (`1384(A5)`) and the game code addresses it by
register `A6`/`A1`/`A3`. In the saved state [S]:

| index | address | contents |
|---|---|---|
| 0 | `$ff8568` | player 1 (Cody): first byte 1, x `$01fa`, y `$002f` |
| 1 | `$ff8628` | player 2: first byte 0 (inactive), x `$026a`, y `$0030` left over from the select screen |
| 2-14 | `$ff86e8-$ff90a7` | 13 records whose byte 18 is 2; index 14 is **Bred** (first byte 1, x `$0221`, y `$002f`); the other 12 are empty |
| 15-20 | `$ff90a8-$ff9527` | 6 records, byte 18 = 6, all empty |
| 21-28 | `$ff9528-$ff9b27` | 8 records, byte 18 = 4, all empty |
| 29-58 | `$ff9b28-$ffb0e7` | 30 records, byte 18 = 8 (three have byte 19 set), all empty |
| 59 | `$ffb1a8` | one record with byte 18 = `$10`, the `A6` of `$6026` |

Bred was found by scanning the state for a record with the same layout as Cody's at a plausible world
position and matching the HUD's BRED bar; his record sits exactly 14 x `$c0` after Cody's [S]. Byte 18 is
constant over each run of records in a state where almost everything is empty, so it is a per-pool tag
that is set at build time (the empty records keep it): the pools are players, 13 + 6 + 8 + 30 slots and
one special. What each pool holds (grunts, bosses, items, weapons, projectiles) is **[I]**: one live
enemy is the only sample; a second state with several kinds on screen is the check.

Fields seen in use (offsets from the record base `A6`) [R] [L]:

| offset | meaning | evidence |
|---|---|---|
| +0, +1 | first byte non-zero = in use (the loops test `tst.b 1(A6)` in `$639e`, the players' first byte in `$61e24`) | [R] [S] |
| +6 word, +8 word | x position (integer, fraction); `add.l D0,6(A6)` adds a 16.16 step | [R] [L] |
| +10 word, +12 word | y position (integer, fraction), same layout; `$c0f6` writes it | [R] [L] |
| +14 | a copy of y (`$c046`: `move.l 10(A6),14(A6)`), apparently the ground line; z is the difference | [R] **[I]** |
| +46 | facing, bit 0 = flip; `$41e4` toggles it | [R] |
| +54 | animation frame index | [R] |
| +64, +66, +67, +68 | partner link: `68(A6)` is a pointer to another record and `67(partner)` a pose index; the follower copies the partner's position plus an offset from a table at `70(A6)` (`$41ba-$4230`), mirrored by the partner's facing. Holder and held in a grab fits this, so does an owner and its follower; not told apart | [R] |
| +184, +188 | pointers to the current animation's per-frame x and y step tables (`$c0d8`, `$c0ea`): motion is driven by tables, `D0 = table[frame] << 16 >> 8` | [R] |

Writers of the position over frames 1790-2200 [L]: for player 1, x (+6) is written by `$8e46` (410 times,
`sub.w D2,6(A6)`, a scroll or push correction) and by the step integrator `$c0e6` (286 times); y (+10) by
`$8e58` (410) and `$c0f6` (286); Bred's position by the partner-follow code `$41cc`/`$41d2` and `$4206`/`$420e`
(19 each) and by `$27dbc`/`$27de4` (17 each). The roles of `$8e46` (a scroll compensation is a guess **[I]**) and
`$27dbc` were not read; `$c0e6` is the step integrator for animation-driven motion.

## Hit resolution (`$6396`)

`$6f6c` walks lists of up to 21 (`$15`) record pointers kept at `21250(A5)` and `21306(A5)` (player 1) and
`21354(A5)` and onward (player 2) (the arrays start at `$ffd302` and `$ffd33a`, reset at `$6fde`), with the
player record in `A1` or `A3` and the list entry in the other. It copies the player record's `116/118` words
(probably a hit-box x and y **[I]**) to `-28200(A5)/-28196(A5)`, calls `$708e` or `$7564`, then clears the
entry [R]; only the first two lists and the start of the third were read. `$7766` is entered after `$6f6c` and compares the two player records pairwise (`$77e0`: both
in use, neither in a state `148/97/44/139`, and a distance test on `14` and `90`) and calls `$78c6` and `$7932`,
which look like player-versus-player contact **[I]**. The hit boxes themselves (`116/118(A6)`, `112/120(A6)`) and
the damage application in `$708e`/`$7564` are the next read.

## Sprite list (`$16600`)

`$16600` builds the CPS1 object list for the next frame and swaps buffers [R] [L]. `158(A5)` holds `$9000` or
`$9040`, the high byte pair of `$900000` and `$904000`, and the VBL handler stores it to CPS-A `$800100` (`$584`).
At the end of `$16600` the value is flipped (`$16668-$16674`); the first lines clear the stale tail of the buffer
about to be written (`144(A5) = $100` entries, the previous count kept at `148(A5)` or `154(A5)`), and
`$1667c` drains lists at `$ffd290`, `$ffd03e`, `$ffd080`, ... through `$16850`/`$1680c`. A tap on
`$900000-$907fff` over frames 2150-2154: 928 writes, 464 into each of the two buffers, all from `$16a36`,
`$16a38`, `$16a3a`, `$16a3c` (228 each: the four words of one object entry) and `$16656`/`$16658` (8 each:
the stale-tail clear) [L]. The same VBL handler (`$53e`) reads its inputs and copies the scroll values;
`kernel.md` lists the rest.

## Not read, not proven

- The thirteen callees of `$5668`, the tables behind `$6026` and `$61e24`, `$708e` and `$7564`, and
  `$27fc4`. Player health and the hit-box layout are in there; none of it is named.
- What the pools of the object array hold, and the meaning of byte 18 beyond "constant per pool".
- The entries of the TIME table per stage/area and what happens at TIME 0.
- Difficulty counter: the role is **[I]** from the code shape, no live check beyond its initial values.

# Final Fight in-level frame (phase 6, `$4e3a`), the object pools, health, hit boxes and damage

What runs each frame once the stage is under way, where the fighters, props and effects live, and how a
hit becomes a health change. Evidence tags as in `kernel.md`: **[R]** read in the ROM listing, **[L]**
checked live in MAME (write taps, breakpoint counters, per-frame RAM or HUD comparison) with a count,
**[S]** read from a saved state, **[I]** inferred. `A5 = $ff8000`. The saved states are `ff_gameplay` (stage 1,
Cody, Bred, end of frame 2200) and `ff_enemies` (stage 1, end of frame 4150, five enemies; `enemies.png`,
`py/poolcensus.py`). The scripts that reproduce each claim are listed in the README ("Scripts").

## Who calls it

Task slot 1 (`$4c16`, `kernel.md`) sleeps one frame at a time and calls `$4cc2`, which dispatches on the
word `0(A5)`. Phase 6 (`$4e3a`) is the in-level frame [R]; it was entered at frame 1313 and was still
current at frame 4300 [L]. Its body, in order:

| call | what it is | evidence |
|---|---|---|
| `tst.b 21416(A5)` | non-zero (all players out) jumps to `$5da78` instead of the pipeline | [R] |
| `bsr $5326` | difficulty counter (below) | [R] [L] |
| `bsr $5238` | TIME countdown (below) | [R] [L] [S] |
| `jsr $5668` | the thirteen updaters, below ("The per-frame updates"), called 60 of 60 frames each | [R] [L] |
| `jsr $6396` | hit resolution: `bsr $6f6c`, `bra $7766` (below) | [R] |
| `jsr $6026` | `A6 = $ffb1a8` (`12712(A5)`, a 64-byte record with tag `$10`), dispatches on byte `2(A6)` (table `$604a`), then `jmp $27fc4`; skipped while `299(A5)` is set. Its spawner variants (`$6278-$62f6`) feed the stage-script executor `$61a8`, below; its other states are not read | [R] |
| `jsr $61e24` | stores the active-player mask (bit 0 of each player record's first byte) in `21610(A5)`, then updates the two player objects at `1036(A5)` and `1164(A5)` by their state byte `2(A6)` (dispatch table `$61e5a` for the first, a routine at `$6241e` for the second); not read | [R] |
| `jsr $16600` | sprite list builder (below) | [R] [L] |
| `tst.b 297(A5)` ... | `297(A5)` negative and `140(A5)` zero: `jsr $2636`, phase := 8 (stage over); otherwise `$4e9c` sets `21416(A5)` when both player records' first byte is zero | [R] |

`$56b4` and `$570e` are two shorter variants of the `$5668`..`$16600` sequence, entered from elsewhere or not
at all (callers not searched). The three `jsr $50e` calls with `D0 = $43, $53, $54` (and `$5a` inside `$5668`)
are not game logic: `$50e` fills 32 palette words at `$908500` with `D0 + $4400` only when `142(A5) = 0`,
Service Mode (`132(A5)`) is on and bit 6 of `100(A5)` is held (`lua/specs/validate_50e.lua`, README
"callcap"). They are the CPU-load colour bar of the test mode and do nothing in normal play [R].

## TIME

`175(A5)` (`$ff80af`) is the on-screen TIME in packed BCD. At frame 1316 `$51ec` loads it from a byte table
at `$5210` indexed by `190(A5) * 4 + 191(A5)`; `190(A5)` and `191(A5)` are the stage and area (the stage
script `$5aea` selects its script from the same pair, below). Entry 0 is `$30` and the tap saw `$ff80ae <-
$0030` at that frame [L]. The table is `30 30 50 99 | 50 70 30 70 | 50 50 50 99 | 70 50 99 99 | 99 99 99 99 |
60 70 70 99 | 30 99 99 99 | 20 99 99 99 | ...` in rows of four (`$5210`, 40 bytes read, `$99` in many entries); it
was not mapped to the game's actual stages and areas. From frame 1677, when the scripted intro has ended,
`$5238` increments `176(A5)` once per frame and at `$1e0` (480 frames, about 8.05 s at 59.63 Hz) clears it and
decrements `175(A5)` with `sbcd` (`$5266`) and redraws through `$559a`. The tap saw the single decrement at
frame 2156 (`$ff80ae <- $2929`), 1677 + 479, and the saved state holds `175(A5) = $29` with `176(A5) = 43 =
2200 - 1677 - 480`. The HUD of that frame shows "TIME 29" (`gameplay.png`): 1 of 1 [L] [S]. `$559a` writes the
two digits as tile words at `$909014` (the second digit 256 bytes lower, 8 KB higher for player 2's HUD when
`21417(A5)` is set) from a tile table at `$55f4` with attribute `$186` [R]. A second countdown, `$52b6`, uses a
60-frame period and on reaching zero sets `297(A5) = 1` and phase 6; phase 6 does not call it, and its caller
was not searched [R].

`$5238` skips the count while `298(A5)`, `297(A5)` or `291(A5)` is non-zero, and at TIME 0 calls `$51de` (reload
`174(A5)` from `186(A5)`, redraw) and `$5298` for each player record [R], so the end-of-time behaviour is a
reload at that call site, not obviously "time over"; unproven.

## Difficulty counter

`$5326` (`168(A5)`, `172(A5)`, `176`, `276(A5)`, `180(A5)`, `188(A5)`): initialised at `$5464` from a byte table
at `$54ac` indexed by `134(A5)` (168, 170 and 188 all take the value, 4 here) and `172(A5) := 135(A5)` (1 here)
[L, frame 1200]. Each frame without the flags `290/291/297/298(A5)` it adds 1 to `276(A5)` and, when that
reaches a limit from the table at `$536a` indexed by `172(A5)`, resets it and raises `168(A5)` by one up to a
ceiling from `$5372`; other entry points subtract table amounts (`$5386`, `$53b2`, `$53dc`) down to a floor
`188(A5)`. In Service Mode `$554e` prints `168`, `172` and `276` on the screen. A value that rises with
elapsed play time and falls on events: a dynamic-difficulty rank **[I]**; `134/135(A5)` are probably the
difficulty DIP bytes (not checked against `hardware.md`).

## The object pools

All game objects are `$c0`-byte records handed out by per-pool free stacks, tagged by the byte at `+18`
(constant over a pool, set at build time, kept by empty records) [R] [S]. `+19` is the kind: the index of the
handler a pool's updater calls. Most pools sit in one run from `$ff8568`; three do not. The census of
`ff_enemies` [S] (`py/poolcensus.py`, array index = pool-local index + 2 in pool 2) and what each updater
walks [R] [L]:

| tag | records, base | updater | contents |
|---|---|---|---|
| (players) | 2 at `$ff8568` | `$5764` | player 1 (Cody), player 2 (inactive in every run) |
| 2 | 13 at `$ff86e8` (`1768(A5)`) | `$57f2` | fighters: enemies and bosses, 9 kind handlers (`$21cec`, `$2813a`, `$2a310`, `$2ccac`, `$3136c`, `$3514c`, `$389b8`, `$3c446`, `$3c48e`); the only damage-taking pool apart from `$a` |
| 6 | 6 at `$ff90a8` | `$5962` | never live in stage 1 |
| 4 | 8 at `$ff9528` | `$5a1a` | never live in stage 1 |
| 8 | 30 at `$ff9b28` (`6952(A5)`) | `$5848` | 60 kind handlers from `$1a1f0`; one record live in `ff_enemies` (kind 1, word `20 = $0300`, x `$518`), role unknown. Records 56 and 57 of the array are live already in `ff_gameplay` [S] |
| `$10` | `$ffb1a8` and `$ffb1e8`, 64 bytes each | `$6026`, `$5aea` | the placement record and the stage-script record (below) |
| `$c` | one `$c0` record at `$ffb228` (`12840(A5)`) | `$5acdc` | a scripted scene actor, three types (table `$5acf2`); never in use in any run **[I]** |
| `$a` | 16 at `$ffb2e8` (`13032(A5)`) | `$59a4` | breakable props: kind 5 (4 live in `ff_enemies`; one was named TEL.BOOTH by the HUD when hit, 1 sample); kinds 5 and 8 seen |
| `$e` | 271 records of 64 bytes at `$ff3000`, handed out in groups of 6 by `$5a72` | `$5a72` | effects: kind 0 is a hit spark created on the frame of each hit on Cody (8 of 8); kinds 1 and 3 seen |
| `$12` | 10 at `$ffbee8` | `$5fc6` | one kind (`$5a55a`), not live in `ff_enemies` |
| `$14` | 10 at `$ffc668`, 64 bytes | `$5ff4` | one kind (`$563dc`), kind 0 seen in the earlier run |

The allocators are `$3892` (tag 2), `$38ce` (6), `$390a` (4), `$3946` (8), `$3982` (`$a`), `$39be` (`$12`), `$39fa`
(`$14`); the effect allocator is `$3a96`. Earlier text called `$ffb1a8` the last record of one 60-record array
and treated the pools as one array; that was wrong: the `$c0`-spaced run `$ff8568-$ffb1a7` holds the players
and tags 2, 6, 4 and 8 only, and the remaining pools have their own bases and strides.

**Stage script executor `$61a8`.** The enemy and prop spawns are read from a script [R]: `$5aea` keeps a script
pointer at `6(A6)` of `$ffb1e8`, chosen from `190/191(A5)` through the tables at `$5f5e` and `$5f7e`; state 2
(`$5b4e`) waits for the camera to pass the entry's trigger x and then spawns 16-byte entries through `$61a8`
(via `$5e36`, `$5e84`, `$5ee6`). Script byte 6 selects the pool (1 tag 2, 2 tag 4, 3 tag 6, 4 tag 8, 5 tag
`$a`, 6 the `$ffb228` slot, 8 `$ffb1e8`, 9 tag `$12`, 10 tag `$14`), byte 7 becomes `+19` (kind), word 8 becomes
`+20`, byte 12 becomes `+96`. Live: the script pointer moved from `$70676` to `$70684` at frame 3223, when the
camera x reached `$3f0` (the entry's trigger), and a tag-2 record was created at `$5ee6` 94 frames later, 1 of 1
[L].

**Fighter identity.** The enemy name on the HUD (the game's own text) was read from screenshots of `ff_enemies`
and its run, and matched to the character data pointer at `92(A6)`: BRED `$23f8c` (kind 0, subtype `+20 = 0`; 5
of 5 clean frames), DUG `$24f2a` (kind 0, subtype 1; 4 of 4), JAKE `$25ed0` (kind 0, subtype 2; 6 of 6),
HOLLY WOOD `$37be0` (kind 5; 1 sample), AXL `$2bf94` (kind 2) inferred only from the order three HUD names appeared
in one frame (AXL, JAKE, DUG against pool order) **[I]**. `92(A6)` is also the table the damage value is read from
(below). The HUD's enemy-name selection code (`$5b4aa`) is not read.

## The player and fighter record

Offsets from the record base `A6`, for the players and for pool 2 [R] unless tagged:

| offset | meaning | evidence |
|---|---|---|
| +0 | non-zero = in use (bit 7 is cleared by the updaters). `+1` is not "in use": `$8dfa`/`$8e00` clear and set it, a visible/blink flag during invulnerability **[I]** | [R] [S] |
| +2, +3 | state byte and sub-state; the player state table `$a566` has 7 entries (2 alive with sub-states from `$a5b6`; 4 `$dc08`, 5 `$e8e8`, 6 `$c840`) | [R] |
| +6 word, +8 word | x (integer, fraction); `add.l D0,6(A6)` adds a 16.16 step | [R] [L] |
| +10 word, +12 word | y (integer, fraction); `$c0f6` writes it | [R] [L] |
| +14 | copy of y (`$c046`): the ground line; the depth lane test compares it | [R] |
| +18, +19, +20 | pool tag, kind, subtype word | [R] [S] |
| +24 word | **health**, +26 shadow of the last-seen health, +28 maximum (Cody `$90` = 144, Bred `$1c`), set together at spawn by `$2fa2` from the data record at `92(A6)` (7 spawns of each) | [R] [L] |
| +44, +45 | hurt-box index, attack-box index (bit 7 set = grab attack); +55 defence class | [R] [L] |
| +46 | facing, bit 0 = flip | [R] |
| +54 | animation frame index; `56(A6)` points at the current animation's data (box blocks) | [R] |
| +64, +66, +67, +68 | grab link: `64 = 1` and `68 = victim` on the holder, `64 = $ff` and `68 = holder` on the held; the follower copies the holder's position plus an offset from the table at `70(A6)` (`$41ba-$4230`) | [R] [L] |
| +92 | pointer to the character's data (damage table, `$23f8c` for Bred) | [R] [L] |
| +96, +97 | `+97` non-zero disables the hurt box | [R] |
| +112 long, +116/+118 words | attack-box descriptor pointer (0 = none), attack-box centre x, y | [R] [L] |
| +120 long, +124/+126 words | hurt-box descriptor pointer, hurt-box centre x, y | [R] [L] |
| +128 byte (players) | **lives**, BCD (the HUD draws `+128 - 1`, `$1e86`) | [R] [L] |
| +129 (players) | the character chosen on the select screen; `$a13c` copies it to `+20` | [R] |
| +134 (players) | P1 score, BCD in hundreds (`$ff85ee`; HUD 300, 600, 1600 in 6 of 6 screenshots) | [R] [L] |
| +184, +188 | pointers to the animation's per-frame x and y step tables (`$c0d8`, `$c0ea`): motion is driven by tables | [R] |

Position writers of player 1 over frames 1790-2200 [L]: the camera-window clamp `$8e46`/`$8e58` (410 each) and
the step integrator `$c0e6`/`$c0f6` (286 each); Bred's position by the partner-follow code `$41cc`/`$41d2` and
`$4206`/`$420e` (19 each) and by `$27dbc`/`$27de4` (17 each, not read). `$8e46` is **not** a scroll compensation:
it clamps the player into the camera window, x in `[cam + $18, cam + $168]`, y in `[camy - $40, camy + $d0]`, and
subtracts the overshoot from `+6`, `+10` and `+14` (and from a held partner). The camera is `1042(A5)`
(x) and `1046(A5)` (y); `$ff8412` rose from `$012a` to `$03b2` while Cody walked right [L].

## Health, lives and the HUD

Reader first. The player HUD routine `$1eca` (A4 = the player record, called per player from `$1244` and
`$5b1cc`) reads `28(A4)` and `24(A4)` at `$1f72` and draws an 18-tile bar at `$908590 + 128 k` (P1; `$909290` for
P2), 8 health per tile: full tiles `$4560`, a partial tile for the remainder r (table `$2078`, `$4567`..`$4561`),
damaged variants for health lost from the maximum (table `$2088`) and empty tiles `$4568` (`$2098`). The tile run
decodes to `+24` in 1100 of 1100 frames (idle Cody, Bred hitting him, frames 2201-3300) and to `+26` in 1092 (the
shadow lags a frame); Cody went 144, 140, 128, 124, 120, 116, 112, 108, 96 and the bar followed every step
(`py/hpcheck.py`). The bar is pixel exact: the yellow run in the screenshot is `+24` pixels wide, 256 of 256 and
117 of 117 frames for Cody, 237 of 237 for the enemy bar at lag 1 (`py/hudbar.py`, `py/hudenemy.py`).
A bar object at `$15854` also reads `+24` (`$158ea`, 60 of 60 frames) and compares it to a displayed value; how
it relates to the tile bar of `$1eca` was not resolved. The enemy bar does not read the record: `$28d0` pushes
an 8-byte entry (record pointer, `+24`, `+26`, `+28`) into a ring at `644(A5)` (player 2: `772(A5)`; write
index `900(A5)`, read index `902(A5)`) and the HUD task `$5b240` pops it, which is why the enemy bar and name lag
a few frames and can show the previous enemy [R] [L].

Writers of `+24` [L, frames 2200-4300]: `$7a12` (13 hits on Cody, unscaled), `$79fe` (13 hits on enemies,
scaled by `+55`), `$db68` (2 grapple strikes), `$3fae` (1 halving, 28 to 14) and `$3a44` (record clears); others
exist and were not seen (`$7bd6`, `$7bec`, `$7a02`, `$7a32`, `$3fa2`, `$3fb4`, `$22c38`, `$6630`). A write tap
on Cody's `+24` over 1100 frames shows 8 writes, all from `$7a12` (`sub.w D1,24(A3)`, an idle run), and with no
input there is no write in 60 frames [L]. There is no clamp at the write: Bred went `$0003` to `$fff9`; the
state handlers then see `+24 != +26`, enter the hit-reaction state (`3(A6) := 4`; `$a6d6` for Cody, `$2701a` and
`$22c44` for enemies) and call `$b8a` for a negative word. `+26` is rewritten one frame later by `$a6e2`/`$a8b6`
(13 of 13 after Cody's hits). After death `$a1d2` refills `+24` and `+26` from `+28` (1 of 1).

Lives: the death countdown `$a5ee` decrements `+128` at `$a600` after `$53b2`; at zero it clears `0(A6)` and
`1(A6)` and sets state 6 (`$c840`, game over or continue, not read), otherwise it calls `$1e5a` (the lives
HUD) and `$a144` (respawn). Live, with lives poked to 5 and health to 0: state byte 4 at frame 2415, `+128` 5 to
4 at 2475 and health refilled to `$90`, the HUD digit changed from 1 to 3 only at that redraw (1 of 1;
`lua/poke_hp.lua`).

## Hit and hurt boxes

`$32c4` rebuilds a record's boxes each frame (called from `$8cc4` for the players and `$3382` for the other
records; 11162 calls in 1300 frames [L]) [R]. From the record: attack box = `A0 + (byte45 & $7f) * 16 + word(A0)`
with `A0 = 56(A6)`, none if `+45` is 0 or if bit 7 is set while the record is airborne (`14 != 10`); hurt box =
`A0 + byte44 * 8`, none if `+97` is set. A box entry is dx, dy, half-width, half-height (words) and, for an
attack, `+8` the damage-table index, `+11` bit 7 (hard hit) and `+12` a sound id. The centre is `y + dy` and
`x + dx`, mirrored (`x - dx`) when `+46` is non-zero. `$ff85dc` (`+116` of Cody) is therefore the attack-box centre
x, which is why it tracked x + 12 while walking and moved in the kick animation.

Live (`py/boxcheck.py`, frames 2201-3300): re-deriving `112`, `120` from `56`, `44`, `45`, `46`, `97` and the ROM
matches 1100 of 1100 frames for Cody and Bred, `124`/`126` 545 of 545 (Cody) and 1100 of 1100 (Bred), `116`/`118`
118 of 118 for Bred. Cody has no attack box in that run, so his offence side is derived only; two separate runs
agree on the field writers (`$32dc`/`$32f2` write 112, `$3310`/`$3320` write 120, `$3344`/`$336a` write 116,
`$32fe` 118, `$3356`/`$337c` 124, `$332c` 126).

## Hit resolution

Candidates are queued first, then tested. A record is added to a player's victim list (`21250(A5)`) or attacker
list (`21306(A5)`; player 2: `21354` and `21410`) when the attacker has `+45` set, the candidate has `+44` set,
the candidate's x is within 128 of the player, and its ground line `14(A6)` is inside a depth lane around the
player's: `[-12, +9]`, or `[-24, +24]` when the player is airborne (`139(A6)`, set by `$8d70`) (`$33c4`,
`$33f2`, `$3578`) [R]. Only tags 2, 4 and `$a` are eligible (tables `$3410`, `$3596`). `$6f6c` walks the lists
(up to 21 entries, reset at `$6fde`) and calls `$708e` (player attacks, A1 player, A3 victim) or `$7564` (enemy
attacks), which test `45(A1)` and then `$7932`.

`$7932` is the overlap test, A1 attacker and A3 victim, Z clear for a hit: with `dx = 124(A3) - 116(A1)` and `s =
hw(attack) + hw(hurt)` the x axis passes iff `((dx + s) & $ffff) <= 2s`; the y test, same with `118/126` and the
half-heights, runs only if x passed [R]. Replayed against 818 live calls: 818 of 818 agree that the y word is
written iff x passed; 63 calls reached the y test and the prediction matched all 63 (44 predicted overlaps had
their effect, 30 damages or `+60` writes and 14 grab completions at `$754e`; 19 predicted misses had none;
`py/hitcheck.py`, rerun fresh this pass). The body-versus-body variant `$7984` (centres `116/118` on both sides)
serves player-versus-player contact from `$78c6`; `$7766` and `$2934` are not read.

## Damage dispatch

Both dispatchers index a word table by the pool tag (tag / 2, 11 entries) [R]:

| table | tag 2 | tags 4, 6, `$12` | tag `$a` | other tags |
|---|---|---|---|---|
| `$70ae` (`$708e`, victim `18(A3)`) | `$70c6` | `$736e` | `$70e6` | `$70c4` (`bra *`) |
| `$7584` (`$7564`, attacker `18(A1)`) | `$75d0` | `$75d0` (tags 4, 6) | `$759c` | `$759a` (`bra *`) |

The two `bra *` entries are assert traps that the eligibility filter makes unreachable.

- `$70c6`, a pool-2 victim, dispatches on the kind (table `$70d4`): kinds 0, 3, 4, 5, 7, 8 to the standard
  handler `$736e`, kind 1 `$73b8`, kind 2 `$73e4`, kind 6 `$7456`. `$736e` stores the attacker in `+60`, the attack
  id in `+22` and `11(A2)` in `+63` (negative takes the knockdown variant `$74aa`), then calls the hit sound
  `$7b10`, the scaled damage `$79d8`, the spark `$7b18`, sets hit-stop `23(A1) = 23(A3) = 6`, calls `$7aa8` and
  `$28d0` (the HUD queue). Live: `$7374` 12 times (kind 0), `$740c` once (kind 2).
- `$75d0`, a fighter hitting Cody: the same shape with the unscaled damage `$7a04`, then `exg A1,A3; jsr
  $28d0`. Live: 13 of 13.
- `$70e6` (a tag `$a` victim, kind table `$70f4`): the default `$7156` is the breakable-prop hit (1 live hit on
  kind 5); kinds 1, 9, 12-14 have their own handlers, kinds 11 and 15-17 a bare `rts`. `$759c` (a tag `$a` attacker,
  table `$75aa`): kind 2 fixed damage 50, kinds 16-18 damage 40, kind 15 a distance table; not exercised live.
- A negative attack id (`45(A1)` bit 7) is a grab: `$74ee` (table `$74fc`: tag 2 `$7520`, tag 4 `$7512`) sets `64(A1) =
  1`, `68(A1) = A3`, `64(A3) = $ff`, `68(A3) = A1`. 14 grab overlaps and 14 `$754e` completions live.

The damage amount is `byte[92(victim-or-attacker) + 8(attack box)]` (`$7a04`, unscaled; 8 of 8 drops from Bred
on Cody, 4 4 12 4 4 4 4 12, and 26 of 26 hits over the longer run); when the victim's `+55` is non-zero
`$79d8` replaces it with `word[$cea74 + (base << 6) + 2 * def]` (10 became 8 for classes 4 and 6). Other helpers:
`$7a18` 1 point and `$7a1e` one eighth (minimum 1) for the player-versus-player path `$782a`; `$7bba` damage for
thrown and carried objects (from `$6e28`); `$7b18`/`$7b30`/`$7b48`/`$7b60` spawn a spark at the midpoint of the two
box centres. Grapple strikes use the table at `$db6e` (2 of 2, `$db68`, 4 steps per row), and `$3f7a` is the
release damage of the linked partner (a kill threshold, a halving, then a flat amount from `$3fd8`; live: one
28 to 14 halving matching the Cody row `18/62/40`; that it is a throw is **[I]**; its callers were not searched).
Cody hitting Bred during a grapple is not a box overlap (no attack box in those states, 0 predicted, drops
observed): the grab path applies it.

## The per-frame updates

All thirteen callees of `$5668` run every frame [L] (`lua/hitcount.lua`). `$5668` starts with
`A6 = $ffb228`. Roles are from the bodies [R]:

| routine | role |
|---|---|
| `$5764` | `jsr $2b7c` (controller input into `92/94(A5)`, then each player's input byte `+130`, previous `+131`; demo playback when `130(A5)` is set), then `$5780` per player: unused records are skipped, a held player (`+64` negative) runs the holder's routine from `$57c4`, otherwise `jmp $a558` (the player state machine, table `$a566`); ends `jsr $8c6e` (camera-window clamp, box refresh `$32c4`, the rectangle for the candidate lists) |
| `$5b1cc` | HUD manager, state word `$ff1312`: state 1 draws both panels (`$1eca`, `$14e8`), state 2 keeps the enemy bar objects at `-27884(A5)` and `-27628(A5)` fed from the ring at `644(A5)` and the last-hit pointers `302(A5)`/`1452(A5)` |
| `$5aea` | the stage spawn script (above) |
| `$5acdc` | the single record at `$ffb228` |
| `$90fa` | camera-triggered sound-cue script (A6 = `21634(A5) = $ffd482`): entries compare the camera and call `$9d0`, which enqueues a sound command in the ring at `388(A5)`; `$9b2` writes `$800180`. Its state byte was 6 (ended) in every run, so it did nothing |
| `$57f2`, `$5848`, `$5962`, `$59a4`, `$5a1a`, `$5a72`, `$5fc6`, `$5ff4` | the pool updaters of the table above; each calls the kind handler for every live record |

## Sprite list (`$16600`)

`$16600` builds the CPS1 object list for the next frame and swaps buffers [R] [L]. `158(A5)` holds `$9000` or
`$9040`, the high byte pair of `$900000` and `$904000`, and the VBL handler stores it to CPS-A `$800100` (`$584`).
At the end of `$16600` the value is flipped (`$16668-$16674`); the first lines clear the stale tail of the buffer
about to be written (`144(A5) = $100` entries, the previous count kept at `148(A5)` or `154(A5)`), and `$1667c`
drains lists at `$ffd290`, `$ffd03e`, `$ffd080`, ... through `$16850`/`$1680c`. A tap on `$900000-$907fff`
over frames 2150-2154: 928 writes, 464 into each of the two buffers, all from `$16a36`, `$16a38`, `$16a3a`,
`$16a3c` (228 each: the four words of one object entry) and `$16656`/`$16658` (8 each: the stale-tail clear)
[L]. The same VBL handler (`$53e`) reads its inputs and copies the scroll values; `kernel.md` lists the rest.

## Not read, not proven

- `$6026`'s other states and its table `$604a`, `$61e24` and `$6241e`, `$27fc4`, `$2934`, `$7766-$7920`
  (player-versus-player), the kind handlers `$73b8`, `$73e4`, `$7456`, `$711a`, `$71a2`, `$7222-$7232`, the
  `$a558` states other than state 2, the continue screen (`22188(A5)`, state 6 `$c840`), and the producer of the
  enemy-bar ring.
- What pools 4, 6, `$12` and `$14` hold, and pool 8: none was live in stage 1; the first boss or a later stage is
  the way to get them. Player 2 was inactive in every run (its record is `$1eca`-shaped by [R] only). Names for
  the three unnamed tag-`$a` props, for the pool-8 record, and AXL's confirmation.
- The relation of the `$15854` bar object to the `$1eca` tile bar.
- The TIME table per stage and area, and what happens at TIME 0.
- The difficulty counter's role is **[I]** from the code shape, with no live check beyond its initial values.

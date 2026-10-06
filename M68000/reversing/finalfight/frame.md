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
| `jsr $6026` | `A6 = $ffb1a8` (`12712(A5)`, a 64-byte record with tag `$10`), dispatches on byte `2(A6)` (table `$604a`), then `jmp $27fc4`; skipped while `299(A5)` is set. `$27fc4` parks unused player records at the camera (`+6,+10,+14` from `1042/1046(A5)`) and, while `-28332(A5)` (kind 0-2 alive count) is non-zero, refreshes one formation-slot flag per player and frame through `$2804e` (`ai.md`, "`$27fc4`"; [R], flags [L]). Its states, the 14-byte entries, the spawner `$61a8` (variants `$6278-$62f6`) and the tables are in `placement.md` | [R] [L] |
| `jsr $61e24` | stores the active-player mask (bit 0 of each player record's first byte) in `21610(A5)`, then updates the two **camera** records at `1036(A5)` and `1164(A5)` (`+6`, `+10` are the camera x and y `1042/1046(A5)`; the players are at `1384(A5)` and `1576(A5)`) by their state byte `2(A6)` (dispatch table `$61e5a` for the first, a routine at `$6241e` for the second); state 0 spawns the area-bound markers, state 2 runs the GO-arrow timer (`placement.md`, "The camera records") | [R] [L] |
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
is read as stage * 4 + area (stage 0 has the three areas 30, 30, 50; the full mapping and the stage order are in `transitions.md`). From frame 1677, when the scripted intro has ended,
`$5238` increments `176(A5)` once per frame and at `$1e0` (480 frames, about 8.05 s at 59.63 Hz) clears it and
decrements `175(A5)` with `sbcd` (`$5266`) and redraws through `$559a`. The tap saw the single decrement at
frame 2156 (`$ff80ae <- $2929`), 1677 + 479, and the saved state holds `175(A5) = $29` with `176(A5) = 43 =
2200 - 1677 - 480`. The HUD of that frame shows "TIME 29" (`gameplay.png`): 1 of 1 [L] [S]. `$559a` writes the
two digits as tile words at `$909014` (the second digit 256 bytes lower, 8 KB higher for player 2's HUD when
`21417(A5)` is set) from a tile table at `$55f4` with attribute `$186` [R]. A second countdown, `$52b6`, uses a
60-frame period and on reaching zero sets `297(A5) = 1` and phase 6; phase 6 does not call it, the bonus-stage frame (phase `$e`, `$5000`) does: a 60-frame tick, 30 ticks live, and at 0 the stage ends without a death (`transitions.md`) [R] [L].

`$5238` skips the count while `298(A5)`, `297(A5)` or `291(A5)` is non-zero, and at TIME 0 calls `$51de` (reload
`174(A5)` from `186(A5)`, redraw) and `$5298` for each player record [R]: it kills them (`63 := 3`, health `$ffff`) and spawns the pool-8 kind `$25` TIME OVER banner. Live with an idle
Cody from a cold boot: TIME 00 at 16077, at 16557 TIME reloaded to 30, banner, fatal knockdown, state 4 at 16649, respawn with lives 2 to 1 at 16709 (7 of 7, `transitions.md`) [L].

## Difficulty counter

`$5326` (`168(A5)` the rank, `172(A5)`, `276(A5)` the frame counter, `180(A5)`, `188(A5)`): initialised at `$5464` from a byte table
at `$54ac` indexed by `134(A5)` (168, 170 and 188 all take the value, 4 here) and `172(A5) := 135(A5)` (1 here)
[L, frame 1200]. Each frame without the flags `290/291/297/298(A5)` it adds 1 to `276(A5)` and, when that
reaches the limit `word[$536a + 2*172(A5)]` (600, 600, 480, 300 frames for `172(A5)` 0..3), resets it and raises `168(A5)` by one up to the
ceiling `word[$5372 + 2*172(A5)]`; other entry points subtract table amounts (`$5386`, `$53b2`, `$53dc`) down to a floor
`188(A5)`. In Service Mode `$554e` prints `168`, `172` and `276` on the screen. Live in `ff_enemies` (`172(A5) = 1`): the rank rose from 8 at
frame 4151 to 10 after 1501 frames and to 13 after 3001 (+1 per 600 frames, 2 of 2) [L]. Its readers: `$3e88` caps the number of live
fighters per kind by the rank (`ai.md`), and a stage-script entry whose level byte is `$ff` gets `169(A5)` (the rank's low byte) as `+96`, which
indexes the fighter's health, defence class, damage column and attack-roll masks (`ai.md`) [R] [L]. The stage change lowers it (`$5382` subtracts `word[$53aa + 2*172(A5)]`, 1 here: 18 to 17 at frame 11595 [L], `transitions.md`); the death drop `$53b2` was not
triggered; `134/135(A5)` are probably the difficulty DIP bytes (not checked against `hardware.md`) **[I]**.

## The object pools

All game objects are `$c0`-byte records handed out by per-pool free stacks, tagged by the byte at `+18`
(constant over a pool, set at build time, kept by empty records) [R] [S]. `+19` is the kind: the index of the
handler a pool's updater calls. Most pools sit in one run from `$ff8568`; three do not. The census of
`ff_enemies` [S] (`py/poolcensus.py`, array index = pool-local index + 2 in pool 2) and what each updater
walks [R] [L]:

| tag | records, base | updater | contents |
|---|---|---|---|
| (players) | 2 at `$ff8568` | `$5764` | player 1, player 2 (active only after a two-player start or a join, `twoplayer.md`; the character is `+20`) |
| 2 | 13 at `$ff86e8` (`1768(A5)`) | `$57f2` | fighters: enemies and bosses, 9 kind handlers: 0 `$21cec` (BRED, DUG, JAKE, SIMONS), 1 `$2813a` (J, TWO.P), 2 `$2a310` (AXL, SLASH), 3 `$2ccac` (the ANDORE family), 4 `$3136c` (G.ORIBER, BILL BULL, WONG WHO), 5 `$3514c` (HOLLY WOOD, EL GADO), 6 `$389b8` (ROXY, POISON), 7 `$3c446`, 8 `$3c48e` (roles in `ai.md`); the only damage-taking pool apart from `$a` |
| 6 | 6 at `$ff90a8` | `$5962` | weapons: 6 kinds (`$57a76`, `$5828e`, `$58b1c`, `$5935e`, `$5957a`, `$59b2e`); a drop byte `>= $24` creates kind `byte - $24`; kinds 0, 1, 2 are picked up by Cody with Button 1 (`$9c72`; 3 of 3 [L]), kinds 3 and 4 can never be picked up (`74` is never 0; `player.md` "Weapons"): kind 3 is the EDI.E gun bullet (a flying 40-hp projectile) and kind 4 (`$5957a`) is the fire bottle of the tag-2 kind 8 fighter, which a player's attack can deflect in flight (`ai.md`, "The bottle and the fire"); a tag-2 kind 5 fighter draws a kind 0 weapon; HUD names by kind: KNIFE, MURAMASA!, PIPE, SHELL, BOTTLE, ARROW; a stage-0 run saw kind 0 three times, kind 2 once and kind 4 twice (`placement.md`, "Weapons") |
| 4 | 8 at `$ff9528` (`5416(A5)`) | `$5a1a` | the bosses: eight kinds through the long table at `$5a52` (0 DAMND `$3d3d6`, 1 SODOM, 2 EDI.E, 3 ROLENTO, 4 ABIGAIL, 5 BELGER, 6 the BOSSTEST dummy, 7 a scene object), allocator `$390a`, free `$38f0`; DAMND is record 7 (`$ff9a68`), live from the first frame of stage 0 area 2 [L]; `boss.md` |
| 8 | 30 at `$ff9b28` (`6952(A5)`) | `$5848` | 60 kind handlers from `$1a1f0`: scenery and event objects, created by the placement lists, the camera records and other handlers. Kind 1 (`$0300` in `+20..+21` is ch 3 of the tile-patch objects, x `$518`) is an invisible tile-patch object, 2 the GO arrow, 3 the screen shaker, `$f` a door opener, `$15` a ceiling lamp, `$22` an area-bound marker, `$23` the door gang; the table is in `placement.md`, "Pool 8 kinds". Records 56 and 57 of the array are live already in `ff_gameplay` [S]. Fighter helpers create three kinds [L]: `$34` (`$20f4e`, follows its owner's x and ground line while it falls in), `$1f` (`$1f3b0`, the ground shadow of an ANDORE-family fighter), `$1b` (`$1f1a4`, a 180-frame marker that follows a respawned player, role [I]) |
| `$10` | `$ffb1a8` and `$ffb1e8`, 64 bytes each | `$6026`, `$5aea` | the placement record and the stage-script record (below) |
| `$c` | one `$c0` record at `$ffb228` (`12840(A5)`) | `$5acdc` | a scripted scene actor, three types (table `$5acf2`); never in use in any run **[I]** |
| `$a` | 16 at `$ffb2e8` (`13032(A5)`) | `$59a4` | breakable props: 19 kinds (`$515a6` to `$551e2`), named by the game's text `$5bbaa` (0 DOOR, 1 DRUMCAN, 2 CHANDELIER, 3 BILLBOARD, 4 FREIGHT, 5 DUSTBIN, 6 BARREL, 7 TIRE, 8 TEL.BOOTH, 9 and 11-14 GLASS, 10 DRUMCAN, 15 GRANADE, 16-17 FLAME, 18 WHEELCHAIR; 8 of 8 live HUD checks); kind 5 (hp 0, one hit breaks it, +500 on break [L]); stage 0 places kinds 1, 4, 5, 6, 7, 8 (`placement.md`); the break calls the drop routine `$5a934` (explicit item or weapon from `+21`, random row of `$5a9e0`, or a 10,000-point item when the killer presses a direction or jump on the kill frame, [L] 1 of 1), break awards per kind and the hit handlers are in `player.md` |
| `$e` | 271 records of 64 bytes at `$ff3000`, handed out in groups of 6 by `$5a72` | `$5a72` | effects: kind 0 is a hit spark created on the frame of each hit on Cody (8 of 8); kinds 1 and 3 seen |
| `$12` | 10 at `$ffbee8` | `$5fc6` | pickup items: `+20` = type 0 to 35 (`$9b88`), heal `$80`, `$40`, `$20`, `$10` for types 0-2, 3-7, 8-12, 13-19 (to a cap of `$90`) or, at full health and for types 20 to 34, a score of 10,000, 5,000, 3,000 or 1,000 (24 of 24 [L]); created by the prop break `$5a934`, by placement type 18 and by pool-4 kind 2; item names `$5bee2` (`placement.md`); one kind handler (`$5a55a`) |
| `$14` | **30** at `$ffc668`, 64 bytes (`$998e`, `D2 = $40`) | `$5ff4` | debris: kind 0 `$563dc` a flying piece, kind 1 `$56e44` a glass shard; created by prop breaks, the player's area-intro and area-clear scripts and DAMND (44 pieces in a stage-0 run to the boss trigger [L]; `placement.md`, "Pool `$14`") |

The allocators are `$3892` (tag 2), `$38ce` (6), `$390a` (4), `$3946` (8), `$3982` (`$a`), `$39be` (`$12`), `$39fa`
(`$14`); the effect allocator is `$3a96`. Earlier text called `$ffb1a8` the last record of one 60-record array
and treated the pools as one array; that was wrong: the `$c0`-spaced run `$ff8568-$ffb1a7` holds the players
and tags 2, 6, 4 and 8 only, and the remaining pools have their own bases and strides.

**Stage script executor `$5aea`.** The enemy and prop spawns are read from a script [R]: `$5aea` keeps a script
pointer at `6(A6)` of `$ffb1e8`, chosen from `190/191(A5)` (stage, area) through the tables at `$5f5e` and `$5f7e`. The live set is
`$5f7e`: `$5b12` takes it because the ROM word `$726e0` is 2 [R]; `$5b0a-$5b2a` index it by `190(A5)*4` and `191(A5)*2`. A script is a mode
word (which camera coordinate the triggers compare with) followed by segments and commands (`$5b6a-$5c2e`). A segment is a trigger word,
a 12-byte header (three words, a flag word, a long continuation pointer) and 16-byte entries up to a word with bit 15 set; state 2
(`$5b4e`) waits for the camera to pass the trigger and spawns the entries through `$5e36 -> $5e84 -> $5ee6` [R]. Entry layout, offsets from
the entry start: `+0` delay in frames, `+2` track flag (non-zero: the segment waits for the record to die), `+4` x word, `+6` y word (bit 15
set: the low 15 bits plus a random value in -15..+15), `+8` pool tag (2 `$3892`, 4 `$390a`, `$a` `$3982`), `+9` kind to `+19`, `+10/+11` to
`+20/+21`, `+12` to `+54`, `+13` to `+98`, `+14` to `+96` (negative: `169(A5)`), `+15` two-player-only (skipped unless both players are
live, `$5f46`). For tag 2 `$3e88` first applies the per-kind spawn cap (`ai.md`, difficulty). `$61a8` is a different spawner (byte 6 selects
the pool: a word table `$61b6` indexed by the even byte 6: 2 tag 2, 4 tag 4, 6 tag 6, 8 tag 8, 10 tag `$a`, 12 the `$ffb228` slot, 16 `$ffb1e8`, 18 tag `$12`, 20 tag `$14`; byte 7 becomes `+19`,
word 8 `+20`, byte 12 `+96`) fed by the placement record `$6026` (`placement.md`) [R]. Live: the script pointer moved from `$70676` to `$70684` at frame
3223, when the camera x reached `$3f0` (the entry's trigger), and a tag-2 record was created at `$5ee6` 94 frames later, 1 of 1 [L].
`py/ai_kind45/script.py` decodes the set.

**Fighter identity.** The name on the HUD is built by `$5b640`: `A0 = $5b6fc + word[$5b6fc + 2*kind] + 32*(+20)`, 16 tile words
(`$4400` plus ASCII after a 6-word header) [R]; `$5b4aa` only clears byte 1 of the HUD record and is not the selector. The table, by `+20`: kind 0
BRED, DUG, JAKE, SIMONS; kind 1 J, TWO.P; kind 2 AXL, SLASH; kind 3 ANDORE JR., ANDORE, G.ANDORE, U.ANDORE, F.ANDORE; kind 4 G.ORIBER,
BILL BULL, WONG WHO; kind 5 HOLLY WOOD, EL GADO; kind 6 ROXY, POISON; kinds 7 and 8 index the same rows as kind 5 (`$212`), so the name
shown for them is HOLLY WOOD or EL GADO whatever the handler is [R] (kind 8 was seen on screen with HOLLY WOOD's name and a different sprite,
`ai.md`). AXL is therefore confirmed by name (kind 2, `+20 = 0`), no longer inferred from HUD order. Live HUD names matched to `+19/+20`:
BRED, DUG, JAKE (earlier screenshots, 5 of 5, 4 of 4, 6 of 6) and G.ORIBER, BILL BULL, WONG WHO, HOLLY WOOD, EL GADO (one screenshot each from
spawned records, `ai.md`). `92(A6)` is the damage table, not the character record: `$2fa2` sets it to the record base + `$60` + the level `+96`
(HOLLY WOOD level 0 `$37be0` from the record `$37b80` [L]; BRED `$23f8c`, DUG `$24f2a`, JAKE `$25ed0` are the same kind of pointer **[I]**), and the damage value is read
from it (below).

## The player and fighter record

Offsets from the record base `A6`, for the players and for pool 2 [R] unless tagged:

| offset | meaning | evidence |
|---|---|---|
| +0 | non-zero = in use (bit 7 set means new: the pool-2 updater `$57f2` skips such a record for one frame and clear the bit, so a spawn's init runs on the second frame [L] for kind 0). `+1` is not "in use": `$8dfa`/`$8e00` clear and set it, a visible/blink flag during invulnerability **[I]** | [R] [S] |
| +2, +3 | state byte and sub-state; the player state byte takes the values 0, 2, 4, 6, 8, 10, 12 (table `$a566`: 0 `$a574` spawn, 2 `$a64e` alive, 4 `$a5aa` dying, 6 `$a62e` inactive, 8 `$dc08` area intro, 10 `$e8e8` area clear, 12 `$c840` scripted scene); state 2's sub-states are the 18-entry table at `$a7a6`, and `$a5b6` is the 2-entry sub-table of state 4 (`player.md`) | [R] [L] |
| +6 word, +8 word | x (integer, fraction); `add.l D0,6(A6)` adds a 16.16 step | [R] [L] |
| +10 word, +12 word | y (integer, fraction); `$c0f6` writes it | [R] [L] |
| +14 | copy of y (`$c046`): the ground line; the depth lane test compares it | [R] |
| +18, +19, +20, +21 | pool tag, kind, `+20` the character byte within the kind (kind 6: 0 ROXY, 1 POISON), `+21` the entrance type byte; the script entry's bytes 8-11 are copied here by one `move.l 8(A3),18(A4)` (`$5f24`) | [R] [L] |
| +24 word | **health**, +26 shadow of the last-seen health, +28 maximum (Cody `$90` = 144, Bred `$1c`), set together at spawn by `$2fa2` from the data record at `92(A6)` (7 spawns of each) | [R] [L] |
| +44, +45 | hurt-box index, attack-box index (bit 7 set = grab attack); +55 defence class | [R] [L] |
| +46 | facing, bit 0 = flip | [R] |
| +54 | animation frame index (set from script entry byte 12 at spawn; kind 6 uses it as the 0..31 walk heading); `56(A6)` points at the current animation's data (box blocks) | [R] [L] |
| +64, +66, +67, +68 | grab link: `64 = 1` and `68 = victim` on the holder, `64 = $ff` and `68 = holder` on the held; the follower copies the holder's position plus an offset from the table at `70(A6)` (`$41ba-$4230`) | [R] [L] |
| +92 | pointer to the character's data (damage table, `$23f8c` for Bred) | [R] [L] |
| +96, +97, +98 | `+96` difficulty level (script entry byte 14, `$ff` meaning `169(A5)`; kind 6 init overwrites it with the low byte of `168(A5)`) indexing the character data rows; `+97` non-zero disables the hurt box; `+98` (script entry byte 13) non-zero skips the spawn limiter `$3e88` and its later decrement | [R] [L] |
| +112 long, +116/+118 words | attack-box descriptor pointer (0 = none), attack-box centre x, y | [R] [L] |
| +120 long, +124/+126 words | hurt-box descriptor pointer, hurt-box centre x, y | [R] [L] |
| +128 byte (players) | **lives**, BCD (the HUD draws `+128 - 1`, `$1e86`) | [R] [L] |
| +129 (players) | the character chosen on the select screen; `$a13c` copies it to `+20` | [R] |
| +132..+135 (players) | score: an 8-digit BCD longword in points (`$ff85ec`, capped at 9,999,999); the low word `+134` (`$ff85ee`) read `$0300`, `$0600`, `$1600` against HUD 300, 600, 1600 in 6 of 6 screenshots; awards are queued through `$288c` (`player.md`) | [R] [L] |
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
scaled by `+55`), `$db68` (2 grapple strikes), `$3fae` (1 halving, 28 to 14) and `$3a44` (a record clear: the routine is `$3a1c`, called from the free routine `$3878`, which zeroes `+0..+127` and keeps `+78`); others
exist and were not seen (`$7bd6`, `$7bec`, `$7a02`, `$7a32`, `$3fa2`, `$3fb4`, `$22c38`, `$6630`). A write tap
on Cody's `+24` over 1100 frames shows 8 writes, all from `$7a12` (`sub.w D1,24(A3)`, an idle run), and with no
input there is no write in 60 frames [L]. There is no clamp at the write: Bred went `$0003` to `$fff9`; the
state handlers then see `+24 != +26`, enter the hit-reaction state (`3(A6) := 4`; `$a6d6` for Cody, `$2701a` and
`$22c44` for enemies) and call `$b8a` for a negative word. `+26` is rewritten one frame later by `$a6e2`/`$a8b6`
(13 of 13 after Cody's hits). After death `$a1d2` refills `+24` and `+26` from `+28` (1 of 1).

Lives: the death countdown `$a5ee` decrements `+128` at `$a600` after `$53b2`; at zero it clears `0(A6)` and
`1(A6)` and sets state 6 (`$a62e`, the inactive record; the continue screen is the separate scene `$5da78`, entered from phase 6 when `21416(A5)` is set, `player.md`), otherwise it calls `$1e5a` (the lives
HUD) and `$a144` (respawn). Live, with lives poked to 5 and health to 0: state byte 4 at frame 2415, `+128` 5 to
4 at 2475 and health refilled to `$90`, the HUD digit changed from 1 to 3 only at that redraw (1 of 1;
`lua/poke_hp.lua`).

## Hit and hurt boxes

`$32c4` rebuilds a record's boxes each frame (called from `$8cc4` for the players and `$3382` for the other
records; 11162 calls in 1300 frames [L]) [R]. From the record: attack box = `A0 + (byte45 & $7f) * 16 + word(A0)`
with `A0 = 56(A6)` and the word added sign-extended (`adda.w`; Poison's descriptors need it), none if `+45` is 0 or if bit 7 is set while the record is airborne (`14 != 10`); hurt box =
`A0 + byte44 * 8`, none if `+44` is 0 or `+97` is set. A box entry is dx, dy, half-width, half-height (words) and, for an
attack, `+8` the damage-table index, `+11` bit 7 (hard hit) and `+12` a sound id. The centre is `y + dy` and
`x + dx`, mirrored (`x - dx`) when `+46` is non-zero. `$ff85dc` (`+116` of Cody) is therefore the attack-box centre
x, which is why it tracked x + 12 while walking and moved in the kick animation.

Live (`py/boxcheck.py`, frames 2201-3300): re-deriving `112`, `120` from `56`, `44`, `45`, `46`, `97` and the ROM
matches 1100 of 1100 frames for Cody and Bred, `124`/`126` 545 of 545 (Cody) and 1100 of 1100 (Bred), `116`/`118`
118 of 118 for Bred. Cody has no attack box in that run, so his offence side is derived only; two separate runs
agree on the field writers (`$32dc`/`$32f2` write 112, `$3310`/`$3320` write 120, `$3344`/`$336a` write 116,
`$32fe` 118, `$3356`/`$337c` 124, `$332c` 126). The same rule re-derived over the live player, fighter and boss records of 127 saved work-RAM dumps (state byte 2): attack boxes 51 of 52, hurt boxes 212 of 213, and 216 of 216 and 55 of 55 absent boxes; the one miss is a hand-spawned kind 7 boss on its first frame, before its boxes are built (`infographic/py/boxes_gate.py` [S]). `infographic/finalfight_hit_detection.html` draws these boxes over two MAME frames and the blow tables of the three characters.

## Hit resolution

Candidates are queued first, then tested, and the whole queue hangs off the two players. Once per frame `$8d70` (from `$8c6e`) writes each player's candidate rectangle into words 6, 8, 10, 12 of the victim-list descriptor (`21250(A5)`; player 2 `21354(A5)`): lane low `-12`, lane high `+9`, x offset `$80`, x width `$100`, or `-24`/`+24` while the player's sub-state `3(A6)` is `$10` (the special; `$8d1e` sets `139(A6)` for exactly that sub-state, so a jump attack does not widen the lane), and all zero while the player's state byte `+2` is not 2 or `+22` is non-zero. The rectangle equals that rule for 115 of 115 active player records in 127 saved dumps and is zero for the 26 of 26 others (`infographic/py/lanes_gate.py` [S]); the `+-24` case is [R] only. Every other record calls `$3382` after rebuilding its boxes, and `$33c4` offers it to each player: to the victim list (`21250(A5)`) when the player has an attack box (`+45`) and the candidate a hurt box (`+44` set, `+97` clear), to the attacker list (`21306(A5)`; player 2 `21354` and `21410`) when the candidate has an attack box and the player a hurt box (`$33c4`, `$33f2`, `$3578`) [R]. A victim candidate of tag 2 or 4 (`$3428`) must satisfy `(x - player x + $80) <= $100` unsigned, that is within 128 px, and its ground line gap `14(A6) - 14(player)` must lie in the rectangle's lane (`>= 0` up to `+9`, negative down to `-12`); a tag `$a` prop (`$3466`) takes its lane limits from the per-kind word table at `$34c4` (two pairs per kind, 0 to 48 px, the second pair while `139(player)` is set) instead; other tags return at once. The attacker list uses the fixed `+-128` and `[-12, +9]` for tag 2 (`$35ae`); the tag 4 and tag `$a` variants (`$3688`, `$35ec`) were not read. The tables `$3410`, `$3596` admit only tags 2, 4 and `$a`. A fighter never appears as a victim of another fighter's box: the lists exist only for the two players, and fighters hurt each other only through props, thrown bodies and the bottle and fire (`$639e`, `$6c7a`) [R].

**One blow lands once** (`$3386-$33a0`, `$8cc8-$8cdc`): a victim handler leaves the attacker in `+60` and the blow id in `+22`. While `+22` is non-zero and the attacker (`+60`) is in use with an attack box (`+45`), a non-player record returns from `$3382` before it is offered to any list, and a player's rectangle is zeroed (`$8d84`); once the attacker's attack box ends the next pass clears `+22`. Of 17 records with `+22` set in 127 saved dumps, 13 had the attacker's box still on and 4 had it already off, consistent with the clear running on the next pass [S] [I]; a live count of one hit per multi-frame blow is not made. `$6f6c` walks the lists
(up to 21 entries, reset at `$6fde`) and calls `$708e` (player attacks, A1 player, A3 victim) or `$7564` (enemy
attacks), which test `45(A1)` and then `$7932`.

`$7932` is the overlap test, A1 attacker and A3 victim, Z clear for a hit: with `dx = 124(A3) - 116(A1)` and `s =
hw(attack) + hw(hurt)` the x axis passes iff `((dx + s) & $ffff) <= 2s`; the y test, same with `118/126` and the
half-heights, runs only if x passed [R]. Replayed against 818 live calls: 818 of 818 agree that the y word is
written iff x passed; 63 calls reached the y test and the prediction matched all 63 (44 predicted overlaps had
their effect, 30 damages or `+60` writes and 14 grab completions at `$754e`; 19 predicted misses had none;
`py/hitcheck.py`, rerun fresh this pass). The body-versus-body variant `$7984` (centres `116/118` on both sides)
serves player-versus-player contact from `$78c6` (the clash of two hard attack boxes). The player-versus-player path `$7766-$7920` (gates, the lane window, 1 hp per soft hit, the 100-frame immunity `+148`, the award to the attacker) and `$2934` (the partner's health into each player's HUD ring) are read and run live in `twoplayer.md`.

## Damage dispatch

Both dispatchers index a word table by the pool tag (tag / 2, 11 entries) [R]:

| table | tag 2 | tags 4, 6, `$12` | tag `$a` | other tags |
|---|---|---|---|---|
| `$70ae` (`$708e`, victim `18(A3)`) | `$70c6` | `$736e` | `$70e6` | `$70c4` (`bra *`) |
| `$7584` (`$7564`, attacker `18(A1)`) | `$75d0` | `$75d0` (tags 4, 6) | `$759c` | `$759a` (`bra *`) |

The two `bra *` entries are assert traps that the eligibility filter makes unreachable.

- `$70c6`, a pool-2 victim, dispatches on the kind (table `$70d4`): kinds 0, 3, 4, 5, 7, 8 to the standard
  handler `$736e`, kind 1 `$73b8`, kind 2 `$73e4`, kind 6 `$7456` (stores `105`, `60`, `22`, `63` like `$736e`, then calls the dodge hook `$3a454`; a non-zero return ends the handler with no damage; see `ai.md` "Kind 6"). `$736e` stores the attacker in `+60`, the attack
  id in `+22` and `11(A2)` in `+63` (negative takes the knockdown variant `$74aa`), then calls the hit sound
  `$7b10`, the scaled damage `$79d8`, the spark `$7b18`, sets hit-stop `23(A1) = 23(A3) = 6`, calls `$7aa8` and
  `$28d0` (the HUD queue). Live: `$7374` 12 times (kind 0), `$740c` once (kind 2).
- `$75d0`, a fighter hitting Cody: the same shape with the unscaled damage `$7a04`, then `exg A1,A3; jsr
  $28d0`. Live: 13 of 13.
- `$70e6` (a tag `$a` victim, kind table `$70f4`): the default `$7156` is the breakable-prop hit (1 live hit on
  kind 5); kinds 1, 9, 12-14 have their own handlers, kinds 11 and 15-17 a bare `rts`. Kind 1 (DRUMCAN) `$711a` takes the default path when the prop's variant `128(A3)` (placement byte 10) is below 2; for variant 2 and up it damages and sparks with hit-stop 6 but sets no attacker flags, gives no award (`$7aa8`) and queues no HUD entry: these are the six opening-scene barrels (cold boot, frames 1 to 1900: `$711a` 6, `$7156` 0, `$7aa8` 0 [L]). Kind 11 (GLASS) ignores every hit. Kinds 12 and 13 accept a hit only when the attacker's facing byte `46(A1)` is 0 (12) or non-zero (13), kind 14 always; the accepted hit (`$7232`) spawns a pool-8 kind `$2d` effect, subtracts the attack-box damage (`$72fc`; `$1e` for a hard hit when `22184(A5)` flags the player) from `+24` clamped at 0, and a zero-damage hit bounces the attacker. Live in bonus stage 1: 12 of 12 hits on the kind 12 pane from the left (health `$8c` to `$14`, break +5000); kinds 11, 13 and 14 were not reached. Kind 9 (the bonus 2 car pane) `$71a2` calls `$53182`: a broken pane (`136(A3)`) hurts the attacker for 1 and bounces it; otherwise the ground-line difference `dy` takes 2 from the counter `133(A3)` (`dy` < 3), 1 (`dy` < 7) or nothing; live 2 of 2 hits then the break (+100, +1000). The break sound of every prop is read from the table `$7348` by kind (`$7334`). `$759c` (a tag `$a` attacker,
  table `$75aa`): kind 2 fixed damage 50, kind 16 (the fire) `$764c` and kinds 17-18 `$768e` fixed damage 40 with reaction 8, kind 15 a distance table;
  the fire's 40 was run live on Cody (7 of 7, `ai.md` "The bottle and the fire"), the others are [R]. The same props also hurt pool-2 fighters through `$639e` (table `$63ca`).
- A negative attack id (`45(A1)` bit 7) is a grab: `$74ee` (table `$74fc`: tag 2 `$7520`, tag 4 `$7512`) sets `64(A1) =
  1`, `68(A1) = A3`, `64(A3) = $ff`, `68(A3) = A1`. 14 grab overlaps and 14 `$754e` completions live.

The damage amount is `byte[92(victim-or-attacker) + word(attack box +8)]`, where the box `+8` word is a row offset (`$00,$20,$40,$60`: rows of 32 bytes) and `92` already holds the variant column (`$2fa2` adds `+96` and `$60` at spawn; `ai.md`, 59 of 59 kind-0 hits) (`$7a04`, unscaled; 8 of 8 drops from Bred
on Cody, 4 4 12 4 4 4 4 12, and 26 of 26 hits over the longer run); when the victim's `+55` is non-zero
`$79d8` replaces it with `word[$cea74 + (base << 6) + 2 * def]` (10 became 8 for classes 4 and 6). Other helpers:
`$7a18` 1 point and `$7a1e` one eighth (minimum 1) for the player-versus-player path `$782a`; `$7bba` damage for
thrown and carried objects (from `$6e28`); `$7b18`/`$7b30`/`$7b48`/`$7b60` spawn a spark at the midpoint of the two
box centres. Grapple strikes use the table at `$db6e` (2 of 2, `$db68`, 4 steps per row), and `$3f7a` is the
landing damage of a thrown fighter (a kill threshold, a halving, then a flat amount from `$3fd8`: Guy 15/45/30, Cody and Haggar 18/62/40; live: one 28 to 14 halving earlier, and 4 of 4 throws of Dug with hp 60, 10, 80, 82 ending at 30, dead, 40, 42, writer `$3fa2`, [L]).
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
| `$90fa` | camera-triggered sound-cue script (A6 = `21634(A5) = $ffd482`): entries compare the camera and call `$9d0`, which enqueues a sound command in the ring at `388(A5)`; the pump `$984` in the VBL handler writes one command per two frames to `$800180` (`kernel.md`, "The two deferred rings", with the sound id table). Its state byte was 6 (ended) in every run, so it did nothing |
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

## The screen shaker (`$1b428`, pool 8 kind 3)

One shaker record exists at a time (flag `-27916(A5)`, record pointer `-27920(A5)`). `$1b428` starts it or restarts it; the kind 3 handler `$1b478` then moves the camera for 28 frames [R] [L]:

```
$1b428: if !flag: rec = alloc8($3946); rec.in_use = 1; rec.kind = 3; rec.+96 = 0; ptr = rec; flag = 1; return
        rec = ptr; rec.+2.w = 0 (restart); d = rec.+96; rec.+96 = 0
        if d < 0: apply(rec.+20, -d)                               // undo the pending offset
apply(ch, d): ch 0: camY(1046(A5)) += d ; ch 2: camY += d, cam2Y(1174(A5)) += d ; ch 4: 918(A5) -= d, 1116(A5) += d, camY += d
$1b478 state 0: +2 = 2 ; +96 = 4 ; +30 = 7 ; +31 = 3 ; +20 = axis(stage 190, area 191)
        state 2: if --31 == 0 { 31 = 4; if --30 == 0 { +2 = 4; +96 = 0; return }; +96 = word[$1b55c + 2 * 30] }   // 1 1 1 2 2 2 3 4
                 +96 = -+96 ; apply(+20, +96)                      // every frame
        state 4, 6: flag = 0; free ($392c)
```

The axis `+20` comes from the table `$1b592` by stage and area (stage 0: 0, 2, 0; stage 1: 2, 0, 0, 2; stage 3: 0, 4; every other area 0) except stage 2: area 0 gives 0, or 2 once the camera x is `$100` or more; area 1 gives 2; area 2 gives 2 for camera x in `[$980, $c20)`, else 0. The amplitude does not depend on the caller: the signed offsets alternate, so the displaced frames carry 4, 3, 3, then 2 six times and 1 four times (13 frames) and the pair of steps cancels; the record lives 28 frames (Haggar's pile driver 1986 to 2014, DAMND's death 11262 to 11290 [L]). The camera y reaches the CPS-A scroll registers two frames later: the rendered playfield (rows 32 to 223) shifted by exactly the logged camera y in 35 of 35 frames for each axis. Axis 0 moves scroll 2 y (`$800112`) and every sprite (the sprite builder subtracts the camera y); axis 2 also moves scroll 3 y (`$800116`, through the second camera record); axis 4 (stage 3 area 1) moves `918(A5)`, which `$61f86` copies to the scroll 1 y shadow, and `1116(A5)`, the camera y copy that area compares against (the jitter was seen on `1116(A5)` live, 26 frames; the scroll 1 side is [R]).

Callers (13 call sites of `$1b428`; `py/engine/` gates `shaker`, `shake_sites`, `haggar`, `edi`): Haggar's pile driver `$d17a` and jump slam `$d3ae` (below); the kind 3 (ANDORE family) entrances 8, 10 and 12 at `$2d0c2`, `$2d178`, `$2d352` (the drop-in landing, [L] one run each, five subs for entrance 8), its aimed-leap landing `$2de58` (the end of attack sub-state 18: a shock test on both players, damage `byte[92(A6) + $20]`, hit type 3; [L] 13 in 16000 frames for ANDORE, 4 each for G., U. and F.ANDORE) and its carry slam `$2ed96` (hit type 5; [L] 10); the kind 4 entrance 8 landing `$315e0` ([L] 3 of 3 subs); the pool-4 deaths of DAMND `$3ed0e` ([L] 1), SODOM `$426d8` ([R]), EDI.E `$477bc` ([L] 1, hand spawn) and ABIGAIL `$4d550` ([R]); and the ending scene object `$184b2` ([R]). The sum of the live hits at the sites equals the hits of `$1b428` in every run.

Haggar's damage does not come from the shaker. The pile driver (`$d128`, sub-state 8 of his grapple, step `$d14c`) and the jump slam (`$d37c`, step `$d386`) first call `$d9b6` or `$d9e2`, then the award, the HUD push `$28be`, the sound `$aaa` and `$1b428`:

```
$d9b6 pile driver:  hp <= $18: hp = -1 ; hp <= $64: hp >>= 1 ; else hp -= $32      // 50
$d9e2 jump slam:    hp <= $1e: hp = -1 ; hp <= $8c: hp >>= 1 ; else hp -= $46      // 70
```

Ten victim health values (`$300 $65 $64 $19 $18` for the driver, `$300 $8d $8c $1f $1e` for the slam) matched in 10 of 10 runs, each with a shaker created.

## Not read, not proven

- `$61e24`'s camera follow and lock (`transitions.md`; its first lines compute the in-use mask `21610(A5)`, `twoplayer.md`), and the producer of the enemy-bar ring (the tag-`$a` victim handlers are in "Damage dispatch"). (`$27fc4` refreshes the formation
  slot flags, `$73b8` and `$73e4` are the kind 1 dodge and kind 2 guard victim handlers, `$7456` the kind 6 one, `ai.md`;
  the continue screen is `$5da78` and `22188(A5)` is the attract-demo flag, `player.md`.)
- Pool 8's kinds are all read in `placement.md` ("Pool 8 kinds"); pool 4 is the boss pool, `boss.md`. Player 2, mid-game joining and two-player play were run live (`twoplayer.md`). The fighters of kinds 1 to 8 were
  exercised in spawned records (`ai.md`); stage 0 was also played by a bot, 18 of 18 script entries (`py/stage/`).
- The relation of the `$15854` bar object to the `$1eca` tile bar.
- The difficulty counter's falling side (`$5382` at a stage change is in `transitions.md`; `$53b2`, `$53dc` are not exercised) and its effect with two players (`ai.md` has the rising side and its readers).

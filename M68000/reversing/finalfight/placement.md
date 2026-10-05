# The placement path and the other pools of a played stage

Where the objects of a level come from besides the stage script of `frame.md`: the placement tables read by `$6026`, who creates every record of every
pool in a played stage 0, and what the pool 8, `$a`, 6, `$12` and `$14` records are. Evidence tags as in `kernel.md`: **[R]** read in the ROM, **[L]** live in
MAME with a count, **[S]** read from a saved state, **[I]** inferred. `A5 = $ff8000`. Everything live comes from a stage-0 play (`py/stage/run.sh boss`, the
bot of `lua/stagebot.lua`, Cody poked to full health; see the README there) logged by `py/placement/` (`README.md` there lists the scripts and the gate).

## Two spawn paths

A level's records are created by two independent engines that feed the same pools. The stage script (`$5aea`, `frame.md`) spawns tag-2 fighters (165
entries over all stages) and 15 tag-`$a` props (stage 3 area 0) [R]. The placement path (`$6026`) spawns everything else and also many fighters: bosses,
scenery objects, props, weapons, items, and the tile-patch and door objects of pool 8. In stage 0 the script supplies 18 fighters (`census.py` 18 of 18)
and the placement tables 9 fighters (8 spawned, 1 refused by the cap), 17 props, the pool-8 objects and the boss [L].

## `$6026` and the placement record

`$6026` runs once per frame from phase 6 (`$4e66`), is skipped while `299(A5) != 0`, runs `$603c` on `A6 = $ffb1a8` (`12712(A5)`, a 64-byte record of tag
`$10`) and ends with `jmp $27fc4` (the formation-slot refresh of `ai.md`) [R]. The record: `+2` state byte (0, 2, 4, 6; table `$604a`: 0 `$6052`, 2
`$609a`, 4 and 6 `rts`), `+32` long cursor into the active trigger list, `+36` word mode.

```
placement():                          // $603c
  switch (A6->state)
    0: state = 2                      // $6052
       for (e = init_list(stage, area); e->w0 >= 0; e += 14) spawn(e)   // init list: the trigger word is not read ($6066-$6076)
       p = ($726e0 != 0) ? $6346 : $631e                                  // $607a; the word at $726e0 is 2 in this ROM
       p = long[p + 4*stage]; p += word[p + 2*area]
       mode = *p++; A6->mode = mode; A6->cursor = p
    2: p = A6->cursor                 // $609a, mode word 0/2/4/6 -> $60e6 / $60b8 / $6126 / $6156
       loop:
         w = *p
         if (w < 0) { if (w == $8000) { mode = p[1]; p += 2 words; continue }   // change of mode
                      state += 2; return }                                       // any other negative word ends the list
         if (!reached(mode, w)) { A6->cursor = p; return }
         spawn(p); p += 14                                                      // the result of spawn is ignored
       reached: mode 2: w <= camX (1042(A5)); mode 0: w <= camY (1046(A5); stage 3 compares 1116(A5));
                mode 4: w >= camY; mode 6: w >= camX
```

Because the cursor advances whatever `spawn` did, an entry that the cap `$3e88` or an empty pool refuses is lost for the area, not retried.

Evidence: the state and cursor writes of `$ffb1a8-$ffb1e7` over a played run [L]: per area `$9b06` clears the record (frames 1315, 5563, 7808), `$6052` sets
state 2 two frames later (1317, 5564, 7809), `$60b2` sets state 4 on the frame the last entry is consumed (4375, 5566, 8266); the cursor sits at
`$6d10c` (stage 0 area 0's list after its mode word) while it waits. The area start itself is `$961e`: a flag table `$964a` per (stage, area) (all areas of
stages 0 to 5 are flagged) decides whether `$982a` re-initialises every pool and both script records, so each area begins with empty pools [R]; the
`$9b06` clears above are that re-initialisation [L].

An **init list** is spawned entirely at area start whatever its first words say: stage 0 area 1's eight entries, whose first words are `$650`, `$650`,
`$66e`, `$600` and 0, all spawned in the first frame with the camera at `$650` (8 of 8 [L]); DAMND's entry (first word `$af0`) spawned at the start of area 2 with
the camera at `$900` (1 of 1 [L]). A **trigger list** spawns an entry on the first frame the camera passes its first word (mode 2): all 17 trigger-list
spawns of stage 0 came within 1 to 3 camera pixels of their trigger [L]. Only mode 2 occurs in stage 0; modes 0, 4 and 6 are read from the code only [R]
(mode 0 is used by stage 3 area 1 and stage 5 area 0).

## The 14-byte entry and the spawner `$61a8`

| offset | meaning |
|---|---|
| +0 word | trigger (trigger lists only: compared with the camera, bit 15 marks the end or a command) |
| +2, +4 words | x, y; bit 15 set: the low 15 bits plus a random -15..+15 (`$3c26 & $1f - $f`) |
| +6 byte | spawner type, an even value indexing the word table `$61b6` (below) |
| +7 byte | kind, stored in `+19` |
| +8, +9 bytes | stored in `+20` and `+21` (character or variant, entrance type or drop byte) |
| +10 byte | `+54` (animation frame index) |
| +11 byte | `+98`; for tag 2 a non-zero value skips the spawn cap `$3e88` |
| +12 byte | `+96`, the level; negative: `169(A5)` |
| +13 byte | two-player-only: skipped unless `1384(A5) & 1576(A5)` is non-zero (`$6306`) |

`$61a8` dispatches on byte 6 through `$61b6` [R]:

| byte 6 | routine | allocator and pool |
|---|---|---|
| 0, 14 | `$61cc` | none (`rts`) |
| 2 | `$61ce` | `$3892`, tag 2 fighters; first the demo flag `22188(A5)`, `$6306`, and `$3e88` (kind in `+7`) |
| 4 | `$6278` | `$390a`, tag 4 |
| 6 | `$6288` | `$38ce`, tag 6 |
| 8 | `$6298` | `$3946`, tag 8 |
| 10 | `$62a8` | `$3982`, tag `$a` |
| 12 | `$62b8` | the single `$ffb228` record, if free |
| 16 | `$62ce` | the `$ffb1e8` record, if its `+0` is 0 (no table uses it) |
| 18 | `$62e6` | `$39be`, tag `$12` |
| 20 | `$62f6` | `$39fa`, tag `$14` |

Every path then runs `$61f8`: `+0 = 1` (a new record, so its handler starts on the second frame), x, y, `+19`, `+20`/`+21` as one word, `+54`, `+98`, `+96`.

Live: 46 entries were processed in stage 0; 44 spawned with every field equal to the entry (pool, kind, `+20`, `+21`, x, y, and `+96`, the rank where the
entry byte is `$ff`); the other two were never created: 06d136 (kind 1 at trigger `$190`) was refused by `$3e88` at frame 2638 (`D0 = 1`, `$ff1154 = 3`,
rank 5 against the cap `byte[$3eda + 5]`, the three door-gang fighters being alive; 1 of 1), and 06d210 (a DRUMCAN with `+13 = 1`) never spawned in a
one-player run (1 of 1) [L]. The two sets of tables differ in two entries only (stage 5 area 1: `+54` and `+98` swapped) [R]; `$631e`/`$5f5e` are not used here.

## The tables

Stage `s`, area `a`: a long pointer table at `$6346 + 4*s` (trigger lists) and `$636e + 4*s` (init lists) gives a block whose first words are word offsets to
the areas' lists. A trigger list is `mode.w`, entries, `$ffff`; an init list is entries up to a word with bit 15 set. Stage numbers are the stage byte
`190(A5)`, which is not the play order after stage 1 (`py/stage/README.md`).

| stage | init lists, areas 0.. | trigger lists, areas 0.. |
|---|---|---|
| 0 | `6ecfa`, `6ed96`, `6ee08` | `6d10a`, `6d1a8`, `6d200` |
| 1 | `6ee4a`, `6ee84`, `6eea2`, `6eeb2` | `6d260`, `6d2d4`, `6d460`, `6d528` |
| 2 | `6eee4`, `6ef9c`, `6f046` | `6d532`, `6d5b4`, `6d60c` |
| 3 | `6f0e6`, `6f158` | `6d6d8`, `6d936` (mode 0) |
| 4 | `6f186` | `6da46` |
| 5 | `6f1fe`, `6f22a` (empty), `6f22c` | `6e2a0` (modes 2, 0, 2), `6e6f0`, `6e9a2` |

`py/placement/dumpplace.py` prints every entry; `summary.py` the per-area counts. Bosses are init-list entries of type 4, spawned at area start: stage 0 area 2
pool-4 kind 0 (DAMND, x `$b98` y `$3f`), stage 1 area 3 kind 1, stage 2 area 2 kind 2, stage 4 area 0 kind 4, stage 5 area 2 kind 5; stage 3 area 1 places
kind 3 from its trigger list (mode 0, camera y `$980`). Pool-4 kind 7 is placed by no table: its one allocator site is `$f1ca` in player code [R]. Entries
of type 12 (the `$ffb228` actor, three types) sit in the init lists of stage 3 area 1, stage 4 area 0 and stage 5 area 0 [R]. Items (type 18) are placed in
stage 3 area 1 and stage 5; weapons (type 6) in stage 2 area 1, stage 3 area 1 and stage 4; the stage-0 lists place none [R].

## Everything created in stage 0

Write taps on the in-use word of every pool record give the pc that creates each record; joined to a census taken every frame from frame 1316, all 118 records
first seen up to the boss trigger (frame 8298) have a creator, and all 159 up to the stage byte becoming 1 (frame 11595) [L].

| creator pc | what it is | records to 8298 (+ to stage 1) |
|---|---|---|
| `$61f8` | placement spawner: pool 2 (8), pool 4 (1), pool 8 (18), pool a (17) | 44 |
| `$5ee6` | stage script, pool 2 | 8 (+10) |
| `$1fb36` | kind `$23`: the three door fighters | 6 |
| `$1d14e` | kind `$f` creates kind `$23` | 2 |
| `$62a46`, `$62a86` | the two area-bound markers (kind `$22`) from the camera record's state 0 | 3 + 3 |
| `$61526` | the GO arrow (kind 2) from the camera record | 3 |
| `$453e`, `$4680` | pool 14 debris: 32 and 12 | 44 (+24 at `$4680`) |
| `$5a9aa`, `$5a972` | prop drops: pool 6 (3), pool 12 (1) | 4 |
| `$35506` | a pool-2 kind 5 fighter's weapon | 1 (+1) |
| `$3d414`, `$3d180`, `$1b438`, `$595fa` | DAMND's overlay, the bottle thrower's bottles, the screen shaker, fire | (+1, +2, +1, +2) |

Records that resemble script spawns but are not: the 3 + 3 pool-2 kind-0 fighters with entrance type 7 (frames 2516 and 3911) are the
door gangs; the pool 2 kind 1 and 2 entries with `+21 = 2` and the kind 0 entries with `+21 = 4` and `6` are trigger-list entries (area 2 and area 1); the
pool-4 record DAMND is the init entry above, not a script entry.

## The camera records `$61e24` and `$6241e`

`$61e24` updates the records at `1036(A5)` and `1164(A5)` (`$ff840c`, `$ff848c`), by their state byte `+2` (table `$61e5a`: 0 `$61e5e`, 2 `$61e8e`; the second
record through `$6241e`). They are the **camera** records: `+6` and `+10` are `1042(A5)` and `1046(A5)`, the camera x and y; the player records are at
`1384(A5)` and `1576(A5)`. State 0 sets the idle timer `60(A6) = $1a4` (420), copies x and y into `+78`/`+80`, calls the camera setup `$62bce` and spawns the two
kind `$22` markers (`$62a34`: stage byte below 6; x, y from the word tables `$62ac2` and `$62b16`, four bytes per area). State 2 calls `$614e4`, which
does nothing while `290(A5)` is set, `50(A6) = 2` or `42(A6) = 6(A6)`; otherwise a set lock `278(A5)` or a moved camera (`56(A6) != 6(A6)`) reloads the
timer to 420, and an unlocked, unmoved camera counts `60(A6)` down and at 0 creates pool 8 kind 2 (the GO arrow) and reloads 420. Live: the arrow appeared at frames 3060, 3480 and 6195, the first two 420 apart (1 of 1 interval) [L]. The camera follow and the lock
are in `transitions.md`.

## Pool 8 kinds

Pool 8 is 30 records of `$c0` bytes at `$ff9b28`, updater `$5848`, 60 handlers from `$1a1f0` (table `$5872`). The kinds placed in the stage-0 tables or created
by their handlers:

| kind | handler | role |
|---|---|---|
| 0 | `$1a1f0` | dispatch on `+20`; a timed cycle of the top nibble of the tile code words at `$914000` (`$1a2fa` loop), no sprite (hide test: no change) [R]; not run in the other sections |
| 1 | `$1aa5c` | **tile patch object**, invisible; `+20` is the patch id 0..17 (below) |
| 2 | `$1b2ec` | **GO arrow**: 4×4 tiles written at `$909528` (two tile sets and a clear set, 20/7/20 frame steps) for 240 frames, cue `$3b`; hiding the record changes no pixel (tiles, not a sprite) |
| 3 | `$1b478` | **screen shaker**, one instance (flag `-27916(A5)`), created by `$1b428` (callers in player code, the ANDORE family and the boss handlers); its `+96` shake value alternates sign and is applied by dispatch on `+20` [R]; created once in the played run, with A6 = DAMND (`$ff9a68`) at frame 11263 [L] |
| `$f` | `$1d0f2` | **door opener**: four tile patches (`$4872`, 4×8 tiles, tables at `$1d186`) every 7 frames, then creates kind `$23` with its own `+20`; ch 0 at x `$228`, ch 1 at x `$3b8`, y `$b8` |
| `$13` | `$1d92a` | seen once, in the frame before the stage starts; not read |
| `$15` | `$1e1bc` | **ceiling lamp**: a fluorescent fixture drawn at the top of the screen (hide test: an 80×30 px sprite at the HUD line, for ch 0 and 1 of area 1 at x `$70e` and `$78e`); animation by a gfx RAM word at `$914000` |
| `$17`, `$21` | `$1e520`, `$1f562` | **cast of the opening scene**, placed by area 0's init list at x `$190`..`$1c8`: the hide test at frames 1325 and 1400 gives the kidnapper (`$21` ch 0, 85×110 px) carrying the hostage (`$17`, 45×74 px) and two thugs (`$21` ch 1, 2); dispatch on `+20` selects the cast member [L] [R] |
| `$1e` | `$1f32e` | follows its owner (`128(A6)`, DAMND), draws through `$32a2` only while `-27896(A5)` is non-zero; created by `$3d414` (DAMND) and `$4ff2c` (pool-4 kind 5); the sprite was not seen (hide test of the record: no change) [R] |
| `$22` | `$1fa5a` | **area-bound marker**, two per area from the camera record: ch 0 at the area's left edge writes `$1400` into the attribute word of an 80-tile block at its x, y (via `$477a`, base `$90c000`) at once; ch 1 at the right edge does the same with `$0c00` when the camera x passes `1078(A5) - $20` (the first camera record's `+42` word). 80 words each: ch 0 at frames 1317, 5565, 7810; ch 1 at 4406 and 7723 [L] |
| `$23` | `$1faf6` | **door gang**: three tag-2 kind-0 fighters (characters 0, 1, 2 = Bred, Dug, Jake; `+54` 0, 1, 2; `+96` 0; entrance type 7) at x `$240` (ch 0) or `$3d0` (ch 1), y `$3f`; each through `$3e88` (kind 0), so a full cap leaves some out; then frees itself. Frames 2516 and 3911, 6 of 6 fighters [L] |
| `$1f` | `$1f3b0` | ground shadow; created by pool 6 kinds 0, 1, 2, 5, pool `$12`, and ANDORE (`$2ccec`) [R]; not seen live |
| `$34`, `$1b` | | `frame.md` |

The other kinds placed in stages 1 to 5 (`summary.py` lists them per area: 6, 7, 8, 9, `$a`, `$b`, `$c`, `$d`, `$e`, `$10`, `$11`, `$16`, `$18`, `$2a`,
`$2b`, `$30`, `$3b`) were not read.

### Kind 1: tile patches

`+20` selects a row of `$1ab14` (data), `$1abb8` (routine) and `$1ac00` (width, height in tiles). State 0 clears flag `$ff12de + ch` and waits until its own x, y
is inside the camera window (`$49dc`, camera at `1042/1046(A5)`, or `$4a08` for the second camera), checked every fourth frame; then every eighth frame it
waits for the flag, applies the patch once at its own x, y, and frees itself. The patch routines rewrite the tile map (`$477a`: base `$90c000`; `$47a6`:
base `$910000`):

| routine | writes | ch |
|---|---|---|
| `$4872` | code word `+ $3000` and attribute (keeps the flip bits cleared by `& $ff9f`) | 0, 1, 2, 16 |
| `$4840` | only the priority bits of the attribute (`& $fe7f`, or data) | 3 to 7, 14, 17 |
| `$47ea` | code words only (`+ $3000`) | 8 |
| `$4814` | 32-bit code and attribute (`+ $3000`) | 9, 10, 11 |
| `$493a` | attribute bits, second-camera test | 12, 13 |
| `$490e` | 32-bit words (`+ $980`), second-camera test | 15 |

Width × height (tiles): ch 0 2×8, 1 2×8, 2 7×8, 3 7×`$b`, 4 3×`$a`, 5 3×`$a`, 6 7×`$b`, 7 8×8, 8 2×4, 9 to 11 4×9, 12 and 13 1×8, 14 2×`$10`, 15 2×2, 16 2×`$a`,
17 4×4. The flags are set by the player's scripted area-intro and area-clear code (states 8 and 10), by prop and boss handlers (setters at `$516c4`..`$5173c`,
`$3d444`, `$0185f6`, ...), and by a test-mode routine (`$635ec`: all 17 flags). In stage 0 all six patches that happened followed their flag write within 1 to 7
frames (6 of 6 [L]): flag 3 at 5435 by `$ee20` (patch `$4840`, 4 frames later), flag 0 at 5624 by `$dd6a` (`$4872`, 3), flag 4 at 5728 by `$dde6` (`$4840`, 5), flag 5
at 7723 by `$ef1c` (`$4840`, 1), flag 1 at 7727 by `$ef50` (`$4872`, 3), flag 6 at 7972 by `$df7c` (`$4840`, 7). A `$4872` patch of ch 0 or 1 writes 64 words,
the door patch of kind `$f` 128 words per step (taps of the patch routines [L]).

## Props (pool `$a`)

The HUD name is the game's text `$5bbaa` indexed by kind (`$5b640`, tag `$a` ignores `+20`): 0 DOOR, 1 DRUMCAN, 2 CHANDELIER, 3 BILLBOARD, 4 FREIGHT, 5 DUSTBIN, 6 BARREL,
7 TIRE, 8 TEL.BOOTH, 9 GLASS, 10 DRUMCAN, 11 to 14 GLASS, 15 GRANADE, 16 and 17 FLAME, 18 WHEELCHAIR [R]. Pushing a live record of kinds 8, 5 (three records,
`+20` = 1, 5, 2), 6, 4 and 7 into the HUD ring printed the matching name in 8 of 8 cases, as did DAMND (pool 4 kind 0) [L].

Stage 0 places kinds 1 (the six DRUMCANs of the opening scene, `+21 = $ff`: no drop; and one two-player-only DRUMCAN), 4, 5, 6, 7 and 8; all 17 props of
the one-player run were created by the placement spawner [L]. Pool-a kind `$a` (a second DRUMCAN) creates a tag-2 kind-0 fighter with entrance type 9 when
broken (`$5375a`) [R]. The fire is kind `$10`, created at `$595fa` by the landing bottle (pool 6 kind 4): 2 in the played run [L].

Drop (`$5a934`, `+21` of the prop): bit 7 clear: the item or weapon number itself; `$ff`: none; bit 7 set: the byte at `$5a9e0 + (+21 & $f)*32 + (LFSR & $1f)`, `$80`
none. A value below `$24` creates the pool-12 item of that type, otherwise the pool-6 weapon of kind value - `$24`. `py/placement/drops.py` prints the decode for every
`+21` the tables use. Live: a BARREL with `+21 = $24` dropped a KNIFE twice, the FREIGHT with `$26` a PIPE, a DUSTBIN with `$8e` (row `$e`: 30 distinct
drops and two nones) dropped item 30 [L].

## Weapons (pool 6) and items (pool `$12`)

Weapon HUD names (`$5babe`, kind then `+20`): kind 0 KNIFE (`+20` 1, 2: MURAMASA!, MASAMUNE!), 1 MURAMASA! (`+20` 1: MASAMUNE!), 2 PIPE, 3 SHELL, 4 BOTTLE, 5 ARROW [R].
Seen in stage 0: kind 0 three times (two barrel drops and one from a pool-2 kind 5 fighter at `$35506`), kind 2 once (the FREIGHT drop), kind 4 twice (the
kind 8 fighter's bottles at `$3d180`, which break into the kind `$10` fire) [L]. The kind 3 and 5 creators in player and boss code (`$a83e`, `$467d2`,
`$4fe00`, `$4fe52`, `$4fe9e`) are [R]. Item names (`$5bee2`, by `+20`): 0 BARBECUE, 1 STEAK, 2 CHICKEN, 3 HAMBURGER, 4 HOT DOG, 5 PIZZA, 6 CURRY, 7 SUSHI,
8 BANANA, 9 PINEAPPLE, 10 APPLE, 11 ORANGE, 12 GRAPES, 13 SOFT DRIN, 14 KSOFT DRIN, 15 K BEER, 16 BEER, 17 WHISKY, 18 BEER, 19 GUM, 20 DIAMOND, 21 GOLD BAR, 22 RUBY,
23 EMERALD, 24 PEARL, 25 TOPAZ, 26 NECKLACE, 27 WATCH, 28 DOLLAR, 29 and 30 YEN, 31 RADIO, 32 NAPKIN, 33 HAT, 34 HAMMER, 35 GUM, 36 DIE (spelled as in the ROM)
[R]; the heal and score of each type is in `player.md`. Type 30 was dropped once and the HUD printed YEN (1 of 1 [L]). The placement tables place items
only in stages 3 and 5 [R].

## Pool `$14`: debris

Pool `$14` is 30 records of 64 bytes at `$ffc668` (`$998e` with `D2 = $40`; updater `$5ff4`, 64-byte stride), allocator `$39fa`. Two kinds: 0 (`$563dc`)
a flying debris piece: `+20` type, `+21` piece index selecting an 8-byte row of initial velocities, `+54` mirror, `+60` a random 0..3; 1 (`$56e44`) a glass
shard (same layout). Creators, all [R] unless counted: `$4536` through `$451e`/`$4524` (props: BARREL 6 pieces, FREIGHT 6, and the player's area-intro script
`$dd74` twice with 7 pieces each), `$4632` through `$4622`, `$4678` through `$466a` (DAMND's handler at `$3d4b6`, `$3d4c6`, `$3d4d6`, `$3d4e6`: four calls of six; the
player's area-clear script at `$ef6e`, `$ef7e`, `$f122`, `$f132`), `$46de` through `$46b0` (the glass props), and `$62fc` (placement type 20, no table uses it).
Live: 14 pieces at frame 5625 (the area-1 intro, 2 calls of 7), 6 each at 6268, 6506 and 6948 (prop breaks), 12 at 7728 (the area-1 exit, 2 calls of 6), 24 at
8300 (DAMND at the camera trigger, 4 calls of 6) [L].

## Pool `$12`

Pool `$12` is 10 records of `$c0` bytes (`$ffbee8`), one handler (`$5a55a`), created by the prop drop (`$5a972`), by placement type 18 (`$62ec`) and by pool-4 kind 2
(`$4609e`). Item effects are in `player.md`.

## Not read or not proven

- The sprite of kind `$1e` and the live creation of kind `$1f`; kind 0's tile-cycle effect and kind `$13` are read only; the roughly 48 other pool 8 kinds.
- The setters of the tile-patch flags in prop and boss code, and what the attribute values `$1400` and `$0c00` of kind `$22` change on screen.
- What the word at `$726e0` is (it selects `$6346` and `$5f7e` over `$631e` and `$5f5e`; the live and the alternate set differ in two entries).
- Pool-4 kind 7 (the `$f1ca` spawn) and the placement types 12 and 16.
- Modes 0, 4 and 6 of the trigger lists were not run (stage 3 area 1 and stage 5).

## Saved states of the logging runs

`py/placement/gates.sh` saves `bb_<frame>` (1325, 1400, 2500, 3070, 3600, 4380, 5570, 7830) in its run directory. Work RAM sha256 prefixes after load: `bb_2500`
`4b51d232767d3e1d`, `bb_5570` `45902fe058ececd2`, `bb_7830` `6c27211dc54926af` (identical over two cold boots); `bb_1325` `b1d8ef4d5ab5379a`, `bb_1400`
`56670907262c0cff`, `bb_3070` `87085cbe77f7b167`, `bb_3600` `47c153f37153eea1`, `bb_4380` `ea83741891e8dcc3`.

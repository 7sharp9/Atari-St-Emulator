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
       p = ($726e0 != 0) ? $6346 : $631e                                  // $607a; $726e0 is the ROM region word (0 Japan, 2 USA, 4 World), 2 here
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
one-player run (1 of 1) [L]. The two sets of tables are the copies that the ROM region word `$726e0` selects (below); they differ in two entries only, both pool `$a` kind 10 DRUMCANs of stage 5 area 1 at x `$2010` (`+54` and `+98` swapped: live set `0`, `2`) [R] (`py/engine/regionsets.py`: the script copies `$5f5e`/`$5f7e` differ by 40 shifted pointers and nothing else); `$631e`/`$5f5e` are not used here.

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
kind 3 from its trigger list (mode 0, camera y `$980`). Pool-4 kind 7 is placed by no table: its one allocator site is `$f1ca`, in the area-clear walk-off of the player for stage 2 area 0 (below). Entries
of type 12 (the `$ffb228` actor, three types) sit in the init lists of stage 3 area 1, stage 4 area 0 and stage 5 area 0; type 16 has no entry in any list of stages 0 to 9 [R]. Items (type 18) are placed in
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

Pool 8 is 30 records of `$c0` bytes at `$ff9b28`, updater `$5848`, 60 handlers from `$1a1f0` (table `$5872`). The first table lists the kinds of the stage-0 tables and the objects their handlers
create; the two tables after it cover the kinds of stages 1 to 5 and every other kind:

| kind | handler | role |
|---|---|---|
| 0 | `$1a1f0` | **palette-RAM animation** (no sprite, no tile writes); `+20` 0 to 7 picks one effect. `$914000` is the palette source of CPS-A register `$80010a` (`hardware.md`, "CPS-A registers"; MAME `cps1_v.cpp` `m_cps_a_regs[CPS1_PALETTE_BASE] = 0x9140` and `cps1_build_palette`), so the top nibble of its words is the brightness nibble. Id 0 (stage 0 area 1): per-frame `$1a2e4` loop rewrites the nibble of 64 × 8 words (`$f000`, `$c000`, `$8000` from the table at `$1a336`, switched by the timer table `$1a28a`) and 16-colour lines at `$914940`/`$914c60` through `$47d0`; waits while a fade runs (`140(A5)`). Ids 2 to 6 (stage 2) are camera-threshold colour cycles of the lines `$914880/$9148a0` (cam `$280`, `$900`), `$914960/$914cc0` (`$200`, `$480`), `$914980`, `$914c20` and `$914ce0`; id 1 copies a block to `$914ca0` at cam `$12c0`, id 7 to `$9143e0`. [L] id 0: the palette changed in 45 of 59 frames (24,300 words) with the record and in 0 of 59 with it hidden, the screen differed in 82,723 px (`py/objects/gates.sh`); ids 2 to 5 sat in state 0 for 474 to 523 frames, ran 272 to 752 frames in state 2 and freed themselves at their cam threshold (stage 2 area 0 sweep) |
| 1 | `$1aa5c` | **tile patch object**, invisible; `+20` is the patch id 0..17 (below) |
| 2 | `$1b2ec` | **GO arrow**: 4×4 tiles written at `$909528` (two tile sets and a clear set, 20/7/20 frame steps) for 240 frames, cue `$3b`; hiding the record changes no pixel (tiles, not a sprite) |
| 3 | `$1b478` | **screen shaker**, one instance (flag `-27916(A5)`), created by `$1b428` (13 call sites; state machine, axes, amplitudes and callers in `frame.md`, "The screen shaker"); created once in the played run, with A6 = DAMND (`$ff9a68`) at frame 11262 [L] |
| `$f` | `$1d0f2` | **door opener**: four tile patches (`$4872`, 4×8 tiles, tables at `$1d186`) every 7 frames, then creates kind `$23` with its own `+20`; ch 0 at x `$228`, ch 1 at x `$3b8`, y `$b8` |
| `$13` | `$1d92a` | **scripted scenery step** created by the player's area-intro and area-clear scripts (sites `$17236` to `$18b30`, `$199e2` to `$19bce`); `+20` 0 to 10 selects a palette cycle (0 to 2: `$914740`, `$914a40`, `$914920`, 3 to 5 frame steps) or a one-shot or stepped tile patch (3 to 10: `$47ea`, `$48e2`, 18-frame steps) with its own timers [R]; not placed by any table |
| `$15` | `$1e1bc` | **ceiling lamp**: a fluorescent fixture drawn at the top of the screen (hide test: an 80×30 px sprite at the HUD line, for ch 0 and 1 of area 1 at x `$70e` and `$78e`); animation by a gfx RAM word at `$914000` |
| `$17`, `$21` | `$1e520`, `$1f562` | **cast of the opening scene**, placed by area 0's init list at x `$190`..`$1c8`: the hide test at frames 1325 and 1400 gives the kidnapper (`$21` ch 0, 85×110 px) carrying the hostage (`$17`, 45×74 px) and two thugs (`$21` ch 1, 2); dispatch on `+20` selects the cast member [L] [R] |
| `$1e` | `$1f32e` | follows its owner (`128(A6)`, DAMND), draws through `$32a2` only while `-27896(A5)` is non-zero; created by `$3d414` (DAMND) and `$4ff2c` (pool-4 kind 5); it is **DAMND's ground shadow**: with the flag held, hiding the record removes a 214 px band (46 × 5 px) under his feet [L] (`sb_boss`, `py/objects/gates.sh`); the earlier hide test showed no change because the flag was 0 |
| `$22` | `$1fa5a` | **area-bound marker**, two per area from the camera record: ch 0 at the area's left edge writes `$1400` into the attribute word of an 80-tile block at its x, y (via `$477a`, base `$90c000`) at once; ch 1 at the right edge does the same with `$0c00` when the camera x passes `1078(A5) - $20` (the first camera record's `+42` word). 80 words each: ch 0 at frames 1317, 5565, 7810; ch 1 at 4406 and 7723 [L]. The bits are invisible **terrain codes**, an invisible wall at each area edge ("Terrain codes" below) |
| `$23` | `$1faf6` | **door gang**: three tag-2 kind-0 fighters (characters 0, 1, 2 = Bred, Dug, Jake; `+54` 0, 1, 2; `+96` 0; entrance type 7) at x `$240` (ch 0) or `$3d0` (ch 1), y `$3f`; each through `$3e88` (kind 0), so a full cap leaves some out; then frees itself. Frames 2516 and 3911, 6 of 6 fighters [L] |
| `$1f` | `$1f3b0` | **ground shadow** (a record that copies its owner's x and ground line, drawn through `$3264`/`$36c6`); created by pool 6 kinds 0, 1, 2, 5, pool `$12`, and ANDORE (`$2ccec`) [R]. [L] stage 3 area 1, an ANDORE's shadow created at the fighter's spawn: hiding it removes 82 px (48 × 5 px) at the ground (`py/objects/gates.sh`) |
| `$34`, `$1b` | | `frame.md` |

Palette RAM is `$914000` (CPS-A `PALETTE_BASE`) and the tile maps are the scroll-1 map at `$908000`, the scroll-2 map at `$90c000` and the scroll-3 map at `$910000`
(`hardware.md`); the tile patchers of `$4700..$49dc` write the scroll-2 map (`$477a` address, `$47ea`/`$4814`/`$4840`/`$4872`/`$48aa`) or the scroll-3 map (`$47a6`
address, `$48e2`..`$49a4`, `$47d0`), windowed by camera 1 (`$49dc`, `1042/1046(A5)`) or camera 2 (`$4a08`, `1170/1174(A5)`). Every handler and its live count is in
`py/objects/` (`kindmap.py` lists the placement entries and creators of all 60 kinds, `digest.py` their calls and flags, `gates.sh` the counts below).

**Kinds placed in stages 1 to 5** (stage byte, area; `py/placement/summary.py` lists them per area). Live counts are frames per `state.mode.step` from area-poked runs
(`py/objects/area_sweep.sh`: `190/191(A5)` and the phase word `0(A5) := 4`, player 1 swept along the area) or, where a tile write is the effect, an A/B with the kind's records
zeroed (`ab.sh`).

| kind | handler | placed | role from the body | live |
|---|---|---|---|---|
| 6 | `$1b70c` | 2/2, six records `+20` 0 to 5 | 2-frame blinking 2×2 patch of the scroll-2 map: waits until it is on camera 1's window (`$49dc`, every 8th frame), then a random 1-to-5-frame timer (table `$1b762`) toggles `112(A6)` by 2 and `$47ea` writes the frame | 6 records state 0 for ~450 frames, then 2.x; A/B, camera parked: scroll-2 map changed in 124 frames (410 words), hidden 0 |
| 7 | `$1b846` | 2/1, ten records `+20` 0 to 9 | 2-frame flip of one tile pair in the scroll-3 map (`$47a6` address kept in `128(A6)`, `+$980` code offset), random 2-to-18-frame timer (table `$1b890`), no window test; freed with the area | 10 records, state 2 for 247 to 258 frames; scroll-3 map changed in 54 frames/95 words (rel 15 to 90) and 113/184 (100 to 250), hidden 0 and 0 |
| 8 | `$1b950` | 2/0 (x `$3f0`, `$6d0`), 2/2 (`$8a0`) | **solid barrier for airborne players**: every 4th frame, per active player with ground line `14 != 10`, tests a box from `128/130(A6)` and a per-character height (`$1b9a0`), moves the player to the box edge in x (or on top in y) and clears his `80/82/84` [R] | state 2 for 1,490 of 1,490 frames; the push itself was not run |
| 9 | `$1ba66` | 4/0, `+20` 0 to 2 (x `$10`, `$110`, `$210`) | 8-tile column of the scroll-3 map (8 frames, tables 128 bytes apiece) cycled on a random 10-to-25-frame timer (table `$1bada`) once camera 2's x reaches `$120`, `$220` or `$320` for `+20` 0, 1, 2 | 3 records, state 2 for 843 to 1,602 frames; scroll-3 map 44 frames/250 words, hidden 0 |
| `$a` | `$1bcb0` | 4/0, three records `+20` 0 (x `$7a8`, `$1058`, `$1ad8`) | 2×2 blink of the scroll-2 map, 3 frames, `$47ea`, random 2-to-11-frame timer (table `$1bd0c`); frees itself when its window test fails | `$7a8` state 0 for 508 frames then 2.0 11 / 2.2 339; scroll-2 map 37 frames/74 words, hidden 0 |
| `$b` | `$1bd72` | 3/1 (x `$d00`) | **elevator cage** foreground sprites: `+20` 0 creates `+20` 1 and 2 at the same place; `14 := $7fff` (never hit), drawn through `$3858`; piece 0 frees when `1116(A5) >= $b00` | 3 records live for 2,990 frames; hiding piece 0 removes 992 px (48 × 48, vertical bars), piece 1 939 px and piece 2 1,042 px (40 × 64 posts at the left and right edge) |
| `$c` | `$1bea2` | 3/0 (x `$c88`) | door-burst tile animation (scroll-2 map): waits for the flag byte `-27910(A5)` (`+20` 0) or `-27909(A5)` (`+20` 1), set by the DOOR prop's break (`$5171c`, `$51726`) and the script `$5d66`, then 5 patches 12 frames apart (`$48aa`, 4 rows of 11 or 10 tiles) | state 0 for 769 frames, 2.0 for 532; flag poked: 72 frames in mode 2, freed, scroll-2 map 4 frames/128 words, hidden 0 |
| `$d` | `$1c4d0` | 5/0 | stage 5 lobby elevator sequence: waits for camera x `$560`, then five modes, each started by one pulse of `22192(A5)` (set by the stage script at `$5ae58`..`$5b016`, answered with `$ff` while it runs) and playing a 6-row scroll-2 patch (12, 8, 3 and 13 columns by mode) in 8 steps of 18 frames; the last mode creates two kind `$19` pieces | state 0 for 525 frames, then the pulses: modes 0 to 8 in 5 of 5 pulses; scroll-2 map changed at rel 761 (66 words) and every 18 frames from 857 and back from 1037; two kind `$19` at 1145. A patch outside camera 1's window is skipped |
| `$e` | `$1cf50` | 1/0, four records (x `$11d0`, `$1210`, `$1390`, `$1510`) | train **door panels**: waits for camera x `$d0`, then the flag `-27908(A5)` (set by the camera hook at `$61848` when the train has stopped), and for each door inside camera 2's window (`0 <= x - 1170(A5) <= $18f`) writes four 4 × 4 scroll-3 patches (`$496c`, frames from the table at `$1d028`) 10 frames apart, then frees | idle 2,344 frames in 2.0 (flag never set); flag and camera-2 x `$1100` poked: two doors ran modes 2 and 4 (40 frames) and freed, two waited in mode 6; scroll-3 map changed at +12, +22, +32 (40/24/24 words), the screenshot shows the door panels |
| `$10` | `$1d392` | 3/0, `+20` 0 to 4 (x `$10`..`$410`) | 8-tile column of the scroll-3 map cycled through 4 frames every 15 frames until camera 2's x passes the `+20` threshold (`$120`..`$520`); then frees | 5 records state 2 for 360 to 942 frames; scroll-3 map 19 frames/760 words, hidden 0 |
| `$11` | `$1d590` | 2/0 (x `$670`) | one-tile scroll-3 lamp: tile changes when camera 2's x passes x - `$172`, - `$dc`, - `$64`; blinks between two tiles every 14 frames in the middle phase | 322 frames in state 0, then 29 / 37 / 30 / 676 in modes 0 to 6; the A/B shows 2 changed words more with the record |
| `$16` | `$1e2a8` | 1/2 (triggers `$f00`, `$fa8`) | **ceiling water drips**: `+20` 0 an emitter (within camera + `$190`, random 40 or 60-frame timer (table `$1e318`), creates a `+20` 1 drop at its x, y whose landing y is y - `+21`); `+20` 1 the drop (anim to its event byte, then falls with gravity `$18` to the landing y, splash anim, free); `+20` 2 a drop created by kind `$21` | 3 emitters live 325 to 428 frames in 2.2; about 20 drops of 54 to 137 frames each; hiding a drop in flight removes 17 px (4 × 6) |
| `$18` | `$1ecf8` | 1/1 (x `$500`) | **subway hand-straps**: `+20` 0 is a spawner that walks the table at `$1ee6a` and creates `+20` 1 children at y `$e0` as the camera nears each x; the children animate in sync (a chain through `132/136(A6)`) and switch animation when `1228(A5) == 4` and `1216(A5) == 0` (camera 2's hook); freed when off the left edge | spawner live 1,024 frames, 28 children of 185 to 187 frames; hiding 7 children removes 1,841 px in a 335 × 48 band |
| `$2a` | `$20182` | 3/1 (triggers y `$1d4`, `$5d4`) | **descending hoist**: waits 192 frames, descends 0.5 px per frame, at 1 px per frame creates a kind `$2c` grenadier at three 11-frame steps, then rises at 2 px per frame and frees at y `$110` (sounds through `$4b04a`) | two runs of 192 + 12/10/11/10/11/10/1 + 89 frames; three kind `$2c` each |
| `$2b` | `$202e0` | 3/1 | elevator-scene fade follower: waits for `1116(A5) == $b00`, then each frame copies the brightness nibble of palette word `$914000` to the 16 words at `$9147e0`; when it reaches 0 it blanks three scroll-1 areas with tile `$4420` and frees [R, the tail] | state 0 for 2,993 frames; poked: palette changed 75 words at +2, scroll-1 map 53/40/40 words; brightness 0 not reached |
| `$30` | `$20ce6` | 1/1, 2/1, 3/0 | **attract-demo hook**: with `22188(A5)` set it creates one tag-2 fighter of kind 4, 5 or 3 (by `22189(A5)`, fixed x, y), otherwise it frees itself in the same frame | 1 frame in state 0, then freed, 3 of 3 areas |
| `$3b` | `$21bdc` | 3/0 (`+20` 0), 5/2 (`+20` 1) | one-shot recolouring of scroll-2 patches (`andi #$3ff` / `or` of the attribute word): `+20` 0 at camera x `$630` (5 × 5 at `$7b8`,`$88` and 1 × 5 at `$808`,`$88`), `+20` 1 at `$3240` (7 × 2 at `$31b8`,`$818`) | stage 3 area 0: 491 frames waiting, 1 in state 2, freed; 18 extra changed words at rel 499 against the hidden run |

**Kinds created by other code**, every one with its creators (sites from `py/placement/sites.py`):

| kind | handler | creators | role from the body |
|---|---|---|---|
| 4 | `$1b5cc` | DAMND's death (`$3ed36`, `+20` 1) | temporary camera-mode override: saves `1086(A5)` and `1088(A5)`, sets 4 and `$100`, restores them when `298(A5) == 0` (`+20` 0), camera x `> $b30` (1) or `> $1300` (2), then frees |
| 5 | `$1b644` | SODOM (`$40d18`) | background wobble: waits for `-27914(A5)` (set at `$40d52`), plays sound `$1a`, toggles camera 2's y (`1174(A5)`) between `$210` and `$310` every 9 or 20 frames for 70 frames |
| `$12` | `$1d69a` | bonus stage 6's init list | **BREAK CAR damage board**: three counters `-27904..-27902(A5)` (targets 3, 3, 2) redraw three scroll-3 tile blocks; at the targets it sets `-27900(A5)` and `-27906 = $64` |
| `$14` | `$1e10c` | none found | 2-frame tile blink on camera 2's window (stub-like) |
| `$19` | `$1ef5e` | kind `$d` | elevator door/cab pieces following the `$ffb228` actor (`12846/12850(A5)`) until camera y `$800` |
| `$1a`, `$1c`, `$1d` | `$1f15e`, `$1f258`, `$1f2cc` | none | stubs: `$1a` frees at once, `$1c` and `$1d` have no behaviour |
| `$20` | `$1f4d2` | SODOM (`$40cf6`) | proximity sensor: sets `-27898(A5)` when the player chosen by `138(owner)` is within ±`$20`/±`$10` of a point 64 px in front of the owner |
| `$24` | `$1fba0` | the GLASS prop (pool `$a` kind 9, `$52fea`) | sprite attached to the prop, animated from the owner's event byte; live in bonus stage 7 (4 records) |
| `$25` | `$1fc1c` | `$5284` | TIME OVER banner (`transitions.md`) |
| `$26` to `$29` | `$1fc5e`..`$20090` | phase-`e` code (`$4fb6`..`$51be`), `$26` also by `$27`/`$28` | bonus-stage result lines: text ids through `$14e8`, score adds through `$1a22`, counters `22155..22164(A5)`, the `175(A5)` TIME bonus [R] |
| `$2c` | `$2039c` | kind `$2a`, ROLENTO (`$4a42a`, `$496f4`, `$4989e`) | hanging **grenadier**: moves and throws pool-`$a` kind `$f` (GRANADE, 45-frame life, six seen in 3,000 frames) |
| `$2d` | `$20aa8` | the GLASS props (pool `$a` kind 11) and `$7242` | adds word pairs from a script table to `22172/22174(A5)` (bonus-stage counters) |
| `$2e` | `$20baa` | bonus stage 6's init list | proximity flags `22184..22187(A5)` for the players at x `$48`/`$148` (`+20` 0) and in a ±`$78` window (1) |
| `$2f` | `$20c7e` | ROLENTO (`$4a6ec`) | 12-frame blinking sprite (draw attribute `47(A6)` sequence) |
| `$31` | `$20d8a` | bonus stage 6's init list, `+20` 0 to 2 | the three **BREAK POINT** arrows over the car, blinking while the area intro runs (`298(A5)`), freed at 383 frames [L] |
| `$32` | `$20e28` | bonus stage 7's trigger list, `+20` 0 to 2 | the same arrows for bonus stage 7 [L: three records, 334 frames in state 2] |
| `$33` | `$20ec6` | none found | follower drawn only while the owner is airborne (`10 != 14`) |
| `$35`, `$36`, `$37` | `$20fc0`, `$2167e`, `$2170a` | player scripts (`$185b8`, `$18828`..`$18858`, `$18a08`) | pieces of the end-of-game window scene (`$35` x `$3283`, y `$838`, three sub-records; `$37` sets palette word `$9143e2 := $f000`) [R] |
| `$38` | `$218d0` | ABIGAIL (`$4d4da`) | one-shot sprite with the hurt box off (`97(A6) = 1`) |
| `$39` | `$21964` | the CHANDELIER prop (`$51e0e`) | follower drawn while the owner is airborne (a shadow); 110 frames in stage 5 area 0 [L] |
| `$3a` | `$219de` | player scripts (`$1842a`), itself | `+20` 0: a debris spawner locked to camera y + `$70`, a 90-frame burst (`31(A6)`) with a random 1-to-4-frame timer (table `$21a60`) that creates `+20` 1 children [R] |

Kinds `$f`, `$15`, `$17`, `$1b`, `$1e`, `$1f`, `$21` to `$23` and `$34` are in the table above and `frame.md`. A bonus stage (stage byte 6 or 7) places pool-`$a` GLASS props
(`$b` to `$e`, `$9`) with these objects; the stage 6 run is BREAK CAR (kinds `$12`, `$2e` twice, `$31` three times, seen in `sb_s6`, 896 frames), stage 7 uses `$32`, `$c` and `$24`.

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
`$4fe00`, `$4fe52`, `$4fe9e`) are [R]: kind 3 is EDI.E's gun bullet, a projectile that flies 10 px per frame and hurts both players and the fighters for 40, kind 4 is the fire bottle, and neither can be
picked up (`74` is never 0; `player.md` "Weapons", `ai.md` "The bottle and the fire"). Item names (`$5bee2`, by `+20`): 0 BARBECUE, 1 STEAK, 2 CHICKEN, 3 HAMBURGER, 4 HOT DOG, 5 PIZZA, 6 CURRY, 7 SUSHI,
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

## Terrain codes in the scroll-2 attribute word

The CPS1 video reads only bits 0 to 8 of a tile's attribute word (palette, flips, priority group; `cps1_v.cpp` 2466 to 2468), so the game keeps a 6-bit **terrain code in bits 15 to 10** of the scroll-2 map (`$90c000`, 4 bytes per entry) and the level maps carry it already (stage 0 uses codes 0 to 5 and 9 to 11). The reader is the probe `$89dc` (D3 = x, D4 = y, tile address as `$477a`):

```
terrain(x, y) = (byte[$90c002 + addr(x, y)] >> 2) & $3f      // 279(A5) set (a lift ride): the alternate lookup at $8a28
dispatch: word table $7fe6, entries 0 to 42; 0, 1 open ground; 2, 4 push the mover in y; 3 and 6 push it left in x; 5 pushes it right; 7 and up slopes and steps; 39 to 42 and beyond jump to $17c4c
```

Pool 8 kind `$22` (`$1fa5a`) writes code 5 (`$1400`, push right) over an 80-entry block (5 columns of 16 rows) at each area's left edge and code 3 (`$0c00`, push left) at the right edge: an invisible wall. Nothing changes on screen: writing code 3, code 5 or `$3f` over 80 tiles left the rendered frame identical in 4 of 4 compared frames. A code-3 block put on the player's row held Cody at x `$1df` for 160 frames while Right was pressed (he started inside it at `$22b`), a code-5 block let him walk on, and with no block he reached `$3a5`; the probe's read at `$8a1e` hit the block 976 times in 500 frames (`py/engine/` gate `terrain`, `bb_2500`). Whether the walls matter for fighters is not shown: the player is already held by the camera-window clamp (`$8e46`, x `>= cam + $18`; `px = $173` at `bb_2500`).

## The region word `$726e0`

A ROM data word, 2 in this set: 0 Japan, 2 USA, 4 World. The boot code `$e68` indexes the warning text by it (`$ea8`: `$1a` Japan only, `$39` USA, Canada and Mexico, `$1b` elsewhere) and the banner (`$ede`: `$3f` JAPAN, `$40` U.S.A., `$41` ETC); the live ring commands `$0040` (frame 115) and `$0039` (frame 314) are the US pair. `$5b1e` takes the script table `$5f7e` and `$607a` the placement tables `$6346` when it is non-zero. About twenty more of its 26 absolute references in the attract, title and ending code choose Japanese or English text and logos, and `$17a46` separates 2 from 4 for the copyright line. It is neither a dip setting nor a player count.

## Pool-4 kind 7: the carrier

Handler `$513f8`, spawned by `$f1ca` inside the player's area-clear walk-off for stage 2 area 0 (area-clear sub 4 reads the row of `$edd0` for the stage and area, here `$f15a`; its step table `$f16c` step 0 is `$f1b8`, which allocates the record unless `145(A6)` is set). Proven only with the clear forced by poking `297(A5) := 1` (state `p5b_k7`, 2 of 2 runs); the natural area clear of stage 2 area 0 was not played.

```
init $5140c: target = a player; x = camX - $48; y = player y; destination x = player x - $20; sprite data $d2db4
+3 = 0 $51486: on arrival: player.64 = $ff, .66 = 2, .68 = A6 ; A6.64 = 1, .66 = 2, .68 = player ; 30 = $1e ; +3 = 2     // grab link
+3 = 2 $514de: after 30 frames face left, destination x = camX - $48, +3 = 4
+3 = 4 $5150e: walk to the destination, +3 = 6 ; the area change frees the record ($38f0)
```

Live (`sb_s2`, `297(A5)` poked at relative frame 600): slot 7 of pool 4 holds kind 7 from relative frame 734, `+3` runs 0, 2, 4, 6, and stage 2 area 1 starts about 230 frames later. The screenshots show a large red-vested man (ANDORE-style sprites) carrying Cody off to the left; his HUD name stays whatever the ring last held (kinds 7 and 8 index the rows of kind 5, `frame.md`).

## The `$ffb228` actor (placement type 12)

`$5acdc` dispatches on `19(A6)` through `$5acf2`: three scene actors, all init-list entries. Kind 0 (stage 3 area 1, x `$cae`, y `$28`) is the lift ride: it sets `279(A5)`, waits 180 frames, plays sounds `$32`, `$30` and `$31` on the way and `$32` again at the stop, sets the vertical scroll speed `284(A5) := $10000` and ends when the camera y copy `1116(A5)` reaches `$b00`; live, `279` set at relative frame 3846 and `1116(A5)` +1 per frame in 341 of 341 frames from 4119 (poke recipe in `py/engine/README.md`). Kind 1 (stage 5 area 0, x `$710`, y `$100`) is the elevator platform of the player's state 12 scene: it starts when the camera x reaches `$550`, handshakes with the player through `22191(A5)` to `22194(A5)`, carries the players at 3 px per frame (`128(A6) = $30000`), then creates a GO arrow, sets the right limit `1078(A5) := $1280` and clears `291(A5)`; live with the camera and player x poked, the player's y was the actor's y + 3 in 807 of 807 frames. Kind 2 (stage 4 area 0, x `$530`, y `$b0`) has no body of its own: its handler is pool 8 kind 20 (`$1e10c`), a tile blink that rewrites two by two tiles of scroll 3 every eighth frame while on screen [R]. Placement type 16 (`$62ce`, the `$ffb1e8` executor record) has no entry in any list.

## Not read or not proven

- Pool 8 kinds read but not run: `$8` (the barrier's push), `$13`, `$14`, `$19`, `$20`, `$26` to `$29` (bonus tally), `$2c`/`$2d`, `$2f`, `$33`, `$35` to `$38`, `$3a` (no live observation, or a creator found only in
  player or boss code), the tail of `$2b` (brightness 0), and the natural trigger of `$e` (the camera hook `$61848`) and `$d` (the script's `22192(A5)` pulses): those two were driven by poking the flag.
- The setters of the tile-patch flags in prop and boss code.
- Terrain codes 6 to 38 (read, not exercised; only 3 and 5 were poked), the lift lookup `$8a28`, and whether the edge walls matter for fighters.
- The natural area clear of stage 2 area 0 (the carrier was run on a poked clear), the placement type 12 kind 2 blink (read only) and the stage 3 area 1 and stage 5 area 0 scenes without the camera and player pokes.
- Modes 0, 4 and 6 of the trigger lists were not run (stage 3 area 1 and stage 5).

## Saved states of the logging runs

`py/placement/gates.sh` saves `bb_<frame>` (1325, 1400, 2500, 3070, 3600, 4380, 5570, 7830) in its run directory. Work RAM sha256 prefixes after load: `bb_2500`
`4b51d232767d3e1d`, `bb_5570` `45902fe058ececd2`, `bb_7830` `6c27211dc54926af` (identical over two cold boots); `bb_1325` `b1d8ef4d5ab5379a`, `bb_1400`
`56670907262c0cff`, `bb_3070` `87085cbe77f7b167`, `bb_3600` `47c153f37153eea1`, `bb_4380` `ea83741891e8dcc3`.

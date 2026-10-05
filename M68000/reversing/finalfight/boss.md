# Pool 4: the bosses (DAMND first)

Pool 4 holds the stage bosses. This document covers the pool, its allocator and spawn sites, the eight kind handlers, and the first boss, DAMND (stage 0 area 2), in detail: states, attacks, damage, health, the hp thresholds, the retreat that releases the stage script, and death. Evidence tags as in `kernel.md`: **[R]** read in the ROM listing, **[L]** checked live in MAME with a count, **[S]** read from a saved state, **[I]** inferred. `A5 = $ff8000`, `A6` the boss record. The runs are poke runs in one respect: Cody's health word is topped up to `+28` each frame and his lives kept at 2 or more (`DM_GOD`), with the drop read before the refill, so every damage count below is a count of real hits on a Cody who cannot die. Other pokes are named at the claim. Scripts and the gate list: `py/boss/README.md`.

## The pool

Eight records of `$c0` bytes at `$ff9528` (`5416(A5)`), tag `+18` = 4. The updater `$5a1a` (called from `$5694` inside the per-frame updates of `frame.md`) walks them:

```
for i in 0..7:  A6 = $ff9528 + $c0*i
    if rec[0] == 0: skip
    if rec[0] & $80: rec[0] &= $7f            // new: skipped for one frame
    else: jmp *(long[$5a52 + 4 * rec[19]])    // $5a42, eight handlers
```

Allocator `$390a` pops from a stack of record addresses (count word `20280(A5)` = `$ffcf38`, pointer long `20282(A5)`): Z set on success with `A4` the record (sign-extended word), D0 = 1 and Z clear when empty. It does not zero the record. The free routine `$38f0` calls `$3a1c` (clear `+0..+127`, keeping the word `+78`; bytes `+128..+191` keep their old values), sets `+18` := 4 and pushes the record back, so pops are LIFO: DAMND is record 7 (`$ff9a68`) and a second record gets `$ff99a8` [L]. Records in use are eligible hit candidates and victims (tags 2, 4 and `$a`, `frame.md` "Hit resolution"); a pool-4 victim takes the standard handler `$736e` with the scaled damage `$79d8`, and a grab on tag 4 goes through `$74ee` / `$7512` (the first live grab of a pool-4 record is in "Hit reactions" below).

### Spawn sites

`$390a` has three callers [R]: `$5ebc` (the stage-script entry spawner, entry byte 8 = 4), `$627e` (the placement spawner `$61a8`, type byte 4, via `$6278`) and `$f1ca` (kind 7, the carrier that grabs the player in the area-clear walk-off of stage 2 area 0, `placement.md`). No script entry spawns pool 4: 0 of 180 entries in both script sets (`$5f5e`, `$5f7e`) have tag 4 [R], and `$5ebc` had 0 hits over 4,400 frames of stage 0 area 2 and the start of stage 1 [L]. Every boss comes from the placement tables (`placement.md`; `py/boss/pool4_placement.py` lists the type-4 entries): the init groups (table `$636e`, run once with no trigger test when the placement record `$ffb1a8` leaves state 0) and one per-area table (`$6346`). The six entries:

| stage, area | table | x, y | kind |
|---|---|---|---|
| 0, 2 | init `$6ee32` | `$b98`, `$3f` | 0 DAMND |
| 1, 3 | init `$6eeb2` | `$1448`, 56 | 1 SODOM |
| 2, 2 | init `$6f0d2` | `$ec0`, 56 | 2 EDI.E |
| 3, 1 | area `$6da34`, mode 0 (camera y), trigger `$980`, level byte `$ff` | `$d74`, `$a80` | 3 ROLENTO |
| 4, 0 | init `$6f1e8` | `$2430`, 39 | 4 ABIGAIL |
| 5, 2 | init `$6f248` | `$3370`, `$830` | 5 BELGER |

Live for DAMND (run from `a_area2`, frame 7807): the area byte is 2 at 7808, the placement record goes from state 0 to 2 at 7810, `$605c` runs twice and `$61a8` seven times in that burst, `$6278` once, `$390a` once, and the in-use byte of `$ff9a68` is written by PC `$61fe` at 7810 (write tap) [L]. The record then waits in `+2`/`+3` = 0/0 for the camera.

## The eight kinds

| kind | handler | HUD name (`$5b640`) | trigger inside the handler [R] | health 1P / 2P | kill award code |
|---|---|---|---|---|---|
| 0 | `$3d3d6` | DAMND | camera x >= `$aa0` (`$3d3fe`) | 300 / 450 [L] | 4 = 10,000 [L] |
| 1 | `$40c6e` | SODOM (rows for `+20` = 0 and 1) | camera x >= `$1300` (`+20` = 0) or `$2230` | 300 / 450 (300 live) | `$1a` = 20,000 |
| 2 | `$45f8c` | EDI.E | on screen (`$3264`) | 300 / 450 (300 live) | `$1b` = 30,000 |
| 3 | `$48a76` | ROLENTO | camera y `1116(A5)` >= `$ac0` after init | from the character record by level (300 live at level 13) | `$1e` = 40,000 |
| 4 | `$4be66` | ABIGAIL | camera x >= `$2280` | 500 / 650 (500 live) | `$1c` = 50,000 |
| 5 | `$4ea40` | BELGER | camera x >= `$3240`, sets x := `$3200` | 600 / 900 (600 live) | `$1f` = 100,000 |
| 6 | `$511ac` | BOSSTEST | none | 10 (live) | none |
| 7 | `$513f8` | none (blank rows) | enters at camera x - `$48` | none | none |

The name row is `$5b682 + word[$5b682 + tag] + word[... + 2 * kind] + 32 * (+20)` (`$5b640`, `py/boss/names.py`: 16 tile words after a 6-word header); each kind has one name row except SODOM, which has two. Health, trigger and award columns are [R]; "live" marks a value read from a hand-spawned record (below), the 2P values are [R] except DAMND's 450 [L]. The award codes are entries of the `$1b26` table (`player.md` "Score"); only DAMND's was seen paid live. Kind 6 is a developer's dummy: it has no placement entry, and its death sets `297(A5)` := 1 (`+20` = 0) or `$ff` (`+20` != 0 with `140(A5)` = 0), the stage-over and game-over flags. Kind 7 spawns from `$f1ca`, carries the nearest player off to the left (`64/66(A4)` = `$ff`/2) and is not a fighter; its caller is a player-state block that was not read [I]. Per-kind character records (`92(A6)` bases `$40572/$40632`, `$45d8c/$45e8c`, `$48956/$489d6`, `$4e800/$4e920`, `$510ec/$5114c`): `py/boss/chars4.py`.

Hand spawns (`py/boss/dm.lua` `DM_SPAWN`: the `$390a` pop plus the `$61f8` field writes, level `169(A5)`, into `sb_boss` with DAMND removed, camera poked where a trigger needs it): kind 1 reads hp 300 and runs to x `$125c` after the camera poke to `$1300`; kind 4 hp 500 after the poke to `$2280`; kind 5 hp 600 after `$3240` (x `$3200`); kind 3 hp 300 and waits; kind 6 hp 10 and stands; kind 7 enters at x `$a58` and grabs Cody; kind 2 initialised (hp 300) and the machine then reset about 350 frames later (boot screen in the 8700 screenshot) [L, one run each]. The reset was the harness: `spawn4` zeroed `+78`, the effect-group handle that `$3a52` reads to allocate the death debris (`$44d0`), so the pointer was garbage and the move at `$44fc` took an address error (`$ff167e` = `$01ff`, handler `$719c6`, trap #8 restart). With `+0..+127` zeroed except `+78` (fixed in `dm.lua`, `py/engine/dmk.lua` adds an hp kill) EDI.E, killed by an hp poke and Cody's hits, dies normally: `$477bc` runs once, the shaker starts and the stage clear follows, no reset (checked with the fixed `dm.lua` itself and with `dmk.lua`).

## DAMND (`$3d3d6`)

A large blond man in a yellow outfit who comes through the door of the first area; the HUD shows DAMND with a long green bar. Record fields beyond the common ones of `frame.md`:

| offset | meaning |
|---|---|
| `+2` | 0 init, 2 alive, 4 dying, 6 free (`$3ed30`) |
| `+3`, `+4`, `+5` | state 2: behaviour, sub-state, sub-sub-state (all even) |
| `+23` | hit-stop frames; `+30` byte timer; `+41` animation flag (`$ff` end, 1 and 2 are event frames) |
| `+55` | defence class, re-read every 16 frames from the character record by level (`$2fd4`) |
| `+56` | box table `$404ca` (set at `$3f2aa`); `+92` damage table, reset by `$40a8c` to `$40572` (`$40632` for two players) and moved to `+ $60 + level` by `$2fd4` |
| `+96` | level = `168(A5)`, written every alive frame; `+97` invulnerability timer (no hurt box while non-zero) |
| `+105` | last killer (0 P1, 1 P2) |
| `+128` | target record (long); `+132`, `+134` stand point; `+138` target index |
| `+140`..`+142` | idle script id, current step, script pointer; `+146` word idle wait |
| `+148` | angry flag; `+149` attacking; `+150` word drawn at each pick (not read by anything found, [I]); `+152` current attack step; `+153` script id; `+154` script pointer; `+158` stand-off offset |
| `+160` | target in reach; `+161` killed by a thrown landing; `+162` copy of the hit type |
| `+163` | active-player mask at init (1, 2 or 3); `+164` retreat pending; `+165` retreat stage (0, 2, 4); `+166` word ledge timer; `+168` retreat latch; `+169` angry stage; `+170` landing hit once; `+172` word ledge-leap target y; `+174` airborne; `+175` flag read by the ledge wait |

### Init and entrance

`+3` = 0 (`$3d3fe`) waits for camera x >= `$aa0`; then `302(A5)` := A6 (the HUD enemy-bar target, already `$9a68` in `sb_boss` [S]), a pool-8 kind `$1e` record is created with `128(A4)` = A6 (role not read), and `+3` := 2. `$3d42a`: `$2fa2`, then health `$12c` (`$1c2` when `21610(A5)` = 3) into `+24/26/28`, `163(A6)` := `21610(A5)`, `+97` := `$28`, sound `$17`, four calls of `$466a` (pool `$14` kind 0 debris at x `$b90`, `$ba0`, `$b78`, `$bb8`; the pool-`$14` live count goes 0 to 4 at frame 8302 [L]). `+3` = 4 plays the entrance animation `$3fbf6` for 25 frames, `+3` = 6 (`$3d510`) enters state 2 and picks the target by the player mask (`$3d530`: none, P1, P2, or random P1/P2 by `$aaaa`). The first alive frame is 8300 from `sb_boss` (frame 8299 shows `+2` = 0 with health 0).

### Idle (`+3` = 0)

```
+4=0   heading from the arena map ($40940)
+4=2   k = $3d6c4[rnd & 31]; script k of the 14 at $3d6e4, steps ended by $ff:
       step 0 hop A (vy $340, motion table $3f26a), 2 hop B (vy $5c0, $3f22a), 4 walk 60 frames, 6 walk 120 frames
       (0: 0 | 1: 2 | 2: 0 0 0 | 3: 0 0 4 | 4: 0 0 6 | 5: 0 6 4 | 6: 2 2 0 | 7: 2 0 0 | 8: 2 0 4 | 9: 2 2 6 | 10: 2 6 4 | 11: 4 4 | 12: 6 4 | 13: 6 6 4)
+4=4   fetch step;  +4=6 run it;  +4=8 pause $3d9ce[rnd & 31] (10..70 frames)
+4=10  146 := word[$3da1a (normal) or $3da5a (angry)][rnd & 31]: 180..380 or 20..120 frames of standing, with a
       120-frame taunt (animation $3f5de, sound $28) whose roll mask is $ffff, so it always fires;
       at 146 = 0: +3 := 2
every frame, unless airborne (174 = 0):  $3edbe
       narrow window ($40728: dx -72..72, |dy| <= 9)   -> 160 := 1, attack now
       wide window   ($407a2: dx -88..88, |dy| <= 24)  -> attack with an approach
```

Live (run e7: Cody held left at the arena edge, DAMND poked to x `$bf0`): sub-states `+4` = 0, 2, 4, 6, 8, 10 all visited; `$3d694` 11 hits, `$3d6a0` 1, hop B 141 frames, walk 120 60 frames, the approach/taunt state `$3da9a` 220 frames, `$3edbe` 370 hits [L]. With Cody beside him (runs e4 and g1, 5,000 frames) `$3d6a0` had 0 hits: the window test starts every attack at once and the idle scripts never run [L].

### Attack (`+3` = 2)

```
+4=0  150 := word[$3db58][rnd & $3e];  153 := $3dbda[32*148 + (rnd & $1f)];  154 := $3dc1a + word[$3dc1a + 2*153];  149 := 1
+4=2  if 160: go.  else walk to the target's side (x +- $40, validated by $40c4e inside x $ab4..$bf3, y $10..$3f),
      heading smoothed +-1 per 2 frames ($40c06); go when $40728 holds and the stand point is reached ($40bda)
+4=4  abort ($3dfae) if the target's 137 is set;  152 := next step byte;  a byte >= $80 ends the script (+4 += 4)
+4=6  run step 152 (table $3dd62: 0 -> $3dd6c ...), then +4 := 4
+4=8  wait $3df72[rnd & 31] (10..70 frames), then the chain roll $406f2:
      bit (rnd & $1f) of the long at $3edea[4*level] (+128 when angry; $3eeea for two players); set: +3 := 2 again, clear: $3dfae (160 = 149 = 0, +3 = +4 = +5 = 0)
```

Pick table per 32 draws: normal 6, 7, 10, 3, 3, 3 for scripts 0 to 5; angry 3, 3, 3, 6, 7, 10. Scripts (`$3dc1a`): 0 = A0 A0 A2, 1 = A8, 2 = A0 A0 A0 A8, 3 = A4 A4 A6, 4 = A4 A4 A4 A4 A6, 5 = A4 A4 A4 A8.

| step | list (ticks) | attack box: id, dx, dy, hw, hh, active | damage row | hit type | sound | ROM damage, 1P, level 0 / 13 / 31 |
|---|---|---|---|---|---|---|
| A0 | `$3fbf6` (35) | 1: 40, 56, 36, 34, 7 ticks (frame 4) | `$00` | 0 | 0 | 12 / 17 / 24 |
| A2 | `$3fc1a` (35) | 2: same box | `$00` | 3 | 0 | same |
| A4 | `$3fc3e` (14) | 3: same box, 3 ticks | `$20` | 0 | `$11` | 18 / 25 / 36 |
| A6 | `$3fc5a` (14) | 4: same box | `$20` | 3 | `$11` | same |
| A8 | `$3ff72` (55) | 5: 24, 40, 40, 24, last 30 ticks (a jump, vy `$780`, vx +-`$1aa`) | `$40` | 3 | 1 | 30 / 35 / 43 |

Box 5 is also active in the last 10 ticks of the ledge landing (list `$3ff3e`). Two-player rows are lower (row `$00`: 10 / 14 / 20 at levels 0 / 13 / 31). The hurt box is idx 1 (idle) or idx 2 (attack frames); hop and jump lists use idx 0, a zero-size box (`py/boss/anims.py`).

### Damage and health

Damage on Cody is `byte[92(A6) + word(attack box +8)]`, unscaled (`$7a04`); 127 of 127 drops of Cody's health word attributed to DAMND's box matched (runs e3 11, e4 81, e5 35; by box: row `$00` 51, row `$20` type 0 56, row `$20` type 3 1, row `$40` 19) [L]. Another 267 drops in those runs belong to pool-2 fighters and are not counted. Damage on DAMND is `$79d8`: `dmg = byte[92(P1) + row]`, then `word[$cea74 + (dmg << 6) + 2 * def]` with `def` = `+55`; 31 of 32 drops matched (Cody's raw 10, 10, 16 became 8, 8, 13 at level 13 and 7, 7, 12 from level 15) [L]; the 32nd is the thrown-body landing: -40 at hp 242 (rule of `$3f7a`, holder `+20` = 1: 18/62/40, hp > 80 so a flat 40; 1 of 1 [L]). The level is the difficulty rank `168(A5)` (13 to 18 in the runs); the defence class by level is 1, 3, 4, 6, 7, 8, 8, 9, 11 at levels 0, 4, 8, 12, 16, 20, 24, 28, 31.

Health is a constant: `$12c` = 300, or `$1c2` = 450 when both players are active at init (`21610(A5)` poked to 3 before the init: hp 450, `163(A6)` = 3, `92` = `$4069f`, 1 of 1; the live mask brings `92` back to the 1P table at the next 16-frame refresh). It does not depend on rank: with `168(A5)` poked to 0 and to 31 before the init the health was 300 both times, `+96` 0 and 31, `+55` 1 and 11, `92` = `$405d2` and `$405f1` [L]. Rank changes only his damage column and his defence class. DAMND dies at health < 0; at exactly 0 he is alive.

Attack picks: 160 of 160 draws satisfied index = `32 * 148 + roll`, picked byte = `$3dbda[index]` and `153(A6)` = pick two frames later (breakpoints `$3dbbc`, `$3dbc0`; 100 normal, 60 angry); the draws follow the tables (normal, 100 picks: scripts 0 to 5 chosen 16, 19, 29, 11, 14, 11 times; angry, 59 picks: 4, 3, 2, 11, 15, 24) [L]. The chain roll gave 15 chains in 24 decisions against 11.7 expected from the mask bit density [L, weak].

### Hit reactions (`+3` = 4)

`$3ed58` runs each alive frame: health < 0 starts death (unless `161`); otherwise `+24` != `+26` copies it, sets `63` := 3 if he is airborne and not hit type 8, and enters `+3` = 4 with `+4` = `+5` = 0, so a hit during a reaction restarts it. `$3dfd6` copies the type into `162` and faces the attacker; `$3dffa` dispatches by type through `$3e008` (types 0, 2 `$3e01a`; 1 `$3e058`; 3, 7 `$3e0ce`; 4 `$3e460`; 5 `$3e20e`; 6 `$3e324`; 8 `$3e43a`). Seen live (31 hits, run e3): type 0 (Cody's first punch): stun A (list `$40162`), 13 to 22 frames; type 1 (second punch): stun B (`$40172`), about 20 frames; type 3 (third hit): knockdown, flight and get-up (`$4022a`, `$40232`, `$3f93a`), 85 to 101 frames. Types 2 and 4 to 8 were not seen. At the end of a reaction (`$3e46c` and its kin) `168` set sends him to the retreat, otherwise `$4088c` runs the threshold check and `149` set resumes the attack (`+3` := 2), else idle. Invulnerability `+97` is set to `$3e` at the get-up after a knockdown (9 of 9, first seen as 61), to `$28` at init and after the retreat landing (3 of 3).

A grab: Cody walking into him grabs him (frame 8688: boss `+64` = `$ff`, Cody `+64` = 1, boss `+66` = 2 from 8689, 29 frames held), then throws him (`+3` = 10, `$3e5e0`: flight with the thrown-body test `$6c96`, landing damage `$3f7a` via `$3e6bc`, then get-up) [L, 1 of 1]. A release without a throw goes to `+3` = 6 (grounded, `+97` := `$32`) or 8 (airborne, lands); both were visited incidentally (7 visits of `+3` = 6 in run e7) and not analysed.

### Hp thresholds and the retreat (`+3` = 12)

```
$4088c (at a reaction end):  stage 0: hp <= $c8 (1P) / $12c (2P):  165 := 2, 164 := 1 -> 168 := 1 (retreat latched)
                             stage 2: hp <= $64:                    165 := 4, 164 := 1, 148 := 1
$408ec (every 16th alive frame): hp <= $70 (1P) / $4b (2P): 148 := 1 (angry)
```

Live (run e3): the first retreat latched at hp 165 (frame 8986; hp had been 194 at 8850, but the check runs only when a reaction ends), the second at hp 99 (9906), the angry flag at hp 111 (9797): 1 of 1 each; with hp poked to 110 at 8310 the angry flag was set at 8341 and the retreat at 8357 [L].

The retreat: `$3e7c6` jumps to the ledge (x `$c60`, y `$30`: `80 = ($c60 - x) * 4`, `84 = ($30 - y) * 4`, `86 = $400`; `174` and `-27896(A5)` set); `+4` = 2 stands 30 frames; `+4` = 4 (`$3e8ae`) plays the taunt list `$3f7ee`, sound `$27` at its flag-2 frame, and at its flag-1 frame (after 55 frames) calls `$5f9e`, sets `166` := `$12c` and clears `175`; `+4` = 6 (`$3e8e2`) waits on the ledge for 300 frames (a player with `137` set starts a 120-frame sound-`$28` pause); `+4` = 8 (`$3e942`) leaps at the target's ground line, lands with box 5 active in the last 10 ticks, sets `+97` := `$28` and returns to `+3` = 0. Per episode (2 in run e3): jump 33 + 34 frames, stand 30, taunt 55, ledge 300, return jump 33 + 38; `$3e8ae` 110 hits and `$5f9e` 2 hits in all [L]. While he is on the ledge the released wave fights Cody.

### The stage-script pause

The executor record `$ffb1e8` has the pause flag at `+22`; `$5b4e` returns while it is set. The `pause` command (`$5bfe`) is the only setter, and the only two `pause` commands of the whole `$5f7e` script set are in stage 0 area 2 (`$7072e`, `$70780`) [R]. `$5f9e`, whose only direct caller is `$3e8d2`, is the only clearer:

```
$5f9e:  A0 = $ffb1e8
        if 22(A0) != 0:  clear it                       // release a pause
        else:            6(A0) := 24(A0) + 4; 3(A0), 4(A0), 5(A0) := 0; 22(A0) := 0   // restart from the segment's continuation
```

Timeline (run e3 from `sb_boss`): the pause at `$7072e` is executed at frame 7811, one frame after DAMND is allocated, and the script sits at `$70730` with the flag set; the first retreat's taunt calls `$5f9e` at 9139 (flag 1 to 0), the executor then spawns segment `$70730` (kinds 5, 0, 0, 1; pointer `$7073e` to `$70780`), pauses again at `$70782` (9352), the second retreat releases it at 10059, segment `$70782` (kinds 4, 6, 0, 0, 8, 8) follows and the pointer ends at `$707f2`. Two pauses, two releases [L]. Two pokes confirm the mechanism: with the flag cleared at 9138 (run e8) `$5f9e` takes the restart branch, the pointer jumps to `$70782` (`24(A0)` = `$7077e` was set by the executor in the same frame) and wave 1 is never spawned; with his hp set to 20 at 8310 (run e9) he retreats once (8357, release 8509), dies at 8966 before the second retreat, and the second pause stays set for the rest of the stage, so wave 2 never spawns, yet the stage still ends [L, 1 of 1 each]. At the first pause `24(A0)` is 0, so the restart branch is safe only after a segment header has set it [R].

### Death and what follows

`+2` = 4. `+3` = 0 (`$3eb98`) is the fall, 51 frames. `+3` = 2 (`$3ecb2`) sets `299(A5)` := 1 (the stage-clear mass kill of the other fighters; the placement and script executors stop while it is set) for 40 frames. `+3` = 4 (`$3ecea`) runs the death animation `$3f906` (175 frames) and then sets `297(A5)` := 1, calls `$1b428`, `$b8a` and `$288c` with code 4 (bit 7 if `105(A6)` = 1): the score rises by 10,000 in that frame (run e3 at 11274 and run e9 at 9233, 2 of 2) and the record rests in (4, 4, 2) with only `$3b3c` running. A kill by a thrown landing (`161`) enters state 4 at `+3` = 2. In run e3 (hp -7 at 11007): `299` = 1 at 11059, `297` = 1 at 11274, Cody's state 10 from 11275, `297` = `$ff` at 11589, `191` = 3 at 11590, stage byte 1 at 11606, the camera limit `1078(A5)` goes from `$b00` to `$380` and the camera to 0 at 11607; the stage script is untouched (pointer `$707f2`) and `190/191` stay 0/2 until the transition (the run e9 shows the same 314-frame gap from `297` = 1 to `297` = `$ff`). The transition and area flow are in `transitions.md`. The record is cleared by the pool initialiser (PC `$9b0a` in a `$9b02` clear loop, write tap on the in-use byte, frame 11573, two frames after the stage byte changes) [L].

State 6 (`$3ed30`: `1078(A5)` := `$b30`, a pool-8 kind 4 record, `297` := 1, `jmp $38f0`) is not reached by play: no code in the kind 0 body writes `+2` := 6 [R], `$3ed30` and `$38f0` had 0 hits from the area start to frame 12,200, and write taps on `+2` of all eight pool-4 records over a whole fight and stage change (frames 7807 to 11700, `runs.sh` s3) saw exactly ten writes: DAMND's init `0` to `2` (PC `$3d516`, frame 8326), his death `2` to `4` (PC `$3edae`, frame 10971) and the pool initialiser clearing all eight records (PC `$9b0a`, frame 11573), none with a 6 [L, 1 run]. A write from other code in some other stage is not excluded, so state 6 is dead code for stage 0 and [I] elsewhere.

## Evidence

| claim | count | gate |
|---|---|---|
| damage on Cody equals the ROM byte | 127 of 127 (e3 11, e4 81, e5 35) | `gate_dmg_cody.py` |
| damage on DAMND equals the scaled table value | 31 of 32 (the 32nd is the thrown landing, 40, `$3f7a`) | `gate_dmg_boss.py` |
| attack pick index, byte and script | 160 of 160 | `gate_pick.py` |
| retreat latches at hp 165 and 99, angry at 111 (110 after the poke) | 1 of 1 each | `thresh.py` |
| two-player health 450, ranks 0 and 31 give 300 | 1 of 1 each | `thresh.py`, `rank.py` |
| `$390a` once from `$6278`; `$5ebc`, `$3ed30`, `$38f0` 0; `$5f9e` 2 | one run from `a_area2` | `runs.sh` s1, s2 |
| pause release, restart branch, early kill | 2 of 2, 1 of 1, 1 of 1 | `exe.py` |

Saved states: `a_area2` (frame 7807, work RAM sha256 `d594bed6...eed4`, identical over two cold boots) and `a_boss_mid` (frame 8850, DAMND at hp 194, `867747b9...9dac`, identical over two runs); both come from `py/boss/states.sh` and `runs.sh` (`sb_boss` is `py/stage/run.sh boss`).

## Not proven

- Attack A2 (box 2) and hit types 2 and 4 to 8 never occurred live. Prove by poking `63(A6)` in state 2 and forcing `153(A6)` := 0.
- Two-player behaviour beyond the init health: the `$12c` and `$4b` thresholds, the 2P damage rows, the random target `$40922`. Needs player 2.
- Kinds 1 to 5: only init, health and the camera triggers were checked; their handlers, attacks and awards are [R] only. Kind 7 is the carrier of `placement.md`. The shaker `$1b428` is `frame.md` "The screen shaker" (death sites: DAMND `$3ed0e` [L], SODOM `$426d8` and ABIGAIL `$4d550` [R], EDI.E `$477bc` [L]; ROLENTO and BELGER do not call it). The `-27896(A5)` flag set in DAMND's jumps and the pool-8 kind `$1e` he creates are unnamed. Hand spawns of kinds 1, 3, 4 and 5 into `sb_boss` with `+78` kept but no camera poke for their trigger stay inert (kind 1 ignores hp -1, kind 3 falls through the floor, kinds 4 and 5 stay at state 0 with maximum hp 0), so their deaths were not run [L, one run each]; `$466a` asks for `word[$459c]` + 1 = 6 pool-`$14` records per call but 4 were live in total.
- The branch taken at each reaction end (`$3e46c`, `$3e4d2`, `$3e57a`, `$3e760`, `$3e522`, `$3e5c2`) was read, not enumerated; the grab-release states `+3` = 6 and 8 were not analysed.
- Whether anything other than `$3e8d2` calls `$5f9e` indirectly.

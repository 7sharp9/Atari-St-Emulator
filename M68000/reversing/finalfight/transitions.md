# Areas, stages and the player's scripted states

How the game moves from one area to the next and from one stage to the next: the phase machine at `0(A5)`, the flag words that ask for an area clear, the player's
scripted states 8 (area intro), 10 (area clear) and 12 (scene), the camera records, the GO prompt, TIME and the difficulty rank. Evidence tags as in `kernel.md`:
**[R]** read in the ROM listing, **[L]** live in MAME with a count, **[S]** saved state, **[I]** inferred. `A5 = $ff8000`. Every [L] count comes from
`py/transitions/` (`gates.sh`, 23 gates, `README.md` there); the per-stage tables are decoded in `py/transitions/tables.txt`. The runs start from the stage 0 states of
`py/stage/` (cold boot with `plans/plan1.lua`, then the bot of `lua/stagebot.lua`); frame numbers are those of that lineage, without `-debug`. The scene and spawn side of
an area is in `placement.md`, the bosses in `boss.md`.

## Stages and areas

`190(A5)` is the stage byte, `191(A5)` the area, `193(A5)` the position in the game's stage sequence, `290(A5)` non-zero in a bonus stage. The sequence comes from the byte
pairs at `$553a` (`$54f8` adds 1 to `193` and loads `190` and `290` from entry `193`) [R, L]:

| `193` | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| `190` | 0 | 1 | **6** | 2 | 3 | **7** | 4 | 5 |
| `290` | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |

So the stage byte is not one more per stage: stages 6 and 7 are the two bonus stages, played after the second and the fourth stage (live: 190 = 0, 1, 6, 2 in that order, 193 = 0, 1,
2, 3, [L]). The byte table `$54c0` gives the number of areas: stage 0 has 3, stage 1 has 4, stage 2 has 3, stage 3 has 2, stage 4 has 1, stage 5 has 3, stages 6 and 7 have 1
(stages 8 and 9 are the player-select and continue scenes, `190 = 8` is written by `$5c3b4` and `$5dade` and restored afterwards, [L] 190 := 8 at frame 1200). Writers of
`190/191`:

- `$c16`, `$4c8a`, `$4c8e`: the stage clock's first frame (0/0, [L] frame 1169); `$4d6e`: phase 2 clears 191 when the game is running.
- `$4eae` (phase 8): `191 += 1` [L 191 := 1, 2, 3 at 5560, 7805, 11578; 1 at 20543; 4 at 11885 in the poked run].
- `$54f8`, `$5504`, `$550a`, `$4ee6` (phase a): the next stage and `191 := 0` [L frames 11594, 12123, 14860].
- Attract, demo, test and select code: the demo header restore `$2b38/$2b3e`, the Service Mode stage select `$54ca` (`101(A5)`), `$5c3b4/$5c912` and `$5dade/$5db3c`
  (select and continue scenes), `$170c6..$19cc6` (title and attract), and four stage viewers of the test mode (`$5fabc`, `$6038c`, `$607ae`, `$60d0c`) [R].

## The phase machine

The word `0(A5)` is dispatched by the stage clock (task slot 1, `kernel.md`) through the word table `$4cce` [R]. Each handler sets the next phase before it does its work:

| phase | handler | what it does |
|---|---|---|
| 0 | `$4cde` | sets phase 2, starts the select scene (task `$5c384`), the two controller tasks and the stage scene task `$5c92e` (unless the attract demo flag `22188(A5)`) |
| 2 | `$4d46` | stage init: `$95d0` (free lists, the camera loader `$6263a`, players `$a056`), clears 302, 296, 299, `300(A5)` from `$531c`; with the game running (130 nonzero, not Service Mode) 191 := 0; phase := 4 |
| 4 | `$4d74` | area init: sets **298 := 1**, clears 297, 291, 278, 279, 280, 284 and the bonus counters, `$95f2` (camera loader again, `$961e` lists, `$a0d6` players, HUD), `$61e24`, loads TIME with `$51ec`; phase := 6, or `$e` when 290 is set |
| 6 | `$4e3a` | the in-level frame (`frame.md`); ends in phase 8 when 297 < 0 and 140(A5) = 0 (calls `$2636`, which clears both CPS object tables) |
| 8 | `$4eae` | `191 += 1`; if the area count `$54b4` is above 191 then phase := 4 and 297 := 0, else phase := `$a` |
| a | `$4ed0` | waits for 297 = 0, then `$54f8` (next stage), `$5382` (rank drop), 191 := 0, phase := 2; at `193 > 7` it goes to the ending (phase `$c`) [R] |
| c | `$4f74` | input service only [R] |
| e | `$4f7a` | the bonus-stage frame: its own state word `2(A5)` (0 play-in, 2 play at `$5000` with the 60-frame TIME `$52b6`, 4 results, 6 end, 8 wait for 297 < 0) |

Phase writes seen from a cold boot after frame 1100 are exactly 0, 2, 4, 6, 8 and 10 (gate `phase_values`), and the complete write sequence of the DAMND area clear into stage 1 matches 17
of 17 at its frame and PC (gate `clear_to_stage1_writes`): 297 := 1 at 11262, state 10 at 11264, 297 := $ff at 11577, phase 8 and `191 := 3` at 11578, phase a at 11578, 297 := 0 at 11593 (the
scene task), `$54f8` at 11594, phases 2, 4, 6 at 11594, 11595, 11596 (the phase-4 handler needs 2 to 3 frames: TIME is set at 11599), the intro end at 11752.
A non-final area goes from phase 8 straight to phase 4 (5560, 7805 [L]). A bonus stage enters phase e at `$4e06` (12128 [L]).

## The flag words

| word | meaning | writers [R], live |
|---|---|---|
| `297(A5)` | 0 normal; **1 the area or stage is cleared, the players walk out**; **$ff the walk-out and fade are finished** | 1: script continuation codes 4 and 8 (`$5d36`, `$5d6c`), the six pool-4 boss death handlers (`$3ed08/$3ed4e`, `$426e4/$42704`, `$477ac/$4780e`, `$4a360`, `$4d52e/$4d590`, `$4fa84/$4fa9a`), the bonus time-out `$52f2`, `$61650`. $ff: `$ed5e` (state 10 sub 6), `$ed94` (sub 8), `$f1aa`, the camera hooks `$61ae2` and `$61b2e`, a pool handler at `$512c6`. Cleared by `$4eca` (phase 8), `$4d84` (phase 4) and the scene task `$5ced4` |
| `298(A5)` | area intro running; freezes TIME and the rank | set `$4d7e`, cleared by the intro handlers at `$dc02` [L 11596 to 11752] |
| `299(A5)` | enemies frozen (the fighters and the script executor test it; the players get no hurt box for the frame at `$9ce6`) | set by the six boss death handlers (`$3ecc6` ...) and `$c88e` (state 12), cleared by `$c8ac` and phase 4 [L 11048 to 11596, 12002 to 12082] |
| `291(A5)` | scene in progress, players go to state 12; freezes TIME | set by script continuation code 6 (`$5d3e`) and `$516b2`; cleared by `$5b0ae` and phase 4 |
| `278(A5)` | camera lock | below |
| `140(A5)` | low nibble: a screen fade is running; `$252e` starts the fade out (`$26c2` sets the bits, the fade task clears them) | [L] set to `$0e` at 11496 and 11599, cleared at 11577 |
| `290(A5)` | bonus stage | from `$553b` |
| `166(A6)` | player record: has walked off, set by `$f6e6`, which also starts the fade | [L 11496] |

## Stage-script continuations and the camera lock

The executor `$5aea` (`frame.md`) reads a segment: trigger, the header words (timer, count, w18, flag) and a long continuation pointer, the entries, then a word `$8000 + code`.
The **code is a byte offset into the word table at `$5cc2`**, so it is 0, 2, 4, 6, 8 or 10 [R] (`py/ai_kind45/script.py` labelled them by table index before; its `CONT` is now
keyed by code):

| code | handler | effect |
|---|---|---|
| 0 | `$5cce` | wait until the tracked records are dead (`$5dca`, checked every 8 frames, or the timer runs out), then 30 frames, spawn the GO prompt if w18 is non-zero, 278 := 0 |
| 2 | `$5d1a` | read the next segment header at once (occurs only on the last segment of an area, so it is never followed by a valid segment, [I] what the executor then does) |
| 4 | `$5d26` | stage end: executor state += 2, **297 := 1** |
| 6 | `$5d3e` | 291 := 1, 278 := 0 |
| 8 | `$5d56` | executor state += 2, `$ff12fa` := 1, 297 := 1 |
| 10 | `$5d74` | pause 30 frames |

A segment whose flag word is 0 sets **278 := 1** when its trigger is reached (`$5dfe`, `$5e0e`). Live: stage 0 area 0 locks at camera `$3f0` (frame 4424) and code 4 ends the area
at 5265 (297 := 1 at `$5d36`), stage 0 area 1 ends the same way at 7627, and the two code-0 segments of stage 0 area 2 end at 9374 and 10761 (278 cleared at `$5d08`, 2 of 2). Which areas end how
(`py/transitions/tables.txt`): code 4 ends stage 0 areas 0 and 1, stage 1 areas 0, 1 (second segment) and 2, stage 2 area 1, stage 5 areas 0 (third segment) and 1; code 8 ends stage 3 area 0; code 2 is the last segment of stage 2 areas 0 and 2, stage 4 and stage 5 area 2; the other areas
end through a boss (`boss.md`) or a camera hook.

## Area clear: player state 10 (`$e8e8`)

`$9ce0` runs at the end of each state-2 frame [R]:

```
if 299: 154 := 0, 97 := 1 (invulnerable for the frame)
if 297 != 0 or 291 != 0:
    154 := 0; 97 := 1
    if 14(A6) != 10(A6): return        // wait until the player stands on the ground
    64 := 0; 66 := 0                    // release a grapple
    2(A6) := state 10 (297) or 12 (291), sub 0
    if 24(A6) < 0: 24 := 26 := 0        // a negative health is cleared: the player cannot die in the walk-out
```

[L] the wait is real: a jump at 11801, 297 poked at 11820 in the air, state 10 starts at the landing frame 11850 with the state byte staying 2 in between (gate `area_clear_waits_landing`).
The state table is `$e8f8` (sub 0, 2, 4, 6, 8, `$a`):

- **sub 0** (`$e936`): sub := 2; idle animation `$c4be`, per-character animation tables `$f422`, `145(A6)` from the other player `$f53c`, a carried weapon turns into points `$e962`
  (kind 0 500, 1 1000, 2 800, 3 none, `player.md`), and `$f44e` loads the walk target `156(A6)` (x) and `158(A6)` from the table `$f488` (stage word, area, 8 bytes: one player, then the
  other player). A negative x means "no walk": the second word selects sub 6 (0) or sub `$a` (4). Targets: stage 0 areas `$4d0`, `$850`, `$bd0` (y `$30`/`$32`), stage 1 area 0 `$3d9`, area 2 `$1148`,
  stage 2 areas 0 and 1 `$850`, `$fcc`, stage 3 area 0 `$cf0`, stage 6 `$200`, stage 7 `$3c0`; everything else is negative (stage 1 area 1: sub `$a`; stage 1 area 3, stage 2 area 2, stage 3 area 1,
  stages 4 and 5: sub 6).
- **sub 2** (`$e99a`), step byte `4(A6)`: step 0 waits 80 frames (`30(A6) = $50`), step 2 (`$e9c2`) picks a per-area variant from the byte table `$e9e8` (0 `$ea10` default, 2 `$ea7e`,
  4 `$eada`, 6 `$eae8`; the last two are the bonus stages). The default `$ea10` clears 278, compares x with the target (`target - x + 8`) and chooses step 4 (walk to the target, `$eb18`: animation `$c578`,
  step `$f5ba`, ends when `$f58e` matches, then sub 4), step 6 (`$eb50`: a back-jump to a target left of the player: animation `$c55a`, velocities `$f64c`, airborne, landing recovery, then step 4; Button 1
  in the air still attacks, `$c6a8`), or a variant for an airborne player. `$ea7e` (stage 1 area 0, stage 2 area 1) does **not** clear 278.
- **sub 4** (`$eda0`): a canned walk-off per stage and area (`$edd0`, routines `$ee0e`, `$ef02`, `$efd0` for stage 0: a per-character table of x and y steps, the player leaves toward the top right). Stage 2 area 0 (`$f15a`) does not walk: step 0 `$f1b8` spawns the pool-4 kind 7 carrier that grabs the player and carries him off (`placement.md`; seen with `297(A5)` poked, 2 of 2 runs). When
  the walk is done `$f6e6` sets `166(A6) := 1` and starts the fade (`$252e`). The sub then waits for 166 and `140(A5) = 0`, takes sub 8 (`$e91e`).
- **sub 8** (`$ed68`): step 0 and 2: if `140(A5) = 0` then **297 := $ff** (`$ed94`); the second player's record idles at step 4. **sub 6** (`$ed2e`) fades out at once and then does the same;
  **sub `$a`** (`$ed9e`) is an `rts`: the area ends through its camera hook.

Live timeline of the DAMND clear (stage 0 area 2), from 297 := 1 at 11262: sub 0 at 11264 (1 frame); sub 2 step 0 for 80 frames (11265); step 2 at 11345 with 278 cleared (`$ea10`); step 6, the player is
right of the target `$bd0`: 6 frames, airborne 42 frames, landing 6 frames (11346 to 11400); step 4, a 31-frame walk (11401); sub 4 at 11433, the walk-off 63 frames, the fade from 11496 to 11577
(81 frames, 166 := 1 and 140 := `$0e` at `$f6ec/$26d4`, 140 cleared at `$26ea` in the frame 297 := $ff is written, gate `fade_before_297`, 4 of 4); sub 8 at 11578 (12 of 12 timeline values, gate
`clear_state_timeline`). From 297 := 1 to the next area's first controllable frame: 464 frames (area 0), 346 (area 1), 491 (area 2 into stage 1) [L]. The fade and a 15-frame wait in the scene task
(`$5ceb8..$5ced4`, 297 := 0 at 11593) are part of the last area's clear. In stage 1 area 0 (poked 297, `$ea7e`) the clear takes 164 frames and the camera stays frozen at `$340`. Stage 1 area 1 (sub `$a`): the
camera hook `$61ad4` starts the fade and writes 297 := $ff 359 frames after 297 := 1, phase 8 follows 81 frames later (gate `stage1_area1_hook_exit`, 7 of 7). Stage 1 area 3 (sub 6, poked):
297 := $ff 81 frames after state 10 starts.

**There is no bonus tally between stages.** From the boss kill (score +10,000, the award code `$04` at `$3ed18`) to the next kill 0 score changes happen in 695 frames and TIME stays 44 (gate
`no_score_tally`). `191 = 3` after the last area of stage 0 is only the incremented counter of phase 8; stage 0 has no area 3. The "ROUND 1 CLEAR!" text over the map is the stage scene task
`$5c92e` (state 4 sub 6, `$5cdb6`): it starts about 41 frames after 297 := 1 in the last area of a stage and shows for the whole walk-out [L screenshots 11304 to 11568, `$5c9c2` waits for
297 and the last area]; the next stage's intro keeps the map overlay [L 11592 to 11736, state 4 sub 2, `$5cb34`, R].

## Area intro: player state 8 (`$dc08`)

Every area starts in state 8 sub 0 (the start-state table `$a446` holds `$08000000` for all of them, [R]). The handler is `$dc2a + word[stage] + word[area]` (`py/transitions/tables.txt`: stage 0 `$dc6e`,
`$dd06`, `$de5a`; stage 1 `$df88`, `$e054`, `$e092`, `$e0d0`; stage 2 `$e1b4`, `$e1f8`, `$e250`; stage 3 `$e292`, `$e2d0`; stage 4 `$e30e`; stage 5 `$e34c`, `$e38a`, `$e3bc`; stage 6 `$e3ee`; stage 7 `$e4a0`).
Most intros place the player from the camera (`$e692`, partner offset `$e714/$e71e`), walk him in (`$c578`, `$e680`) and end with `$dbf0`: state 2 sub 0 and, for the first player, `278 := 0` and
`298 := 0` (`$dbfe/$dc02`). The camera is locked (278 := 1) from the intro's start (`$dd1c`, `$de6e`, `$df9c`, `$e064`, ...).

[L] durations: stage 0 area 0 1315 to 1676 (sub 2 118 frames, sub 4 242 frames) and it ends in state 2 sub `$10`, the special move (`p1st = $0210` at 1677, `$dcf2` writes `$02100000`);
stage 0 area 1 5563 to 5728 (166 frames), area 2 7808 to 7972, stage 1 area 0 11598 to 11752 (155 frames). Stage 1 area 0 (`$df88`): sub 0 sets 278, places the player and starts a fall (`90(A6)` from
`288(A5)`, animation `$c55a`); sub 4 falls (`$30aa`), lands at 11654 (sub 6), then he walks to camera x + `$b0` (`$e02c`); 278 is cleared early, at 11606 (`$dfee`), so the camera follows the walk
(cam `$0000` to `$00de`). TIME is loaded at the start of phase 4 and starts counting when 298 clears: the first decrement is 480 frames after the intro end (12233 = 11753 + 480, [L]).
The player's spawn offset from the camera (`$9d76`, table `$9dba`) is `+$40, +$30` for player 1 and `+$a0, +$30` for player 2 in every area [R].

## Player state 12 (`$c840`)

Entered from `$9ce0` when `291(A5)` is set (after the 297 test), sub table `$c852`: sub 0 (`$c85a`) sets 299 := 1 and waits 80 frames, then sub 2 (`$c8b2`), sub 4 (`$c97c`, an eight-step scene that uses
the x constants `$6b0` to `$710`) and sub 6 (`$cb8c`). [L] with 291 poked to 1 at 12000 in stage 1: state 12 at 12001, 299 := 1 at 12002 and 0 at 12082, sub 2 at 12082, sub 4 at 12083 and the player parks
at sub 4 step 4; TIME stays frozen (`176(A5)` constant to 12690) (gate `state12_poke`, 6 of 6). In the game it is the scene of stage 5 area 0 (script continuation code 6 at trigger `$600`, the scene
actor `$5acdc` moving y to `$780`, then `$5b0a2` sets the right limit `$1280` and clears 291): the actor is the elevator platform (`placement.md`, "The `$ffb228` actor"); run from `p5b_s5pre` with the camera x and player x poked to `$560`/`$5e0` and `291(A5)` poked to 1 (the scene starts by the stage script in play; stage 5 was not played).

## The camera

The two records at `1036(A5)` (`$ff840c`) and `1164(A5)` (`$ff848c`) are camera records, updated by `$61e24` (which first stores the active-player mask in `21610(A5)`, then `$61e4e` for the first and `$6241e`
for the second). The first has the state byte `2(A6)` (0 init `$61e5e`, 2 run `$61e8e`), x at `+6` (`1042(A5)`), y at `+10` (`1046`), `+42` right limit (`1078(A5)`), `+44` left limit (`1080`), `+50`/`+51` x and y
mode (`1086`, `1087`), `+56/+58` last x and y, `+60` the GO counter, `+64` a per-stage hook step. Its x and y are copied to `42/44(A5)`, which the VBL handler `$53e` writes to CPS scroll 2
(`$800110/$800112`, one frame late through `46/48(A5)`); the second record (x `1170`, y `1174`, copied to `50/52(A5)`) drives scroll 3 (`$800114/$800116`) and its parameters `1216/1218(A5)` come from `$62754`
(x drifts 1 pixel per 2 frames in stage 0 area 2 [L]). When bit 4 of the camera x or y changes the run state streams the next map column or row (`$62b76`, `$62d6c`, `$62db6`, `$62f88`, [R]).

The loader `$6263a`, called by phases 2 and 4, fills the record from tables indexed by stage and area: start x/y/x2/y2 (`$626c0`, `$62940`), the limits (`$626fa`, `$6285c`: words left, right and two more, `1084/1082(A5)`
[I y limits]) and the modes (`$6268e`, `$627d8`). Stage 0: area 0 left `$0060` right `$03f0`, area 1 `$0650` `$0730`, area 2 `$0900` `$0b00`; stage 1: `$0000/$0380`, `$0500/$0ce0`, `$0f00/$1080`, `$1200/$1380`;
stage 2: `$0000/$0750`, `$0f00/$0f00`, `$0700/$0d80`; stage 3: `$0000/$0b40`, `$0d00/$0d00`; stage 4: `$0000/$2280`; stage 5: `$0000/$0600`, `$1400/$24f0`, `$2700/$3240` (all stages in `tables.txt`).
The camera x is set to the area's start x at the area start [L cam `$0650` at 5580, `$0900` at 7830, `$0000` at 11610].

Each frame, with **278 = 0** (`$61ed8`): in mode 0 and 2 (`$62012`, `$62138`; mode 2 is the one in play after a hook sets it, mode 0 is the default for stage 0 and follows to the right only)

```
right: if p.x - cam >= $d0: cam += min(4, p.x - cam - $d0)           // p is the first live player (one player), or the pair rule of $6207e
left (mode 2): if p.x - cam < $b0: cam -= min(4, $b0 - (p.x - cam))
cam = clamp(cam, left limit, right limit)
```

[L] the right limit is `1078(A5)`: with the limit poked from `$0b00` to `$0c00` at frame 11100 the camera went to `$0b4f` = p.x `$0c1f` - `$d0` where the baseline held `$0b00` with the same player x; the left rule held at
`$0b3c` (= `$0bec - $b0`) and `$0ae7` (= `$0b97 - $b0`) (gates `camera_right_limit`, `camera_follow_rule`). The camera x has seven writers in the first 12000 frames of a cold boot: `$62050` (3081 writes),
`$6205e` (289), `$62176` (1991), `$62184` (1082), `$621c0` (302), `$621ce` (222), `$626e8` (6) (gate `camera_x_writers`). **278 = 1 skips the camera step altogether**: poked to 1 at 11900 in stage 1 area 0 the camera stayed
`$01a7` on 7 of 7 samples to 12090 while the baseline went to `$01c0`, and caught up after the release at 12100 (gate `camera_lock_poke`). The lock comes from the script (above) or from an intro handler; in stage 0 area 1
it holds the camera at `$06e1` (the limit is `$0730`) until `$ea10` clears it at 7710 and the camera runs to the limit (gate `camera_lock_script`, 7 of 7).

**Per-stage hooks** (`$614e4` calls the hook of the stage, table `$6153a`, then the GO rule below). The stage 0 area 2 hook (`$61566`, step byte `64(A6)`): when cam >= `$ab0` it writes `$4009`, `$7fff`, `$0000` to `116/118/120(A5)`
(copied by the VBL handler to `$80016c/e`, `$800170`: video control words, effect [I]); the next frame it sets the left limit to `$0aa0` and the x mode to 2, so the boss area cannot be left to the left [L 8307 and 8308, gate
`camera_hook_stage0`]. The right limit stays `$0b00` through the whole DAMND clear [L]; the `$3ed30` write of `$b30` belongs to another death routine and was not reached. Other hooks end areas by themselves
(stage 1 area 1 `$61ad4`, `$61b2e`, above).

## The GO prompt and the area-edge objects

**GO** is pool-8 kind 2 (handler `$1b2ec`: a 4x4 tile block at `$909528` that alternates a pointing hand and the word GO, sound `$3b`, 240 frames [L screenshots at 3070, 3080 (hand), 3090, 3100 (GO)]). It has three spawn
sites: the segment end `$5cfa` (only when the header word w18 is non-zero), the stage 5 scene `$5b09a`, and the camera's idle rule `$6152c`:

```
if not bonus and x mode != 2 and cam != right limit and 278 == 0:
    if cam == last cam: if --60(A6) == 0: spawn GO; 60(A6) := $1a4
    else 60(A6) := $1a4                                              // 420 frames
```

[L] spawns at 3060, 3480 (exactly 420 frames apart, the camera moved last at 2640) and 6195 in stage 0, and every 420 frames while the camera is idle (24806, 25226, ... 29426); none at the two code-0 segment ends
of stage 0 area 2, whose w18 is 0 (gates `go_prompt_420`, `go_not_on_cont0_w18_0`).

Pool-8 **kind `$22`** pairs (ch 0 and 1) are spawned at each area start of stages 0 to 5 by `$62a34` at positions from `$62ac2/$62b16` (stage 0: x `$0028/$0568`, `$0618/$08a8`, `$08c8/$0c38`; stage 1 area 0:
`$1fb8/$04f8` [L 3 of 3 areas]); the handler `$1fa5a` rewrites the attribute bits of an 80-tile block of the scroll map (`$1400`; channel 1 `$0c00` once the camera is within `$20` of the right limit): not a visible patch but the terrain codes 5 and 3, an invisible wall at each area edge (`placement.md`, "Terrain codes"). Kind `$25` is the TIME OVER banner, kind `$26` the bonus-stage TIME OVER banner (below).

## TIME and the difficulty rank

`175(A5)` is the packed-BCD TIME, `186(A5)` its start value for the area, `176(A5)` the tick counter. `$51ec` loads `byte[$5210 + 4*stage + area]` at phase 4 (stage 0: 30, 30, 50; stage 1: 50, 70, 30, 70; stage 2: 50, 50, 50;
stage 3: 70, 50; stage 4: 99; stage 5: 60, 70, 70; stage 6: 30; stage 7: 20; stage 4 has the single entry 99; the 99 entries of areas that do not exist are never loaded) [R, L 7 of 7 area starts: 30 at 1316 and 5564, 50 at 7809 and 11599, 70 at 12018, the bonus 30 at 12128 and 50
at 14865, gate `time_table`]. `$5238` counts `176` up and at `$1e0` (480 frames) decrements; it does nothing while 298, 297 or 291 is set (TIME stayed 44 from the boss kill to the next stage). A bonus stage uses
`$52b6` instead, a 60-frame tick (12566 to 14306 [L], 30 ticks).

**TIME 0** [L, idle Cody from a cold boot, gate `time_zero`, 7 of 7]: TIME shows 00 from frame 16077 (1676 + 30 * 480 + 1); at the next 480-frame tick, 16557, `$5270` runs: `$51de` reloads TIME from `186(A5)` (30),
`$5298` handles each live player (if his health equals its shadow `63(A0) := 3`; then `24(A0) := $ffff`), and pool-8 kind `$25` is spawned (the TIME OVER banner, 120 frames, `$1fc1c`, text on screen at 16560 to 16620).
The player goes to the hit reaction (state 2 sub 6) and the fatal knockdown (`4 = $14`, 92 frames), state 4 at 16649, a 60-frame countdown, and the respawn at 16709 with lives 2 to 1 and full health. TIME 0 in a bonus
stage does not kill: `$52f2` sets 297 := 1 and `2(A5) := 6`, kind `$26` (TIME OVER) is spawned (14367 [L]) and the normal walk-out follows; 297 := $ff comes at 14843, phase 8 at 14844, stage 2 begins at 14861 (gate
`bonus_stage_flow`, 8 of 8). No bot run reached TIME 0 (the lowest value was 34); the idle run is the proof.

The difficulty rank `168(A5)` (`frame.md`) rises by 1 every 600 frames of `$5326` when none of 298, 297, 290, 291 is set (8485, 9085, 9685, 10285, 10885 [L]); at the stage change `$5382` (phase a) clears the counter and
subtracts `word[$53aa + 2*172(A5)]` (2, 1, 1, 0) down to the floor `188(A5)`, not in a bonus stage: 18 to 17 at 11595 [L, gate `rank_stage_change`, 6 of 6]. The death drop `$53b2` uses `$53d4` (3, 2, 1, 1).

## Poke recipes

All exercised by `py/transitions/gates.sh` (the pokes are byte writes at frame end; the addresses are `$ff8000 + offset`):

| goal | poke | effect [L] |
|---|---|---|
| start an area clear now | `297(A5)` := 1 (`$ff8129`) | state 10 at the next grounded frame; the stage's own walk-out and fade follow |
| end the stage, enter a bonus stage | `191(A5)` := 3 (`$ff80bf`) in stage 1, then 297 := 1 | state 10 sub 6, phase 8, phase a, stage 6 (`190 = 6`, `193 = 2`, `290 = 1`), later stage 2 |
| start state 12 | `291(A5)` := 1 (`$ff8123`) | state 12 one frame later |
| freeze or free the camera | `278(A5)` (`$ff8116`) | frozen at its value |
| move the camera right limit | `1078(A5)` (`$ff8436`, word) | the camera follows to the new limit |
| TIME | `175(A5)` (`$ff80af`, BCD) and `176(A5)` | a poke of 00 with `176` at `$1df` triggers the TIME 0 branch (not exercised; the gate uses the real count) |

## The whole game and the ending, played by the bot

`py/stage/README.md` ("Stages 2 to 5, played"): the bot (god mode, health poke) took the game through stage bytes 0, 1, 6, 2, 3, 7, 4, 5, the order of the table at `$553a`. After the stage 5 boss the player's area clear (state 10, sub 6)
runs at frame 289,030 and the game goes on without a player. Runs of the (stage byte, area) pair `(190, 191)` from the state `sb_s8` (frame 289,034; `py/stage/` log `end.log`, screenshots every 400 frames; `ending.png` is the contact sheet,
frame number on each tile):

| frames | `190/191` | screen |
|---|---|---|
| 289,040-289,050 | 8/3 | the byte the chain log shows for 21 frames, then 5 again |
| 289,060-289,770 | 5/0 | ROUND CLEAR over the stage 5 arena with the boss down (289,440) |
| 289,780-291,520 | 9/0 | the father and daughter dialogue panel, text typed out ("Oh Father! I was so scared...") |
| 291,530-294,290 | 5/0 | the staff roll (programmer, character design, music and sound, special thanks) over Metro City scenes, Cody and Guy walking, Jessica in the park |
| 294,300-299,060 | 9/0 | a second dialogue ("Where are you going?"), the cast roll ("My name is POM", EAMEKON, TISSUE, PRINCE...), then GAME OVER |
| 299,070 on | 8/0 | the Mad Gear story text and a portrait scene (attract mode): the game has returned to its start |

So the ending is not a stage with its own area table: it reuses stage bytes 5 and 9 (and 8 for the attract story) while no player is live. [L, 1 run; the pair of bytes is read from work RAM every 10 frames, the screens from the screenshots]

## Not proven

- The stages and the ending were played (below), but only the stage byte and the screenshots were logged: the area-clear walk-offs of stages 2 to 5, bonus stage 7, the phase handlers of the ending (phase a with `193 > 7`, phase `$c`)
  and every `$e9c2` variant other than `$ea10` and `$ea7e` were not traced, and the mapping of the ending's stage-byte runs to `193` and to the phases was not read. Steps 8, `$a`, `$c` of state 10 sub 2 and everything with `145(A6)` (two players) are unexercised.
- State 12's scene is the stage 5 area 0 elevator (run on pokes, not reached by play). What the executor does after a code 2 continuation is unknown ([I]: the data that follows is the next area's).
- The effect of `116/118/120(A5)`, the y limit words `1082/1084(A5)`, the y camera `$62316`, and the record-2 mode table `$624ce` are [I]; the bonus-stage state machine of phase `$e` is [R] only except for the
  play, time-out and walk-out path above.
- A resumed state can stamp a write one frame off against a cold boot (2 of 4008, gate `cold_vs_resumed`), and a state loaded under `-debug` resumes on another trajectory; the gates run without `-debug`.

# py/stage: playing the game instead of spawning into `ff_enemies`

`lua/stagebot.lua` wraps `lua/ffdrive.lua` (cold boot or `FF_LOAD=<state>`) and from `FF_BOT_START` drives player 1 from the live records: walk right
when nothing is near, else close on the nearest live fighter (pool 2, or pool 4 where the bosses are) and tap Button 1 in range; with `FF_BOT_PROPS=1` and no
fighter alive it attacks the breakable prop (pool `$a`) just ahead (barrels block the walk from stage 1 on). **`FF_BOT_GOD=1` (default) tops the health word
`+24` up to `+28` and keeps the lives byte at 2 or more every frame: a run is a survival poke, not a fair play-through.** It logs per 10 frames
(`f sa=<190(A5)><191(A5)> cam=<1042(A5)> scr=<long at $ffb1ee> x= y= st= hp lives live-records-per-pool`), a `S` line when a record first appears in a pool
(frame, pool, index, address, `+19`, `+20`, `+21`, `+96`, x, y, hp, camera, script pointer), `D` lines on request.

| file | what it does |
|---|---|
| `run.sh boss` | cold boot, kill Bred (`plans/plan1.lua`), bot to camera x `$aa0` (stage 0 area 2 trigger); state `sb_boss`, frame 8298 |
| `run.sh stage1` | from `sb_boss`: the bot through DAMND and the area clear to stage byte 1; state `sb_s1`, frame 11595 (work RAM sha256 `6389dc8c...`, gfx RAM `359a7c73...`, identical in a second run in fresh run and output directories) |
| `chain.sh <stage byte> <steps>` | from `sb_s<stage byte>` play until `190(A5)` changes and save `sb_s<new>` (`FF_BOT_LEAVE`, `FF_SAVE_PREFIX`); `FF_BOT_PROPS=1`. The stage byte is not +1 per stage: after the subway (1) it is 6, then 2 |
| `dest_gate.py <poolrec.bin>` | gate for the kind 3 destination rule of `ai.md` (19 of 19 destination changes equal player x +/- `$50`/`$80` by the side byte; 11 left of the camera) on a `py/ai_kind0/poolrec.lua` dump of the stall state |
| `census.py <logs>` | matches the `S` lines against the `$5f7e` script entries of stage 0 (18 of 18 one-player entries seen, in order) and lists the spawns no entry explains |

Environment: `FFS_RUN` (MAME run directory, default `scratchpad/finalfight/stage/run`), `FFS_OUT` (default `scratchpad/finalfight/stage/out`), `FFS_SECONDS`
(emulated seconds MAME runs at most, default 6000). Two runs that share `FFS_RUN` collide on cfg, nvram and states: give each its own.

Facts that the bot established (each from a played run, not a spawn):

- The state `sb_boss` is deterministic: work RAM sha256 `a0cb6b52...4837` identical over two cold boots. The bot itself has no randomness; the game's LFSR is
  seeded identically each boot.
- **The bot's default lane mapping is inverted.** Measured (`py/twoplayer`, 6 of 6 runs): Up raises both `+10` and `+14` by 0.8 px per frame, lane limits `$10` and `$3f`. The default bot presses Down when the target's lane is higher; it still kills enemies because they walk up to it, and it is kept because `sb_boss` and `sb_s1` come from it. `FF_BOT_LANEFIX=1` selects the correct mapping (then the run differs). With the correct mapping stage 2 area 0 still stalls (fighter at x `$1cf` the bot does not reach, then props), so lane direction is not the cause.
- A fighter's health word is 0 while it still fights (HOLLY WOOD at `+24 = 0`); it dies at `+24 < 0`. A bot that treats 0 as dead stalls at the area wall for 7000 frames.
- The first boss is DAMND, a pool-4 record (not pool 2): a bot that targets only pool 2 never kills him and the stage-0 script stays paused for 20,000 frames (his retreat releases the pause, `boss.md`). A pool-4 record at hp 0 is alive (the rule is hp >= 0), but the default bot still tests hp > 0 there so that `sb_boss` and `sb_s1` stay reproducible: `FF_BOT_HP0=1` selects the corrected rule and gives a different run.
- Stage 1 area 1: three barrels (pool `$a` kind 6) block the walk and only a hit clears them.
- Stage order seen: 0 (areas 0 to 2, boss DAMND; `191` reads 3 afterwards only because phase 8 increments it past the last area, there is no tally and no area 3, `transitions.md`) -> 1 (areas 0 to 3, then `191` = 4 the same way; pool-4 bosses in the last areas) -> **6** -> 2. Stage 1 took
  about 28,000 frames and stage 6 about 2,800. Stage 2 needs the options below (sections after this list); without them the bot stalls three times (next section).
- `FF_STOP` (ffdrive's last frame) defaults to 1,000,000 in `run.sh`; MAME's `-seconds_to_run` counts emulated seconds (`FFS_SECONDS`, 6000 = 357,000 frames).

## Stage 2: three stalls and the options that clear them

Run from `sb_s2` (`chain.sh 2 5`, or `run.sh custom` with `FF_LOAD=sb_s2 FF_BOT_START=0 ...`) with `FF_BOT_LANEFIX=1 FF_BOT_LURE=1 FF_BOT_UNSTICK=1 FF_BOT_PROPS=1 FF_BOT_HP0=1`. Each option is off by default so that the
stage 0 and 1 states keep their hashes. The run is deterministic: a second run from `sb_s2` to frame 56,840 gave the same first pool-4 spawn line as the first.

1. **A fighter parked off screen (area 0, first lock, camera `$201`).** The last fighter, an ANDORE (pool 2 kind 3) from the left edge, sat at x `$1cf` while the bot held Left at the window clamp `x = cam + $18`. His
   destination is player x minus `$50` (`$1c9`), 56 px off screen, and `$2e3f6` never tests the camera (`ai.md`, "Kind 3", gate `dest_gate.py`). `FF_BOT_LURE=1` walks to mid-screen when the nearest target has stood
   within `$80` px outside the camera window for 120 frames; he then walks in and dies. (Its first version fired for any off-screen target and froze the bot beside a boss 1,600 px away.)
2. **A curb (area 0, second lock, camera `$2dc`).** Lane y `>= $30` is walled at x `$3a0` by terrain codes 7 and 8 (`placement.md`, "Terrain codes"); the bot at `y = $31` with no target never changed lane. Moving it to y `$20`
   by poke walked it from `$3ab` to `$4cf` with the camera following. `FF_BOT_UNSTICK=1` presses Down, then Up on the next stall, for 40 frames after 45 frames without movement.
3. **A DOOR prop (area 2, x `$888`, y `$38`, created at frame 56,989).** Its terrain codes (6, 7, 8) fill `x = $870-$8af` in every lane, the boss (pool 4 kind 2, x `$ec0`) is behind it, and the bot ignores props while a
   fighter is alive. `FF_BOT_UNSTICK=1` with `FF_BOT_PROPS=1` makes a stuck bot prefer a prop ahead for 600 frames (props get a vertical reach of 12 instead of 8). `FF_BOT_HP0=1` is needed here: the boss sits at hp 0.

Seen on the way, naturally rather than by poke: the pool-4 kind 7 carrier at the stage 2 area 0 clear (record from frame 52,760 at camera `$750`), stage 2 area 1 (camera `$f00`) and the area 2 boss. Stage 2 ends at frame 64,752
(stage byte 3, state `sb_s3`).

## Stages 2 to 5, played

With the same options (`chain.sh 2 5` from `sb_s2`, `FF_BOT_UNSTICK=1` also selects two prop rules: FLAME props, kinds `$10`/`$11`, are never targeted, and a prop is swung at only with the lane aligned, `|dy| <= 5`,
or after 40 frames without lane movement) the bot played every stage of the game; stage 3 area 0 holds rows of FLAME props over a walkway and a DRUMCAN row that a misaligned swing never reaches (the bot whiffed at a
DRUMCAN 12 px off its lane for 165,000 frames before the lane rule). **Stage byte order seen: 0, 1, 6 (bonus), 2, 3, 7 (bonus), 4, 5, then 8 for 21 frames and back to 5.** Frames from the lineage's `sb_s2`
(frame 42,784; this is a god-mode play, the health poke tops health, not the clock):

| stage | ends at frame | pool-4 bosses seen (`S` lines) | note |
|---|---|---|---|
| 2 | 64,752 | kind 7 carrier at 52,760 (camera `$750`), kind 2 at 56,841 (x `$ec0`) | areas 0 to 2 |
| 3 | 84,917 | kind 3 at 79,161 (x `$d74`, camera `$d00`) | 20,000 frames |
| 7 (bonus) | 87,000 | none | 2,100 frames |
| 4 | 202,844 | kind 4 at 87,005 (x `$2430`) | 116,000 frames, 3 life losses (TIME) in the log; camera ends at `$2280` |
| 5 | 289,034 | kind 4 at 202,845 (a dying record), kind 5 at 277,309 (x `$3370`, camera `$2700`) | camera ends at `$3240` |
| 8 | 289,055 | kind 5 record carried over | 21 frames |

Stage 4 is slow and loses lives; its log (`s4.log`, `FFS_OUT`) is not yet read for why. States `sb_s3` to `sb_s8` are in the stage run directory (`scratchpad/ANCHORS.md`).

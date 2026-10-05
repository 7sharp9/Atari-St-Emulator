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
  about 28,000 frames and stage 6 about 2,800. The bot stalls at stage 2 area 0 (two trash cans, pool `$a` kind 5, one lane in front of Cody; props have no ground-line copy at `+14`, use `+10`): it stands still with `tgt` set, cause not found. A stall of about 20,000 frames ends with TIME
  running out and Cody losing a life (the god poke tops health, not the clock), after which the run goes on. The bot does not play stages 2 to 5 yet.
- `FF_STOP` (ffdrive's last frame) defaults to 1,000,000 in `run.sh`; MAME's `-seconds_to_run` counts emulated seconds (`FFS_SECONDS`, 6000 = 357,000 frames).

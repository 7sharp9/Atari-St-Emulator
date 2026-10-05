# boss: live checks and ROM readers for pool 4 (DAMND and the other bosses)

Method and results are in `../../boss.md`. A run loads a saved state into MAME 0.289 (headless, `SDL_VIDEODRIVER=dummy`), optionally plays player 1 with a bot, applies pokes, and writes a
per-frame dump of work RAM `$ff8000-$ffb300` (`dd.py` reads it), a text log and breakpoint/watchpoint hit lists. Every script derives the repo root from `__file__` (or `M68000_ROOT`); each
run uses a run directory of its own (`scratchpad/finalfight/boss/runs/run_<name>`), so runs can go in parallel. Cody is kept alive by a poke (`DM_GOD=1`, health topped up after the dump of
each frame, lives >= 2), so every run is a poke run for survival questions.

Quick start: `sh runs.sh` (builds `sb_boss` and `a_area2` from a cold boot through `../stage/run.sh` if they are missing, then starts 14 runs together, 1 to 3 minutes each, about 600 MB of
dumps under `scratchpad/finalfight/boss/out`), then `sh gates.sh`.

| file | what it does / proves | how to run |
|---|---|---|
| `dm.lua` | harness: `DM_LOAD` state, `DM_BOT` 0/1/2 (stagebot rule; pool 4 alive at hp >= 0), `DM_KEYS`, `DM_POKES=frame:addr:hex,...`, `DM_DUMP`/`DM_RANGES`, `DM_ADDRS` (bp counts, `DM_HITLOG` with D0, D1, A0, A1, A6), `DM_WPS=addr:len` (write taps with PC), `DM_SPAWN=kind:ch:x:y:lvl@frame` (hand-built pool-4 record: the `$390a` pop plus `$61f8`), `DM_SAVE` at `DM_SAVEF` or `DM_SAVEHP`, `DM_SHOT`; header of the file lists all | through `par.sh` |
| `mame.sh`, `par.sh` | the MAME wrapper (`DM_DEBUG=1` adds `-debug -debugger none`, needed for bp/wp) and the one-run-per-directory runner | `sh par.sh <name> DM_LOAD=sb_boss ...` |
| `states.sh` | builds `sb_boss` (`run.sh boss`, work RAM `a0cb6b52...4837`) and `a_area2` (`run.sh custom`, `FF_BOT_CAM=2304`, frame 7807, `d594bed6...eed4`) | `sh states.sh` |
| `runs.sh` | all runs behind `boss.md`: e3 (bot fight to the stage change), e4 (idle Cody), e5 (hp poked to 110), e6 (`21610(A5)` = 3), e7 (idle scripts), e8 (pause flag cleared), e9 (early kill), g1/g2 (pick breakpoints), s1 (spawn and death breakpoint counts), s2 (writers of the boss in-use byte), s3 (write taps on `+2` of all pool-4 records), d1 (saves `a_boss_mid`), r0/r31 (rank poke) | `sh runs.sh` |
| `gates.sh` | runs every gate below and prints the counts | `sh gates.sh` |
| `dd.py` | reader of the per-frame dumps (`DM_BOSS` selects the record, default `$ff9a68`) | import |
| `gate_dmg_cody.py` | drops of Cody's health word equal `byte[92(A6) + word(box +8)]` of DAMND: 127 of 127 (e3 11, e4 81, e5 35) | `gate_dmg_cody.py <dump>` |
| `gate_dmg_boss.py` | drops of DAMND's health equal the `$79d8` scaled value: 31 of 32 (the 32nd is the 40-point thrown landing, `$3f7a`) | `gate_dmg_boss.py <dump>` |
| `gate_pick.py` | attack pick index, byte and script: 160 of 160 | `gate_pick.py <hits> <dump>` |
| `thresh.py` | changes of the hp flags (retreat 165/164/168, angry 148/169, mask 163) with hp: 165 and 99 for the retreats, 111 for the angry flag, 450 for two players | `thresh.py <dump>` |
| `rank.py` | health, level, defence class and damage table 30 frames in, after a rank poke (300, 0/31, 1/11) | `rank.py <dump>` |
| `attacks.py`, `chain.py` | attack pick distribution against the tables; chain roll outcomes against the mask bit density (15 of 24, 11.7 expected) | `attacks.py <dump>...` |
| `react2.py`, `hist.py` | per-hit reaction (type, length, sub-state path, animations, next state); `(+2,+3,+4,+5)` histogram with animation lists and attack boxes | `<script> <dump>` |
| `timeline.py`, `exe.py` | DAMND state changes with hp, 190/191, 297/299, camera limit, script pointer, pause flag, score; the executor record `$ffb1e8` and the pause flag | `<script> <dump> [lo hi]` |
| `writes.py` | summary of the write-tap hit list (`s3`): writes to `+2` of the pool-4 records by PC and value | `writes.py <hits>` |
| `names.py`, `pool4_placement.py`, `chars4.py` | ROM readers: HUD names per (tag, kind, `+20`) from `$5b640`; the type-4 entries of the placement tables `$636e`/`$6346`; the per-kind character records | run |
| `anims.py`, `tables.py` | DAMND's animation lists with hurt and attack boxes (box table `$404ca`); its data tables (idle scripts, pause tables, pick tables, retaliation masks) | run |
| `rdis2.py`, `mk.sh`, `ends.txt`, `k0.asm` | `tools/rdis.py` with table sizes capped at the next table base or a hand `--end` (rdis takes first word / 2, which runs into a following table where the first entry points past it: `$3d5b8`/`$3d5c6`, `$3db1c`); DAMND's listing (`mk.sh 3d3d6 40c6e 3d3d6`) | `sh mk.sh <lo> <hi> <roots>` |

Gate list (counts from `gates.sh`, see `boss.md` "Evidence"): Cody damage 127 of 127, boss damage 31 of 32, attack picks 160 of 160, thresholds (e3 retreat 165 and 99, angry 111; e5 angry 110),
two-player health 450, ranks 0 and 31 (hp 300, def 1 and 11), `s1` counts (`$390a` 1, `$5ebc` 0, `$5f9e` 2, `$3ed30` 0, `$38f0` 0), `s3` writes to `+2` of the pool-4 records (no write of 6).

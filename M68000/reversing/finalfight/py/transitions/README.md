# py/transitions: areas, stages, the camera, TIME and the player's scripted states

Reference text: `../../transitions.md`. Every script derives the repo root from its own location (or `M68000_ROOT`); `gates.sh` and `run.sh` keep their own MAME run
directory (`FFT_RUN`, default `scratchpad/finalfight/transitions/run`) and output directory (`FFT_OUT`, `.../out`), so two runs never collide.
Quick start: `./gates.sh` (about 2.5 minutes, 23 gates). It needs the states `sb_boss` and `sb_s1` (`py/stage/run.sh boss`, `stage1`); they are copied from
`scratchpad/finalfight/stage/run/sta/ffightuc/` into the run directory.

| file | what it does / proves | how to run |
|---|---|---|
| `run.sh` | MAME wrapper (SDL dummy, no `-debug`, `-nothrottle`) that runs `trans.lua` or `pctap.lua` on top of `lua/stagebot.lua`; any `FF_*` variable of the bot passes through | `run.sh trans <name>`, `run.sh pt <name>` |
| `trans.lua` | per-frame change log of the phase words, `190..193`, `278..300(A5)`, player 1 state and step, TIME, score, lives, camera limits and modes, difficulty rank (`C` lines); write taps with the writing PC on those words and on the camera x (`T` lines); a pool census (`S` lines); `P` position lines every 30 frames. `FF_TR_POKE="frame:hexaddr:hexbytes,..."` pokes at frame end, `FF_TR_HOLD="f1-f2:field:level,..."` holds inputs after the bot, `FF_TR_TAPS=0`, `FF_TR_POOLS=0` | via `run.sh trans` |
| `pctap.lua` | write or read taps with the PC on arbitrary [even, odd] word ranges (`FF_PT_W`, `FF_PT_R`, `FF_PT_LO/HI`), under the bot | via `run.sh pt` |
| `runs.py` | `runs.py <log> <f0> <f1> [field...]`: forward-fills the `C` lines and prints the runs (value, first frame, length) of fields such as `p1st p1s45 297` | `runs.py g_boss.log 11262 11600` |
| `tables.py`, `tables.txt` | decodes every per-stage and per-area table of the transition code: stage order, areas per stage, TIME, area start camera, camera limits and modes, record-2 parameters, kind `$22` pairs, state 8 handlers, state 10 targets, variants and sub-4 routines, area start state, player spawn offsets, and every stage-script segment with its corrected continuation code | `tables.py > tables.txt` |
| `rom.py` | ROM word and byte readers (`ff_main.bin`), area counts | imported |
| `gates.sh` | regenerates every log below (cold boot with taps, the DAMND clear to stage 1, six poke runs, an idle run to TIME 0, a bonus-stage run, a stage 1 area 1 run) and runs `gates.py` | `./gates.sh` |
| `gates.py` | the 23 gates, each with its count; exit status 1 on a failure | `gates.py <out dir>` |

None of the runs uses `-debug` (`FF_MAMEARGS` is empty). The runs that start from a loaded state (`sb_boss`, `sb_s1`, `c_s1a1`) therefore follow the trajectory of a
loaded state without the debugger; a state loaded under `-debug` resumes on a different trajectory (camera `$aa4` against `$aa0` at 8300), so the frame numbers in the
gates are only valid without it. Cold boots are identical either way. A resumed run can also stamp a write one frame off against the cold boot (gate 20).

## The 23 gates

| gate | what it checks | count |
|---|---|---|
| `clear_to_stage1_writes` | the writes of phase, 190/191/193/290, 297, 278, 298 with their PC and frame from the DAMND kill to the end of the stage 1 intro | 17 of 17 |
| `clear_state_timeline` | player state and step of that area clear: sub 0, sub 2 step 0 (80 frames), the back-jump, the walk, sub 4, the fade, sub 8, the state 8 intro | 12 of 12 |
| `no_score_tally` | no score change and no TIME change between the boss kill and the next kill | 0 changes in 695 frames |
| `time_table` | TIME at seven area starts equals `$5210[4*stage+area]` | 7 of 7 |
| `area_counter` | phase 8 adds 1 to 191; phase 4 after areas 0 and 1, phase a after the last; `$54f8` makes stage 1 | 8 of 8 |
| `area_start_camera` | the camera is at the area's start x | 3 of 3 |
| `camera_x_writers` | the PCs that write the camera x from the game start to 12000 | 6973 writes, 7 PCs |
| `camera_right_limit` | poking `1078(A5)` releases the camera that the limit held | cam `$0b4f` against `$0b00` |
| `camera_follow_rule` | cam = p.x - `$d0` to the right, p.x - `$b0` to the left | 2 of 2 |
| `camera_lock_poke` | `278(A5)` = 1 freezes the camera | 7 of 7 samples |
| `camera_lock_script` | the script sets 278 at the trigger, `$ea10` and `$5d08` clear it | 7 of 7 |
| `camera_hook_stage0` | the stage 0 area 2 camera hook (video words, left limit `$aa0`, mode 2) | 3 of 3 |
| `go_prompt_420` | pool-8 kind 2 spawns 420 frames after the camera stops | 3 spawns, 420 apart |
| `go_not_on_cont0_w18_0` | no GO at a segment end whose header w18 is 0 | 0 spawns |
| `time_zero` | TIME 00, then reload, kind `$25`, death and respawn 480 frames later | 7 of 7 |
| `area_clear_waits_landing` | 297 poked in the air starts state 10 at the landing | frame 11850 |
| `state12_poke` | 291 := 1 gives state 12, 299 for 80 frames, TIME frozen | 6 of 6 |
| `bonus_stage_flow` | stage 6, phase `$e`, TIME ticks of 60 frames, walk-out, stage 2 | 8 of 8 |
| `fade_before_297` | the walked-off flag and the fade, 81 frames, 297 := `$ff` in the frame the fade ends | 4 of 4 |
| `cold_vs_resumed` | the cold boot and the resumed lineage execute the same writes | 4008, 4006 same frame |
| `phase_values` | the phase word takes 0, 2, 4, 6, 8, 10 | 6 values |
| `stage1_area1_hook_exit` | stage 1 area 1 ends through its camera hook (297 := `$ff` at `$61ae2`) | 7 of 7 |
| `rank_stage_change` | the difficulty rank rises every 600 frames and drops by 1 at the stage change | 6 of 6 |

Poke recipes (all in `gates.sh`): `297(A5)` = 1 at `$ff8129` starts the area clear; `191(A5)` = 3 at `$ff80bf` with it makes stage 1 end and starts bonus stage 1;
`291(A5)` at `$ff8123` starts state 12; `278(A5)` at `$ff8116` freezes the camera; `1078(A5)` at `$ff8436` is the camera right limit; `175(A5)` at `$ff80af` is TIME.

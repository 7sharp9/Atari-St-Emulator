# Final Fight (Capcom CPS1, 1989), reverse-engineering workspace

First arcade subject in this repo. Target set: MAME `ffightuc` (Final Fight, USA 900613), a clone of
`ffight`. MAME 0.289 is the emulator and oracle; the F# core is not involved. The ST tooling that
carries over is the 68000 disassembler (`tools/disassemble.py`, `--rom <flat image> --base 0`) and the
method (census, callcap, gates, claims need a match count).

## ROMs (not committed)

| file | sha256 | role |
|---|---|---|
| `ffight.zip` | `a7cc8894...7eab` | parent set: gfx (`ff-1m/3m/5m/7m`), OKI samples, `ff-32m.8h` (program ROM at `$080000-$0fffff`, not a bank ROM), PLD dumps |
| `ffightub.zip` | `b9f8098e...e49c2` | misnamed: its CRCs are the **`ffightuc`** program ROMs + Z80 `ff_23.12b`, not MAME 0.289's `ffightub` |

MAME looks for `ffightuc.zip` beside `ffight.zip`, so the second file is copied to
`~/mame-roms/ffightuc.zip` (`ffmame.sh` reads `$FF_ROMS`, default `~/mame-roms`). `mame -verifyroms
ffightuc` reports "good" with both present.

## Running

`./ffmame.sh callcap` (spec in `$CALLCAP_SPEC`) or `./ffmame.sh script <file.lua>`. It runs MAME with
`-debug -debugger none -video none -sound none`, which gives Lua a working debugger without a window,
at about 18x real time. MAME's cfg/nvram/state go under `scratchpad/finalfight/run/`.
`lua/dumprom.lua` (`FF_OUT=<dir>`) writes `ff_main.bin` (68000 space `$000000-$0fffff`, sha256
`8535dd51...e6ec`) and `ff_z80.bin` (sound CPU `$0000-$7fff`) for static work:

```
python3 tools/disassemble.py --rom <abs path>/ff_main.bin --base 0 --linear 5e88c 24
```

`./ffrun.sh <script.lua>` is the second wrapper: no `-debug`, `-nothrottle` (about 4-8x real time with
RAM dumps), same `scratchpad/finalfight/run/` directories. Use it for input-driven scripts
(`lua/lib.lua`, `ffdrive.lua`, `resume_check.lua`, `ioport_dump.lua`, `kernel_log.lua`); use `ffmame.sh` for `callcap`.
Both wrappers export `SDL_VIDEODRIVER=dummy`: with `-video none` alone macOS still makes `mame` the
frontmost (full-screen-looking) app on every run. A Lua `install_write_tap` handle must be kept in a
global, or a garbage collection silently removes the tap (a short probe never collected, the drive did).

## Driving the game

`FF_SAVE=ff_gameplay ./ffrun.sh $PWD/lua/ffdrive.lua` plays the scripted drive from a cold boot and
saves the state at the end of frame 2200 (about 9 s of wall time; `FF_TRACE=1 FF_TRACE_LO/HI` dumps
work RAM per frame to `<FF_OUT>/tmp/`, `FF_VARIANT=ctl` is the control run without the walk-test
presses, `FF_LOAD=<state>` loads one at frame 1). Inputs are set in `emu.register_frame_done` with
`field:set_value(1/0)`; a level set at the end of frame N is what the game reads from N+1.
`ioport.txt` lists the 36 ioport fields (`:IN0`, `:IN1`, `:DSWA/B/C`, polarity measured: all active low;
Coin 1 reads `$00fe` only from the frame after a multi-frame hold).

| frames | input | result |
|---|---|---|
| 1100-1112 | Coin 1 | `CREDIT =1` on the title screen (credit byte `$ff804d`) |
| 1150-1162 | P1 Start | SELECT PLAYER, cursor on Guy |
| 1250-1256 | Right | cursor on Cody |
| 1280-1292 | Button 1 | confirm Cody |
| 1370-1700 | none | scripted stage intro: Cody walks in and kicks the barrels by himself; Right/Left held at 1500-1580 give identical x at every frame, so input is ignored |
| 1800+ | Right, Left, Up, Down | the walk test below |
| 2040-2195 | Right | Bred appears and grapples Cody; state saved at 2200 (`gameplay.png`) |

A hold-right test before about frame 1700 reads as "input does nothing"; test after the intro.

Proven (`lua/analyze_inputs.py`, per-frame work-RAM trace of frames 1790-2029, reproduced from the
promoted scripts): player x word `$ff856e` changed in 59 of 60 Right frames (steps +1/+2, monotone, the
missing one is the one-frame latency), 39 of 40 Left (-1/-2), 0 on 81 idle frames and 0 in the other
axis's phases; y word `$ff8572` changed in 19 of 30 Up frames and 16 of 20 Down (it clamps at 44..63);
the control run stays at x=194, y=44 over the same frames and its work RAM equals the drive's through
frame 1800 and first differs at 1801. Also seen (names inferred from behaviour, no game reader of them
identified): `$ff805c` rises `$0100`, `$0101` while Right is held (an input shadow?). Named later from
their readers (`frame.md`): `$ff85dc` is Cody's attack-box centre x (`+116` of his record), `$ff85ee` the P1
score (`+134`, BCD in hundreds; `$0300`, `$0600`, `$1600` against HUD 300, 600, 1600 in 6 of 6 screenshots),
`$ff8580` his health (`+24`), `175(A5)` TIME.

Determinism and resume: work RAM at frame 2200 sha256 `79ed3cc1...0b2c` and gfx RAM
`d6fbca5f...d8b0` are identical over three cold boots; a state loaded in
a fresh MAME matches a fresh run's next 6 frames of work RAM byte for byte (6 of 6). The `.sta` file
itself differs by one byte of device state between boots: compare RAM, not the file.

## Harness facts (checked on this build, MAME 0.289)

- Lua sees the debugger only under `-debug`; `-debugger none` keeps it headless.
- `emu.register_periodic` runs about once per frame **and keeps running while the CPU is stopped on a
  breakpoint**; `dbg.execution_state` is `"stop"` then. There is no `emu.register_pause`; the 0.289
  names are `emu.add_machine_pause_notifier` / `..._resume_notifier`.
- While stopped, `cpu.state["PC"]` reads **2 above** the breakpoint address (`$540` for `bpset 53e`);
  `cpu.state["CURPC"]` is the instruction address. Compare on `CURPC`.
- The stack pointer is `SP` (no `A7`). Registers: `D0-D7 A0-A6 SP USP SR PC CURPC`.
- `emu.register_frame_done` works without `-debug`. `manager.machine:save("n")`/`:load("n")` work from
  it (file `<state_dir>/ffightuc/n.sta`; the load applies before the next callback and restores the
  screen frame counter). `screen:snapshot(name)` renders under `-video none` (384x224). Ports:
  `manager.machine.ioport.ports[":IN0"].fields["Coin 1"]:set_value(1)`.
- Not tested: the drive with `-debug` on (`callcap.lua`'s stop at `$53e` may interact with the frame callback).
- Setting registers from a periodic callback while the CPU free-runs did not take (PC stayed in the
  idle loop, sentinel never reached). `callcap.lua` therefore stops the CPU at the VBL entry `$53e`
  once per frame, and sets the call up only after `warm` frames of that.
- **Lua cost** (measured on 0.289, `sb_s4` frames 87,000 to 107,000; MAME itself is about 79% of a bot run's wall time, about 870 frames/s): `mem:read_range(lo, hi, 8)` returns the bytes in bus order and
  equals a per-word `read_u16` loop (work RAM 65,536 of 65,536 bytes, gfx RAM 196,608 of 196,608, two smaller regions), about 100 times faster for a dump: `lib.lua` `M.ram`/`M.region` use it.
  For many small reads it is the wrong tool (a 2,496-byte pool: 23 us against 33 us for 113 cached byte reads); there cache the method, `local ru8 = m.read_u8` then `ru8(m, a)`, 0.25 us a call against
  0.85 us for `m:read_u8(a)` (the method lookup on the userdata dominates). Whole-run effect on the bot of caching, no per-frame tables and a cheaper `ffdrive.lua` trace hash: 34.6 s to 31.5 s
  (1.10x, 3 interleaved runs each); work RAM, gfx RAM, `bot.log` and `drive_trace.txt` are byte-identical to the unoptimised files, and the default-option gates (`py/stage/run.sh boss`, `stage1`) still give
  the hashes of `py/stage/README.md`. MAME silently accepts bad arguments (`read_u16("abc")` returns 255, a float address is accepted): a script typo reads wrong data rather than failing.

## callcap

`lua/callcap.lua` is the MAME counterpart of the ST `callcap`: warm up, stop at the VBL entry, apply
`regs`/`pokes`, push a sentinel return address, run with `SR=$2700` until the sentinel, then print
`regdelta` and `mem` lines (work RAM and gfx RAM diffed by default). Spec format is in the file header.
Validated on `$50e` (`lua/specs/validate_50e.lua`): the code writes `D0+$4400` to 32 words at
`$908500`, stride 4, when `142(A5)==0`, `132(A5)!=0` and bit 6 of `100(A5)` is set (`A5=$ff8000`).
Live: 32/32 words written (the odd bytes `20`→`53`; the even bytes were already `44`), `D0=$4453`,
`D7=$ffff`, `A0=$908580`, nothing else changed. The negative control with `142(A5)=1`
(`validate_50e_gated.lua`) returns with an empty diff. The check covers one routine in the attract
mode; it does not yet cover a routine that sleeps, yields (`trap #4/#5`) or waits on a VBL flag.

## Hardware and boot

The hardware reference is `hardware.md` (read from `cps1.cpp` 0.289, every address with a source line
and a tag for what the ROM confirms). What the rest of this README depends on: `ffightuc` is board
89624B-3 with **CPS-B-05** (layer control `$800168`, priority masks `$80016a-$800170`, palette control
`$800172`, ID register `$800160` reads `$0005`), not the `CPS_B_04` of `ffight`/`ffightu`; the ROM's
own writes match B-05. The 68000 map is program ROM `$000000-$3fffff` (including `ff-32m.8h` at
`$080000`, no main-CPU bank switching), inputs `$800000` (IN1 word, P1 low byte, P2 high byte) and
`$800018-$80001e` (IN0, DSWA/B/C bytes), coin control `$800030`, CPS-A `$800100-$80013f`, CPS-B
`$800140-$80017f`, sound latches `$800180`/`$800188`, gfx RAM `$900000-$92ffff`, work RAM
`$ff0000-$ffffff`. VBL is one interrupt at scanline 240 (IPL1, vector `$68` by autovector convention,
unconfirmed in the source); there is no raster interrupt on this board. Z80: ROM `$0000-$7fff`, banked
`$8000-$bfff`, RAM `$d000`, YM2151 `$f000`, OKI `$f002`, bank `$f004`, latches `$f008`/`$f00a`.

From the ROM: SSP `$00ff1000`, reset PC `$0005e88c`; the reset code clears the sound latch and coin
registers, then programs the CPS-A layer base pointers (`$800100..$80010e`); VBL vector `$68` ->
`$53e` latches scroll registers into CPS-A/B, reads the inputs into `84..103(A5)`, calls `$984`, `$fac`,
`$e46`, then counts down the sleep timers of the task records. The task kernel (16 records at
`$ff1000`, `trap #0..#8` as create/exit/kill/sleep/yield/suspend/wake/restart/reset) is in `kernel.md`.
The in-level frame (TIME, the object pools, health, hit boxes, damage, the sprite list builder) is in `frame.md`. The enemy handlers (kinds 0 to 8) are in `ai.md`, the player's states, moves, pickups, score and continue scene in `player.md`. The bosses (pool 4, DAMND first) are in `boss.md`, the placement path and the other pools of a played stage in `placement.md`, the phase machine, area and stage transitions, camera, TIME and the player's scripted states in `transitions.md`, two players, Guy, Haggar and player versus player in `twoplayer.md`.

## Scripts

Lua (run through `ffrun.sh`, or `ffmame.sh` for `-debug` ones; all wrap `ffdrive.lua`, `FF_LOAD=<state>` starts
from a saved state, `FF_STOP=<frame>`):

| script | what it does |
|---|---|
| `lua/ffdrive.lua` | the cold-boot drive and state save; `FF_PLAN=<plan.lua>` adds `{frame, field, level}` input entries (`lua/plans/`), `FF_CENSUS=<file>` logs the live records per frame, `FF_SHOT_*` takes screenshots. `plans/plan3.lua` is the drive to `ff_enemies` (`FF_SAVE=ff_enemies FF_SAVE_FRAME=4150 FF_PLAN=...`) |
| `lua/tap.lua`, `fieldtap.lua`, `htap.lua` | write/read taps on word ranges (`FF_W`, `FF_R`), on record byte ranges over the object pools (`FF_FIELDS`), and on the overlap-test operands |
| `lua/hpbar.lua`, `recdump.lua` | per-frame HUD bar tiles with Cody's and Bred's health words; per-frame records of Cody and Bred (`FF_PRESS` holds Button 1) |
| `lua/hitcount.lua` | count executions of listed addresses (`FF_ADDRS`, needs `FF_MAMEARGS="-debug -debugger none"`) |
| `lua/occ.lua`, `spawnlog.lua`, `poke_hp.lua` | pool occupancy per frame; spawn writes with the camera and script pointer; the lives and health poke |
| `py/hpcheck.py`, `boxcheck.py`, `hitcheck.py` | gates: HUD bar versus health, box derivation versus `$32c4`, the overlap test versus 818 live calls |
| `py/hudbar.py`, `hudenemy.py`, `namesheet.py`, `poolcensus.py` | HUD pixel width versus health, enemy-name sheets, the census of `ff_enemies` |
| `py/rd.py`, `jt.py`, `callers.py` | read ROM or state words, resolve a `move.w 6(PC,Dn.w),D1 / jmp 2(PC,D1.w)` table (pass the address of the `move.w`), find direct callers |
| `py/ai_kind0/` (README there) | `ai.md` "Shared helpers and kind 0": `run_ai.sh` (rec/cold/hit/poke wrapper), `poolrec.lua` and `hitc.lua` (per-frame record dump, breakpoint counts, `FF_POKE`/`FF_COPY`/`FF_WTAP`), `rdl.py` (recursive lister with jump tables), `anims.py` (animation and attack-box decoder), gates `counters.py`, `dmgcheck.py` (59/59), `slotcheck.py` (2855/2857), `rngcheck.py` (505/505), `hist.py`, `animstate.py`, `st28.py`; `gates.sh` reruns all (`AI_OUT`, `FF_RUN`) |
| `py/ai_kind123/` (README there) | `ai.md` "Kinds 1, 2 and 3": `run.sh`, `fdrive.lua` (spawns the kinds into `ff_enemies` by emulating `$3892`, `FF_NOSCRIPT` clean arena), `hits.lua`, state/transition/damage logs, combo-script, stat-table and animation decoders; `gates.py` redoes names 9/9, damage 98/98, slot geometry, target rule 8/8, guard rolls, dodge length and the `ff_kinds123` determinism (`AI123_RUN`, `AI123_OUT`) |
| `py/ai_kind45/` (README there) | `ai.md` "Kinds 4 and 5": `drv.lua` spawns one fighter into `ff_enemies` and dumps per-frame RAM; `gate_dmg.py` (151/151), `gate_zone.py`, `gate_zone4.py`, `gate_names.py` (5/5), `gate_caps.sh` (`$3e88` caps, 16/16); `anim.py`, `chars.py`, `script.py`, `mklist.py` decode animations, characters, the `$5f7e` stage script and ROM ranges (`AI45_RUN`, `AI45_OUT`; `runs.sh`, then `gates.sh`) |
| `py/ai_kind6/` (README there) | `ai.md` "Kind 6": recursive-descent lister, stage-script parser, `k6run.lua` (spawn, force, poke, bot harness through the real script engine, `ffrun_k6.sh`), `k6hit.lua` breakpoints, state histograms, decision, dodge and attack-mask checks, `gate_dmg` 85/85, `gate_score` 15/16 (`K6_RUN_DIR`; `make_pre.sh`, then `run_checks.sh`, about 15 min) |
| `py/ai_kind78/` (README there) | `ai.md` "Kinds 7 and 8": `rdis.py`, `scripts.py`, `hudnames.py`, `anims.py`, the spawn harness (`spawn.lua`, `sp.sh`, `ffrun.sh`) and the handler-count gates (`corpus.sh`/`corpus.py`, `forced*.sh`/`corpus2.py`, `cover.py`, `kind7.sh`, `script_spawn.sh`, `determinism.sh`; `FF_E_RUN`, `FF_E_OUT`) |
| `py/player/` (README there) | `player.md`: Cody driver and logger (`pdrive.lua` with plans, pokes, taps and breakpoints), ROM readers (`ffchar.py`, `boxes.py`, `dmg.py`, `anim.py`, `rdis.py`, `tab.py`) and 19 gates for the move set, damage, throws, items, weapons, kill awards, walk speed, drop rule, death and lives (`sh gates.sh`; `FFP_RUN`, `FFP_OUT`) |
| `lua/stagebot.lua`, `py/stage/` (README there) | plays player 1 from live records instead of spawning: `run.sh boss` (cold boot to the stage 0 area 2 trigger, state `sb_boss`, frame 8298), `run.sh stage1` (through DAMND and the area clear, `sb_s1`, frame 11595), `chain.sh` (stage 1, bonus stage 6, into stage 2), `census.py` (18 of 18 script entries seen). **The bot plays the whole game and the ending** (`chain.sh 2 6` with `FF_BOT_LANEFIX/LURE/UNSTICK/HP0`; options, the three stage 2 stalls and the per-stage table are in the README there; `ending.png`) |
| `py/boss/` (README there) | `boss.md`: harness `dm.lua`/`par.sh`/`runs.sh`, readers, `rdis2.py` (table-aware lister) and 14 gates: damage on Cody 127/127, on DAMND 31/32, attack pick 160/160, thresholds, pause release, death (`gates.sh`; about 3 minutes in parallel) |
| `py/placement/` (README there) | `placement.md`: the placement table readers, entry-to-record match (44 of 46), creator of every record (118/118 to the boss trigger, 159/159 to stage 1), tile patches 6/6, HUD names, allocator call sites (`gates.sh`, about 70 s) |
| `py/objects/` (README there) | `placement.md` "Pool 8 kinds", `ai.md` "The bottle and the fire", `player.md` "Weapons": `sp.lua` (spawn any pool through the allocator bookkeeping, per-frame changed-record, gfx-hash and byte-watch logs, pins, holds, hides, screenshots), `kindmap.py`/`digest.py`/`lst.py` (placement entries and creators of the 60 pool 8 kinds, calls and flags, a table-aware lister), fire, bottle, deflect, pickup and shell runs with checkers, area sweeps, A/B and hide-diff tests (`gates.sh`, about 12 minutes) |
| `py/transitions/` (README there) | `transitions.md`: `trans.lua` change logs and taps, `tables.py`, 23 gates for the phase machine, the 297/278/291 protocol, camera, GO prompt, TIME, bonus-stage entry (`gates.sh`, about 2.5 minutes) |
| `py/twoplayer/` (README there) | `twoplayer.md`: two-player bot and select-screen drives, `py/char` (Guy, Cody, Haggar, 26 gates) and `py/pvp` (player versus player, 14 gates), states and run scripts (`run/all.sh`, about 25 minutes) |
| `py/engine/` (README there) | `kernel.md` "The two deferred rings", `frame.md` "The screen shaker" and the prop victim handlers, `placement.md` terrain codes, the region word, the carrier and the lift actors: static scans of the text-ring callers and the sound ids, the Z80 tap and id sweep, shaker, terrain, Haggar-damage, prop and lift drivers, `dmk.lua`, and `gates.sh`/`gates.py` (16 gates; `FFB_BASE`) |
| `py/gfx/` (README there) | `graphics.md`: tile ROM decode, palette, composite renderer (2,322,432 of 2,322,432 pixels equal to MAME), the game's object-list builder `$16910` ported and gated against MAME (4,572 of 4,572), sheets, characters, whole-stage backgrounds from the game's own column streamers (98.41%); viewer PNGs in `gfx/` |
| `infographic/` | `finalfight_hit_detection.html` (one-page figure set: the game's boxes over two MAME landing frames, an interactive overlap test with the reach list and depth lane, the per-frame pipeline, blow reach of Guy, Cody and Haggar to scale), built by `py/build.py` from `py/frames.py` (boxes of a saved frame and the hit test); gates `py/boxes_gate.py` (box rule over 127 saved dumps) and `py/lanes_gate.py` (candidate rectangle over the same dumps); both read `scratchpad/finalfight/gfx/dump` (`py/gfx/README.md`) |

Gates run this pass from fresh runs: health bar 1100/1100, `+24` writer `$7a12` 8/8, box derivation 1100/1100, overlap
818/818, a third cold boot of `ff_enemies` with identical work RAM (`2657a253...b0ae`) and gfx RAM (`1a4357c4...e94a`),
and the original cold drive (`ff_gameplay`) still giving `79ed3cc1...0b2c` after the `ffdrive.lua` extension.

## Next

1. Natural versions of what pass 5 poked, from the states of the whole-game play (`scratchpad/ANCHORS.md`, `sb_s2a2`, `sb_s3` to `sb_s8`): the bosses of stages 1 to 5 (pool 4 kinds 1 to 5; the bot has killed kinds 2, 3, 4 and 5 and logged their spawns, none is yet checked against `boss.md`), the kind 7 carrier's `+3` steps, pool 8 kinds `$d`, `$e`, `$2b`, kind 8's push, the stage 5 elevator scene, and a census of each stage's spawns against `placement.md` (the logs have every `S` line). Stage 4's play loses lives to TIME (`py/stage/README.md`).
2. What is still unread: terrain codes 6 to 38 (the codes 6, 7, 8 of the stage 2 curb and door are seen, `placement.md`) and the lift lookup `$8a28`; the shaker sites `$426d8`, `$4d550`, `$184b2` (the ending now plays: read the scene objects); glass kinds 11, 13, 14; pool 8 kinds `$35`-`$3a`, `$13`, `$14`, `$33`, `$26`-`$29`; the Z80 control commands `$f1`-`$f6` and the silent sound ids (need the Z80 code).
3. Paths no run took (each section of `ai.md`, `boss.md` and `twoplayer.md` lists its own): DAMND's attack A2 and hit types 2, 4 to 8, the grounded-death variants, thrown flight `$6c96`, entrance types 9 and 11 to 14, Haggar's chain-end back grab, PvP hard boxes and clash.
4. Read the Z80 program (control commands, music ids by ear), then finish graphics (gameplay dumps of stages 4 and 6 and stage 1 areas 0, 2, 3; player scripts reached through pointer tables; held weapons), then Ghouls'n Ghosts only after 1 to 3.

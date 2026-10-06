# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-06 by the session that ended at commit `4ab66ca` (plus the handoff commit).

## Resume point

- Last commits of this workstream: `4ab66ca` (frameskip in `py/stage/run.sh`, `py/gdbstub/`), `aa7185e` (faster Lua harness, `README.md` "Lua cost"); the tooling session (pass 8) changed no game finding. Shared-file commits of that session: `0e8353d` (`tools/fsi_drive.fsx`), `fa29b0a` (`tools/mame_st/`, `DEVELOPING.md`).
  Before them: `aaa0edf` hit detection infographic (`infographic/`), lane rule and once-per-blow rule in `frame.md`; `c279b1c` (graphics decoded and proven against MAME), `39ef56c` (the ending played by the bot, `ending.png`), `758d175` (the bot plays stages 2 to 5, kind 3 destination, stage 2 curb), `d1d499b` (previous handoff).
- Workspace: `M68000/reversing/finalfight/` (`README.md` with the script index; docs `hardware.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`, `boss.md`, `placement.md`, `transitions.md`, `twoplayer.md`,
  **`graphics.md`**). The emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `ff_main.bin`, `ff_z80.bin`, `src/` (MAME driver sources), the old states `ff_gameplay`, `ff_enemies`, `ff_kinds123`;
  the whole-game states **`stage/run/sta/ffightuc/sb_s2a2` (stage 2 area 2 start), `sb_s3`, `sb_s7`, `sb_s4`, `sb_s5`, `sb_s8`** (plus `sb_boss`, `sb_s1`, `sb_s2`, `sb_s6`), logs and RAM dumps in `stage/out5/`, `stage/out6/` (the ending);
  `gfx/dump/` (34 MB, 107 gfx RAM dumps) and `gfx/out/` (sheets, 70 character sheets, pristine strips; regenerate with `py/gfx/README.md`).
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). Not committed.
- Start from: `sb_s4` (stage 4 start, frame 87,000; the bot loses lives to TIME there) or `sb_s5` (boss kind 5 spawns at frame 277,309) for item 1. Copy the `.sta` into the MAME run directory's `sta/ffightuc/`; load **without `-debug`**.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's line-rewrap and `reversing/crudebuster/` is another session's; do not stage them.

## Proven so far

Detail in the docs; every count is from a fresh run of the promoted gate. Passes 1 to 5 (hardware, kernel, TIME, pools, health, boxes, damage, the nine pool-2 fighter handlers, the player's states, moves, items,
score, continue scene; stage 0 by the bot, pool 4 and DAMND, placement, transitions, two players, Guy, Haggar, PvP; the two deferred rings, the shaker, terrain codes, region word, fire, all 60 pool 8 kinds) are in
`README.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`, `boss.md`, `placement.md`, `transitions.md`, `twoplayer.md`. Pass 6:

- **The bot plays the whole game and the ending** (god mode: a survival poke, not a fair play). Stage byte order 0, 1, 6, 2, 3, 7, 4, 5; stage 2 ends at frame 64,752, 3 at 84,917, bonus 7 at 87,000, 4 at 202,844, 5 at
  289,034 (frames of the `sb_s2` lineage). Pool-4 bosses logged: kind 7 carrier (stage 2 area 0 clear, frame 52,760), kind 2 (stage 2 area 2, x `$ec0`), kind 3 (stage 3, frame 79,161), kind 4 (stage 4), kind 5 (stage 5,
  frame 277,309). `py/stage/README.md` ("Stage 2", "Stages 2 to 5, played") has the options and the per-stage table. Not yet cross-checked over two full chains.
- **The ending** (`transitions.md`, `ending.png`): after the stage 5 boss the stage byte runs 8/3, 5/0 (ROUND CLEAR), 9/0 (dialogue), 5/0 (staff roll), 9/0 (dialogue, cast roll, GAME OVER), 8/0 (Mad Gear story): 1 run.
- **Kind 3 destination ignores the camera** (`ai.md`): `$2e3f6` puts the fighter `$50`/`$80` px beside the player on his side and tests only terrain (`$7fac`); 19 of 19 destination changes equal player x +/- offset by the side byte, 11 left of
  the camera (`py/stage/dest_gate.py`). An ANDORE camped off screen for 54,000 frames while the bot hugged the left edge; `FF_BOT_LURE=1` clears it. Whether a human at that edge gets the same camping is [I].
- **A curb and a door of terrain codes** (`placement.md`): stage 2 area 0, x `$3a0`, codes 7 and 8 wall lane y `>= $30` (`$c0e6` writes x+2, `$7c72` takes it back, 61 of 61 frames; from y `$20` Cody walks on, `$3ab` to `$4cf`);
  stage 2 area 2 DOOR prop (x `$888`) fills `$870-$8af` in every lane with codes 6 to 8.
- **Graphics** (`graphics.md`, `py/gfx/README.md`): the tile ROM decode, palette, layers, priority and the sprite rules equal MAME's screenshots in 2,322,432 of 2,322,432 pixels (`prove.py`, rerun this pass); the game's
  object-list builder `$16910` ported and equal to the game's own routine in 4,572 of 4,572 tests (`gate_oracle.py`); whole-stage backgrounds from the game's own column streamers equal 151,230 of 153,678 map entries of
  90 gameplay dumps (`gate_pristine.py`). Corrections to `hardware.md`: object entries are drawn last to first; the sprite table shown is the previous frame's.

Pass 7 (hit detection, `infographic/finalfight_hit_detection.html`, published as https://claude.ai/artifact/1PjfeXcUbWnmPisZL9SJW7, same file path keeps the URL):

- **Both hit boxes re-derived from the ROM over 127 saved dumps**: attack 51 of 52, hurt 212 of 213, 216 of 216 and 55 of 55 absent; the one miss is a hand-spawned kind 7 boss on its first frame (`infographic/py/boxes_gate.py`). The descriptor word is added sign-extended (`adda.w`).
- **The candidate rectangle**: lane -12 to +9, x +-128, written per player by `$8d70`, zero unless the player's state is 2 and `+22` is 0: 115 of 115 active, 26 of 26 inactive (`py/lanes_gate.py`). `139` is the special (sub-state `$10`), not "airborne": corrects the old `frame.md` text. **One blow lands once** through `+22`/`+60` (`$3386`, `$8cc8`, `frame.md` "Hit resolution"): [R] and 13 of 17 saved records, no live count.
- Two landing frames (`st_bb_4800_1`, `st_a_boss_mid_1`): the victim's `+60`, `+22` and hit-stop name the blow and the game's overlap test on the drawn boxes passes in x and y (`py/frames.py`). Box to screen is x - camera, 240 - y (from `$16910`), no pixel gate.

Pass 8 (tooling; nothing about the game changed, every item below is gated):

- **Lua harness faster, byte-identical** (`README.md` "Lua cost"): `lib.lua` `M.ram`/`M.region` use `read_range` (about 100x per dump; 65,536 and 196,608 of those bytes equal); `stagebot.lua`/`ffdrive.lua` cache the memory methods (34.6 s to 31.5 s per 20,000 frames of `sb_s4`;
  MAME is about 79% of a bot run). The default-option gates `py/stage/run.sh boss`/`stage1` reproduce `a0cb6b52`, `6389dc8c`, `359a7c73`.
- **`-frameskip 10 -joystickprovider none` in `py/stage/run.sh`** (`FFS_FRAMESKIP=0` to turn off): about 12% faster, RAM, gfx RAM and logs identical (5 of 5 pairs; the gate above reruns with it). Other wrappers (`ffrun.sh`, `py/placement/run.sh`, `py/transitions/run.sh`, ...) do not have it yet: `FF_MAMEARGS` can carry it.
- **`py/gdbstub/`**: MAME's gdbstub for gdb, a Python RSP client and Ghidra's Debugger, `gate.sh` 600 of 600 stops and 65,536 of 65,536 RAM bytes at six hit counts, `ghidra/chain.sh` 65,536 of 65,536 through a Ghidra trace. The Ghidra GUI is not run (procedure in its README).
- Tried, no gain, do not repeat: GC and JIT settings for the F# core (`DEVELOPING.md` "Performance"), TypeScriptToLua over the Lua scripts (compiles and runs in MAME and catches method typos and bad argument types, not tap garbage collection, float addresses or wrong offsets; only worth it for
  `lib.lua` with a tap registry), several windows chained in one MAME process (a dependent `boss` then `stage1` chain differs from the first frame after the load).

## Open, in priority order

1. **Bosses of stages 1 to 5, natural, against `boss.md` and `ai.md`** (pool 4 kinds 1 to 5; kinds 2 to 5 killed by the bot, logs only). Take a state one frame before each spawn (`FF_BOT_STOPF=<spawn-1> FF_SAVE=...` from `sb_s2a2` (56,841), `sb_s3`
   (79,161), `sb_s4` (87,005), `sb_s5` (277,309); stage 1 area 3 from `sb_s1`), record per frame (`py/ai_kind45/drv.lua`/`py/ai_kind0/poolrec.lua` need the pool-4 records added) and run the damage, attack-pick and zone gates of
   `py/ai_kind45`, `py/boss` on the played records. Also the stage 1 to 5 hand-spawn failures: diff a natural record against a hand-spawned one (`boss.md` trap on `+78`).
2. **Natural versions of pass 5's pokes**: the kind 7 carrier's `+3` steps in the natural clear (state: `sb_s2`, frame 52,760), pool 8 kinds `$d`, `$e`, `$2b`, kind 8's push, the stage 5 elevator scene (`sb_s5`, camera `$600`), and a **census of each stage's
   spawns against `placement.md`** (the `S` lines of `stage/out5/s*.log` have every spawn; extend `py/stage/census.py` with the stage scripts of stages 1 to 5, `py/ai_kind6/scripts.py` parses them but mislabels an entry after a jump past an area end).
3. **Why stage 4 is slow** (116,000 frames, 3 life losses to TIME, `stage/out5/s4.log`) and a reproducibility check: run `chain.sh 2 6` twice in fresh run dirs and `cmp` the RAM of every `sb_s*` (not yet done).
4. **The ending's mechanism**: the runs use stage bytes 5, 9 and 8, so `$553a` has entries past 7 or `$54f8` wraps; read `$54f8`/`$553a`, the phase `$c` handler, and the scene objects for the shaker site `$184b2`.
5. **Still read-only**: terrain codes 6 to 38 (6, 7, 8 are now seen as walls, the dispatch `$7fe6` for them is not read) and the lift lookup `$8a28`; shaker sites `$426d8`, `$4d550`; glass kinds 11, 13, 14; pool 8 kinds `$35`-`$3a`, `$13`, `$14`, `$33`,
   `$26`-`$29`; the fire against a pool-4 boss, a prop and player 2; the Z80 control commands `$f1`-`$f6` and silent sound ids `$4a $4b $4d-$4f $56 $59-$5c` (need the Z80 code).
6. **Paths no run took**: DAMND attack A2 and hit types 2, 4 to 8, grounded-death variants, thrown flight `$6c96`, entrance types 9 and 11 to 14, kind 2's guard slide, TWO.P's attack roll (21% against 44%), Haggar's chain-end back grab, PvP hard boxes
   and the `$78c6` clash.
7. **Graphics remainder** (`graphics.md`, "Not done"): gameplay dumps of stages 4 and 6 and stage 1 areas 0, 2, 3 (from `sb_s4`, `sb_s6`, `sb_s1` with `py/gfx/gfxdump.lua`) to validate and colour their strips; player scripts reached through pointer tables;
   held weapons and effects pools; 28 character sheets use a fallback palette. Then **read the Z80 program**, then Ghouls'n Ghosts only after 1 to 3.
8. **Hit detection remainder** (`frame.md` "Hit resolution"): a live count that one multi-frame blow lands once (write tap on the victim's `+22` and `$7aa8` during a jab on a dummy); the special's +-24 lane live (state with Cody in sub `$10`, read `21250(A5)+6..12`); the attacker-list variants for tags 4 and `$a` (`$3688`, `$35ec`) and the prop lane table `$34c4` entry by entry; a gate for the box-to-screen mapping (x - camera, 240 - y): compare the box edges of a standing fighter with the bounds of his sprite rows from `py/gfx/ffframes.py`.

## Known traps

- **`-frameskip` makes `screen:snapshot` stale** on skipped frames (35 of 60 PNGs differed): `py/stage/run.sh` skips by default, so a bot run's stop-frame PNG is unreliable; use `FFS_FRAMESKIP=0`, or set `manager.machine.video.frameskip = 0` a frame before a snapshot. RAM, gfx RAM and logs are unaffected.
- **Never chain dependent windows in one MAME process** (a state saved by one window loaded by the next): `boss` then `stage1` in one process differs from the first frame after the load; independent windows are identical. Use one process per window.
- The gdbstub needs `-debug` and serves one client per MAME process; a state loaded under `-debug` resumes on another trajectory, so take stub evidence from cold boots (`py/gdbstub/README.md`).

- A web-fetch summary of a source file is a paraphrase from a small model: `curl` the raw file (`scratchpad/finalfight/src/`). A ROM zip's file name does not say which MAME set it is: find the set by CRC.
- MAME on macOS grabs focus even with `-video none` unless `SDL_VIDEODRIVER=dummy`; all wrappers export it. Never launch `mame` directly from a Bash call.
- **`-seconds_to_run` counts emulated seconds and a loaded state restores the frame counter**: loading a state at frame N with a limit below N/59.6 exits MAME one frame after the load, leaving a one-frame dump that looks like a bad state (`py/ai_kind0/run_ai.sh` took 300 s; it
  now reads `FF_SECONDS`; `py/stage/run.sh` uses 6000). `ffdrive.lua`'s `FF_STOP` defaults to 60,000 frames unless the wrapper raises it.
- **A state loaded under `-debug` resumes on a different trajectory** from the same state without `-debug`. Cold boots are identical either way. Take breakpoint evidence from cold boots; run state-resume gates without `-debug`.
- **Kill a background MAME run completely before restarting one.** `pkill -f stagebot.lua` missed one process and MAME ignored SIGTERM on two: two runs appended to one `s2.log` and looked like one impossible trajectory. After a kill, `ps aux | grep mame` and
  `lsof <log>`, `kill -9` your own leftovers, and give every run its own `FFS_OUT`. `chain.sh` is a shell loop around `run.sh`: kill it too.
- The saved gfx/work-RAM dumps are taken at the end of a frame: the player candidate lists are already reset (empty, descriptor words zero) and a landed blow shows only as `+60`/`+22`/`+23` on the victim. Test list membership with a live tap, not from a dump. The stage bot plays with a survival poke, so health in these dumps does not show hits.
- Parallel MAME runs collide on a shared `run/`: every promoted script takes its own run directory from an environment variable (`FFS_RUN`, `FFD_RUN`, `FFT_RUN`, `BB_RUN`, `DM_*`, `FF_RUN`, `FFA_RUN`, `FFB_BASE`, ...).
- **`stagebot.lua` defaults are pinned to what `sb_boss` and `sb_s1` came from** (a pool-4 record at hp 0 is alive: `FF_BOT_HP0=1`; Up raises the lane: `FF_BOT_LANEFIX=1`), and the stage 2 to 5 behaviour is behind `FF_BOT_LURE`, `FF_BOT_UNSTICK` (also the
  prop rules: no FLAME targets, lane-aligned swings), `FF_BOT_PROPS`. Play stages 2 to 5 with all of them: `FF_BOT_LANEFIX=1 FF_BOT_LURE=1 FF_BOT_UNSTICK=1 FF_BOT_HP0=1` (`chain.sh` sets PROPS). `FF_BOT_SCRIPT` cannot stop at a pointer below `$719b4` (the
  pointer starts there): use `FF_BOT_STOPF`.
- **Diagnosing a bot stall** (three found this pass, each different): read the log's last `tgt` line against the camera (an off-screen target means a parked fighter), then a write tap on the player's x `$ff856e` with Right held (`py/ai_kind0/run_ai.sh rec`,
  `FF_WTAP`, `FF_KEYS`): a `$c0e6` write followed by a `$7c72` write of the old value is a terrain wall; then read the terrain codes from the gfx RAM dump with the probe's formula (`placement.md`); a bot that stands in `st=0214` (attack) with `tgt` a prop is
  swinging out of reach, not blocked. A bot option that fires on "target off screen" needs a bound: the first lure froze the bot beside a boss 1,600 px away.
- A state resumed through `poolrec.lua` showed Cody drifting right and up with no keys (`stall/out/st1`) and with Left held (`st3`): not explained. Hold the inputs explicitly and check player movement before using a resumed run for anything that depends on where he stands.
- A hand-spawned record must keep what the game keeps across a free (`+78` is the effect-group handle that `$3a52` reads); spawn through the allocator logic, then diff the record against a natural one.
- Briefs that name a role mislead: the pass-5 brief called `$2874` a sound sender and `$f1ca` a scripted-scene block; both agents corrected it from the bodies. The pass-6 graphics brief was right on layouts but the draw order and the table timing were corrected by pixels.
- Lua `install_write_tap` handles must be held in a global; ranges must be [even, odd]; `screen:vpos()` does not exist; in `callcap.lua` use `CURPC`; debugger `b@(a6+n)` expressions read 0 (A5-based addresses sign-extend): mask with `&ffffff`;
  inside a task `d@(sp)` is the supervisor stack, use `usp` for a task's return address.
- Inputs are levels read once per frame: hold several frames; test movement only after frame ~1700. A fighter dies at `+24 < 0`; hp 0 is alive (HOLLY WOOD, DAMND). A pool-4 boss that the bot ignores keeps the stage script paused for ever.
- Props (pool `$a`) have no ground-line copy at `+14`: use `+10`. Pool `$14` is 30 records of 64 bytes. Prop kinds 16 and 17 are FLAME hazards, not breakable.
- `tools/rdis.py` sizes a dispatch table by its first word / 2 and goes out of sync over back-to-back tables (`$3d5b8`/`$3d5c6`, `$e8f8`): use `py/boss/rdis2.py` (`--end`) or hand roots.
- `py/ai_kind6/scripts.py` labels the stage and area of an entry wrongly where the parse follows a jump past an area's end; the table in `ai.md` is recomputed.
- A task's variable (`$ff1288`) keeps its last value after the task dies: read the TCB state first. The `.sta` file differs by one byte of device state between boots: compare RAM. System `python3` has no numpy: use `M68000/.venv/bin/python`.
  zsh does not word-split `$D`, and an unquoted `export A=.. B=$A/x` on one line expands `$A` before it is set.
- `py/engine/gates.py` and `py/objects/gates.sh` run 10 to 25 minutes and up to 12 MAME processes; run a subset by name (`gates.py shaker haggar`).

## Next session

Run `/resume final_fight`. Item 1: take a state one frame before each natural boss spawn (stages 1 to 5) from the whole-game states, record the pool-4 record per frame, and run the `boss.md`/`ai.md` gates on the played bosses; correct the docs where a
natural boss differs from a hand-spawned one. Then item 2 (carrier steps, pool 8 pokes, a stage-by-stage spawn census from the `S` lines) and item 3's two-chain reproducibility check. Reading the Z80 program or finishing the graphics (item 7) are the
self-contained tasks if the boss work stalls. Do not start Ghouls'n Ghosts before 1 to 3.

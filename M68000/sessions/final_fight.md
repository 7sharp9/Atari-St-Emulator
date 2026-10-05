# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `25a0a25` (plus the handoff commit).

## Resume point

- Last commit of this workstream: `25a0a25` finalfight: stage 0 played by a bot, pool 4 and DAMND, the placement path, transitions, two players. New docs `boss.md`,
  `placement.md`, `transitions.md`, `twoplayer.md`; scripts promoted to `py/stage/`, `py/boss/`, `py/placement/`, `py/transitions/`, `py/twoplayer/`; `lua/stagebot.lua`.
  Before it: `74cf1fc` (previous handoff), `4b2a1aa` (fighter AI and player mechanics).
- Workspace: `M68000/reversing/finalfight/` (`README.md` with the script index; docs `hardware.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`, `boss.md`,
  `placement.md`, `transitions.md`, `twoplayer.md`). The emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `ff_main.bin` (sha256 `8535dd51...e6ec`), `ff_z80.bin`, `src/`, the old states
  `ff_gameplay`, `ff_enemies`, `ff_kinds123`, and **`stage/run/sta/ffightuc/sb_boss.sta`, `sb_s1.sta`, `sb_s6.sta`, `sb_s2.sta`** (stage 0 played by the bot; regenerate with
  `py/stage/run.sh boss`, `stage1`, `chain.sh`). `scratchpad/finalfight/p4/` holds the four agents' working directories and reports (disposable, up to 600 MB each).
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). Not committed.
- Start from: `sb_boss` (frame 8298, camera `$aa0`, stage 0 area 2, DAMND about to be allocated; work RAM `a0cb6b52...4837`) for anything about the first boss, the stage script or
  the area clear; `sb_s1` (frame 11595, stage 1 area 0) for the subway; `ff_enemies` and `ff_kinds123` for the stage-1 fighter arenas. Copy the `.sta` into the MAME run directory's
  `sta/ffightuc/`; load **without `-debug`** (see traps).
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's line-rewrap in the working tree; do not stage it.

## Proven so far

Detail in the docs; every count is from a fresh run of the promoted gate. Earlier passes (hardware, kernel, TIME, pools, health, boxes, damage, the nine pool-2 fighter handlers,
the player's states, moves, items, score and continue scene) are in `README.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`.

- **Stage 0 played from a cold boot** by `lua/stagebot.lua` (state-reading bot; health poke on): `sb_boss` frame 8298, `sb_s1` frame 11595, identical over cold boots (`py/stage/`).
  18 of 18 script entries spawned in order with their fields (`py/stage/census.py`). The stage byte goes 0, 1, **6**, 2, 3, **7**, 4, 5 (6 and 7 are bonus stages).
- **Pool 4 is the boss pool** (`boss.md`, `py/boss/gates.sh`): eight records, updater `$5a1a`, allocator `$390a`, kinds 0 DAMND, 1 SODOM, 2 EDI.E, 3 ROLENTO, 4 ABIGAIL, 5 BELGER,
  6 a debug dummy, 7 a scene object. DAMND: damage on Cody 127/127, on DAMND 31/32 (the 32nd is the thrown landing), attack pick 160/160, hp 300 (450 for two players), retreat
  thresholds, death +10,000. **DAMND's retreat releases the stage-script pause** (`$5f9e`); the kind 4 and 6 group of area 2 spawns only after his second release.
- **Placement path** (`placement.md`, `py/placement/gates.sh`): `$6026` placement record, 14-byte entries, spawner `$61a8`, tables per stage and area; 44 of 46 stage 0 entries matched
  (one lost to the `$3e88` cap, one two-player only), 118 of 118 records attributed to a creator pc to the boss trigger, 159 of 159 to stage 1; door ambushes, tile patches 6/6, prop,
  weapon, item and pool `$14` names from the game's own text.
- **Transitions** (`transitions.md`, `py/transitions/gates.sh`, 23 of 23): phase machine, the 297/278/291/298/299 flags, area clear and intro, camera limits and follow, GO prompt (pool 8
  kind 2, 420 idle frames), TIME (0 kills the player in a normal stage; reload 30), no bonus tally, `$61e24` is the camera.
- **Two players, Guy, Haggar, PvP** (`twoplayer.md`, `py/twoplayer/`, 26 + 14 gates): credits, select screen, mid-game join, masks `127(A5)`/`21610(A5)`, token and health tables per player
  count, script byte 15, target rule 70/70, PvP 1 hp per hit with 100-frame immunity, Guy/Cody/Haggar move tables, Guy's wall jump, Haggar's grapple jump.
- Corrections in place: `frame.md` pool 4 is not "never live"; pool `$14` has 30 records; `$61a8` byte 6 indexes a word table; `$61e24`/`$6241e` are the camera records;
  `py/ai_kind45/script.py` continuation labels are byte offsets into `$5cc2`; `+148` of a player is the PvP immunity byte; the ground-line word `+14`: Up raises it.

## Open, in priority order

1. **Stages 2 to 5 by play.** The bot stalls at stage 2 area 0 (cause not found: it stands still with a target set; lane direction and props are ruled out, `py/stage/README.md`). Debug with `FF_BOT_LANEFIX=1
   FF_BOT_PROPS=1` from `sb_s2` and a `D` dump at the stall (`FF_BOT_DUMP`), or skip areas with the pokes in `transitions.md` (`297(A5)` = 1, `191(A5)` = 3). Then census each stage
   against `placement.md`, play the bosses of stages 1 to 5 (kinds 1 to 5 of pool 4 are read and hand-spawned only; EDI.E's hand spawn reset the machine, cause unknown) and run the kind 7
   scroll-lock test (stage 5 area 0, camera `$1280`: watch `278(A5)`).
2. **Unread code**: the fire bottle `$5957a` and fire prop `$54b4a`, about 48 pool 8 kinds of stages 1 to 5, pool 4 kind 7 (`$f1ca`), `$1b428` (screen shaker, boss scene hooks, called by
   Haggar's throws `$d128`/`$d3a6`), `$1fa5a` attribute bits, the `324(A5)` command ring (`$2874`, table `$4ba6`), `$726e0`, the tag-`$a` victim handlers `$711a`, `$71a2`, `$7222-$7232`.
3. **Paths no run took**: DAMND attack A2 and hit types 2, 4 to 8, grounded-death variants of every kind, thrown flight `$6c96`, entrance types 9 and 11 to 14, kind 2's guard slide, TWO.P's
   attack roll (21% observed against 44% expected), Haggar's chain-end back grab, PvP hard boxes and the `$78c6` clash, the player-state 12 scene (stage 5 elevator [I]).
4. **Re-run the `ai.md` gates on script-spawned records** of stage 0 (`py/stage` logs give the records; the gates start from `ff_enemies` spawns).
5. **The sound queue and the Z80**, then **graphics** (decode a tile, commit a PNG), then Ghouls'n Ghosts only after 1 to 3.

## Known traps

- A web-fetch summary of a source file is a paraphrase from a small model: `curl` the raw file (`scratchpad/finalfight/src/`).
- A ROM zip's file name does not say which MAME set it is: find the set by CRC, then rename the copy.
- MAME on macOS grabs focus even with `-video none` unless `SDL_VIDEODRIVER=dummy`; all wrappers export it. Never launch `mame` directly from a Bash call.
- `-seconds_to_run` counts **emulated** seconds (6000 = 357,000 frames); `ffdrive.lua`'s `FF_STOP` defaults to 60,000 frames unless the wrapper raises it (`py/stage/run.sh` does).
- **A state loaded under `-debug` resumes on a different trajectory** from the same state without `-debug` (`sb_boss` at frame 8300: camera `$aa4` without, `$aa0` with; the stage-1 bot never reached stage 1
  in 22,000 frames with it). Cold boots are identical either way. Take breakpoint evidence from cold boots; run state-resume gates without `-debug`.
- Parallel MAME runs collide on a shared `run/`: every promoted script takes its own run directory from an environment variable (`FFS_RUN`, `FFD_RUN`, `FFT_RUN`, `BB_RUN`, `DM_*`, `FF_RUN`, ...).
- `FF_SAVE` (`lua/stagebot.lua`) writes the state into the run directory's `sta/ffightuc/` and `FF_SAVE_PREFIX` with `FF_BOT_LEAVE` names it after the new stage byte; a run that hits the
  frame limit is saved as `<prefix>stuck<stage>` so it cannot overwrite the state it started from.
- **`stagebot.lua` defaults are pinned to what `sb_boss` and `sb_s1` came from, and two of them are wrong**: a pool-4 record at hp 0 is alive (`FF_BOT_HP0=1`), and Up raises the lane word, the bot presses
  it the other way (`FF_BOT_LANEFIX=1`). Changing a default changes every downstream state and gate frame.
- Lua `install_write_tap` handles must be held in a global; ranges must be [even, odd]; `screen:vpos()` does not exist; in `callcap.lua` use `CURPC`; debugger `b@(a6+n)` expressions read 0
  (A5-based addresses sign-extend): mask with `&ffffff`.
- Inputs are levels read once per frame: hold several frames; test movement only after frame ~1700.
- A fighter dies at `+24 < 0`; hp 0 is alive (HOLLY WOOD, DAMND). A pool-4 boss that the bot ignores keeps the stage script paused for ever.
- Props (pool `$a`) have no ground-line copy at `+14`: use `+10`. `stagebot.lua` before this pass logged pool `$14` at stride `$c0`; it is 30 records of 64 bytes.
- `tools/rdis.py` sizes a dispatch table by its first word / 2 and goes out of sync over back-to-back tables (`$3d5b8`/`$3d5c6`, `$e8f8`): use `py/boss/rdis2.py` (`--end`) or hand roots.
- `py/ai_kind6/scripts.py` labels the stage and area of an entry wrongly where the parse follows a jump past an area's end; the table in `ai.md` is recomputed.
- A task's variable (`$ff1288`) keeps its last value after the task dies: read the TCB state first. The `.sta` file differs by one byte of device state between boots: compare RAM. System `python3`
  has no numpy: use `M68000/.venv/bin/python`. zsh does not word-split `$D`, and an unquoted `export A=.. B=$A/x` on one line expands `$A` before it is set.

## Next session

Run `/resume final_fight`. Item 1: find why the bot stalls at stage 2 area 0 (a `D` dump and a screenshot at the stall from `sb_s2`), or jump areas with the poke recipes, and play on to the bosses of stages 1 to 5;
check each against `boss.md` (health, award codes, triggers) and `placement.md` (census of creators). Then item 2's unread code with one agent per area, briefed with `DEVELOPING.md` "Other tools",
`tools/rdis.py` and `py/boss/rdis2.py`. Do not start graphics or Ghouls'n Ghosts before 1 to 3.

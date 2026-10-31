# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-31 by the session that ended at commit `a587fce` (plus the tool and handoff commits after it).

## Resume point

- Last commit of this workstream: `a587fce` (natural boss fights of stages 1 to 5, carrier and elevator unpoked, per-stage census, stage 4 stall cause), then the `logcmp.py`/`stall4.sh` commit.
  Earlier: `4ab66ca` (frameskip, `py/gdbstub/`), `aa7185e` (Lua harness), `aaa0edf` (hit detection), `c279b1c` (graphics).
- Workspace: `M68000/reversing/finalfight/` (`README.md` with the script index; docs `hardware.md`, `kernel.md`, `frame.md`, `ai.md`, `player.md`, `boss.md`, `placement.md`, `transitions.md`, `twoplayer.md`, `graphics.md`).
  The emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core. ROMs `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS`), not committed.
- Working data: `M68000/scratchpad/finalfight/` (gitignored): `ff_main.bin`, `ff_z80.bin`, `src/`; whole-game states in `stage/run/sta/ffightuc/` (`sb_boss`, `sb_s1`, `sb_s2`, `sb_s6`, `sb_s2a2`, `sb_s3`, `sb_s7`, `sb_s4`, **`sb_s5` = frame 202,844, re-saved this pass**, `sb_s8`; `sb_s5_289055` is the copy the old chain wrote over it), logs in `stage/out/`, `stage/out5/`.
  This pass: `bossrec/` (`out_k1`..`out_k5`, `out_k7`, `out_ke`: `rec.bin` per-frame RAM, `s.log`; `run_k*/sta/ffightuc/bb_k<kind>.sta` one frame before each spawn, `rr_s*` stage-end states), `bossrec/aux/stall*/` (state `st4stall`, frame 102,000). Rebuild any of it with `py/stage/bossrec.sh <kind>` and `py/stage/stall4.sh` (`py/stage/README.md`).
- Start from: `bb_k<kind>` (one frame before boss kind 1, 3, 4 spawns: 38,979, 79,160, 87,004; `bb_k5` 277,308; for EDI.E use `sb_s2a2`, frame 56,840, which already holds his record; `bb_k7` 52,759 before the carrier) or `st4stall`. Copy the `.sta` into a run directory's `sta/ffightuc/`; load without `-debug`.
- Uncommitted work left behind: none of this workstream. `scratchpad/ANCHORS.md` has another session's uncommitted edit, so its Final Fight row was not corrected: it still says `sb_s5` = 202,844 (true again now) without naming `sb_s5_289055` or the `bb_k*`/`st4stall` states. Fix that row when the file is free.

## Proven so far

Passes 1 to 8 (hardware, kernel, frame, AI kinds 0 to 8, player, DAMND, placement, transitions, two players, graphics 2,322,432 of 2,322,432 pixels, hit boxes, the whole game and ending by the bot, tooling) are in `README.md` and the topic docs. Pass 9:

- **Bosses of stages 1 to 5, played** (`boss.md` "Natural fights"; `py/stage/bossrec.sh 1..5`, `py/boss/natural.py`): health 300, 300, 300, 500, 600 and every trigger acting the frame after it is met (5 of 5); awards 20k to 100k paid (5 of 5; ROLENTO's on entering `+2` = 6, BELGER's one frame after death); shaker 28 frames for SODOM, EDI.E, ABIGAIL, none for ROLENTO, BELGER; damage on Cody 60 of 60, on the bosses 138 of 141. One fight per kind.
- **Knockdown hits are unscaled** (`$74aa` -> `$7a04`, `frame.md` "Damage dispatch"): `gate_dmg_boss.py` now models it; DAMND's 31 of 32 unchanged.
- **Hand-spawn failures were the missing triggers**: the natural record at spawn equals the hand-spawn field set, 3 of 3 (kinds 1, 3, 4).
- **BELGER's health resets to 300 once** (`$5077e`, latch `163(A6)`, [R]; live 600 -> 300 at the grab frame, 1 of 1); his damage on Cody comes with pool-6 kind 5 records (43 of 43).
- **Carrier natural** (`placement.md` "Pool-4 kind 7"): `+3` 0, 2, 4, freed in 4 at the area change; 2 lasts 46 frames.
- **Stage 5 elevator natural** (`placement.md`, `$ffb228` actor): player y = actor y + 3 in 683 of 683 moving frames; limit `$1280` at the end.
- **Spawn census, stages 0 to 5** (`placement.md` "Two spawn paths", `py/stage/census.py --stage=N`): script entries 155 of 156, placement type 2/4 entries 247 of 286 (a record: cap refusals and matcher misses not separated).
- **Stage 4's stalls are the bot's closing distance while armed** (`py/stage/README.md`, `stall4.sh`): same state, one variable, camera `$b80` (unchanged bot) against `$1060` (`FF_BOT_ARMDX=50`).
- **Replays are deterministic from `sb_s3`, `sb_s4`, `sb_s5`**: logs frame for frame (`logcmp.py`), stage-end states byte for byte (`sb_s7`, `sb_s8`). From `sb_s1`, `sb_s2` the current bot differs from the old logs (13,150, 43,500).

## Running

Nothing running.

## Open, in priority order

1. **Split the census's 39 unseen placement entries**: a `$3e88` refusal log (breakpoint with D0 and the caller) over `bossrec.sh` replays of stages 1 to 5; done when every unseen entry is a refusal or a named matcher miss.
2. **Natural pool 8 kinds `$d`, `$e`, `$2b` and kind 8's push, the stage 3 area 1 lift unpoked** (`placement.md` "Not read or not proven"): find the frames in the `stage/out5` logs, record them with `bossrec.sh`-style windows, compare with the poked results.
3. **Boss behaviour beyond the totals**: attack picks, reactions and thresholds of kinds 1 to 5 are [R] or unread; the `bb_k*` states start each fight. Read BELGER's `$5075c` state and why the carrier's `+3` = 2 lasts 46 frames.
4. **The ending's mechanism**: stage bytes 5, 9, 8 (`$553a` past 7 or `$54f8` wraps); read `$54f8`/`$553a`, the phase `$c` handler and the shaker site `$184b2`.
5. **Still read-only**: terrain codes 6 to 38 and the lift lookup `$8a28`; glass kinds 11, 13, 14; pool 8 kinds `$35`-`$3a`, `$13`, `$14`, `$33`, `$26`-`$29`; the fire against a boss, a prop and player 2; Z80 control commands and silent sound ids (need the Z80 code).
6. **Paths no run took**: DAMND attack A2 and hit types 2, 4 to 8, grounded deaths, thrown flight `$6c96`, entrance types 9, 11 to 14, kind 2's guard slide, TWO.P's attack roll, Haggar's chain-end back grab, PvP hard boxes, `$78c6`.
7. **Graphics remainder** (`graphics.md` "Not done"), then **read the Z80 program**, then Ghouls'n Ghosts.
8. **Hit detection remainder** (`frame.md` "Hit resolution"): one blow lands once (live tap), the special's lane, tags 4 and `$a` attacker lists, a box-to-screen gate.
9. **Tooling leftovers** (optional): Ghidra GUI attach, `-frameskip` in the other wrappers, `callcap` through the gdbstub.

## Known traps

- **`sh` reads a script as it runs it: editing `bossrec.sh` (or any wrapper) while a chain runs it breaks the running copy** ("unexpected EOF" after the MAME step; this pass, twice). Copy the script to the session scratchpad and run the copy.
- **`pkill -f '<pattern>'` from the Bash tool also matches the tool's own `zsh -c` command line** when the pattern is in that command: it killed the calling shell. Kill by PID from `ps`, filtering out `zsh`.
- **A `bossrec`/`FF_BOT_REC` range must cover each pool's last record plus its stride** (pool 2 is 13 records from `$ff86e8`, ending `$ff90a8`): two short ranges cost two reruns. Use the default `ff12e0-ff1300,ff8000-ffb300`.
- **`chain.sh` overwrites a state when the stage byte returns to a value** (stage 8 -> 5 rewrote `sb_s5` with frame 289,055): check a chain's `STOP` lines before trusting a `sb_s*` frame.
- **Old stage logs came from earlier bots**: from `sb_s1`, `sb_s2` and `sb_s2a2` the current bot takes another trajectory; frames in the old `to_a2`, `a2`, `stage2` logs are not reproducible.
- `-frameskip` makes `screen:snapshot` stale on skipped frames: `FFS_FRAMESKIP=0` for runs whose PNGs matter.
- Never chain dependent windows in one MAME process; a state loaded under `-debug` resumes on another trajectory; take breakpoint evidence from cold boots.
- `-seconds_to_run` counts emulated seconds and a loaded state restores the frame counter: raise the limit for late states.
- Kill a background MAME run completely before restarting one; give every run its own `FFS_OUT`/run dir (`FFS_RUN`, `BR_ROOT`, `ST4_ROOT`, ...).
- `stagebot.lua` defaults are pinned to `sb_boss`/`sb_s1`; play stages 2 to 5 with `FF_BOT_LANEFIX=1 FF_BOT_LURE=1 FF_BOT_UNSTICK=1 FF_BOT_HP0=1 FF_BOT_PROPS=1`. A pool-4 record at hp 0 is alive.
- Dumps are taken at the end of a frame; the god poke tops Cody's health after the record, so health in a dump shows the drop of that frame only.
- A hand-spawned record must keep `+78`; boss health 0 is alive; inputs are levels read once per frame.
- `tools/rdis.py` mis-sizes back-to-back dispatch tables: use `py/boss/rdis2.py`. `py/ai_kind6/scripts.py` mislabels entries after a jump past an area end.
- System `python3` has no numpy: use `M68000/.venv/bin/python`. zsh does not word-split `$D`.

## Waiting on Dave

- Proposed `CLAUDE.md` "Shell pitfalls" lines (not added: this session was told not to edit `CLAUDE.md`): "`sh` reads a script while it runs it: editing a running wrapper breaks it; run a copy" and "`pkill -f` from the Bash tool matches its own `zsh -c` line when the pattern appears in the command: kill by PID". Both are in Known traps above until then.
- The `scratchpad/ANCHORS.md` Final Fight row (see Resume point) once the other session's edit there is committed.

## Next session

Run `/resume final_fight`. Open item 1 first: a `$3e88` refusal log over `py/stage/bossrec.sh` replays of stages 3 to 5 (those replays are deterministic), then rerun `census.py --stage=N` and split the 39 unseen entries.
Then item 2 (pool 8 kinds `$d`, `$e`, `$2b`, kind 8's push, the stage 3 lift unpoked). Reading the Z80 program or finishing graphics are the self-contained tasks if those stall. Do not start Ghouls'n Ghosts before items 1 to 3.

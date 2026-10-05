# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `7155dac` (plus the handoff commit after it).

## Resume point

- Last commit of this workstream: `7155dac` finalfight: drive into stage 1 by ioport, reproducible state,
  task kernel checked against a 1200-frame trace.
- Workspace: `M68000/reversing/finalfight/` (`README.md`, `hardware.md`, `kernel.md`, `ioport.txt`,
  `ffmame.sh` for the debugger/callcap runs, `ffrun.sh` for input-driven runs, `lua/`). The emulator and
  oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`):
  `ff_main.bin` (sha256 `8535dd51...e6ec`), `ff_z80.bin` (`2703eedf...2ddd`), `src/` (the raw
  `cps1.cpp`, `cps1_v.cpp`, `cps1.h` from tag `mame0289`), `ff_gameplay.sta`, `run/` (MAME cfg/nvram/state),
  `verify/` (this session's traces, disposable). Rebuild the dumps: `FF_OUT=<dir>
  reversing/finalfight/ffmame.sh script $PWD/reversing/finalfight/lua/dumprom.lua`; rebuild the state:
  `FF_SAVE=ff_gameplay reversing/finalfight/ffrun.sh $PWD/reversing/finalfight/lua/ffdrive.lua` (about 9 s).
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides; `ffightuc.zip` is a copy of the
  misnamed `~/Downloads/ffightub.zip`). Not committed.
- Start from: the state `ff_gameplay` (stage 1, Cody, Bred on screen, end of frame 2200); copy
  `scratchpad/finalfight/ff_gameplay.sta` to `run/sta/ffightuc/` and load it from a script, or just re-run
  the drive. Work RAM sha256 at that frame `79ed3cc1...0b2c`.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's
  line-rewrap in the working tree; do not stage it.

## Proven so far

Detail in `reversing/finalfight/README.md`, `hardware.md`, `kernel.md`.

- Hardware read from `cps1.cpp` 0.289 with line numbers (`hardware.md`): `ffightuc` is **CPS-B-05**
  (`cps1_v.cpp:1802`), not B-04; `ff-32m.8h` is program ROM at `$080000` (`cps1.cpp:5746`), the main
  CPU has no bank switching. Input bits and DIP table checked against the live ioport (`ioport.txt`).
- Drive from cold boot to stage 1 by coin, Start, Right, Button 1 (`lua/ffdrive.lua`): work RAM and gfx RAM
  hashes identical over three cold boots; a loaded state matches a fresh run's next 6 frames of work RAM,
  6 of 6 (`lua/resume_check.lua`). The `.sta` file bytes are not stable (1 byte of device state).
- The intro (frames ~1370-1700) is scripted and ignores input. After it, x `$ff856e` changed in 59 of 60
  Right frames, 39 of 40 Left, 0 of 81 idle; y `$ff8572` 19 of 30 Up, 16 of 20 Down (clamp 44..63); control
  run flat (`lua/analyze_inputs.py`).
- Task kernel (`kernel.md`): states 0/1/2/4/8/`$c`, `trap #0..#8` bodies read; 1200-frame TCB trace agrees
  (VBL countdown 177 of 178 timer>1 samples decrement by one; saved PC `$884`/`$8b8` equal the addresses
  after the `trap #3`/`#4` wrappers). Read and trace-checked, not run under a breakpoint.
- `lua/callcap.lua` on `$50e` (earlier pass): 32/32 words, negative control empty.

## Open, in priority order

1. **Run the kernel live.** `callcap`/`bp` on `$8be` (yield), `$88a` (sleep), `$832` (create) so the
   trap semantics are checked by running them, and find where `register_frame_done` samples relative to
   the VBL interrupt. Needs `ffmame.sh` (debugger) and the drive together: untested that `callcap.lua`'s
   stop at `$53e` coexists with the frame callback; if not, log from a `bpset` callback instead.
2. **Name the tasks.** Log every task's entry point (`+4` at `trap #0`/`#7`, slot in `D0`) over the drive,
   read each body to its first branch, then name roles (slot 11 yields every frame, slots 7/8 sleep one
   frame at a time; roles unknown). Everything about enemies hangs off this.
3. **Entity/object pool, health, TIME, hit boxes, weapons, scoring.** `$ff85dc`, `$ff805c`, `$ff85ee`,
   `$ff0946` are named from behaviour or HUD only (`$ff85ee` score checked against the HUD, 6 of 6). The
   TIME counter and player health were not found by value search; find the game's own reader of each
   field before naming it (CLAUDE.md census rules). Get a second state with two or more enemies first.
4. **Graphics**: `hardware.md` has layouts and mapper ranges; the plane/byte order across
   `ff-5m/7m/1m/3m` is inferred. Decode one known tile, render a sheet, commit the PNG with the doc.
5. **Z80 sound CPU** (`ff_z80.bin`, YM2151, OKI), then Ghouls'n Ghosts: test whether Capcom's
   object/sprite engine is shared (unchecked; only after items 2 and 3).

## Known traps

- A web-fetch summary of a source file is a paraphrase from a small model: the earlier `cps1.cpp`
  summary gave the wrong CPS-B row (`CPS_B_04`; the config is found by exact driver name with no clone
  chain) and called `ff-32m.8h` a bank ROM. Use `curl` on the raw file (`scratchpad/finalfight/src/`).
- A ROM zip's file name does not say which MAME set it is. Find the set by CRC: `mame -listxml |
  awk '/<machine name=/{m=$0} /crc="<crc>"/{print m}'`, then rename the copy. Parent and clone zips
  must both be present for a split set.
- In `callcap.lua`: `PC` reads 2 above the breakpoint while stopped, use `CURPC`; the stack pointer is
  `SP`; registers set while the CPU free-runs do not take; there is no `emu.register_pause`
  (`emu.add_machine_pause_notifier`); `register_periodic` keeps firing while stopped (test
  `dbg.execution_state == "stop"`).
- `-video none` needs `-seconds_to_run` and a script that calls `manager.machine:exit()`.
- Inputs are levels read once per frame: hold several frames; a level set at the end of frame N is seen
  from N+1; hold Coin for several frames and read it a frame later. Test movement only after frame ~1700.
- `ffdrive.lua` silently skips `FF_TRACE` dumps if `<FF_OUT>/tmp` does not exist (`ffrun.sh` creates it).
- System `python3` has no numpy: use `M68000/.venv/bin/python` for `analyze_inputs.py`.
- A subagent's `.sta`-hash or "x equals y" claims were rerun from a fresh cold boot before use; do the
  same with the next agents' scripts. The Bash cwd drifts: `cd` to an absolute path first.

## Next session

Run `/resume final_fight`. Item 1: put `bpset` on `$8be`, `$88a` and `$832` under `ffmame.sh` with the drive
(or a loaded `ff_gameplay` state) and log slot, `D0` and the caller PC, then use the `trap #0`/`#7` entry
points to name the tasks (item 2). Two agents fit again: one for the breakpoint harness, one for a second
state with several enemies plus a search for the TIME and health fields. Do not start graphics or Ghouls'n
Ghosts before the tasks are named.

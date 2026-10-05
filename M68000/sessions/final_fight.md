# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `b18ff59` (plus the handoff commit after it).

## Resume point

- Last commit of this workstream: `b18ff59` finalfight: task kernel checked live by write taps, 15 task
  starts named, headless wrappers stop taking focus.
- Workspace: `M68000/reversing/finalfight/` (`README.md`, `hardware.md`, `kernel.md`, `ioport.txt`,
  `ffmame.sh` for the debugger/callcap runs, `ffrun.sh` for input-driven runs, `lua/`). The emulator and
  oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`):
  `ff_main.bin` (sha256 `8535dd51...e6ec`), `ff_z80.bin` (`2703eedf...2ddd`), `src/` (raw `cps1.cpp`,
  `cps1_v.cpp`, `cps1.h` from tag `mame0289`), `ff_gameplay.sta`, `run/` (MAME cfg/nvram/state,
  `kernel_log.txt` 1,657,594 lines from this session, md5 `941ffa23...f30`, disposable), `verify/`
  (`ff_gameplay_ram.bin`, traces). Rebuild the dumps: `FF_OUT=<dir> reversing/finalfight/ffmame.sh script
  $PWD/reversing/finalfight/lua/dumprom.lua`; rebuild the state: `FF_SAVE=ff_gameplay
  reversing/finalfight/ffrun.sh $PWD/reversing/finalfight/lua/ffdrive.lua` (about 9 s); rebuild the kernel
  log: `FF_KLOG_LO=0 FF_VARIANT=ctl reversing/finalfight/ffrun.sh $PWD/reversing/finalfight/lua/kernel_log.lua 300`
  (about 40 s), then `python3 reversing/finalfight/lua/kernel_tasks.py`.
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). Not committed.
- Start from: the state `ff_gameplay` (stage 1, Cody, Bred on screen, end of frame 2200, `0(A5) = 6`).
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's
  line-rewrap in the working tree; do not stage it.

## Proven so far

Detail in `reversing/finalfight/README.md`, `hardware.md`, `kernel.md`.

- Hardware read from `cps1.cpp` 0.289 with line numbers (`hardware.md`): `ffightuc` is CPS-B-05, `ff-32m.8h`
  is program ROM at `$080000`, no main-CPU bank switching; inputs and DIPs checked against the live ioport.
- Drive from cold boot to stage 1 by coin, Start, Right, Button 1 (`lua/ffdrive.lua`): work RAM and gfx RAM
  identical over three cold boots, a loaded state matches 6 of 6 next frames (`lua/resume_check.lua`);
  input gating by x/y counters (59/60, 39/40, 19/30, 16/20, 0 on 81 idle frames, `lua/analyze_inputs.py`).
- Task kernel checked live by write taps (`lua/kernel_log.lua`, `lua/kernel_tasks.py`, `kernel.md`): 1,657,594
  TCB-area writes over frames 0-2200, md5-identical across two runs; every state write comes from the trap
  body the listing names (12 creates at `$842`, 3 pool creates at `$966`, 1 restart, 4 exits, 3 kills, 9186
  sleeps, 117008 yields); 15 creates = 12 + 3. `D0` of a create is `slot * 16`. `trap #5` and `#8` never ran.
- VBL flag `$ff1100` written once in each of 2086 frames, a median 3.8 scanlines after MAME's frame-done
  callback: samples taken in `register_frame_done` are the state before that frame's VBL handler.
- 15 task starts by entry point, with slots and lifetimes (`kernel.md` "Tasks seen over the drive"). Strong
  from body plus a second observation: slot 2/3 are the P1/P2 controllers (records `$ff1204`/`$ff1244`, byte 0
  = player index, word 2 = 0 active / 2 inactive in the saved state), slot 9 credit and Start handler
  (`76(A5)` credits 0 after Start), slot 15 credit jingle (created by the coin, killed by Start), slot 1 stage
  clock (dispatch word `0(A5)`: 0, 2, 4, 6 at frames 1169, 1200, 1312, 1313, written by the table's own
  bodies). Slots 7, 8, 11, 12, 5, 6 are named from the body alone and tagged inferred.
- No task is created for enemies between frames 1311 and 2200 while Bred appears: they are not tasks.
- `lua/callcap.lua` on `$50e` (earlier pass): 32/32 words, negative control empty.

## Open, in priority order

1. **Read the state-6 frame pipeline `$4e3a`** (`$5326`, `$5238`, `$5668`, `$6396`, `$6026`, `$61e24`,
   `$16600`, with `$50e` calls between). Enemies, items, player health, TIME and hit boxes are updated
   there. Method: read each callee to its first branch, grep the topic docs for the address first, then a
   write tap (as in `kernel_log.lua`, `FF_KLOG_EXTRA`) on the object pool and player records to see who writes
   which field. Census rule: find the game's own reader of a field (HUD, `$ff85dc`, `$ff85ee`) before naming it.
2. **Second state with two or more enemies** (the drive reaches one, Bred), plus a search for the TIME
   counter and player health by their readers, not by value.
3. **Slot 11's queues** (`516(A5)`, `324(A5)`, `$1a22`) and the `jsr $2874` senders: confirm it is the sound
   command queue (tap `$800180`/`$800188` writes and match them to queue entries), then read the Z80 side.
4. **Confirm the `[I]` task roles** (slots 7, 8, 12, 5, 6): tap `106(A5)`/`110(A5)` and `$800030`, and get
   the slot 5 body past its wait by letting the player die (needs an input script that loses all lives).
5. **Graphics**: layouts and mapper ranges are in `hardware.md`; the plane/byte order across
   `ff-5m/7m/1m/3m` is inferred. Decode one known tile, render a sheet, commit the PNG with the doc.
6. **Z80 sound CPU** (`ff_z80.bin`, YM2151, OKI), then Ghouls'n Ghosts: test whether Capcom's
   object/sprite engine is shared (only after items 1 and 2).

## Known traps

- A web-fetch summary of a source file is a paraphrase from a small model: the earlier `cps1.cpp` summary
  gave the wrong CPS-B row and called `ff-32m.8h` a bank ROM. Use `curl` on the raw file
  (`scratchpad/finalfight/src/`).
- A ROM zip's file name does not say which MAME set it is. Find the set by CRC: `mame -listxml |
  awk '/<machine name=/{m=$0} /crc="<crc>"/{print m}'`, then rename the copy.
- MAME on macOS grabs focus even with `-video none` unless `SDL_VIDEODRIVER=dummy` is set; both wrappers
  now export it. Never launch `mame` directly from a Bash call.
- Lua `install_write_tap` returns a handle; if it is not held in a global, a garbage collection removes the
  tap silently (a short probe works, a drive that allocates RAM dumps does not). Tap ranges must be
  word-aligned (`ff807e-ff807f`). `screen:vpos()` does not exist in 0.289: use `machine.time:as_double()`
  with `screen.frame_period` and `scan_period`. A tap callback that errors prints `LUA ERROR`; wrap in
  `pcall` while debugging.
- In `callcap.lua`: `PC` reads 2 above the breakpoint while stopped, use `CURPC`; the stack pointer is
  `SP`; registers set while the CPU free-runs do not take; `register_periodic` keeps firing while stopped.
- `-video none` needs `-seconds_to_run` and a script that calls `manager.machine:exit()`.
- Inputs are levels read once per frame: hold several frames; a level set at the end of frame N is seen
  from N+1. Test movement only after frame ~1700.
- `ffdrive.lua` silently skips `FF_TRACE` dumps if `<FF_OUT>/tmp` does not exist (`ffrun.sh` creates it).
- System `python3` has no numpy: use `M68000/.venv/bin/python` for `analyze_inputs.py`.
- A task's variable (`$ff1288`) keeps its last value after the task dies: read the TCB state before saying
  a task "is in state N".
- zsh does not word-split `$D`: use a shell function for repeated `disassemble.py` arguments.

## Next session

Run `/resume final_fight`. Item 1: disassemble the state-6 pipeline callees from `$4e3a`, then put write taps
on the player records (`$ff1204`, `$ff1244`) and the object pool fields found there, using
`FF_KLOG_EXTRA` in `kernel_log.lua`. Two agents fit: one for the pipeline read, one for a second
multi-enemy state plus the TIME/health readers. Do not start graphics or Ghouls'n Ghosts before the pipeline
is read.

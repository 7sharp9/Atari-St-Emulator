# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `66c92d5` (plus the handoff commit after it).

## Resume point

- Last commit of this workstream: `66c92d5` finalfight: first arcade subject, MAME harness.
- Workspace: `M68000/reversing/finalfight/` (README with the harness facts, `ffmame.sh`, `lua/`). The
  emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored): `ff_main.bin` (68000 space
  `$000000-$0fffff`, sha256 `8535dd51...e6ec`), `ff_z80.bin` (sha256 `2703eedf...2ddd`), `run/` (MAME's
  cfg/nvram/state). Rebuild: `FF_OUT=<dir> reversing/finalfight/ffmame.sh script
  $PWD/reversing/finalfight/lua/dumprom.lua` (reproduced byte for byte this session).
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). `ffightuc.zip` is a copy of
  `~/Downloads/ffightub.zip`, which is misnamed (its CRCs are the `ffightuc` program ROMs). The ROM zips
  are not committed.
- Start from: a cold MAME boot; `callcap.lua` warms up 600 frames itself. There are no saved states
  yet.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` also carries another
  session's unrelated line-rewrap in the working tree; only the `final_fight.md` row is staged.

## Proven so far

Detail in `reversing/finalfight/README.md`.

- The set boots headless: `mame -verifyroms ffightuc` good; `-debug -debugger none -video none` runs
  about 18x real time with the Lua debugger available.
- `tools/disassemble.py --rom ff_main.bin --base 0` decodes the CPS1 ROM; reset code at `$5e88c`
  programs CPS-A (`$800100..$80010e`). Whole-listing and unknown-opcode coverage were not measured.
- `lua/callcap.lua` on `$50e`: 32/32 words of `$4453` written at `$908500` stride 4, `D0=$4453`,
  `D7=$ffff`, `A0=$908580`, no other change; negative control (`142(A5)=1`) empty diff
  (`lua/specs/validate_50e*.lua`). One routine, run once each; no determinism rerun yet.

## Open, in priority order

1. **Read `cps1.cpp` from source** (`curl -s
   https://raw.githubusercontent.com/mamedev/mame/mame0289/src/mame/capcom/cps1.cpp`): the CPS-B
   register ids and layer/palette layout for `ffight`, the `$800000` input and DSW layout, the gfx
   decode layouts and the `ff-32m.8h` bank. The memory map in the README is a web-summary paraphrase
   checked only against the reset code. Unblocks inputs, graphics and every address in the docs.
2. **Drive the game into play.** Coin and start through MAME's ioport (Lua `manager.machine.ioport`) or
   `-record`/`-playback` (both exist in 0.289; unused so far), and save states with `-state`. Until a
   level is on screen nothing about enemies or items can be censused. Prove "it works" by a counter
   that only moves when the input is read (see the CLAUDE.md input rules).
3. **Prove the task kernel.** Inferred from code only: 16 task control blocks of 16 bytes at `$ff1000`
   (state byte 1 counts down to 4 in the VBL handler `$53e`; saved SR/PC/USP at `+2/+4/+8`), `trap #4`
   and `#5` (vectors 36/37 at `$90`/`$94`, handlers not read) and the scheduler `$7f0-$8c0`. Prove with
   a `watch` on the record states over a level and callcap of the trap handlers. A routine that
   yields needs a harness extension: the sentinel is reached in another task's context.
4. **The entity/object pool the tasks drive**, the AI, hit boxes, weapons and scoring: census, then
   find the game's own reader of each field before naming it (CLAUDE.md census rules apply
   unchanged).
5. **Graphics**: the four 512 KB gfx ROMs interleave at offsets 0/2/4/6 per `-listxml`; decode, render a
   sheet, commit the PNG with the proving doc.
6. **Z80 sound CPU** (`ff_z80.bin`, YM2151, OKI) and then Ghouls'n Ghosts: test the hypothesis that
   Capcom's object/sprite engine is shared (unchecked; only worth it after items 3 and 4).

## Known traps

- A ROM zip's file name does not say which MAME set it is. Find the set by CRC: `mame -listxml |
  awk '/<machine name=/{m=$0} /crc="<crc>"/{print m}'`, then rename the copy. Parent and clone zips
  must both be present for a split set.
- `PC` reads 2 above the breakpoint address while stopped; use `CURPC`. The stack pointer is `SP`.
  Setting registers while the CPU free-runs does not take; stop it first (`callcap.lua` stops at the
  VBL entry `$53e`). There is no `emu.register_pause`: use `emu.add_machine_pause_notifier`.
- `register_periodic` keeps firing while the CPU is stopped on a breakpoint, so a stopped CPU is
  detected by `dbg.execution_state == "stop"`.
- `-video none` needs `-seconds_to_run` (`ffmame.sh` sets 120): a run that never calls
  `manager.machine:exit()` ends by the clock, with no output.
- A web-fetch summary of a source file is a paraphrase from a small model (the `cps1.cpp` one dropped
  the CPS-B section it was asked for). Use `curl` on the raw file for anything an address or id depends on.
- The Bash tool's cwd drifts: the first ROM dump landed in `M68000/` instead of the scratchpad
  (CLAUDE.md "Shell pitfalls"); `ffmame.sh` now `cd`s into `scratchpad/finalfight/run` itself.

## Next session

Run `/resume final_fight`. Fetch `cps1.cpp` with `curl` and replace the README's hardware section with
what the source says. Then get coin/start working in MAME's ioport (or `-record`) and save a state at
the first stage; census the task table over a stage with `watch`. Do not start the graphics decode or
Ghouls'n Ghosts before the task kernel is proven.

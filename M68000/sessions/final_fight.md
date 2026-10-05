# Final Fight (Capcom CPS1 arcade, MAME): handoff

Updated 2026-10-05 by the session that ended at commit `7f23b50` (plus the handoff commit).

## Resume point

- Last commit of this workstream: `7f23b50` finalfight: health, lives, hit/hurt boxes and the damage chain
  proved live; object pools by tag; `$5668`'s callees named; second saved state `ff_enemies`.
- Workspace: `M68000/reversing/finalfight/` (`README.md` incl. the script index, `hardware.md`, `kernel.md`,
  `frame.md`, `ioport.txt`, `ffmame.sh` for debugger/callcap runs, `ffrun.sh` for input-driven runs, `lua/`,
  `py/`). The emulator and oracle is **MAME 0.289** (`/usr/local/bin/mame`), not the F# core.
- Working data: `M68000/scratchpad/finalfight/` (gitignored, indexed in `scratchpad/ANCHORS.md`): `ff_main.bin`
  (sha256 `8535dd51...e6ec`), `ff_z80.bin`, `src/` (raw `cps1.cpp` etc.), `ff_gameplay.sta` and
  `ff_enemies.sta`, `run/` (MAME cfg/nvram/state, disposable logs), `verify/` (RAM dumps of both states).
  `p2/a/`, `p2/b/` hold the two agents' working copies and outputs (the promoted scripts are in
  `reversing/finalfight/`). Rebuild the dumps, states and logs with the recipes in `README.md` and
  `ANCHORS.md`.
- ROMs: `~/mame-roms/{ffight,ffightuc}.zip` (`$FF_ROMS` overrides). Not committed.
- Start from: `ff_gameplay` (stage 1, Cody, Bred, end of frame 2200) or `ff_enemies` (frame 4150, five enemies).
  Copy the `.sta` into `scratchpad/finalfight/run/sta/ffightuc/` and start with `FF_LOAD=<name>`.
- Uncommitted work left behind: none of this workstream. `sessions/README.md` carries another session's
  line-rewrap in the working tree; do not stage it.

## Proven so far

Detail in `reversing/finalfight/README.md`, `hardware.md`, `kernel.md`, `frame.md`.

- Hardware, drive to stage 1, input gating, task kernel and TIME: earlier passes, `README.md`, `kernel.md`,
  `frame.md` "TIME".
- Health is the word at `+24` of a fighter record (`+26` shadow, `+28` max), read by the HUD tile bar `$1eca`
  and by the state handlers: the decoded bar equals `+24` in 1100 of 1100 frames, a write tap on Cody's `+24`
  shows 8 of 8 writes from `$7a12` (`py/hpcheck.py`, `lua/hpbar.lua`, `lua/tap.lua`; rerun fresh).
- Lives are `+128` BCD (HUD draws `+128 - 1`); the death countdown `$a5ee` decrements it; poked 5 to 4 with the
  refill and HUD redraw, 1 of 1 (`lua/poke_hp.lua`). Score is `+134` (`$ff85ee`), the attack-box centre x of
  Cody is `$ff85dc` (`+116`).
- Hit and hurt boxes are rebuilt by `$32c4` from `56(A6)`, `44`, `45`, `46`, `97`: 1100/1100 for the pointers,
  545/545 and 1100/1100 for the hurt centres (`py/boxcheck.py`, `lua/recdump.lua`). The overlap test `$7932`
  predicted 818/818 y-word writes and 63/63 outcomes (44 overlaps, 19 misses; `py/hitcheck.py`, `lua/htap.lua`).
- Damage: a per-pool dispatch (`$70ae`, `$7584`), amount = `byte[92(.) + 8(attack box)]`, scaled by `+55` through
  `$79d8`: 26/26 hits; Bred on Cody 8/8.
- The objects are tagged pools with their own bases, not one 60-record array (`frame.md` "The object pools");
  `$5668`'s thirteen callees are named from their bodies and each ran 60 of 60 frames (`lua/hitcount.lua`).
- The stage spawn script `$5aea`/`$61a8` is moved by the camera: pointer `$70676` to `$70684` at camera x
  `$3f0`, a tag-2 record 94 frames later, 1 of 1 (`lua/spawnlog.lua`).
- `ff_enemies`: five fighters named from the HUD's own text (BRED, DUG, JAKE, HOLLY WOOD; AXL inferred) with their
  data pointers at `92(A6)`; work RAM `2657a253...b0ae` and gfx RAM `1a4357c4...e94a` identical over three
  cold boots (`lua/plans/plan3.lua`, `py/poolcensus.py`). The extended `ffdrive.lua` still gives the original
  `ff_gameplay` hashes (`79ed3cc1...0b2c`, `d6fbca5f...d8b0`).

## Open, in priority order

1. **Fill the pools stage 1 never filled**: tags 4, 6, `$12`, `$14`, pool 8 and the `$ffb228` slot (and name the
   three unnamed tag-`$a` props, confirm AXL by `$5b4aa`'s name selection or a clean HUD frame). Drive past the first
   boss or into stage 2 (extend `plans/plan3.lua`; watch the stage counter `190/191(A5)`), save a state, rerun
   `py/poolcensus.py` and `py/hitcheck.py`. Needs a determinism check as for `ff_enemies`.
2. **Read the unread handlers**: `$6026` and tables `$604a`, `$61e24`/`$6241e`, `$27fc4`, the player-versus-player
   path `$7766-$7920` and `$2934`, the kind handlers `$73b8`, `$73e4`, `$7456`, `$711a`, `$71a2`, `$7222-$7232`, the
   continue screen (state 6 `$c840`, `22188(A5)`). Method as in `frame.md`: read to the first branch, grep the
   docs, write-tap the field, histogram writer PCs.
3. **The `$15854` bar object versus the `$1eca` tile bar**: both read `+24`; find out which one draws what you
   see (a sprite-layer test or a tile-layer test on the screenshot).
4. **The sound queue**: slot 11's queues (`516(A5)`, `324(A5)`, `$1a22`), the `jsr $2874` senders and the cue ring
   at `388(A5)` (`$9d0`/`$9b2` write `$800180`): tap `$800180`/`$800188`, match to queue entries, then read the Z80.
5. **Confirm the `[I]` task roles** (slots 7, 8, 12, 5, 6; `kernel.md`); needs an input script that loses all lives
   (the lives poke in `lua/poke_hp.lua` shows how to reach state 6).
6. **Graphics**: decode one known tile, render a sheet, commit the PNG with the doc. Then the Z80 and Ghouls'n
   Ghosts (test whether Capcom's object engine is shared) only after items 1 and 2.

## Known traps

- A web-fetch summary of a source file is a paraphrase from a small model: the earlier `cps1.cpp` summary
  gave the wrong CPS-B row and called `ff-32m.8h` a bank ROM. Use `curl` on the raw file
  (`scratchpad/finalfight/src/`).
- A ROM zip's file name does not say which MAME set it is. Find the set by CRC: `mame -listxml |
  awk '/<machine name=/{m=$0} /crc="<crc>"/{print m}'`, then rename the copy.
- MAME on macOS grabs focus even with `-video none` unless `SDL_VIDEODRIVER=dummy` is set; both wrappers
  now export it. Never launch `mame` directly from a Bash call.
- Two MAME runs at once collide on `scratchpad/finalfight/run/` (cfg, nvram, states): give each agent a copy of the
  wrapper with its own `run=` directory (`p2/a/ffrun_a.sh`) and a copy of the `.sta` in its own `sta/ffightuc/`.
- Lua `install_write_tap` returns a handle; if it is not held in a global, a garbage collection removes the
  tap silently. Tap ranges must be word-aligned (`ff807e-ff807f`). `screen:vpos()` does not exist in 0.289: use
  `machine.time:as_double()` with `screen.frame_period` and `scan_period`. A tap callback that errors prints `LUA
  ERROR`; wrap in `pcall` while debugging.
- In `callcap.lua`: `PC` reads 2 above the breakpoint while stopped, use `CURPC`; the stack pointer is
  `SP`; registers set while the CPU free-runs do not take; `register_periodic` keeps firing while stopped.
  `lua/hitcount.lua` (breakpoint `printf; g`) counts executions without that stop-and-set dance.
- `-video none` needs `-seconds_to_run` and a script that calls `manager.machine:exit()`.
- Inputs are levels read once per frame: hold several frames; a level set at the end of frame N is seen
  from N+1. Test movement only after frame ~1700. Cody has no attack box in the grapple states, so offence checks
  need a run where he hits something that is not holding him.
- `ffdrive.lua` silently skips `FF_TRACE` dumps if `<FF_OUT>/tmp` does not exist (`ffrun.sh` creates it). With
  `FF_LOAD` the plan and the base schedule are now both applied (`L.apply` is unconditional), which is harmless
  because the base schedule ends at frame 2195.
- Pool-local indices and array indices differ: Bred is array index 14, pool-2 local index 12 (`py/poolcensus.py`
  prints local).
- `py/jt.py` takes the address of the `move.w 6(PC,Dn.w),D1` instruction (`70a6`), not the routine start (`708e`):
  the wrong address decodes garbage without an error.
- System `python3` has no numpy: use `M68000/.venv/bin/python` for `analyze_inputs.py`; `py/hudbar.py` and
  `py/namesheet.py` need Pillow (same venv).
- A task's variable (`$ff1288`) keeps its last value after the task dies: read the TCB state before saying
  a task "is in state N".
- zsh does not word-split `$D`: use a shell function for repeated `disassemble.py` arguments.

## Next session

Run `/resume final_fight`. Item 1: drive past the first boss from `ff_enemies` (or stage 2) and census the pools
that stayed empty, then item 2 on whatever the new state exercises. Two agents fit again: one for the drive and
census, one for the unread handlers (`$6026`/`$61e24`/`$27fc4` and the player-versus-player path). Give each its own
MAME run directory. Do not start graphics or Ghouls'n Ghosts before items 1 and 2.

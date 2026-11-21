# Starglider: handoff

Updated 2026-11-21 by the second Starglider session (curios pass, started at `b8c2235`).

## Resume point

- Last commit of this workstream: `3032b7c` starglider: curios.
- Uncommitted work left behind: none.
- Working data: `M68000/scratchpad/starglider/` (`ANCHORS.md` row; rebuild: README "Running it": `tools/msa2st.py`,
  `tools/extract_disk.py`, then `bash reversing/starglider/drive.sh`, about 50 s, deterministic 5/5 by `cmp`).
  Whole-image listing `scratchpad/starglider/sg.asm` (`disassemble.py --snap drive/g_game1.snap --all ab8c 56264`).
  Curios renders: `scratchpad/starglider/curios/out/`.
- Start from: `scratchpad/starglider/drive/g_game1.snap` (level 1, in flight just after launch); `g_title.snap` for
  the title keys.
- Agent working dirs from the first pass: `scratchpad/starglider/agents/<area>/report.md`.

## Proven so far

- Flight, IKBD, keys, energy, laser, messages, define keys: `flight.md`, `py/flight/`.
- Renderer to the whole frame 49,368/49,368 and all 28 models 84/84: `graphics.md`, `py/render/`.
- Objects, AI, collision, laser, RNGs, level init, names: `objects.md`, `py/objects/`.
- `.TRA` format 64,000/64,000, HUD: `frontend.md`, `py/frontend/`.
- Curios (`py/curios/`, README table there):
  - levels are 1 + score/10,000 to 34 and each step reloads the pool (`objects.md` 5, `level_from_score.py`);
  - the 16-entry shield table `$159aa` overruns: levels 16 to 30 cost 0, 31 reads vector memory, 32+ bus-errors
    (`objects.md` 4, `shield_level.py`, `shield_crash.py`, `level_from_score.py 8 --crash`);
  - the rating is level × accuracy, CHEAT!?! is the top grade, a no-shot game reuses a stale accuracy
    (`frontend.md` 4, `rating_stale.py`);
  - G in practice mode is a developer model viewer with its own key table `$e944` (`frontend.md` 4,
    `gallery_keys.py`);
  - dead stereo page flip `$ac70` and debug keys `$d3f8..$d41a` (`graphics.md` 8; the shutter-glasses reading is
    inferred).
- All 16 gates: `uv run python tools/gates.py run starglider`, 16/16 PASS at `3032b7c`; dry run 0 MISSING,
  0/16 declare no inputs.

## Running

Nothing running.

## Open, in priority order

1. **Play a level through.** Write a bot over `py/flight/fly.py` that flies to the silos and towers and shoots, so
   that levels 2 to 4 are reached by kills and a game over comes naturally. Levels are score bands, so the bot only
   has to score; check whether the near-clip overflow or the endless window clip shows in play.
2. **The level-32 crash on real hardware.** TOS drew 3 bombs (vector 2, bus error) in this emulator; check that
   count and what the ST returns at `$2c012c` (the level 16 to 30 pointer) in Hatari with `level_from_score.py 8
   --crash`'s inputs (`frontend.md` Open).
3. **The scanner and gunsight.** Model the second view (`618..628(A6)`, window `672..`) and the sprite blit
   `$143ce`, then score a whole frame including the gunsight box (`graphics.md` section 1).
4. **List builders as their own gate.** `$101a8`'s docked and launch branches and `$10344`'s list order are gated
   only inside the object gates.
5. **Sound.** Decode the effect table `$c3e0`/`$adb4`; check the sample WAVs against Hatari (`frontend.md` 3).
6. **Smaller items.** The `.TRA` permutation table `$156c4`, name entry `$ba2a/$ba92`, type 3's role, what `701`
   is for (set by `$10070`, `graphics.md` 4).

## Known traps

- `tools/lsd_depack.py`'s Ice path fails on Starglider's streams; `py/frontend/ice_depack.py` is the working
  transcription (`frontend.md` section 1). The tool is shared, so it is not changed here.
- `sg.asm` loses sync in data areas between routines (`$e944`'s key table read as code): disassemble the range
  directly with `disassemble.py --snap ... --all lo hi` before reading a table out of it.
- A raw scan for callers missed the level-up path to `$1523a`, which runs through flag `727` at `$cabc`; prove
  "never reloads" or "no caller" with a live `until` after the transition.
- Agent reports disagreed on table roles twice (`$d748/$d790/$d7d8`, `472(A6)`); check table claims against RAM.
- Render gates that take a snapshot argument resolve it from `M68000/` (the REPL's cwd).
- `$f23e` mixes the caller's leftover D0 into its state, so a model of a multi-object pass must carry D0 history.

## Waiting on Dave

- Whether to fix `tools/lsd_depack.py`'s Ice path from `py/frontend/ice_depack.py` (shared tool).
- A push: master is ahead of origin.

## Next session

`/resume starglider`. Rebuild the snapshots with `drive.sh` if the scratchpad was cleared. Run
`uv run python tools/gates.py run starglider`. Then open item 1 (the bot) or, for a quick win, item 2 in Hatari.

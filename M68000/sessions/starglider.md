# Starglider: handoff

Updated 2026-11-21 by the first Starglider session (started at `54efe30`).

## Resume point

- Last commit of this workstream: `cdb0451` starglider: first pass (with `f5bedf6`, the `tools/extract_disk.py`
  FAT-overrun fix it needed).
- Uncommitted work left behind: none.
- Working data: `M68000/scratchpad/starglider/` (`ANCHORS.md` row; rebuild: README "Running it": `tools/msa2st.py`,
  `tools/extract_disk.py`, then `bash reversing/starglider/drive.sh`, about 50 s, deterministic 5/5 by `cmp`).
  Whole-image listing `scratchpad/starglider/sg.asm` (`disassemble.py --snap drive/g_game1.snap --all ab8c 56264`).
- Start from: `scratchpad/starglider/drive/g_game1.snap` (level 1, in flight just after launch); `g_title.snap` for
  the title keys.
- Agent working dirs (reports, probes, sym blocks): `scratchpad/starglider/agents/<area>/report.md`.

## Proven so far

- Flight step `$12340` 400/400, IKBD handler 30/30, key commands 400/400, energy/shield/refuel/death, laser 7/7,
  messages 7/7, define keys 6/6: `flight.md`, `py/flight/`.
- Renderer: matrices and transforms 40/40 each, Bresenham and both clips 150-301/301, object draw 30/30 natural and
  84/84 over all 28 models, whole frame 49,368/49,368 viewport bytes outside the gunsight on `g_game1` and `g_game2`:
  `graphics.md`, `py/render/`.
- Objects: AI pass 750/750 poked plus 11/11 natural, collision 600/600, laser 600/600, projection 200/200, near list
  40/40, impact 30/30, both RNGs 200/200, level init 5/5, database names 17/17: `objects.md`, `py/objects/`.
- `.TRA` picture format 64,000/64,000 pixels; HUD poke diffs: `frontend.md`, `py/frontend/`.
- All 16 gates: `uv run python tools/gates.py run starglider -j 4`, 16/16 PASS on DLL `b17b5ad14363aba6` at
  `cdb0451` (about a minute); 0 MISSING, 0/16 declare no inputs.

## Running

Nothing running.

## Open, in priority order

1. **Play a level through.** Write a bot over `py/flight/fly.py` that flies to the silos and towers and shoots, to
   reach levels 2 to 4 naturally and a natural game over. This tests whether the near-clip overflow or the endless
   window clip ever shows. The level lists are already decoded (`objects.md` section 5).
2. **The scanner and gunsight.** Model the second view (`618..628(A6)`, window `672..`) and the sprite blit `$143ce`,
   then score a whole frame including the gunsight box (`graphics.md` section 1).
3. **List builders as their own gate.** `$101a8`'s docked and launch branches and `$10344`'s list order are gated
   only inside the object gates; the frame gate reads the lists from RAM.
4. **Sound.** Decode the synthesised effect table `$c3e0`/`$adb4`; check the sample WAVs against Hatari
   (`frontend.md` section 3).
5. **The `.TRA` permutation table** (`$156c4`), Esc `$eb7e`, name entry `$ba2a/$ba92`, type 3's role and the
   fourth level-list word for type 3.

## Known traps

- `tools/lsd_depack.py`'s Ice path fails on Starglider's streams; `py/frontend/ice_depack.py` is the working
  transcription (`frontend.md` section 1). The tool is shared, so it is not changed here.
- Agent reports disagreed on table roles twice (`$d748/$d790/$d7d8`, `472(A6)` read as a size); both were settled by
  dumping the table. Check a report's table and count claims against RAM before they reach a doc.
- Render gates that take a snapshot argument resolve it from `M68000/` (the REPL's cwd), not from `py/render/`.
- `$f23e` mixes the caller's leftover D0 into its state, so a model of a multi-object pass must carry D0 history.

## Waiting on Dave

- Whether to fix `tools/lsd_depack.py`'s Ice path from `py/frontend/ice_depack.py` (a shared tool; `frontend.md`
  section 1 has the corrected tables).
- A push: master is ahead of origin (see the handoff report).

## Next session

`/resume starglider`. Rebuild the snapshots with `drive.sh` if the scratchpad was cleared. Run
`uv run python tools/gates.py run starglider`. Then start open item 1: a flying bot on `fly.py`.

# Impossamole: handoff

Updated 2026-09-26 by the session that ended at commit `681d8bb`.

## Resume point

- Last commit of this workstream: `681d8bb` (debunks the VBL-stuck theory, reaches world-select).
- Working data: `M68000/scratchpad/impossamole/` (gitignored) — the extracted `.ST` image, an
  `extracted/` directory (root-dir files pulled via a one-off FAT12 reader), and the snapshot chain
  `after_f1.snap` → `after_space.snap` → `after_retry{1,2,3,4}.snap` (title screen) →
  `after_fire1.snap`/`after_fire2.snap` (world-select screen reached) → `after_select{1,2,3}.snap`
  (Klondike Mine icon highlighted) → `after_load1.snap` (5M idle steps past `after_select3`, still on
  the select screen — confirms the highlight is not itself "enter the level").
- Start from: `scratchpad/impossamole/after_select3.snap` (world-select screen, Klondike Mine
  highlighted, PC in the shared object-update loop at `$1ac3e`/idles back into the VBL-wait at
  `$1ab8a`). **Must be resumed with `--disk-a "impossamole cr replicants - emotion cr replicants.st"`
  or every floppy read silently fails** (see README's "Known traps").
- Uncommitted work left behind: none beyond the scratchpad snapshots (gitignored, reproducible from
  the README's exact command sequence, repeated below).

## Proven so far

See `reversing/impossamole/README.md` for the full writeup and screenshots
(`trainer_menu.png`, `title_logo.png`, `world_select.png`).

- Disk boot → crack menu (F1) → trainer skip (any key) → real title screen: unchanged from the
  previous handoff, still holds.
- **The title screen's "stuck at `$1a2e9`" theory from the prior handoff was wrong, and is now
  corrected in the README with live proof**: `$1a2e9` is a genuine per-frame VBL counter (sole
  writer `$1a2c0` inside the installed VBL handler, `find_field_writers.py`: 31 hits), firing
  correctly (`hits 500000 1a2c0 1f950`: 42 hits ≈ 500000/12000, once a frame) and immediately
  consumed/cleared by its own caller's wait-for-next-vbl utility (`watch 1a2e9`: set to 1 at step
  59808001, cleared at step 59808234, 233 steps later). Two static snapshots agreeing on `= 0` is the
  expected signature of an idle busy-poll, not a hang — see the new CLAUDE.md rule this cost.
- **The real gate is a joystick-1 fire packet.** The attract loop's `btst #7,$1c4c1.l` (5 identical
  copies) waits on `$1c4c1`, written only by the game's own raw-IKBD ACIA-receive handler (`$1c51a`,
  vector `$118`) on header `$FF` (joystick 1). Proven live: `kbd ff` / `s 30` / `kbd 80` sets
  `$1c4c1 = $80` and moves PC out of the attract loop within one frame.
- **World-select screen reached and screenshotted** (`world_select.png`): IMPOSSAMOLE logo, 5 world
  icons (Klondike Mine / The Orient / The Amazon / Ice Land / Bermuda Triangle), walking hero cursor.
  A second fire (press+release, `kbd ff`/`kbd 80` then `kbd ff`/`kbd 00`) drew a gold highlight
  border around the Klondike Mine icon the cursor stood on — the same joystick-1 packet drives the
  select screen's own input too.

## Open, in priority order

1. **Find the "confirm and load a world" input.** From `after_select3.snap` (Klondike Mine already
   highlighted), repeating the same fire packet did not visibly proceed within another 5M idle steps
   (`after_load1.snap`, still on the select screen). Try: a direction packet before/after fire (the
   cursor sprite visibly walked between `after_fire2`/`after_select1`, so movement packets are being
   read — `find_field_writers.py` on `$1c4c0`, joystick-0's slot, may be the one actually driving
   movement, with `$1c4c1`/joystick-1 only for fire); a keyboard key (GEMDOS-style, like the
   trainer-menu skip) in case selection needs Return/Space once a world is highlighted; or find the
   select-screen's own input-check code directly (`bt` from a snapshot sitting in its main loop, or
   `find_ram_callers.py` on `$1ab8a`/`$1abb2`'s other 4-5 caller sites, one of which is this screen's
   loop body, not just the 5 attract-mode copies already identified in the README).
2. Once a world loads: reach actual isometric gameplay for one of the 5 worlds.
3. Classify the main game binary once reached via GEMDOS `Pexec` (watch for the trace line) — likely
   hand-written 68000 asm given the crack/trainer wrapper, but confirm via the LINK-frame-count
   heuristic (§0 of the reversing skill) rather than assuming.

## Known traps

- `resume <snap> repl` does not reattach a disk image — `--disk-a` must be passed again on every
  resume for a disk-booted game, or floppy reads silently return "no data" (looks exactly like a
  real protection/geometry failure). Now in `reversing/impossamole/README.md`'s "Known traps".
- A busy-poll "wait for next interrupt and consume it" utility reads as stuck if you only sample the
  field it polls at rest — see "Proven so far" above and the new CLAUDE.md rule. Also now in the
  README.

## Next session

Start at `scratchpad/impossamole/after_select3.snap` (`--disk-a` attached). Do not burn raw step
budget guessing — first identify the select screen's own input-check code (`bt`/`find_ram_callers.py`
per Open item 1) so the "confirm world" gesture is found by reading, not by trying random packets for
millions of steps. Once a world loads, take a screenshot before going further so the milestone ladder
(title → select → world load → gameplay) has proof at each rung.

# Super Sprint: handoff

Updated 2026-09-30 by the session that ended at commit `bbe86c9`.

## Resume point

- Last commit of this workstream: `bbe86c9` supersprint: topic docs (mechanics, tracks, graphics, sound, secrets), 65-name sym, proof scripts, asset PNGs.
- Working data: `M68000/scratchpad/supersprint/` (game files, `ss.img`, `ss.c` decompile, `ss.asm`, snapshots, each area's scratch under `agents/<area>/`).
  Rebuild recipe: `reversing/supersprint/py/README.md`, "Rebuild the work directory" (about 3 minutes plus the two snapshot runs).
  The Mac source of the game is `~/Library/CloudStorage/Dropbox/Daves/ST games/Super Sprint.zip` (sha256 in the README).
- Start from: `scratchpad/supersprint/ss_prep.snap` (a live Track-1 race just started, one joystick player joined; `sscfg.SNAP_RACE`). Others:
  `ss_attract.snap`, `ss_select.snap`, `ss_race0.snap` (winner's circle), `agents/tracks/snaps/race_0..7.snap` (each track).
- Uncommitted work left behind: none from this workstream. (`M68000/sessions/README.md` also carries another session's line re-wrap; only the
  `supersprint.md` row is committed.)

## Proven so far

Detail and scripts in `reversing/supersprint/{mechanics,tracks,graphics,sound,secrets}.md` (each ends with a proof table) and `py/README.md`.

- The program is compiled C; Ghidra decompiles 288 functions (`README.md`, "Decompile").
- Car model reproduced exactly: 700/700 frames, 35 fields x 4 cars (`py/physics/test_trajectory.py 700 3`); `$df18`, human and drone control, `$bda4`,
  `$b798`, the collision window, car-car and depth sort each differential-tested (`test_df18.py`, `test_ctl.py`, `test_samplers.py`).
- Drone AI: 8-byte waypoint records with a fork/gate/jump control language, rails, 576/576 (`py/ai_econ/drone_diff.py`), 9 of 9 lap times exact.
- No rubber-banding in a race: caps are written once per race from track, race counter, slot and upgrades (live watch, 7 writes in the first ~1300 steps,
  none after; A/B with the human idle vs crashing, 4667 samples bit-identical for two drones). The cross-race catch-up is the race counter `-1748(A4)`.
- Winner's circle ranking and elimination 46/46 (`winner_diff.py 40 6`); upgrade formulas 96/96; coast rules 60/60.
- All 8 tracks rebuilt from `SUPER.DAT`/`INIT.DAT` and equal the game's buffers (`py/tracks/prove_all.py`): 62080/62080 background, 64000/64000 per collision plane, 1000/1000 attribute map.
- Art and blitters: 20 routines differential-tested on whole screens (`py/engine/run_proofs.py`); tile pack format; word-RLE depacker.
- Sound: Timer D three-voice tracker, 7200/7200 ticks tick for tick; a missing `rts` at `$13308` doubles channel C's envelope.
- Secrets: none. One hidden hook (F5 on the winner's circle, `py/secrets/f5_winner.py`), F8/F10/ESC conveniences, dead code (keypad tuner `$e74a`, `BOOT.DAT` check `$101d2`,
  `$f1dc`, `$155ce`), an unused 59.5 s tune, an unshown credits text in `SUPER1.DAT`, a Track 8 stroke that writes past the attribute map.

## Open, in priority order

1. **The prepare-screen / race-start fragility** (unblocks reliable driving, and may be an emulator bug). In `agents/secrets/snap/prep_kbd.snap` a held make of almost any key (116/117) or an
   ESC tap ends with the game dying in race-start init (Line-F exception through a wild jump, ROM bomb loop at `$fca8xx`); the last game function entered is `$f8d0`/`$f91e`
   (the Supexec raster uninstall). `drive_track.py 5` (Track 6, no player joined) also ends in a garbage PC. Make+break taps of the other keys are fine, so it looks like IKBD
   delivery phase, not a key function. Prove: run the same drive under real Hatari (`tools/hatari_trace.py`) as an oracle; log `$70`, the saved VBL vector at `$fa8c`, and the MFP
   registers around `Supexec($f956)`; bisect to the faulting PC. If it is an emulator bug, fix it behind the regression net (skill section 6).
2. **Live tests the docs list as inferred**: a human *leading* the pack (rubber-band test with the human in front), gate-closed routing on Tracks 3, 5, 8 (select cursors 4/5, 8/9, 14/15), the wrench
   increment, item 3 of the shop ("increase score level taken") having no consumer, the human-win increment of the race counter, and hazard-count distributions under differing RNG seeds. Each is
   a same-snapshot A/B with a match count; `py/ai_econ/` has the harness.
3. **Collision on Tracks 2-8**: only rendering is proved for them. Run the `py/physics/test_trajectory.py` model against live play on each track (needs `drive_track.py` snapshots with a player joined).
4. **Unused content**: render the seven never-consumed `SUPER.DAT` blocks (28,672 bytes) and the `SUPER1.DAT` tail cells; 1 KB poison on them; decode the unused 59.5 s tune (script 906) via
   `py/engine/sound_model.py`, or add Timer D delivery to the emulator so the game is audible (an emulator change: regression net, and message live sessions before building).
5. **Residual decode**: collision plane 2's record format (`py/physics/rebuild_planes02.py` unfinished, 7583 pixels), the lap-panel composition `$158ea` (1627 differing HUD pixels), the 150-byte B2 header,
   the tripwire strips' consumer (`-3842`), `$1000e`/`$101bc` and the `-150/-148` campaign-end flags, the race-end control phase (`$13bbe`, `$afc6` not ported).
6. **Doc tidy**: the README's "What it needed from the emulator" and pass-numbered sections are history; fold them into normal prose when next touched.

## Known traps

- `$15080` is a code address inside the flood-fill routine, not a collision map (the old README said so); the collision planes are at `$61436`, and `-3682(A4)` is a 48-byte window, not a pointer.
- The emulator never raises Timer D: the game is silent and any sound proof needs the tick injection in `py/engine/psg_capture.py`.
- Re-driving the same input from a snapshot is deterministic, but two separate cold-boot drives of the same track differed in 634 of 1 MB bytes (`agents/tracks/snaps`): compare behaviour, not snapshot bytes, across re-drives.
- `ss_attract.snap` takes about 75 s (0.5M steps/s); a race plus results is about 20M steps; a same-snapshot scancode scan is 2-3 minutes per screen on 6 cores. Budget long audits (the `secrets` agent ran two hours).
- Every area's scripts write scratch under `scratchpad/supersprint/agents/<area>/`; promoted scripts derive paths from `sscfg.py`. A script that hard-codes `agents/<area>/py` fails after promotion.
- Slot labels: 0 blue (keyboard), 1 red (joystick 0), 2 yellow (joystick 1), 3 green and always a drone (colour names read from sprites).
- Agent reports are in `scratchpad/supersprint/agents/<area>/report.md` (untracked); their contradiction lists are already folded into the docs.

## Next session

Start with open item 1: resume `agents/secrets/snap/prep_kbd.snap`, reproduce the crash with a held key, and find out whether Hatari survives the same input. If it is an emulator bug, fix it; if it
is the game's, document it in `secrets.md`. Then take item 2 (the live rubber-band test with the human leading), which closes the last claim in the headline finding. The prompt that starts it is `/resume supersprint`.

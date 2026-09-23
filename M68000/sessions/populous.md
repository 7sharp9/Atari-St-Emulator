# Populous: handoff

Updated 2026-09-23 by the session that ended with the handoff commit after `28bdff3`.

## Resume point

- Last commits of this workstream: `1459935` (mouse UI driver), `8c274d4` (walker, powers),
  `68c60cf` (AI in play, endgame), `e3e6996` (`systems.md`), `5c32af8` (emulator: IKBD absolute
  mode, Pexec basepage), `28bdff3` (brief rules, `tools/merge_sym.py`).
- **`bin/Debug/net8.0/M68000.dll` may be older than `5c32af8`.** A leftover dotnet process held it
  when the session ended, so the fix was verified on a scratch build only. Before relying on mouse
  input: `ListAgents`, then `dotnet build -c Debug M68000.fsproj` if nobody holds the DLL, then
  `python reversing/populous/py/verify_drive.py` (17/17).
- Working data: `$POP_WORK` = `M68000/scratchpad/pop/` (rebuild: `reversing/populous/README.md`,
  "Drive recipe" and "Working data"). Per-area data under `$POP_WORK/<area>/`; the agents' raw
  output from pass 2 is kept in `$POP_WORK/agents/`.
- Start from: `drive/A.snap` (GENESIS, view on your town) for UI work; `ai/cg1.snap` for a hard
  opponent; `systems/spawn.snap` for the trail monsters. All listed in `scratchpad/ANCHORS.md`.
- Uncommitted work left behind: none.

## Proven so far

Five topic docs (`reversing/populous/README.md` has the table with every count):

- Graphics: the frame rebuilt from RAM, 64000/64000 pixels on 12 frames; the mouse UI (panel,
  minimap, land cursor) decoded and driven, `py/verify_drive.py` 17/17.
- Terrain: world generator byte-identical for 3 worlds; raise/lower; all six powers 2305/2305
  under `callcap` and 8/8 casts through the UI; next world, world names, start paths, starting
  walkers (65/65, 45/45, 35/35, 28/28).
- Mechanics: settlements, mana, spawns, combat; walker direction choice 2400/2400 and 8000/8000
  live decisions in gather and fight; knight 154/154 live calls; score screen 200/200 and 56/56.
- AI: 4800/4800 decision routines; every command of a rating-1 all-powers opponent predicted in two
  natural runs (1854/1854, 2766/2766); walker land edits 2400/2400; ONE PLAYER ctrl bug confirmed.
- Systems: trail monsters 400/400 + 400/400 and 394/394 live frames; key checks pass on the crack;
  pause; LOLO1.GAM is a disk-full truncated save (reproduced); 12 sampled sound effects, no music.

## Open, in priority order

1. **The endgame powers cast by the computer.** Flood and armageddon were never cast live (mana
   never reached 42000 in 5660 frames). Poke evil's mana past 81000 in `ai/cg1.snap` (or run B
   longer) and prove the `$13a44` flood/armageddon branches live with `py/ai/livecheck.py`; then
   model the Armageddon brawl (magnets forced to (32,32), settlements emptied) against a frame
   capture, which also closes the natural Armageddon ending `mechanics.md` 6 reports.
2. **The population-208 swamp monster** (`$e89c`, `systems.md` 1.3): reach 208 live entities (a long
   ATARI VS ATARI run from `ai/cg2.snap`, or pokes) and diff the spawn; its edge comes from `$db4c`'s
   uninitialised local -146(A6), so record which edge it really takes.
3. **What the player sees of the trail monsters.** Dave identified the SPR_320 frames by eye (wizard
   with bubbles, slime, rock monster); confirm with a rendered game frame of the forced type-0 run
   (`py/systems/trailrun.py 220 0`) through `pop_render.py`, and finish the SPR_320 frame identities.
4. `$ef4c`'s post-decision writes (settle, merge, fight start, occupancy and visit counts) diff-tested
   on their own; a knight merging into a friendly walker live; the non-knight town take-over in
   `$108b8` (`$10366`).
5. Smaller loose ends: sounds 5/6 and the `$37e78` bits (`systems.md` 6); the command that sets
   `$3c4e4`; `$135fc`'s second call site `$e580` live; a full-size SAVE then LOAD round trip on a disk
   with space; PAINT MAP, RESTART/NEXT MAP items (code-read only).
6. Lowest: the serial two-player link (`$19652`, MFP 10/12, `$1d03e`, `$3d52c`) needs a second
   emulated machine; the LORD/MOUTHS speech needs side 1 of the original double-sided disk.

For the emulator workstream, not Populous: Timer A is a stub (64 interrupts per frame, ignores
TACR/TADR), so sampled sound plays at the wrong rate (`systems.md` 6.2).

## Known traps

- `py/repl.py`'s `Repl` loses sync after a `bp` (the breakpoint prints registers twice); use
  `py/powers/pwlib.Repl2`.
- In callcap memory compares, exclude `$37f5a..$37f89`: the trap wrappers' register save stack
  changes on every OS call.
- `callcap` masks interrupts: a routine that waits for the VBL (the earthquake's shake) must be
  tested in two halves (callcap from after the wait, `$12470`).
- A land click acts only when one of your entities is in view (`$3d54e`); a magnet click does not.
  The GENESIS human is on an island: contact with the enemy needs the bridging raises of
  `py/walker/campaign2.py`.
- `click.snap` is the CONQUEST click (y 176 is the CONQUEST band), not CUSTOM.
- Snapshots made before `5c32af8` came from a DLL that injected stray key presses on every
  `mouse move`; re-running their drives on the fixed DLL can differ in a few bytes (`$20021`,
  `$37eae`). Every committed count was re-checked, but regenerate rather than diff old vs new.
- A full AI live replay (`py/ai/livecheck.py` over 8 call sites) takes 1.5-2.5 hours with 9
  processes; `join.py` over the recorded logs in `$POP_WORK/ai/live/` takes minutes.

## Next session

Confirm `bin/` is built from `5c32af8` or later (see Resume point) and `verify_drive.py` gives 17/17.
Then item 1: from `ai/cg1.snap` with evil's mana poked above 81000, capture the flood and
armageddon casts through `livecheck.py`, and build the Armageddon-brawl model against a frame
capture. Prompt: `/resume populous`.

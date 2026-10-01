# Cadaver: handoff

Updated 2026-10-01 by the 89th-pass session (no subagents; level 1's arrival, health survey, first leg).

## Resume point

- Last work commit: `1a410ea` (`cadaver: 89th pass -- level 1 arrival driven ...`: `mechanics.md` §78, `exit_level0/l1/route_level1_first.py`, master stages `level1` and `room31`, `py/secrets/potion_amounts.py`, digest line). This handoff is the commit after.
- Read `reversing/cadaver/mechanics.md` §78 (every number below), then `py/secrets/overlay/action/exit_level0/README.md` (stage table).
- Rebuild or re-run the whole chain to level 1's room 31: `cd M68000 && export M68000_ROOT=$PWD ATARI_NOTRACE=1 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/exit_level0/route_level0_exit.py <outdir> --upto=room31` (about 250 s, no injection). `--upto=level1` stops at the arrival (`level1/level1_room0.snap`).
- Working data: `scratchpad/cadaver/s89/full_A/` and `full_B/` are two whole-chain runs (453 snapshots each, `cmp`-identical); `lc/level1_room0.snap` is the level-1 arrival; `l1c/` the first leg alone; `r29/` the room 29 exploration scripts and snapshots (`jump_20`, `took556`, `drank556`); indexed in `scratchpad/ANCHORS.md`.
- Start from: `full_A/room31/end_room31.snap` (level 1, room 31 at (10,20,4,14), health 60 of 200, XP 980, rucksack empty).
- No emulator source changed: no build or regression run needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in the docs)

Passes 77-88: main-loop keys, saves, rank table, assert layer, overlay, 94-verb grammar, sound sequencer, action panel, and the whole level-0 road by natural input, treasury to room 60 (§72-§77, `exit_level0/`).

89th pass (§78):
- **Level change in the real chain:** arrival at level 1 room 0 with health 20 of 200, XP 980, empty rucksack (`--upto=level1`, 7 s; the 88th pass's "inferred" is now driven).
- **Every open-door route out of room 0 goes through room 29** (room 0 has one door, `$00`; 35 rooms reachable, `s86/a7/reach1.py`).
- **Healing placed in level 1** (`potion_amounts.py`): STAMINA 556 room 29 (+20, 2 doses, driven), 521 room 19 (+10, 5 doses, inferred), 475 room 84 (+25 x3), 219 room 6 and 535 room 65 (+100); 492 (room 24) has a zero block; room 96 holds templates and no door leads to it.
- **Room 29's damage = two static patches** 664 (x 64..71, y 16..23) and 665 (x 24..31, y 40..47), -15 per touch frame; the lane from the x 14..20 column (`U R U R`) costs 0.
- **STAMINA 556 on block 425:** one RIGHT+FIRE jump from the arrival, take, two doses: 20 -> 60, driven natural; room 31 reached at health 60 (`route_level1_first.py`, two whole-chain runs 453/453 identical).

## Open, in priority order

1. **Room 31's altar puzzle and the road to level 2** (§75, §78): altar 131, drape 130, skull 198 (z 56..62, event 9 GOMOVEs 130 and 131); 12 -> 90 -> item 731 -> room 17 -> door `$74`; room 87's six teleporters (it deletes weapons and magic items on entry); room 88's countdown (object 735 bit 0, START LEVEL 2); the lethal zones of room 34 (-10 a touch) and room 29. Start from `end_room31.snap` at health 60. First read what room 31's puzzle needs (its objects' event blocks in `secrets_out/scripts_level1.txt`, a placement dump with `s86/a7/survey_inj.py`-style output, labelled injected), then drive it. Proof: a natural script from room 0 to level 2's load, run twice.
2. **More health before the long road:** STAMINA 521 in room 19 (twelve doors on: 29, 28, 30, 2, 3, 13, 14, 15, 16, 18, 19; its doses and a possible creature trio 900-902 in the room are unmeasured), 475 in room 84, 219 in room 6, 535 in room 65 (rooms 6, 65, 84 not reachable by open doors; `a7/opener_rooms.txt` lists the openers). Measure what each room on the way costs at 60 before choosing; 492's zero block and what a drunk dose of 521 gives are open. Proof: drive one dose and read health.
3. **Phase risks in the level-0 chain** (only if re-planned): room 39's north lane has no lookahead, room 38 `up` has 45 of 214 unsolved phases, E1's `WQ` proceeds if no guard appears within 1.5M steps (§77).
4. **Unread or undriven in level 0:** key 110 with object 391 (door `$09`, rooms 40-41), rooms 41, 44, 54, 58, potion 450's effect, item 256 and scroll 27's missile, the extra bit READ MAGIC clears in 324, a cast's charge of 482, why room 27's guard never fired in D2's lineage, the room 52 spiders' respawn, FIRE SHIELD 12.
5. Carried over: events 17 by a natural mover, byte 23's other bits, the regions' z bounds, Disk 2 builds, verbs 56, 90, 44's class-bit-7 branch, 41's collision search, producers of events 1, 4, 10-13, 25, the jump's table, `$006f80`, depth-order loose ends (`graphics.md` §5k), older loose ends in `secrets.md` "Open".

## Known traps

- **A leg free in its own run is proven only for that lineage** (CLAUDE.md rule); run every segment from the previous segment's real end snapshot, then the whole chain twice.
- **Holds after a drop or a panel:** a hold started while the hero is still falling off a block never moves (settle 200,000 steps first); a rucksack panel left open (a Space after the last dose) freezes every hold: open it only for a dose that is drunk.
- **Probe presses FIRE:** repeated `probe` calls while walking can lift the hero (z glimpsed at (85,56)); walk with `goto` to the stand, probe once.
- **Column matters in room 29:** `U` from x 25..31 runs through patch 665, from the west wall (x 7..13) it passes block 561 and `R` then runs through 664; only x 14..20 gives the lane (`goto` Left to x trail <= 14).
- **Creature motion is a function of steps spent inside the room** (rooms 38, 39) and waiting is a move (room 15's patrol, room 53's item 459, room 36's fireballs, room 27's guard).
- **Return grid with six or more items:** the cursor `2122(A5)` names a different item than FIRE opens; search the pulse count and test `1236(A5)` (`find_n`).
- **`lib/drv.py` does `os.chdir(ROOT)` on import:** `os.path.abspath` every snapshot argument first; `from lib import *` clobbers `START` and `OUTDIR`; `type8(r)['recs']` keeps stale records past the count byte (use `[:count]`).
- **Hold timing and phase:** a hold starts moving ~40,000 steps after the press, then one cell per ~10,000; a stall detector needs six 20,000-step chunks; an exact cell needs `goto` with 5,000-step chunks; `Repl.__init__` runs `s 1`, so every route script snapshots, closes and reopens after each hold; after a room arrival wait ~100,000 steps. Do not tidy no-op tokens of a promoted script without two re-runs.
- **REPL `w <addr> <8 hex>` writes four bytes.** Earlier standing traps: injected-state results show a mechanism, not a route (label them); after `H.real()` reload before driving; health only goes up by a verb 45; touch hazards cost per frame; door words are hex door numbers; the REPL prints at most 4096 lines; a delete compacts the resource block; verb 66 with a class other than 10 kills the REPL.
- **Do not `pkill` emulator or route processes by pattern:** the permission classifier denies it (and another session may own a dotnet process); stop your own background run with TaskStop.

## Next session

`/resume cadaver` and start with open item 1: from `full_A/room31/end_room31.snap` (health 60), read room 31's altar puzzle (altar 131, drape 130, skull 198), drive it by natural input, and continue toward item 731 and door `$74`. Measure room 19's STAMINA 521 on the way if health drops below about 30. The level-0 road and level 1's first leg are finished and re-runnable; do not re-plan them unless a gate fails.
Prompt: `/resume cadaver`.

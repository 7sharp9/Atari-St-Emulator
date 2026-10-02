# Cadaver: handoff

Updated 2026-10-02 by the 90th-pass session (no subagents; room 31's altar puzzle, room 32, room 12, room 90).

## Resume point

- Last work commit: the one named `cadaver: 90th pass -- ...` (`mechanics.md` §79, `exit_level0/l1/route_level1_room90.py`, master stage `room90`). This handoff is in that commit or the one after.
- Read `reversing/cadaver/mechanics.md` §79 (every number below), then `py/secrets/overlay/action/exit_level0/README.md` (stage table, knobs).
- Re-run the segment: `cd M68000 && export M68000_ROOT=$PWD ATARI_NOTRACE=1 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/exit_level0/l1/route_level1_room90.py scratchpad/cadaver/s89/full_A/room31/end_room31.snap <outdir>` (about 12 minutes, no injection; or the master with `--upto=room90` from the treasury, about 17 minutes).
- Working data: `scratchpad/cadaver/s90/run1/` and `run2/` (44 snapshots each, `cmp`-identical), `end_room90.snap` in each (room 90 at (14,20,8,14), health 60, XP 1006); `sk1/` the exploration forks and `s90/*.py` its scripts; indexed in `scratchpad/ANCHORS.md`.
- Start from: `run1/end_room90.snap` (room 90, health 60, rucksack holds only the scroll 378 and the base records; the armour 578 went to room 7).
- No emulator source changed: no build or regression run needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in the docs)

Passes 77-89: main-loop keys, saves, rank table, assert layer, overlay, 94-verb grammar, sound sequencer, action panel, the whole level-0 road, level 1's arrival and first leg (§72-§78).

90th pass (§79, all driven natural, two identical runs):
- **Room 31:** a RIGHT+FIRE jump from the arrival lands on altar 131; UP, RIGHT, one FIRE jump overlaps skull 198; the drape and altar slide 16 cells; door `$7a` (north portal x 20..43) leads to room 12.
- **Room 32 (door `$36`):** armour 578 taken; the gates close behind the hero (every Up hold stalls at y trail 9); lever 146 pulled while VAR 6 = VAR 7 = 2 (bytes at `2282(A5)+6/+7`, stepped about every 400,000 steps) opens them; the exit is lane x 14..20.
- **Room 12:** state bit 0 is record +3 bit 0; lever 225's block only runs GOMOVE when that bit is set, which the room's event 17 does when an object lands in region 1 (x 41..55, y 9..23, z 4..12): the armour thrown east after a settle of 145,000 (a frame-phase lottery, searched) arms it (+26 XP, object sent to room 7). Icon 7 then sets pillars 213 and 214 oscillating in z; their clock runs on frames, so each crossing is a searched wait (100,000 under 214, 1,500,000 under 213, clearance 4 and 2); room 90 at health 60.
- **Room 90 does not hold item 731 yet:** 720 (room 53) shows it when key 690 (room 82) is applied; so the 89th handoff's "12 -> 90 -> item 731" was wrong.

## Open, in priority order

1. **The way to key 690 (room 82) and room 53.** Door `$79` (53-90) is closed (`ffff`) and opens only from 720 in room 53 (key 690); door `$67` (76-82) needs 267 in room 76 with item 266 (room 74). Candidate entries, all *read* only: room 93's levers 710 and 711 (each, with the other pressed, TELEPORTs to room 82 at (6,4,2)); room 93 is entered by region teleports (room 12's un-armed region, room 71's) and the pits of rooms 4, 15 (x 8..24, y 32..48, z 2..4, reachable), 47 and 71 lead to room 94 (holds 105, 653); object 740 (room 10) teleports to room 12 z 50. First drive room 15's pit and read what room 94 offers; also test whether room 90's lever 562 (UNLOCK/GOMOVE 670, deletes 213 and 214) opens the way to portal `$79`. Proof: a natural script that stands in room 82 or 53, run twice.
2. **Then 730 or 731 into the rucksack and door `$74`** (room 17 to 87; region event 15 of room 17 tests 730 or 731), room 87's six teleporters (it deletes weapons and magic items on entry), room 88's countdown (object 735, START LEVEL 2). The maze rooms 53-68 (flag doors `$45`-`$5c`, objects 237 in room 65 and 368 in room 56; stones 530-533, 234, 238 teleport into them) are the likely road to 730.
3. **More health before the long road:** STAMINA 521 in room 19, 475 in room 84, 219 in room 6, 535 in room 65 (§78). Health is 60 of 200 and every unknown room costs something; keep each new leg's health ledger.
4. **Unread in rooms already visited:** scroll 378 (room 31; FIRE with it selected casts, not throws), urn 611 and the SOULS RETURNED chain (event 4 gate `9d`, 730/731's blocks), room 31's regions, the chest 129 and plaques of room 32.
5. **Phase risks in the chain:** the three searches of `route_level1_room90.py` (throw settle, two pillar waits) are lineage-specific; a change anywhere earlier moves them (the script re-searches). Carried over from before: room 39's north lane, room 38 `up` unsolved phases, E1's `WQ` (§77); level 0's unread items (§77 Open).
6. Carried over: events 17 by a natural mover (now driven in room 12 for the armour), byte 23's other bits, the regions' z bounds, Disk 2 builds, verbs 56, 90, 44's class-bit-7 branch, 41's collision search, producers of events 1, 4, 10-13, 25, the jump's table, `$006f80`, depth-order loose ends (`graphics.md` §5k), older loose ends in `secrets.md` "Open".

## Known traps

- **Throw range depends on the steps since the last move** (settle S before the FIRE press: 0 lands on the far pillar's edge, 150,000 on the near one, 600,000 hits its side); a facing tap under about 30,000 steps does not turn the hero (the throw goes north); a scroll cannot be thrown (FIRE casts).
- **The pillars' and creatures' clocks can run on frames:** a recording with the hero standing still mispredicts a walk by 150,000 to 250,000 steps; search the wait on forks that perform the same walk (`cross()` in `route_level1_room90.py`).
- **Room 32 is a one-way room until lever 146 is pulled;** `bfs_goal` over holds finds no exit. Do not enter it without the VAR 6/7 plan.
- **Verb 41 PLACE injected with room `$fe` on object 227 crashed the game** (room 0, health 0); inject only on a throwaway fork and check the room afterwards.
- **A leg free in its own run is proven only for that lineage** (CLAUDE.md rule); run every segment from the previous segment's real end snapshot, then the whole chain twice.
- **Holds after a drop or a panel:** a hold started while the hero is still falling never moves (settle 300,000 first); a rucksack panel left open freezes every hold; hero positions step 1 or 2 cells, so an exact lead needs repeated 35,000-step taps (trace `[16,18,19,20]` reached 20).
- **Probe presses FIRE:** repeated `probe` calls while walking can lift the hero; walk with `goto` to the stand, probe once.
- **Return grid with six or more items:** the cursor `2122(A5)` names a different item than FIRE opens (`find_n`); with three or four items `select_item` works.
- **`lib/drv.py` does `os.chdir(ROOT)` on import:** `os.path.abspath` every snapshot argument first; `from lib import *` clobbers `START` and `OUTDIR`; `type8(r)['recs']` keeps stale records past the count byte (use `[:count]`); `Tally.run`'s default site list is `KEYSITES`, so to count a verb handler inside `pick_icon_id` rebind `t.run` with the extra sites.
- **Hold timing and phase:** a hold starts moving ~40,000 steps after the press, then one cell per ~10,000 in the old rooms and ~30,000 to 36,000 in rooms 12 and 32; a stall detector needs six 20,000-step chunks; after a room arrival wait ~100,000 to 150,000 steps. Every route script snapshots, closes and reopens after each hold.
- **Do not `pkill` emulator or route processes by pattern:** the permission classifier denies it; stop your own background run with TaskStop. REPL `w <addr> <8 hex>` writes four bytes. Earlier standing traps: injected-state results show a mechanism, not a route (label them); health only goes up by a verb 45; touch hazards cost per frame; door words are hex door numbers; the REPL prints at most 4096 lines; a delete compacts the resource block; verb 66 with a class other than 10 kills the REPL.

## Next session

`/resume cadaver` and start with open item 1: from `run1/end_room90.snap` (health 60), drive room 15's pit region to room 94 (or press room 90's lever 562) and read what leads to room 93's levers 710/711 and room 82's key 690; then room 53's keyhole 720 and item 731. Keep the room-31-to-90 chain as is; do not re-plan it unless a gate fails.
Prompt: `/resume cadaver`.

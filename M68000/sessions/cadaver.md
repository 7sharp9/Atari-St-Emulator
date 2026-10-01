# Cadaver: handoff

Updated 2026-10-01 by the 88th-pass session (17 agents in four rounds: five tracks, four chaining tracks, three joins, one promotion).

## Resume point

- Last work commit: `69b84e9` (`cadaver: 88th pass -- the whole level-0 road by natural input, treasury to room 60 ...`: `mechanics.md` §77, the promoted `overlay/action/exit_level0/`, digest corrections, README rows). `a6f8c71` is a CLAUDE.md rule (segment scripts need the real hand-off snapshot). This handoff is the commit after.
- Read `reversing/cadaver/mechanics.md` §77 (every number below), then `py/secrets/overlay/action/exit_level0/README.md` (files, hand-off snapshots, knobs). Every agent report is in `scratchpad/cadaver/s88/FINDINGS.md` (`BRIEF.md`, `BRIEF2.md`, `BRIEF3.md` are the briefs).
- Working data: `scratchpad/cadaver/s88/parent/full_A/` is the chain's 427 snapshots (indexed in `scratchpad/ANCHORS.md`); the agents' `out/` and `run*` directories were deleted (the master regenerates them).
- Rebuild or re-run the whole road: `cd M68000 && export M68000_ROOT=$PWD && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/exit_level0/route_level0_exit.py <outdir> [--upto=heal|d1|e1|g1|g2]` (about 4 minutes, no injection). It ends `FINAL room 60 health 20 xp 980` with `g2/end_room60.snap`.
- Start from: `g2/end_room60.snap` of a run (room 60 at (20,31,14,25), health 20, XP 980, rucksack [53,92,182,228,482], door `$29` open, dragon dead); the level change is `g2/level_change.py` (not in the master).
- No emulator source changed: no build or regression run needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in the docs)

Passes 77-87: main-loop keys, saves, rank table, assert layer, overlay, 94-verb grammar, sound sequencer, action panel, the natural road CAVERN -> treasury -> room 13's door `$2a` (§72-§76), the dragon's only killer (MASSACRE 324 after READ MAGIC 371).

88th pass (§77):
- **The whole level-0 road, treasury to room 60, by natural input** (no give, poke or injection; `exit_level0/route_level0_exit.py`): two runs by the parent 427/427 snapshots identical, a third by the promoted master 393/393 (heal, d1, e1, g1) and 34/34 (g2) identical; each leg's health is in the §77 table (47 at the door `$2a` stall, 30 after room 27, 20 at altar 99, 20 at room 60).
- **Way out of room 27 = the six-gem teleport:** variable 4 at `2286(A5)`, six throws from the lane y 25..31 at x lead 69, room 49, door `$0c` to room 48, whose entry teleports to room 22 (6/6 counted, two runs). Gems 164 (room 9) and 290 (room 20, one floor jump) are taken naturally.
- **Room 27's guard fires a 3x3 fireball down x 14..16** (-10), cause of the 87th pass's "drain on the south wall"; the `WQ` token waits it out.
- **The jump rises 35 and lands on both altar tops** (8/8 variants on altar 99, 2/2 on altar 45); a drop fires no event 4, only a thrown mover does.
- **Scroll half:** urn 453 smashes when pushed off platform 37, key 166, chest 157 (482 clears the trap), urn 165, the throw onto altar 99, 324 taken, READ MAGIC, MASSACRE (XP +552, 486, door `$29`, room 60), all driven; the level change (object 84) loads level 1 with health, XP and the maximum carried (health 23 of 200 in a sibling lineage).
- **Rooms 38 and 39 creatures advance only while the hero is inside the room:** `f1/route_cross38.py` crosses 38 from any phase it could find (down 192/192, up 169/214).

## Open, in priority order

1. **Level 1.** Add `level_change.py` to the master (or a `--level1` stage) so the real chain's level-1 arrival snapshot (health 20 carried, maximum 200, XP 980) exists, then solve level 1 from §75's first leg: the room 31 altar puzzle (altar 131, drape 130, skull 198), 12 -> 90 -> item 731 -> room 17 -> door `$74`, room 87's six teleporters, room 88's countdown (START LEVEL 2), lethal zones of rooms 29 (67 -> 7) and 34 (-10). Health is the constraint (20 of 200, no known heal): read level 1's health sources first (potions, flasks, waters in `item_census.py` over the level-1 snapshot) before driving. Proof: a natural script from room 0 to level 2's load, run twice.
2. **Phase risks in the chain** (only matter if the chain is re-planned): room 39's north lane has no lookahead (G1 searched a 1,125,000-step pre-wait: 0 -> -10, 250,000 to 500,000 -> -28), room 38 `up` has 45 of 214 unsolved phases (906 walking the south wall), and E1's `WQ` proceeds if no guard appears within 1.5M steps. Proof: a creature-table lookahead for room 39 on the F1 model; a sidestep or different entry phase for the 45; run from three phases each.
3. **Unread or undriven in level 0:** key 110 with object 391 (icon `$c`, door `$09`, rooms 40-41), rooms 41, 44, 54, 58, potion 450's effect (SUPER FAST?), item 256 (MAGIC SHIELD) and scroll 27's missile, the extra bit (`0x01`) READ MAGIC clears in 324's body byte 3, whether a cast spends a charge of 482, why room 27's guard never fired in D2's lineage (event-14 trigger and the guard AI unread), the room 52 spiders' respawn (-2 each way, not dodged), FIRE SHIELD 12 (stuck on a tomb top in room 57).
4. Carried over: events 17 by a natural mover, byte 23's other bits, the regions' z bounds, Disk 2 builds, verbs 56, 90, 44's class-bit-7 branch, 41's collision search, producers of events 1, 4, 10-13, 25, the jump's table, `$006f80`, depth-order loose ends (`graphics.md` §5k), older loose ends in `secrets.md` "Open".

## Known traps

- **A leg free in its own run is proven only for that lineage** (CLAUDE.md rule): E2's room 38 walk cost 0 in its run and 24 from the real hand-off snapshot. Run every segment from the previous segment's real end snapshot, then the whole chain twice.
- **Creature motion is a function of steps spent inside the room** (rooms 38, 39): waiting in the next room changes nothing; read the creature table (`route_cross38.py`) instead of counting steps.
- **Return grid with six or more items:** the cursor `2122(A5)` names a different item than FIRE opens; search the pulse count on forks and test the item word `1236(A5)` (`find_n`); `drv.pick_icon_id` walks blindly past a short panel row (a flask's `[9,11,13,1,6]`: DOWN from the cancel box selects the next rucksack item).
- **`lib/drv.py` does `os.chdir(ROOT)` on import:** `os.path.abspath` every snapshot argument first; `from lib import *` clobbers `START` and `OUTDIR` (a clobbered start silently cold-boots room 0 at health 67); `type8(r)['recs']` keeps stale records past the count byte (use `[:count]`).
- **Hold timing and phase** (unchanged): a hold starts moving ~40,000 steps after the press, then one cell per ~10,000; a stall detector needs six 20,000-step chunks; an exact cell needs `goto` with 5,000-step chunks; `Repl.__init__` runs `s 1`, so every route script snapshots, closes and reopens after each hold; after a room arrival wait ~100,000 steps. Do not tidy no-op tokens of a promoted script without two re-runs (the reload phase, not the intent, makes it deterministic).
- **Waiting is a move:** room 15's patrol (2,300,000), room 53's item 459 (4.8M), room 36's fireballs (from ~100,000 steps; the cast must come inside that), rooms 38/39's creatures, room 27's guard.
- **REPL `w <addr> <8 hex>` writes four bytes:** a health poke of four digits zeroed health in one trial (write the neighbouring word back).
- Earlier traps still standing: injected-state results show a mechanism, not a route (label them); after `H.real()` reload before driving; health only goes up by a verb 45; touch hazards cost per frame; door words are hex door numbers; the REPL prints at most 4096 lines; a delete compacts the resource block; verb 66 with a class other than 10 kills the REPL; `bt` crashed the REPL once.
- Subagent practice that worked again: a shared `BRIEF.md`, one directory per agent, reports as the final message saved by the parent into `FINDINGS.md`, the parent re-running every promoted script and `cmp`-ing snapshots; then a join round where one agent takes each seam on the real lineage, and a last agent that only promotes and gates (the parent's own join test found the room 38 loss no agent had seen).

## Next session

`/resume cadaver` and start with open item 1: add the level change to the master so the real chain ends at level 1's room 0 (health 20 of 200), then survey level 1's health sources and its first legs (§75 "Level 1's first leg and its graph") before driving. The level-0 road is finished and re-runnable; do not re-plan it unless a gate fails.
Prompt: `/resume cadaver`.

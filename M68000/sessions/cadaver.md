# Cadaver: handoff

Updated 2026-10-17 by the session that ended at commit `9f15b2f` plus this handoff commit.

## Resume point

- Last commits of this workstream: `1bea9b7` and its correction `22bec59` (the cut closures, `graph/armed_cut.py`, `l1/probe_r12_seal.sh`, `plan_full.py --nodoors`, `sim.py` charge count), `30339be` (room 4's high doors crossed: `route_pocket.py` legs 29-33), `751e98a` (README digest line), `9f15b2f` (skill lesson).
- The `bin/` DLL is still built from `0b92317`; no emulator change this session.
- Start from `scratchpad/cadaver/s95/pocket/full/33_to6.snap`: room 6 at (70..76, 8..14), bottom z 64 on ledge 392, health 89, poison 0, XP 1110, rucksack 391, 570 (SLEEP), 680, 491 (CURE POISON, 3 doses), 493; VAR 9 = 4, 380's bit 0 set (480 drunk). `32_raise232.snap` (room 4, raised lift under both doors) also leads to room 5 by `HU`.
- Rebuild chain (about 5 minutes, from `M68000/` with `export M68000_ROOT=$PWD ATARI_NOTRACE=1`, scripts under `reversing/cadaver/py/secrets/overlay/action/exit_level0/l1/`): `route_level1_room89.py scratchpad/cadaver/s90/run1/end_room90.snap A`, `route_health.py A/24_back18.snap B`, `route_tokenL.py B/27_out14.snap C`, `route_pocket.py C/42_take709.snap D` (33 legs; that directory's README). The full `route_pocket.py` run matched 38 of 38 snapshots against the previous runs.
- Disk image `../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (relative to `M68000/`) must exist; untracked, like the rest of `Cadaver/`.
- Uncommitted work left behind: none (`Cadaver/` is the disk images; `scratchpad/cadaver/s95/` is working data).

## Proven so far (counts in the docs)

Earlier passes: main loop, saves, ranks, asserts, overlay, the 94-verb script language, sound, action panel, level 0's road, level 1 to room 89, the linter, key 508, VAR 17, the health route, token L, the tokens on slot 206, rooms 9, 10 and 89's shelf, the portal rule, room 94's death below 200 gold (`secrets.md`, `mechanics.md` sections 1-12).

This session (`mechanics.md` section 12, "Room 4 and the pocket"):
- **Room 4's high doors are crossed by natural input** (`route_pocket.py` legs 29-33, two runs 6/6 identical, full run 38/38): lift 2 lowered by 231, pushed east to x 64..79 over the pit (at z 6..13 it is above the pit region's z 2..4), RIGHT jump onto it, east along the north wall to lever 232, operate it, the lift rises with the hero to bottom z 64 at x 68..74; DOWN through `$08` into room 6, UP through `$07` into room 5. The solution came from the oldgames.sk walkthrough (its level 2, room 40).
- **Lift 2's mover program is z only** (`04 00 | 00 00 00 ce | 04 01 | 02` and the same with +50); both levers run GOANI on themselves and GOMOVE object 2 (*read*, consistent with the drives).
- **Room 12's un-armed region is walled off on foot** (`l1/probe_r12_seal.sh`: both lanes stall at x lead 35 against pillar 214): the closure edge `r12.1` to room 93 is a model over-approximation. With it dropped, or with `$07`/`$08` cut, the closure gives 43 rooms from the arrival and the lineage alike (`graph/armed_cut.py`).
- **`sim.py` counts UNLOCK DOOR charges** (`cast_max` 15) and walks no `no_doors`; the default `plan_full.py` from room 90 still gives 137 actions, 9 casts.

## Open, in priority order

1. **Room 6 and the rest of the pocket.** Room 6 is a height puzzle: the hero arrives on ledge 392 (64..79, 8..23, z 56..63); key 251 sits at (11..13, 74..76) z 64..66 on the west column stacks (167-180, 536: x 8..13, z 0..63); keyhole 698 (19..23, 7, z 24..39, class 11) takes 251 to open `$10` to room 1, the way out; STAMINA 219 (10..12, 57..59, z 64); post 380 (70..78, 20..28, z 0..53) moves now that 480 is drunk (*read*); door `$09` to room 8 (gem 718) is a high east-wall portal (x 80..82, y 4..27, z 64..111). Drive across at z 64 (find the walkable tops with `D`), take 251 and 219, apply 251 to 698, reach room 8 for 718. Then room 5 (`32_raise232.snap` + `HU`): key 245 and `$06`/`$7f` to room 7 for 716, 717.
2. **Then the 91st-pass chain from the pocket:** gem lock 719 in room 2 (716, 717, 718 in that order), key 538 on 539, lever 275, rooms 50, 70, 71, 93 (levers 710/711), room 82 (key 690), 52 (scroll 407): `graph/plan_full.py` from a snapshot taken after the pocket (`CAD_LINEAGE_SNAP=<snap>`) gives the exact script-level legs. Each leg is *inferred* until driven; health is not charged by the ledger (pits into room 94 cost 25 each).
3. **Gold 200 for 653** is no longer on the critical path (room 82's entry block shows 653, *read*); 760/761 in room 14 appear only when VAR 1 > 0 and the room's random value is 4 or 3 (*read*).
4. **`explore.py` `C`/`K` lose pulses with five or more rucksack items:** the cause is *inferred* (the Return grid is four cells wide, RIGHT cycles only the first row, a DOWN reaches the second, the first pulse after Return is lost; `route_pocket.py`'s `SEQS`). Fix the panel code to navigate by row and column, then make `route_level1_room89.py` assert VAR 9 after token F.
5. **Tooling leftovers:** `m` on an unmapped address (`ff8605`) raises BusError and ends the REPL; a negative hex operand (`m -5 4`) crashes with ArgumentException; `snd_proof.py:64` counts a short run as a match; the write-protect tab is not in snapshots. Emulator changes go behind the section-6 net (worktree agents: CLAUDE.md "Emulator changes").
6. **Natural entries still injected:** room 86 (take 507 in room 24, shown by object 492) for the key-508 delivery; the casket 513 applied to the strong box 379 with scroll 378 inside.
7. **Linter gaps:** rule (e) objects 638 and 688 are read-only; rule (d) cannot see `$e020` or the Disk 2 levels; `$00e186` pushes the debug string's address as a text index.
8. **Unread or undriven in the script layer:** `$fa62`'s class `$80`/`$81`/`$84` branches, event 11's two exclusions, ring-queue overflow, the anim ops `$f3 $f4 $fa $f7 $ff`, header `+3` bit 2 and `+15` bits 1, 5, 6, door `+7` bits 4-6 live, verb 44's launch nibble 15, the name of template 135, the Disk 2 levels' scripts; the poison tick schedule.

## Known traps

- **The model does not push objects:** `relax.py`/`sim.py` treat movers as fixed and ignore z, so a puzzle solved by moving a block (room 4's lift) reads as a dead end, and a region walled off by static objects (room 12's `r12.1`) reads as open. Check a closure verdict's deciding edge on foot (skill section 5).
- **The oldgames.sk walkthrough** (`oldgames.sk/docs/cadaver/walkthrough.php?map=c2` for level 1) uses its own room numbers: match rooms by their objects (its room 40 is room 4 here).
- **Room 4 is entered one-way by `$01`** (entry block shuts it; lever 27 is in room 89); its exits are the high doors by the pushed lift, or the pit (room 94, -25, death below 200 gold unless 653 is shown).
- **Room 13 entered by `$15` from room 14:** creature 912 takes 50 about 100,000 steps after arrival; enter by `$16`.
- **The Return grid is four cells wide; the first pulse after Return is lost:** `RD` is cell 4, `RDR` cell 5 (`route_pocket.py` `I<oid>:<icon>` and `SEQS`).
- **Room 89's shelf is one-way down**; the poles leave one gap off it, x lead exactly 28.
- **Room 9's high doors work only from block 140 raised by 393**, and 391 rides up with it and blocks the lane to `$0e` until taken.
- **zsh redirects an unquoted `GR:x>=24`:** quote every `explore.py` command containing `>` or `<`. A goto that stalls (`GR:x>=79` against lever 232) ends without error: read the printed position.
- **A render right after a room change shows the old room** for about 100,000 steps; **health alone does not show a POISON bite:** check `2434(A5)` (`N`).
- **Drink CURE POISON only after leaving the biter**; room 18 after the room-20 detour needs a 450,000-650,000-step stand before going north. Room 92: 808 poisons, 807 comes out of wall 400 about 100,000 steps after lever 399.
- **`hold` ends after six stalled chunks**; a door needs the whole bbox inside its portal; `M<door>` searches lanes. Holds start about 40,000 steps after the press, one cell per about 25,000; a hold begun while falling never moves; jumps need a run-up and the takeoff direction is fixed.
- **`slot_map()` in `g2/lib.py` skips slot 0**; **`lib/drv.py` chdirs to ROOT on import**; **`H.obj()` goes stale after a DELETE**. Two snapshots sit in the `$0117c4` assert spin (`s86/a7/snaps/gomove31.snap`, `s86/a6/snaps/room69.snap`).
- **Injected-state results show a mechanism, not a route** (label them); health only goes up by a verb 45; door words are hex door numbers.

## Next session

`/resume cadaver`. Open item 1 first: survey room 6 from `33_to6.snap` (`explore.py ... D P`, then `W` traces along the tops at z 56..64) and drive to key 251, keyhole 698 (`$10` out to room 1) and room 8's gem 718; then room 5 from `32_raise232.snap` for 245, 716 and 717. Promote the legs into a new `l1/route_pocket2.py` continuing `route_pocket.py`. After that, run `plan_full.py` from the pocket's end snapshot to plan item 2.

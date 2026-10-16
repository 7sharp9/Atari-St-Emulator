# Cadaver: handoff

Updated 2026-10-17 by the session that ended at commit `1a223df` plus this handoff commit.

## Resume point

- Last commits of this workstream: `0b92317` (emulator and tools: open item 5 of the previous handoff, all of it), `c88f599` (`l1/route_pocket.py`, the portal rule, room 4 and room 94, `graph/reach_cut.py`), `ee68406` and `1a223df` (CLAUDE.md and the skill).
- The `bin/` DLL is built from `0b92317`. The REPL now exits 1 with `REPL error: <n>: <line>: <reason>` on an unknown command, wrong arity or bad operand (blank and `#` lines are skipped); undecoded encodings take vector 4 with an `ILLEGAL:` stderr line; `watch` sees covering and DMA writes; `hits`/`bp`/`bpc` count instruction starts with 24-bit compares; snapshots carry disk-A writes (optional `DSKA` section). Details: `DEVELOPING.md`.
- Route work resumes from `scratchpad/cadaver/s94/route206/run1/25_drop89.snap`: room 89 on the floor, door `$01` open, health 89, poison 0, XP 1110, rucksack 391, 570 (SLEEP), 680, 491 (CURE POISON, 3 doses), 493; VAR 9 = 4 (all four tokens on slot 206, `$0b` open); 380's bit 0 set (480 drunk). `29_ride2.snap` (room 4 on raised lift 2) is the probe state for the high doors; room 4 is one-way.
- Rebuild chain (about 4 minutes, from `M68000/` with `export M68000_ROOT=$PWD ATARI_NOTRACE=1`, scripts under `reversing/cadaver/py/secrets/overlay/action/exit_level0/l1/`): `route_level1_room89.py scratchpad/cadaver/s90/run1/end_room90.snap A`, `route_health.py A/24_back18.snap B`, `route_tokenL.py B/27_out14.snap C`, `route_pocket.py C/42_take709.snap D` (index: that directory's README). The promoted `route_pocket.py` on the new DLL matched the old DLL's run 35 of 35.
- Disk image `../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (relative to `M68000/`) must exist; untracked, like the rest of `Cadaver/`.
- Agent reports: `scratchpad/cadaver/s94/{route206,repl5b,item5}/report.md`; the route agent's probe scripts (portal hits, jumps, drops, gold) in `s94/route206/w/`.
- Uncommitted work left behind: none (`Cadaver/` is the disk images).

## Proven so far (counts in the docs)

Passes up to the previous handoff: main loop, saves, ranks, asserts, overlay, the 94-verb script language, sound, action panel, level 0's road, level 1 to room 89, the linter (rules a-f), key 508, VAR 17, the health route and token L (`secrets.md`, `mechanics.md` sections 1-12), the verb 5 XP bug and its fix on Hatari.

This session (`mechanics.md` sections 3 and 12, "Back to slot 206" and "Room 4 and the pocket"):
- **`l1/route_pocket.py`, 29 legs, natural input, two runs 35/35 identical:** room 43 back to room 89 (13 by `$16`), W, U, L on slot 206 (VAR 9 1 to 4, `$0b` open), room 9 (393 raises block 140; high doors only from it), room 10's stair (four jumps), 391 taken, 480 drunk (380 bit 0), `$0e` to room 89's cap 17, lever 27, the one gap off the shelf (x lead 28 exactly), room 4, lift 2 ridden to z 64. Health 89 and poison 0 throughout.
- **Portal rule** (`$008ac8`): walk only; the hero wholly inside the portal along the wall and in z (bottom z 63..82 for a door at z 64..111). A jump into a portal is a wall: `$8b7c` matched, `$716e` 0 runs, against a walk control that runs `$8b7c`, `$716e`, `$727c`.
- **Room 4 is one-way and its high doors `$07`/`$08` are not crossed from any driven stand:** lift 2 stays at x 40..55, the hero falls at x trail 56, the doors need trail 60; lever 232's top (bottom z 36) is the only surface at x 60 or more.
- **Room 94 kills below 200 gold:** pit landing -25, 0 portals, 105's examine with 0 gold runs HEALTH -127 (driven to the death screen). Applying 653 goes to room 52 only for a hero who came from room 52.
- **With `$07`/`$08` cut the lineage cannot finish level 1** (`graph/reach_cut.py --nodoors=7,8` from `25_drop89.snap`: 43 rooms, none of 6, 52, 82, 718, 251, 407, 653, 690, level 2, spells included; control without the cut 77 rooms and all of them). Reachable gold is at most 190, 653 costs 200.

## Open, in priority order

1. **Is level 1 unwinnable from the arrival, or only from this lineage?** Run `graph/reach_cut.py --nodoors=7,8` with `CAD_LINEAGE_SNAP` set to the level-1 arrival (`level1/level1_room0.snap` of `route_level0_exit.py --upto=level1`) and to `end_room90.snap`. If the arrival also cannot reach room 6/52/82, the model is missing an edge (a door, teleport or mover the closure does not see) or `$07`/`$08` are crossed in a way not yet read; if the arrival can, an earlier action of the lineage spent something (find it with `--plan`).
2. **Lift 2's mover program and lever 232's GOMOVE target.** The route agent did not decode the mover (`w/mem.py` dumps its record). Read it with the mover model (mechanics.md section 9): does any branch move the lift in x, stop higher than bottom z 56, or depend on what stands on it? Then drive lever 232 (read only so far). Only if the code says a walk off the lift should reach the portal is a real-hardware check worth it (Hatari cannot load these snapshots: it would need the whole drive replayed there).
3. **Gold 200 for 653:** 760 (+20) and 761 (+100) in room 14 appear only when VAR 1 > 0 and the room's random value is 4 or 3 (*read*). Read VAR 1's writers and the random draw; with 371 (+20) and 743 (+50) that is 190, so a further source is needed in any case.
4. **`explore.py` `C`/`K` lose pulses with five or more rucksack items:** the cause is now *inferred* (the Return grid is four cells wide, RIGHT cycles only the first row, a DOWN reaches the second, the first pulse after Return is lost; `route_pocket.py`'s `SEQS`). Fix `explore.py`'s panel code to navigate by row and column, then make `route_level1_room89.py` assert VAR 9 after token F.
5. **Tooling leftovers:** `m` on an unmapped address (`ff8605`) raises BusError and ends the REPL; a negative hex operand (`m -5 4`) crashes with ArgumentException; `snd_proof.py:64` counts a short run as a match; the write-protect tab is not in snapshots. Emulator changes go behind the section-6 net.
6. **Natural entries still injected:** room 86 (take 507 in room 24, shown by object 492) for the key-508 delivery; the casket 513 applied to the strong box 379 with scroll 378 inside.
7. **Linter gaps:** rule (e) objects 638 and 688 are read-only (a live poke of the bit, as for room 27); rule (d) cannot see `$e020` or the Disk 2 levels; `$00e186` pushes the debug string's address as a text index (drive SLEEP with no creatures registered to see the banner).
8. **Unread or undriven in the script layer:** `$fa62`'s class `$80`/`$81`/`$84` branches, event 11's two exclusions, ring-queue overflow, the anim ops `$f3 $f4 $fa $f7 $ff`, header `+3` bit 2 and `+15` bits 1, 5, 6, door `+7` bits 4-6 live, verb 44's launch nibble 15, the name of template 135, the Disk 2 levels' scripts; the poison tick schedule (ticks in room 15, not in 13 or 28).

## Known traps

- **Room 4 is one-way:** its entry block shuts `$01`, the opener (lever 27) is in room 89. Branch new routes from `25_drop89.snap`, not from the room-4 legs.
- **Room 94 is death without 200 gold** (the pits of rooms 4, 15, 47 and 71 lead there).
- **Room 13 entered by `$15` from room 14:** creature 912 takes 50 about 100,000 steps after arrival; enter by `$16`.
- **The Return grid is four cells wide; the first pulse after Return is lost:** `RD` is cell 4, `RDR` cell 5; RIGHT alone never leaves the first row (`route_pocket.py` `I<oid>:<icon>` and `SEQS`).
- **Room 89's shelf is one-way down** (caps 18/19 to 17 needs a LEFT jump from x lead 34); the poles leave one gap off the shelf, x lead exactly 28.
- **Room 9's high doors work only from block 140 raised by 393**, and 391 rides up with it and blocks the lane to `$0e` until taken.
- **`relax.py`/`reach_cut.py` ignore z:** a room reached through a high door or a key on a cap (room 7 via key 245) is an over-approximation.
- **The disk image must be at `../Cadaver/...[one disk].st`:** without it every `repl.py`-based script fails (now with `repl closed (exit 1)` and the stderr tail).
- **Drink CURE POISON only after leaving the biter.** Room 18 after the room-20 detour needs a 450,000-650,000-step stand before going north.
- **Room 92:** 808 poisons, 807 comes out of wall 400 about 100,000 steps after lever 399; the teleports 401-403 need a vertical jump with x inside 41..43.
- **`hold` ends after six stalled chunks:** `Z<door>:<lane>:<chunk>`; a door needs the whole bbox inside its portal; `M<door>` searches lanes.
- **zsh redirects an unquoted `GR:x>=24`:** quote every `explore.py` command containing `>` or `<`.
- **A render right after a room change shows the old room** for about 100,000 steps.
- **Health alone does not show a POISON bite:** check `2434(A5)` (`N` in `explore.py`).
- **`slot_map()` in `g2/lib.py` skips slot 0**; **`lib/drv.py` chdirs to ROOT on import** (absolutize snapshot arguments first); **`H.obj()` goes stale after a DELETE**.
- **Two snapshots sit in the `$0117c4` fatal-assert spin:** `s86/a7/snaps/gomove31.snap`, `s86/a6/snaps/room69.snap`. Verb 41 PLACE with no free space asserts and hangs; verb 66 with a class other than 10 kills the REPL.
- **Hold timing:** a hold starts moving about 40,000 steps after the press, one cell per about 25,000 in level 1; a hold begun while falling never moves; a panel left open freezes every hold; jumps need a run-up and the takeoff direction is fixed.
- **Injected-state results show a mechanism, not a route** (label them); health only goes up by a verb 45; door words are hex door numbers.

## Next session

`/resume cadaver`. Open item 1 first: it is cheap (a closure run per snapshot) and decides whether the problem is the lineage or the model. Then item 2: decode lift 2's mover program before any more jump trials. Items 3 and 4 can go to parallel agents (one reads the gold gates, one fixes `explore.py`'s grid navigation); worktree agents for any emulator leftover in item 5 (CLAUDE.md "Emulator changes").

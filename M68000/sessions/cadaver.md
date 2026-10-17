# Cadaver: handoff

Updated 2026-10-17 by the session that ended at the commit of this handoff.

## Resume point

- Last commits of this workstream: `30339be` (room 4's high doors crossed, `route_pocket.py` legs 29-33), `22518ef` (previous handoff), then this session's commit (room 6's post mechanism, rooms 5, 7 and 8 surveyed on forks; `explore.py` `P`/`=` commands; `l1_objects/blocks_of.py`, `movers.py`; mechanics.md section 12).
- The `bin/` DLL is still built from `0b92317`; no emulator change this session.
- Lineage snapshots: `scratchpad/cadaver/s95/pocket/full/33_to6.snap` (room 6, ledge 392, z 64, health 89, poison 0, XP 1110, rucksack 391, 570, 680, 491, 493; 391 sits in slot 0, which `T`'s `slot_map()` hides) and `32_raise232.snap` (room 4, raised lift; `HU` enters room 5). Rebuild chain as before (about 5 minutes from `M68000/` with `export M68000_ROOT=$PWD ATARI_NOTRACE=1`, scripts under `reversing/cadaver/py/secrets/overlay/action/exit_level0/l1/`): `route_level1_room89.py scratchpad/cadaver/s90/run1/end_room90.snap A`, `route_health.py A/24_back18.snap B`, `route_tokenL.py B/27_out14.snap C`, `route_pocket.py C/42_take709.snap D`.
- This session's exploration forks (records, not a route) are under `scratchpad/cadaver/s96/r6/`: `floor.snap` (room 6 floor), `s3_flask.snap` (sack taken, post at (16..24, 32..40)), `take718.snap` and `scroll458.snap` (room 8), `r5key.snap` (room 5 floor, key 245 held), `r7.snap` (room 7 arrival by `$06`), `r7probe2.snap` (on the gem tile, health 69). Their command lines are in this session's `mechanics.md` bullet and reproducible with `explore.py`.
- Disk image `../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (relative to `M68000/`) must exist; untracked.
- Uncommitted work left behind: none.

## Proven so far (counts in the docs)

Earlier passes: `mechanics.md` sections 1-12 (main loop, saves, ranks, overlay, the 94-verb script language, level 0's road, level 1 to room 89, the health route, token L, rooms 9, 10, 89's shelf, room 4's high doors by the pushed lift).

This session (`mechanics.md` section 12, "The pocket's rooms 6, 8, 5 and 7"; each driven once on a fork, nothing promoted):
- **Room 6's mechanism**: the caps 162, 164, 166 run GOMOVE on their item (251, 219, 221) on event 9 gated on the post 380's id; the items' programs are +8 in x then stop, so an item falls to the floor when the post's y band does not cover its landing cell. The sack was brought down and taken this way (XP +25). The post moves: pushed north or south against the east wall, north-west by UP+LEFT from its south-east corner while at the wall, west from the east once off the wall.
- **Room 8**: `$09` from the ledge; gem 718 and scroll 458 taken (small objects are pushed ahead of a walk; approach from the north facing down). Chests 207, 328, 329 MOVE sacks 287/288, wand 478, flask 475 on event 5; icon 3 on 329 twice did nothing.
- **Room 5**: key 245 pushed off cap 12 and taken from the floor; `$06` and `$7f` both keyed to 245 (consumed); `$06` crossed into room 7 at (8..14, 14..20) z 0.
- **Room 7**: gems 716, 717 on tile 634; walking east along y 31..37 costs 4 health per 20,000 steps from x lead 33 (89 to 69); SLEEP (spell 23) is a flash-only stub in the cast table.
- Tooling: `explore.py` `P<dirs>:<oid>:<axis><op><n>` (hold until an object's rect meets a condition; ignores the engine's transient `255` rects; stalls out after 150,000 still steps), `=<axis><n>` (exact taps), `T` prints gold and XP; `l1_objects/blocks_of.py` (blocks by owner, `refs` for every block naming an id), `l1_objects/movers.py` (mover programs).

## Open, in priority order

1. **Pin the block push rule, then finish room 6.** Two pushes down from the north with the hero at x 15..21 and 17..23 inside or beside the post's 16..24 did not move it, while the same push at the east wall moved it 20 cells; UP+LEFT off the wall slid along the post instead of pushing. Trace the hero's walk routine's collision branch (`$008a34`/`$008a68` region, mechanics.md "Solidity summary") for the condition that moves the blocking object, or bisect empirically with `s96/r6/trace.py` (hero x offset, facing, approach speed). Then from `s3_flask.snap`: post to y 60..68 and west (flask 219 lands at (18..20, 57..59): take and drink, +100), post to y 64..72 and west (key 251 lands at (19..21, 74..76)), take it from the lane y 73..79, apply it to keyhole 698 at (19..23, 7) from (17..23, 8..14) facing up (`I251:c` through the Return grid, 7 items), `E10`, `Z10` into room 1. Promote the legs into `l1/route_pocket2.py` continuing `route_pocket.py` (copy its `item_icon`/`exact`/`operate`/`run_leg` helpers or move them into `explore.py`).
2. **Room 7's gems**: find the hazard (a creature loop, a region, or the walleyes' projectile: `watch` the health word on `r7probe.snap` while walking east, read the writer's PC) and whether a jump over the tile or a SLEEP cast (the game answers spell 23 somewhere: grep the room blocks for event 24/25 with 23) avoids it. The gems go on the gem lock 719 in room 2 (716, 717, 718 in that order). The way back from room 7: `$06` (open once crossed) to room 5's floor, `$7c` to room 4's floor, lever 231 lowers the lift, then `route_pocket.py` legs 31-33 again.
3. **Room 8's chests** with scroll 458 (name unread; the walkthrough's Unlock Chest spell): select it through the Return grid, FIRE at a chest; two moneybags, the wand and the +75 flask. Also why `1188(A5)` read 0 after the sack's GOLD += 100 block (find the gold word from the status bar's writer).
4. **Then the 91st-pass chain from the pocket**: `graph/plan_full.py` from the pocket's end snapshot (`CAD_LINEAGE_SNAP=<snap>`) for key 538, lever 275, rooms 50, 70, 71, 93, 82 (key 690), 52 (scroll 407).
5. `explore.py` `C`/`K` lose pulses with five or more rucksack items (use `route_pocket.py`'s `I`); tooling leftovers (`m` on an unmapped address, negative hex operand, `snd_proof.py:64`, the write-protect tab) and the linter gaps and unread script-layer branches listed in the previous handoff stand.

## Known traps

- **The first hold after loading `33_to6.snap` takes about 120,000 steps to start**, longer than `hold`'s six-chunk stall test: `HR` from the ledge reads as a stall at x lead 77 (door `$09` needs lead 79). Precede it with any move or an `S`.
- **The placement rect of a moving block reads `255, 255, ...` mid-move**: a condition on it (`P`'s, or your own) must skip such reads, or it fires after one cell.
- **Small objects are pushed ahead of a walk** (718, 458, key 245 off its cap): approach an item from the side you can afford it to move away from, or face it across an axis it cannot move along.
- **A push needs the hero where the rule allows** (not yet pinned): a block against the east wall was pushed from the north, the south and the south-east corner (diagonal); off the wall only the push from the east worked. Trace, do not retry.
- **zsh eats `=x23`** (`=word` is a command path): quote `explore.py` words starting with `=`, as with `>`/`<`.
- **`slot_map()` skips slot 0**: `T`'s rucksack list misses the item in slot 0 (391 all this session, then 458 or 245). Count the type-8 records when an item count matters.
- The rest of the previous handoff's traps (room 4 one-way by `$01`, room 13 by `$15`, the Return grid's lost first pulse, room 89's shelf, room 9's block 140, the render lag, poison, `hold` ends after six stalled chunks, `lib/drv.py` chdirs on import, `H.obj()` stale after a DELETE, injected results are mechanisms not routes).

## Next session

`/resume cadaver`. Open item 1 first: pin the push rule from the code or by bisection on `s96/r6/trace.py`, then drive the flask and the key from `s3_flask.snap`, the keyhole and `$10` into room 1, and promote it all as `l1/route_pocket2.py` (two runs, every snapshot `cmp`). Then room 7's gems (item 2) and the chests (item 3), and `plan_full.py` from the pocket's end for item 4.

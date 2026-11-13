# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `9002027` (lock panel, finishing a base, footprint chase, lift ride).

## Resume point

- Last commit of this workstream: `9002027` captive: promote pcrel_calls.py; ANCHORS rows (work commits `b153c3c`
  panel, finishing a base, footprint chase; `e53c357` curios scripts promoted; `83dbb2c` lift).
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` (README
  "Provenance"). Generator captures `mapgen_full/` (`py/mapgen/full/README.md` rebuilds them byte-identical).
  Sealed-key and panel work `phoopel/` (`base13.snap`, `panel_*.snap/png`, `finish_base1_*`, `finish_m1_100.txt`,
  `sealed_m1_100.txt`). Lift and footprint states `agents/ai/lift/`, `agents/ai/footchase/` (rebuilt by the commands
  in `py/ai/README.md`). Saved agent reports: `agents/{footprint,lift}/report.md` and the older
  `agents/{placement,shafts,chain,ai2,curios,info_*}/`.
- Start from: `base1/in.snap` (natural base, party at the entrance (30,0), facing S), `phoopel/base13.snap` (D0 = 13,
  sealed flame door (7,9), panel W (5,8)), `phoopel/finish_base1_blast_state2.snap` (natural base, generators blown),
  `agents/ai/lift/on_lift.snap` (party on lift (8,3) of the `req4.snap` base), `agents/ai/g16_adj.snap`,
  `agents/curios/base30.snap` (every feature), `mission1.snap` (no sidecar: pass `--disk-a scratchpad/captive/tmb097.st`).
- Uncommitted work left behind: none.

## Proven so far

Detail and commands in the topic docs; scripts under `reversing/captive/py/<area>/` with README tables.

- Whole base generator in Python from (D0, D2): 400/400, every stage gated (`mapgen.md` "The pipeline").
- Locks and keys: keys dug no later than their door 8,617/8,617; 31 sealed on their own door cell (`mapgen.md` "Locks
  and keys", `lockcensus.py`).
- The lock panel: W is a bank of switches behind a cover, compared with the code on every click; Phoopel's lock 4
  opens on segments 5, 8, 10, 15, control with one wrong stays shut; 15099 is the panel's printed label (`mapgen.md`
  "The panel in play", `py/phoopel/panel13.py`). Key kinds 0-2 layouts from reading.
- Finishing a base: EXPLOSIVES on a generator tile, `13410(A6)` 0 -> 1 -> 2 -> 3, 9/9 generators to flame, the fire
  follows the dig arrows 21/21 to the entrance; an untouched base cannot be left (`$87d6` 0 hits), in state 2 the
  entrance click marks the target visited 0 -> 1 (`ai.md` "Finishing a base", `py/phoopel/finish13.py`, `leave.py`).
- Sealed bases: 100 of 24,603 keys in 92 bases (missions 1..100); in 27 of the 92 every generator is behind a sealed
  door, 18 of those with a 16-segment lock (`mapgen.md` "Sealed keys", `py/phoopel/finish.py 0 100`, model).
- A chase that reads footprints: 8/8 trail moves follow bits 3-5, model replay 5/5 against 2/5 from bits 0-2
  (`ai.md` "The trail", `py/ai/footchase.py`).
- Lift: a ride writes no footprint (0/2048, writers 0 hits); a follower forgets only at a lift end holding 4 or 5
  (4/4 at (24,3)) and loiters; at a value-0 end it never forgets (15/15) (`ai.md` "The trail", `py/ai/lift/`).
- Universe, AI decision rule 3000/3000, regroup 2000/2000, doors and the DIE, four infographics: as before
  (`world.md`, `ai.md`, `py/infographics/README.md`).

## Running

Nothing running.

## Open, in priority order

1. Does a mission need every target visited? Decides how much the 27 blocked bases matter. Read what tests the
   visited count `14794(A6)` and the target bytes `14170(A6)` (start at `$87d6`-`$8810` and the map screen), then drive
   it: `leave.py` from `phoopel/finish_base1_blast_state2.snap` reaches the compound with visited = 1.
2. State 3 with the party inside: `14800(A6)` = 3 and what kills or ejects the party (a party poked onto the burning
   entrance ended in mode 1 at (0,0), no exit routine hit). `watch` the mode word `13564(A6)` from
   `finish_base1_blast_after` (re-make with `finish13.py`); also settles `14800` value 3's end message (`$137b0`).
3. The other panels and door kinds: key kinds 0, 1, 2 (1, 3, 8 switches) and door kinds 0 and 1, in `base13.snap`
   (`panel13.py <lock>` takes a lock number; locks 0, 1, 3, 6 cover them; the switch geometry for kinds 0-2 needs
   adding to the script from `$12c2c`-`$12cb2`). The re-close on byte +8 bit 4. Items `$19`.
4. A lift follower reached by play alone (both runs start from a poked party cell; the lift agent reports group 49
   holding the corridor in `req4.snap`, not re-checked); the pair (2,4)-(18,4); tiles `$30`/`$33` (`$9768`/`$977c`).
5. What gives the party a `$66` MESSAGE FROM RATT with word 1 (`$26946` via `$23f64`); `14800` values 1 and 2.
6. The `$c194` item branch live: drop a FLAMBOS or BATTERY on a `$26` cell and read byte 2 (from reading: `$3c`).
7. The six `15538(A6)` tests on an uncracked copy (`system.md` 7; needs READ TRACK `$e0`). `cold_watch.sh b514 12` not
   re-run from the promoted location.

## Known traps

- Panel W took switch clicks from (5,9) facing N with its cover shut and nothing drawn (`$dd96` sends any facing
  with (tile - facing) & 3 != 0 to the switch handler); it is drawn only from the cell it faces. Render the view
  before calling a click drive proven.
- The leave click needs the party on the entrance cell facing N; `base1/in.snap` faces S, so an unpoked control hits
  nothing at all (`leave.py <snap> poke`).
- A poked request-word base (`base13.snap`, `req4.snap`) has no compound and no target: do leave and visited tests in
  `base1/in.snap`.
- `federation` calls far routines by `move.l #imm,Rn` / `jsr -8(PC,Rn.l)`: a grep of the listing for the target finds
  nothing. Use `py/system/pcrel_calls.py`.
- stserver reports watch-event addresses and values as `'$hex'` strings.
- A creature group can step into a cell between two key presses (the walk through the opened flame door stopped at
  (7,9) with a group on (8,9)): read the occupancy bit 7 of the tile ahead before reading a stall as a wall.
- `level_event.py` alone does not reach the compound entrance (22,22) after the exit: the ai2 agent's longer run did.
- `die_all.py`'s 2400 and 6400 are repeats: cite `gen_lock.py`'s 1080/1080.
- `field.py` reports `loop` once the party has moved; use `trailend.py`. Count open cells by tile > `$1a`.
- Map pointer: three `mouse move -127 -127` pin it at (0,0), then 1:1. Lift icons (202,112) up, (251,112) down;
  panel switches from (90,98), 5-pixel cells. Door corner zones: x 70 or 134, y 80 or 145.
- `track.py` samples every 60,000 steps (not a main frame): use `sched.py` or per-action stops (`footchase.py`).
- Menu key: release 30,000 steps after the make. Flight: select body and site, ORBIT, wait for `14858(A6)` = 6, LAND.
- The hint sheet's "level N" is base D0 = N - 1 (inferred from Phoopel alone); the census covers missions 1..100.

## Waiting on Dave

- Leftover worktrees `agent-a528a4455254d699f` (uncommitted emulator edits) and `modest-dirac-449d9c`: keep or remove.
- Push: master is well ahead of origin (67 commits before this handoff's).
- Skill proposal (`reverse-engineer-st-game`, section 3): for position-independent code, resolve computed long calls
  (`move.l #imm` + `jsr d(PC,Rn.l)`) before any "no caller" claim; worked case Captive `$12b4c`, tool
  `reversing/captive/py/system/pcrel_calls.py`. Not edited: two other sessions were live on shared files.
- Blog: `IDEAS.md` entry 9 candidates from this session: the fire as a fuse along the dig tree, and the sealed key
  that leaves 27 bases unfinishable without a blind panel search.

## Next session

`/resume captive`. Start with Open 1 (does a mission need every target): it sets the weight of the sealed-key bug.
Open 2 and 3 are independent drives from existing snapshots and suit one agent each (`finish13.py`/`leave.py` and
`panel13.py` are the starting scripts). Do Open 6 here; it is a few REPL lines in `base13.snap`.

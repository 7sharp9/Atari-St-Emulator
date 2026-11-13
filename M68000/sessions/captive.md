# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `d44fc05` (every target needed; entrance blast; state 3 game over; all panels).

## Resume point

- Last commit of this workstream: `d44fc05` captive: state 3 game over, end-message table, every key and door kind
  (`0efae1d` every target needed, entrance blast).
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` (README
  "Provenance"). Generator captures `mapgen_full/` (`py/mapgen/full/README.md` rebuilds them byte-identical).
  Sealed-key and panel work `phoopel/` (`base13.snap`, `panel_*.snap/png`, `finish_base1_*`, `finish_m1_100.txt`,
  `sealed_m1_100.txt`); `phoopel/revisit/exited.snap` (3M steps after a real exit of the natural base, rebuild still
  running; `revisit.py exit` remakes it); `phoopel/state3/pre3.snap` (one instruction before state 3, `state3.py
  reach` remakes it); `phoopel/panels/lock<N>/` (per-lock snapshots and renders, `panels.py` remakes them). Agent
  reports `agents/{state3,panels}/report.md`. Lift and footprint states `agents/ai/lift/`, `agents/ai/footchase/` (rebuilt by the commands
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
  "The panel in play", `py/phoopel/panel13.py`).
- Every key kind (1, 3, 8, 16 switches; 2, 8, 256, 65,536 settings) and door kind (sliding door, plain wall, flames):
  code opens 8/8, last-bit-wrong control 8/8 shut, walk 8/8 vs 0/8; with byte +8 bit 4 the door shuts again on any
  mismatch 5/5, without it stays open 3/3 (`mapgen.md` "The panel in play", `py/phoopel/panels/`).
- State 3 (fire at the entrance) is a game over in the same frame, wherever the party is: `$134b8` 79,656 steps after
  the write, no leave test runs; a click restarts at MISSION 0001 via `$8570`. End-message table for `14800` -2..4
  (`ai.md` "Finishing a base", "Trill and leaving a base", `py/phoopel/state3/`).
- Finishing a base: EXPLOSIVES on a generator tile, `13410(A6)` 0 -> 1 -> 2 -> 3, 9/9 generators to flame, the fire
  follows the dig arrows 21/21 to the entrance; an untouched base cannot be left (`$87d6` 0 hits), in state 2 the
  entrance click marks the target visited 0 -> 1 (`ai.md` "Finishing a base", `py/phoopel/finish13.py`, `leave.py`).
- Sealed bases: 100 of 24,603 keys in 92 bases (missions 1..100); in 27 of the 92 every generator is behind a sealed
  door, 18 of those with a 16-segment lock (`mapgen.md` "Sealed keys", `py/phoopel/finish.py 0 100`, model).
- A chase that reads footprints: 8/8 trail moves follow bits 3-5, model replay 5/5 against 2/5 from bits 0-2
  (`ai.md` "The trail", `py/ai/footchase.py`).
- Lift: a ride writes no footprint (0/2048, writers 0 hits); a follower forgets only at a lift end holding 4 or 5
  (4/4 at (24,3)) and loiters; at a value-0 end it never forgets (15/15) (`ai.md` "The trail", `py/ai/lift/`).
- A mission needs every target: the station wants `14794(A6)` > 9, a count of target-base exits; a visited target
  lands in mode 2 (D2 = 6) and cannot be entered, `$bd84` 0 vs 1 in the control; the exit sets byte 2 bit 1 live
  (`world.md` "A target is finished once", `py/phoopel/revisit.py exit|land`). So 24 sealed ordinary targets block 23
  of 100 missions without a blind panel search (`mapgen.md` "Sealed keys").
- After an exit, state 4 explodes the entrance every 8 frames: a party left on it dies (4 droid deaths, "DROID'S HAVE
  FAILED"), one that reopens the door by code and walks 4 cells out loses none (`ai.md` "Finishing a base",
  `revisit.py blast`).
- Universe, AI decision rule 3000/3000, regroup 2000/2000, doors and the DIE, four infographics: as before
  (`world.md`, `ai.md`, `py/infographics/README.md`).

## Running

Nothing running.

## Open, in priority order

1. The station landing driven: select slot 0 on the map with `14794` = 9 and 10 (labelled poke) and LAND; expect
   request 4 only with 10 (`$2f66e`, read). Needs the station's map position (`universe.py`). The last unproven link
   in "a mission needs every target".
2. A lift follower reached by play alone (both runs start from a poked party cell; the lift agent reports group 49
   holding the corridor in `req4.snap`, not re-checked); the pair (2,4)-(18,4); tiles `$30`/`$33` (`$9768`/`$977c`).
3. What gives the party a `$66` MESSAGE FROM RATT with word 1 (`$26946` via `$23f64`); `14800` values 2 and -2 driven
   to their screens (table read in `ai.md`).
4. The `$c194` item branch live: drop a FLAMBOS or BATTERY on a `$26` cell and read byte 2 (from reading: `$3c`).
5. Panels: the `cmp.w #5,D0` branch at `$12a7e`/`$12a92` (near/far draw?); `$c420`'s full body; whether the gold
   word (r & `$3ff`) + `$80` is the amount; the end screen's 1.8M-step click delay.
6. The six `15538(A6)` tests on an uncracked copy (`system.md` 7; needs READ TRACK `$e0`). `cold_watch.sh b514 12` not
   re-run from the promoted location.

## Known traps

- The party word reads (0,0) and `13410` 0 for several million steps after an exit, while `$90be` rebuilds the
  compound; read them after the rebuild (30M steps on: `13410` = 4, party on the entrance).
- A party left on the compound entrance after an exit dies about 13M steps later (state-4 blast); a drive that waits
  there reads "DROID'S HAVE FAILED" and a stopped level loop (`$bd6a` 0 hits). Open the door by its code and walk off.
- A panel with a creature on the cell in front of it cannot be driven by a party poke there (locks 3, 6, 12 of
  `base13.snap`); a creature can also stand in an opened doorway for over 1.5M steps (lock 18): wait on the
  occupancy bit 7, as `panels.py` does.
- Panel W took switch clicks from (5,9) facing N with its cover shut and nothing drawn (`$dd96` sends any facing
  with (tile - facing) & 3 != 0 to the switch handler); it is drawn only from the cell it faces. Render the view
  before calling a click drive proven.
- The leave click needs the party on the entrance cell facing N; `base1/in.snap` faces S, so an unpoked control hits
  nothing at all (`leave.py <snap> poke`).
- A poked request-word base (`base13.snap`, `req4.snap`) has no compound and no target: do leave and visited tests in
  `base1/in.snap`.
- Print a stretch of `federation.asm` with `tools/disassemble.py --snap <snap> --linear <addr> <n>` or a numeric
  address filter: an `awk '/$a:/,/$b:/'` range whose end is not an instruction start prints the rest of the file.
- The end screen `$134b8` ignores a click for over a million steps (a click 150k steps in never registered,
  `state3.py leave`); a drive past it holds the click later or waits on `$13624`.
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

- Leftover worktree `agent-a528a4455254d699f` (uncommitted edits to `68k.fs`, `MMU.fs`, `Program.fs`, `run.ps1`,
  `DEVELOPING.md`): keep or remove. `modest-dirac-449d9c` is gone.
- Push: master is 79 commits ahead of origin.
- Skill proposal (`reverse-engineer-st-game`, section 3): for position-independent code, resolve computed long calls
  (`move.l #imm` + `jsr d(PC,Rn.l)`) before any "no caller" claim; worked case Captive `$12b4c`, tool
  `reversing/captive/py/system/pcrel_calls.py`. Not edited: two other sessions were live on shared files.
- Blog: `IDEAS.md` entry 9 candidates from this session: the fire as a fuse along the dig tree, and the sealed key
  that leaves 23 of 100 missions unwinnable without a blind panel search, and the base that blows up its own
  entrance behind the party.

## Next session

`/resume captive`. The sealed-key work is complete except Open 1 (the station landing, a short drive with one
labelled poke). After it, the workstream is at a natural end: decide with Dave whether Captive continues (Open 2-6
are small) or the blog figures in "Waiting on Dave" come first.

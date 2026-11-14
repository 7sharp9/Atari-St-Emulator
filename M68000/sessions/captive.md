# Captive: handoff

Updated 2026-11-14 by the session that ended at commit `7d6e655` (Open 1 closed: final-base survival and Trill's rescue).

## Resume point

- Last commit of this workstream: `7d6e655` captive: the lock count is the generator module's 13270; Trill and group
  78 pictures (after `d378f4e` survival and `595d228` the rescue).
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` (README
  "Provenance"). Final-base runs: `station/` (`survive*.log`, `guard.log`, `survive/` renders) and `station/trill/`
  (leg snapshots and renders). Generator captures `mapgen_full/`. Older per-area outputs and agent reports as before
  (`items/`, `ratt/`, `phoopel/panel2/`, `agents/*/report.md`).
- Start from: `station/fin_safe.snap` (final base, party at (53,1), safe; rebuild with `py/world/station/survive.py
  save`), `station/trill/l2.snap` (just off the floor-1 lift at (45,1)), `station/trill/p2.snap` (beside the opened
  vault), `base1/in.snap`, `base1/outside.snap`, `phoopel/base13.snap`, `agents/ai/req4.snap`, `mission1.snap` (no
  sidecar: pass `--disk-a scratchpad/captive/tmb097.st`).
- Uncommitted work left behind: none.

## Proven so far

Detail and commands in the topic docs; scripts under `reversing/captive/py/<area>/` with README tables.

- Final base survival: the killer is a `$25d88` wanderer placed at (56,3) not hostile (record identical to the
  generator's, `gencheck.py`); the view draws it beside the party (`$d390` from `$a92a`) and it turns hostile; one
  forward step within about 1.0-1.5M steps of the view saves the party: 9/9 forward arms survive 40M, 12/12 others
  die (`world.md` section 1 "Final target", `py/world/station/survive.py`, `guard.py`).
- Trill's rescue in the generated final base: one labelled party poke beside the vault, the code-0 door by its corner
  clicks, a step beside Trill gives `$10eec`, `$87d6`, `$8804`, `$8814`, `$134b8` once each, mission 0 -> 1; Trill
  never moves (30M-step control) (`ai.md` "Trill and leaving a base", `py/world/station/trill.py`).
- The walk from the entrance dies at the floor-1 lift arrival: group 78 (hit points 10,440) turns hostile on arrival;
  the hand keys `$06`-`$0d` leave its hit points unchanged against a no-key control (`fight.py`).
- Whole base generator in Python 400/400; locks, keys, panels, sealed bases; station landing and request 4; Ratt
  notes; end screens -2..4; flames recharge; panel live only in front; gold stacks: as before (`mapgen.md`,
  `world.md`, `ai.md`).

## Running

Nothing running.

## Open, in priority order

1. Trill reached by walking from the entrance (no pokes): a route that keeps groups out of view, since the mission-1
   party cannot hurt them. Needs a model of which cells the view draws (`$a92a` callers of `$d390`) and group
   positions per step; drive with `trill.py` legs from `station/trill/l1.snap`, waiting on floor 1 until group 78 is out
   of the arrival's view. Success: `14800` = -1 with no poke after the station landing's labelled `14794`.
2. What the hand keys do: `$8912` -> `338(A6)` counters -> `$b16e`; read `$b16e`, then a hand key against a
   mission-1 base group with known hit points (a `base1/in.snap` group), with a no-key control.
3. A lift follower by play (`ai.md` Open): open door (14,2) before group 16 has seen the party (fresh from
   `agents/ai/req4.snap`), or lure group 49; then the forget at a value-4/5 lift end vs value 0.
4. Small: 34 prize-cell GOLD items for 24 locks (`items.py`), the `72..87(A6)` door table, the inventory-screen click
   for the gold stack, word 2 note pickup at (19,2), `$906a` (down action).
5. The six `15538(A6)` tests on an uncracked copy (`system.md` 7; needs READ TRACK `$e0`).

## Known traps

- Federation keeps no lock count: `13270` in `mapgen.md` is the generator module's word; federation's `13270(A6)` is
  unrelated (18 in the final base). Walk `$1d782` records while byte 9 is `$20` (32 in the final base).
- Turn keys: `$67` sets facing + 1, `$69` facing - 1 (0 N, 1 W, 2 S, 3 E).
- A `run` that returns `max_steps` did not reach its `until_pc`: `survive.py`'s fork is `$b5c2` + 3M, still inside the
  generator; `$b5c6` comes within the next 2M.
- The final base: a key pressed during "LOADING ..." is buffered and taken later; the floor-1 lift (61,1) goes up to
  (45,1) (offset -16, 0), where group 78 waits.
- One `mouse move` sends at most ±127 per axis: split far pointer moves (`station.py` `goto()`).
- stserver watches survive `restore`: remove each (`watch_remove`); `watch_events` returns `[{id, events}]`.
- A click is consumed during the settle after `mouse down`: arm `run until_pc` before the down (`CLAUDE.md`).
- A party left on a compound entrance after an exit dies about 13M steps later (state-4 blast).
- A panel with a creature in front cannot be driven by a party poke there; wait on occupancy bit 7.
- The leave click needs the party on the entrance facing N; `base1/in.snap` faces S.
- The end screen `$134b8` ignores clicks for over a million steps (2.8M measured).
- `federation` calls far routines by `move.l #imm,Rn` / `jsr -8(PC,Rn.l)`: use `py/system/pcrel_calls.py`.
- Print a stretch of `federation.asm` with `tools/disassemble.py --snap <snap> --linear <addr> <n>`.
- Map pointer: three `mouse move -127 -127` pin it at (0,0). Lift icons (202,112) up, (251,112) down; panel
  switches from (90,98); view click (105,110) the cell ahead; coded-door corners at (71|135, 80|145).
- The hint sheet's "level N" is base D0 = N - 1 (inferred from Phoopel alone).

## Waiting on Dave

- Leftover worktree `agent-a528a4455254d699f` (uncommitted edits to `68k.fs`, `MMU.fs`, `Program.fs`, `run.ps1`,
  `DEVELOPING.md`): keep or remove.
- Push: master is ahead of origin (count in the handoff report).
- Skill proposal (`reverse-engineer-st-game`, section 3): resolve computed long calls (`move.l #imm` + `jsr
  d(PC,Rn.l)`) before any "no caller" claim; worked case `$12b4c`, tool `py/system/pcrel_calls.py`.
- CLAUDE.md proposal ("Emulator behaviours"): the ±127 `mouse move` clamp and stserver watches surviving `restore`.
- Blog (`IDEAS.md` entry 9): the fire as a fuse along the dig tree; the sealed key; the base that blows up its own
  entrance; the panel drawn live only from the cell in front; the final base whose wandering guard is made hostile
  by being seen, with a two-second window to step off the entrance.
- Whether Captive continues (Open 1 is a stealth-route project) or the blog figures come first.

## Next session

`/resume captive`. Open 1 of the previous handoff is closed. The remaining real item is the stealth walk (Open 1),
which needs a view-cell model before any drive; Open 2 (the hand keys) may make it a fight instead and is cheaper.
Decide with Dave first between those, a different game, or the blog figures.

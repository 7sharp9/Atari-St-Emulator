# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `473f748` (whole generator in Python, AI from the view and the
trail, DIE and lock, four infographics).

## Resume point

- Last commit of this workstream: `473f748` ANCHORS: captive mapgen_full captures, base30 feature views, infographic data.
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` (README
  "Provenance"). Generator captures `mapgen_full/` (`py/mapgen/full/README.md` rebuilds them byte-identical); stage
  dumps `mapgen_stages/dumps/`, digger captures `mapgen_digger/`. Infographic caches `infographics/data/`. Agent dirs and
  saved reports: `agents/{placement,shafts,chain,ai2,curios,info_*}/report.md` or `*.facts.md`.
- Start from: `base1/in.snap` (natural base, party at (30,0)), `agents/ai/g16_adj.snap` (group 16 beside the party),
  `agents/curios/base30.snap` (D0 = 30 base with every feature), `mg_ret.snap` (generator shortcut base),
  `mission1.snap` (no sidecar: pass `--disk-a scratchpad/captive/tmb097.st`).
- Uncommitted work left behind: none in this repo. `7sharp9.github.io/IDEAS.md` entry 9 has the Captive candidates
  added (that file is untracked in the blog repo).
- An old agent worktree `.claude/worktrees/agent-a528a4455254d699f` (uncommitted emulator edits) is not this
  workstream's; still waiting on Dave.

## Proven so far

Detail and commands in the topic docs; scripts under `reversing/captive/py/<area>/` with README tables.

- Whole base generator in Python from (D0, D2): 400/400 against the emulator's returned output, incl. D0 300..399;
  every stage gated 80/80 (or 1000/1000) with controls (`mapgen.md` "The pipeline", `py/mapgen/full/chain_run.py gate`).
- Locks and keys: keys on the entrance side 8,617/8,617, doors open in dig order (16,357 dependencies, 0 cycles)
  (`mapgen.md` "Locks and keys", `lockcensus.py`). Difficulty: only hit points scale with the mission (`groups.py`).
- Universe 51/51, 100/100, 150/150; grid lines at cells -1, 4, ..., 39 (`world.md` 1, `py/world/universe.py`).
- AI: decision rule 3000/3000 (two bases); seen-or-hit sets hostile and regroup at `$d390` (watch 17 vs 0);
  cr_Regroup 2000/2000; Trill's attack ends the base (`level_event.py`, `trill_attack.py`); footprints are travel
  directions forming a tree rooted at the party (`trailend.py`: 75 cells follow the party) (`ai.md`).
- Doors: lock census 24,576 presses = model, no per-corner feedback; DIE shows the next corner 1080/1080; table slip
  at code 9 (`ai.md` "Getting into a base", `py/infographics/gen_lock.py`).
- Feature tiles matched in play: hand door, floor trigger, trap plate, valve, spinners, false wall, wall pictures
  (`mapgen.md` "Feature and item stages").
- Four infographics, SVGs byte-identical from the promoted scripts (`py/infographics/README.md`).
- Earlier: trap #9 OS, volume block, Copylock and crack (`system.md`).

## Running

Nothing running. stserver pid 24995 (started 07:47 on 2026-11-13) predates this session and is not its.

## Open, in priority order

1. A natural chase that reads a footprint: no observed chase has (the group 16 chase read dig-tree arrows, then
   sight). Drive the party a few cells from an aware group, out of its row and column, then `track.py`, and show the
   group's trail step read a cell whose bits 3-5 differ from bits 0-2 (`trailend.py` lists them).
2. Lift escape: confirm live that riding a lift writes no footprint and that a following group forgets at the lift
   cell (`$9768`/`$977c`; `ai.md` "The trail", inferred). Needs a base with lifts (`req4.snap` has two).
3. Locks in play: what opens key-kind 0/1 locks (wall item `$22` at W is the candidate), door kind 1 (tile-0 door) and
   kind `$27`; items `$19`, `$1b`. Drive one lock in `base30.snap` from the lock list `13720(A6)`.
4. What gives the party a `$66` MESSAGE FROM RATT item with word 1 (`$26946` via `$23f64` in the compound builder,
   bsr/bra scan only); and `14800` values 1-3 (`$137b0`).
5. Promote the curios feature scripts (`view_tiles.py`, `step_diff.py`, `picwatch.py`, `base30.repl`, now in
   `scratchpad/captive/agents/curios/`) into `py/mapgen/` so `mapgen.md` "Feature and item stages" rests on repo scripts;
   point `gen_lock.py --emu`'s `HELPERS` at `py/ai`.
6. Infographic facts files quote mapgen.md headings that became bold labels ("The turtle", "Each step", "Failure and
   restarts", "Lift offsets"): repoint them.
7. What the six `15538(A6)` tests gate on an uncracked copy (`system.md` 7; needs READ TRACK `$e0`).
8. `cold_watch.sh b514 12` not re-run from the promoted location.

## Known traps

- `level_event.py` alone does not reach the compound entrance (22,22) after the exit: the ai2 agent's longer run did;
  `ai.md` does not cite it.
- `die_all.py`'s 2400 and 6400 are repeats (24 and 64 distinct conditions; `restore` resets the die LCG). Cite the
  1080/1080 census from `gen_lock.py` instead.
- `field.py` reports `loop` once the party has moved (its own cell keeps a stale arrow); use `trailend.py`, which stops
  at the party.
- Counting cells as open by tile != 0 includes decorated rock faces (tiles <= `$1a`); use tile > `$1a`.
- Map pointer: three `mouse move -127 -127` pin it at (0,0), then 1:1. Map pixel = (66,73) + 2 x cell; zoom out
  (202,114), in (251,114); ORBIT (202,72), LAND (251,70). Door corner zones: x 70 or 134, y 80 or 145.
- `track.py` samples every 60,000 steps (not a main frame in the natural base): use `sched.py` for timing; set
  `TRACK_OUT`.
- A poked request word 4 (`enter_base.repl`) builds a base with no compound.
- Menu key: release 30,000 steps after the make. Flight: select body and site, ORBIT, wait for `14858(A6)` = 6, LAND.

## Waiting on Dave

- The leftover worktree `agent-a528a4455254d699f` (uncommitted emulator edits, branch fully upstream): keep or remove.
- Push: master is 50 commits ahead of origin.
- Blog: `IDEAS.md` entry 9 now lists four drawn Captive figures and two undrawn (keys you can always reach, Trill's
  countdown); the file is untracked in the blog repo.

## Next session

`/resume captive`. Open 1 and 2 are live AI drives that settle the footprint story: run them as two agents from
`req4.snap` / `p2.snap` with `track.py` and `trailend.py`. Meanwhile do Open 5 and 6 here (promotion and facts-file
links), then Open 3 (drive one lock) if time allows. Draw "keys you can always reach" from `lockcensus.py` output.

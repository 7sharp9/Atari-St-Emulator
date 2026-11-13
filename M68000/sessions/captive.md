# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `5d18447` (infographics expanded; sealed keys, the Phoopel hint).

## Resume point

- Last commit of this workstream: `90adf0c` captive: sealed keys, the Phoopel hint (key on its own door cell)
  (then `bfb7ecb` skill lesson, `5d18447` ANCHORS row).
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` (README
  "Provenance"). Generator captures `mapgen_full/` (`py/mapgen/full/README.md` rebuilds them byte-identical); stage
  dumps `mapgen_stages/dumps/`, digger captures `mapgen_digger/`. Infographic caches `infographics/data/`. Sealed-key
  work `phoopel/` (`base13.snap` with sidecar, views, `sealed_m1_100.txt`, `keyondoor_m1_100.txt`). Agent dirs and
  saved reports: `agents/{placement,shafts,chain,ai2,curios,info_*}/report.md` or `*.facts.md`.
- Start from: `base1/in.snap` (natural base, party at (30,0)), `agents/ai/g16_adj.snap` (group 16 beside the party),
  `agents/curios/base30.snap` (D0 = 30 base with every feature), `phoopel/base13.snap` (D0 = 13, the sealed flame door
  at (7,9)), `mg_ret.snap` (generator shortcut base), `mission1.snap` (no sidecar: pass
  `--disk-a scratchpad/captive/tmb097.st`).
- Uncommitted work left behind: none.

## Proven so far

Detail and commands in the topic docs; scripts under `reversing/captive/py/<area>/` with README tables.

- Whole base generator in Python from (D0, D2): 400/400 against the emulator's returned output, incl. D0 300..399;
  every stage gated 80/80 (or 1000/1000) with controls (`mapgen.md` "The pipeline", `py/mapgen/full/chain_run.py gate`).
- Locks and keys: keys dug no later than their door 8,617/8,617, doors open in dig order (16,357 dependencies, 0
  cycles); 31 of them sealed on their own door cell (`mapgen.md` "Locks and keys", `lockcensus.py`).
- Sealed keys: the inclusive key test puts a key on its own door; D0 = 13 (PHOOPEL) lock 4's clipboard reads 15099,
  as the player hint sheet says; clipboard number `$12d4e` 301/301 (control 0/50); flame door blocks both ways;
  missions 1..100: 100 of 24,603 keys in 92 bases, 29 cut off a quarter of the base or more (`mapgen.md` "Sealed
  keys", `py/phoopel/`).
- Universe 51/51, 100/100, 150/150; grid lines at cells -1, 4, ..., 39 (`world.md` 1, `py/world/universe.py`).
- AI: decision rule 3000/3000 (two bases); seen-or-hit sets hostile and regroup at `$d390`; cr_Regroup 2000/2000;
  Trill's attack ends the base; footprints form a tree rooted at the party (`ai.md`).
- Doors: lock census 24,576 presses = model, DIE shows the next corner 1080/1080, table slip at code 9 (`ai.md`
  "Getting into a base").
- Four infographics, now with lead, per-panel reading guides and a "how we know" strip; every added sentence sourced
  in its facts file (`py/infographics/README.md`).
- Earlier: feature tiles in play, trap #9 OS, volume block, Copylock and crack (`mapgen.md`, `system.md`).

## Running

Nothing running.

## Open, in priority order

1. Can a sealed base be finished? In `phoopel/base13.snap`: drive the wall panel W at (5,8) (what it takes as input;
   does typing 15099 open the flame door), and try items `$5a`/`$1a` on the `$26` cell (`$c194` branch). Then what
   ends a base (Trill's attack) and whether it needs the cut-off half. Settles whether the bug blocks play.
2. A natural chase that reads a footprint: drive the party a few cells from an aware group, out of its row and column,
   `track.py`, and show a trail step reading a cell whose bits 3-5 differ from bits 0-2 (`trailend.py`).
3. Lift escape: confirm live that riding a lift writes no footprint and a following group forgets at the lift cell
   (`$9768`/`$977c`; `ai.md` "The trail", inferred). `req4.snap` has two lifts.
4. Locks in play beyond kind 2: key-kind 0/1 locks (W's `$22` wall object), door kind 1 (tile-0 door); items `$19`,
   `$1b`. Shares the driving method of Open 1.
5. What gives the party a `$66` MESSAGE FROM RATT with word 1 (`$26946` via `$23f64`); `14800` values 1-3 (`$137b0`).
6. Promote the curios feature scripts (`view_tiles.py`, `step_diff.py`, `picwatch.py`, `base30.repl`, in
   `scratchpad/captive/agents/curios/`) into `py/mapgen/`; point `gen_lock.py --emu`'s `HELPERS` at the repo.
7. `digger.facts.md` and `trail.facts.md` quote mapgen.md "The turtle", "Each step", "Failure and restarts", "Lift
   offsets", which are bold labels, not headings: repoint them.
8. The six `15538(A6)` tests on an uncracked copy (`system.md` 7; needs READ TRACK `$e0`). `cold_watch.sh b514 12` not
   re-run from the promoted location.

## Known traps

- `level_event.py` alone does not reach the compound entrance (22,22) after the exit: the ai2 agent's longer run did.
- `die_all.py`'s 2400 and 6400 are repeats (`restore` resets the die LCG): cite `gen_lock.py`'s 1080/1080.
- `field.py` reports `loop` once the party has moved; use `trailend.py`, which stops at the party.
- Counting cells as open by tile != 0 includes decorated rock faces (tiles <= `$1a`); use tile > `$1a`.
- Map pointer: three `mouse move -127 -127` pin it at (0,0), then 1:1. Map pixel = (66,73) + 2 x cell; zoom out
  (202,114), in (251,114); ORBIT (202,72), LAND (251,70). Door corner zones: x 70 or 134, y 80 or 145.
- `track.py` samples every 60,000 steps (not a main frame): use `sched.py` for timing; set `TRACK_OUT`.
- A poked request word 4 (`enter_base.repl`, `phoopel/enter13.repl`) builds a base with no compound.
- Menu key: release 30,000 steps after the make. Flight: select body and site, ORBIT, wait for `14858(A6)` = 6, LAND.
- The hint sheet's "level N" is base D0 = N - 1 (inferred from Phoopel alone); missions run to 65535, the census
  covers 1..100.

## Waiting on Dave

- The leftover worktree `agent-a528a4455254d699f` (uncommitted emulator edits, branch fully upstream): keep or remove.
- Push: master is 58 commits ahead of origin.
- Blog: `IDEAS.md` entry 9's undrawn "keys you can always reach" is now "keys sealed in their own door" (the Phoopel
  bug, `sealed.py` output); the file is untracked in the blog repo.

## Next session

`/resume captive`. Start with Open 1 from `phoopel/base13.snap`: drive W at (5,8) and the two items at the flame door;
that decides whether the sealed-key bug blocks a base. Run Open 2 and 3 (footprint and lift drives) as two agents
from `req4.snap` / `p2.snap` meanwhile, and do Open 6 and 7 here.

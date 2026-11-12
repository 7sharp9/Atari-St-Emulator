# Captive: handoff

Updated 2026-11-12 by the session that ended at commit `729e138` (four parallel agents: world, ai, mapgen, protect).

## Resume point

- Last commit of this workstream: `729e138` captive: base generator, creature AI, universe and renderer, OS and
  Copylock (plus a one-line `fedfs.py` label fix committed with this file).
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` from
  `The Medway Boys #97.zip` via `tools/msa2st.py` (README "Provenance"). Agent working dirs, reports and briefs:
  `scratchpad/captive/agents/{world,ai,mapgen,protect}/` (`BRIEF.md`, `<area>/report.md`).
- Start from: `mission1.snap` (planet screen, `drive.txt`), `ld_1.snap` (on the surface), or
  `agents/ai/req4.snap` (inside a base, entered by the labelled poke in `py/ai/enter_base.repl`). In-base states
  for AI work: `agents/ai/{p14,p2,door,g16_adj}.snap`; generator call: `mg_entry.snap`, `agents/ai/req4_mg.snap`.
- Uncommitted work left behind: none.

## Proven so far

Each line points at the topic doc section; scripts are under `reversing/captive/py/<area>/` with README tables.

- Universe from the mission number (one LCG): 51/51, 100/100, 150/150 for missions 0, 1, 7 (`world.md` section 1,
  `py/world/universe.py`).
- Base floor plan 1000/1000 seeds, lift pairing 510/510 cells, output deterministic, `$20054` shortcut reproduces
  the landing call (`mapgen.md`; `py/mapgen/zones.py`, `liftpair.py`, `cmp_ret.py`).
- Plane-2 arrows are the dig order, not a BFS: 43,832/43,832 (D2 = 0, D0 1..40) and 44,053/44,053 (D2 = 1)
  (`mapgen.md` "The flow field", `py/mapgen/flowfield.py`).
- Creature decision rule `$10304`: 3000/3000, broken-model control 2974/3000; natural breadcrumb chase observed;
  a group acts every period + 2 frames (`ai.md`, `py/ai/gate_decide.py`, `track.py`).
- Trap #9 OS: 33 functions, heap proven, volume block 31/31 (`system.md`, `py/system/trap9_table.py`,
  `heap_proof.py`, `volblock.py`).
- Copylock in `fed_MapGen` feeds only `15538(A6)`; the Medway crack's write at `$b514` caught by a cold watch at
  step 224,603,006 (`system.md` sections 5 and 6, `py/system/cold_watch.sh`).

## Running

Nothing running.

## Open, in priority order

1. In-game route into a base: `watch 1ef92 2` (request word `14788(A6)`) from `ld_1.snap` while walking the
   surface and using PLANET PROBE; proof is a natural snapshot at `$b5c2` with D2 = 0 and no poke. Unblocks
   every natural-play AI check.
2. Post-dig generator stages `$24f4c`-`$268f8` (objects, doors, creature placement): stage boundaries from
   `py/mapgen/stages.py`, then a Python port gated per stage against `stagedump.py` output over 40 seeds.
3. Python port of the digger `$244b6` (read, not yet gated): diff the carved grid against `basemap.py` over
   1000 seeds, plus a broken-model control.
4. What the six `15538(A6)` tests in `federation` gate on an uncracked copy: poke `$1f280` back to the
   non-crack value from `ld_1.snap`, drive into a base, compare. A real-disk check needs READ TRACK `$e0`
   modelled in the emulator (`system.md` section 7).
5. The regroup bit (group flag bit 2) setter: raw scan for writers of `5(An)` in group records, then a kill in
   `g16_adj.snap` to watch a formation reshuffle (`ai.md` "Formation").
6. Difficulty across missions: AI reads no mission word; dump group period, skill and hp from bases of
   missions 1, 5, 20 (`py/ai/dumplist.py`).
7. Not re-run from the promoted location: `py/system/trap9_log.py` (49 calls) and `cold_watch.sh 140 48` /
   `222 6`. Re-run once and record the counts in their README rows.

## Known traps

- stserver's `server/bin/Debug/net8.0/M68000.dll` predates the FDC Step fix `62219ec`, so a disk load under
  stserver fails (D0 = -1 at `$b7cc`, "PLEASE INSERT DISK" loop at `$b806`). Use the REPL for anything that loads
  a file. The "Project insights" session will rebuild `server/bin` and report whether `ld_1.snap` loads under it.
- Request word `14788(A6)` >= 4 sets mode 3, which calls `fed_MapGen` with D2 = 0 (a base), not D2 = 1.
- `ATARI_TRACE_GEMDOS=1` crashes the emulator in this game; use `ATARI_TRACE_OS=1` and `ATARI_TRACE_FDC=1`.
  A fix is in the "Project insights" emulator worktree; on merge, update README "What it needed from the emulator".
- Menu key: release 30,000 steps after the make (`drive.txt`). Flight: click the planet first, then ORBIT;
  pointer arithmetic for LAND/ORBIT is in `drive.txt`.

## Waiting on Dave

Nothing.

## Next session

`/resume captive`. Check whether `server/bin` has been rebuilt (`cmp` it against `bin/`); if so stserver can load
files again. Then work Open 1 from `ld_1.snap` with a `watch 1ef92 2`, and in parallel (agents, brief at
`scratchpad/captive/agents/BRIEF.md`) Open 2 and 3 on the generator.

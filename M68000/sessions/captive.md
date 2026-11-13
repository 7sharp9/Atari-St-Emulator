# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `c6ab4eb` (natural route into a base).

## Resume point

- Last commit of this workstream: `c6ab4eb` captive: base entered by play alone.
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` from
  `The Medway Boys #97.zip` via `tools/msa2st.py` (README "Provenance"). Agent working dirs, reports and briefs:
  `scratchpad/captive/agents/{world,ai,mapgen,protect}/` (`BRIEF.md`, `<area>/report.md`).
- Start from: `base1/in.snap` (inside the mission 1, target 1 base, reached by play; rebuild with
  `py/ai/natural_base.repl`, README row in `py/ai/`), `base1/outside.snap` (the compound), `mission1.snap` (planet
  screen; no sidecar, pass `--disk-a scratchpad/captive/tmb097.st`), `ld_1.snap` (plain landing surface). The poked
  base states `agents/ai/{req4,p14,p2,door,g16_adj}.snap` are still where the AI gates were measured.
- `server/bin`'s DLL equals `bin/`'s (cmp), so stserver loads files again; the stserver MCP `load` still needs
  `disk` passed explicitly.
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
- Base entered by play alone: map site (object bytes 0, 1), LAND writes request 1 at `$2f61a`, compound (D2 = 2),
  door combination lock `$e270` (code 8 = TL, BL, TR, BR; wrong order cleared), entrance cell `$bd84`, base D2 = 0;
  two runs byte-identical (`ai.md` "Getting into a base", `world.md` "Targets and landing seeds",
  `py/ai/natural_base.repl`).
- Copylock in `fed_MapGen` feeds only `15538(A6)`; the Medway crack's write at `$b514` caught by a cold watch at
  step 224,603,006 (`system.md` sections 5 and 6, `py/system/cold_watch.sh`).

## Running

Nothing running.

## Open, in priority order

1. Post-dig generator stages `$24f4c`-`$268f8` (objects, doors, creature placement): stage boundaries from
   `py/mapgen/stages.py`, then a Python port gated per stage against `stagedump.py` output over 40 seeds. The
   compound door list at `2330(A6)` (cell word, state word with the corner code in bits 4-8) is one of their outputs:
   find its writer.
2. Python port of the digger `$244b6` (read, not yet gated): diff the carved grid against `basemap.py` over
   1000 seeds, plus a broken-model control.
3. Re-run the AI gates in the natural base: `gate_decide.py`/`track.py` from a state made from `base1/in.snap`
   (find a group near the party with `dumplist.py`); same counts expected, since the base layout depends on D0 alone.
4. Where the player learns a door's corner code (a clue object, a terminal, or trial): scan RAM text in the
   compound and base for the code's appearance; `$e270`'s list is filled by the generator.
5. What the six `15538(A6)` tests in `federation` gate on an uncracked copy: poke `$1f280` back to the
   non-crack value from `ld_1.snap`, drive into a base, compare. A real-disk check needs READ TRACK `$e0`
   modelled in the emulator (`system.md` section 7).
6. The regroup bit (group flag bit 2) setter: raw scan for writers of `5(An)` in group records, then a kill in
   `g16_adj.snap` to watch a formation reshuffle (`ai.md` "Formation").
7. Difficulty across missions: AI reads no mission word; dump group period, skill and hp from bases of
   missions 1, 5, 20 (`py/ai/dumplist.py`).
8. Not re-run from the promoted location: `py/system/trap9_log.py` (49 calls) and `cold_watch.sh 140 48` /
   `222 6`. Re-run once and record the counts in their README rows.

## Known traps

- A snapshot without a `.prov.json` sidecar (`mission1.snap`) resumes with no disk: LAND then shows "PLEASE INSERT
  DISK CAPTIVE.DISK1" and every later `u` gives up. Pass `--disk-a`.
- Map pointer: three `mouse move -127 -127` pin it at (0,0), then moves are 1:1 screen pixels. Map pixel of a body =
  (66,73) + 2 x cell; ladder icons zoom out (202,114) and in (251,114); ORBIT (202,72), LAND (251,70). Door corner
  zones in the view: x 70 or 134, y 80 or 145.
- A poked request word 4 with `14782(A6)` nonzero (`enter_base.repl`) builds a base with D2 = 0 and no compound;
  natural play writes request 4 only at the station, where `$b5a0` makes it D2 = 1.
- `ATARI_TRACE_GEMDOS=1` used to crash the emulator in this game; the tracer fix is in `0c44c77` but not re-run
  here. `ATARI_TRACE_OS=1` and `ATARI_TRACE_FDC=1` are known to work.
- Menu key: release 30,000 steps after the make (`drive.txt`). Flight: select the body (and its landing site for a
  target), then ORBIT, wait for ship state `14858(A6)` = 6 (27.4M steps from the station to planet 1), then LAND.

## Waiting on Dave

Nothing.

## Next session

`/resume captive`. Run Open 1 and 2 as parallel agents; first refresh `scratchpad/captive/agents/BRIEF.md` (it still
says the README is the only committed doc and gives the poked base as the only way in: point it at the four topic
docs and `base1/`). Meanwhile do Open 3 here from `base1/in.snap`.

# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `920106b` (generator stages and digger ported, AI re-gated in
the natural base).

## Resume point

- Last commit of this workstream: `920106b` ANCHORS: captive generator stage dumps and digger captures.
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` from
  `The Medway Boys #97.zip` via `tools/msa2st.py` (README "Provenance"). Generator dumps:
  `mapgen_stages/dumps/` (`py/mapgen/stages/dumpall.py`), digger captures `mapgen_digger/*.bin`
  (`py/mapgen/digger/dig_capture.py`). Agent dirs and reports: `agents/{world,ai,mapgen,protect,stages,digger}/`
  (`BRIEF.md` refreshed this session, `<area>/report.md`).
- Start from: `base1/in.snap` (inside the mission 1, target 1 base, reached by play), `base1/outside.snap` (the
  compound), `base1/land_mg.snap` (the compound `fed_MapGen` call), `mg_ret.snap` (generator shortcut base),
  `mission1.snap` (no sidecar: pass `--disk-a scratchpad/captive/tmb097.st`).
- `server/bin`'s DLL equals `bin/`'s (cmp), so stock stserver loads from disk; `STSERVER_DLL` is not needed.
- Uncommitted work left behind: none. An old agent worktree `.claude/worktrees/agent-a528a4455254d699f` holds
  uncommitted emulator edits (`68k.fs`, `MMU.fs`, `Program.fs`, `DEVELOPING.md`, `run.ps1`); not this workstream's,
  left for Dave.

## Proven so far

Each line points at the topic doc section; scripts are under `reversing/captive/py/<area>/` with README tables.

- Universe from the mission number: 51/51, 100/100, 150/150 (`world.md` section 1, `py/world/universe.py`).
- Floor plan 1000/1000, lift pairing 510/510, flow field 43,832/43,832 and 44,053/44,053 (`mapgen.md` "Floors and
  lifts", "The flow field"; `py/mapgen/`).
- Digger `$244b6` ported byte-exact: 1000/1000 (D2 = 1), 100/100 (D2 = 0), controls 0, 0, 24 of 1000; rooms
  ((s&7)+2) x (((s>>3)&7)+2) 25,771/25,771; blobs, pre-placed shafts, loop census 819/1000 forests with rooms and
  blobs contracted (`mapgen.md` "The digger and rooms", `py/mapgen/digger/`).
- 17 post-dig stage calls ported, each 80/80 with controls; coded-door list written by `$23e80` via `$24298`
  (natural watch, 357/357, 317/317) (`mapgen.md` "After the flow field", `py/mapgen/stages/`).
- Creature decision rule `$10304`: 3000/3000 in the poked and the natural base, controls 2974 and 2975; scheduler
  2400/2400 group-frames, main frame load-dependent (median 72,000 steps in the base) (`ai.md` "Scheduling",
  `py/ai/gate_decide.py`, `sched.py`).
- Base entered by play alone; door combination lock `$e270` (`ai.md` "Getting into a base", `natural_base.repl`).
- Trap #9 OS (33 functions, heap, volume block 31/31); trap #9 log re-run byte-identical, 48 calls; Copylock feeds
  only `15538(A6)`; crack writers re-run (`system.md`, `py/system/`).

## Running

Nothing running.

## Open, in priority order

1. Creature and object placement: `$25e08` (group writer), then `$25d88`, `$25c1e`, `$25722`, `$25414`, `$2543a` and
   the door stage `$2419a`. Port in `py/mapgen/stages/models.py`, gate with `stages/gate.py` (80/80 per stage) over
   the existing dumps; the group list is what `ai.md` reads at `4532(A6)`, so a gated port lets the AI be run on any
   base offline.
2. Shaft layout `$245e2`/`$24606`/`$2465e` and room reservations `$263c2`, then `$263fa` (reuses the digger's room
   builder): port and gate at `$23ca8`/`$23cb0` from `dig_capture.py`-style captures. With items 1 and 2 the whole
   base generator is in Python.
3. Where the player learns a door's corner code: the code is random per door (`mapgen.md` "Coded doors"), so scan
   RAM text and objects in the compound and base for the code or its corner order; else the answer is trial.
4. Feature and tile meanings (`$16`, `$24`-`$26`, `$30`-`$32`, `$2c` pictures): match each to the 3D view by
   rendering a cell holding it (`world.md` section 3, `tools/snap_render.py`).
5. Regroup bit (group byte 5 bit 2) setter: a static scan of federation found no `bset #2,5(An)` on a group record
   (writers at `$f64e`, `$f6ca`, `$107ae`, `$107c4`, `$10814` are other records); `watch` the group list across a
   kill in `g16_adj.snap` instead.
6. What the six `15538(A6)` tests gate on an uncracked copy (`system.md` section 7; needs READ TRACK `$e0`).
7. Difficulty across missions: dump group period, skill and hp from bases of missions 1, 5, 20 (`dumplist.py`), or
   from the placement port once item 1 lands.
8. `cold_watch.sh b514 12` not re-run from the promoted location.

## Known traps

- A snapshot without a `.prov.json` sidecar (`mission1.snap`) resumes with no disk: pass `--disk-a`.
- Map pointer: three `mouse move -127 -127` pin it at (0,0), then moves are 1:1. Map pixel of a body = (66,73) + 2 x
  cell; zoom out (202,114), in (251,114); ORBIT (202,72), LAND (251,70). Door corner zones: x 70 or 134, y 80 or 145.
- `track.py` samples every 60,000 steps, which is not a main frame in the natural base: use `sched.py` for timing.
  It writes `agents/ai/track_end.snap` unless `TRACK_OUT` is set.
- A poked request word 4 (`enter_base.repl`) builds a base with no compound; natural play writes request 4 only at
  the station.
- Menu key: release 30,000 steps after the make. Flight: select body and site, ORBIT, wait for `14858(A6)` = 6, LAND.

## Waiting on Dave

- The leftover worktree `agent-a528a4455254d699f` (uncommitted emulator edits, branch fully upstream): keep or remove.
- Push: master is 41+ commits ahead of origin.

## Next session

`/resume captive`. Run Open 1 as an agent (brief: `agents/BRIEF.md`, the stages report
`agents/stages/report.md` "Not finished", models in `py/mapgen/stages/`), and Open 2 as a second agent in
`py/mapgen/digger/`. Meanwhile do Open 4 here: render one cell per unexplained feature from a base snapshot.

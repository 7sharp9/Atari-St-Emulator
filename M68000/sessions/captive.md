# Captive: handoff

Updated 2026-11-13 by the session that ended at commit `1cde27b` (open items 1, 3, 4, 5 closed by five Sonnet agents, each count re-run by the parent).

## Resume point

- Last commit of this workstream: `1cde27b` captive: station landing writes request 4 only with 14794 = 10; Ratt
  notes picked up by click; -2 and 2 end screens; flames recharge items; panel live only in front; `$c420`; gold.
- Working data: `M68000/scratchpad/captive/` (rows in `scratchpad/ANCHORS.md`). Disk `tmb097.st` (README
  "Provenance"). Generator captures `mapgen_full/` (`py/mapgen/full/README.md`). Per-area outputs of the promoted
  scripts: `items/`, `ratt/`, `station/`, `phoopel/panel2/` (each script's README says which snapshot it writes and
  in what order). Agent reports of this pass: `agents/{landing,liftplay,ratt,itemdrop,panel2}/report.md`, with the
  parent's re-run logs in each `verify/`. Older reports `agents/{state3,panels,footprint,lift,...}/report.md`.
- Start from: `base1/in.snap` (natural base, party at the entrance facing S), `base1/outside.snap` (compound),
  `phoopel/base13.snap` (sealed flame door base), `phoopel/finish_base1_blast_state2.snap`, `phoopel/revisit/exited.snap`,
  `agents/ai/req4.snap`, `agents/curios/base30.snap` (every feature), `mission1.snap` (no sidecar: pass
  `--disk-a scratchpad/captive/tmb097.st`).
- Uncommitted work left behind: none.

## Proven so far

Detail and commands in the topic docs; scripts under `reversing/captive/py/<area>/` with README tables.

- Whole base generator in Python from (D0, D2): 400/400 (`mapgen.md` "The pipeline").
- Locks and keys, the panel, every key and door kind, sealed bases (23 of 100 missions need a blind panel search):
  `mapgen.md` "Locks and keys", "The panel in play", "Sealed keys".
- A mission needs every target, and the station landing closes it: request 4 and the final base (`$b5c2` D0 = 10,
  D2 = 1) only with `14794` = 10, none with 9 or 0 (`world.md` section 1 "Final target", `py/world/station/`).
- The final base loads (310 FDC reads, all OK) and places the party at (53,0) beside a hostile group that kills the
  four droids without input, `14800` = 1 (`world.md` "Final target", `station/death.py`, `fdc.py`).
- Ratt's notes are generator floor items, word 1 only in base D0 = 0's compound at (21,20), gated on D0 (`$23f48`):
  `$26946` 1 vs 0 with D0 = 1; picked up by a floor click, hand `00660001`, control 0 (`mapgen.md` "Feature and item
  stages", `ai.md` "Door hints", `py/ai/ratt/`).
- End screens -2 (by play, up icon on the pad after an exit; control 0) and 2 (labelled `13412` poke; control 0);
  table -2..4 complete (`ai.md` "Trill and leaving a base", `py/ai/ratt/`).
- FLAMBOS/BATTERY dropped into flames recharge to 60 shots (`$c1b0` 2 arms 1, 6 controls 0); ACID on `$1e` 50
  (`mapgen.md` "Sealed keys", `py/items/itemdrop.py`).
- Panel: live only in the cell in front (`$12a20` D0 = 6: 3/3 near, 0/14 far; state poke changes only the near
  render); `$c420` door toggle with 4 animation slots (open 1 call, control 0); gold word = amount, stacked by
  `$e7d0` (537, 1634, 2647, cap 65500/88) (`mapgen.md` "The panel in play", "Locks and keys", `py/phoopel/panel2/`).
- Finishing a base, state 3 and 4, footprint chase, lift, universe, AI rule, infographics: as before (`ai.md`,
  `world.md`, `py/infographics/README.md`).

## Running

Nothing running.

## Open, in priority order

1. Whether a party that moves off (53,0) survives the final base, and why a group stands beside its entrance: drive
   `station/death.py`'s arm with a step or turn right after the view comes up (~13M after LAND), `410` and `14800`
   against the unmoved arm. Then Trill in that base by play (value -1 or 2 without pokes).
2. A lift follower by play (`ai.md` Open): open door (14,2) before group 16 has seen the party (fresh from
   `agents/ai/req4.snap`), or lure group 49 and outrun it; then the forget at a value-4/5 lift end vs value 0.
   `agents/liftplay/auto.py` needs a did-the-party-move check first. Pair (2,4)-(18,4), tiles `$30`/`$33`.
3. Small: why 34 prize-cell GOLD items for 24 locks (`items.py`), the `72..87(A6)` door table (`$ca70`/`$ca08`), the
   inventory-screen click for the gold stack, word 2 note pickup at (19,2), `$906a` (down action).
4. The six `15538(A6)` tests on an uncracked copy (`system.md` 7; needs READ TRACK `$e0`).

## Known traps

- One `mouse move` sends at most ±127 per axis (a relative IKBD packet): a pointer target farther than 127 from the
  pinned corner needs split moves (`station.py` `goto()`); an unsplit ORBIT click registered nothing.
- stserver watches survive `restore`: an arm after a restore reports the earlier arm's watch events unless each is
  removed (`watch_remove`); `watch_events` returns `[{id, events}]`.
- The final base shows "LOADING ..." for about 12M steps after LAND: a render before ~13M is the load, not a stall.
- A party left on the compound entrance after an exit dies about 13M steps later (state-4 blast); open the door by
  its code and walk off. The party word reads (0,0) and `13410` 0 for millions of steps while `$90be` rebuilds.
- A panel with a creature in front cannot be driven by a party poke there (locks 3, 6, 12 of `base13.snap`); wait on
  occupancy bit 7 as `panels.py` does. Panel W takes switch clicks from a non-facing cell with nothing drawn: render
  the view before calling a click drive proven.
- The leave click needs the party on the entrance facing N; `base1/in.snap` faces S (`leave.py <snap> poke`).
- A poked request-word base (`base13.snap`, `req4.snap`) has no compound and no target: do leave and visited tests in
  `base1/in.snap`.
- The end screen `$134b8` ignores clicks for over a million steps (2.8M measured); hold the click later or wait on
  `$13624`.
- `federation` calls far routines by `move.l #imm,Rn` / `jsr -8(PC,Rn.l)`: use `py/system/pcrel_calls.py`. The Ratt
  notes' writers are in `fed_MapGen`, not in `federation.asm`.
- Print a stretch of `federation.asm` with `tools/disassemble.py --snap <snap> --linear <addr> <n>`.
- stserver reports watch-event addresses and values as `'$hex'` strings.
- Keys facing S (`g16_adj.snap`): `k68` forward, `k6e` back, `k6c`/`k6a` strafe W/E, `k69`/`k67` turn; 360k steps each.
- `track.py` samples every 60,000 steps (not a main frame): use `sched.py` or per-action stops.
- Map pointer: three `mouse move -127 -127` pin it at (0,0), then 1:1. Lift icons (202,112) up, (251,112) down;
  panel switches from (90,98). View click y 132..144 the cell ahead, y >= 150 the party's cell, y ~105 a throw.
- The hint sheet's "level N" is base D0 = N - 1 (inferred from Phoopel alone).

## Waiting on Dave

- Leftover worktree `agent-a528a4455254d699f` (uncommitted edits to `68k.fs`, `MMU.fs`, `Program.fs`, `run.ps1`,
  `DEVELOPING.md`): keep or remove.
- Push: master is 2 commits ahead of origin after this handoff.
- Skill proposal (`reverse-engineer-st-game`, section 3): resolve computed long calls (`move.l #imm` + `jsr
  d(PC,Rn.l)`) before any "no caller" claim; worked case `$12b4c`, tool `py/system/pcrel_calls.py`.
- CLAUDE.md proposal ("Emulator behaviours"): the ±127 `mouse move` clamp and stserver watches surviving `restore`
  (both in Known traps above; repo-wide, not Captive-specific).
- Blog (`IDEAS.md` entry 9): the fire as a fuse along the dig tree; the sealed key that leaves 23 of 100 missions
  unwinnable; the base that blows up its own entrance; the panel that is only drawn live from the cell in front.

## Next session

`/resume captive`. Open 1 is one short drive from `py/world/station/death.py`. After it the workstream is at a
natural end: decide with Dave whether Captive continues (Open 2 is the only real one left) or the blog figures
come first.

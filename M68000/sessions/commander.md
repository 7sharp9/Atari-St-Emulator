# Commander: handoff

Updated 2026-10-13 by the session that ended at commit `345a763`.

## Resume point

- Last commit of this workstream: `345a763` powermonger: digest, stuck men classified by A*; the executor takes any player order from any side's slot (work in `a57983b`).
- Working data: `M68000/scratchpad/cmd1/` (gitignored; every gate rebuilds its own outputs under `$CMD_WORK`). Agent reports from the fan-out: `scratchpad/cmd1/agents/{astar,observe,orders}/report.md`.
- Start from: `scratchpad/pm142/rand1.snap` (Play Random Land, side 1 local with two captains, AI sides 2..4 live).
- Uncommitted work left behind: none.

## Proven so far

All in `reversing/powermonger/commander/` (README "Design" and "Files"):

- Injection: a slot at state 2 silences a side's AI and takes injected orders, `gate_inject.sh` 7/7.
- Every player order works from an AI slot (posture, transfer, dismiss, drop food/equipment, spy, alliance, get food/men, invent, equip, trade, supply, attack), `gate_orders.sh` 57/57; the executor has no local-side test. Encodings: README order table.
- Terrain sampler port matches `$1648e` at 4128/4128 points (`gate_sampler.py`); A* over triangles (`astar.py`) gives a verified waypoint path for all 2417 stuck pairs with water on their line (`classify_stuck.py`); a waypoint is followed live where the control stays stuck (`live_check.py`).
- Observation JSON (`observe.py`): 1312/945/4051/56 against the older scripts (`gate_observe.py`), 380/380 against the game's panels (`gate_ui.py`). `act.py` reproduces the injection gate byte for byte; `step.py` runs one step, about 2.4 s per 10M steps.

## Open, in priority order

1. **Decision loop and scripted baseline** (README step 3): `step.py` in a loop, one decision per N ticks per group (orders from the README table, movement as one A* leg per order, re-issued at arrival), every decision logged with its clock so a run replays. Proof: a land played to a result (the `$57fce` ratio verdict, `$d2c8`) twice with identical logs and final snapshots (`cmp`). Needs mid-run pokes: `act.py` takes neighbour bytes from the input snapshot, so each step must start from a snapshot, or read the neighbours with `m` first.
2. **Order target cell to world point**: which world point the game derives from bytes 2/3 (cell centre or corner); A* waypoints are world points. Proof: inject a `$1a` supply at a known cell and read the lead's target words 20/22.
3. **Walker model disagreement**: `Map.simulate_walk` predicts arrival for 206 stuck pairs the game keeps stuck (121 on k143 side 4, prev mode `$14`). Needed before the walker is used as a cheap forecaster; check group hand-off `$14fa2` and followers first.
4. Ungated order cases: an alliance with no goods to pay tribute, an alliance aimed at the player's side (panel `$1a` via `$c706`), invent at a lord with a workshop, equip at a lord with goods, go `$02` and home `$0a`.
5. economy.md "The trade (`$63f4`)" says the food spent is added to the lord's food; one run saw lord food rewritten unchanged at `$64cc` when the sale covered the purchase (orders report). Settle from the code before editing the doc.

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply (REPL `w` writes a longword, a resumed snapshot may have no disk, `callcap` masks interrupts, group frames).

- A target can change sides while the group walks to it (`$3da4` then joins a spy to the new owner); the side is checked only at dispatch. Re-read the owner at arrival.
- After a man reaches a poked waypoint his job rewrites the target: one order per leg, re-issued.
- `stuck_census.py` counts men at their target and commuters as stuck; use `classify_stuck.py`'s type (b) for real shore cases.
- In `gate_orders.sh` the spy arrives at 39.55M of the 40M budget: lowering `BUDGET` fails its arrival rows.

## Next session

Build the decision loop with a scripted baseline commander for one side (Open 1), with replay
logging, and prove it with two identical runs of one land. Settle Open 2 on the way, since the
movement orders depend on it.

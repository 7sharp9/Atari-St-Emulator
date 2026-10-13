# Commander: handoff

Updated 2026-10-13 by the session that opened the workstream.

## Resume point

- Last commit of this workstream: the injection gate (`commander/gate_inject.sh`).
- Working data: `M68000/scratchpad/cmd1/` (gitignored).
- Start from: `scratchpad/pm142/rand1.snap` (Play Random Land, two player captains, AI sides live).
- Uncommitted work left behind: none.

## Proven so far

- **Injection interface** (`commander/gate_inject.sh`, 7/7; README "Action interface"): a side's slot `$58016 + 6*side` at state 2 silences its AI (0 slot writes in 30M steps against 3 unpoked); an order written there (bytes: side, type, x, y) acts for the group in `$58042[2*side]`, at once for group 0, by pigeon for the others (attack `$0c`: `$6c32`/`$4a7a`/`$4b80` 1 each).

## Open, in priority order

1. **A* reachability tool** (README step 2): terrain planes to a land graph; split the stuck men of
   `py/fsm/stuck_census.py` into unreachable and reachable-but-walker-fails.
2. **Observe/act harness with a scripted baseline** (step 3). Open question for it: whether the
   orders an AI side never issues (posture `$16`, spy `$20`, alliance `$1e`) work from a non-local
   slot; each needs its own arm like the gate's.

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply here (REPL `w` writes a longword, a resumed
snapshot may have no disk, `callcap` masks interrupts, group frames).

## Next session

Build the A* reachability tool (Open 1), then the harness.

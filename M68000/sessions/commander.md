# Commander: handoff

Updated 2026-10-13 by the session that opened the workstream.

## Resume point

- Last commit of this workstream: the one adding this file and `reversing/powermonger/commander/README.md`.
- Working data: `M68000/scratchpad/cmd1/` (gitignored).
- Start from: `scratchpad/pm142/rand1.snap` (Play Random Land, two player captains, AI sides live).
- Uncommitted work left behind: none.

## Proven so far

Nothing yet. The design and plan are in `reversing/powermonger/commander/README.md`.

## Open, in priority order

1. **Injection gate** (README step 1): an order written into a state-2 slot of an AI side runs like
   a natural order and `$6522` stops issuing for that side. Same-snapshot control at state 4.
2. **A* reachability tool** (step 2).
3. **Observe/act harness with a scripted baseline** (step 3).

## Known traps

The PowerMonger traps in `sessions/powermonger.md` apply here (REPL `w` writes a longword, a resumed
snapshot may have no disk, `callcap` masks interrupts, group frames).

## Next session

Run the injection gate from `pm142/rand1.snap`, then start the A* tool.

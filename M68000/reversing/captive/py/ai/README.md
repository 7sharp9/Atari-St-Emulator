# Captive creature AI scripts

Scripts behind `reversing/captive/ai.md`. Run from `M68000/` with `uv run python -I reversing/captive/py/ai/<script>`.
Each finds the repo root by walking up to `tools/rdis.py` (or `M68000_ROOT`) and drives `stserver` through
`tools/stclient.py`. Snapshots are working data under `scratchpad/captive/agents/ai/` (not committed): make
`req4.snap` with `enter_base.repl`, then `p2.snap` with the two `keys.py`/`click.py` steps in the last rows.

stserver's own core DLL (`server/bin/Debug/net8.0/M68000.dll`) must include the FDC Step-in/Step-out fix for
anything that loads from disk (entering a level). A build without it fails the game's file load (D0 = -1 at `$b7cc`,
then the "PLEASE INSERT DISK" loop at `$b806`), so `enter_base.repl` runs in the REPL. The scripts below only run
inside a level already in RAM.

| script | what it proves | command | expected output |
|---|---|---|---|
| `enter_base.repl` | a base is built and entered by a labelled poke of the request word `14788(A6)` = 4 | `ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/captive/ld_1.snap repl < reversing/captive/py/ai/enter_base.repl` | stops at `$b5c2` after 798,539 steps with D2 = 0, A0 = `$1d9e8`; `$b5c6` reached 3,254,901 steps later, D0 = 3; writes `req4_mg.snap`, `req4.snap` (a re-run gives a byte-identical `req4.snap`) |
| `natural_base.repl` | a base entered by play alone: target 1's site, ORBIT, LAND, the compound door's corner code, the entrance cell | `ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/captive/mission1.snap repl --disk-a scratchpad/captive/tmb097.st < reversing/captive/py/ai/natural_base.repl` (make `scratchpad/captive/base1/` first) | `$b5c2` with D0 = 0, D1 = 0, D2 = 2, return D0 = `$30` after 873,002 steps; `$b5c2` with D2 = 0, return D0 = 3 after 3,590,553 steps; `base1/in.snap` has the party at (30,0), mode 3; two runs byte-identical |
| `gate_decide.py` | the decision rule at the head of `$10304` (model in the file) | `gate_decide.py scratchpad/captive/agents/ai/p2.snap 3000 2` | `3000/3000 match`; by label WANDER 1231, TURN 659, FORWARD 422, BEHIND_TURN 257, FORGET 202, SPECIAL 95, ATTACK 68, TURN_ATTACK 66 |
| `gate_decide.py` (natural base) | the same rule in a base reached by play (`natural_base.repl`), whose plane 2 differs | `gate_decide.py scratchpad/captive/base1/in.snap 3000 2` | `3000/3000 match`; WANDER 1231, TURN 666, FORWARD 415, BEHIND_TURN 257, FORGET 202, SPECIAL 95, ATTACK 68, TURN_ATTACK 66; the control below gives `2975/3000` |
| `sched.py` | the scheduler `$102a0`: a group thinks iff timer > period at frame start; the timer left after a think is 0 or period / 2; the main frame's length in steps | `sched.py scratchpad/captive/base1/in.snap 100` | `2400/2400 group-frames match`; main frame steps min 68793, median 72000, max 87207; group 1 intervals all 7, timer after think 4 |
| (control) | the gate discriminates | the same with the model's `dy > 6` changed to `dy > 5` and `rng <= 0x31e0` to `rng < 0x31e0` | `2974/3000 match` |
| `track.py` | scheduling (period + 2 frames) and a natural chase along the trail | `track.py scratchpad/captive/agents/ai/p2.snap 200 7` | group 16 moves at frames 4, 22, 40, 58, 76: (13,4) N to (13,3), turns E, E to (14,3), turns S, S to (14,4); writes `agents/ai/track_end.snap` (kept as `g16_adj.snap`), replacing any earlier one unless `TRACK_OUT=<path>` is set |
| `field.py` | plane 2's generated field drains into the lift cells | `field.py scratchpad/captive/agents/ai/req4.snap` | ends (24,3) value 5: 449, (2,4) value 4: 11, (12,0) edge: 74; max path 68 |
| `field.py ... trail` | the same over bits 3-5 (what creatures read), after the party moved | `field.py scratchpad/captive/agents/ai/req4.snap trail` | (24,3): 433, (2,4): 10, (12,0): 75 |
| `walk.py` | the party writes its step direction into bits 3-5 of the cell it leaves | `walk.py scratchpad/captive/agents/ai/req4.snap <out.snap> 6a,6a,68` | party (13,0), (14,0), (14,1); plane-2 writers besides the seen marks at `$86a0`/`$86ae`/`$86bc`/`$86ca`: `$9332`/`$9336` (breadcrumb, values `$80`/`$81`/`$98`/`$99`/`$91`) and `$86d8` (the fifth seen mark, the cell above, only once the party has left row 0) |
| `dumplist.py` | group list layout | `dumplist.py scratchpad/captive/agents/ai/req4.snap` | 63 records, last `$1d11a` size 56, end at `$1d152` |
| `grid.py` | map and plane-2 views (`walk`, `tile`, `p2dir`, `p2lo`, `p2hi`, `occ`) | `grid.py scratchpad/captive/agents/ai/p2.snap p2dir` | 32 rows of arrows, `@` = party |
| `keys.py` | keypad drive (`$68` forward, `$67`/`$69` turn, `$6a`/`$6c` strafe) | `keys.py scratchpad/captive/agents/ai/req4.snap scratchpad/captive/agents/ai/p14.snap 6a,6a,68` | party (13,0), (14,0), (14,1) |
| `click.py` | opening the door ahead by clicking the view | `click.py scratchpad/captive/agents/ai/p14.snap scratchpad/captive/agents/ai/door.snap 105 110`, then `keys.py .../door.snap .../p2.snap 68,68,68,68` | party walks (14,2) to (14,5) |
| `cap.py` | shared helpers | - | - |

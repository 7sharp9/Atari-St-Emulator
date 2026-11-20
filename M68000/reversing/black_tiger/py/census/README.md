# py/census: which code each Black Tiger level runs

Run from `M68000/`. Both scripts drive `tools/code_census.py` (`DEVELOPING.md`, "Other tools") and write under
`scratchpad/black_tiger/census/` (`BT_WORK` override). The result and its reading are in `../../README.md`,
"Code each level adds".

| script | what it does | expected output | runtime |
|---|---|---|---|
| `run_levels.sh [jobs=6] [walk=30] [idle=10] [boss=10]` | 24 runs, one directory each: `L<k>_walk` (30 chunks of `walk.txt`) and `L<k>_idle` (10 of `idle.txt`) from `play_start.snap` (k = 0) or `agents/systems/lvl<k>.snap`, and `B<k>_walk` (10 of `walk.txt`) from `boss/boss<k>_fight.snap`; stops a run if `$17846` (level index) changes | 24 lines `rc=0`, each run's last read the same level index it started on | about 2 min at `-P 6` |
| `report_levels.sh` | first makes the `D0_timeout` control if it is missing (5 chunks of `timeout.txt`: level 0 with TIME poked to 5, so the death and retry path is in the base), then reports every level against level index 0 over `$a2fc..$1f274` | L0 11,610 bytes run, union 14,266; 37 spans, 2,630 bytes not run in L0 | about 30 s |

The fragments are REPL text run once per 1M-step chunk. **Labelled pokes**: every fragment writes lives `$1f00c = 5` first, so
no run reaches game over (which would fall into the attract demo and mix level 0's code into every run); `timeout.txt` also
writes TIME `$1eedc = 5`. `walk.txt` cycles joystick 1 right+fire, up+fire, right+fire, up+right+fire, left+fire; it moves the
hero but follows no route, so each run covers the start of its level and, for `B<k>`, the boss arena.

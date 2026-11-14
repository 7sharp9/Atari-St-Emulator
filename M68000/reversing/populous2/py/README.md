# populous2 scripts

Run from `M68000/` with `uv run python reversing/populous2/py/<script> ...`. Inputs are the
anchors under `scratchpad/populous2/anchors/` (`scratchpad/ANCHORS.md`; rebuilt by `../drive.txt`).

| script | what it proves or does | result |
|---|---|---|
| `corners.py <snap> [--callcap]` | corner heights implied by the 4-byte cell records at `$3979e`; Populous 1's cell derivation without the shore rule; `$1f176` under callcap | `p2_game_start`: 4225/4225 shared corners, 4071/4071 cells (control 3334), 915/915 callcaps (control 357); `p2_game_60m`: 4055/4055, 920/920 |
| `find_corner_grid.py <snap> [--control]` | no separate 65x65 corner grid in RAM | best real candidate 2875/4086 (all-sea baseline); planted grid 4071 |
| `rand_gate.py <snap> [n]` | `rand` `$215dc` model (32-bit LCG `$bb40e62d`, seed `$47382`) | 50/50; control without the zero-seed rule 49/50 |
| `fdc_files.py <st> <fdc.log>` | file and DMA address behind every FDC sector read | 11 of 13 game files at their table address |
| `walkers.py <snap> [--dump]` | object heap (`$3f42a` scenery, `$3ff1a` entities, `$4505a`, `$46f9a`): every live record in exactly one occupant list, its own cell's (cell word 2, links +2/+4 signed from `$3ff1a`) | `p2_game_start` 22/22, `p2_game_60m` 31/31, 0 list faults; control (cell from bytes 7/9) 22 and 31 lists broken |
| `entity_states.sh [outdir]` | `hits` on `update_entities` `$2309a` and its state handlers over 2.4M steps from `p2_game_60m`, then `walkers.py` on the end state | 29 ticks, 522 first dispatches (18 x 29), 535 with 13 state-4 expiries; state 6 377 (13 x 29), state 4 158 (145 + 13 from state 2); end state 31/31 |
| `raise_gate.py <snap> [n]` | commands 2 and 4 poked into the command record and `$292dc` callcapped at 35 corners (side 1 raise and lower, side 2 raise at 6): corner grid vs the `raise_point`/`lower_point` model with the own-settlement redirect, mana, cell re-derivation | `p2_game_start` and `p2_game_60m`: 76/76 grid (control 40 and 42), 76/76 mana, 76/76 re-derive; 75/76 without the redirect rule |
| `click_ab.py [outdir]` | a left and a right click at cursor corner (11,30) from `p2_game_60m` vs a no-click run of the same length | left: command 2, 16 corners, model equal, neighbour models 0/3, mana 322; right: command 4, 1 corner, model equal, mana 20 |
| `gen_entry.sh` | rebuilds `anchors/p2_gen_entry.snap` (briefing OK click, `bp 1ebee`) | stops 8,057,305 steps after `p2_briefing`, seed `$10d7` |
| `gen_gate.py <entry snap> [n]` | `gen_land` `$1ebee` callcapped for n poked seeds against the literal model (hill table, walk LCG, stop at a reject or height 8, `raise_point` cell-bit writes) | 30/30 cell map byte for byte, 30/30 with seed and counters; controls: stop at 6 16/30, write-before-recursion 0/30 |
| `god_census.sh [outdir]` | `hits` on the computer god `$25652` over 12M steps from `p2_game_60m`: unpoked, side 2's controller word poked to human, side 1's poked to computer | computer branch 143 / 0 / 268 against 143 / 143 / 134 ticks; commands executed 5 / 0 / 91, each equal to the posts counted |
| `owned_cells.py <snap>...` | every settled entity on its side's code (`$2f` side 1, `$3f` side 2); unoccupied `$2f`/`$3f` cells near a same-side settlement | `p2_zeus` 4/4 (swapped 0/4), 6/6; `p2_game_start` 8/8 (0/8), 17/17; `p2_game_60m` 13/13 (0/13), 28/28 |
| `build_passes.sh [outdir]` | snapshots after each pass of `build_world` `$22942` (`a_1f870`, `b_1fa6c`, `c_22986`, `d_after`) from `p2_gen_entry` | records only |
| `scatter_gate.py <snap> [n] [--fa6c]` | `$1f870` (from `build/a_1f870`) or `$1fa6c` (from `build/b_1fa6c`) callcapped for n seeds against the scatter model; for `$1f870` a second half with `$3f6a9` poked `$80` forces the stale-D2 bonus | `$1f870` 30/30 (controls 10/30, no-bonus 30/30); poked 30/30 (2/30, no-bonus 0/30); `$1fa6c` 30/30 (9/30) |

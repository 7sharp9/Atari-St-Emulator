# Causeway planner (cheapest raise path across water)

Run from `M68000/`. Data and output go to `$POP_WORK/causeway/` (default `scratchpad/pop/causeway/`):
`table.json`, `snaps/<tag>/`, `gate_<tag>.json`, PNGs. Inputs are the `$POP_WORK` snapshots `game_start`, `late4`,
`walker/snaps/front` and `pop_auto.st`. The model is `popgen.Gen` (not reimplemented).

| script | what it proves | command | expected |
|---|---|---|---|
| `planner.py` | library: A* over (cell, raised corners in the 4x4 window); baselines `straight_naive`, `straight_best`, `greedy`; `replay` through `Gen.raise_pt` | imported | |
| `table.py` | planner vs baselines on 31 gaps of 3 snapshots (about 4 min) | `uv run python reversing/populous/py/causeway/table.py` | 31 lines, every planner mana the lowest, every result connects start to goal |
| `opt_check.py` | planner equals exhaustive subset search of sea corners in the gap's box | `uv run python reversing/populous/py/causeway/opt_check.py` | 6 lines `match True` |
| `gate.py` | the planner's clicks driven through the mouse UI (`popdrive`); ACT vs a CTL chain with the raise clicks removed; per-click corner 0 to 1, `$37f8a` 1, mana -14; whole map vs model; broken-model control (one click moved a corner) | `uv run python reversing/populous/py/causeway/gate.py g1 game_start "14,23;16,25;18,27"` | `corners_exact_vs_model_CTL` 4225, `mana_delta_act_minus_ctl` -42 = `mana_predicted`, `walk_cells_match` 4096, `broken_model_corners_exact_ctl` 4223 |
| | same, 5 clicks over three views | `gate.py g4 late4 "14,23;16,25;18,27;23,43;26,47"` | 4225, -70 = -70, 4096, broken 4223 |
| | the other two gated gaps | `gate.py g2 game_start "22,49;24,47"`, `gate.py g3 late4 "26,47;22,42"` | 4225, -28 = -28 each |
| `verify_conn.py` | start to goal connected in the game's own shape map after the clicks (ACT) and not without (CTL); needs the gates run | `uv run python reversing/populous/py/causeway/verify_conn.py` | `ACT connected True CTL connected False` per gated gap |
| `render.py` | one PNG per gap: before, causeway corners, after (emulator map where gated, model otherwise) | `uv run python reversing/populous/py/causeway/render.py` | 7 PNGs |
| `flatten.py` | fewest-clicks NxN flattening, beam search plus the ideas-file lower bound; model only, not played | `uv run python reversing/populous/py/causeway/flatten.py game_start 7 5 3` | `BEST T 1 clicks 3 mana 42 LB 1 flat True` |

Poke: `gate.py` teleports own walker idx 7 into the view (entity `+8`, `+10`, `+12`, `+18` zeroed, `+4` str 3000, occupancy
map moved), before the first click and whenever it has left the view, identically in both chains; without an own entity in
view a land click does nothing (`terrain.md` 2). No walker was walked across a causeway.

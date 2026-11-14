# Midwinter cell scan (`graphics.md` section 5a)

Run from `M68000/`. Needs `scratchpad/midwinter/pipeline/f1_start.snap` (made by `bash reversing/midwinter/py/pipeline/run.sh`)
and `scratchpad/midwinter/zuul067.st`. Captures and logs go to `scratchpad/midwinter/scan/` (`snaps/`, `cells/`); they are
not committed and `cap_scan.sh` rebuilds them (about 20 s, one emulator at a time).

| script | what it proves | command | expected line |
|---|---|---|---|
| `run.sh` | everything below from fresh captures (gate `scan` in `gates.toml`) | `bash reversing/midwinter/py/scan/run.sh` | `scan gate cells in order 6900/6900 ; headings exact 46/46`, `BROKEN-MODEL CONTROL cells in order 6405/6900 ; headings exact 0/46`, four `projection heading <h>: ... match 190 ... mismatch 0` |
| `cap_scan.sh` | 46 snapshots at `$19ce2`: 40 headings at camera cell (50,50) (poke `$12c98` at `$14e00`) and 6 poses (poke `$12c60`/`$12c64` at `$14e00`, `$12c98` at `$18304`) | `bash reversing/midwinter/py/scan/cap_scan.sh` | `snaps/h*.snap` |
| `gate_scan.py` | `scan_model.py`'s list equals the game's `$18f02` list, cell for cell in order | `uv run python reversing/midwinter/py/scan/gate_scan.py` (`--break`: last `$17140` word 2 to 3) | `scan gate cells in order 6900/6900 ; headings exact 46/46` (control: 6405/6900, 0/46) |
| `cap_cells.sh` | snapshots at `$1835a` for the projection check (poke `$12c98` at `$14e00`) | `bash reversing/midwinter/py/scan/cap_cells.sh 100 300 640 899` | `cells/c<h>.snap` |
| `order_check.py` | the model's list drawn last entry first, against view depth along the heading: 8-adjacent pairs drawn nearer-first (inferred, a property of the model) | `uv run python reversing/midwinter/py/scan/order_check.py` | 26% to 33% per heading, worst 1.41 cells |
| `draw_scan.py` | writes `reversing/midwinter/scan_order.png` | `uv run python reversing/midwinter/py/scan/draw_scan.py` | `wrote ...` |
| `scan_model.py`, `lists.py`, `common.py` | the model (tables are literals from `$17140`, `$17150`, `$172d0`), the list reader, shared paths | | |

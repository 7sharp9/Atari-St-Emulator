# `fed_MapGen` digger port

Evidence for `reversing/captive/mapgen.md`, "The digger and rooms". Run from `M68000/` with `uv run python -I
reversing/captive/py/mapgen/digger/<script>`. The repo root is found by walking up to `tools/rdis.py` (or
`M68000_ROOT`). Captures go to the gitignored `scratchpad/captive/mapgen_digger/` and need
`scratchpad/captive/mg_ret.snap`. Below, D = `scratchpad/captive/mapgen_digger` and F = `$D/d2_1_0.bin $D/d2_1_250.bin
$D/d2_1_500.bin $D/d2_1_750.bin`.

| script | what it proves | command | expected output |
|---|---|---|---|
| `dig_capture.py` | the module block and registers at `$23cb0` (before the digger) and `$23cb4` (after it), through `gen.py`'s shortcut call | `dig_capture.py d2_1_<b>.bin <b> <b+250> 1` for b = 0, 250, 500, 750; `dig_capture.py d2_0_0.bin 0 100 0` | five `.bin` files (about 0.7 s per seed; a re-run is byte-identical) |
| `dig.py gate` | the port of `$244b6` and its callees reproduces the whole module block and D1-D7 | `dig.py gate $F`; `dig.py gate $D/d2_0_0.bin` | `match 1000/1000`, `{'restarts': 874, 'lifts': 126}`; `match 100/100`, `{'restarts': 89, 'lifts': 11}` |
| (control) | the gate discriminates | `dig.py gate $F --break carve2`, `--break roomsize`, `--break pillar` | `match 0/1000`, `0/1000`, `24/1000` |
| `dig.py tree` (`tree.py`) | loop census of the carved bases | `dig.py tree $F` | `raw ... 0/1000`; `rooms+blobs no lifts ... 819/1000 ... cycles summed 232`; `rooms+blobs lifts ... 503/1000 ... 925`; components `{1: 1000}` |
| `rooms.py` | room sizes and room-list entries | `rooms.py $F` | `rooms 25771: bounding box ((s & 7) + 2) x (((s >> 3) & 7) + 2) in 25771; without pillars 20578`; room list `in 25588`, `mismatches not explained by that 0` |

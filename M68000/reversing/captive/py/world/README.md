# Captive `py/world/`: universe, picture sheets, Case.pic

Scripts behind `../../world.md`. Run from `M68000/`. Each one finds the repo root by walking up to
`tools/rdis.py` (or `M68000_ROOT`). Outputs go under `scratchpad/captive/agents/world/`. The
snapshots are `scratchpad/captive/{mission1,star,ld_1}.snap` (see the README's milestones).

| script | what it proves | command | expected output |
|---|---|---|---|
| `universe.py` | the universe generator (`$30280`-`$304a8`) reimplemented equals RAM | `uv run python -I reversing/captive/py/world/universe.py scratchpad/captive/mission1.snap` | `51/51`, `100/100`, `150/150 match`; targets `(0, 1), (127, 2), ...` |
| `universe.py --callcap` | the same for other missions: the generator is re-run by `callcap` after a poke of the mission index | `printf 'w 1ef86 00070001\ncallcap 302c6 3000000 scratchpad/captive/agents/world/cc_m7.json\nq\n' \| ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/captive/mission1.snap repl`, then `universe.py scratchpad/captive/mission1.snap --callcap scratchpad/captive/agents/world/cc_m7.json --mission 7` (mission 1: `00010001`, `cc_m1.json`, `--mission 1`) | callcap `returned`, 750 bytes changed (mission 1: 729); `51/51`, `100/100`, `150/150 match` |
| `universe.py --names` | the name generator `$3066e` | `uv run python -I reversing/captive/py/world/universe.py scratchpad/captive/star.snap --names` | line `13 PAICKOT`: the screen of `star.snap` (object 14 selected, `14782(A6)` = `$e`) shows `PLANET-PAICKOT` |
| `starscreen.py` | the 50 white dots of the map screen are the 50 generated planets | `uv run python -I tools/snap_render.py scratchpad/captive/mission1.snap scratchpad/captive/agents/world/m1.png` then `uv run python -I reversing/captive/py/world/starscreen.py scratchpad/captive/agents/world/m1.png scratchpad/captive/mission1.snap --png scratchpad/captive/agents/world/map_fit.png` | `fit pixel = (66,73) + 2*cell: 50/51`, the miss is slot 0 (station), `white pixels no cell explains: 0` |
| `render_pics.py` | `.pic` files are four separate 8,000-byte bitplanes; renders every sheet, the surface montage and the view buffer | `uv run python -I reversing/captive/py/world/render_pics.py scratchpad/captive/ld_1.snap scratchpad/captive/agents/world/pics` | 23 sheet PNGs (20 `.pic`, 3 `.pi`), `sheets_surface.png`, `view.png`; prints the live palette and `view buffer 0xf51e0` |
| `case_frames.py` | `Case.pic` = player + 9 planar frames | `uv run python -I reversing/captive/py/world/case_frames.py scratchpad/captive/fed/Case.pic scratchpad/captive/agents/world/case` | `frames 9`, play order `[8 x9, 7, 6, 5, 4, 4, 4, 4, 5, 6, 7, 8 x11, 7 ... 0]`, `case_strip.png` |
| `station/` (own README) | the station landing writes request 4 only with `14794` = 10; the final base's load, placement and the droids' death | see `station/README.md` | `$2f676` 1 and `$b5c2` D0 = 10, D2 = 1 with 10; 0 with 9 and 0; `410` 4 -> 0, `14800` = 1 |

The sheet identification uses an existing tool:
`uv run python -I tools/find_files_in_ram.py scratchpad/captive/ld_1.snap scratchpad/captive/fed 1f7b0 275c0 2f3d0 371e0 3eff0 46e00 4ec10`
prints `FULL` 32000/32000 for fed7-E, fed2-A, fed3-B, fed5, fed6-E, fed8, fed6-F.

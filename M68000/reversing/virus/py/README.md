# virus/py

Work directory `W` is `scratchpad/virus` (gitignored; `VIRUS_WORK` overrides). Everything runs from `M68000/`.
`bash reversing/virus/drive.sh` builds `W/drive/`, `bash reversing/virus/py/capture.sh` builds `W/fl/` and `W/cap/`,
`bash reversing/virus/py/gate_all.sh` runs every model below with its control and writes `W/gates/<gate>/out.txt`;
`uv run python tools/gates.py run virus` runs that last script and checks the expected lines.

| script | proves | command (after the captures) | expected line |
|---|---|---|---|
| `virus_terrain.py` | the height map is a sum of eight table sines, three landscape variants | `uv run python reversing/virus/py/virus_terrain.py W/drive/g_game2.snap [--delta W/cap/cc_l1.json --level 1] [--break]` | `level 0: match 65455/65455`; levels 1, 2: 65455/65455; `--break` 29124/65455 |
| `virus_objects.py` | the RNG and the object scatter | `... virus_objects.py W/drive/g_game2.snap W/cap/cc_l2.json 2 [--break-count\|--break-order]` | level 1 `identical type at the same cell: 571`; level 2 `1774` of 1775; controls 1767 and 1586 |
| `virus_grid.py` | the 11x10 projected vertex grid and its type words | `... virus_grid.py W/fl/f1.snap W/fl/cc1.json [--break]` (cc from `callcap 24098`) | `match 330/330` on f1..f4; `--break` 117/330 |
| `virus_tiles_check.py` | the 132 tile calls take vertices and colour from the rows | `... virus_tiles_check.py W/cap/tile_bp.txt [--break]` | `132/132` and `132/132`; `--break` 33/132 |
| `virus_slope.py` | the `$5ab58` slope table | `... virus_slope.py W/fl/f2.snap [--break]` | `8064/8064`; `--break` 1431/8064 |
| `virus_flight.py` | the ship tick, mouse run and the poked autopilot run | `... virus_flight.py W/cap/flight_bp.txt W/fl/f1.snap [--break]` | `pos 119/119, vel 119/119, att 119/119, mat 119/119`; autopilot log: mat 4/119; `--break` 99/119 |
| `virus_particles.py` | the stage-1 particle behaviour | `... virus_particles.py W/cap/part_bp.txt W/fl/f1.snap [--break]` | `447/447`; `--break` 334/447 |
| `pilot/pilot_model.py` | the pilot tick `$2538c` with `$2529a`, `$24754`, `$22c1e`, `$1f646`, against `callcap` (needs the demo snapshot `W/demo/S1b.snap`; one emulator, about 70 s) | `bash reversing/virus/py/pilot/gate_pilot.sh` (runs `pilot/capture_pilot.py 3500` then the model and five controls) | `model == callcap: 3496/3496`; controls 3494, 3484, 1033, 11, 3410 |
| `pilot/census_scan.py`, `pilot/census_report.py` | what the pilot's nearest-record scan picks: `bp 253a4` stops, behaviour pointer of the chosen record | `bash reversing/virus/py/pilot/gate_pilot.sh census` (about 150 s) | `PRECONDITION ... 1069 of 1563`, `RESULT ... 263`, chosen at a queue position 0 |
| `chain/chain.py`, `chain/table.py` | one lineage of K natural attract games from `W/demo/S1b.snap` (no ESC, no poke): wave `$32a50`, score, over tick, flight steps, carried queue, start snapshots; table and rank tests | `bash reversing/virus/py/chain/gate_chain.sh long 24` (about 55 min) | 24 games: wave rho +0.09 (p 0.68), see `demo.md` |
| `chain/gate_chain.sh`, `chain/check_chain.py` | the 2-game gate from fresh (about 5 min) | `bash reversing/virus/py/chain/gate_chain.sh` | `equal the six-game run: 2/2`; control (tick + 1) 0/2 |
| `chain/startdiff.py`, `chain/trend_bytes.py` | RAM diff of successive demo starts (outside stack and screens), and the bytes that grow monotonically | `uv run python reversing/virus/py/chain/startdiff.py W/chain/long/starts main` | per-pair 14,704 to 19,681 bytes |
| `chain/bench.py`, `chain/par.py` | interleaved timing of ways to run N steps; concurrent-emulator throughput | `uv run python reversing/virus/py/chain/bench.py W/demo/S1b.snap 30000000 3 argv repl_s repl_bp` | table in README "Running long" |
| `render_heightmaps.py` | draws `heightmaps.png` from the model | `uv run python reversing/virus/py/render_heightmaps.py <out.png>` | `wrote <out.png>` |
| `capture.sh`, `gate_all.sh`, `vcommon.py` | captures, the gate set, shared paths | | `captured` |

Pokes in the captures: the stub code at `$90000` for the `callcap` targets (`cc_l*.json`, `cc_n*.json`), and `wb 62a5f ff` for
`flight_auto_bp.txt` and `auto_hits.txt`.

# `fed_MapGen` scripts

The evidence behind `reversing/captive/mapgen.md`. Run them from `M68000/` with `uv run python -I`. Each script finds
the repo root by walking up to `tools/rdis.py`, or from `M68000_ROOT` if it is set. A relative output path is
written under `scratchpad/captive/agents/mapgen/`. They need `scratchpad/captive/mg_ret.snap` and its disk sidecar.
`flowfield.py --snap` also needs `scratchpad/captive/agents/ai/req4.snap`.

All the calls go through `stserver`. They enter the module body at `$20054`, after the Copylock prologue, which is
the only part that reads the disk. They therefore do not depend on stserver's FDC behaviour. `gen.py`'s control and
`flowfield.py --snap` show that the shortcut reproduces a natural call.

| script | what it proves | command | expected output |
|---|---|---|---|
| `gen.py` | runs the generator for any (D0, D1, D2, D3) and dumps G0/G1/G2, both federation layers and the module variables to json (shared core of the others) | `gen.py land.json 1,0xffff,14,0` | one line per case: args, steps, D0, D5, D6 (`[1, 65535, 14, 0] 234362 $00000030 $00000000 $00200010`) |
| `cmp_ret.py` | control: the shortcut entry reproduces the natural landing call. Outputs are pre-filled with `$5a`, so "equal" means rewritten | `MAPGEN_POISON=1 gen.py land.json 1,0xffff,14,0` then `cmp_ret.py land.json` | all 8 regions `equal` (g0, g1, g2, outa, outb, vars, fedtab, mvars) |
| `cmpcases.py` | determinism and which arguments seed the base | `gen.py seeds.json 1,0,1,0 1,0,1,0 1,0x1234,1,7 1,0,0,0 2,0,1,0 1,164,14,1 1,165,14,1 1,164,14,2` then `cmpcases.py seeds.json` | pair 1-2 and pair 2-3: every count 0; `1,0x1234,1,7` vs `1,0,0,0`: outa 39; `1,164,14,1` vs `1,165,14,1`: outa 406; `1,165,14,1` vs `1,164,14,2`: outa 406 (`1,164,14,1` vs `1,164,14,2` is identical: run with `--all`) |
| `zones.py` | Python model of the floor plan (`$2011e`, `$201de`, `$20252`, `$202a2`) and the RNG `$23b96` | `zones.py gate 0 1000`; `zones.py model 5` prints one plan | `match 1000/1000 (module bytes 0..55, rng word 12404(A6), G0 4096 bytes at the return from $202a2)` |
| `liftpair.py` | every lift end has its partner on the adjacent floor at that floor pair's offset | `liftpair.py 0 41` | `paired 510/510 lift cells over D0 = 0..40, D2 = 1` |
| `flowfield.py` | Python model of plane 2 (`$24f4c`): each cell points to the open neighbour or lift partner with the lowest carve number; with `--snap`, the shortcut against the natural base-mode call | `flowfield.py 1 41 0 --snap scratchpad/captive/agents/ai/req4.snap`; `flowfield.py 0 41 1` | `match 43832/43832 open cells over D0 = 1..40, D2 = 0; G2 bytes changed later: 0`, both layers `2048/2048 equal ignoring bit 7`; `match 44053/44053 open cells over D0 = 0..40, D2 = 1; G2 bytes changed later: 0` |
| `stagedump.py` | grids after each of the 38 stages of `$23bb0` and the export; prints the G0/G1/G2 bytes each stage changed | `stagedump.py stages.json 1,0,1,0` | `39 stages`; `244b6 {'g0': 891, 'g1': 550, 'g2': 0}`; `24f4c {'g0': 0, 'g1': 184, 'g2': 362}` |
| `stages.py`, `evt.py` | steps per stage from an `ATARI_TRACE_EVENTS` log of the call | REPL `callcap 20054 4000000 D0=1 D1=0 D2=1 D3=0 D4=ffffffff A0=1d9e8 A1=b532 A2=303c` from `mg_ret.snap` with `ATARI_NOTRACE=1 ATARI_TRACE_EVENTS=base.evt`, then `stages.py base.evt 2` | `023cb0 -> 0244b6 ... steps 1708805` (the digger) |
| `base30.repl` | REPL drive: labelled pokes of the request word and `32(A6)` = 30, build and enter the D0 = 30 base; writes `scratchpad/captive/agents/curios/base30.snap` | `resume scratchpad/captive/ld_1.snap repl < reversing/captive/py/mapgen/base30.repl` | the base with every feature (`mapgen.md` "Feature and item stages") |
| `view_tiles.py` | puts the party (labelled pokes) in front of a cell holding a chosen tile, saves the state and renders the view | `view_tiles.py scratchpad/captive/agents/curios/base30.snap <outdir> 22 --n 1` | `tile $22 cell (7,3) from (7,2) facing 2; ... 15408(A6) $22`; `t22_7_3_d1.snap`, `.png`, `_view.png` |
| `step_diff.py` | tile and party changes between two snapshots (a `view_tiles.py` state and the same after `keys.py`) | `step_diff.py <before.snap> <after.snap>` | `party [x, y, f] -> [...] ... tile changes (bit 7 ignored): ...` |
| `picwatch.py` | writers of the wall-picture list `$1bd58` during one generator call | `picwatch.py 30,0,0,0` | `events 800`: `$023b8e` 400 (the clear), `$0263ac`/`b0`/`b4`/`b8` 100 each |
| `basemap.py` | renders bases (`mapgen_base_*.png`) | `gen.py bases.json 1,0,1,0 5,0,1,0 12,0,1,0` then `basemap.py bases.json png` | one PNG path per case |
| `stages/` | 17 of the post-dig stage calls, ported and gated 80/80 each (the other 12 are in `full/`), the coded-door list writer | `stages/README.md` | `stages/gate.py 0 40`: 17 lines of `exact 80/80` |
| `full/` | the whole generator in Python from (D0, D2): shafts, reservations, room pass 2, the group writer and placement stages, locks and keys, the encoder; chained, it equals the emulator's returned output | `full/README.md` | `full/chain_run.py gate ...`: `400/400` (D2 = 0 and 1, D0 = 0..99 and 300..399); lock census 8,617/8,617 keys dug no later than their door |
| `digger/` | a register-level port of the digger `$244b6`, byte-exact against the emulator; room sizes, room list, loop census | `digger/README.md` | `digger/dig.py gate ...`: `match 1000/1000` (D2 = 1), `match 100/100` (D2 = 0) |

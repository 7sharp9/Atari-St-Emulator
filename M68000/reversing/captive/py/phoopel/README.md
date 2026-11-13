# Sealed keys (the Phoopel hint)

Scripts behind `mapgen.md` "Sealed keys: the Phoopel case": a lock whose CLIPBOARD key the generator drops on its own
door cell. Run from `M68000/` with `uv run python -I reversing/captive/py/phoopel/<script>`; outputs go to
`scratchpad/captive/phoopel/`. All but `shown_emu.py`, `emu_base13.py`, `live13.py`, `itemview.py` and
`enter13.repl` are model-only (the chained generator, gated 400/400 in `../mapgen/full/`).

| Script | What it does | Expected output |
|---|---|---|
| `find_names.py <name> <missions>` | universe model names (syllable tables from `scratchpad/captive/star.snap`) | `PHOOPEL 512`: MOON-PHOOPEL at mission index 1 object 98 (target 3) and index 438 (not a target) |
| `locks13.py <d0> <d2>`, `shown.py <d0> <d2>` | the lock list of one base; with each key's cell and the number its clipboard shows | `shown.py 13 0`: lock 4 code 34080 shown 15099, K (7,9) = D (7,9) |
| `findcode.py <code> <lo> <hi> <d2>` | bases whose raw lock code equals a value | `15099 0 1500 0`: none; control `44558 13 14 0`: lock 2 |
| `shown_emu.py <snap> <n> ...` | the clipboard number `$12d4e` computes in the emulator against `shown.shown` | 301/301 incl. (34080, 13) -> 15099; `32(A6)` unpoked 0/50 |
| `enter13.repl` | REPL drive: `ld_1.snap`, labelled pokes `32(A6)` = 13 and request word 4, build and enter base 13; writes `scratchpad/captive/phoopel/base13.snap` | `$b5c2` called with D0 = `$0d`, returns D0 = 5 |
| `emu_base13.py` | model chain for D0 = 13, D2 = 0 against capture_final's `f_0_0.bin` | `chain == emulator ... True` |
| `live13.py` | base13.snap tile layer against the model; forward presses at the flame door (labelled pokes of party x, y, facing) | 2041/2048 cells; door blocks from (6,9) and (8,9), control facing W moves to (4,9) |
| `itemview.py` | renders the view toward an item cell | `clip_*_view.png`, `view_*.png` |
| `region.py` | reachability around lock 4 with the door closed | K and E unreachable with D closed, reachable with it open; `region.txt` map |
| `keyondoor.py <lo> <hi>` | every key on its own door over missions lo+1..hi, with its clipboard number | `0 100`: 100 of 24,603 keys, 92 of 1,100 bases; first mission 2 target 3 |
| `sealed.py <lo> <hi>` | for each sealed key, the open cells cut off by its door and the other locks inside | `0 100` (about 3 min): 100 sealed, cut off 1..1230 cells (median 76), 29 cut off 25% or more; Phoopel 622 of 1193 |

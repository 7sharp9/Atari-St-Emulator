# Sealed keys (the Phoopel hint)

Scripts behind `mapgen.md` "Sealed keys: the Phoopel case": a lock whose CLIPBOARD key the generator drops on its own
door cell. Run from `M68000/` with `uv run python -I reversing/captive/py/phoopel/<script>`; outputs go to
`scratchpad/captive/phoopel/`. All but `shown_emu.py`, `emu_base13.py`, `live13.py`, `itemview.py`, `panel13.py`, `finish13.py`, `leave.py` and
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
| `panel13.py [lock] [bits]` | the lock's wall panel driven by mouse clicks in `base13.snap` (labelled pokes: party cell and facing): cover, then one click per code bit; control with the last bit wrong; then a walk onto the door cell | lock 4: cover W `$11` -> `$15`; bits 5, 8, 10 leave D (7,9) `$26`, bit 15 gives state `$8520`, byte8 `$3b`, D `$20`; control ends state `$0521`, D `$26`; walk reaches (7,9). `panel_code_{before,open,after}.png` |
| `finish.py <lo> <hi>` | model: in each base with a sealed key, whether a generator tile (`$28`) can be stood beside with the sealed doors closed | `0 100` (about 4 min): 92 bases, 0 without a generator, 27 with every generator behind a sealed door (first: mission 2 target 3) |
| `finish13.py` | EXPLOSIVES on a generator (labelled pokes: party cell, facing, hand slot `404(A6)`), the state word `13410(A6)`, the fire cell against the dig arrows; control with an empty hand. `SNAP=base1/in.snap TAG=finish_base1` for the natural base | base 13: `13410` 0 -> 1 -> 2, `$28` tiles 9 -> 0, fire 28/29 moves on bits 0-2 in 60M steps (the other is the lift move (54,11) to (22,27)); `base1/in.snap`: 21/21, entrance (30,0) reached, state 3; control `13410` stays 0; writes `<TAG>_blast_state2.snap` |
| `leave.py <snap> [poke]` | census of the leave code for a view click at the entrance facing N (`poke`: labelled pokes of the party onto it) | `base1/in.snap poke`: `$dd90` 1, `$87c0` 1, `$87d6` 0, mode 3; `phoopel/finish_base1_blast_state2.snap poke`: `$87d6`, `$87f4`, `$8836` 1 each, visited 0 -> 1, mode 1 |

# populous2 scripts

Run from `M68000/` with `uv run python reversing/populous2/py/<script> ...`. Inputs are the
anchors under `scratchpad/populous2/anchors/` (`scratchpad/ANCHORS.md`; rebuilt by `../drive.txt`).

| script | what it proves or does | result |
|---|---|---|
| `corners.py <snap> [--callcap]` | corner heights implied by the 4-byte cell records at `$3979e`; Populous 1's cell derivation without the shore rule; `$1f176` under callcap | `p2_game_start`: 4225/4225 shared corners, 4071/4071 cells (control 3334), 915/915 callcaps (control 357); `p2_game_60m`: 4055/4055, 920/920 |
| `find_corner_grid.py <snap> [--control]` | no separate 65x65 corner grid in RAM | best real candidate 2875/4086 (all-sea baseline); planted grid 4071 |
| `rand_gate.py <snap> [n]` | `rand` `$215dc` model (32-bit LCG `$bb40e62d`, seed `$47382`) | 50/50; control without the zero-seed rule 49/50 |
| `fdc_files.py <st> <fdc.log>` | file and DMA address behind every FDC sector read | 11 of 13 game files at their table address |
| `call_census.py <events.bin> [min]` | call and interrupt counts from an `ATARI_TRACE_EVENTS` log | from `p2_game_60m`, 2.4M steps: 23 call targets at exactly 29 calls (one per main-loop pass), VBL 200, IKBD 1200 |

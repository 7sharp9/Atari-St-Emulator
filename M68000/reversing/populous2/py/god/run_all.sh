#!/bin/bash
# Populous II computer-god model vs callcap of $25652: every arm and the broken-model controls.
# Run from anywhere:  bash reversing/populous2/py/god/run_all.sh   (60 to 70 minutes on a loaded machine; one
# emulator process at a time). The short promoted gate is gate_short.sh.
cd "$(dirname "$0")/../../../.." || exit 1
D=reversing/populous2/py/god
S=scratchpad/populous2/anchors/p2_game_60m.snap
g() { uv run python $D/god_gate.py "$@" 2>&1 | grep -v '^---'; }
echo "== natural (no poke), 1424 ticks"; g $S 1424
echo "== side 1 controller word poked to 4 (ww 47118 4), 1000 ticks"; g $S 1000 --poke 0x47118:2:4
echo "== per-state variants (pokes on the forked state only), 50 ticks, every 7th tick"; g $S 50 --variants
for c in reload swap; do echo "== control $c (side 1 computer, 400 ticks)"; g $S 400 --poke 0x47118:2:4 --control $c; done
for c in radius quirk; do echo "== control $c (variants)"; g $S 50 --variants --control $c; done

#!/bin/bash
# Short promoted gate: the side-1-computer arm (controller word poked to 4, nothing else) for 150 ticks against the
# model, then the same ticks against a model whose reload value is one too high (must fail).
# Run from M68000/:  bash reversing/populous2/py/god/gate_short.sh
cd "$(dirname "$0")/../../../.." || exit 1
D=reversing/populous2/py/god
S=scratchpad/populous2/anchors/p2_game_60m.snap
echo "arm side1_computer"; uv run python $D/god_gate.py $S 150 --poke 0x47118:2:4 2>&1 | grep '^states'
echo "arm side1_computer_control_reload"; uv run python $D/god_gate.py $S 150 --poke 0x47118:2:4 --control reload 2>&1 | grep '^states'

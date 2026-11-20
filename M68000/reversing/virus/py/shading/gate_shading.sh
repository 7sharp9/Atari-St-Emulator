#!/bin/bash
# Shading gates, captured afresh into $W/shading/gate/: the tile colour has no slope term (height-poke A/B with a positive control),
# the span routines (with control), the tile filler against a frame's real calls (with control), the whole slope table (with control)
# and the page flip.  Needs the captures of drive.sh (g_game2.snap) and capture.sh (fl/f1.snap).  About 5 minutes.
# Usage: bash reversing/virus/py/shading/gate_shading.sh   (from anywhere)
cd "$(dirname "$0")/../../../.." || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; P=reversing/virus/py/shading; G=$W/shading/gate; PY="uv run python -I"
mkdir -p "$G"; rm -f "$G"/*
S=$W/drive/g_game2.snap; F=$W/fl/f1.snap
run() { "$@" 2>&1 | grep -v "^WARNING\|^---" | tee -a "$G/out.txt"; }
echo "== tile colour has no slope term (poke A same type band, poke B positive control)"; run $PY $P/height_poke.py $S
echo "== span tables decoded"; run $PY $P/span_colours.py $F
echo "== span routines vs pixel model"; run $PY $P/span_gate.py $S 60
echo "control: one pixel too wide"; run $PY $P/span_gate.py $S 60 control
echo "== tile filler vs a frame's real calls"; $PY $P/tile_capture.py $S $G/tile_bp.txt >/dev/null 2>&1
echo "tile calls logged: $(grep -c 'PC: 00026b78' $G/tile_bp.txt)"
run $PY $P/tile_gate.py $G/tile_bp.txt $S
echo "control: bow-tie vertex order"; run $PY $P/tile_gate.py $G/tile_bp.txt $S control
echo "== slope table"; run $PY $P/slope_full.py $S
echo "control: low byte kept"; run $PY $P/slope_full.py $S --break
echo "== page flip"; run $PY $P/flip_check.py $F

#!/bin/bash
# gate_painter.sh: the Virus depth-bucket painter (README "The renderer", "Depth sorting and paint order").
# Captures afresh into $W/painter/gate/ (W = $VIRUS_WORK or scratchpad/virus), then prints
#   1. the bucket-rule gate: object-dot records, model records and the ship against the pools and the camera, with
#      three wrong bucket rules as controls (analyze.py);
#   2. the tile-row / bucket interleave of the painter loop (gate_order.py);
#   3. the draw-order pixel test: the screen against the last-drawn dot, first-drawn dot as the control (analyze_order.py).
# Start snapshots (README "Running it", py/chain, py/capture.sh): demo/S1b.snap, fl/f1.snap, chain/long100/starts/main_g050.snap.
# One emulator at a time; about 2 minutes.
set -e
cd "$(dirname "$0")/../../../.."
W=${VIRUS_WORK:-scratchpad/virus}
G=$W/painter/gate
P=reversing/virus/py/painter
mkdir -p "$G"
rm -f "$G"/*.json
uv run python $P/capture.py $W/fl/f1.snap 0 120 $G/f1.json | tail -1
uv run python $P/capture.py $W/demo/S1b.snap 0 300 $G/S1b.json | tail -1
uv run python $P/capture.py $W/chain/long100/starts/main_g050.snap 600 360 $G/g050.json | tail -1
echo "== bucket rule (controls are the ctl lines)"
uv run python $P/analyze.py $G/f1.json $G/S1b.json $G/g050.json
echo "== tile rows and buckets"
uv run python $P/gate_order.py $W/demo/S1b.snap 40 | tail -4
uv run python $P/capture_screen.py $W/demo/S1b.snap 0 200 $G/scr_S1b.json | tail -1
uv run python $P/capture_screen.py $W/chain/long100/starts/main_g050.snap 600 200 $G/scr_g050.json | tail -1
echo "== draw order against pixels"
uv run python $P/analyze_order.py $G/scr_S1b.json $G/scr_g050.json

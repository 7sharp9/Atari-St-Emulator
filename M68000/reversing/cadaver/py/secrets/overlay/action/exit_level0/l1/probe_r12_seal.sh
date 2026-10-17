#!/bin/bash
# probe_r12_seal.sh <room12_unarmed.snap> <OUTDIR>: can the hero walk into room 12's region 1 (x 41..55, y 9..23) before lever 225 is armed?
# From route_level1_room90.py's ck_10_s12.snap (first visit, pillars 213/214 static at z 0..47): the north lane (y lead to the wall, then east)
# and the south lane (east along the south wall) both stall at x lead 35, against pillar 214 (x 36..39, y 8..23; lintel 216 on it at z 49..96).
# Expected: both legs end in room 12 at x lead 35, health 60 (no teleport to room 93).
set -e
ROOT=${M68000_ROOT:?set M68000_ROOT to M68000/}; E=$ROOT/reversing/cadaver/py/secrets/overlay/action/exit_level0/l1/explore.py
IN=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); mkdir -p "$2"; OUT=$(cd "$2" && pwd)
cd "$ROOT"; export ATARI_NOTRACE=1
uv run python "$E" "$IN" "$OUT/north.snap" 'GU:y<=7' 'GR:x>=48' 'WD:20' T A12
uv run python "$E" "$IN" "$OUT/south.snap" 'GR:x>=33' HD HR T A12

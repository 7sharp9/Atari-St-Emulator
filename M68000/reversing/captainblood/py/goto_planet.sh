#!/bin/bash
# goto_planet.sh <start.snap (bridge, planet view)> <x> <y> <prefix>   (x, y = galaxy coordinates)
# Cockpit, galaxy map, pick (x,y), hyperspace jump, then "land" with its hit-table handler at $d5c0 poked from the
# canyon flight $10686 to the contact setup $d8c8 (a labelled poke: the flight is skipped). Writes
# scratchpad/captainblood/<prefix>_{a..e}.snap; _e is the conversation screen on an inhabited planet.
# Run from M68000/.
W=scratchpad/captainblood; X=$2; Y=$3; P=$W/$4
D(){ uv run python -I reversing/captainblood/py/drive.py "$@" | tail -1; }
D $1 ${P}_a.snap 160 50 4000000
D ${P}_a.snap ${P}_b.snap 123 16 8000000
D ${P}_b.snap ${P}_c.snap $((X+30)) $((Y+54)) 3000000
D ${P}_c.snap ${P}_d.snap 157 33 40000000
PRE='w d5c0 0000d8c8' D ${P}_d.snap ${P}_e.snap 187 16 4000000

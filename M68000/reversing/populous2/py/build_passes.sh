#!/bin/bash
# Populous II: snapshots between the world-build passes of build_world $22942, from p2_gen_entry.
# a_1f870 = after gen_land, b_1fa6c = after $1f870, c_22986 = after $1fa6c, d_after = after $22986.
# Run from M68000/. Output dir defaults to scratchpad/populous2/build.
set -e
D=${1:-scratchpad/populous2/build}
mkdir -p "$D"; rm -f "$D"/{a_1f870,b_1fa6c,c_22986,d_after}.snap
printf "u 2294e 50000000\nsnap $D/a_1f870.snap\nu 22954 50000000\nsnap $D/b_1fa6c.snap\nu 2295a 50000000\nsnap $D/c_22986.snap\nu 22960 50000000\nsnap $D/d_after.snap\nq\n" |
  dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/populous2/anchors/p2_gen_entry.snap repl 2>&1 | grep -E 'reached|saved'

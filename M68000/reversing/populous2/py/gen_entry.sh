#!/bin/bash
# Populous II: snapshot stopped at gen_land $1ebee's entry during the conquest world build, from p2_briefing
# (the briefing's OK click, then bp). Writes scratchpad/populous2/anchors/p2_gen_entry.snap. Run from M68000/.
set -e
OUT=scratchpad/populous2/anchors/p2_gen_entry.snap
rm -f "$OUT" "$OUT.prov.json"
printf "mouse move -90 94\ns 300000\nmouse down l\ns 60000\nmouse up l\nbp 1ebee 80000000\nsnap $OUT\nm 47382 4\nq\n" |
  dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/populous2/anchors/p2_briefing.snap repl 2>&1 |
  grep -E 'breakpoint|state saved|^00 '

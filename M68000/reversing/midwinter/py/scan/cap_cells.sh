#!/bin/bash
# Snapshots at $1835a (cell scan and projection done) for the projection check at other headings.
# Poke: `ww 12c98 <h>` at $14e00. Run from M68000/ after py/pipeline/run.sh.
D=scratchpad/midwinter/scan
export ATARI_NOTRACE=1
mkdir -p $D/cells
for h in "$@"; do
  printf 'ww 12c98 %04x\nbp 1835a 400000\nsnap %s/cells/c%s.snap\nq\n' $h $D $h > $D/cells/c$h.repl
  dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/midwinter/pipeline/f1_start.snap repl --disk-a scratchpad/midwinter/zuul067.st < $D/cells/c$h.repl > $D/cells/c$h.log 2>&1
done

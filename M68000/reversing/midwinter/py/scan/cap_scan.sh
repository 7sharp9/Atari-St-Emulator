#!/bin/bash
# Fresh captures for the scan gate. Run from M68000/ after reversing/midwinter/py/pipeline/run.sh (it writes f1_start.snap).
# Pokes (all labelled): 40 headings: `ww 12c98 <h>` at $14e00 (camera cell 50,50); 6 poses: `w 12c60`/`w 12c64` (position) at
# $14e00 and `ww 12c98` at $18304 (a heading poked at $14e00 is overwritten when the position is also poked).
# Each snapshot is taken at $19ce2, when the cell list $18f02 is complete.
D=scratchpad/midwinter/scan
START=scratchpad/midwinter/pipeline/f1_start.snap
DISK=scratchpad/midwinter/zuul067.st
export ATARI_NOTRACE=1
mkdir -p $D/snaps
rm -f $D/snaps/*
run() { dotnet exec bin/Debug/net8.0/M68000.dll resume $START repl --disk-a $DISK < $1 > ${1%.repl}.log 2>&1; }
for h in $(seq 0 32 992) 5 77 131 300 511 700 899 1001; do
  printf 'ww 12c98 %04x\nbp 19ce2 400000\nsnap %s/snaps/h%s.snap\nq\n' $h $D $h > $D/snaps/h$h.repl; run $D/snaps/h$h.repl
done
pose() { # name heading posx posy
  printf 'w 12c60 %08x\nw 12c64 %08x\nbp 18304 400000\nww 12c98 %04x\nbp 19ce2 400000\nsnap %s/snaps/h%s_%s.snap\nq\n' $3 $4 $2 $D $2 $1 > $D/snaps/pose_$1.repl; run $D/snaps/pose_$1.repl
}
pose p1 300 15700 23100; pose p2 700 35900 15500; pose p3 40 17900 30700
pose p4 1000 40900 10300; pose p5 600 25600 25600; pose p6 450 31000 33300

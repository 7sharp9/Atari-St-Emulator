#!/bin/bash
# poked.sh [natural dir] [out dir]: waves 9, 10, 15 and 16 driven from natural.sh's end_4.snap (stopped at $20fb4 after wave 4
# was cleared: counter 4, landscape 1 built, nothing poked up to there).  Every poke is labelled:
#   P1  ww 32a50 0008 at $20fb4: $20fd0 makes the counter 9, so $20e74(9) builds landscape 2 (a poke: no chain game gets there).
#   P2  w 27082 00031d54 + ww 32a3e 0000: empties the actor pool so $20f82 falls into $20fb4 on its next tick ("wave destroyed").
#   P3  ww 32a50 000e / 000f at $20fb4: counters 15 / 16 after the increment (the table index wraps at 16).
# Snapshots per stage: pend_N (stop at $20fb4), pafter_N ($210e8), pbuilt_N ($20f80), N = 9, 10, 15, 16.  About 25 seconds.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; cd "$d" || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; N=${1:-$W/landscape/natural}; O=${2:-$W/landscape/poked}; mkdir -p "$O"
empty() { echo "w 27082 00031d54"; echo "ww 32a3e 0000"; }
{
echo "ww 32a50 0008"
echo "bp 210e8 40000000"; echo "bp 20f80 40000000"; echo "snap $O/pbuilt_9.snap"
empty; echo "bp 20fb4 100000000"; echo "snap $O/pend_9.snap"
echo "bp 210e8 40000000"; echo "snap $O/pafter_9.snap"; echo "bp 20f80 40000000"; echo "snap $O/pbuilt_10.snap"
empty; echo "bp 20fb4 100000000"; echo "ww 32a50 000e"; echo "snap $O/pend_10.snap"
echo "bp 210e8 40000000"; echo "snap $O/pafter_10.snap"; echo "bp 20f80 40000000"; echo "snap $O/pbuilt_15.snap"
empty; echo "bp 20fb4 100000000"; echo "ww 32a50 000f"; echo "snap $O/pend_15.snap"
echo "bp 210e8 40000000"; echo "snap $O/pafter_15.snap"; echo "bp 20f80 40000000"; echo "snap $O/pbuilt_16.snap"
echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$N/end_4.snap" repl > "$O/out.txt" 2>&1
echo "poked.sh rc=$?"

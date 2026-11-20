#!/bin/bash
# poked_inf.sh <poked dir>: the wave-end bonus on landscape 2 with a nonzero infected count.  Start: poked.sh's pend_9.snap
# (at $20fb4, counter 9, landscape 2, object map freshly scattered: no bit-5 cells).  POKE (labelled): wb 20 into 3000
# object-map bytes at $32a58 + 17 i (i < 3000), then run to the end of the pay loop.  Writes inf_end.snap, inf_after.snap.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ]; do d=$(dirname "$d"); done; cd "$d" || exit 1
W=${VIRUS_WORK:-scratchpad/virus}; O=${1:-$W/landscape/poked}
{
for i in $(seq 0 2999); do printf 'wb %x 20\n' $((0x32a58 + 17 * i)); done
echo "snap $O/inf_end.snap"; echo "bp 210e8 40000000"; echo "snap $O/inf_after.snap"; echo q
} | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$O/pend_9.snap" repl > "$O/inf_out.txt" 2>&1
echo "poked_inf.sh rc=$?"

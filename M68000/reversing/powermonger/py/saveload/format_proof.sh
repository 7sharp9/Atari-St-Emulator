#!/bin/bash
# format_proof.sh [file-panel-snap] [tag]
# FORMAT, SAVE, OVERWRITE and LOAD on a blank disk, all in ONE emulator process (disk writes stay in memory):
#   insert a zeroed 409,600-byte disk -> FORMAT (170,117) -> requester OK (120,118), 30M steps -> snap <tag>_fmt
#   -> options icon (71,138), FILE (111,92) -> SAVE (170,99), bp $1beae -> snap <tag>_S1
#   -> options, FILE (142,92) -> SAVE again: OVERWRITE? requester $1bed4 -> snap <tag>_ow -> OK, bp $1beae -> snap <tag>_S2
#   -> options, FILE (111,92) -> LOAD (170,81), bp $1bdf8 -> snap <tag>_L; then compares $3f768..$58368 of S2 and L.
# The options panel opens at a different origin after a requester has closed (FILE at 111,92) than after a plain
# SAVE (142,92). Default start: scratchpad/pm150/saveload/out/file.snap (FILE panel open, slot A selected).
# Work dir $PM_WORK (default scratchpad/pm152/format). ATARI_TRACE_FDC=1 log in <tag>.txt (fdc_sectors.py reads it).
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm152/format}; mkdir -p "$W"
SNAP=${1:-scratchpad/pm150/saveload/out/file.snap}; T=${2:-proof}
python3 -c "open('$W/zero.st','wb').write(bytes(409600))"
A="1ba72 1bf0e cce2 1bd38 1bec2 1bf04 1beec 1bed4 1bdfe 1bd70 1bd52 d9fc 7740 77a2 e288 e29c 12726"
home() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }
# click x y steps [bp-addr snap-path]: a hits census over the steps, or a stop at the bp and a snapshot there.
click() { home; echo "mouse move $1 $2"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
          echo "mouse down l"; echo "mouse move 0 0"
          if [ -n "$4" ]; then echo "bp $4 $3"; echo "snap $5"; else echo "hits $3 $A"; fi
          echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"; }
{ echo "disk $W/zero.st"
  click 170 117 3000000; click 120 118 30000000; echo "snap $W/${T}_fmt.snap"
  click 71 138 600000; click 111 92 600000
  click 170 99 3000000 1beae $W/${T}_S1.snap; echo "m 1bbfa 4"; echo "s 10000000"
  click 71 138 600000; click 142 92 600000
  click 170 99 3000000; echo "snap $W/${T}_ow.snap"
  click 120 118 3000000 1beae $W/${T}_S2.snap; echo "m 1bbfa 4"; echo "s 10000000"
  click 71 138 600000; click 111 92 600000
  click 170 81 3000000 1bdf8 $W/${T}_L.snap; echo "m 1bbfa 4"; echo q
} > "$W/$T.cmds"
ATARI_TRACE_FDC=1 ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$T.cmds" > "$W/$T.txt" 2>&1
grep -v '^FDC\|^mouse' "$W/$T.txt" | grep -v ' 0  first -1' | grep 'hits\|\$0\|breakpoint\|gave up'
echo "write-track commands: $(grep -c WRITE-TRACK "$W/$T.txt"), sectors skipped: $(grep -c 'skipped' "$W/$T.txt"), failed reads: $(grep -c 'no data' "$W/$T.txt")"
for s in S1 S2 L; do python3 reversing/powermonger/py/snap2ram.py "$W/${T}_$s.snap" >/dev/null; done
python3 - "$W/${T}_S1.ram" "$W/${T}_S2.ram" "$W/${T}_L.ram" <<'EOF'
import sys
s1, s2, l = (open(p, 'rb').read()[0x3f768:0x58368] for p in sys.argv[1:])
print('S2 vs L  %d/%d' % (sum(a == b for a, b in zip(s2, l)), len(s2)))
print('S1 vs S2 %d/%d (the overwrite changed the slot)' % (sum(a == b for a, b in zip(s1, s2)), len(s2)))
EOF

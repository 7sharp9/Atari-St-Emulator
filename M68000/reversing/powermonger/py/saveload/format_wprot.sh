#!/bin/bash
# format_wprot.sh [file-panel-snap]
# FORMAT on a write-protected disk, in ONE emulator process per arm (REPL `wprot on|off`, MMU.SetWriteProtectA):
#   retry arm:  zeroed disk, wprot on -> FORMAT (170,117) -> save-disk OK (120,118), 30M steps -> snap wp_ask
#               (expect $1bf04 "IS IT WRITE PROTECTED ?", no data written)
#               -> wprot off -> requester OK (120,118), 30M steps -> snap wp_retry (expect the format: 80 Write Tracks)
#   cancel arm: same up to wp_ask, then CANCEL (200,118) -> snap wp_cancel (expect $1beec, no data written)
# Default start: scratchpad/pm150/saveload/out/file.snap (FILE panel open). Work dir $PM_WORK (default
# scratchpad/pm159/wprot). ATARI_TRACE_FDC=1 log in <arm>.txt: the WRITE-PROTECTED and WRITE-TRACK lines.
ROOT=$(cd "$(dirname "$0")" && while [ ! -f tools/rdis.py ] && [ "$PWD" != / ]; do cd ..; done; pwd)
cd "$ROOT" || exit 1
W=${PM_WORK:-scratchpad/pm159/wprot}; mkdir -p "$W"
SNAP=${1:-scratchpad/pm150/saveload/out/file.snap}
python3 -c "open('$W/zero.st','wb').write(bytes(409600))"
A="1ba72 1bd38 1bec2 1bf04 1beec 1bf0e d9fc"
home() { echo "mouse move -400 -400"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"; }
click() { home; echo "mouse move $1 $2"; echo "s 300000"; echo "mouse move 0 0"; echo "s 300000"
          echo "mouse down l"; echo "mouse move 0 0"; echo "hits $3 $A"
          echo "mouse up l"; echo "mouse move 0 0"; echo "s 300000"; }
ask() { echo "disk $W/zero.st"; echo "wprot on"; click 170 117 3000000; click 120 118 30000000; echo "snap $W/wp_ask_$1.snap"; }
{ ask retry; echo "wprot off"; click 120 118 30000000; echo "snap $W/wp_retry.snap"; echo q; } > "$W/retry.cmds"
{ ask cancel; click 200 118 30000000; echo "snap $W/wp_cancel.snap"; echo q; } > "$W/cancel.cmds"
for arm in retry cancel; do
  ATARI_TRACE_FDC=1 ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$SNAP" repl < "$W/$arm.cmds" > "$W/$arm.txt" 2>&1
  echo "== $arm"
  grep -v '^FDC\|^mouse' "$W/$arm.txt" | grep 'hits\|\$0\|protect' | grep -v ' 0  first -1'
  echo "write-protected commands: $(grep -c WRITE-PROTECTED "$W/$arm.txt"), write-track commands: $(grep -c WRITE-TRACK "$W/$arm.txt"), sector writes: $(grep -c WRITE-SECTOR "$W/$arm.txt")"
done

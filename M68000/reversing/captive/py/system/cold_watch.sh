#!/bin/bash
# Cold boot with a REPL `watch <hexaddr> <decimal len>` over drive.txt's inputs (menu key 1, then Space in the
# intro) up to the mission 1 planet screen; prints the WATCH lines that are not TOS's RAM clear (pc=$fc...).
#   cold_watch.sh 140 48   -> the Medway menu ($010452) writes the $140 patch at step 40,055,110
#   cold_watch.sh 222 6    -> the track-0 decode ($075164) writes `bra $140` at step 40,062,226
#   cold_watch.sh b514 12  -> depacker $31b2 writes the original bytes, then $14e/$158/$162 patch them
# Run from anywhere; the repo root is found by walking up to tools/rdis.py.
set -e
R="${M68000_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
while [ ! -f "$R/tools/rdis.py" ]; do R="$(dirname "$R")"; [ "$R" = / ] && { echo "repo root not found" >&2; exit 1; }; done
cd "$R"
{ printf 'watch %s %s\n' "$1" "$2"; grep -v '^snap\|^q' reversing/captive/drive.txt; printf 'q\n'; } |
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 1 repl --disk-a scratchpad/captive/tmb097.st 2>&1 |
  grep 'WATCH' | grep -v 'pc=\$fc'

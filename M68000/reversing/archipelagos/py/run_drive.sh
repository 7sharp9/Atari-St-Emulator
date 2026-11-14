#!/bin/bash
# Cold boot to gameplay: writes boot30m, menu, k2, at1301c, p2, p3, n0, n2, m2 snapshots to scratchpad/archipelagos/.
d=$(cd "$(dirname "$0")" && pwd); while [ ! -f "$d/tools/rdis.py" ] && [ "$d" != / ]; do d=$(dirname "$d"); done
cd "$d" || exit 1
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 30000000 repl --disk-a scratchpad/archipelagos/tmb58.st < reversing/archipelagos/drive.txt 2>&1 | grep -E "breakpoint|saved|REPL|gave|ILLEGAL"

#!/usr/bin/env bash
# repro_xfer.sh: the natural transfer arm `$668c` (no pokes, no input): Play Random Land roll k25 (scratchpad/pm143/lands/k25.snap), run from the land start;
# expect "breakpoint $0000668c hit (1/1) after 313678190 step(s)", D7 = 4, A1 = $518f0 (side 3, group 2), then `$1c18` about 6.28M steps later (pigeon flight) with men 41 / 3 -> 44 / 0.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
printf 'disk scratchpad/powermonger.st\nbp 668c 400000000\nr\nm 51920 8\nbp 1c18 9000000\nm 51920 8\ns 20000\nm 51920 8\nq\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm143/lands/k25.snap repl 2>&1 | grep -E "breakpoint|gave|^D7|^D0|^A0|^[0-9a-f][0-9a-f] [0-9a-f][0-9a-f]"

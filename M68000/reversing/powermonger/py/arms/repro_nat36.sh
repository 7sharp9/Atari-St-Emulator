#!/usr/bin/env bash
# repro_nat36.sh: a natural mode `$36` (no input, no pokes): Play Random Land roll k108 (scratchpad/pm143/lands/k108.snap).
# Side 2's group 0 (31 men) attacks lord 8 (nation 1, home troops 0) at cell (20,42), whose cell already holds side 2's own men and a kind-$10 record:
# `$4a7a` finds no foreign settlement or man there and takes the first sheep (class 8): expect `bp 5100` "after 55343859 step(s)", A1 = $5284a,
# A3 = $4ccea (an animal owned by side 3's shepherd), and `hits` 32 x $5100, 71 x $153cc, 222 x $1547e over the next stretch; the sheep becomes category $1c.
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=${M68000_ROOT:-$(cd "$HERE/../../../.." && pwd)}
cd "$ROOT" || exit 1
ARMS=${ARMS_WORK:-scratchpad/pm148/arms}   # work dir (default named here): long/ (chunk snapshots, hits txt), sheep/, lands2/, natgate/
PYA=reversing/powermonger/py/arms
printf 'disk scratchpad/powermonger.st\nbp 5100 60000000\nr\nq\n' | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume scratchpad/pm143/lands/k108.snap repl 2>&1 | grep -E "breakpoint|gave|^D0|^A0"

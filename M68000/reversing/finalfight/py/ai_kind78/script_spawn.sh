#!/bin/sh
# script_spawn.sh: the stage script spawns kind 8 by itself. Pokes stage 0 / area 2, points the script record ($ffb1e8) at the
# third wave block of that area ($070782), camera x := $aa0; the executor then spawns kind 4, 6 and, 371 frames later, two kind 8
# (entries $0707d0 and $0707e0). Output: $FF_E_OUT/scr4.log, summary via scrwatch.py.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
"$here/sp.sh" scr4 "" 700 FF_KILL=1 FF_SCRIPTREC=1 FF_POKES="3:ff80be:00:1,3:ff80bf:02:1,3:ffb1ea:02:1,3:ffb1eb:00:1,3:ffb1ec:00:1,3:ffb1ed:00:1,3:ffb1fe:00:1,3:ffb1ee:00070782:4,3:ffb1f2:0002:2,4:ff8412:0aa0:2,4:ff856e:0b20:2" >/dev/null
python3 "$here/scrwatch.py" "$out/scr4.log" | grep 'kind 8'

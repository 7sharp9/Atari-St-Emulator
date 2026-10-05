#!/bin/sh
# forced2.sh: held / thrown / released / dies-in-jump runs with execution counters.  out/g_<name>.log/.hits
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
mkdir -p "$out"
ADDRS=$(cat "$here/addrs.txt")
HP="35:@3:00:1,35:@4:04:1,35:@30:ff:1,35:@24:0400:2,35:@26:0400:2,35:@28:0400:2"
r() { # name spawns stop pokes [env...]
  nm=$1; sp=$2; st=$3; pk=$4; shift 4
  "$here/sp.sh" g_$nm "$sp" "$st" FF_SPAWN_AT=30 FF_POKES="$pk" FF_MAMEARGS="-debug -debugger none" FF_ADDRS="$ADDRS" FF_HIT_OUT="$out/g_$nm.hits" "$@" >/dev/null
  echo "$nm done"
}
r grabthrow "8:0:0:45:47" 330 "$HP" FF_PLAN2="$here/plan_grab.lua"
# held, then the holder's grab flag (Cody +64 = $ff8568+64) is cleared at rel 100: the link breaks and the record falls to mode 8
r release "8:0:0:45:47" 330 "$HP,100:ff85a8:00:1" FF_PLAN2="$here/plan_grab_only.lua"
# killed while jumping off (mode 4 step 4): hp := -1 at rel 120 (first run: jump happens near rel 106-140 when spawned near the right edge)
r jumpdie "8:0:0:150:47" 330 "$HP" 
# thrown, then hp poked to 1 so the impact kills it: the only route into dying mode 2 ($3d058/$3d080/$3d094)
r thrdie "8:0:0:45:47" 330 "$HP,166:@24:0001:2,166:@26:0001:2" FF_PLAN2="$here/plan_grab.lua"

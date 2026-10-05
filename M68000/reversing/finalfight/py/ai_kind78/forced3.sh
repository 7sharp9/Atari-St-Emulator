#!/bin/sh
# forced3.sh: (a) hit reactions while held (3d2f0 table 3d318 by 63(A6)), (b) death at the end of a knockdown slide (3caee -> dying mode 2)
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
mkdir -p "$out"
ADDRS=$(cat "$here/addrs.txt")
HP="35:@3:00:1,35:@4:04:1,35:@30:ff:1,35:@24:0400:2,35:@26:0400:2,35:@28:0400:2"
r() { nm=$1; sp=$2; st=$3; pk=$4; shift 4
  "$here/sp.sh" g_$nm "$sp" "$st" FF_SPAWN_AT=30 FF_POKES="$pk" FF_MAMEARGS="-debug -debugger none" FF_ADDRS="$ADDRS" FF_HIT_OUT="$out/g_$nm.hits" "$@" >/dev/null; echo "$nm done"; }
# held from rel 43 (see plan_grab_only); at rel 60 lower hp by 5 (word @24 := $3fb) and set the hit id
for id in 0 3 5 8; do
  r held$id "8:0:0:45:47" 200 "$HP,60:@63:$(printf %02x $id):1,60:@24:03fb:2" FF_PLAN2="$here/plan_grab_only.lua"
done
r heldkill "8:0:0:45:47" 200 "$HP,60:@63:00:1,60:@24:ffff:2" FF_PLAN2="$here/plan_grab_only.lua"
# id 5 knockdown (see f_5: step 6 = 3caee runs from rel 82): kill at rel 83
r react5kill "8:0:0:30:47" 260 "36:@3:06:1,36:@4:00:1,36:@5:00:1,36:@63:05:1,36:@24:0400:2,36:@26:0400:2,36:@28:0400:2,36:@62:01:1,82:@24:ffff:2,82:@80:0000:2,82:@82:0000:2"
# id 6 knockdown (step 3cc00 runs from rel 64 in f_6): kill at rel 65
r react6kill "8:0:0:30:47" 260 "36:@3:06:1,36:@4:00:1,36:@5:00:1,36:@63:06:1,36:@24:0400:2,36:@26:0400:2,36:@28:0400:2,36:@62:01:1,64:@24:ffff:2,64:@80:0000:2,64:@82:0000:2"

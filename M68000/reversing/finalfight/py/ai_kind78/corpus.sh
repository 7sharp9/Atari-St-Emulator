#!/bin/sh
# corpus.sh: natural runs of kind 8 from ff_enemies (Cody idle, other enemies cleared), with execution counters on every
# state entry of the handler.  Output: out/c_<n>.log (state log) and out/c_<n>.hits.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FF_E_OUT:-$root/scratchpad/finalfight/p3/e/out}
mkdir -p "$out"
ADDRS=$(cat "$here/addrs.txt")
n=0
run() { # <spawns> <rel_stop> [env...]
  n=$((n+1)); sp=$1; st=$2; shift 2
  "$here/sp.sh" c_$n "$sp" "$st" FF_SPAWN_AT=30 FF_MAMEARGS="-debug -debugger none" FF_ADDRS="$ADDRS" FF_HIT_OUT="$out/c_$n.hits" "$@" >/dev/null
  echo "run $n: $sp $st $*"
}
run "8:0:0:60:47" 500
run "8:0:0:-60:47" 500
run "8:0:0:150:47" 500
run "8:0:0:-100:47" 500
run "8:0:0:60:28" 500
run "8:0:0:-60:64" 500
run "8:0:0:100:47" 500
run "8:0:0:30:47" 500

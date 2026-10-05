#!/bin/sh
# trace_all.sh <lo-hex> <hi-hex> : rtrace each song id lo..hi (decimal loop over hex values), 300 frames after the latch write, one MAME per id,
# up to 4 in parallel.  Output out/rt_<id>.log
here=$(cd "$(dirname "$0")" && pwd)
lo=$((0x$1)); hi=$((0x$2)); i=$lo; n=0
while [ $i -le $hi ]; do
  id=$(printf '%02x' $i)
  "$here/mlua.sh" rtrace.lua "rt_$id" CB_STOP=470 CMDS="170:$id" > "$here/out/rt_$id.stdout" 2>&1 &
  n=$((n+1)); i=$((i+1))
  if [ $n -ge 4 ]; then wait; n=0; fi
done
wait

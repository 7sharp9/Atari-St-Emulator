#!/bin/sh
# chain.sh <stage byte> <steps> : from the state sb_s<stage byte> play until 190(A5) changes, save sb_s<new stage byte>, repeat <steps> times.
# The stage byte is not +1 per stage (it goes 1 -> 6 after the subway). Log per played stage: $FFS_OUT/s<stage byte>.log; the last line is "STOP <frame> ... stage=<new>".
# FF_BOT_PROPS=1 is needed from stage 1 on (barrels block the walk). Stops when a step ends on the frame limit instead of a stage change.
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
out=${FFS_OUT:-$root/scratchpad/finalfight/stage/out}
cur=$1; n=0
while [ "$n" -lt "$2" ]; do
  FF_BOT_PROPS=1 FF_LOAD=sb_s$cur FF_BOT_START=0 FF_BOT_LEAVE=$cur FF_SAVE_PREFIX=sb_s FF_BOT_STOPF=${CHAIN_MAXF:-300000} FF_BOT_LOG="$out/s$cur.log" sh "$here/run.sh" custom >/dev/null 2>&1
  last=$(tail -1 "$out/s$cur.log"); echo "stage $cur: $last"
  new=$(echo "$last" | sed -n 's/.*stage=\([0-9]*\).*/\1/p')
  [ -n "$new" ] && [ "$new" != "$cur" ] || break
  cur=$new; n=$((n + 1))
done

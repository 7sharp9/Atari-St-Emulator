#!/bin/sh
# stall4.sh : the stage 4 stall test of README.md ("Why stage 4 is slow"). From sb_s4 play to frame 102,000 and save st4stall, then two runs of 6,000 frames from it
# that differ only in FF_BOT_ARMDX (A unset, B 50). Output under $ST4_ROOT (default scratchpad/finalfight/bossrec/aux/stall): A/out/s.log, B/out/s.log.
# Expected: A ends with the camera at $b80, B at $1060 with 17 more pool-2 spawns (S lines).
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
R=${ST4_ROOT:-$root/scratchpad/finalfight/bossrec/aux/stall}
OPTS="FF_BOT_LANEFIX=1 FF_BOT_LURE=1 FF_BOT_UNSTICK=1 FF_BOT_HP0=1 FF_BOT_PROPS=1 FF_BOT_START=0"
mkdir -p "$R/run/sta/ffightuc" "$R/out"
if [ ! -f "$R/run/sta/ffightuc/st4stall.sta" ]; then
  cp "$root/scratchpad/finalfight/stage/run/sta/ffightuc/sb_s4.sta" "$R/run/sta/ffightuc/"
  env $OPTS FF_LOAD=sb_s4 FF_BOT_STOPF=102000 FF_SAVE=st4stall FF_BOT_LOG="$R/out/save.log" FF_BOT_DUMP=102000 FFS_RUN="$R/run" FFS_OUT="$R/out" sh "$here/run.sh" custom > "$R/out/save.out" 2>&1
fi
for v in A B; do
  mkdir -p "$R/$v/run/sta/ffightuc" "$R/$v/out"; cp "$R/run/sta/ffightuc/st4stall.sta" "$R/$v/run/sta/ffightuc/"
  x=; [ $v = B ] && x="FF_BOT_ARMDX=50"
  env $OPTS $x FF_LOAD=st4stall FF_BOT_STOPF=108000 FF_BOT_LOG="$R/$v/out/s.log" FFS_RUN="$R/$v/run" FFS_OUT="$R/$v/out" sh "$here/run.sh" custom > "$R/$v/out/run.out" 2>&1 &
done
wait
for v in A B; do echo "$v: $(tail -1 "$R/$v/out/s.log"); pool-2 S lines $(grep -c '^S .*pool=2' "$R/$v/out/s.log")"; done

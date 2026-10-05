#!/bin/sh
# playtap.sh <name> boss|stage1|custom : run py/stage/run.sh's step with write taps (FF_W) logged to out/<name>.tap. Own run dir run_<name>.
# usage: FF_W="ff8144-ff8183,ff8184-ff8203" ./playtap.sh ring boss
here=$(cd "$(dirname "$0")" && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
root=$(cd "$here/../../../.." && pwd)
name=$1; step=$2
run=$base/runs/run_$name; out=$base/out/$name
mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$out/tmp"
for s in sb_boss sb_s1 sb_s2 sb_s6; do [ -f "$base/run/sta/ffightuc/$s.sta" ] && cp -n "$base/run/sta/ffightuc/$s.sta" "$run/sta/ffightuc/"; done
export FF_DIR="$root/reversing/finalfight/lua" FF_OUT="$out" SDL_VIDEODRIVER=dummy FF_SAVE_FRAME=99999 FF_STOP=${FF_STOP:-1000000}
export FF_TAP_OUT="$out/$name.tap"
case "$step" in
  boss)   export FF_PLAN="$root/reversing/finalfight/lua/plans/plan1.lua" FF_BOT_START=2450 FF_BOT_CAM=2720 FF_BOT_LOG="$out/boss.log" ;;
  stage1) export FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STAGE=1 FF_BOT_STOPF=30000 FF_BOT_LOG="$out/stage1.log" ;;
  custom) ;;
esac
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle $FF_MAMEARGS \
  -seconds_to_run "${FFS_SECONDS:-6000}" -autoboot_script "$here/${LUA:-tapbot.lua}"

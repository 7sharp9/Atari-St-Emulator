#!/bin/sh
# p4/b run wrapper: like py/stage/run.sh but runs bbot.lua (stagebot.lua with correct pool strides and write taps, FF_BOT_WLOG=<file>).
#   run.sh boss | stage1 | full | custom   (full = cold boot to the stage byte 1; env: FF_LOAD FF_BOT_START FF_BOT_STOPF FF_BOT_CAM FF_BOT_STAGE FF_BOT_SCRIPT FF_BOT_LOG FF_BOT_WLOG FF_BOT_DUMP FF_BOT_GOD FF_SAVE)
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../../../.." && pwd)
ff="$root/reversing/finalfight"
run=${BB_RUN:-$root/scratchpad/finalfight/placement/run}
out=${BB_OUT:-$root/scratchpad/finalfight/placement/out}
mkdir -p "$run/cfg" "$run/nvram" "$run/sta" "$run/snap" "$out/tmp"
export FF_DIR="$ff/lua" FF_OUT="$out" SDL_VIDEODRIVER=dummy
export FF_SAVE_FRAME=99999 FF_STOP=${FF_STOP:-60000}
step=${1:-custom}
case "$step" in
  boss)   export FF_PLAN="$ff/lua/plans/plan1.lua" FF_BOT_START=2450 FF_BOT_CAM=2720 FF_SAVE=${FF_SAVE:-b_boss} FF_BOT_LOG="$out/boss.log" FF_BOT_WLOG="$out/boss.w" ;;
  stage1) export FF_LOAD=sb_boss FF_BOT_START=0 FF_BOT_STAGE=1 FF_BOT_STOPF=30000 FF_SAVE=${FF_SAVE:-b_stage1} FF_BOT_LOG="$out/stage1.log" FF_BOT_WLOG="$out/stage1.w" ;;
  full)   export FF_PLAN="$ff/lua/plans/plan1.lua" FF_BOT_START=2450 FF_BOT_STAGE=1 FF_BOT_STOPF=30000 FF_SAVE=${FF_SAVE:-b_full} FF_BOT_LOG="$out/full.log" FF_BOT_WLOG="$out/full.w" FF_BOT_SLOG="$out/full_early.log" ;;
  custom) ;;
  *) echo "usage: $0 boss | stage1 | full | custom" >&2; exit 2 ;;
esac
cd "$run" || exit 1
exec mame ffightuc -rompath "${FF_ROMS:-$HOME/mame-roms}" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" \
  -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle ${FF_MAMEARGS} \
  -seconds_to_run "${BB_SECONDS:-900}" -autoboot_script "$here/bbot.lua"

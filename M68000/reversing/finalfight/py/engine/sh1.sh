#!/bin/sh
# sh1.sh <name> <state> <calls> [n]: run shake.lua from a state in its own run dir
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
name=$1; run=$base/runs/run_$name; mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$base/out/$name"
cp -n "$base/run/sta/ffightuc/$2.sta" "$run/sta/ffightuc/"
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy SH_LOAD=$2 SH_CALLS="$3" SH_N=${4:-80} SH_LOG="$base/out/$name/shake.log"
cd "$run" || exit 1
exec mame ffightuc -rompath "$HOME/mame-roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -seconds_to_run 600 -autoboot_script "$here/shake.lua"

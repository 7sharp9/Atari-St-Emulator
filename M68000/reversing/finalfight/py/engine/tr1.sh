#!/bin/sh
# tr1.sh <name> <state> [VAR=val..]: terr.lua from a state in its own run dir; log out/<name>/terr.log
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
name=$1; st=$2; shift 2
run=$base/runs/run_$name; mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$base/out/$name"
cp -n "$base/run/sta/ffightuc/$st.sta" "$run/sta/ffightuc/"
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy TR_LOAD=$st TR_LOG="$base/out/$name/terr.log"
for kv in "$@"; do export "$kv"; done
cd "$run" || exit 1
exec mame ffightuc -rompath "$HOME/mame-roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -seconds_to_run 900 -autoboot_script "$here/terr.lua"

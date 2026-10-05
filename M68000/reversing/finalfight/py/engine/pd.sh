#!/bin/sh
# pd.sh <name> <state> [VAR=val ...] : propdrive.lua from a state; PD_ADDRS needs PD_DEBUG=1. Log out/<name>/pd.log, snapshots runs/run_<name>/snap
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
name=$1; st=$2; shift 2
run=$base/runs/run_$name; mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$base/out/$name"
cp -n "$base/run/sta/ffightuc/$st.sta" "$run/sta/ffightuc/"
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy PD_LOAD=$st PD_LOG="$base/out/$name/pd.log"
for kv in "$@"; do export "$kv"; done
dbg=""; [ "$PD_DEBUG" = 1 ] && dbg="-debug -debugger none"
cd "$run" || exit 1
mame ffightuc -rompath "$HOME/mame-roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle $dbg -seconds_to_run 900 -autoboot_script "$here/propdrive.lua" > "$base/out/$name/mame.err" 2>&1
tail -1 "$base/out/$name/mame.err"

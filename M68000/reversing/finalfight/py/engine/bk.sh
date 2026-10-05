#!/bin/sh
# bk.sh <name> <kind:ch:x:y:lvl> <killat> <frames> [ADDRS]: sb_boss + a hand-spawned pool-4 boss (dmk.lua), killed by hp poke; breakpoint counts on the $1b428 boss sites. out/bk/<name>.*
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
name=$1; sp=$2; kill=$3; n=$4; addrs=${5:-"1b428 3ed0e 426d8 477bc 4d550"}
run=$base/runs/run_bk_$name; mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$base/out/bk"
cp -n "$base/run/sta/ffightuc/sb_boss.sta" "$run/sta/ffightuc/"
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy DM_LOAD=sb_boss DM_STOPF=$((8299+n)) DM_SPAWN="$sp@8310" DMK_KILLAT=$kill DM_GOD=1 DM_BOT=${BK_BOT:-0} DM_POKES="${BK_POKES:-}" DM_LOG="$base/out/bk/$name.log" DM_LOGN=10 DM_ADDRS="$addrs" DM_HITLOG="$base/out/bk/$name.hits" DM_OUT="$base/out/bk"
cd "$run" || exit 1
mame ffightuc -rompath "$HOME/mame-roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -debug -debugger none -seconds_to_run 900 -autoboot_script "${BK_LUA:-$here/dmk.lua}" > "$base/out/bk/$name.err" 2>&1
tail -2 "$base/out/bk/$name.err"

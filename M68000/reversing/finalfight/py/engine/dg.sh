#!/bin/sh
# dg.sh <name> <state> <frames> : dumpgfx.lua -> out/<name>/gfx.bin (+ .ram)
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../../../.." && pwd)
base=${FFB_BASE:-$(cd "$here/../../../.." && pwd)/scratchpad/finalfight/engine}   # work area (runs/, out/, run/sta/); default scratchpad/finalfight/engine; FFB_BASE overrides
name=$1; st=$2; n=$3
run=$base/runs/run_$name; mkdir -p "$run/cfg" "$run/nvram" "$run/sta/ffightuc" "$run/snap" "$base/out/$name"
for d in "$base/run/sta/ffightuc" "$root/scratchpad/finalfight/placement/run/sta/ffightuc"; do [ -f "$d/$st.sta" ] && cp -n "$d/$st.sta" "$run/sta/ffightuc/"; done
export FF_DIR="$root/reversing/finalfight/lua" SDL_VIDEODRIVER=dummy DG_LOAD=$st DG_N=$n DG_OUT="$base/out/$name/gfx.bin"
cd "$run" || exit 1
mame ffightuc -rompath "$HOME/mame-roms" -cfg_directory "$run/cfg" -nvram_directory "$run/nvram" -state_directory "$run/sta" -snapshot_directory "$run/snap" -video none -sound none -nothrottle -seconds_to_run 900 -autoboot_script "$here/dumpgfx.lua" > "$base/out/$name/mame.log" 2>&1
sha256sum "$base/out/$name/gfx.bin" "$base/out/$name/gfx.bin.ram" | cut -c1-20
